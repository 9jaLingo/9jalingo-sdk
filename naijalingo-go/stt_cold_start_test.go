package naijalingo

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

const okResponse = `{"status":"success","result":{"text":"how we dey","language":"pcm_Latn","duration":1.5}}`

func writeJSON(w http.ResponseWriter, status int, body string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = w.Write([]byte(body))
}

func queuedBody(jobID string) string {
	b, _ := json.Marshal(map[string]any{"status": "queued", "job_id": jobID, "retry_after": 5, "warming": true})
	return string(b)
}

func newColdStartClient(url string) *Client {
	c := NewClient(ClientOptions{APIKey: "test-key", BaseURL: url})
	c.coldStartPollInterval = time.Millisecond
	return c
}

func apiError(t *testing.T, err error) *APIError {
	t.Helper()
	var apiErr *APIError
	if !errors.As(err, &apiErr) {
		t.Fatalf("expected *APIError, got %T: %v", err, err)
	}
	return apiErr
}

func TestSTTWarmEngineAnswersDirectlyAndOptsInToAsync(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if got := r.Header.Get("Prefer"); got != "respond-async-on-cold-start" {
			t.Errorf("Prefer = %q", got)
		}
		writeJSON(w, 200, okResponse)
	}))
	defer server.Close()

	got, err := newColdStartClient(server.URL).STT.Transcribe(context.Background(), "https://a.example/a.wav", TranscribeOptions{Language: "pcm"})
	if err != nil {
		t.Fatal(err)
	}
	if got.Text != "how we dey" || got.Language != "pcm_Latn" || got.Duration != 1.5 {
		t.Fatalf("unexpected transcript: %#v", got)
	}
}

func TestSTTColdStartWaitsForQueuedJob(t *testing.T) {
	var polls int32
	paths := make(chan string, 16)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		paths <- r.URL.EscapedPath()
		if r.Header.Get("X-API-Key") != "test-key" {
			t.Errorf("missing API key on %s", r.URL.Path)
		}
		if r.Method == http.MethodPost {
			writeJSON(w, 202, queuedBody("job/unsafe"))
			return
		}
		switch atomic.AddInt32(&polls, 1) {
		case 1:
			writeJSON(w, 200, `{"status":"queued","warming":true,"retry_after":5}`)
		case 2:
			writeJSON(w, 200, `{"status":"running","warming":true}`)
		default:
			writeJSON(w, 200, `{"status":"completed","response":`+okResponse+`}`)
		}
	}))
	defer server.Close()

	got, err := newColdStartClient(server.URL).STT.Transcribe(context.Background(), "https://a.example/a.wav", TranscribeOptions{})
	if err != nil {
		t.Fatal(err)
	}
	if got.Text != "how we dey" {
		t.Fatalf("unexpected transcript: %#v", got)
	}
	close(paths)
	var seen []string
	for p := range paths {
		seen = append(seen, p)
	}
	want := []string{
		"/v1/audio/transcriptions",
		"/v1/audio/transcriptions/jobs/job%2Funsafe", // job id is URL-escaped
		"/v1/audio/transcriptions/jobs/job%2Funsafe",
		"/v1/audio/transcriptions/jobs/job%2Funsafe",
	}
	if strings.Join(seen, "|") != strings.Join(want, "|") {
		t.Fatalf("paths = %v, want %v", seen, want)
	}
}

func jobServer(statusBody string, pollStatus int) *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			writeJSON(w, 202, queuedBody("job-1"))
			return
		}
		writeJSON(w, pollStatus, statusBody)
	}))
}

func TestSTTFailedJobAndCapacityTimeout(t *testing.T) {
	server := jobServer(`{"status":"failed","error":"Unsupported audio format."}`, 200)
	defer server.Close()
	_, err := newColdStartClient(server.URL).STT.Transcribe(context.Background(), "https://a.example/a.wav", TranscribeOptions{})
	if e := apiError(t, err); e.StatusCode != 502 || !strings.Contains(e.Message, "Unsupported audio format") {
		t.Fatalf("unexpected error: %v", e)
	}

	server2 := jobServer(`{"status":"failed","error":"The speech engine did not start in time. You were not charged. Please try again."}`, 200)
	defer server2.Close()
	_, err = newColdStartClient(server2.URL).STT.Transcribe(context.Background(), "https://a.example/a.wav", TranscribeOptions{})
	if e := apiError(t, err); e.StatusCode != 503 || !strings.Contains(e.Message, "not charged") {
		t.Fatalf("unexpected error: %v", e)
	}
}

func TestSTTRejectsUnknownStatusMissingResultAndMalformedQueue(t *testing.T) {
	for name, body := range map[string]string{
		"unknown status": `{"status":"weird"}`,
		"missing result": `{"status":"completed"}`,
	} {
		server := jobServer(body, 200)
		_, err := newColdStartClient(server.URL).STT.Transcribe(context.Background(), "https://a.example/a.wav", TranscribeOptions{})
		server.Close()
		if e := apiError(t, err); e.StatusCode != 502 {
			t.Fatalf("%s: status = %d", name, e.StatusCode)
		}
	}
	for _, body := range []string{`{"status":"success"}`, `{"status":"queued"}`, `[1]`, `not json`} {
		queueBody := body
		server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { writeJSON(w, 202, queueBody) }))
		_, err := newColdStartClient(server.URL).STT.Transcribe(context.Background(), "https://a.example/a.wav", TranscribeOptions{})
		server.Close()
		if e := apiError(t, err); e.StatusCode != 202 {
			t.Fatalf("queue body %q: status = %d", queueBody, e.StatusCode)
		}
	}
}

func TestSTTPollingToleratesBriefGatewayErrorsButNotExpiredJobs(t *testing.T) {
	var polls int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			writeJSON(w, 202, queuedBody("job-1"))
			return
		}
		if atomic.AddInt32(&polls, 1) <= 2 {
			writeJSON(w, 502, `{"detail":"bad gateway"}`)
			return
		}
		writeJSON(w, 200, `{"status":"completed","response":`+okResponse+`}`)
	}))
	defer server.Close()
	got, err := newColdStartClient(server.URL).STT.Transcribe(context.Background(), "https://a.example/a.wav", TranscribeOptions{})
	if err != nil || got.Text != "how we dey" {
		t.Fatalf("got %#v, err %v", got, err)
	}

	gone := jobServer(`{"detail":"Transcription job not found or expired"}`, 404)
	defer gone.Close()
	_, err = newColdStartClient(gone.URL).STT.Transcribe(context.Background(), "https://a.example/a.wav", TranscribeOptions{})
	if !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound, got %v", err)
	}

	var failing int32
	dead := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			writeJSON(w, 202, queuedBody("job-1"))
			return
		}
		atomic.AddInt32(&failing, 1)
		writeJSON(w, 502, `{"detail":"bad gateway"}`)
	}))
	defer dead.Close()
	_, err = newColdStartClient(dead.URL).STT.Transcribe(context.Background(), "https://a.example/a.wav", TranscribeOptions{})
	if e := apiError(t, err); e.StatusCode != 502 || atomic.LoadInt32(&failing) != coldStartMaxPollFailures {
		t.Fatalf("expected to give up after %d polls, polled %d (err %v)", coldStartMaxPollFailures, atomic.LoadInt32(&failing), err)
	}
}

func TestSTTGivesUpAfterOverallDeadlineAndHonoursContext(t *testing.T) {
	server := jobServer(`{"status":"running"}`, 200)
	defer server.Close()

	c := newColdStartClient(server.URL)
	c.coldStartMaxWait = 50 * time.Millisecond
	_, err := c.STT.Transcribe(context.Background(), "https://a.example/a.wav", TranscribeOptions{})
	if e := apiError(t, err); e.StatusCode != 504 {
		t.Fatalf("unexpected error: %v", e)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Millisecond)
	defer cancel()
	slow := newColdStartClient(server.URL)
	slow.coldStartPollInterval = time.Hour // would block forever without ctx support
	if _, err := slow.STT.Transcribe(ctx, "https://a.example/a.wav", TranscribeOptions{}); !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("expected context deadline, got %v", err)
	}
}

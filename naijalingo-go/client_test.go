package naijalingo

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestGenerateSendsAuthenticatedSpeechRequest(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		if request.Method != http.MethodPost || request.URL.Path != "/v1/audio/speech" {
			t.Fatalf("unexpected request: %s %s", request.Method, request.URL.Path)
		}
		if got := request.Header.Get("X-API-Key"); got != "test-key" {
			t.Fatalf("X-API-Key = %q, want test-key", got)
		}
		var body map[string]any
		if err := json.NewDecoder(request.Body).Decode(&body); err != nil {
			t.Fatal(err)
		}
		if body["input"] != "Bawo ni!" || body["voice"] != "adeola_yo" || body["lang"] != "yo" {
			t.Fatalf("unexpected request body: %#v", body)
		}
		writer.Header().Set("Content-Type", "audio/wav")
		_, _ = writer.Write([]byte("wav-data"))
	}))
	defer server.Close()

	client := NewClient(ClientOptions{APIKey: "test-key", BaseURL: server.URL})
	audio, err := client.TTS.Generate(context.Background(), "Bawo ni!", GenerateOptions{
		Voice: "adeola_yo",
		Lang:  "yo",
	})
	if err != nil {
		t.Fatal(err)
	}
	if string(audio.Content) != "wav-data" || audio.MediaType != "audio/wav" {
		t.Fatalf("unexpected audio response: %#v", audio)
	}
}

func TestSTTReturnsAPIErrorForBrokenAudioURL(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		writer.Header().Set("Content-Type", "application/json")
		writer.WriteHeader(http.StatusUnprocessableEntity)
		_, _ = writer.Write([]byte(`{"detail":"Audio URL returned HTTP 404. Use a direct public audio URL."}`))
	}))
	defer server.Close()

	client := NewClient(ClientOptions{APIKey: "test-key", BaseURL: server.URL})
	_, err := client.STT.Transcribe(context.Background(), "https://audio.example/missing.wav", TranscribeOptions{Language: "yo"})
	apiError, ok := err.(*APIError)
	if !ok || apiError.StatusCode != http.StatusUnprocessableEntity || apiError.Message == "" {
		t.Fatalf("expected detailed 422 APIError, got %#v", err)
	}
}

func TestSTTRejectsErrorAndMalformedSuccessPayloads(t *testing.T) {
	cases := []struct {
		name string
		body string
	}{
		{name: "error envelope", body: `{"result":{"error":"Model failed"}}`},
		{name: "top-level error envelope", body: `{"error":"Model failed"}`},
		{name: "missing text", body: `{"result":{"language":"yor_Latn"}}`},
	}
	for _, testCase := range cases {
		t.Run(testCase.name, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
				writer.Header().Set("Content-Type", "application/json")
				_, _ = writer.Write([]byte(testCase.body))
			}))
			defer server.Close()

			client := NewClient(ClientOptions{APIKey: "test-key", BaseURL: server.URL})
			transcript, err := client.STT.Transcribe(context.Background(), "https://audio.example/sample.wav", TranscribeOptions{})
			apiError, ok := err.(*APIError)
			if !ok || apiError.StatusCode != http.StatusBadGateway {
				t.Fatalf("expected 502 APIError for %s, got transcript=%#v error=%#v", testCase.body, transcript, err)
			}
		})
	}
}

func TestSTTAcceptsEmptyTranscript(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		writer.Header().Set("Content-Type", "application/json")
		_, _ = writer.Write([]byte(`{"result":{"text":"","language":"yor_Latn"}}`))
	}))
	defer server.Close()

	client := NewClient(ClientOptions{APIKey: "test-key", BaseURL: server.URL})
	transcript, err := client.STT.Transcribe(context.Background(), "https://audio.example/silent.wav", TranscribeOptions{})
	if err != nil {
		t.Fatal(err)
	}
	if transcript.Text != "" || transcript.Language != "yor_Latn" {
		t.Fatalf("unexpected silent-audio transcription: %#v", transcript)
	}
}

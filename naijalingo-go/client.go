package naijalingo

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

const defaultBaseURL = "https://api.9jalingo.org"

// ClientOptions configures a Client. Empty values use environment/default values.
type ClientOptions struct {
	APIKey     string
	BaseURL    string
	HTTPClient *http.Client
}

// Client is a 9jaLingo API client.
type Client struct {
	apiKey     string
	baseURL    string
	httpClient *http.Client
	TTS        *TTSService
	STT        *STTService

	// Cold-start waiting (see postJSONWaitingForColdStart). Zero values use the defaults; tests
	// override them.
	coldStartPollInterval time.Duration
	coldStartMaxWait      time.Duration
}

// NewClient creates a client. APIKey and BaseURL fall back to NAIJALINGO_API_KEY
// and NAIJALINGO_BASE_URL respectively.
func NewClient(options ClientOptions) *Client {
	apiKey := options.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("NAIJALINGO_API_KEY")
	}
	baseURL := options.BaseURL
	if baseURL == "" {
		baseURL = os.Getenv("NAIJALINGO_BASE_URL")
	}
	if baseURL == "" {
		baseURL = defaultBaseURL
	}
	httpClient := options.HTTPClient
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 5 * time.Minute}
	}
	client := &Client{
		apiKey:     apiKey,
		baseURL:    strings.TrimRight(baseURL, "/"),
		httpClient: httpClient,
	}
	client.TTS = &TTSService{client: client}
	client.STT = &STTService{client: client}
	return client
}

func (c *Client) newRequest(ctx context.Context, method, path string, body io.Reader) (*http.Request, error) {
	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+"/"+strings.TrimLeft(path, "/"), body)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "naijalingo-go/0.3.0")
	if c.apiKey != "" {
		req.Header.Set("X-API-Key", c.apiKey)
	}
	return req, nil
}

func (c *Client) do(req *http.Request) (*http.Response, error) {
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		return resp, nil
	}
	defer resp.Body.Close()
	var payload struct {
		Detail string `json:"detail"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil || payload.Detail == "" {
		payload.Detail = resp.Status
	}
	return nil, &APIError{StatusCode: resp.StatusCode, Message: payload.Detail}
}

func (c *Client) getJSON(ctx context.Context, path string, destination any) error {
	req, err := c.newRequest(ctx, http.MethodGet, path, nil)
	if err != nil {
		return err
	}
	resp, err := c.do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return json.NewDecoder(resp.Body).Decode(destination)
}

func (c *Client) postJSON(ctx context.Context, path string, payload, destination any) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal request: %w", err)
	}
	req, err := c.newRequest(ctx, http.MethodPost, path, bytes.NewReader(data))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return json.NewDecoder(resp.Body).Decode(destination)
}

const (
	// While a speech engine starts from zero the API queues the request. Wait at most this long
	// (the server itself gives up after 20 minutes, then a long file still needs time to process).
	defaultColdStartMaxWait  = 40 * time.Minute
	coldStartMaxPollFailures = 5
)

type queuedJob struct {
	Status     string          `json:"status"`
	JobID      string          `json:"job_id"`
	RetryAfter float64         `json:"retry_after"`
	Error      string          `json:"error"`
	Response   json.RawMessage `json:"response"`
}

// postJSONWaitingForColdStart POSTs JSON and, if the engine is starting up, transparently waits
// for the queued job.
//
// It sends "Prefer: respond-async-on-cold-start". A warm engine answers 200 directly (identical to
// postJSON). When the engine was scaled to zero the server answers 202 with a job_id; this polls
// jobPath(jobID) until the job completes and decodes the final response into destination.
// Servers that do not know the header simply ignore it.
func (c *Client) postJSONWaitingForColdStart(
	ctx context.Context, path string, payload, destination any, jobPath func(jobID string) string, label string,
) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal request: %w", err)
	}
	req, err := c.newRequest(ctx, http.MethodPost, path, bytes.NewReader(data))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Prefer", "respond-async-on-cold-start")
	resp, err := c.do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusAccepted {
		return json.NewDecoder(resp.Body).Decode(destination)
	}

	var queued queuedJob
	if err := json.NewDecoder(resp.Body).Decode(&queued); err != nil || queued.Status != "queued" {
		return &APIError{StatusCode: http.StatusAccepted, Message: fmt.Sprintf("The API returned an invalid queued %s response.", label)}
	}
	if strings.TrimSpace(queued.JobID) == "" {
		return &APIError{StatusCode: http.StatusAccepted, Message: fmt.Sprintf("The queued %s response did not include a job ID.", label)}
	}

	statusPath := jobPath(url.PathEscape(strings.TrimSpace(queued.JobID)))
	maxWait := c.coldStartMaxWait
	if maxWait <= 0 {
		maxWait = defaultColdStartMaxWait
	}
	deadline := time.Now().Add(maxWait)
	retryAfter := queued.RetryAfter
	failures := 0

	for time.Now().Before(deadline) {
		delay := c.coldStartPollInterval
		if delay <= 0 {
			delay = time.Duration(retryAfter * float64(time.Second))
			if delay < time.Second {
				delay = time.Second
			}
			if delay > 30*time.Second {
				delay = 30 * time.Second
			}
		}
		timer := time.NewTimer(delay)
		select {
		case <-ctx.Done():
			timer.Stop()
			return ctx.Err()
		case <-timer.C:
		}

		var job queuedJob
		if err := c.getJSON(ctx, statusPath, &job); err != nil {
			if ctx.Err() != nil {
				return ctx.Err()
			}
			// A brief network or gateway problem must not abandon a job that is still running.
			var apiErr *APIError
			if errors.As(err, &apiErr) && apiErr.StatusCode < 500 {
				return err // e.g. 404: the job expired, 401: bad key
			}
			failures++
			if failures >= coldStartMaxPollFailures {
				return err
			}
			continue
		}
		failures = 0
		if job.RetryAfter > 0 {
			retryAfter = job.RetryAfter
		}

		switch strings.ToLower(job.Status) {
		case "completed":
			if len(job.Response) == 0 || string(job.Response) == "null" {
				return &APIError{StatusCode: http.StatusBadGateway, Message: fmt.Sprintf("The completed %s job did not include a result.", label)}
			}
			return json.Unmarshal(job.Response, destination)
		case "failed":
			message := job.Error
			if message == "" {
				message = fmt.Sprintf("Queued %s job failed.", label)
			}
			if strings.Contains(strings.ToLower(message), "did not start in time") {
				return &APIError{StatusCode: http.StatusServiceUnavailable, Message: message}
			}
			return &APIError{StatusCode: http.StatusBadGateway, Message: message}
		case "queued", "running", "processing":
		default:
			return &APIError{
				StatusCode: http.StatusBadGateway,
				Message:    fmt.Sprintf("The queued %s job returned an unknown status: %q.", label, job.Status),
			}
		}
	}
	return &APIError{StatusCode: http.StatusGatewayTimeout, Message: fmt.Sprintf("Queued %s job did not finish in time.", label)}
}

// ListModels returns OpenAI-compatible model metadata.
func (c *Client) ListModels(ctx context.Context) (ModelList, error) {
	var models ModelList
	return models, c.getJSON(ctx, "/v1/models", &models)
}

// APIInfo returns root API metadata.
func (c *Client) APIInfo(ctx context.Context) (APIInfo, error) {
	var info APIInfo
	return info, c.getJSON(ctx, "/", &info)
}

// ServiceInfo returns v1 service metadata.
func (c *Client) ServiceInfo(ctx context.Context) (ServiceInfo, error) {
	var info ServiceInfo
	return info, c.getJSON(ctx, "/v1", &info)
}

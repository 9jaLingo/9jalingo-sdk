package naijalingo

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
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
	return client
}

func (c *Client) newRequest(ctx context.Context, method, path string, body io.Reader) (*http.Request, error) {
	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+"/"+strings.TrimLeft(path, "/"), body)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "naijalingo-go/0.1.0")
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

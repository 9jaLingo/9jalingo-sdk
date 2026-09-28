package naijalingo

import "context"

// STTService exposes speech transcription operations.
type STTService struct{ client *Client }

type TranscribeOptions struct {
	Language        string  `json:"language,omitempty"`
	DurationSeconds float64 `json:"duration_seconds,omitempty"`
}

type Transcription struct {
	Text     string  `json:"text"`
	Language string  `json:"language"`
	Duration float64 `json:"duration"`
	Model    string  `json:"model"`
}

func (s *STTService) Transcribe(ctx context.Context, fileURL string, options TranscribeOptions) (Transcription, error) {
	payload := map[string]any{"file_url": fileURL}
	if options.Language != "" { payload["language"] = options.Language }
	if options.DurationSeconds > 0 { payload["duration_seconds"] = options.DurationSeconds }
	var response struct { Result struct { Result Transcription `json:"result"`; Text string `json:"text"`; Language string `json:"language"`; Duration float64 `json:"duration"`; Model string `json:"model"` } `json:"result"` }
	err := s.client.postJSON(ctx, "/v1/audio/transcriptions", payload, &response)
	if response.Result.Text != "" { return Transcription{Text: response.Result.Text, Language: response.Result.Language, Duration: response.Result.Duration, Model: response.Result.Model}, err }
	return response.Result.Result, err
}
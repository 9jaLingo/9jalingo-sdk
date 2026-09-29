package naijalingo

import "context"
import "net/http"

// STTService exposes speech transcription operations.
type STTService struct{ client *Client }

type TranscribeOptions struct {
	Language string `json:"language,omitempty"`
}

type Transcription struct {
	Text     string  `json:"text"`
	Language string  `json:"language"`
	Duration float64 `json:"duration"`
	Model    string  `json:"model"`
}

func (s *STTService) Transcribe(ctx context.Context, fileURL string, options TranscribeOptions) (Transcription, error) {
	payload := map[string]any{"file_url": fileURL}
	if options.Language != "" {
		payload["language"] = options.Language
	}
	type transcriptionResponse struct {
		Result   *transcriptionResponse `json:"result"`
		Text     *string                `json:"text"`
		Language string                 `json:"language"`
		Duration float64                `json:"duration"`
		Model    string                 `json:"model"`
		Error    string                 `json:"error"`
	}
	var response transcriptionResponse
	err := s.client.postJSON(ctx, "/v1/audio/transcriptions", payload, &response)
	if err != nil {
		return Transcription{}, err
	}
	result := &response
	for result.Result != nil {
		result = result.Result
	}
	if result.Error != "" {
		return Transcription{}, &APIError{StatusCode: http.StatusBadGateway, Message: result.Error}
	}
	if result.Text == nil {
		return Transcription{}, &APIError{
			StatusCode: http.StatusBadGateway,
			Message:    "The API returned an invalid transcription response.",
		}
	}
	return Transcription{
		Text:     *result.Text,
		Language: result.Language,
		Duration: result.Duration,
		Model:    result.Model,
	}, nil
}

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

// Transcribe transcribes audio hosted at a public HTTPS URL. options.Language is one of
// "yo", "ig", "ha", "pcm" or "en". If the speech engine was idle it needs a few minutes to start;
// Transcribe then waits for the queued job instead of failing (cancel ctx to stop waiting), and long
// recordings (over 40 s) are split automatically.
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
	err := s.client.postJSONWaitingForColdStart(
		ctx,
		"/v1/audio/transcriptions",
		payload,
		&response,
		func(jobID string) string { return "/v1/audio/transcriptions/jobs/" + jobID },
		"STT",
	)
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

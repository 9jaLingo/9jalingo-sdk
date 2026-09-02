package naijalingo

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
)

const defaultModel = "9jalingo-tts-1"

// TTSService exposes speech generation, voice cloning, and voice discovery.
type TTSService struct{ client *Client }

type GenerateOptions struct {
	Voice             string    `json:"voice,omitempty"`
	Speaker           string    `json:"speaker,omitempty"`
	Lang              string    `json:"lang,omitempty"`
	Language          string    `json:"language,omitempty"`
	Model             string    `json:"model,omitempty"`
	SpeakerEmbedding  []float64 `json:"speaker_embedding,omitempty"`
	ResponseFormat    string    `json:"response_format,omitempty"`
	Temperature       *float64  `json:"temperature,omitempty"`
	TopP              *float64  `json:"top_p,omitempty"`
	RepetitionPenalty *float64  `json:"repetition_penalty,omitempty"`
	EnableLongForm    *bool     `json:"enable_long_form,omitempty"`
	MaxChunkDuration  *float64  `json:"max_chunk_duration,omitempty"`
	SilenceDuration   *float64  `json:"silence_duration,omitempty"`
}

func (o GenerateOptions) payload(text string) map[string]any {
	voice := o.Voice
	if o.Speaker != "" {
		voice = o.Speaker
	}
	if voice == "" && len(o.SpeakerEmbedding) == 0 {
		voice = "blessing_pcm"
	}
	lang := o.Lang
	if o.Language != "" {
		lang = o.Language
	}
	model := o.Model
	if model == "" {
		model = defaultModel
	}
	responseFormat := o.ResponseFormat
	if responseFormat == "" {
		responseFormat = "wav"
	}
	payload := map[string]any{"input": text, "voice": voice, "model": model, "response_format": responseFormat, "enable_long_form": true}
	if lang != "" {
		payload["lang"] = lang
	}
	if len(o.SpeakerEmbedding) > 0 {
		payload["speaker_embedding"] = o.SpeakerEmbedding
	}
	if o.Temperature != nil {
		payload["temperature"] = *o.Temperature
	}
	if o.TopP != nil {
		payload["top_p"] = *o.TopP
	}
	if o.RepetitionPenalty != nil {
		payload["repetition_penalty"] = *o.RepetitionPenalty
	}
	if o.EnableLongForm != nil {
		payload["enable_long_form"] = *o.EnableLongForm
	}
	if o.MaxChunkDuration != nil {
		payload["max_chunk_duration"] = *o.MaxChunkDuration
	}
	if o.SilenceDuration != nil {
		payload["silence_duration"] = *o.SilenceDuration
	}
	return payload
}

// Generate synthesizes speech and returns the complete audio response.
func (s *TTSService) Generate(ctx context.Context, text string, options GenerateOptions) (AudioResponse, error) {
	return s.audioRequest(ctx, "/v1/audio/speech", options.payload(text))
}

// Stream starts a chunked speech request. Call Close when finished reading.
func (s *TTSService) Stream(ctx context.Context, text string, options GenerateOptions) (io.ReadCloser, error) {
	data, err := json.Marshal(options.payload(text))
	if err != nil {
		return nil, err
	}
	req, err := s.client.newRequest(ctx, http.MethodPost, "/v1/audio/speech/stream", bytes.NewReader(data))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := s.client.do(req)
	if err != nil {
		return nil, err
	}
	return resp.Body, nil
}

func (s *TTSService) audioRequest(ctx context.Context, path string, payload map[string]any) (AudioResponse, error) {
	data, err := json.Marshal(payload)
	if err != nil {
		return AudioResponse{}, err
	}
	req, err := s.client.newRequest(ctx, http.MethodPost, path, bytes.NewReader(data))
	if err != nil {
		return AudioResponse{}, err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := s.client.do(req)
	if err != nil {
		return AudioResponse{}, err
	}
	defer resp.Body.Close()
	content, err := io.ReadAll(resp.Body)
	if err != nil {
		return AudioResponse{}, err
	}
	return AudioResponse{Content: content, MediaType: resp.Header.Get("Content-Type")}, nil
}

type CloneOptions struct {
	Voice             string
	Lang              string
	Speaker           string
	Model             string
	ResponseFormat    string
	Temperature       *float64
	TopP              *float64
	RepetitionPenalty *float64
}

// Clone creates a reusable voice from a reference audio file and synthesizes text.
func (s *TTSService) Clone(ctx context.Context, text, audioPath string, options CloneOptions) (CloneResponse, error) {
	file, err := os.Open(audioPath)
	if err != nil {
		return CloneResponse{}, err
	}
	defer file.Close()
	var body bytes.Buffer
	writer := multipart.NewWriter(&body)
	fields := map[string]string{"text": text, "lang": options.Lang, "model_name": options.Model, "response_format": options.ResponseFormat}
	if fields["lang"] == "" {
		fields["lang"] = options.Voice
	}
	if fields["model_name"] == "" {
		fields["model_name"] = defaultModel
	}
	if fields["response_format"] == "" {
		fields["response_format"] = "wav"
	}
	if options.Speaker != "" {
		fields["voice"] = options.Speaker
	}
	for key, value := range fields {
		if value != "" {
			_ = writer.WriteField(key, value)
		}
	}
	if options.Temperature != nil {
		_ = writer.WriteField("temperature", fmt.Sprint(*options.Temperature))
	}
	if options.TopP != nil {
		_ = writer.WriteField("top_p", fmt.Sprint(*options.TopP))
	}
	if options.RepetitionPenalty != nil {
		_ = writer.WriteField("repetition_penalty", fmt.Sprint(*options.RepetitionPenalty))
	}
	part, err := writer.CreateFormFile("audio", filepath.Base(audioPath))
	if err != nil {
		return CloneResponse{}, err
	}
	if _, err = io.Copy(part, file); err != nil {
		return CloneResponse{}, err
	}
	if err = writer.Close(); err != nil {
		return CloneResponse{}, err
	}
	req, err := s.client.newRequest(ctx, http.MethodPost, "/v1/audio/clone", &body)
	if err != nil {
		return CloneResponse{}, err
	}
	req.Header.Set("Content-Type", writer.FormDataContentType())
	resp, err := s.client.do(req)
	if err != nil {
		return CloneResponse{}, err
	}
	defer resp.Body.Close()
	content, err := io.ReadAll(resp.Body)
	if err != nil {
		return CloneResponse{}, err
	}
	return CloneResponse{AudioResponse: AudioResponse{Content: content, MediaType: resp.Header.Get("Content-Type")}, VoiceID: resp.Header.Get("X-Voice-ID"), VoiceCode: resp.Header.Get("X-Voice-Code"), VoiceName: resp.Header.Get("X-Voice-Name"), CloneID: resp.Header.Get("X-Clone-ID"), JobID: resp.Header.Get("X-Job-ID")}, nil
}

func (s *TTSService) ListSpeakers(ctx context.Context, language, gender, domain string) (SpeakerList, error) {
	query := url.Values{}
	if language != "" {
		query.Set("language", language)
	}
	if gender != "" {
		query.Set("gender", gender)
	}
	if domain != "" {
		query.Set("domain", domain)
	}
	path := "/v1/speakers"
	if encoded := query.Encode(); encoded != "" {
		path += "?" + encoded
	}
	var speakers SpeakerList
	return speakers, s.client.getJSON(ctx, path, &speakers)
}

func (s *TTSService) GetSpeaker(ctx context.Context, speakerID string) (Speaker, error) {
	var speaker Speaker
	return speaker, s.client.getJSON(ctx, "/v1/speakers/"+url.PathEscape(speakerID), &speaker)
}

func (s *TTSService) DeleteVoice(ctx context.Context, voiceID string) error {
	req, err := s.client.newRequest(ctx, http.MethodDelete, "/v1/voices/"+url.PathEscape(voiceID), nil)
	if err != nil {
		return err
	}
	resp, err := s.client.do(req)
	if resp != nil {
		resp.Body.Close()
	}
	return err
}

func (s *TTSService) ListLanguages(ctx context.Context) (LanguageList, error) {
	var languages LanguageList
	return languages, s.client.getJSON(ctx, "/v1/languages", &languages)
}

func (s *TTSService) Health(ctx context.Context) (HealthStatus, error) {
	var health HealthStatus
	return health, s.client.getJSON(ctx, "/v1/health", &health)
}

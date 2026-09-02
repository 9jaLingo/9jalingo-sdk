package naijalingo

// AudioResponse contains generated audio and its MIME type.
type AudioResponse struct {
	Content   []byte
	MediaType string
}

// CloneResponse includes audio and metadata for a reusable cloned voice.
type CloneResponse struct {
	AudioResponse
	VoiceID   string
	VoiceCode string
	VoiceName string
	CloneID   string
	JobID     string
}

type Speaker struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Language string `json:"language"`
	Gender   string `json:"gender"`
	Domain   string `json:"domain"`
}

type SpeakerList struct {
	Speakers   []Speaker      `json:"speakers"`
	Total      int            `json:"total"`
	ByLanguage map[string]int `json:"by_language"`
}

type Language struct {
	Name         string `json:"name"`
	SpeakerCount int    `json:"speaker_count"`
}

type LanguageList struct {
	Languages map[string]Language `json:"languages"`
	Domains   []string            `json:"domains"`
}

type HealthStatus struct {
	Status         string   `json:"status"`
	SpeakersLoaded int      `json:"speakers_loaded"`
	Languages      []string `json:"languages"`
}

type Model struct {
	ID      string `json:"id"`
	Object  string `json:"object"`
	OwnedBy string `json:"owned_by"`
}

type ModelList struct {
	Object string  `json:"object"`
	Data   []Model `json:"data"`
}

type APIInfo struct {
	Name        string            `json:"name"`
	Version     string            `json:"version"`
	Description string            `json:"description"`
	Endpoints   map[string]string `json:"endpoints"`
}

type ServiceInfo struct {
	Object          string `json:"object"`
	Name            string `json:"name"`
	ModelsURL       string `json:"models_url"`
	SpeechURL       string `json:"speech_url"`
	SpeechStreamURL string `json:"speech_stream_url"`
}

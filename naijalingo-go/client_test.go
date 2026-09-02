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

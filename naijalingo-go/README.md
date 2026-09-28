# 9jaLingo Go SDK

Official Go client for the 9jaLingo Text-to-Speech, Speech-to-Text, and
voice-cloning API.

## Install

```bash
# Run in your application directory. `go get` requires a Go module.
go mod init example.com/my-9jalingo-app
go get github.com/9jaLingo/9jalingo-sdk/naijalingo-go
export NAIJALINGO_API_KEY="YOUR_API_KEY"
```

Requires Go 1.22 or later. `NAIJALINGO_BASE_URL` optionally overrides the API URL for a self-hosted server.

## Quick start

```go
package main

import (
    "context"
    "log"
    "os"

    naijalingo "github.com/9jaLingo/9jalingo-sdk/naijalingo-go"
)

func main() {
    client := naijalingo.NewClient(naijalingo.ClientOptions{})
    audio, err := client.TTS.Generate(context.Background(), "Bawo ni, I dey greet you!", naijalingo.GenerateOptions{
        Voice: "adeola_yo", Lang: "yo",
    })
    if err != nil {
        log.Fatal(err)
    }
    if err := os.WriteFile("greeting.wav", audio.Content, 0o644); err != nil {
        log.Fatal(err)
    }
}
```

Run the included end-to-end example:

```bash
export NAIJALINGO_API_KEY="YOUR_API_KEY"
go run ./examples/tts
```

## Speech-to-Text

```go
transcript, err := client.STT.Transcribe(
    context.Background(),
    "https://cdn.example.com/pidgin-sample.wav",
    naijalingo.TranscribeOptions{Language: "pcm", DurationSeconds: 8.1},
)
if err != nil {
    log.Fatal(err)
}
fmt.Println(transcript.Text, transcript.Language, transcript.Duration)
```

The audio URL must be publicly reachable and your API key must have the `stt`
scope. Supported language hints are `yo`, `ha`, `ig`, `pcm`, and `en`.

For an offline request/response check that works directly in GoLand, run `go test ./...`.

## API

`client.TTS` provides `Generate`, `Stream`, `Clone`, `ListSpeakers`, `GetSpeaker`, `DeleteVoice`, `ListLanguages`, and `Health`. The client also exposes `ListModels`, `APIInfo`, and `ServiceInfo`.

`Generate` and `Stream` accept speaker IDs in `Voice` or `Speaker`, and language codes in `Lang` or `Language`. Use `ha`, `ig`, `yo`, or `pcm`. For `Clone`, set `CloneOptions.Voice` to the language code and pass a local reference-audio path.

## Error handling

All non-2xx responses return `*naijalingo.APIError`, which includes `StatusCode` and `Message`.

```go
if errors.Is(err, naijalingo.ErrAuthentication) {
    // Check NAIJALINGO_API_KEY.
}
```

## Development

```bash
go test ./...
go vet ./...
```

## License

MIT
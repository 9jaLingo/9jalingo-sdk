# 9jaLingo SDKs

Official client libraries for the [9jaLingo](https://www.9jalingo.org) API — Text-to-Speech and Voice Cloning for Hausa, Igbo, Yoruba, and Nigerian Pidgin.

---

[![Watch the video](https://img.youtube.com/vi/Ib8WVXiwPlU/maxresdefault.jpg)](https://youtu.be/Ib8WVXiwPlU)

Whether you're building voice assistants, accessibility tools, e-learning platforms, audiobook generators, or any application that needs high-quality African language speech synthesis — 9jaLingo has you covered.

### Key Features

- 🗣️ **Text-to-Speech** — Convert text to natural speech in 4 Nigerian languages
- 🎭 **240+ Speaker Voices** — Choose from a diverse library of male and female voices
- 🔊 **Voice Cloning** — Clone any voice from a short reference audio sample (WAV, MP3, M4A, etc.)
- 🎧 **Multi-Format Output** — Export speech natively to WAV, PCM, MP3, FLAC, AAC, ALAC, or OGG
- 📡 **Streaming** — Stream audio chunks as they're generated for real-time playback
- ⚡ **Long-Form Generation** — Automatically handles long texts with intelligent chunking
- 🤖 **OpenAI-Compatible** — Drop-in replacement for OpenAI TTS with Nigerian language support
- 📝 **Speech-to-Text** — Transcribe publicly hosted Nigerian-language audio through `client.stt`

---

| SDK | Directory | Install |
|-----|-----------|---------|
| **Python** | [`python-naijalingo/`](python-naijalingo/) | `pip install naijalingo` |
| **Node.js** | [`naijalingo-js/`](naijalingo-js/) | `npm install naijalingo` |
| **Go** | [`naijalingo-go/`](naijalingo-go/) | `go get github.com/9jaLingo/9jalingo-sdk/naijalingo-go` |

## Quick start

**Python**

```bash
pip install naijalingo
export NAIJALINGO_API_KEY="YOUR_API_KEY"
```

```python
from naijalingo import NaijaLingo

client = NaijaLingo()
audio = client.tts.generate("Bawo ni!", voice="adeola_yo", lang="yo")
audio.save("greeting.wav")
```

**Go**

```bash
# Run in your application directory. `go get` requires a Go module.
go mod init example.com/my-9jalingo-app
go get github.com/9jaLingo/9jalingo-sdk/naijalingo-go
export NAIJALINGO_API_KEY="YOUR_API_KEY"
```

```go
client := naijalingo.NewClient(naijalingo.ClientOptions{})
audio, err := client.TTS.Generate(context.Background(), "Bawo ni!", naijalingo.GenerateOptions{
  Voice: "adeola_yo", Lang: "yo",
})
if err != nil { log.Fatal(err) }
os.WriteFile("greeting.wav", audio.Content, 0o644)
```

**Node.js**

```bash
npm install naijalingo
export NAIJALINGO_API_KEY="YOUR_API_KEY"
```

```ts
import { NaijaLingo } from "naijalingo";

const client = new NaijaLingo();
const audio = await client.tts.generate("Bawo ni!", {
  voice: "adeola_yo",
  lang: "yo",
});
await audio.save("greeting.wav");
```

## Speech-to-Text

STT audio must be available at a public HTTPS URL. Each request needs an API key
with the `stt` scope.

**Cold starts:** the speech engine scales down when idle and takes a few minutes to start. The
first request after a quiet period waits for it automatically (it returns once the transcript is
ready) instead of failing; you are only charged for the successful transcription. Long recordings
(over 40 seconds, up to 60 minutes) are split and transcribed automatically, so allow a few minutes
for long audio.

**Python**

```python
transcript = client.stt.transcribe(
    "https://cdn.example.com/pidgin-sample.wav",
    language="pcm",
)
print(transcript.text, transcript.language)
```

**Node.js**

```ts
const transcript = await client.stt.transcribe(
  "https://cdn.example.com/pidgin-sample.wav",
  { language: "pcm" },
);
console.log(transcript.text, transcript.language);
```

**Go**

```go
transcript, err := client.STT.Transcribe(ctx, "https://cdn.example.com/pidgin-sample.wav", naijalingo.TranscribeOptions{Language: "pcm"})
if err != nil { log.Fatal(err) }
fmt.Println(transcript.Text, transcript.Language)
```

## Links

- [Website](https://www.9jalingo.org)
- [API documentation](https://www.9jalingo.org/api-documentation)
- [PyPI](https://pypi.org/project/naijalingo/) · [npm](https://www.npmjs.com/package/naijalingo) · [pkg.go.dev](https://pkg.go.dev/github.com/9jaLingo/9jalingo-sdk/naijalingo-go)

Get an API key from the [dashboard](https://9jalingo.org/dashboard).

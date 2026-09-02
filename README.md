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

## Links

- [Website](https://www.9jalingo.org)
- [API documentation](https://www.9jalingo.org/api-documentation)
- [PyPI](https://pypi.org/project/naijalingo/) · [npm](https://www.npmjs.com/package/naijalingo) · [pkg.go.dev](https://pkg.go.dev/github.com/9jaLingo/9jalingo-sdk/naijalingo-go)

Get an API key from the [dashboard](https://9jalingo.org/dashboard).

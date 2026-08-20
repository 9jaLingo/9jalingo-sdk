# 9jaLingo Python SDK

<p align="center">
  <strong>🇳🇬 The Official Python SDK for <a href="https://www.9jalingo.org">9jaLingo</a> — AI-Powered Text-to-Speech for African Languages</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/naijalingo/"><img src="https://img.shields.io/pypi/v/naijalingo.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/naijalingo/"><img src="https://img.shields.io/pypi/pyversions/naijalingo.svg" alt="Python versions"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

---

**9jaLingo** is the first AI speech platform built specifically for **African languages**. This SDK provides a simple, Pythonic interface to the [9jaLingo TTS API](https://www.9jalingo.org), enabling developers to generate natural-sounding speech in **Hausa**, **Igbo**, **Yoruba**, and **Nigerian Pidgin** with over **240+ speaker voices**.

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
- 🐍 **Python 3.11+** — Modern Python with full type hints

---

## Installation

```bash
pip install naijalingo
```

## Quick Start

```python
from naijalingo import NaijaLingo

client = NaijaLingo(api_key="nl-...")

# voice/speaker = speaker ID · lang/language = language code
audio = client.tts.generate(
    "Bawo ni, I dey greet you!",
    voice="adeola_yo",
    lang="yo",
)
audio.save("greeting.wav")
```

Or set your API key as an environment variable:

```bash
export NAIJALINGO_API_KEY="nl-..."
```

```python
from naijalingo import NaijaLingo

client = NaijaLingo()  # picks up NAIJALINGO_API_KEY from env
audio = client.tts.generate("Sannu da zuwa!", speaker="aisha_ha", language="ha")
audio.save("output.wav")
```

> **Important:** For `generate` and `stream`:
> - `voice` / `speaker` = **speaker ID** (e.g. `ada_pcm`, `adaeze_ig`)
> - `lang` / `language` = **language code** (`ha`, `ig`, `yo`, `pcm`)
>
> Do **not** pass language codes as `voice`. Use `list_speakers(language="pcm")`
> to discover speaker IDs. Voice cloning is different: `clone(..., voice="ig")`
> still takes a language code (sent as API `lang`).

---

## API Reference

### Text-to-Speech

```python
from naijalingo import NaijaLingo

client = NaijaLingo(api_key="nl-...")

# Basic generation (returns WAV) — voice/speaker = speaker ID, lang = language
audio = client.tts.generate("How you dey?", voice="ada_pcm", lang="pcm")
audio.save("output.wav")

# speaker= is an alias for voice= (takes precedence when both are set)
audio = client.tts.generate(
    "Nnoo, kedu ka i mere?",
    speaker="adaeze_ig",
    language="ig",
)
audio.save("adaeze_greeting.wav")

# Raw PCM format
audio = client.tts.generate(
    "Hello!", voice="ada_pcm", lang="pcm", response_format="pcm"
)
pcm_bytes = audio.content  # raw 16-bit signed LE, 22050 Hz mono

# Export directly to compressed formats like MP3 or FLAC
audio = client.tts.generate(
    "Make we test compressed audio.",
    voice="ada_pcm",
    lang="pcm",
    response_format="mp3",
)
audio.save("output.mp3")

# Adjust generation parameters
audio = client.tts.generate(
    "Na so life be sometimes.",
    voice="ada_pcm",
    lang="pcm",
    temperature=0.8,
    top_p=0.9,
    repetition_penalty=1.2,
)
```

### Streaming

For long texts, stream audio chunks as they're generated:

```python
# Stream to a file
with open("long_speech.wav", "wb") as f:
    for chunk in client.tts.stream(
        "Very long text here...", speaker="ada_pcm", lang="pcm"
    ):
        f.write(chunk)

# Or collect the full stream
long_text = """
        Life na one kind journey wey nobody fit fully understand. From the day person open eye for this world, the journey don start.
        Some people go say life na race, some go say na school, others go talk say na battle. But the truth be say life na mixture of many things together. E get sweet time, e get bitter time, e get time wey everything go dey move smooth like fresh engine, and e get time wey everywhere go just scatter like market wey rain beat.
        """
stream = client.tts.stream(long_text, lang="pcm", speaker="ada_pcm")
audio = stream.collect()
audio.save("long_speech.wav")
```

### Voice Cloning

Clone a voice from a reference audio file. Here `voice` is a **language code**
(`ha` / `ig` / `yo` / `pcm`), not a speaker ID:

```python
audio = client.tts.clone(
    "Kedu ka i mere?",
    audio_file="reference_voice.mp3", # Natively supports MP3, M4A, FLAC, OGG, etc.
    voice="ig",
    response_format="mp3"
)
audio.save("cloned.mp3")

# Reuse the persisted clone as either voice or speaker.
audio = client.tts.generate(
    "Nnoo, kedu ka i mere?",
    voice=audio.voice_id,
)
audio.save("cloned_voice_greeting.wav")

# Permanently delete the cloned voice when consent is withdrawn.
client.tts.delete_voice(audio.voice_id)

# From a file-like object
with open("reference.wav", "rb") as f:
    audio = client.tts.clone("Hello!", audio_file=f, voice="pcm")
```

### Speakers

```python
# List all speakers
speakers = client.tts.list_speakers()
for s in speakers:
    print(f"{s.id} — {s.language} ({s.gender})")

# Filter by language code
yoruba_speakers = client.tts.list_speakers(language="yo")

# Get a specific speaker
speaker = client.tts.get_speaker("ada_pcm")
print(speaker.name, speaker.language)
```

### Languages

```python
langs = client.tts.list_languages()
for lang in langs.languages:
    print(f"{lang.code}: {lang.name}")
# ha: Hausa
# ig: Igbo
# yo: Yoruba
# pcm: Pidgin
```

### Models

```python
models = client.list_models()
for model in models:
    print(f"{model.id} — owned by {model.owned_by}")
```

### API Info

```python
# Get root API information
info = client.api_info()
print(info.name)        # "9jaLingo TTS API"
print(info.version)     # "1.0.0"
print(info.endpoints)   # dict of all available endpoints

# Get v1 service metadata
service = client.service_info()
print(service.name)             # "9jaLingo API v1"
print(service.speech_url)       # "/v1/audio/speech"
print(service.models_url)       # "/v1/models"
```

### Health Check

```python
status = client.tts.health()
print(status.status)            # "healthy"
print(status.speakers_loaded)   # 240
```

---

## Supported Languages

Language codes (`ha`, `ig`, `yo`, `pcm`) are used to **filter speakers** and for
**voice cloning**. They are **not** valid `voice` values for `generate` / `stream`.

| Code  | Language        | Description | Example speakers |
|-------|-----------------|-------------|------------------|
| `ha`  | Hausa           | Widely spoken across Northern Nigeria and West Africa | `aisha_ha`, `bello_ha` |
| `ig`  | Igbo            | Native to southeastern Nigeria | `adaeze_ig`, `ifeanyi_ig` |
| `yo`  | Yoruba          | Spoken across southwestern Nigeria and Benin | `adeola_yo`, `adekunle_yo` |
| `pcm` | Nigerian Pidgin | The most widely spoken lingua franca in Nigeria | `ada_pcm`, `blessing_pcm` |

---

## Error Handling

```python
from naijalingo import NaijaLingo, AuthenticationError, NotFoundError, ServerError

client = NaijaLingo(api_key="nl-...")

try:
    audio = client.tts.generate("Hello!", voice="nonexistent_speaker")
except AuthenticationError:
    print("Invalid API key")
except NotFoundError as e:
    print(f"Speaker not found: {e.message}")
except ServerError:
    print("Server error — try again later")
except ValueError as e:
    # Raised locally if you pass a language code as voice, e.g. voice="pcm"
    print(e)
```

---

## Configuration

| Parameter  | Environment Variable     | Default                      |
|------------|--------------------------|------------------------------|
| `api_key`  | `NAIJALINGO_API_KEY`     | —                            |
| `base_url` | `NAIJALINGO_BASE_URL`    | `https://api.9jalingo.org`   |
| `timeout`  | —                        | `120` seconds                |

---

## Context Manager

```python
with NaijaLingo(api_key="nl-...") as client:
    audio = client.tts.generate("Bawo ni!", voice="adeola_yo", lang="yo")
    audio.save("output.wav")
# Connection pool is automatically closed
```

---

## Links

- 🌐 **Website:** [www.9jalingo.org](https://www.9jalingo.org)
- 📚 **API Docs:** [www.9jalingo.org/api-documentation](https://www.9jalingo.org/api-documentation)
- 💬 **Support:** [support@9jalingo.org](mailto:support@9jalingo.org)

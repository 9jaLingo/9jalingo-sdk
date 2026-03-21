# 9jaLingo Python SDK

<p align="center">
  <strong>🇳🇬 The Official Python SDK for <a href="https://www.9jalingo.org">9jaLingo</a> — AI-Powered Text-to-Speech for Nigerian Languages</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/naijalingo/"><img src="https://img.shields.io/pypi/v/naijalingo.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/naijalingo/"><img src="https://img.shields.io/pypi/pyversions/naijalingo.svg" alt="Python versions"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

---

**9jaLingo** is the first AI speech platform built specifically for **Nigerian languages**. This SDK provides a simple, Pythonic interface to the [9jaLingo TTS API](https://www.9jalingo.org), enabling developers to generate natural-sounding speech in **Hausa**, **Igbo**, **Yoruba**, and **Nigerian Pidgin** with over **240+ speaker voices**.

[![Watch the video](https://img.youtube.com/vi/Ib8WVXiwPlU/maxresdefault.jpg)](https://youtu.be/Ib8WVXiwPlU)

Whether you're building voice assistants, accessibility tools, e-learning platforms, audiobook generators, or any application that needs high-quality Nigerian language speech synthesis — 9jaLingo has you covered.

### Key Features

- 🗣️ **Text-to-Speech** — Convert text to natural speech in 4 Nigerian languages
- 🎭 **240+ Speaker Voices** — Choose from a diverse library of male and female voices
- 🔊 **Voice Cloning** — Clone any voice from a short reference audio sample
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

# Generate speech
audio = client.tts.generate("Bawo ni, I dey greet you!", voice="yo")
audio.save("greeting.wav")
```

Or set your API key as an environment variable:

```bash
export NAIJALINGO_API_KEY="nl-..."
```

```python
from naijalingo import NaijaLingo

client = NaijaLingo()  # picks up NAIJALINGO_API_KEY from env
audio = client.tts.generate("Sannu da zuwa!", voice="ha")
audio.save("output.wav")
```

---

## API Reference

### Text-to-Speech

```python
from naijalingo import NaijaLingo

client = NaijaLingo(api_key="nl-...")

# Basic generation (returns WAV)
audio = client.tts.generate("How you dey?", voice="pcm")
audio.save("output.wav")

# With a specific speaker voice
audio = client.tts.generate(
    "Nnoo, kedu ka i mere?",
    voice="ig",
    speaker="adaeze_ig",
)
audio.save("adaeze_greeting.wav")

# Raw PCM format
audio = client.tts.generate("Hello!", voice="pcm", response_format="pcm")
pcm_bytes = audio.content  # raw 16-bit signed LE, 22050 Hz mono

# Adjust generation parameters
audio = client.tts.generate(
    "Na so life be sometimes.",
    voice="pcm",
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
    for chunk in client.tts.stream("Very long text here...", voice="pcm"):
        f.write(chunk)

# Or collect the full stream
long_text="""
        Life na one kind journey wey nobody fit fully understand. From the day person open eye for this world, the journey don start. 
        Some people go say life na race, some go say na school, others go talk say na battle. But the truth be say life na mixture of many things together. E get sweet time, e get bitter time, e get time wey everything go dey move smooth like fresh engine, and e get time wey everywhere go just scatter like market wey rain beat.
        """
stream = client.tts.stream(long_text, voice="pcm", speaker="ada_pcm")
audio = stream.collect()
audio.save("long_speech.wav")
```

### Voice Cloning

Clone a voice from a reference audio file:

```python
audio = client.tts.clone(
    "Kedu ka i mere?",
    audio_file="reference_voice.wav",
    voice="ig",
)
audio.save("cloned.wav")

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

# Filter by language
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

| Code  | Language        | Description |
|-------|-----------------|-------------|
| `ha`  | Hausa           | Widely spoken across Northern Nigeria and West Africa |
| `ig`  | Igbo            | Native to southeastern Nigeria |
| `yo`  | Yoruba          | Spoken across southwestern Nigeria and Benin |
| `pcm` | Nigerian Pidgin | The most widely spoken lingua franca in Nigeria |

---

## Error Handling

```python
from naijalingo import NaijaLingo, AuthenticationError, NotFoundError, ServerError

client = NaijaLingo(api_key="nl-...")

try:
    audio = client.tts.generate("Hello!", speaker="nonexistent_speaker")
except AuthenticationError:
    print("Invalid API key")
except NotFoundError as e:
    print(f"Speaker not found: {e.message}")
except ServerError:
    print("Server error — try again later")
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
    audio = client.tts.generate("Bawo ni!", voice="yo")
    audio.save("output.wav")
# Connection pool is automatically closed
```
---

## Links

- 🌐 **Website:** [www.9jalingo.org](https://www.9jalingo.org)
- 📖 **Documentation:** [docs.9jalingo.org](https://docs.9jalingo.org)
- 🐛 **Issues:** [GitHub Issues](https://github.com/9jaLingo/naijalingo-python/issues)
- 📦 **PyPI:** [pypi.org/project/naijalingo](https://pypi.org/project/naijalingo/)



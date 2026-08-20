# 9jaLingo Node.js SDK

<p align="center">
  <strong>The Official Node.js SDK for <a href="https://www.9jalingo.org">9jaLingo</a> — AI-Powered Text-to-Speech for Nigerian Languages</strong>
</p>

<p align="center">
  <a href="https://www.npmjs.com/package/naijalingo"><img src="https://img.shields.io/npm/v/naijalingo.svg" alt="npm version"></a>
  <a href="https://www.npmjs.com/package/naijalingo"><img src="https://img.shields.io/node/v/naijalingo.svg" alt="Node version"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

---

**9jaLingo** is a Voice AI speech platform built specifically for **African languages**. This SDK provides a simple TypeScript/JavaScript interface to the [9jaLingo TTS API](https://www.9jalingo.org), enabling developers to generate natural-sounding speech in **Hausa**, **Igbo**, **Yoruba**, and **Nigerian Pidgin** with over **240+ speaker voices**.

### Key Features

- **Text-to-Speech** — Convert text to natural speech in 4 Nigerian languages
- **240+ Speaker Voices** — Choose from a diverse library of male and female voices
- **Voice Cloning** — Clone any voice from a short reference audio sample
- **Multi-Format Output** — WAV, PCM, MP3, FLAC, AAC, ALAC, or OGG
- **Streaming** — Stream audio chunks as they're generated
- **Long-Form Generation** — Automatic chunking for long texts
- **OpenAI-Compatible** — Familiar TTS-style API surface
- **Node.js 18+** — Native `fetch`, TypeScript types included

---

## Installation

```bash
npm install naijalingo
```

Requires **Node.js 18+**.

## Quick Start

```bash
# 1) Copy your real key from https://9jalingo.org/dashboard
# 2) Replace YOUR_API_KEY (do not leave this as-is)
export NAIJALINGO_API_KEY="YOUR_API_KEY"
```

```ts
import { NaijaLingo } from "naijalingo";

const client = new NaijaLingo(); // picks up NAIJALINGO_API_KEY

// voice/speaker = speaker ID · lang/language = language code
const audio = await client.tts.generate("Bawo ni, I dey greet you!", {
  voice: "adeola_yo",
  lang: "yo",
});
await audio.save("greeting.wav");
```

Or pass the key explicitly:

```ts
const client = new NaijaLingo({ apiKey: "YOUR_API_KEY" });
```

> **Important:** For `generate` and `stream`:
> - `voice` / `speaker` = **speaker ID** (e.g. `ada_pcm`, `adaeze_ig`)
> - `lang` / `language` = **language code** (`ha`, `ig`, `yo`, `pcm`)
>
> Do **not** pass language codes as `voice`. Use `listSpeakers({ language: "pcm" })`
> to discover speaker IDs. Voice cloning is different: `clone(..., { voice: "ig" })`
> still takes a language code (sent as API `lang`).

---

## API Reference

### Text-to-Speech

```ts
import { NaijaLingo } from "naijalingo";

const client = new NaijaLingo();

const audio = await client.tts.generate("How you dey?", {
  voice: "ada_pcm",
  lang: "pcm",
});
await audio.save("output.wav");

// speaker= / language= aliases
const igbo = await client.tts.generate("Nnoo, kedu ka i mere?", {
  speaker: "adaeze_ig",
  language: "ig",
});
await igbo.save("adaeze_greeting.wav");

// Export to MP3
const mp3 = await client.tts.generate("Make we test compressed audio.", {
  voice: "ada_pcm",
  lang: "pcm",
  responseFormat: "mp3",
});
await mp3.save("output.mp3");

// Fine-tune generation parameters
const tuned = await client.tts.generate("Na so life be sometimes.", {
  voice: "ada_pcm",
  lang: "pcm",
  temperature: 0.8,
  topP: 0.9,
  repetitionPenalty: 1.2,
});
```

### Streaming

```ts
import { createWriteStream } from "node:fs";

const stream = client.tts.stream("Very long text here...", {
  speaker: "ada_pcm",
  lang: "pcm",
});

const writer = createWriteStream("long_speech.wav");
for await (const chunk of stream) {
  writer.write(chunk);
}
writer.end();

// Or collect the full stream
const audio = await client.tts
  .stream(longText, { lang: "pcm", speaker: "ada_pcm" })
  .collect();
await audio.save("long_speech.wav");
```

### Voice Cloning

```ts
const audio = await client.tts.clone(
  "Kedu ka i mere?",
  "reference_voice.mp3",
  { voice: "ig", responseFormat: "mp3" },
);
await audio.save("cloned.mp3");

// The backend persists the clone and returns a reusable voice ID.
const greeting = await client.tts.generate("Nnoo, kedu ka i mere?", {
  voice: audio.voiceId,
});
await greeting.save("cloned_voice_greeting.wav");

// `speaker: audio.voiceId` is equivalent.

// Permanently delete the cloned voice when consent is withdrawn.
await client.tts.deleteVoice(audio.voiceId);

// From a Buffer
import { readFileSync } from "node:fs";
const buf = readFileSync("reference.wav");
const cloned = await client.tts.clone("Hello!", buf, { voice: "pcm" });
```

### Speakers

```ts
const speakers = await client.tts.listSpeakers();
for (const s of speakers) {
  console.log(`${s.id} — ${s.language} (${s.gender})`);
}

const yoruba = await client.tts.listSpeakers({ language: "yo" });
const speaker = await client.tts.getSpeaker("ada_pcm");
console.log(speaker.name, speaker.language);
```

### Languages

```ts
const langs = await client.tts.listLanguages();
for (const lang of langs.languages) {
  console.log(`${lang.code}: ${lang.name}`);
}
```

### Models

```ts
const models = await client.listModels();
for (const model of models) {
  console.log(`${model.id} — owned by ${model.ownedBy}`);
}
```

### API Info & Health

```ts
const info = await client.apiInfo();
console.log(info.name, info.version);

const service = await client.serviceInfo();
console.log(service.speechUrl);

const status = await client.tts.health();
console.log(status.status, status.totalSpeakers);
```

---

## Error Handling

```ts
import {
  NaijaLingo,
  AuthenticationError,
  NotFoundError,
  ServerError,
} from "naijalingo";

const client = new NaijaLingo();

try {
  await client.tts.generate("Hello!", { voice: "nonexistent_speaker" });
} catch (err) {
  if (err instanceof AuthenticationError) {
    console.error("Invalid API key");
  } else if (err instanceof NotFoundError) {
    console.error("Speaker not found:", err.message);
  } else if (err instanceof ServerError) {
    console.error("Server error — try again later");
  } else if (err instanceof Error) {
    // e.g. language code passed as voice
    console.error(err.message);
  }
}
```

---

## Configuration

| Option / Env | Environment Variable | Default |
|---|---|---|
| `apiKey` | `NAIJALINGO_API_KEY` | — |
| `baseUrl` | `NAIJALINGO_BASE_URL` | `https://api.9jalingo.org` |
| `timeout` | — | `300000` ms |

```ts
const client = new NaijaLingo({
  apiKey: "YOUR_API_KEY",
  baseUrl: "https://api.9jalingo.org",
  timeout: 300_000,
});
```

---

## Supported Languages

| Code | Language | Example speakers |
|------|----------|------------------|
| `ha` | Hausa | `aisha_ha`, `bello_ha` |
| `ig` | Igbo | `adaeze_ig`, `ifeanyi_ig` |
| `yo` | Yoruba | `adeola_yo`, `adekunle_yo` |
| `pcm` | Nigerian Pidgin | `ada_pcm`, `blessing_pcm` |

---

## Links

- **Website:** [www.9jalingo.org](https://www.9jalingo.org)
- **API Docs:** [www.9jalingo.org/api-documentation](https://www.9jalingo.org/api-documentation)
- **Python SDK:** [`pip install naijalingo`](https://pypi.org/project/naijalingo/)
- **Support:** [support@9jalingo.org](mailto:support@9jalingo.org)

## License

MIT

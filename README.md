# 9jaLingo SDKs

Official client libraries for the [9jaLingo](https://www.9jalingo.org) API — Text-to-Speech and Voice Cloning for Hausa, Igbo, Yoruba, and Nigerian Pidgin.

| SDK | Directory | Install |
|-----|-----------|---------|
| **Python** | [`python-naijalingo/`](python-naijalingo/) | `pip install naijalingo` |
| **Node.js** | [`naijalingo-js/`](naijalingo-js/) | `npm install naijalingo` |

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
- [PyPI](https://pypi.org/project/naijalingo/) · [npm](https://www.npmjs.com/package/naijalingo)

Get an API key from the [dashboard](https://9jalingo.org/dashboard).

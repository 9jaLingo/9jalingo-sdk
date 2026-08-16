import assert from "node:assert/strict";
import test from "node:test";

import { NaijaLingo } from "../dist/index.js";

test("clone returns reusable voice metadata", async () => {
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (url, init) => {
    requests.push({ url, init });
    if (new URL(url).pathname === "/v1/audio/clone") {
      return new Response("RIFFcloned", {
        headers: {
          "Content-Type": "audio/wav",
          "X-Voice-ID": "voice-uuid-123",
          "X-Voice-Code": "my-cloned-voice",
          "X-Voice-Name": "My Cloned Voice",
          "X-Clone-ID": "clone-uuid-456",
          "X-Job-ID": "job-uuid-789",
        },
      });
    }
    return new Response("RIFFgenerated", {
      headers: { "Content-Type": "audio/wav" },
    });
  };

  try {
    const client = new NaijaLingo({ baseUrl: "https://api.test" });
    const clone = await client.tts.clone(
      "Hello from my clone",
      new Uint8Array([1, 2, 3]),
      { voice: "pcm" },
    );

    assert.equal(new TextDecoder().decode(clone.content), "RIFFcloned");
    assert.equal(clone.voiceId, "voice-uuid-123");
    assert.equal(clone.voiceCode, "my-cloned-voice");
    assert.equal(clone.voiceName, "My Cloned Voice");
    assert.equal(clone.cloneId, "clone-uuid-456");
    assert.equal(clone.jobId, "job-uuid-789");

    await client.tts.generate("Use cloned voice", { voice: clone.voiceId });
    await client.tts.generate("Use cloned speaker", { speaker: clone.voiceId });

    const generationRequests = requests.filter(
      ({ url }) => new URL(url).pathname === "/v1/audio/speech",
    );
    assert.equal(generationRequests.length, 2);
    for (const request of generationRequests) {
      assert.equal(JSON.parse(request.init.body).voice, "voice-uuid-123");
    }
  } finally {
    globalThis.fetch = originalFetch;
  }
});
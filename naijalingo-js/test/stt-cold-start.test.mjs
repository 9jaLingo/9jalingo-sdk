import assert from "node:assert/strict";
import test from "node:test";

import {
  InferenceCapacityError,
  NaijaLingo,
  NotFoundError,
  ServerError,
} from "../dist/index.js";

const OK = { status: "success", result: { text: "how we dey", language: "pcm_Latn", duration: 1.5 } };
const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const queued = (jobId = "job-1") =>
  json({ status: "queued", job_id: jobId, retry_after: 5, warming: true }, 202);

async function withFetch(handler, run, options = {}) {
  const original = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (url, init) => {
    requests.push({ url: new URL(url), init });
    return handler(new URL(url), init, requests);
  };
  try {
    const client = new NaijaLingo({ baseUrl: "https://api.test", apiKey: "k", coldStartPollIntervalMs: 5, ...options });
    return await run(client, requests);
  } finally {
    globalThis.fetch = original;
  }
}

test("warm engine answers directly and the request opts in to async", async () => {
  await withFetch(
    () => json(OK),
    async (client, requests) => {
      const t = await client.stt.transcribe("https://audio.example/a.wav", { language: "pcm" });
      assert.equal(t.text, "how we dey");
      assert.equal(t.language, "pcm_Latn");
      assert.equal(requests.length, 1);
      assert.equal(requests[0].init.headers.Prefer, "respond-async-on-cold-start");
    },
  );
});

test("cold start waits for the queued job and returns the transcript", async () => {
  const states = ["queued", "running", "completed"];
  await withFetch(
    (url, init) => {
      if (init.method === "POST") return queued("job/unsafe");
      const state = states.shift();
      return json({ status: state, warming: state !== "completed", retry_after: 5, ...(state === "completed" ? { response: OK } : {}) });
    },
    async (client, requests) => {
      const t = await client.stt.transcribe("https://audio.example/a.wav");
      assert.equal(t.text, "how we dey");
      assert.deepEqual(
        requests.map((r) => r.url.pathname + r.url.search),
        [
          "/v1/audio/transcriptions",
          "/v1/audio/transcriptions/jobs/job%2Funsafe", // job id is URL-encoded
          "/v1/audio/transcriptions/jobs/job%2Funsafe",
          "/v1/audio/transcriptions/jobs/job%2Funsafe",
        ],
      );
      assert.equal(requests[1].init.headers["X-API-Key"], "k");
    },
  );
});

test("failed job raises with the server message", async () => {
  await withFetch(
    (url, init) => (init.method === "POST" ? queued() : json({ status: "failed", error: "Unsupported audio format." })),
    async (client) => {
      await assert.rejects(client.stt.transcribe("https://audio.example/a.wav"), (e) => {
        assert.ok(e instanceof ServerError);
        assert.match(e.message, /Unsupported audio format/);
        return true;
      });
    },
  );
});

test("an engine that never started raises a capacity error", async () => {
  const message = "The speech engine did not start in time. You were not charged. Please try again.";
  await withFetch(
    (url, init) => (init.method === "POST" ? queued() : json({ status: "failed", error: message })),
    async (client) => {
      await assert.rejects(client.stt.transcribe("https://audio.example/a.wav"), (e) => {
        assert.ok(e instanceof InferenceCapacityError);
        assert.match(e.message, /not charged/);
        return true;
      });
    },
  );
});

test("unknown status, missing result and malformed queue responses are rejected", async () => {
  await withFetch(
    (url, init) => (init.method === "POST" ? queued() : json({ status: "weird" })),
    async (client) => {
      await assert.rejects(client.stt.transcribe("https://audio.example/a.wav"), /unknown status/);
    },
  );
  await withFetch(
    (url, init) => (init.method === "POST" ? queued() : json({ status: "completed" })),
    async (client) => {
      await assert.rejects(client.stt.transcribe("https://audio.example/a.wav"), /did not include a result/);
    },
  );
  for (const body of [{ status: "success" }, { status: "queued" }, ["x"]]) {
    await withFetch(
      () => json(body, 202),
      async (client) => {
        await assert.rejects(client.stt.transcribe("https://audio.example/a.wav"), ServerError);
      },
    );
  }
});

test("a brief gateway error while polling does not abandon the job", async () => {
  let polls = 0;
  await withFetch(
    (url, init) => {
      if (init.method === "POST") return queued();
      polls += 1;
      if (polls <= 2) return json({ detail: "bad gateway" }, 502);
      return json({ status: "completed", response: OK });
    },
    async (client) => {
      assert.equal((await client.stt.transcribe("https://audio.example/a.wav")).text, "how we dey");
    },
  );
});

test("persistent polling failure eventually gives up", async () => {
  await withFetch(
    (url, init) => (init.method === "POST" ? queued() : json({ detail: "bad gateway" }, 502)),
    async (client, requests) => {
      await assert.rejects(client.stt.transcribe("https://audio.example/a.wav"), ServerError);
      assert.equal(requests.filter((r) => r.init.method === "GET").length, 5);
    },
  );
});

test("an expired job is reported as not found", async () => {
  await withFetch(
    (url, init) => (init.method === "POST" ? queued() : json({ detail: "Transcription job not found or expired" }, 404)),
    async (client) => {
      await assert.rejects(client.stt.transcribe("https://audio.example/a.wav"), NotFoundError);
    },
  );
});

test("gives up after the overall deadline", async () => {
  await withFetch(
    (url, init) => (init.method === "POST" ? queued() : json({ status: "running" })),
    async (client) => {
      await assert.rejects(client.stt.transcribe("https://audio.example/a.wav"), (e) => {
        assert.ok(e instanceof InferenceCapacityError);
        assert.match(e.message, /did not finish in time/);
        return true;
      });
    },
    { coldStartMaxWaitMs: 60 },
  );
});

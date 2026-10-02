import {
  AuthenticationError,
  ConnectionError,
  InferenceCapacityError,
  InvalidRequestError,
  NaijaLingoError,
  NotFoundError,
  RateLimitError,
  ServerError,
} from "./errors.js";

const DEFAULT_BASE_URL = "https://api.9jalingo.org";
const DEFAULT_TIMEOUT_MS = 300_000;
// While a speech engine starts from zero the API queues the request. Wait at most this long
// (the server itself gives up after 20 minutes, then a long file still needs time to process).
const COLD_START_MAX_WAIT_MS = 40 * 60_000;
const COLD_START_MAX_POLL_FAILURES = 5;

export interface ClientOptions {
  apiKey?: string;
  baseUrl?: string;
  /** Request timeout in milliseconds (default 300000). */
  timeout?: number;
  /** @internal Fixed pause between cold-start status checks (default: the server's retry_after). */
  coldStartPollIntervalMs?: number;
  /** @internal Longest total wait for a queued cold-start job (default 40 minutes). */
  coldStartMaxWaitMs?: number;
}

export class BaseClient {
  readonly apiKey: string;
  readonly baseUrl: string;
  readonly timeout: number;
  private readonly coldStartPollIntervalMs?: number;
  private readonly coldStartMaxWaitMs: number;
  private readonly defaultHeaders: Record<string, string>;

  constructor(options: ClientOptions = {}) {
    this.apiKey =
      options.apiKey ?? process.env.NAIJALINGO_API_KEY ?? "";
    const base =
      options.baseUrl ??
      process.env.NAIJALINGO_BASE_URL ??
      DEFAULT_BASE_URL;
    this.baseUrl = base.replace(/\/+$/, "");
    this.timeout = options.timeout ?? DEFAULT_TIMEOUT_MS;
    this.coldStartPollIntervalMs = options.coldStartPollIntervalMs;
    this.coldStartMaxWaitMs = options.coldStartMaxWaitMs ?? COLD_START_MAX_WAIT_MS;

    this.defaultHeaders = {
      "User-Agent": "naijalingo-js/0.3.0",
    };
    if (this.apiKey) {
      this.defaultHeaders["X-API-Key"] = this.apiKey;
    }
  }

  private async request(
    method: string,
    path: string,
    init: RequestInit & { timeoutMs?: number } = {},
  ): Promise<Response> {
    const url = `${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    const timeoutMs = init.timeoutMs ?? this.timeout;
    let lastError: unknown;

    for (let attempt = 0; attempt < 3; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const response = await fetch(url, {
          ...init,
          method,
          headers: {
            ...this.defaultHeaders,
            ...(init.headers as Record<string, string> | undefined),
          },
          signal: controller.signal,
        });
        clearTimeout(timer);

        if (response.ok) {
          return response;
        }
        await this.raiseForStatus(response);
        // unreachable
        return response;
      } catch (err) {
        clearTimeout(timer);
        if (err instanceof NaijaLingoError) {
          throw err;
        }
        lastError = err;
        const isAbort =
          err instanceof Error &&
          (err.name === "AbortError" || err.name === "TimeoutError");
        // Only retry connect-style failures, not aborts from long reads
        if (isAbort) {
          throw new ConnectionError(
            `Request timed out after ${timeoutMs}ms: ${String(err)}`,
          );
        }
        if (attempt < 2) {
          await sleep(1500);
          continue;
        }
      }
    }

    throw new ConnectionError(
      `Unable to connect to ${this.baseUrl}: ${String(lastError)}`,
    );
  }

  private async raiseForStatus(response: Response): Promise<never> {
    const status = response.status;
    let detail: string;
    let body: unknown;
    try {
      body = await response.json();
      detail =
        typeof body === "object" &&
        body !== null &&
        "detail" in body
          ? String((body as { detail: unknown }).detail)
          : JSON.stringify(body);
    } catch {
      detail = await response.text();
    }

    const normalizedDetail = detail.toLowerCase();
    if (status === 503 && (
      normalizedDetail.includes("inference capacity")
      || normalizedDetail.includes("inference component has no capacity")
      || normalizedDetail.includes("capacity is starting")
    )) {
      throw new InferenceCapacityError(detail, status, body);
    }
    if (status === 401 || status === 403) {
      throw new AuthenticationError(detail, status, body);
    }
    if (status === 404) {
      throw new NotFoundError(detail, status, body);
    }
    if ([400, 413, 415, 422].includes(status)) {
      throw new InvalidRequestError(detail, status, body);
    }
    if (status === 429) {
      throw new RateLimitError(detail, status, body);
    }
    if (status >= 500) {
      throw new ServerError(detail, status, body);
    }
    throw new NaijaLingoError(detail, status, body);
  }

  async getJson(
    path: string,
    params?: Record<string, string | undefined | null>,
  ): Promise<Record<string, unknown>> {
    let url = path;
    if (params) {
      const qs = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        if (v != null) qs.set(k, v);
      }
      const s = qs.toString();
      if (s) url = `${path}?${s}`;
    }
    const resp = await this.request("GET", url);
    return (await resp.json()) as Record<string, unknown>;
  }

  async postBytes(
    path: string,
    body: Record<string, unknown>,
  ): Promise<Uint8Array> {
    const resp = await this.request("POST", path, {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return new Uint8Array(await resp.arrayBuffer());
  }

  async postJson(path: string, body: Record<string, unknown>): Promise<Record<string, unknown>> {
    const resp = await this.request("POST", path, {
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return (await resp.json()) as Record<string, unknown>;
  }

  /**
   * POST JSON and, if the engine is starting up, transparently wait for the queued job.
   *
   * Sends `Prefer: respond-async-on-cold-start`. A warm engine answers 200 directly (identical to
   * {@link postJson}). When the engine was scaled to zero the server answers 202 with a `job_id`;
   * this polls `jobPath(jobId)` until the job completes and returns the final response body.
   * Servers that do not know the header simply ignore it.
   */
  async postJsonWaitingForColdStart(
    path: string,
    body: Record<string, unknown>,
    options: { jobPath: (jobId: string) => string; label: string },
  ): Promise<Record<string, unknown>> {
    const { jobPath, label } = options;
    const resp = await this.request("POST", path, {
      headers: {
        "Content-Type": "application/json",
        Prefer: "respond-async-on-cold-start",
      },
      body: JSON.stringify(body),
    });
    if (resp.status !== 202) {
      return (await resp.json()) as Record<string, unknown>;
    }

    const invalid = `The API returned an invalid queued ${label} response.`;
    let queued: unknown;
    try {
      queued = await resp.json();
    } catch {
      throw new ServerError(invalid, 202);
    }
    if (typeof queued !== "object" || queued === null || (queued as Record<string, unknown>).status !== "queued") {
      throw new ServerError(invalid, 202, queued);
    }
    const queuedBody = queued as Record<string, unknown>;
    const jobId = String(queuedBody.job_id ?? "").trim();
    if (!jobId) {
      throw new ServerError(`The queued ${label} response did not include a job ID.`, 202, queued);
    }

    const statusPath = jobPath(jobId);
    const deadline = Date.now() + this.coldStartMaxWaitMs;
    let statusBody: Record<string, unknown> = queuedBody;
    let transientFailures = 0;

    while (Date.now() < deadline) {
      const retryAfter = Number(statusBody.retry_after ?? queuedBody.retry_after ?? 5);
      const delayMs =
        this.coldStartPollIntervalMs ??
        Math.max(1000, Math.min(Number.isFinite(retryAfter) ? retryAfter * 1000 : 5000, 30_000));
      await sleep(delayMs);

      try {
        statusBody = await this.getJson(statusPath);
        transientFailures = 0;
      } catch (err) {
        // A brief network or gateway problem must not abandon a job that is still running.
        if (err instanceof ConnectionError || err instanceof ServerError) {
          transientFailures += 1;
          if (transientFailures >= COLD_START_MAX_POLL_FAILURES) throw err;
          continue;
        }
        throw err;
      }

      if (typeof statusBody !== "object" || statusBody === null) {
        throw new ServerError(`The queued ${label} job returned an invalid status.`, 502);
      }
      const state = String(statusBody.status ?? "").toLowerCase();
      if (state === "completed") {
        const final = statusBody.response;
        if (typeof final !== "object" || final === null || Array.isArray(final)) {
          throw new ServerError(`The completed ${label} job did not include a result.`, 502, statusBody);
        }
        return final as Record<string, unknown>;
      }
      if (state === "failed") {
        const message = String(statusBody.error ?? `Queued ${label} job failed.`);
        if (message.toLowerCase().includes("did not start in time")) {
          throw new InferenceCapacityError(message, 503, statusBody);
        }
        throw new ServerError(message, 502, statusBody);
      }
      if (!["queued", "running", "processing"].includes(state)) {
        throw new ServerError(
          `The queued ${label} job returned an unknown status: ${state || "missing"}.`,
          502,
          statusBody,
        );
      }
    }

    throw new InferenceCapacityError(`Queued ${label} job did not finish in time.`, 504, statusBody);
  }

  async *postStream(
    path: string,
    body: Record<string, unknown>,
  ): AsyncGenerator<Uint8Array, void, unknown> {
    let lastError: unknown;
    for (let attempt = 0; attempt < 3; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), this.timeout);
      try {
        const response = await fetch(
          `${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`,
          {
            method: "POST",
            headers: {
              ...this.defaultHeaders,
              "Content-Type": "application/json",
            },
            body: JSON.stringify(body),
            signal: controller.signal,
          },
        );
        clearTimeout(timer);

        if (!response.ok) {
          await this.raiseForStatus(response);
        }
        if (!response.body) {
          throw new ConnectionError("No response body for stream");
        }

        const reader = response.body.getReader();
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            if (value && value.length > 0) {
              yield value;
            }
          }
        } finally {
          reader.releaseLock();
        }
        return;
      } catch (err) {
        clearTimeout(timer);
        if (err instanceof NaijaLingoError) throw err;
        lastError = err;
        const isAbort =
          err instanceof Error &&
          (err.name === "AbortError" || err.name === "TimeoutError");
        if (isAbort) {
          throw new ConnectionError(`Request timed out: ${String(err)}`);
        }
        if (attempt < 2) {
          await sleep(1500);
          continue;
        }
      }
    }
    throw new ConnectionError(
      `Unable to connect to ${this.baseUrl}: ${String(lastError)}`,
    );
  }

  async postMultipart(
    path: string,
    form: FormData,
    timeoutMs?: number,
  ): Promise<Response> {
    return this.request("POST", path, {
      body: form,
      timeoutMs: timeoutMs ?? Math.max(this.timeout, 600_000),
      // Let fetch set multipart boundary — do not set Content-Type
    });
  }

  async delete(path: string): Promise<void> {
    await this.request("DELETE", path);
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

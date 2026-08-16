import {
  AuthenticationError,
  ConnectionError,
  InferenceCapacityError,
  NaijaLingoError,
  NotFoundError,
  RateLimitError,
  ServerError,
} from "./errors.js";

const DEFAULT_BASE_URL = "https://api.9jalingo.org";
const DEFAULT_TIMEOUT_MS = 300_000;

export interface ClientOptions {
  apiKey?: string;
  baseUrl?: string;
  /** Request timeout in milliseconds (default 300000). */
  timeout?: number;
}

export class BaseClient {
  readonly apiKey: string;
  readonly baseUrl: string;
  readonly timeout: number;
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

    this.defaultHeaders = {
      "User-Agent": "naijalingo-js/0.1.2",
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
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

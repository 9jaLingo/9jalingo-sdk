import { BaseClient } from "./client.js";
import { ServerError } from "./errors.js";

export type TranscribeOptions = {
  language?: string;
};

export type Transcription = {
  text: string;
  language?: string;
  duration?: number;
  model?: string;
};

export class STT {
  constructor(private readonly client: BaseClient) {}

  /**
   * Transcribe audio hosted at a public HTTPS URL.
   *
   * `options.language`: `yo`, `ig`, `ha`, `pcm` or `en`. If the speech engine was idle it needs a few
   * minutes to start; this call then waits for the queued job instead of failing, and long
   * recordings (over 40 s) are split automatically.
   */
  async transcribe(fileUrl: string, options: TranscribeOptions = {}): Promise<Transcription> {
    const body: Record<string, unknown> = { file_url: fileUrl };
    if (options.language) body.language = options.language;
    let response: Record<string, unknown> = await this.client.postJsonWaitingForColdStart(
      "/v1/audio/transcriptions",
      body,
      { jobPath: (id) => `/v1/audio/transcriptions/jobs/${encodeURIComponent(id)}`, label: "STT" },
    );
    while (true) {
      if (response.error) {
        throw new ServerError(String(response.error), 502, response);
      }
      if (typeof response.result !== "object" || response.result === null || Array.isArray(response.result)) {
        break;
      }
      response = response.result as Record<string, unknown>;
    }
    if (typeof response.text !== "string") {
      throw new ServerError("The API returned an invalid transcription response.", 502, response);
    }
    return response as Transcription;
  }
}
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

  async transcribe(fileUrl: string, options: TranscribeOptions = {}): Promise<Transcription> {
    const body: Record<string, unknown> = { file_url: fileUrl };
    if (options.language) body.language = options.language;
    let response: Record<string, unknown> = await this.client.postJson("/v1/audio/transcriptions", body);
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
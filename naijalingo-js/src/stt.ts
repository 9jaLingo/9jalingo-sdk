import { BaseClient } from "./client.js";

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
    while (typeof response.result === "object" && response.result !== null && !Array.isArray(response.result)) {
      response = response.result as Record<string, unknown>;
    }
    return response as Transcription;
  }
}
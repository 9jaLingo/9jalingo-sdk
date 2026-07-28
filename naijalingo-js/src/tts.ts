import { mkdir, writeFile } from "node:fs/promises";
import { basename, dirname } from "node:path";
import { readFileSync } from "node:fs";
import { BaseClient } from "./client.js";
import {
  type HealthStatus,
  type LanguageList,
  type ResponseFormat,
  type Speaker,
  type SpeakerList,
  healthStatusFromDict,
  languageListFromDict,
  speakerFromDict,
  speakerListFromDict,
} from "./types.js";
import {
  resolveCloneLangAndSpeaker,
  resolveTtsVoiceAndLang,
} from "./voice.js";

const DEFAULT_MODEL_NAME = "9jalingo-tts-1";

export type GenerateOptions = {
  voice?: string;
  speaker?: string;
  lang?: string;
  language?: string;
  modelName?: string;
  speakerEmbedding?: number[];
  responseFormat?: ResponseFormat;
  temperature?: number;
  topP?: number;
  repetitionPenalty?: number;
  enableLongForm?: boolean;
  maxChunkDuration?: number;
  silenceDuration?: number;
};

export type StreamOptions = Omit<
  GenerateOptions,
  "modelName" | "responseFormat"
>;

export type CloneOptions = {
  voice?: string;
  lang?: string;
  speaker?: string;
  modelName?: string;
  temperature?: number;
  topP?: number;
  repetitionPenalty?: number;
  responseFormat?: ResponseFormat;
};

export type ListSpeakersOptions = {
  language?: string;
  gender?: string;
  domain?: string;
};

/** Audio data returned from a generation request. */
export class AudioResponse {
  readonly content: Uint8Array;
  readonly mediaType: string;

  constructor(content: Uint8Array, mediaType = "audio/wav") {
    this.content = content;
    this.mediaType = mediaType;
  }

  /** Write the audio to a file. */
  async save(path: string): Promise<string> {
    await mkdir(dirname(path), { recursive: true });
    await writeFile(path, this.content);
    return path;
  }

  get length(): number {
    return this.content.length;
  }

  toString(): string {
    return `AudioResponse(${this.content.length} bytes, ${this.mediaType})`;
  }
}

/** Streaming audio response — yields byte chunks as they arrive. */
export class AudioStream implements AsyncIterable<Uint8Array> {
  private readonly chunks: AsyncIterable<Uint8Array>;
  private collected: Uint8Array | null = null;

  constructor(chunks: AsyncIterable<Uint8Array>) {
    this.chunks = chunks;
  }

  async *[Symbol.asyncIterator](): AsyncIterator<Uint8Array> {
    for await (const chunk of this.chunks) {
      yield chunk;
    }
  }

  /** Consume the entire stream and return an AudioResponse. */
  async collect(): Promise<AudioResponse> {
    if (this.collected == null) {
      const parts: Uint8Array[] = [];
      let total = 0;
      for await (const chunk of this.chunks) {
        parts.push(chunk);
        total += chunk.length;
      }
      const out = new Uint8Array(total);
      let offset = 0;
      for (const part of parts) {
        out.set(part, offset);
        offset += part.length;
      }
      this.collected = out;
    }
    return new AudioResponse(this.collected, "audio/wav");
  }
}

export class TTS {
  private readonly client: BaseClient;

  constructor(client: BaseClient) {
    this.client = client;
  }

  /** Generate speech from text. */
  async generate(
    text: string,
    options: GenerateOptions = {},
  ): Promise<AudioResponse> {
    let [resolvedVoice, resolvedLang] = resolveTtsVoiceAndLang(options);
    if (resolvedVoice == null && options.speakerEmbedding == null) {
      resolvedVoice = "blessing_pcm";
    }
    const responseFormat = options.responseFormat ?? "wav";
    const body = buildBody({
      input: text,
      voice: resolvedVoice,
      lang: resolvedLang,
      model: options.modelName ?? DEFAULT_MODEL_NAME,
      speaker_embedding: options.speakerEmbedding,
      response_format: responseFormat,
      temperature: options.temperature,
      top_p: options.topP,
      repetition_penalty: options.repetitionPenalty,
      enable_long_form: options.enableLongForm ?? true,
      max_chunk_duration: options.maxChunkDuration,
      silence_duration: options.silenceDuration,
    });
    const content = await this.client.postBytes("/v1/audio/speech", body);
    const mediaType = MEDIA_TYPES[responseFormat] ?? "application/octet-stream";
    return new AudioResponse(content, mediaType);
  }

  /** Stream speech generation — audio arrives as it's produced. */
  stream(text: string, options: StreamOptions = {}): AudioStream {
    let [resolvedVoice, resolvedLang] = resolveTtsVoiceAndLang(options);
    if (resolvedVoice == null && options.speakerEmbedding == null) {
      resolvedVoice = "blessing_pcm";
    }
    const body = buildBody({
      input: text,
      voice: resolvedVoice,
      lang: resolvedLang,
      speaker_embedding: options.speakerEmbedding,
      response_format: "wav",
      temperature: options.temperature,
      top_p: options.topP,
      repetition_penalty: options.repetitionPenalty,
      enable_long_form: options.enableLongForm ?? true,
      max_chunk_duration: options.maxChunkDuration,
      silence_duration: options.silenceDuration,
    });
    return new AudioStream(this.client.postStream("/v1/audio/speech/stream", body));
  }

  /**
   * Generate speech using a cloned voice from a reference audio file.
   * `audioFile` may be a filesystem path, Buffer, Uint8Array, Blob, or File.
   */
  async clone(
    text: string,
    audioFile: string | Buffer | Uint8Array | Blob,
    options: CloneOptions = {},
  ): Promise<AudioResponse> {
    const voice = options.voice ?? "pcm";
    const [resolvedLang, resolvedSpeaker] = resolveCloneLangAndSpeaker(
      voice,
      { lang: options.lang, speaker: options.speaker },
    );
    const responseFormat = options.responseFormat ?? "wav";

    const form = new FormData();
    form.append("text", text);
    form.append("lang", resolvedLang);
    form.append("model_name", options.modelName ?? DEFAULT_MODEL_NAME);
    form.append("response_format", responseFormat);
    if (resolvedSpeaker) {
      form.append("voice", resolvedSpeaker);
    }
    if (options.temperature != null) {
      form.append("temperature", String(options.temperature));
    }
    if (options.topP != null) {
      form.append("top_p", String(options.topP));
    }
    if (options.repetitionPenalty != null) {
      form.append("repetition_penalty", String(options.repetitionPenalty));
    }

    const { blob, filename } = await toAudioBlob(audioFile);
    form.append("audio", blob, filename);

    const content = await this.client.postMultipart("/v1/audio/clone", form);
    const mediaType = MEDIA_TYPES[responseFormat] ?? "application/octet-stream";
    return new AudioResponse(content, mediaType);
  }

  async listSpeakers(
    options: ListSpeakersOptions = {},
  ): Promise<SpeakerList> {
    const data = await this.client.getJson("/v1/speakers", {
      language: options.language,
      gender: options.gender,
      domain: options.domain,
    });
    return speakerListFromDict(data);
  }

  async getSpeaker(speakerId: string): Promise<Speaker> {
    const data = await this.client.getJson(`/v1/speakers/${speakerId}`);
    return speakerFromDict(data);
  }

  async listLanguages(): Promise<LanguageList> {
    const data = await this.client.getJson("/v1/languages");
    return languageListFromDict(data);
  }

  async health(): Promise<HealthStatus> {
    const data = await this.client.getJson("/v1/health");
    return healthStatusFromDict(data);
  }
}

const MEDIA_TYPES: Record<string, string> = {
  wav: "audio/wav",
  pcm: "application/octet-stream",
  flac: "audio/flac",
  aac: "audio/aac",
  ogg: "audio/ogg",
  mp3: "audio/mpeg",
  alac: "audio/alac",
};

function buildBody(
  kwargs: Record<string, unknown>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(kwargs)) {
    if (v !== undefined && v !== null) out[k] = v;
  }
  return out;
}

async function toAudioBlob(
  audioFile: string | Buffer | Uint8Array | Blob,
): Promise<{ blob: Blob; filename: string }> {
  if (typeof audioFile === "string") {
    const bytes = readFileSync(audioFile);
    const filename = basename(audioFile);
    const mime = guessMime(filename);
    return {
      blob: new Blob([bytes], { type: mime }),
      filename,
    };
  }
  if (audioFile instanceof Blob) {
    return {
      blob: audioFile,
      filename: "audio.wav",
    };
  }
  // Buffer | Uint8Array
  const bytes =
    audioFile instanceof Uint8Array
      ? audioFile
      : new Uint8Array(audioFile);
  return {
    blob: new Blob([bytes], { type: "application/octet-stream" }),
    filename: "audio.wav",
  };
}

function guessMime(filename: string): string {
  const lower = filename.toLowerCase();
  if (lower.endsWith(".wav")) return "audio/wav";
  if (lower.endsWith(".mp3")) return "audio/mpeg";
  if (lower.endsWith(".flac")) return "audio/flac";
  if (lower.endsWith(".ogg")) return "audio/ogg";
  if (lower.endsWith(".aac") || lower.endsWith(".m4a")) return "audio/aac";
  return "application/octet-stream";
}

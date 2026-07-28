/**
 * 9jaLingo Node.js SDK
 *
 * Official SDK for the 9jaLingo API — Nigerian language Text-to-Speech.
 *
 * @example
 * ```ts
 * import { NaijaLingo } from "naijalingo";
 *
 * const client = new NaijaLingo(); // uses NAIJALINGO_API_KEY
 * const audio = await client.tts.generate("Bawo ni!", {
 *   voice: "adeola_yo",
 *   lang: "yo",
 * });
 * await audio.save("greeting.wav");
 * ```
 */

import { BaseClient, type ClientOptions } from "./client.js";
import { TTS } from "./tts.js";
import {
  apiInfoFromDict,
  modelListFromDict,
  serviceInfoFromDict,
  type APIInfo,
  type ModelList,
  type ServiceInfo,
} from "./types.js";

export const VERSION = "0.1.0";

export {
  AuthenticationError,
  ConnectionError,
  NaijaLingoError,
  NotFoundError,
  RateLimitError,
  ServerError,
} from "./errors.js";

export {
  AudioResponse,
  AudioStream,
  TTS,
  type CloneOptions,
  type GenerateOptions,
  type ListSpeakersOptions,
  type StreamOptions,
} from "./tts.js";

export type {
  APIInfo,
  HealthStatus,
  Language,
  LanguageList,
  Model,
  ModelList,
  ResponseFormat,
  ServiceInfo,
  Speaker,
  SpeakerList,
} from "./types.js";

export type { ClientOptions };

export class NaijaLingo {
  private readonly _client: BaseClient;
  readonly tts: TTS;

  constructor(options: ClientOptions = {}) {
    this._client = new BaseClient(options);
    this.tts = new TTS(this._client);
  }

  /** List available TTS models. GET /v1/models */
  async listModels(): Promise<ModelList> {
    const data = await this._client.getJson("/v1/models");
    return modelListFromDict(data);
  }

  /** Root API information. GET / */
  async apiInfo(): Promise<APIInfo> {
    const data = await this._client.getJson("/");
    return apiInfoFromDict(data);
  }

  /** v1 service metadata. GET /v1 */
  async serviceInfo(): Promise<ServiceInfo> {
    const data = await this._client.getJson("/v1");
    return serviceInfoFromDict(data);
  }
}

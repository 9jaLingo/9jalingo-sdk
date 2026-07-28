/** A speaker voice identity. */
export interface Speaker {
  id: string;
  name: string;
  language: string;
  gender?: string | null;
  domain?: string | null;
}

export function speakerFromDict(data: Record<string, unknown>): Speaker {
  return {
    id: String(data.id ?? data.speaker_id ?? ""),
    name: String(data.name ?? data.id ?? ""),
    language: String(data.language ?? ""),
    gender: (data.gender as string | null | undefined) ?? null,
    domain: (data.domain as string | null | undefined) ?? null,
  };
}

/** List of speakers with metadata. */
export interface SpeakerList {
  speakers: Speaker[];
  total: number;
  byLanguage: Record<string, number>;
  [Symbol.iterator](): Iterator<Speaker>;
  length: number;
}

export function speakerListFromDict(data: Record<string, unknown>): SpeakerList {
  const raw = (data.speakers as Record<string, unknown>[] | undefined) ?? [];
  const speakers = raw.map(speakerFromDict);
  const total = typeof data.total === "number" ? data.total : speakers.length;
  const byLanguage =
    (data.by_language as Record<string, number> | undefined) ?? {};
  return {
    speakers,
    total,
    byLanguage,
    get length() {
      return total;
    },
    [Symbol.iterator]() {
      return speakers[Symbol.iterator]();
    },
  };
}

/** A supported language. */
export interface Language {
  code: string;
  name: string;
  speakerCount: number;
}

export function languageFromDict(data: Record<string, unknown>): Language {
  return {
    code: String(data.code ?? ""),
    name: String(data.name ?? ""),
    speakerCount: Number(data.speaker_count ?? 0),
  };
}

/** List of supported languages and domains. */
export interface LanguageList {
  languages: Language[];
  domains: string[];
}

export function languageListFromDict(data: Record<string, unknown>): LanguageList {
  const rawLangs = data.languages;
  let languages: Language[];

  if (rawLangs && typeof rawLangs === "object" && !Array.isArray(rawLangs)) {
    languages = Object.entries(rawLangs as Record<string, unknown>).map(
      ([code, value]) => {
        if (value && typeof value === "object") {
          const v = value as Record<string, unknown>;
          return {
            code,
            name: String(v.name ?? code),
            speakerCount: Number(v.speaker_count ?? 0),
          };
        }
        return { code, name: String(value), speakerCount: 0 };
      },
    );
  } else {
    const arr = (rawLangs as Record<string, unknown>[] | undefined) ?? [];
    languages = arr.map(languageFromDict);
  }

  return {
    languages,
    domains: (data.domains as string[] | undefined) ?? [],
  };
}

/** API health check result. */
export interface HealthStatus {
  status: string;
  engineReady: boolean;
  codecReady: boolean;
  totalSpeakers: number;
  languages: string[];
  voiceCloningAvailable: boolean;
  speakerProjectionLoaded: boolean;
}

export function healthStatusFromDict(data: Record<string, unknown>): HealthStatus {
  const supported = data.supported_languages;
  let languages: string[] = [];
  if (Array.isArray(data.languages)) {
    languages = data.languages as string[];
  } else if (supported && typeof supported === "object") {
    languages = Object.keys(supported as Record<string, unknown>);
  }

  return {
    status: String(data.status ?? "unknown"),
    engineReady: Boolean(data.engine_ready ?? data.tts_initialized ?? false),
    codecReady: Boolean(data.codec_ready ?? false),
    totalSpeakers: Number(data.total_speakers ?? data.speakers_loaded ?? 0),
    languages,
    voiceCloningAvailable: Boolean(data.voice_cloning_available ?? false),
    speakerProjectionLoaded: Boolean(data.speaker_projection_loaded ?? false),
  };
}

/** An available TTS model. */
export interface Model {
  id: string;
  object: string;
  ownedBy: string;
}

export function modelFromDict(data: Record<string, unknown>): Model {
  return {
    id: String(data.id ?? ""),
    object: String(data.object ?? "model"),
    ownedBy: String(data.owned_by ?? "9jalingo"),
  };
}

/** List of available models. */
export interface ModelList {
  models: Model[];
  object: string;
  [Symbol.iterator](): Iterator<Model>;
  length: number;
}

export function modelListFromDict(data: Record<string, unknown>): ModelList {
  const raw = (data.data as Record<string, unknown>[] | undefined) ?? [];
  const models = raw.map(modelFromDict);
  return {
    models,
    object: String(data.object ?? "list"),
    get length() {
      return models.length;
    },
    [Symbol.iterator]() {
      return models[Symbol.iterator]();
    },
  };
}

/** Root API information returned by GET /. */
export interface APIInfo {
  name: string;
  version: string;
  description: string;
  endpoints: Record<string, string>;
}

export function apiInfoFromDict(data: Record<string, unknown>): APIInfo {
  return {
    name: String(data.name ?? ""),
    version: String(data.version ?? ""),
    description: String(data.description ?? ""),
    endpoints: (data.endpoints as Record<string, string> | undefined) ?? {},
  };
}

/** Service metadata returned by GET /v1. */
export interface ServiceInfo {
  object: string;
  name: string;
  modelsUrl: string;
  speechUrl: string;
  speechStreamUrl: string;
}

export function serviceInfoFromDict(data: Record<string, unknown>): ServiceInfo {
  return {
    object: String(data.object ?? "service"),
    name: String(data.name ?? ""),
    modelsUrl: String(data.models_url ?? ""),
    speechUrl: String(data.speech_url ?? ""),
    speechStreamUrl: String(data.speech_stream_url ?? ""),
  };
}

export type ResponseFormat =
  | "wav"
  | "pcm"
  | "flac"
  | "aac"
  | "ogg"
  | "mp3"
  | "alac";

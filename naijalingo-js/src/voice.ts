const LANG_ALIASES: Record<string, string> = {
  yo: "yo",
  yor: "yo",
  yoruba: "yo",
  ig: "ig",
  ibo: "ig",
  igbo: "ig",
  ha: "ha",
  hau: "ha",
  hausa: "ha",
  pcm: "pcm",
  pidgin: "pcm",
};

export function normalizeLang(code: string): string | null {
  return LANG_ALIASES[code.trim().toLowerCase()] ?? null;
}

/**
 * Resolve speech API fields: voice/speaker + lang/language.
 * Returns [speakerId, langCode]. Bare language codes must be passed via lang/language.
 */
export function resolveTtsVoiceAndLang(options: {
  voice?: string | null;
  speaker?: string | null;
  lang?: string | null;
  language?: string | null;
}): [string | null, string | null] {
  let resolvedLang: string | null = null;

  if (options.lang != null) {
    resolvedLang = normalizeLang(options.lang);
    if (resolvedLang == null) {
      throw new Error(
        `Unsupported language '${options.lang}'. Use ha, ig, yo, or pcm.`,
      );
    }
  } else if (options.language != null) {
    resolvedLang = normalizeLang(options.language);
    if (resolvedLang == null) {
      throw new Error(
        `Unsupported language '${options.language}'. Use ha, ig, yo, or pcm.`,
      );
    }
  }

  // speaker takes precedence over voice
  const candidate =
    options.speaker != null ? options.speaker : options.voice;
  if (candidate == null || !String(candidate).trim()) {
    return [null, resolvedLang];
  }

  const resolved = String(candidate).trim();
  const normalized = resolved.toLowerCase();
  if (normalized in LANG_ALIASES) {
    const langCode = LANG_ALIASES[normalized];
    throw new Error(
      `'${resolved}' is a language code, not a speaker ID. ` +
        `Pass speaker/voice='ada_pcm' (or another speaker ID) and ` +
        `lang='${langCode}' for the language. ` +
        `Browse speakers with: client.tts.listSpeakers({ language: '${langCode}' })`,
    );
  }

  if (resolvedLang == null && resolved.includes("_")) {
    const suffix = resolved.split("_").pop()!;
    resolvedLang = normalizeLang(suffix);
  }

  return [resolved, resolvedLang];
}

/**
 * Resolve clone form fields.
 * voice may be a language code ("pcm") or a speaker ID with a language suffix.
 */
export function resolveCloneLangAndSpeaker(
  voice: string,
  options: { lang?: string | null; speaker?: string | null } = {},
): [string, string | null] {
  let resolvedLang =
    options.lang != null ? normalizeLang(options.lang) : null;
  let resolvedSpeaker = options.speaker?.trim() || null;

  const voiceStr = (voice || "").trim();
  const voiceNorm = voiceStr.toLowerCase();

  if (voiceNorm in LANG_ALIASES) {
    if (resolvedLang == null) {
      resolvedLang = LANG_ALIASES[voiceNorm];
    }
  } else if (voiceStr.includes("_")) {
    if (resolvedSpeaker == null) {
      resolvedSpeaker = voiceStr;
    }
    if (resolvedLang == null) {
      const suffix = voiceStr.split("_").pop()!;
      resolvedLang = normalizeLang(suffix);
    }
  } else if (voiceStr && resolvedLang == null) {
    throw new Error(
      `'${voice}' is not a language code (ha/ig/yo/pcm) or a speaker ID ` +
        `with a language suffix (e.g. 'daniel_pcm'). ` +
        `Pass voice='pcm' or lang='pcm'.`,
    );
  }

  if (!resolvedLang) {
    throw new Error(
      "Clone requires a language. Pass voice='pcm' (or 'ha'/'ig'/'yo'), " +
        "lang='pcm', or a speaker ID ending in _pcm/_ha/_ig/_yo.",
    );
  }

  return [resolvedLang, resolvedSpeaker];
}

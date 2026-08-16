"""Text-to-Speech resource for the 9jaLingo SDK."""

from __future__ import annotations

import io
import struct
from pathlib import Path
from typing import IO, Iterator, Literal

from naijalingo._client import _BaseClient
from naijalingo._types import HealthStatus, LanguageList, Speaker, SpeakerList

_DEFAULT_MODEL_NAME = "9jalingo-tts-1"

# Language codes are NOT valid speaker IDs for /v1/audio/speech.
# Common mistake: voice="pcm" → must be voice="ada_pcm" (or any speaker from list_speakers).
_LANGUAGE_CODES = frozenset({"ha", "hau", "ig", "ibo", "yo", "yor", "pcm", "pidgin"})

_LANG_ALIASES = {
    "yo": "yo", "yor": "yo", "yoruba": "yo",
    "ig": "ig", "ibo": "ig", "igbo": "ig",
    "ha": "ha", "hau": "ha", "hausa": "ha",
    "pcm": "pcm", "pidgin": "pcm",
}


def _normalize_lang(code: str) -> str | None:
    return _LANG_ALIASES.get(code.strip().lower())


def _resolve_tts_voice_and_lang(
    voice: str | None = None,
    speaker: str | None = None,
    lang: str | None = None,
    language: str | None = None,
) -> tuple[str | None, str | None]:
    """Resolve speech API fields: ``voice``/``speaker`` + ``lang``/``language``.

    Returns ``(speaker_id, lang_code)``. Bare language codes must be passed via
    ``lang``/``language``, not ``voice``/``speaker``.
    """
    resolved_lang = None
    if lang is not None:
        resolved_lang = _normalize_lang(lang)
        if resolved_lang is None:
            raise ValueError(
                f"Unsupported language '{lang}'. Use ha, ig, yo, or pcm."
            )
    elif language is not None:
        resolved_lang = _normalize_lang(language)
        if resolved_lang is None:
            raise ValueError(
                f"Unsupported language '{language}'. Use ha, ig, yo, or pcm."
            )

    # speaker takes precedence over voice (same as the inference API)
    candidate = speaker if speaker is not None else voice
    if candidate is None or not str(candidate).strip():
        return None, resolved_lang

    resolved = str(candidate).strip()
    normalized = resolved.lower()
    if normalized in _LANG_ALIASES:
        lang_code = _LANG_ALIASES[normalized]
        raise ValueError(
            f"'{resolved}' is a language code, not a speaker ID. "
            f"Pass speaker/voice='ada_pcm' (or another speaker ID) and "
            f"lang='{lang_code}' for the language. "
            f"Browse speakers with: client.tts.list_speakers(language='{lang_code}')"
        )
    if resolved_lang is None and "_" in resolved:
        # Optional convenience — server also infers lang from speaker suffix
        resolved_lang = _normalize_lang(resolved.rsplit("_", 1)[-1])
    return resolved, resolved_lang


def _resolve_clone_lang_and_speaker(
    voice: str,
    *,
    lang: str | None = None,
    speaker: str | None = None,
) -> tuple[str, str | None]:
    """Resolve clone form fields.

    ``voice`` may be either a language code (``"pcm"``) or a speaker ID with a
    language suffix (``"daniel_pcm"``). The API expects language on ``lang``.
    """
    resolved_lang = _normalize_lang(lang) if lang else None
    resolved_speaker = speaker.strip() if speaker else None

    voice_str = (voice or "").strip()
    voice_norm = voice_str.lower()

    if voice_norm in _LANG_ALIASES:
        # voice="pcm" → lang only
        if resolved_lang is None:
            resolved_lang = _LANG_ALIASES[voice_norm]
    elif "_" in voice_str:
        # voice="daniel_pcm" → optional speaker + lang from suffix
        if resolved_speaker is None:
            resolved_speaker = voice_str
        if resolved_lang is None:
            resolved_lang = _normalize_lang(voice_str.rsplit("_", 1)[-1])
    elif voice_str and resolved_lang is None:
        raise ValueError(
            f"'{voice}' is not a language code (ha/ig/yo/pcm) or a speaker ID "
            f"with a language suffix (e.g. 'daniel_pcm'). "
            f"Pass voice='pcm' or lang='pcm'."
        )

    if not resolved_lang:
        raise ValueError(
            "Clone requires a language. Pass voice='pcm' (or 'ha'/'ig'/'yo'), "
            "lang='pcm', or a speaker ID ending in _pcm/_ha/_ig/_yo."
        )
    return resolved_lang, resolved_speaker


class TTS:
    """Text-to-Speech operations.

    Usage::

        from naijalingo import NaijaLingo

        client = NaijaLingo(api_key="nl-...")
        audio = client.tts.generate(
            "Bawo ni!", voice="adeola_yo", lang="yo"
        )
        audio.save("greeting.wav")
    """

    def __init__(self, client: _BaseClient):
        self._client = client

    # ── Generation ───────────────────────────────────────────────

    def generate(
        self,
        text: str,
        *,
        voice: str | None = None,
        speaker: str | None = None,
        lang: str | None = None,
        language: str | None = None,
        model_name: str = _DEFAULT_MODEL_NAME,
        speaker_embedding: list[float] | None = None,
        response_format: Literal["wav", "pcm"] = "wav",
        temperature: float | None = None,
        top_p: float | None = None,
        repetition_penalty: float | None = None,
        enable_long_form: bool = True,
        max_chunk_duration: float | None = None,
        silence_duration: float | None = None,
    ) -> AudioResponse:
        """Generate speech from text.

        Args:
            text: The text to convert to speech.
            voice: **Speaker ID** (alias of ``speaker``) — e.g. ``"ada_pcm"``,
                ``"adaeze_ig"``, ``"aisha_ha"``, ``"adeola_yo"``.
                Do **not** pass language codes here; use ``lang`` / ``language``.
                ``speaker`` takes precedence when both are provided.
            speaker: Speaker ID (same as ``voice``). Takes precedence over
                ``voice`` when both are set.
            lang: Language code — ``"ha"``, ``"ig"``, ``"yo"``, or ``"pcm"``.
                Optional when the speaker ID already ends in a language suffix.
            language: Alias of ``lang``.
            model_name: Model ID (e.g. ``"9jalingo-tts-1"``). Defaults to
                ``"9jalingo-tts-1"``.
            speaker_embedding: Raw 128-dim speaker embedding vector for
                custom voices (from a previous ``/v1/audio/vcn/clone`` call).
            response_format: ``"wav"`` (default) or ``"pcm"`` (raw 16-bit
                signed LE samples at 22050 Hz).
            temperature: Sampling temperature (lower → more deterministic).
            top_p: Nucleus sampling threshold.
            repetition_penalty: Repetition penalty factor.
            enable_long_form: Auto-chunk texts longer than ~20 s.
            max_chunk_duration: Target max seconds per chunk.
            silence_duration: Silence gap between chunks (seconds).

        Returns:
            An :class:`AudioResponse` containing the generated audio bytes.
        """
        resolved_voice, resolved_lang = _resolve_tts_voice_and_lang(
            voice=voice, speaker=speaker, lang=lang, language=language
        )
        if resolved_voice is None and speaker_embedding is None:
            # Match API default speaker when neither speaker nor embedding is set
            resolved_voice = "blessing_pcm"
        body = self._build_body(
            input=text,
            voice=resolved_voice,
            lang=resolved_lang,
            model=model_name,
            speaker_embedding=speaker_embedding,
            response_format=response_format,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            enable_long_form=enable_long_form,
            max_chunk_duration=max_chunk_duration,
            silence_duration=silence_duration,
        )
        content = self._client._post_speech_bytes("/v1/audio/speech", body)
        media_type = "audio/wav" if response_format == "wav" else "application/octet-stream"
        return AudioResponse(content, media_type=media_type)

    def stream(
        self,
        text: str,
        *,
        voice: str | None = None,
        speaker: str | None = None,
        lang: str | None = None,
        language: str | None = None,
        speaker_embedding: list[float] | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        repetition_penalty: float | None = None,
        enable_long_form: bool = True,
        max_chunk_duration: float | None = None,
        silence_duration: float | None = None,
    ) -> AudioStream:
        """Stream speech generation — audio arrives as it's produced.

        Returns an :class:`AudioStream` that can be iterated for byte chunks
        or collected into a single :class:`AudioResponse`.

        Args:
            text: The text to convert to speech.
            voice: **Speaker ID** (alias of ``speaker``), e.g. ``"ada_pcm"``.
                ``speaker`` takes precedence when both are provided.
            speaker: Speaker ID (same as ``voice``).
            lang: Language code (``"ha"`` / ``"ig"`` / ``"yo"`` / ``"pcm"``).
            language: Alias of ``lang``.
            speaker_embedding: Raw 128-dim embedding vector.
            temperature: Sampling temperature.
            top_p: Nucleus sampling threshold.
            repetition_penalty: Repetition penalty factor.
            enable_long_form: Auto-chunk long texts.
            max_chunk_duration: Max seconds per chunk.
            silence_duration: Silence between chunks.

        Returns:
            An :class:`AudioStream` yielding WAV byte chunks.
        """
        resolved_voice, resolved_lang = _resolve_tts_voice_and_lang(
            voice=voice, speaker=speaker, lang=lang, language=language
        )
        if resolved_voice is None and speaker_embedding is None:
            resolved_voice = "blessing_pcm"
        body = self._build_body(
            input=text,
            voice=resolved_voice,
            lang=resolved_lang,
            speaker_embedding=speaker_embedding,
            response_format="wav",
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            enable_long_form=enable_long_form,
            max_chunk_duration=max_chunk_duration,
            silence_duration=silence_duration,
        )
        chunks = self._client._post_stream("/v1/audio/speech/stream", body)
        return AudioStream(chunks)

    def clone(
        self,
        text: str,
        audio_file: str | Path | IO[bytes],
        *,
        voice: str = "pcm",
        lang: str | None = None,
        speaker: str | None = None,
        model_name: str = _DEFAULT_MODEL_NAME,
        temperature: float | None = None,
        top_p: float | None = None,
        repetition_penalty: float | None = None,
        response_format: Literal["wav", "pcm", "flac", "aac", "ogg", "mp3", "alac"] = "wav",
    ) -> CloneResponse:
        """Generate speech using a cloned voice from a reference audio file.

        Args:
            text: The text to synthesize.
            audio_file: Path to a WAV file or a file-like object containing
                the reference audio.
            voice: **Language code** (``"ha"``, ``"ig"``, ``"yo"``, ``"pcm"``)
                or a speaker ID with a language suffix (``"daniel_pcm"``).
                Unlike ``generate`` / ``stream``, bare language codes are valid
                here. Sent to the API as ``lang`` (and ``voice`` only when a
                speaker ID is provided).
            lang: Explicit language code. Overrides language inferred from
                ``voice`` when set.
            speaker: Optional base speaker ID forwarded as the API ``voice``
                field. If omitted and ``voice`` looks like a speaker ID, that
                value is used.
            model_name: Model ID (e.g. ``"9jalingo-tts-1"``). Defaults to
                ``"9jalingo-tts-1"``.
            temperature: Sampling temperature.
            top_p: Nucleus sampling threshold.
            repetition_penalty: Repetition penalty factor.
            response_format: ``"wav"``, ``"pcm"``, ``"flac"``, ``"aac"``, ``"ogg"``, ``"mp3"``, or ``"alac"``.

        Returns:
            A :class:`CloneResponse` containing the generated audio bytes and
            the reusable cloned voice ID.
        """
        if isinstance(audio_file, (str, Path)):
            path = Path(audio_file)
            file_obj = open(path, "rb")
            filename = path.name
            should_close = True
        else:
            file_obj = audio_file
            filename = getattr(audio_file, "name", "audio.wav")
            should_close = False

        try:
            resolved_lang, resolved_speaker = _resolve_clone_lang_and_speaker(
                voice, lang=lang, speaker=speaker
            )
            data: dict[str, str] = {
                "text": text,
                "lang": resolved_lang,
                "model_name": model_name,
                "response_format": response_format,
            }
            # Only send voice when it's a speaker ID — bare lang codes go in lang.
            if resolved_speaker:
                data["voice"] = resolved_speaker
            if temperature is not None:
                data["temperature"] = str(temperature)
            if top_p is not None:
                data["top_p"] = str(top_p)
            if repetition_penalty is not None:
                data["repetition_penalty"] = str(repetition_penalty)

            import mimetypes
            mime_type, _ = mimetypes.guess_type(filename)
            mime_type = mime_type or "application/octet-stream"

            files = {"audio": (filename, file_obj, mime_type)}
            response = self._client._post_multipart("/v1/audio/clone", data=data, files=files)
        finally:
            if should_close:
                file_obj.close()

        media_type = {
            "wav": "audio/wav",
            "pcm": "application/octet-stream",
            "flac": "audio/flac",
            "aac": "audio/aac",
            "ogg": "audio/ogg",
            "mp3": "audio/mpeg",
            "alac": "audio/alac",
        }.get(response_format, "application/octet-stream")
        return CloneResponse(
            self._client._audio_bytes(response),
            media_type=media_type,
            voice_id=response.headers.get("X-Voice-ID"),
            voice_code=response.headers.get("X-Voice-Code"),
            voice_name=response.headers.get("X-Voice-Name"),
            clone_id=response.headers.get("X-Clone-ID"),
            job_id=response.headers.get("X-Job-ID"),
        )

    # ── Speakers ─────────────────────────────────────────────────

    def list_speakers(
        self,
        *,
        language: str | None = None,
        gender: str | None = None,
        domain: str | None = None,
    ) -> SpeakerList:
        """List available speaker voices.

        Args:
            language: Filter by language code (``"ha"``, ``"ig"``, ``"yo"``, ``"pcm"``).
            gender: Filter by gender.
            domain: Filter by domain.

        Returns:
            A :class:`SpeakerList` of matching speakers.
        """
        data = self._client._get_json(
            "/v1/speakers", language=language, gender=gender, domain=domain
        )
        return SpeakerList.from_dict(data)

    def get_speaker(self, speaker_id: str) -> Speaker:
        """Get information about a specific speaker.

        Args:
            speaker_id: The speaker identifier (e.g. ``"ada_pcm"``).

        Returns:
            A :class:`Speaker` with the speaker's details.
        """
        data = self._client._get_json(f"/v1/speakers/{speaker_id}")
        return Speaker.from_dict(data)

    # ── Languages ────────────────────────────────────────────────

    def list_languages(self) -> LanguageList:
        """List supported languages and domains.

        Returns:
            A :class:`LanguageList` with available languages.
        """
        data = self._client._get_json("/v1/languages")
        return LanguageList.from_dict(data)

    # ── Health ───────────────────────────────────────────────────

    def health(self) -> HealthStatus:
        """Check API health status.

        Returns:
            A :class:`HealthStatus` with current server state.
        """
        data = self._client._get_json("/v1/health")
        return HealthStatus.from_dict(data)

    # ── Private ──────────────────────────────────────────────────

    @staticmethod
    def _build_body(**kwargs: object) -> dict:
        """Build a request body, omitting None values."""
        return {k: v for k, v in kwargs.items() if v is not None}


# ── Audio response types ─────────────────────────────────────────


class AudioResponse:
    """Audio data returned from a generation request.

    Attributes:
        content: Raw audio bytes.
        media_type: MIME type (e.g. ``"audio/wav"``).
    """

    __slots__ = ("content", "media_type")

    def __init__(self, content: bytes, *, media_type: str = "audio/wav"):
        self.content = content
        self.media_type = media_type

    def __len__(self) -> int:
        return len(self.content)

    def __repr__(self) -> str:
        return f"AudioResponse({len(self.content)} bytes, {self.media_type})"

    def save(self, path: str | Path) -> Path:
        """Write the audio to a file.

        Args:
            path: Destination file path.

        Returns:
            The resolved :class:`Path` of the written file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.content)
        return path

    def to_bytes_io(self) -> io.BytesIO:
        """Return audio wrapped in a :class:`~io.BytesIO` buffer."""
        return io.BytesIO(self.content)


class CloneResponse(AudioResponse):
    """Audio and reusable voice metadata returned by a clone request.

    Use :attr:`voice_id` as either ``voice`` or ``speaker`` in a subsequent
    :meth:`TTS.generate` or :meth:`TTS.stream` request.
    """

    __slots__ = ("voice_id", "voice_code", "voice_name", "clone_id", "job_id")

    def __init__(
        self,
        content: bytes,
        *,
        media_type: str = "audio/wav",
        voice_id: str | None = None,
        voice_code: str | None = None,
        voice_name: str | None = None,
        clone_id: str | None = None,
        job_id: str | None = None,
    ):
        super().__init__(content, media_type=media_type)
        self.voice_id = voice_id
        self.voice_code = voice_code
        self.voice_name = voice_name
        self.clone_id = clone_id
        self.job_id = job_id


class AudioStream:
    """Streaming audio response — yields byte chunks as they arrive.

    Can be iterated directly, or collected into an :class:`AudioResponse`::

        stream = client.tts.stream("Hello world")

        # Option 1: iterate chunks (e.g. pipe to a player)
        for chunk in stream:
            player.write(chunk)

        # Option 2: collect all bytes
        audio = stream.collect()
        audio.save("output.wav")
    """

    def __init__(self, chunks: Iterator[bytes]):
        self._chunks = chunks
        self._collected: bytes | None = None

    def __iter__(self) -> Iterator[bytes]:
        return self._chunks

    def collect(self) -> AudioResponse:
        """Consume the entire stream and return an :class:`AudioResponse`."""
        if self._collected is None:
            self._collected = b"".join(self._chunks)
        return AudioResponse(self._collected, media_type="audio/wav")

"""Text-to-Speech resource for the 9jaLingo SDK."""

from __future__ import annotations

import io
import struct
from pathlib import Path
from typing import IO, Iterator, Literal

from naijalingo._client import _BaseClient
from naijalingo._types import HealthStatus, LanguageList, Speaker, SpeakerList

_DEFAULT_MODEL_NAME = "9jalingo-tts-1"


class TTS:
    """Text-to-Speech operations.

    Usage::

        from naijalingo import NaijaLingo

        client = NaijaLingo(api_key="nl-...")
        audio = client.tts.generate("Bawo ni, I dey greet you!", voice="yo")
        audio.save("greeting.wav")
    """

    def __init__(self, client: _BaseClient):
        self._client = client

    # ── Generation ───────────────────────────────────────────────

    def generate(
        self,
        text: str,
        *,
        voice: str = "pcm",
        model_name: str = _DEFAULT_MODEL_NAME,
        speaker: str | None = None,
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
            voice: Language tag — ``"ha"`` (Hausa), ``"ig"`` (Igbo),
                ``"yo"`` (Yoruba), ``"pcm"`` (Pidgin).
            model_name: Model ID (e.g. ``"9jalingo-tts-1"``). Defaults to
                ``"9jalingo-tts-1"``.
            speaker: Speaker ID (e.g. ``"ada_pcm"``). Auto-detects language
                from the speaker name.
            speaker_embedding: Raw 128-dim speaker embedding vector for
                custom voices.
            response_format: ``"wav"`` (default) or ``"pcm"`` (raw 16-bit
                signed LE samples).
            temperature: Sampling temperature (lower → more deterministic).
            top_p: Nucleus sampling threshold.
            repetition_penalty: Repetition penalty factor.
            enable_long_form: Auto-chunk texts longer than ~20 s.
            max_chunk_duration: Target max seconds per chunk.
            silence_duration: Silence gap between chunks (seconds).

        Returns:
            An :class:`AudioResponse` containing the generated audio bytes.
        """
        body = self._build_body(
            text=text,
            voice=voice,
            model_name=model_name,
            speaker=speaker,
            speaker_embedding=speaker_embedding,
            response_format=response_format,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            enable_long_form=enable_long_form,
            max_chunk_duration=max_chunk_duration,
            silence_duration=silence_duration,
        )
        content = self._client._post_bytes("/v1/audio/speech", body)
        media_type = "audio/wav" if response_format == "wav" else "application/octet-stream"
        return AudioResponse(content, media_type=media_type)

    def stream(
        self,
        text: str,
        *,
        voice: str = "pcm",
        speaker: str | None = None,
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
            voice: Language tag.
            speaker: Speaker ID.
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
        body = self._build_body(
            text=text,
            voice=voice,
            speaker=speaker,
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
        model_name: str = _DEFAULT_MODEL_NAME,
        temperature: float | None = None,
        top_p: float | None = None,
        repetition_penalty: float | None = None,
        response_format: Literal["wav", "pcm", "flac", "aac", "ogg", "mp3", "alac"] = "wav",
    ) -> AudioResponse:
        """Generate speech using a cloned voice from a reference audio file.

        Args:
            text: The text to synthesize.
            audio_file: Path to a WAV file or a file-like object containing
                the reference audio.
            voice: Language tag.
            model_name: Model ID (e.g. ``"9jalingo-tts-1"``). Defaults to
                ``"9jalingo-tts-1"``.
            temperature: Sampling temperature.
            top_p: Nucleus sampling threshold.
            repetition_penalty: Repetition penalty factor.
            response_format: ``"wav"``, ``"pcm"``, ``"flac"``, ``"aac"``, ``"ogg"``, ``"mp3"``, or ``"alac"``.

        Returns:
            An :class:`AudioResponse` containing the generated audio bytes.
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
            data = {
                "text": text,
                "voice": voice,
                "model_name": model_name,
                "response_format": response_format,
            }
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
            content = self._client._post_multipart("/v1/audio/clone", data=data, files=files)
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
        return AudioResponse(content, media_type=media_type)

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

    def __len__(self) -> int:
        return len(self.content)

    def __repr__(self) -> str:
        return f"AudioResponse({len(self.content)} bytes, {self.media_type})"


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

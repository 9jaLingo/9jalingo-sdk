"""Response types for the 9jaLingo SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class Speaker:
    """A speaker voice identity."""

    id: str
    name: str
    language: str
    gender: str | None = None
    domain: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Speaker:
        return cls(
            id=data.get("id", data.get("speaker_id", "")),
            name=data.get("name", data.get("id", "")),
            language=data.get("language", ""),
            gender=data.get("gender"),
            domain=data.get("domain"),
        )


@dataclass
class SpeakerList:
    """List of speakers with metadata."""

    speakers: list[Speaker]
    total: int
    by_language: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> SpeakerList:
        speakers = [Speaker.from_dict(s) for s in data.get("speakers", [])]
        return cls(
            speakers=speakers,
            total=data.get("total", len(speakers)),
            by_language=data.get("by_language", {}),
        )

    def __iter__(self) -> Iterator[Speaker]:
        return iter(self.speakers)

    def __len__(self) -> int:
        return self.total


@dataclass
class Language:
    """A supported language."""

    code: str
    name: str
    speaker_count: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> Language:
        return cls(
            code=data.get("code", ""),
            name=data.get("name", ""),
            speaker_count=data.get("speaker_count", 0),
        )


@dataclass
class LanguageList:
    """List of supported languages and domains."""

    languages: list[Language]
    domains: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> LanguageList:
        raw_langs = data.get("languages", [])
        if isinstance(raw_langs, dict):
            # vLLM server returns {"ha": {"name": "Hausa", "speaker_count": N, ...}}
            languages = [
                Language(
                    code=k,
                    name=v["name"] if isinstance(v, dict) else str(v),
                    speaker_count=v.get("speaker_count", 0) if isinstance(v, dict) else 0,
                )
                for k, v in raw_langs.items()
            ]
        else:
            languages = [Language.from_dict(lang) for lang in raw_langs]
        return cls(
            languages=languages,
            domains=data.get("domains", []),
        )


@dataclass
class HealthStatus:
    """API health check result."""

    status: str
    engine_ready: bool = False
    codec_ready: bool = False
    total_speakers: int = 0
    languages: list[str] = field(default_factory=list)
    voice_cloning_available: bool = False
    speaker_projection_loaded: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> HealthStatus:
        return cls(
            status=data.get("status", "unknown"),
            engine_ready=data.get("engine_ready", data.get("tts_initialized", False)),
            codec_ready=data.get("codec_ready", False),
            total_speakers=data.get("total_speakers", data.get("speakers_loaded", 0)),
            languages=data.get("languages", list(data.get("supported_languages", {}).keys())),
            voice_cloning_available=data.get("voice_cloning_available", False),
            speaker_projection_loaded=data.get("speaker_projection_loaded", False),
        )


@dataclass
class Model:
    """An available TTS model."""

    id: str
    object: str = "model"
    owned_by: str = "9jalingo"

    @classmethod
    def from_dict(cls, data: dict) -> Model:
        return cls(
            id=data.get("id", ""),
            object=data.get("object", "model"),
            owned_by=data.get("owned_by", "9jalingo"),
        )


@dataclass
class ModelList:
    """List of available models."""

    models: list[Model]
    object: str = "list"

    @classmethod
    def from_dict(cls, data: dict) -> ModelList:
        models = [Model.from_dict(m) for m in data.get("data", [])]
        return cls(models=models, object=data.get("object", "list"))

    def __iter__(self) -> Iterator[Model]:
        return iter(self.models)

    def __len__(self) -> int:
        return len(self.models)


@dataclass
class APIInfo:
    """Root API information returned by ``GET /``."""

    name: str
    version: str
    description: str
    endpoints: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> APIInfo:
        return cls(
            name=data.get("name", ""),
            version=data.get("version", ""),
            description=data.get("description", ""),
            endpoints=data.get("endpoints", {}),
        )


@dataclass
class ServiceInfo:
    """Service metadata returned by ``GET /v1``."""

    object: str
    name: str
    models_url: str = ""
    speech_url: str = ""
    speech_stream_url: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> ServiceInfo:
        return cls(
            object=data.get("object", "service"),
            name=data.get("name", ""),
            models_url=data.get("models_url", ""),
            speech_url=data.get("speech_url", ""),
            speech_stream_url=data.get("speech_stream_url", ""),
        )

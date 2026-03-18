"""
9jaLingo Python SDK
~~~~~~~~~~~~~~~~~~~

Official Python SDK for the 9jaLingo API — Nigerian language
Text-to-Speech (and soon Speech-to-Text).

Quick start::

    from naijalingo import NaijaLingo

    client = NaijaLingo(api_key="nl-...")
    audio = client.tts.generate("Bawo ni!", voice="yo")
    audio.save("greeting.wav")

Environment variables:
    NAIJALINGO_API_KEY   — default API key
    NAIJALINGO_BASE_URL  — override API base URL
"""

from naijalingo._client import _BaseClient
from naijalingo._exceptions import (
    AuthenticationError,
    ConnectionError,
    NaijaLingoError,
    NotFoundError,
    RateLimitError,
    ServerError,
)
from naijalingo._types import (
    APIInfo,
    HealthStatus,
    Language,
    LanguageList,
    Model,
    ModelList,
    ServiceInfo,
    Speaker,
    SpeakerList,
)
from naijalingo.tts import TTS, AudioResponse, AudioStream

__all__ = [
    "NaijaLingo",
    # Exceptions
    "NaijaLingoError",
    "AuthenticationError",
    "ConnectionError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
    # Types
    "AudioResponse",
    "AudioStream",
    "Speaker",
    "SpeakerList",
    "Language",
    "LanguageList",
    "HealthStatus",
    "Model",
    "ModelList",
    "APIInfo",
    "ServiceInfo",
    # Resources
    "TTS",
]

__version__ = "0.1.0"


class NaijaLingo:
    """9jaLingo API client.

    Args:
        api_key: Your 9jaLingo API key. Falls back to the
            ``NAIJALINGO_API_KEY`` environment variable.
        base_url: Override the API base URL. Falls back to
            ``NAIJALINGO_BASE_URL`` or ``https://api.9jalingo.org``.
        timeout: Request timeout in seconds (default 120).

    Usage::

        from naijalingo import NaijaLingo

        client = NaijaLingo(api_key="nl-...")

        # Generate speech
        audio = client.tts.generate("Sannu da zuwa!", voice="ha")
        audio.save("output.wav")

        # Stream speech
        for chunk in client.tts.stream("Long text...", voice="pcm"):
            sys.stdout.buffer.write(chunk)

        # List speakers
        speakers = client.tts.list_speakers(language="yo")
        for s in speakers:
            print(s.id, s.name)

        # Voice cloning
        audio = client.tts.clone(
            "Kedu ka i mere?",
            audio_file="reference.wav",
            voice="ig",
        )
        audio.save("cloned.wav")

        # List models
        models = client.list_models()
        for m in models:
            print(m.id, m.owned_by)

        # Health check
        status = client.tts.health()
        print(status.status)

        # API info
        info = client.api_info()
        print(info.name, info.version)
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = 120.0,
    ):
        self._client = _BaseClient(api_key=api_key, base_url=base_url, timeout=timeout)
        self.tts = TTS(self._client)

    # ── Model endpoints ──────────────────────────────────────────

    def list_models(self) -> ModelList:
        """List available TTS models.

        Calls ``GET /v1/models``.

        Returns:
            A :class:`ModelList` containing the available models.
        """
        data = self._client._get_json("/v1/models")
        return ModelList.from_dict(data)

    # ── Info endpoints ───────────────────────────────────────────

    def api_info(self) -> APIInfo:
        """Get root API information and available endpoints.

        Calls ``GET /``.

        Returns:
            An :class:`APIInfo` with the API name, version, and endpoint listing.
        """
        data = self._client._get_json("/")
        return APIInfo.from_dict(data)

    def service_info(self) -> ServiceInfo:
        """Get v1 service metadata.

        Calls ``GET /v1``.

        Returns:
            A :class:`ServiceInfo` with service URLs and metadata.
        """
        data = self._client._get_json("/v1")
        return ServiceInfo.from_dict(data)

    # ── Lifecycle ────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self) -> str:
        return f"NaijaLingo(base_url={self._client.base_url!r})"

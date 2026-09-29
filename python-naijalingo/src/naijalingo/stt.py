"""Speech-to-Text resource for the 9jaLingo SDK."""

from dataclasses import dataclass

from naijalingo._client import _BaseClient
from naijalingo._exceptions import ServerError


@dataclass(frozen=True)
class Transcription:
    text: str
    language: str | None = None
    duration: float | None = None
    model: str | None = None


class STT:
    """Speech-to-Text operations backed by the 9jaLingo API."""

    def __init__(self, client: _BaseClient):
        self._client = client

    def transcribe(
        self,
        file_url: str,
        *,
        language: str | None = None,
    ) -> Transcription:
        """Transcribe audio hosted at a public HTTPS URL."""
        body = {"file_url": file_url}
        if language is not None:
            body["language"] = language
        response = self._client._post_json("/v1/audio/transcriptions", body)
        result = response
        while isinstance(result, dict) and isinstance(result.get("result"), dict):
            result = result["result"]
        if isinstance(result, dict) and result.get("error"):
            raise ServerError(str(result["error"]), status_code=502, response=result)
        return Transcription(
            text=str(result.get("text", "")),
            language=result.get("language"),
            duration=result.get("duration"),
            model=result.get("model"),
        )
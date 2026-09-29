import httpx
import pytest

from naijalingo import InvalidRequestError, ServerError
from naijalingo._client import _BaseClient
from naijalingo.stt import STT


def _stt_with_response(body, status_code=200):
    client = _BaseClient(api_key="test-key", base_url="https://api.test")
    client._client.close()
    client._client = httpx.Client(
        base_url="https://api.test",
        headers={"X-API-Key": "test-key"},
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status_code, json=body)
        ),
    )
    return STT(client)


def test_stt_maps_broken_audio_url_to_invalid_request():
    stt = _stt_with_response(
        {"detail": "Audio URL returned HTTP 404. Use a direct public audio URL."},
        status_code=422,
    )

    with pytest.raises(InvalidRequestError, match="HTTP 404") as exc:
        stt.transcribe("https://audio.example/missing.wav", language="yo")

    assert exc.value.status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {"result": {"error": "Model failed"}},
        {"error": "Model failed", "result": {"text": "ignored success"}},
        {"result": {"text": None}},
        {"result": "unexpected"},
    ],
)
def test_stt_rejects_error_or_malformed_success_payloads(body):
    stt = _stt_with_response(body)

    with pytest.raises(ServerError):
        stt.transcribe("https://audio.example/sample.wav", language="yo")


def test_stt_accepts_empty_transcript_for_silence():
    stt = _stt_with_response({"result": {"text": "", "language": "yor_Latn"}})

    transcript = stt.transcribe("https://audio.example/silent.wav", language="yo")

    assert transcript.text == ""
    assert transcript.language == "yor_Latn"
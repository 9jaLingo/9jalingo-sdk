from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
import pytest

from naijalingo._client import _BaseClient
from naijalingo._exceptions import InferenceCapacityError, ServerError


def client_with(handler):
    client = _BaseClient(api_key="test-key", base_url="https://api.test")
    client._client.close()
    client._client = httpx.Client(
        base_url="https://api.test",
        headers={"X-API-Key": "test-key"},
        transport=httpx.MockTransport(handler),
    )
    return client


def test_speech_returns_warm_audio_directly():
    def handler(request):
        assert request.headers["prefer"] == "respond-async-on-cold-start"
        return httpx.Response(200, content=b"RIFFaudio", headers={"content-type": "audio/wav"})

    client = client_with(handler)
    assert client._post_speech_bytes("/v1/audio/speech", {"input": "hello"}) == b"RIFFaudio"


def test_speech_polls_queued_job_and_downloads_audio_with_api_key():
    requests = []
    statuses = iter(["queued", "completed"])
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    def handler(request):
        requests.append(request)
        assert request.headers["x-api-key"] == "test-key"
        if request.method == "POST":
            return httpx.Response(
                202,
                json={
                    "status": "queued",
                    "job_id": "job/unsafe",
                    "retry_after": 1,
                    "expires_at": expires_at,
                },
            )
        if request.url.path.endswith("/audio"):
            return httpx.Response(200, content=b"RIFFdone", headers={"content-type": "audio/wav"})
        return httpx.Response(200, json={"status": next(statuses), "retry_after": 1})

    client = client_with(handler)
    with patch("naijalingo._client.time.sleep"):
        audio = client._post_speech_bytes("/v1/audio/speech", {"input": "hello"})

    assert audio == b"RIFFdone"
    assert [request.url.path for request in requests] == [
        "/v1/audio/speech",
        "/v1/jobs/job%2Funsafe",
        "/v1/jobs/job%2Funsafe",
        "/v1/jobs/job%2Funsafe/audio",
    ]


def test_speech_raises_explained_failed_job():
    def handler(request):
        if request.method == "POST":
            return httpx.Response(202, json={"status": "queued", "job_id": "job-1", "retry_after": 1})
        return httpx.Response(200, json={"status": "failed", "error": "model failed"})

    client = client_with(handler)
    with patch("naijalingo._client.time.sleep"):
        with pytest.raises(ServerError, match="model failed"):
            client._post_speech_bytes("/v1/audio/speech", {"input": "hello"})


@pytest.mark.parametrize(
    "body",
    [
        {"status": "queued"},
        {"status": "unexpected", "job_id": "job-1"},
    ],
)
def test_speech_rejects_malformed_202(body):
    client = client_with(lambda request: httpx.Response(202, json=body))
    with pytest.raises(ServerError, match="invalid queued|job ID"):
        client._post_speech_bytes("/v1/audio/speech", {"input": "hello"})


def test_speech_honors_expired_queue_deadline():
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    client = client_with(
        lambda request: httpx.Response(
            202,
            json={"status": "queued", "job_id": "job-1", "expires_at": expired},
        )
    )
    with pytest.raises(InferenceCapacityError, match="expired"):
        client._post_speech_bytes("/v1/audio/speech", {"input": "hello"})


def test_stream_does_not_send_cold_start_preference():
    def handler(request):
        assert "prefer" not in request.headers
        return httpx.Response(200, content=b"audio")

    client = client_with(handler)
    assert b"".join(client._post_stream("/v1/audio/speech/stream", {"input": "hello"})) == b"audio"
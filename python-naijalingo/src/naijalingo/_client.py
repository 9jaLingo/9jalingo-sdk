"""Low-level HTTP client for the 9jaLingo API."""

from __future__ import annotations

import os
from typing import Any, Iterator

import httpx

from naijalingo._exceptions import (
    AuthenticationError,
    ConnectionError,
    InferenceCapacityError,
    NaijaLingoError,
    NotFoundError,
    RateLimitError,
    ServerError,
)

_DEFAULT_BASE_URL = "https://api.9jalingo.org"
# The server serializes all inference behind a single asyncio.Lock (batch_size=1).
# Under concurrent load, each request must wait for all preceding ones to finish.
# Formula: N_concurrent * single_request_latency.  300s handles up to ~25 requests
# at ~12s each.  Override via NaijaLingo(timeout=...) for higher concurrency.
_DEFAULT_TIMEOUT = 300.0


class _BaseClient:
    """Shared HTTP transport for all 9jaLingo resource classes."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key or os.environ.get("NAIJALINGO_API_KEY", "")
        resolved_base_url = base_url
        self.base_url = resolved_base_url.rstrip("/")
        self.timeout = timeout

        # api_key is optional for self-hosted / local vLLM servers that have
        # no authentication middleware. For the managed API (api.9jalingo.org)
        # a key is required and the server will 401 without it.
        headers: dict[str, str] = {"User-Agent": "naijalingo-python/0.1.0"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers=headers,
        )

    # ── HTTP helpers ─────────────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Make an HTTP request and handle errors."""
        import time
        last_exc = None
        for attempt in range(3):
            try:
                response = self._client.request(method, path, **kwargs)
                break
            except httpx.ConnectError as exc:
                last_exc = exc
            except httpx.TimeoutException as exc:
                # Only retry connection timeouts, not read timeouts
                if isinstance(exc, httpx.ConnectTimeout):
                    last_exc = exc
                else:
                    raise ConnectionError(f"Request timed out after {self.timeout}s: {exc}") from exc
                
            if attempt < 2:
                time.sleep(1.5)
        else:
            if isinstance(last_exc, httpx.ConnectError):
                raise ConnectionError(f"Unable to connect to {self.base_url}: {last_exc}") from last_exc
            else:
                raise ConnectionError(f"Request timed out after {self.timeout}s: {last_exc}") from last_exc

        if response.is_success:
            return response

        self._raise_for_status(response)

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Convert HTTP error responses into typed exceptions."""
        status = response.status_code
        try:
            body = response.json()
            detail = body.get("detail", response.text)
        except Exception:
            detail = response.text

        capacity_message = detail.lower() if isinstance(detail, str) else ""
        if status == 503 and (
            "inference capacity" in capacity_message
            or "inference component has no capacity" in capacity_message
            or "capacity is starting" in capacity_message
        ):
            raise InferenceCapacityError(
                detail,
                status_code=status,
                response=body if isinstance(body, dict) else None,
            )
        elif status == 401 or status == 403:
            raise AuthenticationError(detail, status_code=status)
        elif status == 404:
            raise NotFoundError(detail, status_code=status)
        elif status == 429:
            raise RateLimitError(detail, status_code=status)
        elif status >= 500:
            raise ServerError(detail, status_code=status)
        else:
            raise NaijaLingoError(detail, status_code=status)

    def _get_json(self, path: str, **params: Any) -> dict:
        """GET request returning parsed JSON."""
        resp = self._request("GET", path, params={k: v for k, v in params.items() if v is not None})
        return resp.json()

    def _post_json(self, path: str, body: dict) -> dict:
        """POST request with JSON body, returning parsed JSON."""
        resp = self._request("POST", path, json=body)
        return resp.json()

    def _post_bytes(self, path: str, body: dict) -> bytes:
        """POST request with JSON body, returning raw bytes."""
        resp = self._request("POST", path, json=body)
        return resp.content

    def _post_stream(self, path: str, body: dict) -> Iterator[bytes]:
        """POST request returning a byte stream (chunked transfer)."""
        import time
        for attempt in range(3):
            try:
                with self._client.stream("POST", path, json=body) as resp:
                    if not resp.is_success:
                        resp.read()
                        self._raise_for_status(resp)
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        if chunk:
                            yield chunk
                return
            except httpx.ConnectError as exc:
                if attempt < 2:
                    time.sleep(1.5)
                    continue
                raise ConnectionError(f"Unable to connect to {self.base_url}: {exc}") from exc
            except httpx.TimeoutException as exc:
                if attempt < 2 and isinstance(exc, httpx.ConnectTimeout):
                    time.sleep(1.5)
                    continue
                raise ConnectionError(f"Request timed out: {exc}") from exc

    def _post_multipart(self, path: str, data: dict, files: dict) -> bytes:
        """POST multipart/form-data, returning raw bytes."""
        resp = self._request(
            "POST", path, data=data, files=files,
            timeout=httpx.Timeout(max(self.timeout, 600), connect=10.0),
        )
        return resp.content

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args: Any):
        self.close()

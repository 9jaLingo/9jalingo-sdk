"""Low-level HTTP client for the 9jaLingo API."""

from __future__ import annotations

import os
from typing import Any, Iterator

import httpx

from naijalingo._exceptions import (
    AuthenticationError,
    ConnectionError,
    NaijaLingoError,
    NotFoundError,
    RateLimitError,
    ServerError,
)

_DEFAULT_BASE_URL = "https://api.9jalingo.org"
_DEFAULT_TIMEOUT = 120.0


class _BaseClient:
    """Shared HTTP transport for all 9jaLingo resource classes."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key or os.environ.get("NAIJALINGO_API_KEY", "")
        resolved_base_url = base_url or os.environ.get("NAIJALINGO_BASE_URL", _DEFAULT_BASE_URL)
        self.base_url = resolved_base_url.rstrip("/")
        self.timeout = timeout

        if not self.api_key:
            raise AuthenticationError(
                "No API key provided. Pass api_key= or set the NAIJALINGO_API_KEY environment variable."
            )

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={
                "X-API-Key": self.api_key,
                "User-Agent": "naijalingo-python/0.1.0",
            },
        )

    # ── HTTP helpers ─────────────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Make an HTTP request and handle errors."""
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Unable to connect to {self.base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise ConnectionError(f"Request timed out after {self.timeout}s: {exc}") from exc

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

        if status == 401 or status == 403:
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
        try:
            with self._client.stream("POST", path, json=body) as resp:
                if not resp.is_success:
                    resp.read()
                    self._raise_for_status(resp)
                for chunk in resp.iter_bytes(chunk_size=8192):
                    if chunk:
                        yield chunk
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Unable to connect to {self.base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise ConnectionError(f"Request timed out: {exc}") from exc

    def _post_multipart(self, path: str, data: dict, files: dict) -> bytes:
        """POST multipart/form-data, returning raw bytes."""
        resp = self._request("POST", path, data=data, files=files)
        return resp.content

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args: Any):
        self.close()

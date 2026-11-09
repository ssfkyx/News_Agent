# =============================================================================
# Module: newsagent.http
# Responsibilities: Shared HTTP client: retries, user agent, request pacing.
# Dependencies: httpx
# Dependents: fetch adapters
# ADRs: ADR-0003
# Traceability: docs/decisions/README.md
# =============================================================================
"""Small HTTP wrapper: retries, UA, per-request pacing."""

from __future__ import annotations

import time

import httpx


class HttpClient:
    def __init__(self, *, timeout: float = 25.0, retries: int = 2,
                 user_agent: str = "AI-News-Agent/0.1",
                 interval_seconds: float = 0.5) -> None:
        self.retries = retries
        self.interval_seconds = interval_seconds
        self.client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            timeout=timeout,
            follow_redirects=True,
        )

    def get(self, url: str, **kwargs) -> httpx.Response:
        """Perform a GET with retries and request pacing.

        Preconditions:
            url is an absolute HTTP(S) URL; client kwarg overrides are forwarded to httpx.
        Postconditions:
            httpx.Response after retries; pacing sleep applied before returning.
        Prohibitions:
            Do not set follow_redirects=False without a reason.
        Raises:
            RuntimeError after all retries fail.
        """
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.client.get(url, **kwargs)
                if response.status_code >= 500 and attempt < self.retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if self.interval_seconds:
                    time.sleep(self.interval_seconds)
                return response
            except Exception as exc:  # noqa: BLE001 - network errors are retried
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"GET {url} failed: {last_error}")

    def get_json(self, url: str, **kwargs):
        """GET a URL and decode a JSON body.

        Preconditions:
            url is absolute; response must be HTTP 200 with JSON.
        Postconditions:
            Decoded JSON value.
        Prohibitions:
            Do not use for large binary payloads.
        Raises:
            RuntimeError on non-200; json.JSONDecodeError for invalid JSON.
        """
        response = self.get(url, **kwargs)
        if response.status_code != 200:
            raise RuntimeError(f"GET {url} -> HTTP {response.status_code}: {response.text[:160]}")
        return response.json()

    def close(self) -> None:
        """Close the underlying httpx client.

        Preconditions:
            The client has not been closed yet.
        Postconditions:
            Nothing; subsequent requests fail.
        Prohibitions:
            Do not reuse the client after closing.
        Raises:
            None.
        """
        self.client.close()

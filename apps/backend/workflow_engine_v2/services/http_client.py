"""HTTP client wrapper for runners.

Provides a small sync API on top of httpx with sensible defaults.
"""

from __future__ import annotations

import base64
import time
from typing import Any, Dict, Optional

import httpx


class HTTPResponse:
    def __init__(self, status_code: int, headers: Dict[str, str], json: Any, text: str):
        self.status_code = status_code
        self.headers = headers
        self.json = json
        self.text = text


class HTTPClient:
    def __init__(
        self, timeout: float = 30.0, follow_redirects: bool = True, verify_ssl: bool = True
    ):
        self._client = httpx.Client(
            timeout=timeout, follow_redirects=follow_redirects, verify=verify_ssl
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Any] = None,
        data_body: Optional[Dict[str, Any]] = None,
        auth: Optional[Dict[str, Any]] = None,
        retry_attempts: int = 0,
        backoff_seconds: float = 0.0,
    ) -> HTTPResponse:
        # Handle auth injection
        h = dict(headers or {})
        if auth:
            atype = str(auth.get("type", "")).lower()
            if atype == "bearer" and auth.get("token"):
                h["Authorization"] = f"Bearer {auth['token']}"
            if atype == "basic" and auth.get("username") and auth.get("password"):
                raw = f"{auth['username']}:{auth['password']}".encode()
                h["Authorization"] = "Basic " + base64.b64encode(raw).decode()

        attempt = 0
        exc: Optional[Exception] = None
        while attempt <= int(retry_attempts or 0):
            try:
                r = self._client.request(
                    method.upper(), url, headers=h, params=params, json=json_body, data=data_body
                )
                try:
                    j = r.json()
                except Exception:
                    j = None
                return HTTPResponse(r.status_code, dict(r.headers), j, r.text)
            except Exception as e:
                exc = e
                attempt += 1
                if attempt > int(retry_attempts or 0):
                    break
                if backoff_seconds and backoff_seconds > 0:
                    time.sleep(backoff_seconds)
        # If we reach here, final exception was raised
        raise exc or Exception("HTTP request failed")

    def close(self):
        self._client.close()


__all__ = ["HTTPClient", "HTTPResponse"]

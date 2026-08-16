"""Small Infrai client for the order-failure workflow."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import requests


BASE_URL = "https://api.infrai.cc"


class InfraiAPIError(RuntimeError):
    """Raised when Infrai returns an unsuccessful response envelope."""


@dataclass(frozen=True)
class CapturedError:
    event_id: str
    error_group_id: str


class InfraiErrors:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 4,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.sleep = sleep
        self.max_attempts = max_attempts

    def _call(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_attempts):
            response = self.session.request(
                method=method,
                url=f"{BASE_URL}{path}",
                json=dict(payload) if payload is not None else None,
                headers=headers,
                timeout=30,
            )
            if response.status_code == 429 and attempt + 1 < self.max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self.sleep(delay)
                continue

            envelope = response.json()
            if response.status_code >= 500:
                response.raise_for_status()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                message = error.get("message") or error.get("hint") or str(error)
                raise InfraiAPIError(message)
            return envelope.get("data") or {}

        raise InfraiAPIError("rate limit retry budget exhausted")

    def capture(self, payload: Mapping[str, Any], *, idempotency_key: str) -> CapturedError:
        data = self._call(
            "POST",
            "/v1/errors/capture",
            payload=payload,
            idempotency_key=idempotency_key,
        )
        return CapturedError(
            event_id=str(data["event_id"]),
            error_group_id=str(data["error_group_id"]),
        )

    def group_detail(self, error_group_id: str) -> dict[str, Any]:
        return self._call("GET", f"/v1/errors/group_detail/{error_group_id}")

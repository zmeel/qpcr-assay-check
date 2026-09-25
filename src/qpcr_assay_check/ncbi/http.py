"""HTTP layer: NCBI etiquette (identification, throttling) plus retry with exponential backoff."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable, Mapping
from typing import Any

import requests

from .. import __version__
from ..config import NcbiSettings
from ..errors import QpcrAssayCheckError
from .settings import Credentials

log = logging.getLogger(__name__)

RETRY_STATUS = {429, 500, 502, 503, 504}
# NCBI allows 3 requests/second without an API key and 10 with one. Spacing requests exactly at
# that limit still produced HTTP 429 in a live run (bursts on the server side), so stay well below.
EUTILS_INTERVAL_NO_KEY = 0.5  # about 2 requests/second
EUTILS_INTERVAL_KEY = 0.15  # about 6-7 requests/second
# NCBI Datasets v2 answered with "X-Ratelimit-Limit: 10" when an API key was sent (live probe,
# 2026-09-23); the limit without a key was not measured, so stay at the E-utilities keyless pace.
DATASETS_INTERVAL_KEY = 0.25  # about 4 requests/second
DATASETS_INTERVAL_NO_KEY = 0.5


class NcbiError(QpcrAssayCheckError):
    """A problem talking to NCBI (network, server, or an unexpected response)."""


class RateLimiter:
    """Guarantees a minimum interval between successive calls."""

    def __init__(
        self,
        min_interval_s: float,
        *,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.min_interval_s = min_interval_s
        self._clock = clock or (lambda: time.monotonic())
        self._sleep = sleep or (lambda s: time.sleep(s))
        self._last: float | None = None

    def wait(self) -> None:
        """Block until the minimum interval since the previous call has elapsed."""
        now = self._clock()
        if self._last is not None:
            remaining = self._last + self.min_interval_s - now
            if remaining > 0:
                self._sleep(remaining)
                now = self._clock()
        self._last = now


class NcbiHttp:
    """Sends requests to NCBI politely: identified, throttled, retried with backoff."""

    def __init__(
        self,
        settings: NcbiSettings,
        creds: Credentials,
        *,
        session: requests.Session | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
        jitter: Callable[[], float] | None = None,
    ) -> None:
        self.settings = settings
        self.creds = creds
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = (
            f"{settings.tool}/{__version__} ({creds.email}) python-requests"
        )
        self._sleep = sleep or (lambda s: time.sleep(s))
        self._jitter = jitter or (lambda: random.random())
        eutils_interval = EUTILS_INTERVAL_KEY if creds.api_key else EUTILS_INTERVAL_NO_KEY
        datasets_interval = DATASETS_INTERVAL_KEY if creds.api_key else DATASETS_INTERVAL_NO_KEY
        self._limiters = {
            "blast": RateLimiter(settings.blast_min_interval_s, clock=clock, sleep=sleep),
            "eutils": RateLimiter(eutils_interval, clock=clock, sleep=sleep),
            "datasets": RateLimiter(datasets_interval, clock=clock, sleep=sleep),
        }

    def _identify(self, service: str, payload: dict[str, Any]) -> dict[str, Any]:
        out = dict(payload)
        if service == "datasets":
            # The Datasets API documents no tool/email parameters; the key goes in a header and
            # the User-Agent identifies the tool.
            return out
        out["tool"] = self.settings.tool
        out["email"] = self.creds.email
        if service == "eutils" and self.creds.api_key:
            out["api_key"] = self.creds.api_key
        return out

    def request(
        self,
        method: str,
        url: str,
        *,
        service: str,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
    ) -> requests.Response:
        """Send one request, retrying transient failures. Raises :class:`NcbiError` on failure."""
        limiter = self._limiters[service]
        s = self.settings
        query = self._identify(service, dict(params)) if params is not None else None
        body = self._identify(service, dict(data)) if data is not None else None
        if query is None and body is None:
            query = self._identify(service, {})
        headers = (
            {"api-key": self.creds.api_key}  # datasets.openapi.yaml: ApiKeyAuthHeader
            if service == "datasets" and self.creds.api_key
            else None
        )
        last_problem = ""
        for attempt in range(s.max_retries + 1):
            limiter.wait()
            try:
                log.debug("NCBI %s %s (attempt %d)", method, url, attempt + 1)
                resp = self.session.request(
                    method, url, params=query, data=body, timeout=s.request_timeout_s,
                    headers=headers,
                )  # fmt: skip
            except (
                requests.ConnectionError,
                requests.Timeout,
                # the body was cut off mid-transfer (live: a Datasets genome download ended
                # with "Response ended prematurely" after hours of downloads)
                requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ContentDecodingError,
            ) as exc:
                last_problem = f"{type(exc).__name__}: {self.creds.redact(str(exc))}"
            else:
                if resp.status_code < 400:
                    return resp
                last_problem = f"HTTP {resp.status_code}"
                if resp.status_code not in RETRY_STATUS:
                    snippet = self.creds.redact(resp.text[:300].strip())
                    raise NcbiError(f"NCBI rejected the request ({last_problem}): {snippet}")
                retry_after = resp.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    self._sleep(min(float(retry_after), 300.0))
            if attempt < s.max_retries:
                delay = s.backoff_base_s * (2**attempt) * (1 + 0.25 * self._jitter())
                log.warning("NCBI request failed (%s); retrying in %.0f s", last_problem, delay)
                self._sleep(delay)
        raise NcbiError(
            f"NCBI request failed after {s.max_retries + 1} attempts ({last_problem}). "
            "A resumable run keeps its state; run the same command again later."
        )

"""
http_client.py — HTTP Client Wrapper (Sync)
=============================================
Contract v1.2 — Decision: Sync (گزینه A)

Wrapper روی httpx.Client با قابلیت‌های:
    - ارسال درخواست‌های GET / POST (Sync)
    - Logging استاندارد (METHOD, URL, elapsed_ms, status_code)
    - Error Translation به Exceptionهای پروژه
    - Session Reuse (یک Client مشترک)
    - Headerهای استاندارد (User-Agent, Accept, Accept-Encoding)
    - Timeout / Limits از Config خوانده می‌شود

Retry logic به RetryExecutor در retry_policy.py واگذار شده است.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.services.geo.clients.exceptions import (
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderServerError,
    ProviderRateLimitError,
    ProviderClientError,
)

logger = logging.getLogger(__name__)

# ── Defaults (fallback — real values from Config) ──────────
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_KEEPALIVE = 5
DEFAULT_MAX_CONNECTIONS = 10


class HttpClient:
    """
    کلاینت HTTP ساده (Sync) — بدون retry داخلی.

    Usage:
        client = HttpClient("https://fimap.local")
        resp = client.get("/api/health")
        data = resp.json()
    """

    # ═════════════════════════════════════════════════════════
    # Constructor
    # ═════════════════════════════════════════════════════════

    def __init__(
        self,
        base_url: str,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
        max_keepalive_connections: int | None = None,
        max_connections: int | None = None,
    ):
        """
        Args:
            base_url: آدرس پایه Provider (مثلاً http://fimap.local).
            timeout: timeout کلی به ثانیه (None = از Config خوانده شود).
            headers: Headerهای اضافی (با default merge می‌شود).
            max_keepalive_connections: حداکثر اتصالات keep-alive.
            max_connections: حداکثر اتصالات هم‌زمان.
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout or self._read_timeout_from_config()
        self._provider_name = self._extract_provider_name(base_url)

        merged_headers = self._build_default_headers()
        if headers:
            merged_headers.update(headers)

        self._client = httpx.Client(
            timeout=httpx.Timeout(self._timeout),
            headers=merged_headers,
            limits=httpx.Limits(
                max_keepalive_connections=max_keepalive_connections
                or self._read_max_keepalive_from_config(),
                max_connections=max_connections
                or self._read_max_connections_from_config(),
            ),
        )

    # ═════════════════════════════════════════════════════════
    # Public API
    # ═════════════════════════════════════════════════════════

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """
        GET request (Sync).

        Args:
            path: مسیر نسبی (مثلاً /api/health).
            **kwargs: پارامترهای اضافی httpx (params, headers, ...).

        Returns:
            httpx.Response.

        Raises:
            ProviderConnectionError | ProviderTimeoutError |
            ProviderServerError | ProviderClientError |
            ProviderRateLimitError
        """
        url = self._build_url(path)
        start = time.perf_counter()

        try:
            response = self._client.get(url, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "GET %s → %s (%.2fms)",
                url,
                response.status_code,
                elapsed_ms,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "GET %s → %s (%.2fms) HTTP ERROR",
                url,
                e.response.status_code,
                elapsed_ms,
            )
            self._translate_error(e)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "GET %s → %s (%.2fms)",
                url,
                type(e).__name__.upper(),
                elapsed_ms,
            )
            self._translate_error(e)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        """
        POST request (Sync).

        Args:
            path: مسیر نسبی.
            **kwargs: پارامترهای اضافی httpx (json, data, params, ...).

        Returns:
            httpx.Response.

        Raises:
            ProviderConnectionError | ProviderTimeoutError |
            ProviderServerError | ProviderClientError |
            ProviderRateLimitError
        """
        url = self._build_url(path)
        start = time.perf_counter()

        try:
            response = self._client.post(url, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "POST %s → %s (%.2fms)",
                url,
                response.status_code,
                elapsed_ms,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "POST %s → %s (%.2fms) HTTP ERROR",
                url,
                e.response.status_code,
                elapsed_ms,
            )
            self._translate_error(e)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "POST %s → %s (%.2fms)",
                url,
                type(e).__name__.upper(),
                elapsed_ms,
            )
            self._translate_error(e)

    # ═════════════════════════════════════════════════════════
    # Cleanup / Context Manager
    # ═════════════════════════════════════════════════════════

    def close(self) -> None:
        """بستن کلاینت و آزادسازی اتصالات."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # ═════════════════════════════════════════════════════════
    # Private Helpers
    # ═════════════════════════════════════════════════════════

    def _build_url(self, path: str) -> str:
        """ساخت URL کامل از base_url + path."""
        return f"{self._base_url}/{path.lstrip('/')}"

    @staticmethod
    def _build_default_headers() -> dict[str, str]:
        """Headerهای استاندارد برای تمام درخواست‌ها."""
        return {
            "User-Agent": "DIP-GeoClient/1.2",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }

    def _translate_error(self, e: Exception) -> None:
        """
        تبدیل Exceptionهای httpx به Exceptionهای استاندارد پروژه.

        این متد همیشه raise می‌کند — هیچ‌گاه return نمی‌کند.
        """
        if isinstance(e, httpx.HTTPStatusError):
            status = e.response.status_code
            detail = e.response.text[:500]
            if status == 429:
                retry_after = self._parse_retry_after(e.response)
                raise ProviderRateLimitError(self._provider_name, retry_after)
            elif 500 <= status < 600:
                raise ProviderServerError(self._provider_name, status, detail)
            else:
                raise ProviderClientError(self._provider_name, status, detail)

        elif isinstance(e, httpx.TimeoutException):
            raise ProviderTimeoutError(
                self._provider_name,
                self._timeout,
                str(e),
            )

        elif isinstance(e, httpx.ConnectError):
            raise ProviderConnectionError(self._provider_name, str(e))

        # Fallback
        raise ProviderConnectionError(self._provider_name, str(e))

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float | None:
        """خواندن Retry-After header (در صورت وجود)."""
        raw = response.headers.get("Retry-After")
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    @staticmethod
    def _extract_provider_name(base_url: str) -> str:
        """استخراج نام Provider از URL (برای Exception messages)."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            return parsed.hostname or base_url
        except Exception:
            return base_url

    # ═════════════════════════════════════════════════════════
    # Config Readers (TODO: replace with actual config)
    # ═════════════════════════════════════════════════════════

    @staticmethod
    def _read_timeout_from_config() -> float:
        """خواندن timeout از Config (fallback = DEFAULT_TIMEOUT)."""
        try:
            from app.core.config import settings
            return getattr(settings, "GEO_HTTP_TIMEOUT", DEFAULT_TIMEOUT)
        except ImportError:
            return DEFAULT_TIMEOUT

    @staticmethod
    def _read_max_keepalive_from_config() -> int:
        """خواندن max_keepalive از Config."""
        try:
            from app.core.config import settings
            return getattr(settings, "GEO_MAX_KEEPALIVE", DEFAULT_MAX_KEEPALIVE)
        except ImportError:
            return DEFAULT_MAX_KEEPALIVE

    @staticmethod
    def _read_max_connections_from_config() -> int:
        """خواندن max_connections از Config."""
        try:
            from app.core.config import settings
            return getattr(settings, "GEO_MAX_CONNECTIONS", DEFAULT_MAX_CONNECTIONS)
        except ImportError:
            return DEFAULT_MAX_CONNECTIONS

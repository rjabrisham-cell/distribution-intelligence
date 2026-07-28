"""
clients/exceptions.py — Client-Level Exceptions
================================================
Contract v1.2 — Exceptionهای استاندارد برای لایه HTTP Client.

این Exceptionها جایگزین Exceptionهای raw httpx می‌شوند
تا Adapterها وابسته به کتابخانه خارجی نباشند.
"""

from __future__ import annotations


class ProviderConnectionError(Exception):
    """خطای اتصال به Provider (DNS, refusal, network)."""

    def __init__(self, provider: str, detail: str):
        self.provider = provider
        self.detail = detail
        super().__init__(f"[{provider}] Connection error: {detail}")


class ProviderTimeoutError(Exception):
    """Timeout در انتظار پاسخ از Provider."""

    def __init__(self, provider: str, timeout_s: float, detail: str):
        self.provider = provider
        self.timeout_s = timeout_s
        self.detail = detail
        super().__init__(f"[{provider}] Timeout ({timeout_s}s): {detail}")


class ProviderServerError(Exception):
    """خطای سمت سرور Provider (5xx)."""

    def __init__(self, provider: str, status_code: int, detail: str):
        self.provider = provider
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{provider}] Server error {status_code}: {detail}")


class ProviderRateLimitError(Exception):
    """Rate Limit توسط Provider (429)."""

    def __init__(self, provider: str, retry_after: float | None = None):
        self.provider = provider
        self.retry_after = retry_after
        msg = f"[{provider}] Rate limited"
        if retry_after:
            msg += f" — retry after {retry_after}s"
        super().__init__(msg)


class ProviderClientError(Exception):
    """خطای سمت کلاینت (4xx غیر از 429)."""

    def __init__(self, provider: str, status_code: int, detail: str):
        self.provider = provider
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{provider}] Client error {status_code}: {detail}")

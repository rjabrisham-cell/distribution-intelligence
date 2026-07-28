"""
clients package — HTTP Client & Retry (Sync)
=============================================
Contract v1.2 — Decision: Sync (گزینه A)

Provides:
    - HttpClient        : httpx.Client wrapper با logging و error translation
    - RetryPolicy       : immutable retry configuration
    - RetryExecutor     : synchronous retry execution (generic)
    - Exceptions        : ProviderConnectionError, ProviderTimeoutError, ...
"""

from app.services.geo.clients.http_client import HttpClient
from app.services.geo.clients.retry_policy import RetryPolicy, RetryExecutor
from app.services.geo.clients.exceptions import (
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderServerError,
    ProviderRateLimitError,
    ProviderClientError,
)

__all__ = [
    "HttpClient",
    "RetryPolicy",
    "RetryExecutor",
    "ProviderConnectionError",
    "ProviderTimeoutError",
    "ProviderServerError",
    "ProviderRateLimitError",
    "ProviderClientError",
]

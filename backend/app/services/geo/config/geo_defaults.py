"""
config/geo_defaults.py — Centralized Geo Defaults
==================================================
Contract v1.2

تمامی مقادیر پیش‌فرض برای Geo Providers در یک نقطه متمرکز شده‌اند.
هیچ وابستگی به clients/ یا adapters/ ندارد.

Usage:
    from app.services.geo.config.geo_defaults import GEO_DEFAULTS
    timeout = GEO_DEFAULTS["timeout_seconds"]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, FrozenSet

# ═════════════════════════════════════════════════════════════
# Immutable defaults container
# ═════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class GeoDefaults:
    """
    مقادیر پیش‌فرض تمام Geo Providers.

    Attributes:
        timeout_seconds: HTTP request timeout (پیش‌فرض).
        max_retries: حداکثر تعداد retry.
        backoff_base_seconds: زمان پایه backoff.
        backoff_multiplier: ضریب نمایی backoff.
        max_backoff_seconds: سقف زمان backoff.
        retryable_statuses: HTTP status codes قابل retry.
        user_agent: User-Agent header.
    """

    timeout_seconds: float = 10.0
    max_retries: int = 3
    backoff_base_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 30.0
    retryable_statuses: FrozenSet[int] = frozenset({429, 502, 503, 504})
    user_agent: str = "DIP-GeoClient/1.2"

    def to_dict(self) -> dict[str, Any]:
        """تبدیل به dict (برای استفاده در ProviderConfig.extra)."""
        return {
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "backoff_base_seconds": self.backoff_base_seconds,
            "backoff_multiplier": self.backoff_multiplier,
            "max_backoff_seconds": self.max_backoff_seconds,
            "retryable_statuses": self.retryable_statuses,
            "user_agent": self.user_agent,
        }


# ═════════════════════════════════════════════════════════════
# Singleton instance
# ═════════════════════════════════════════════════════════════

GEO_DEFAULTS = GeoDefaults()

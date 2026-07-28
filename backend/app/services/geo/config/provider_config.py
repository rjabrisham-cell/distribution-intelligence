"""
config/provider_config.py — Provider Configuration Loader
===========================================================
Contract v1.2

فقط Environment Variables را می‌خواند. هیچ Connection یا Validation
Provider انجام نمی‌دهد. هیچ وابستگی به clients/ یا adapters/ ندارد.

Dependency direction:
    config  ←  clients  ←  adapters   (correct)
    NOT:  config → clients  (wrong)

Naming convention for env vars:
    GEO_<PROVIDER>_BASE_URL          (mandatory)
    GEO_<PROVIDER>_API_KEY           (optional)
    GEO_<PROVIDER>_TIMEOUT           (optional, default from GeoDefaults)
    GEO_<PROVIDER>_MAX_RETRIES       (optional)
    GEO_<PROVIDER>_BACKOFF_BASE      (optional)
    GEO_<PROVIDER>_BACKOFF_MULTIPLIER(optional)
    GEO_<PROVIDER>_MAX_BACKOFF       (optional)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from app.services.geo.config.geo_defaults import GEO_DEFAULTS
from app.services.geo.exceptions.geo_exceptions import ConfigurationError

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════
# ProviderConfig (immutable, no clients dependency)
# ═════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ProviderConfig:
    """
    Immutable configuration for a single Geo provider.

    **هیچ وابستگی به RetryPolicy یا clients ندارد.**
    RetryPolicy باید در لایه Client از این مقادیر raw ساخته شود.

    Attributes:
        name: Provider identifier (e.g. 'fimap', 'nominatim').
        base_url: Normalized base URL (بدون trailing slash).
        timeout_seconds: HTTP request timeout (> 0).
        api_key: Optional API key / token (None اگر خالی باشد).
        retry_max_retries: Maximum retry attempts (≥ 0).
        retry_backoff_base_seconds: Base wait before first retry (> 0).
        retry_backoff_multiplier: Exponential multiplier (> 0).
        retry_max_backoff_seconds: Ceiling for backoff (> 0).
        extra: Arbitrary provider-specific key-value pairs.
    """

    name: str
    base_url: str
    timeout_seconds: float = GEO_DEFAULTS.timeout_seconds
    api_key: str | None = None
    retry_max_retries: int = GEO_DEFAULTS.max_retries
    retry_backoff_base_seconds: float = GEO_DEFAULTS.backoff_base_seconds
    retry_backoff_multiplier: float = GEO_DEFAULTS.backoff_multiplier
    retry_max_backoff_seconds: float = GEO_DEFAULTS.max_backoff_seconds
    extra: dict[str, Any] = field(default_factory=dict)

    def masked_api_key(self) -> str | None:
        """نمایش masked شده API Key برای Logging."""
        if not self.api_key:
            return None
        if len(self.api_key) <= 8:
            return "*" * len(self.api_key)
        return self.api_key[:8] + "*" * (len(self.api_key) - 8)

    def log_safe_dict(self) -> dict[str, Any]:
        """تبدیل به dict بدون افشای API Key (مناسب برای Log)."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "api_key": self.masked_api_key(),
            "retry_max_retries": self.retry_max_retries,
            "retry_backoff_base_seconds": self.retry_backoff_base_seconds,
            "retry_backoff_multiplier": self.retry_backoff_multiplier,
            "retry_max_backoff_seconds": self.retry_max_backoff_seconds,
        }


# ═════════════════════════════════════════════════════════════
# ProviderConfigLoader
# ═════════════════════════════════════════════════════════════

class ProviderConfigLoader:
    """
    Loads provider configuration from environment variables.

    Usage:
        loader = ProviderConfigLoader()
        config = loader.load("fimap")        # cached
        config = loader.load("nominatim")    # cached
    """

    _PREFIX = "GEO"

    # Regex for provider name validation
    _NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_\-]*$")

    # Regex for URL validation
    _URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)

    # Known standard keys (excluded from extra)
    _KNOWN_KEYS = {
        "BASE_URL",
        "API_KEY",
        "TIMEOUT",
        "MAX_RETRIES",
        "BACKOFF_BASE",
        "BACKOFF_MULTIPLIER",
        "MAX_BACKOFF",
    }

    # ═══════════════════════════════════════════════════════
    # Public API (cached)
    # ═══════════════════════════════════════════════════════

    @lru_cache(maxsize=32)
    def load(self, provider_name: str) -> ProviderConfig:
        """
        Load configuration for *provider_name* (cached).

        Args:
            provider_name: نام Provider (مثلاً 'fimap').

        Returns:
            ProviderConfig (immutable).

        Raises:
            ConfigurationError: اگر provider_name نامعتبر باشد یا
                                BASE_URL تنظیم نشده باشد.
        """
        self._validate_provider_name(provider_name)

        ns = provider_name.upper()

        # Mandatory
        base_url = self._read_base_url(ns)

        # Optional with defaults from GeoDefaults
        timeout = self._read_positive_float(
            f"{self._PREFIX}_{ns}_TIMEOUT",
            default=GEO_DEFAULTS.timeout_seconds,
            label="timeout",
        )

        api_key = self._read_api_key(ns)

        retry_max_retries = self._read_non_negative_int(
            f"{self._PREFIX}_{ns}_MAX_RETRIES",
            default=GEO_DEFAULTS.max_retries,
            label="max_retries",
        )

        retry_backoff_base = self._read_positive_float(
            f"{self._PREFIX}_{ns}_BACKOFF_BASE",
            default=GEO_DEFAULTS.backoff_base_seconds,
            label="backoff_base",
        )

        retry_backoff_multiplier = self._read_positive_float(
            f"{self._PREFIX}_{ns}_BACKOFF_MULTIPLIER",
            default=GEO_DEFAULTS.backoff_multiplier,
            label="backoff_multiplier",
        )

        retry_max_backoff = self._read_positive_float(
            f"{self._PREFIX}_{ns}_MAX_BACKOFF",
            default=GEO_DEFAULTS.max_backoff_seconds,
            label="max_backoff",
        )

        extra = self._collect_extra(ns)

        config = ProviderConfig(
            name=provider_name,
            base_url=base_url,
            timeout_seconds=timeout,
            api_key=api_key,
            retry_max_retries=retry_max_retries,
            retry_backoff_base_seconds=retry_backoff_base,
            retry_backoff_multiplier=retry_backoff_multiplier,
            retry_max_backoff_seconds=retry_max_backoff,
            extra=extra,
        )

        logger.debug(
            "Provider config loaded: %s",
            config.log_safe_dict(),
        )

        return config

    # ═══════════════════════════════════════════════════════
    # Private: Readers & Validators
    # ═══════════════════════════════════════════════════════

    def _read_base_url(self, ns: str) -> str:
        """خواندن و اعتبارسنجی BASE_URL."""
        key = f"{self._PREFIX}_{ns}_BASE_URL"
        raw = os.getenv(key)

        if raw is None or raw.strip() == "":
            raise ConfigurationError(
                f"Missing required environment variable: {key}"
            )

        url = raw.strip()

        # Validate URL scheme
        if not self._URL_PATTERN.match(url):
            raise ConfigurationError(
                f"{key} must start with http:// or https://, got: {url!r}"
            )

        # Normalize: remove trailing slash
        return url.rstrip("/")

    def _read_api_key(self, ns: str) -> str | None:
        """خواندن API_KEY (اگر خالی بود → None)."""
        key = f"{self._PREFIX}_{ns}_API_KEY"
        raw = os.getenv(key)
        if raw is None:
            return None
        cleaned = raw.strip()
        return cleaned if cleaned else None

    def _read_positive_float(self, key: str, *, default: float, label: str) -> float:
        """خواندن مقدار float مثبت."""
        raw = os.getenv(key)
        if raw is None:
            return default
        try:
            value = float(raw)
        except ValueError:
            raise ConfigurationError(
                f"{key} must be a number, got: {raw!r}"
            )
        if value <= 0:
            raise ConfigurationError(
                f"{key} ({label}) must be > 0, got: {value}"
            )
        return value

    def _read_non_negative_int(self, key: str, *, default: int, label: str) -> int:
        """خواندن مقدار int غیرمنفی."""
        raw = os.getenv(key)
        if raw is None:
            return default
        try:
            value = int(raw)
        except ValueError:
            raise ConfigurationError(
                f"{key} must be an integer, got: {raw!r}"
            )
        if value < 0:
            raise ConfigurationError(
                f"{key} ({label}) must be >= 0, got: {value}"
            )
        return value

    # ═══════════════════════════════════════════════════════
    # Private: Extra collection
    # ═══════════════════════════════════════════════════════

    def _collect_extra(self, ns: str) -> dict[str, Any]:
        """
        جمع‌آوری env varهای اضافی با prefix GEO_<NS>_

        فقط کلیدهایی که در لیست KNOWN نیستند جمع می‌شوند.
        کلیدها lowercase شده و prefix حذف می‌شود.
        """
        extra: dict[str, Any] = {}
        prefix = f"{self._PREFIX}_{ns}_"

        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue

            # Extract suffix
            suffix = key[len(prefix):]
            suffix_upper = suffix.upper()

            # Skip known keys
            if suffix_upper in self._KNOWN_KEYS:
                continue

            # Whitelist: only allow alphanumeric + underscore
            if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", suffix):
                logger.warning(
                    "Skipping extra env var with non-standard name: %s", key
                )
                continue

            extra[suffix.lower()] = value

        return extra

    @classmethod
    def _validate_provider_name(cls, name: str) -> None:
        """اعتبارسنجی provider name."""
        if not name or not name.strip():
            raise ConfigurationError("Provider name must not be empty.")
        if not cls._NAME_PATTERN.match(name):
            raise ConfigurationError(
                f"Invalid provider name: {name!r}. "
                f"Must start with a letter, then alphanumeric, dash, or underscore."
            )


# ═════════════════════════════════════════════════════════════
# Singleton loader
# ═════════════════════════════════════════════════════════════

@lru_cache()
def get_provider_config_loader() -> ProviderConfigLoader:
    """Singleton (cached) loader instance."""
    return ProviderConfigLoader()

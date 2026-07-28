"""
http_provider.py — HTTP-based Geo Provider
==========================================
Contract v1.0 (Frozen) — کاملاً Sync

Provider مبتنی بر HTTP که از یک Adapter برای ارتباط با سرویس خارجی استفاده می‌کند.
تمامی Exceptionهای خام HTTP به Exceptionهای دامنه Geo تبدیل می‌شوند.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Callable, TypeVar

import httpx

from app.services.geo.geo_models import CONTRACT_VERSION
from app.services.geo.geo_provider import GeoProvider
from app.services.geo.exceptions import (
    ProviderTimeoutError,
    ProviderConnectionError,
    ProviderServerError,
    ProviderRateLimitError,
    ProviderResponseError,
)

if TYPE_CHECKING:
    from app.services.geo.geo_models import (
        GeoAddress,
        GeoCoordinate,
        AddressValidationResult,
        GeoProviderCapability,
    )
    from app.services.geo.adapters.base_adapter import BaseGeoAdapter

logger = logging.getLogger(__name__)

T = TypeVar("T")


class HttpGeoProvider(GeoProvider):
    """
    Provider مبتنی بر HTTP (Sync).

    این Provider:
    - یک Adapter را از طریق DI دریافت می‌کند.
    - تمام متدهای Sync اینترفیس GeoProvider را پیاده‌سازی می‌کند.
    - تمام خطاهای HTTP/Network را به Exceptionهای دامنه تبدیل می‌کند.
    - از Logger استاندارد برای ثبت تمام عملیات استفاده می‌کند.
    """

    def __init__(self, adapter: BaseGeoAdapter):
        """
        Args:
            adapter: Adapter سازگار با BaseGeoAdapter (مثلاً FimapAdapter)
        """
        if adapter is None:
            raise ValueError("Adapter cannot be None")
        self._adapter = adapter

    # ═══════════════════════════════════════════════════════════
    # شناسنامه (Identification)
    # ═══════════════════════════════════════════════════════════

    @property
    def provider_name(self) -> str:
        return self._adapter.provider_name

    @property
    def provider_version(self) -> str:
        return self._adapter.provider_version

    @property
    def contract_version(self) -> str:
        return CONTRACT_VERSION

    @property
    def adapter_name(self) -> str:
        """نام Adapter فعلی."""
        return self._adapter.adapter_name

    # ═══════════════════════════════════════════════════════════
    # Internal — error handling (DRY refactor)
    # ═══════════════════════════════════════════════════════════

    def _execute_with_error_handling(
        self,
        operation_name: str,
        callable: Callable[[], T],
    ) -> T:
        """
        wrapper یکسان برای تمام فراخوانی‌های Adapter.

        ✅ اصلاح: بلوک try/except که قبلاً ۳ بار تکرار شده بود،
        حالا یکجا تعریف شده و همه متدها از آن استفاده می‌کنند.

        Args:
            operation_name: نام عملیات برای logging.
            callable: یک callable بدون آرگومان که عملیات اصلی را انجام می‌دهد.

        Returns:
            خروجی callable.

        Raises:
            ProviderTimeoutError, ProviderConnectionError,
            ProviderServerError, ProviderRateLimitError,
            ProviderResponseError
        """
        start = time.perf_counter()
        logger.info(f"[{self.provider_name}] {operation_name}: started")
        try:
            result = callable()
            elapsed = time.perf_counter() - start
            logger.info(
                f"[{self.provider_name}] {operation_name}: completed in {elapsed:.3f}s"
            )
            return result
        except httpx.TimeoutException as e:
            logger.error(f"[{self.provider_name}] Timeout in {operation_name}: {e}")
            raise ProviderTimeoutError(self.provider_name) from e
        except httpx.ConnectError as e:
            logger.error(f"[{self.provider_name}] Connection error in {operation_name}: {e}")
            raise ProviderConnectionError(self.provider_name) from e
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[{self.provider_name}] HTTP {e.response.status_code} in {operation_name}: {e}"
            )
            if e.response.status_code == 429:
                raise ProviderRateLimitError(
                    self.provider_name,
                    retry_after=e.response.headers.get("Retry-After"),
                ) from e
            if 500 <= e.response.status_code < 600:
                raise ProviderServerError(
                    self.provider_name, status_code=e.response.status_code
                ) from e
            raise ProviderResponseError(
                self.provider_name,
                status_code=e.response.status_code,
                message=str(e),
            ) from e
        except Exception as e:
            logger.error(
                f"[{self.provider_name}] Unexpected error in {operation_name}: {e}"
            )
            raise ProviderResponseError(self.provider_name, message=str(e)) from e

    # ═══════════════════════════════════════════════════════════
    # متدهای اصلی (Core — Frozen v1.0)
    # ═══════════════════════════════════════════════════════════

    def validate_address(self, address: GeoAddress) -> AddressValidationResult:
        """اعتبارسنجی آدرس با استفاده از Adapter (Sync)."""
        return self._execute_with_error_handling(
            "validate_address",
            lambda: self._adapter.validate_address(address),
        )

    def validate_coordinate(self, coordinate: GeoCoordinate) -> AddressValidationResult:
        """اعتبارسنجی مختصات با استفاده از Adapter (Sync)."""
        return self._execute_with_error_handling(
            "validate_coordinate",
            lambda: self._adapter.validate_coordinate(coordinate),
        )

    def reverse_geocode(self, coordinate: GeoCoordinate) -> GeoAddress | None:
        """تبدیل مختصات به آدرس (Sync)."""
        return self._execute_with_error_handling(
            "reverse_geocode",
            lambda: self._adapter.reverse_geocode(coordinate),
        )

    def health_check(self) -> bool:
        """بررسی سلامت (Sync)."""
        start = time.perf_counter()
        logger.info(f"[{self.provider_name}] health_check: started")
        try:
            result = self._adapter.health_check()
            elapsed = time.perf_counter() - start
            logger.info(
                f"[{self.provider_name}] health_check: completed in {elapsed:.3f}s "
                f"— {'healthy' if result else 'unhealthy'}"
            )
            return result
        except Exception as e:
            logger.error(f"[{self.provider_name}] health_check failed: {e}")
            return False

    def get_capabilities(self) -> GeoProviderCapability:
        """اعلام قابلیت‌های Adapter."""
        return self._adapter.get_capabilities()

    def get_supported_contract_version(self) -> str:
        """نسخه Contract پشتیبانی‌شده توسط این Provider."""
        return CONTRACT_VERSION

    # ═══════════════════════════════════════════════════════════
    # Dunder Methods
    # ═══════════════════════════════════════════════════════════

    def __str__(self) -> str:
        return (
            f"HttpGeoProvider(name={self.provider_name}, "
            f"version={self.provider_version}, adapter={self.adapter_name})"
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} adapter={self.adapter_name!r}>"

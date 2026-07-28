"""
base_adapter.py — Abstract Adapter Contract (Sync)
===================================================
Contract v1.2 — Decision: Sync (گزینه A)

کلاس پایه تمام Adapterها. پیاده‌ساز GeoProvider.
مدیریت httpx.Client (Sync)، Retry Policy، Exception Mapping
و Health Check پایه را متمرکز می‌کند.
"""

from __future__ import annotations

import time
import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Any

import httpx

from app.services.geo.geo_provider import GeoProvider
from app.services.geo.geo_models import (
    GeoAddress,
    GeoCoordinate,
    AddressValidationResult,
    GeoProviderCapability,
    CapabilityInfo,
    CapabilityLevel,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════

class GeoConnectionError(Exception):
    """خطای اتصال به سرویس خارجی Geo (شبکه، timeout، HTTP 5xx)."""

    def __init__(self, provider: str, detail: str):
        self.provider = provider
        self.detail = detail
        super().__init__(f"[{provider}] Connection failed: {detail}")


class GeoAdapterError(Exception):
    """خطای عمومی Adapter (mapping error, unexpected response, ...)."""

    def __init__(self, provider: str, detail: str):
        self.provider = provider
        self.detail = detail
        super().__init__(f"[{provider}] Adapter error: {detail}")


# ═══════════════════════════════════════════════════════════════════
# BaseGeoAdapter
# ═══════════════════════════════════════════════════════════════════

class BaseGeoAdapter(GeoProvider):
    """
    کلاس پایه تمام Adapterها — پیاده‌ساز GeoProvider.

    Responsibilities:
        - پیاده‌سازی GeoProvider Interface
        - مدیریت httpx.Client (Sync)
        - Timeout و Retry Policy (exponential backoff)
        - Exception Mapping → GeoConnectionError / GeoAdapterError
        - Health Check پایه
        - Logging استاندارد

    Adapterهای فرزند باید:
        1. endpointهای Provider خارجی را بدانند.
        2. پاسخ raw را به DTOهای استاندارد geo_models تبدیل کنند.
        3. متدهای abstract را override کنند.
    """

    # ═══════════════════════════════════════════════════════════
    # Constructor
    # ═══════════════════════════════════════════════════════════

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        timeout: float = 10.0,
        max_retries: int = 2,
    ):
        self._client = http_client or self._create_client(timeout)
        self._timeout = timeout
        self._max_retries = max_retries

    def _create_client(self, timeout: float) -> httpx.Client:
        return httpx.Client(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": "DIP-GeoAdapter/1.2"},
        )

    # ═══════════════════════════════════════════════════════════
    # Identification (GeoProvider)
    # ═══════════════════════════════════════════════════════════

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """نام یکتا Adapter (مثلاً 'fimap', 'nominatim')."""
        ...

    @property
    def provider_name(self) -> str:
        """نام Provider خارجی — پیش‌فرض برابر adapter_name."""
        return self.adapter_name

    @property
    @abstractmethod
    def provider_version(self) -> str:
        """نسخه Provider — مثلاً '1.0.0'."""
        ...

    @property
    def contract_version(self) -> str:
        """نسخه Contract — هماهنگ با CONTRACT_VERSION ریشه."""
        return "1.2"

    # ═══════════════════════════════════════════════════════════
    # Capabilities (override in child)
    # ═══════════════════════════════════════════════════════════

    def get_capabilities(self) -> GeoProviderCapability:
        """
        قابلیت‌های پیش‌فرض — Adapter فرزند باید override کند.

        Returns:
            GeoProviderCapability با تمام فیلدها روی CapabilityLevel.NONE.

        Note:
            فیلدهای معتبر: city_validation, street_validation, postal_code,
            reverse_geocode, coordinate_check  (مطابق Contract v1.2).
        """
        return GeoProviderCapability(
            city_validation=CapabilityInfo(
                level=CapabilityLevel.NONE,
                accuracy=0.0,
                coverage="unknown",
                notes="Override in child adapter",
            ),
            street_validation=CapabilityInfo(
                level=CapabilityLevel.NONE,
                accuracy=0.0,
                coverage="unknown",
                notes="Override in child adapter",
            ),
            postal_code=CapabilityInfo(
                level=CapabilityLevel.NONE,
                accuracy=0.0,
                coverage="unknown",
                notes="Override in child adapter",
            ),
            reverse_geocode=CapabilityInfo(
                level=CapabilityLevel.NONE,
                accuracy=0.0,
                coverage="unknown",
                notes="Override in child adapter",
            ),
            coordinate_check=CapabilityInfo(
                level=CapabilityLevel.NONE,
                accuracy=0.0,
                coverage="unknown",
                notes="Override in child adapter",
            ),
        )

    # ═══════════════════════════════════════════════════════════
    # GeoProvider: validate_address (abstract)
    # ═══════════════════════════════════════════════════════════

    @abstractmethod
    def validate_address(self, address: GeoAddress) -> AddressValidationResult:
        """اعتبارسنجی آدرس با Provider خارجی و تبدیل پاسخ به DTO."""
        ...

    # ═══════════════════════════════════════════════════════════
    # GeoProvider: validate_coordinate (abstract)
    # ═══════════════════════════════════════════════════════════

    @abstractmethod
    def validate_coordinate(self, coordinate: GeoCoordinate) -> AddressValidationResult:
        """اعتبارسنجی مختصات — آیا مختصات در محدوده معتبر است؟"""
        ...

    # ═══════════════════════════════════════════════════════════
    # GeoProvider: reverse_geocode (abstract)
    # ═══════════════════════════════════════════════════════════

    @abstractmethod
    def reverse_geocode(self, coordinate: GeoCoordinate) -> GeoAddress | None:
        """تبدیل مختصات به آدرس با Provider خارجی."""
        ...

    # ═══════════════════════════════════════════════════════════
    # Extended API: geocode (abstract — extension beyond GeoProvider)
    # ═══════════════════════════════════════════════════════════

    @abstractmethod
    def geocode(
        self, address_string: str, country: str | None = None
    ) -> list[GeoCoordinate]:
        """تبدیل آدرس متنی به مختصات (Forward Geocoding)."""
        ...

    # ═══════════════════════════════════════════════════════════
    # Extended API: search (abstract — extension beyond GeoProvider)
    # ═══════════════════════════════════════════════════════════

    @abstractmethod
    def search(
        self, query: str, country: str | None = None
    ) -> list[GeoAddress]:
        """جستجوی آزاد با Provider خارجی."""
        ...

    # ═══════════════════════════════════════════════════════════
    # Health Check (abstract)
    # ═══════════════════════════════════════════════════════════

    @abstractmethod
    def health_check(self) -> bool:
        """بررسی سلامت Provider خارجی."""
        ...

    # ═══════════════════════════════════════════════════════════
    # HTTP Helpers (protected)
    # ═══════════════════════════════════════════════════════════

    def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        """GET request با retry + exponential backoff."""
        last_exception: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.get(url, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                raise GeoConnectionError(
                    self.provider_name,
                    f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                )
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                if attempt < self._max_retries:
                    wait = 0.5 * (2 ** attempt)
                    time.sleep(wait)
                continue

        raise GeoConnectionError(
            self.provider_name,
            f"All {self._max_retries + 1} attempts failed: {last_exception}",
        )

    def _post(
        self,
        url: str,
        json_data: dict | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        """POST request با retry + exponential backoff."""
        last_exception: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.post(url, json=json_data, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                raise GeoConnectionError(
                    self.provider_name,
                    f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                )
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                if attempt < self._max_retries:
                    wait = 0.5 * (2 ** attempt)
                    time.sleep(wait)
                continue

        raise GeoConnectionError(
            self.provider_name,
            f"All {self._max_retries + 1} attempts failed: {last_exception}",
        )

    # ═══════════════════════════════════════════════════════════
    # Cleanup
    # ═══════════════════════════════════════════════════════════

    def close(self):
        """بستن HTTP Client (در صورت نیاز)."""
        if self._client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

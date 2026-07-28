"""
geoserver_adapter.py — GeoServer Adapter (Sync SKELETON)
==========================================================
Contract v1.2 — Decision: Sync (گزینه A)

Skeleton برای GeoServer (WFS/WMS) integration.

TODO Sprint 3:
    - پیاده‌سازی endpointها از Config
    - پیاده‌سازی validate_address, validate_coordinate, reverse_geocode
    - پیاده‌سازی geocode, search
    - تنظیم health_check واقعی
    - انتقال mapping logic به mappers/geoserver_mapper.py
"""

from __future__ import annotations

import logging

from app.services.geo.adapters.base_adapter import BaseGeoAdapter
from app.services.geo.geo_models import (
    GeoAddress,
    GeoCoordinate,
    AddressValidationResult,
    GeoProviderCapability,
    CapabilityInfo,
    CapabilityLevel,
)

logger = logging.getLogger(__name__)


class GeoServerAdapter(BaseGeoAdapter):
    """
    SKELETON — GeoServer integration.

    سرویس WMS / WFS برای visualisation و query لایه‌های برداری.
    """

    PROVIDER_VERSION = "0.1.0"

    def __init__(
        self,
        base_url: str = "",
        http_client=None,
        timeout: float = 10.0,
        max_retries: int = 2,
    ):
        super().__init__(
            http_client=http_client,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._base_url = base_url

    @property
    def adapter_name(self) -> str:
        return "geoserver"

    @property
    def provider_version(self) -> str:
        return self.PROVIDER_VERSION

    # ── GeoProvider ───────────────────────────────────────

    def validate_address(self, address: GeoAddress) -> AddressValidationResult:
        raise NotImplementedError("GeoServerAdapter.validate_address — Sprint 3")

    def validate_coordinate(self, coordinate: GeoCoordinate) -> AddressValidationResult:
        raise NotImplementedError("GeoServerAdapter.validate_coordinate — Sprint 3")

    def reverse_geocode(self, coordinate: GeoCoordinate) -> GeoAddress | None:
        raise NotImplementedError("GeoServerAdapter.reverse_geocode — Sprint 3")

    # ── Extended API ─────────────────────────────────────

    def geocode(
        self, address_string: str, country: str | None = None
    ) -> list[GeoCoordinate]:
        raise NotImplementedError("GeoServerAdapter.geocode — Sprint 3")

    def search(
        self, query: str, country: str | None = None
    ) -> list[GeoAddress]:
        raise NotImplementedError("GeoServerAdapter.search — Sprint 3")

    # ── Health Check ─────────────────────────────────────

    def health_check(self) -> bool:
        # TODO Sprint 3: health check واقعی
        return True

    # ── Capabilities ─────────────────────────────────────

    def get_capabilities(self) -> GeoProviderCapability:
        """
        قابلیت‌های GeoServer — SKELETON (همه NONE).
        TODO Sprint 3: مقداردهی واقعی.
        """
        return GeoProviderCapability(
            city_validation=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="iran",
                notes="GeoServer WFS — Sprint 3",
            ),
            street_validation=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="iran",
                notes="GeoServer WFS — Sprint 3",
            ),
            postal_code=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="iran",
                notes="GeoServer WFS — Sprint 3",
            ),
            reverse_geocode=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="iran",
                notes="GeoServer WMS — Sprint 3",
            ),
            coordinate_check=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="iran",
                notes="GeoServer WFS — Sprint 3",
            ),
        )

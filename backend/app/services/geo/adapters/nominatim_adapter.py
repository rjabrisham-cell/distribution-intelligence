"""
nominatim_adapter.py — Nominatim Adapter (Sync SKELETON)
==========================================================
Contract v1.2 — Decision: Sync (گزینه A)

Skeleton برای Nominatim (OpenStreetMap) integration.

TODO Sprint 3:
    - تنظیم endpointها (https://nominatim.openstreetmap.org)
    - رعایت Rate Limiting و User-Agent Policy
    - پیاده‌سازی متدها
    - انتقال mapping logic به mappers/nominatim_mapper.py
"""

from __future__ import annotations

import logging

import httpx

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


class NominatimAdapter(BaseGeoAdapter):
    """
    SKELETON — Nominatim geocoding integration.
    """

    PROVIDER_VERSION = "0.1.0"

    def __init__(
        self,
        base_url: str = "https://nominatim.openstreetmap.org",
        http_client: httpx.Client | None = None,
        timeout: float = 10.0,
        max_retries: int = 2,
    ):
        super().__init__(
            http_client=http_client,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._base_url = base_url.rstrip("/")

    @property
    def adapter_name(self) -> str:
        return "nominatim"

    @property
    def provider_version(self) -> str:
        return self.PROVIDER_VERSION

    # ── GeoProvider ───────────────────────────────────────

    def validate_address(self, address: GeoAddress) -> AddressValidationResult:
        raise NotImplementedError("NominatimAdapter.validate_address — Sprint 3")

    def validate_coordinate(self, coordinate: GeoCoordinate) -> AddressValidationResult:
        raise NotImplementedError("NominatimAdapter.validate_coordinate — Sprint 3")

    def reverse_geocode(self, coordinate: GeoCoordinate) -> GeoAddress | None:
        raise NotImplementedError("NominatimAdapter.reverse_geocode — Sprint 3")

    # ── Extended API ──────────────────────────────────────

    def geocode(
        self, address_string: str, country: str | None = None
    ) -> list[GeoCoordinate]:
        raise NotImplementedError("NominatimAdapter.geocode — Sprint 3")

    def search(
        self, query: str, country: str | None = None
    ) -> list[GeoAddress]:
        raise NotImplementedError("NominatimAdapter.search — Sprint 3")

    # ── Health Check ─────────────────────────────────────

    def health_check(self) -> bool:
        # TODO Sprint 3: health check واقعی
        try:
            url = f"{self._base_url}/status"
            response = self._client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    # ── Capabilities ─────────────────────────────────────

    def get_capabilities(self) -> GeoProviderCapability:
        """
        قابلیت‌های Nominatim — SKELETON (همه NONE).
        TODO Sprint 3: مقداردهی واقعی.
        """
        return GeoProviderCapability(
            city_validation=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="world",
                notes="Nominatim — Sprint 3",
            ),
            street_validation=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="world",
                notes="Nominatim — Sprint 3",
            ),
            postal_code=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="world",
                notes="Nominatim — Sprint 3",
            ),
            reverse_geocode=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="world",
                notes="Nominatim reverse — Sprint 3",
            ),
            coordinate_check=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="world",
                notes="Nominatim — Sprint 3",
            ),
        )

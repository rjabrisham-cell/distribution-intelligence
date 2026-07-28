"""
photon_adapter.py — Photon Adapter (Sync SKELETON)
====================================================
Contract v1.2 — Decision: Sync (گزینه A)

Skeleton برای Photon (Komoot) integration.

TODO Sprint 3:
    - تنظیم endpointها (https://photon.komoot.io)
    - پیاده‌سازی متدها (autocomplete geocoding)
    - انتقال mapping logic به mappers/photon_mapper.py
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


class PhotonAdapter(BaseGeoAdapter):
    """
    SKELETON — Photon (Komoot) geocoding / autocomplete integration.
    """

    PROVIDER_VERSION = "0.1.0"

    def __init__(
        self,
        base_url: str = "https://photon.komoot.io",
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
        return "photon"

    @property
    def provider_version(self) -> str:
        return self.PROVIDER_VERSION

    # ── GeoProvider ───────────────────────────────────────

    def validate_address(self, address: GeoAddress) -> AddressValidationResult:
        raise NotImplementedError("PhotonAdapter.validate_address — Sprint 3")

    def validate_coordinate(self, coordinate: GeoCoordinate) -> AddressValidationResult:
        raise NotImplementedError("PhotonAdapter.validate_coordinate — Sprint 3")

    def reverse_geocode(self, coordinate: GeoCoordinate) -> GeoAddress | None:
        raise NotImplementedError("PhotonAdapter.reverse_geocode — Sprint 3")

    # ── Extended API ─────────────────────────────────────

    def geocode(
        self, address_string: str, country: str | None = None
    ) -> list[GeoCoordinate]:
        raise NotImplementedError("PhotonAdapter.geocode — Sprint 3")

    def search(
        self, query: str, country: str | None = None
    ) -> list[GeoAddress]:
        raise NotImplementedError("PhotonAdapter.search — Sprint 3")

    # ── Health Check ─────────────────────────────────────

    def health_check(self) -> bool:
        # TODO Sprint 3: health check واقعی
        try:
            url = f"{self._base_url}/api/"
            response = self._client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    # ── Capabilities ─────────────────────────────────────

    def get_capabilities(self) -> GeoProviderCapability:
        """
        قابلیت‌های Photon — SKELETON (همه NONE).
        TODO Sprint 3: مقداردهی واقعی.
        """
        return GeoProviderCapability(
            city_validation=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="world",
                notes="Photon autocomplete — Sprint 3",
            ),
            street_validation=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="world",
                notes="Photon autocomplete — Sprint 3",
            ),
            postal_code=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="world",
                notes="Photon autocomplete — Sprint 3",
            ),
            reverse_geocode=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="world",
                notes="Photon reverse — Sprint 3",
            ),
            coordinate_check=CapabilityInfo(
                level=CapabilityLevel.NONE,
                coverage="world",
                notes="Photon — Sprint 3",
            ),
        )

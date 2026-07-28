"""
fimap_adapter.py — Adapter for Fimap Provider (Sync)
=====================================================
Contract v1.2 — Decision: Sync (گزینه A)

Adapter برای سرویس Fimap (PHP/SQLite3, OSRM, TileServer-PHP, GeoServer).
پاسخ raw Fimap را به DTOهای استاندارد geo_models تبدیل می‌کند.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.geo.adapters.base_adapter import (
    BaseGeoAdapter,
    GeoConnectionError,
    GeoAdapterError,
)
from app.services.geo.geo_models import (
    GeoAddress,
    GeoCoordinate,
    AddressValidationResult,
    FieldValidationResult,
    GeoProviderCapability,
    CapabilityInfo,
    CapabilityLevel,
)

logger = logging.getLogger(__name__)


class FimapAdapter(BaseGeoAdapter):
    """
    Adapter برای Fimap.

    این Adapter:
        - endpointهای Fimap را می‌داند.
        - پاسخ raw Fimap را به DTOهای استاندارد تبدیل می‌کند.
        - مدیریت HTTP را به BaseGeoAdapter واگذار می‌کند.
    """

    PROVIDER_VERSION = "1.0.0"

    def __init__(
        self,
        base_url: str,
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

    # ═══════════════════════════════════════════════════════════
    # Identification
    # ═══════════════════════════════════════════════════════════

    @property
    def adapter_name(self) -> str:
        return "fimap"

    @property
    def provider_version(self) -> str:
        return self.PROVIDER_VERSION

    # ═══════════════════════════════════════════════════════════
    # GeoProvider: validate_address
    # ═══════════════════════════════════════════════════════════

    def validate_address(self, address: GeoAddress) -> AddressValidationResult:
        """
        اعتبارسنجی آدرس با Fimap.

        Endpoint: POST {base_url}/api/validate
        """
        url = f"{self._base_url}/api/validate"
        payload = self._address_to_payload(address)

        try:
            response = self._post(url, json_data=payload)
            data = response.json()
            return self._parse_validation_response(data)
        except GeoConnectionError:
            raise
        except Exception as e:
            logger.exception("Fimap validate_address failed")
            raise GeoAdapterError(self.provider_name, str(e))

    # ═══════════════════════════════════════════════════════════
    # GeoProvider: validate_coordinate
    # ═══════════════════════════════════════════════════════════

    def validate_coordinate(self, coordinate: GeoCoordinate) -> AddressValidationResult:
        """
        اعتبارسنجی محدوده مختصات با Fimap.

        Endpoint: POST {base_url}/api/validate/coordinate
        """
        url = f"{self._base_url}/api/validate/coordinate"
        payload = {
            "latitude": coordinate.latitude,
            "longitude": coordinate.longitude,
        }

        try:
            response = self._post(url, json_data=payload)
            data = response.json()
            return self._parse_coordinate_validation(data)
        except GeoConnectionError:
            raise
        except Exception as e:
            logger.exception("Fimap validate_coordinate failed")
            raise GeoAdapterError(self.provider_name, str(e))

    # ═══════════════════════════════════════════════════════════
    # Extended API: geocode
    # ═══════════════════════════════════════════════════════════

    def geocode(
        self, address_string: str, country: str | None = None
    ) -> list[GeoCoordinate]:
        """
        تبدیل آدرس متنی به مختصات با Fimap (Forward Geocoding).

        Endpoint: GET {base_url}/api/geocode?q=...
        """
        url = f"{self._base_url}/api/geocode"
        params: dict[str, str] = {"q": address_string}
        if country:
            params["country"] = country

        try:
            response = self._get(url, params=params)
            data = response.json()
            return self._parse_geocode_response(data)
        except GeoConnectionError:
            raise
        except Exception as e:
            logger.exception("Fimap geocode failed")
            raise GeoAdapterError(self.provider_name, str(e))

    # ═══════════════════════════════════════════════════════════
    # GeoProvider: reverse_geocode
    # ═══════════════════════════════════════════════════════════

    def reverse_geocode(self, coordinate: GeoCoordinate) -> GeoAddress | None:
        """
        تبدیل مختصات به آدرس با Fimap.

        Endpoint: GET {base_url}/api/reverse?lat=...&lon=...
        """
        url = f"{self._base_url}/api/reverse"
        params = {"lat": coordinate.latitude, "lon": coordinate.longitude}

        try:
            response = self._get(url, params=params)
            data = response.json()
            return self._parse_reverse_geocode_response(data)
        except GeoConnectionError:
            raise
        except Exception as e:
            logger.exception("Fimap reverse_geocode failed")
            return None

    # ═══════════════════════════════════════════════════════════
    # Extended API: search
    # ═══════════════════════════════════════════════════════════

    def search(
        self, query: str, country: str | None = None
    ) -> list[GeoAddress]:
        """
        جستجوی آزاد با Fimap.

        Endpoint: GET {base_url}/api/search?q=...
        """
        url = f"{self._base_url}/api/search"
        params: dict[str, str] = {"q": query}
        if country:
            params["country"] = country

        try:
            response = self._get(url, params=params)
            data = response.json()
            return self._parse_search_response(data)
        except GeoConnectionError:
            raise
        except Exception as e:
            logger.exception("Fimap search failed")
            raise GeoAdapterError(self.provider_name, str(e))

    # ═══════════════════════════════════════════════════════════
    # Health Check
    # ═══════════════════════════════════════════════════════════

    def health_check(self) -> bool:
        """بررسی سلامت Fimap — GET {base_url}/api/health."""
        url = f"{self._base_url}/api/health"
        try:
            response = self._client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    # ═══════════════════════════════════════════════════════════
    # Capabilities
    # ═══════════════════════════════════════════════════════════

    def get_capabilities(self) -> GeoProviderCapability:
        """
        اعلام قابلیت‌های Fimap به صورت استاندارد (Contract v1.2).
        """
        return GeoProviderCapability(
            city_validation=CapabilityInfo(
                level=CapabilityLevel.FULL,
                accuracy=0.95,
                coverage="iran",
                notes="پشتیبانی کامل از استان و شهر ایران — مبتنی بر OSRM",
            ),
            street_validation=CapabilityInfo(
                level=CapabilityLevel.BASIC,
                accuracy=0.85,
                coverage="iran",
                notes="اعتبارسنجی خیابان — پوشش متغیر بر اساس منطقه",
            ),
            postal_code=CapabilityInfo(
                level=CapabilityLevel.NONE,
                accuracy=0.0,
                coverage="iran",
                notes="اعتبارسنجی کد پستی — در دست پیاده‌سازی",
            ),
            reverse_geocode=CapabilityInfo(
                level=CapabilityLevel.FULL,
                accuracy=0.90,
                coverage="iran",
                notes="Reverse geocode از طریق OSRM nearest point",
            ),
            coordinate_check=CapabilityInfo(
                level=CapabilityLevel.FULL,
                accuracy=0.99,
                coverage="iran",
                notes="بررسی محدوده مختصات در پلیگون ایران",
            ),
        )

    # ═══════════════════════════════════════════════════════════
    # Private: Payload Builders
    # ═══════════════════════════════════════════════════════════

    def _address_to_payload(self, address: GeoAddress) -> dict[str, str]:
        """تبدیل GeoAddress به payload Fimap API."""
        payload: dict[str, str] = {}
        if address.province:
            payload["province"] = address.province
        if address.city:
            payload["city"] = address.city
        if address.district:
            payload["district"] = address.district
        if address.neighbourhood:
            payload["neighbourhood"] = address.neighbourhood
        if address.street:
            payload["street"] = address.street
        if address.alley:
            payload["alley"] = address.alley
        if address.building_name:
            payload["building_name"] = address.building_name
        if address.postal_code:
            payload["postal_code"] = address.postal_code
        return payload

    # ═══════════════════════════════════════════════════════════
    # Private: Response Parsers
    # TODO Sprint 3: انتقال به mappers/fimap_mapper.py
    # ═══════════════════════════════════════════════════════════

    # ── Field name mapping: Fimap API key → GeoAddress field ──
    _FIELD_NAMES = [
        "province",
        "city",
        "district",
        "neighbourhood",
        "street",
        "alley",
        "building_name",
        "postal_code",
    ]

    def _parse_validation_response(
        self, data: dict[str, Any]
    ) -> AddressValidationResult:
        """
        تبدیل پاسخ validate_address Fimap → AddressValidationResult.

        ساختار پاسخ Fimap:
        {
            "fields": {
                "province": {"exists": bool, "confidence": float, "normalized": str},
                "city":     {...},
                ...
            },
            "overall_match": bool,
            "overall_confidence": float
        }
        """
        raw_fields = data.get("fields", {}) if isinstance(data, dict) else {}
        fields: dict[str, FieldValidationResult] = {}

        for field_name in self._FIELD_NAMES:
            fdata = raw_fields.get(field_name, {}) if isinstance(raw_fields, dict) else {}
            fields[field_name] = FieldValidationResult(
                field_name=field_name,
                exists=fdata.get("exists", False),
                confidence=fdata.get("confidence", 0.0),
                value=fdata.get("normalized"),
                message="",
            )

        is_valid = data.get("overall_match", False) if isinstance(data, dict) else False
        overall_score = (data.get("overall_confidence", 0.0) if isinstance(data, dict) else 0.0) * 100.0

        return AddressValidationResult(
            provider_name=self.provider_name,
            fields=fields,
            is_valid=is_valid,
            overall_score=overall_score,
            raw_response=str(data),
        )

    def _parse_coordinate_validation(
        self, data: dict[str, Any]
    ) -> AddressValidationResult:
        """
        تبدیل پاسخ validate_coordinate Fimap → AddressValidationResult.

        ساختار پاسخ: {"valid": bool, "confidence": float}
        """
        is_valid = data.get("valid", False) if isinstance(data, dict) else False
        confidence = data.get("confidence", 0.0) if isinstance(data, dict) else 0.0

        return AddressValidationResult(
            provider_name=self.provider_name,
            fields={},
            is_valid=is_valid,
            overall_score=confidence * 100.0,
            raw_response=str(data),
        )

    def _parse_geocode_response(
        self, data: dict[str, Any]
    ) -> list[GeoCoordinate]:
        """
        تبدیل پاسخ geocode Fimap → list[GeoCoordinate].

        ساختار پاسخ:
        {"results": [{"lat": float, "lon": float}, ...]}
        """
        results = data.get("results", []) if isinstance(data, dict) else []
        coords: list[GeoCoordinate] = []
        for r in results:
            coords.append(
                GeoCoordinate(
                    latitude=r["lat"],
                    longitude=r["lon"],
                )
            )
        return coords

    def _parse_reverse_geocode_response(
        self, data: dict[str, Any]
    ) -> GeoAddress | None:
        """
        تبدیل پاسخ reverse_geocode Fimap → GeoAddress.

        ساختار پاسخ:
        {
            "found": bool,
            "province": str, "city": str, "district": str,
            "neighbourhood": str, "street": str, "alley": str,
            "building_name": str, "postal_code": str,
            "full_address": str
        }
        """
        if not data.get("found", False):
            return None
        return GeoAddress(
            province=data.get("province"),
            city=data.get("city"),
            district=data.get("district"),
            neighbourhood=data.get("neighbourhood"),
            street=data.get("street"),
            alley=data.get("alley"),
            building_name=data.get("building_name"),
            postal_code=data.get("postal_code"),
            full_address=data.get("full_address"),
        )

    def _parse_search_response(
        self, data: dict[str, Any]
    ) -> list[GeoAddress]:
        """
        تبدیل پاسخ search Fimap → list[GeoAddress].

        ساختار پاسخ:
        {"results": [{"province": str, "city": str, ...}, ...]}
        """
        results = data.get("results", []) if isinstance(data, dict) else []
        addresses: list[GeoAddress] = []
        for r in results:
            addresses.append(
                GeoAddress(
                    province=r.get("province"),
                    city=r.get("city"),
                    district=r.get("district"),
                    neighbourhood=r.get("neighbourhood"),
                    street=r.get("street"),
                    alley=r.get("alley"),
                    building_name=r.get("building_name"),
                    postal_code=r.get("postal_code"),
                    full_address=r.get("full_address"),
                )
            )
        return addresses

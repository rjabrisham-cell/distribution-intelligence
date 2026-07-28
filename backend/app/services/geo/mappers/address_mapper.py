# mappers/address_mapper.py
"""
Canonical address mapper for all Geo providers.
Contract v1.2 (FROZEN)

Transforms raw provider-specific address representations into the
standardised DTOs defined in geo_models:
    - GeoAddress
    - GeoCoordinate
    - AddressValidationResult

Mappers ONLY do mapping — no business validation, no scoring, no provider knowledge.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from app.services.geo.geo_models import (
    GeoAddress,
    GeoCoordinate,
    AddressValidationResult,
)
from app.services.geo.exceptions.geo_exceptions import MappingError

logger = logging.getLogger(__name__)


# ── Raw input model (provider-agnostic) ───────────────────────────

@dataclass(frozen=True)
class RawAddress:
    """
    Normalised intermediate representation of a provider address response.

    Every adapter must convert its provider-specific JSON into this
    structure before the mapper can produce a GeoAddress (FROZEN v1.2).

    Fields map directly to GeoAddress:
        province    → GeoAddress.province
        city        → GeoAddress.city
        region      → GeoAddress.district
        street      → GeoAddress.street
        postal_code → GeoAddress.postal_code
        raw_address → GeoAddress.full_address
        latitude    → GeoCoordinate.latitude  (converted to Decimal)
        longitude   → GeoCoordinate.longitude (converted to Decimal)

    Any provider-specific fields that do NOT map to FROZEN GeoAddress
    should be placed in `extra`.
    """

    province: str | None = None
    city: str | None = None
    region: str | None = None
    street: str | None = None
    postal_code: str | None = None
    raw_address: str | None = None

    latitude: float | None = None
    longitude: float | None = None

    extra: dict[str, Any] = field(default_factory=dict)


# ── Protocol for injectable transformation strategies ────────────

class AddressMappingStrategy(Protocol):
    """
    Protocol for optional per-field transformation hooks.

    Adapters can inject a custom strategy to normalise provider-specific
    values before they enter the canonical DTO.
    """

    def clamp_confidence(self, raw_value: Any) -> float:
        """Normalise and clamp a confidence value to [0.0, 1.0]."""
        ...

    def normalise_province(self, raw: str | None) -> str | None:
        """Normalise province name (e.g. remove province suffix)."""
        ...

    def normalise_city(self, raw: str | None) -> str | None:
        """Normalise city name."""
        ...


# ── Mapper ───────────────────────────────────────────────────────

class AddressMapper:
    """
    Transforms RawAddress → GeoAddress / GeoCoordinate.
    Contract v1.2 (FROZEN)

    Usage:
        mapper = AddressMapper(strategy=my_strategy)
        geo_addr = mapper.to_geo_address(raw)
        coord    = mapper.to_geo_coordinate(raw)
    """

    # Fields that identify an address (must have at least one)
    _IDENTIFIABLE_FIELDS = ("province", "city", "region", "street", "postal_code", "raw_address")

    def __init__(self, strategy: AddressMappingStrategy | None = None) -> None:
        self._strategy = strategy

    # ── public API ───────────────────────────────────────────────

    def to_geo_address(self, raw: RawAddress) -> GeoAddress:
        """
        Convert a RawAddress into a canonical GeoAddress (FROZEN v1.2).

        Maps:
            province    → GeoAddress.province
            city        → GeoAddress.city
            region      → GeoAddress.district
            street      → GeoAddress.street
            postal_code → GeoAddress.postal_code
            raw_address → GeoAddress.full_address

        NOTE: GeoAddress has NO coordinate field (FROZEN v1.2).
              Use to_geo_coordinate() separately for lat/lon.

        Raises:
            MappingError: if NO identifiable text fields are present
                          (i.e. the result would be an empty address).
        """
        # ── Validate: at least one identifiable field ─────────
        if not self._has_identifiable_fields(raw):
            raise MappingError(
                "Cannot create GeoAddress: no identifiable text fields present.",
                source_type="RawAddress",
                target_type="GeoAddress",
                details={
                    "raw_province": raw.province,
                    "raw_city": raw.city,
                    "raw_region": raw.region,
                    "raw_street": raw.street,
                    "raw_postal_code": raw.postal_code,
                    "raw_address": raw.raw_address,
                },
            )

        return GeoAddress(
            province=self._normalise_province(raw.province),
            city=self._normalise_city(raw.city),
            district=raw.region,
            street=raw.street,
            postal_code=raw.postal_code,
            full_address=raw.raw_address,
        )

    def to_geo_coordinate(self, raw: RawAddress) -> GeoCoordinate:
        """
        Extract a GeoCoordinate from a RawAddress.

        Raises:
            MappingError: if lat/lon are missing or invalid.
        """
        if raw.latitude is None or raw.longitude is None:
            raise MappingError(
                "Cannot create GeoCoordinate: latitude and/or longitude is None.",
                source_type="RawAddress",
                target_type="GeoCoordinate",
                details={"raw_lat": raw.latitude, "raw_lon": raw.longitude},
            )
        return self._make_coordinate(raw)

    def to_validation_result(
        self,
        *,
        provider_name: str,
        province_exists: bool = False,
        province_confidence: float = 0.0,
        city_exists: bool = False,
        city_confidence: float = 0.0,
        region_exists: bool = False,
        region_confidence: float = 0.0,
        street_exists: bool = False,
        street_confidence: float = 0.0,
        postal_code_valid: bool = False,
        postal_confidence: float = 0.0,
        coordinate_valid: bool = False,
        coordinate_confidence: float = 0.0,
        warnings: tuple[str, ...] = (),
    ) -> AddressValidationResult:
        """
        Build an AddressValidationResult (FROZEN v1.2).

        All confidence values are clamped to [0.0, 1.0].
        """
        return AddressValidationResult(
            provider_name=provider_name,
            province_exists=province_exists,
            province_confidence=self._clamp_confidence(province_confidence),
            city_exists=city_exists,
            city_confidence=self._clamp_confidence(city_confidence),
            region_exists=region_exists,
            region_confidence=self._clamp_confidence(region_confidence),
            street_exists=street_exists,
            street_confidence=self._clamp_confidence(street_confidence),
            postal_code_valid=postal_code_valid,
            postal_confidence=self._clamp_confidence(postal_confidence),
            coordinate_valid=coordinate_valid,
            coordinate_confidence=self._clamp_confidence(coordinate_confidence),
            warnings=warnings,
        )

    def to_address_list(self, raw_list: list[RawAddress]) -> list[GeoAddress]:
        """Bulk conversion.  Un-mappable items are logged and skipped."""
        result: list[GeoAddress] = []
        for i, raw in enumerate(raw_list):
            try:
                result.append(self.to_geo_address(raw))
            except MappingError as exc:
                logger.debug(
                    "Skipping RawAddress[%d] in bulk conversion: %s", i, exc.message
                )
        return result

    def to_coordinate_list(self, raw_list: list[RawAddress]) -> list[GeoCoordinate]:
        """Bulk conversion of coordinates.  Un-mappable items logged & skipped."""
        result: list[GeoCoordinate] = []
        for i, raw in enumerate(raw_list):
            try:
                result.append(self.to_geo_coordinate(raw))
            except MappingError as exc:
                logger.debug(
                    "Skipping RawAddress[%d] coordinate in bulk conversion: %s",
                    i,
                    exc.message,
                )
        return result

    # ── internal helpers ─────────────────────────────────────────

    @staticmethod
    def _has_identifiable_fields(raw: RawAddress) -> bool:
        """Check that at least one text field has a non-empty value."""
        for field_name in AddressMapper._IDENTIFIABLE_FIELDS:
            value = getattr(raw, field_name, None)
            if value is not None and str(value).strip():
                return True
        return False

    @staticmethod
    def _make_coordinate(raw: RawAddress) -> GeoCoordinate:
        """
        Build a GeoCoordinate from RawAddress lat/lon.

        Converts float → Decimal for FROZEN contract compliance.

        Pre-condition: raw.latitude and raw.longitude are NOT None
                       and are valid finite numbers.

        Raises:
            MappingError: if Decimal conversion fails (NaN, Inf, etc.).
        """
        try:
            return GeoCoordinate(
                latitude=Decimal(str(raw.latitude)),
                longitude=Decimal(str(raw.longitude)),
            )
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise MappingError(
                "Invalid coordinate values — cannot convert to Decimal.",
                source_type="RawAddress",
                target_type="GeoCoordinate",
                details={
                    "raw_lat": raw.latitude,
                    "raw_lon": raw.longitude,
                    "error": str(exc),
                },
            ) from exc

    def _maybe_make_coordinate(self, raw: RawAddress) -> GeoCoordinate | None:
        """
        Build a GeoCoordinate if lat/lon are present; otherwise None.

        Lenient variant — missing coordinates are NOT an error
        (unlike to_geo_coordinate which mandates them).
        """
        if raw.latitude is None or raw.longitude is None:
            return None
        return self._make_coordinate(raw)

    def _normalise_province(self, raw: str | None) -> str | None:
        if self._strategy and raw is not None:
            return self._strategy.normalise_province(raw)
        return raw

    def _normalise_city(self, raw: str | None) -> str | None:
        if self._strategy and raw is not None:
            return self._strategy.normalise_city(raw)
        return raw

    def _clamp_confidence(self, value: float) -> float:
        """Clamp confidence to [0.0, 1.0]."""
        if self._strategy:
            return self._strategy.clamp_confidence(value)
        return max(0.0, min(1.0, value))

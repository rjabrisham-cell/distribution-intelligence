# mappers/capability_mapper.py
"""
Capability mapper for Geo providers.
Contract v1.2 (FROZEN)

Converts provider-specific capability / feature metadata into the
canonical GeoProviderCapability DTO using CapabilityInfo (NOT booleans).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.geo.geo_models import (
    CapabilityInfo,
    CapabilityLevel,
    GeoProviderCapability,
)
from app.services.geo.exceptions.geo_exceptions import MappingError


@dataclass(frozen=True)
class RawCapability:
    """
    Normalised intermediate representation of a provider's capabilities.

    Each adapter fills this from its provider's metadata / status endpoint.
    Each field is a CapabilityInfo — NOT a boolean.

    Maps to GeoProviderCapability (FROZEN v1.2):
        city_validation      → GeoProviderCapability.city_validation
        street_validation    → GeoProviderCapability.street_validation
        postal_code_validation → GeoProviderCapability.postal_code
        reverse_geocode      → GeoProviderCapability.reverse_geocode
        coordinate_validation → GeoProviderCapability.coordinate_check

    Fields NOT in FROZEN GeoProviderCapability (dropped silently):
        province_validation, region_validation, geocode
    """

    provider_name: str

    province_validation: CapabilityInfo = field(default_factory=CapabilityInfo)
    city_validation: CapabilityInfo = field(default_factory=CapabilityInfo)
    region_validation: CapabilityInfo = field(default_factory=CapabilityInfo)
    postal_code_validation: CapabilityInfo = field(default_factory=CapabilityInfo)
    street_validation: CapabilityInfo = field(default_factory=CapabilityInfo)
    coordinate_validation: CapabilityInfo = field(default_factory=CapabilityInfo)
    geocode: CapabilityInfo = field(default_factory=CapabilityInfo)
    reverse_geocode: CapabilityInfo = field(default_factory=CapabilityInfo)


class CapabilityMapper:
    """
    Transforms RawCapability → GeoProviderCapability (FROZEN v1.2).

    Usage:
        mapper = CapabilityMapper()
        capability = mapper.to_capability(raw)
    """

    def to_capability(self, raw: RawCapability) -> GeoProviderCapability:
        """
        Convert RawCapability into a canonical GeoProviderCapability.

        Only maps fields that exist in the FROZEN model:
            city_validation, street_validation, postal_code,
            reverse_geocode, coordinate_check

        Raises:
            MappingError: if provider_name is empty.
        """
        if not raw.provider_name.strip():
            raise MappingError(
                "provider_name is required for RawCapability.",
                source_type="RawCapability",
                target_type="GeoProviderCapability",
            )

        return GeoProviderCapability(
            city_validation=raw.city_validation,
            street_validation=raw.street_validation,
            postal_code=raw.postal_code_validation,
            reverse_geocode=raw.reverse_geocode,
            coordinate_check=raw.coordinate_validation,
        )

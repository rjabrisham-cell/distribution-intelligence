# tests/test_mappers.py
"""Unit tests for Geo mappers — aligned with FROZEN v1.2 models."""

import pytest
from decimal import Decimal

from app.services.geo.mappers.address_mapper import AddressMapper, RawAddress
from app.services.geo.mappers.capability_mapper import CapabilityMapper, RawCapability
from app.services.geo.geo_models import (
    CapabilityInfo,
    CapabilityLevel,
    GeoCoordinate,
)
from app.services.geo.exceptions.geo_exceptions import MappingError


class TestAddressMapperToGeoAddress:
    """Tests for RawAddress → GeoAddress mapping."""

    def test_maps_full_address(self):
        """All text fields present → maps correctly."""
        raw = RawAddress(
            province="Tehran",
            city="Tehran",
            region="District 6",
            street="Valiasr Ave",
            postal_code="1234567890",
            raw_address="Valiasr Ave, District 6, Tehran",
        )
        result = AddressMapper().to_geo_address(raw)
        assert result.province == "Tehran"
        assert result.city == "Tehran"
        assert result.district == "District 6"
        assert result.street == "Valiasr Ave"
        assert result.postal_code == "1234567890"
        assert result.full_address == "Valiasr Ave, District 6, Tehran"

    def test_maps_partial_address(self):
        """Only city + street → still valid."""
        raw = RawAddress(city="Mashhad", street="Imam Reza St")
        result = AddressMapper().to_geo_address(raw)
        assert result.city == "Mashhad"
        assert result.street == "Imam Reza St"
        assert result.province is None
        assert result.district is None

    def test_raises_when_no_identifiable_fields(self):
        """Only lat/lon, no text → MappingError."""
        raw = RawAddress(latitude=35.6892, longitude=51.3890)
        with pytest.raises(MappingError, match="no identifiable"):
            AddressMapper().to_geo_address(raw)

    def test_raises_when_all_fields_none(self):
        """All fields None → MappingError."""
        raw = RawAddress()
        with pytest.raises(MappingError):
            AddressMapper().to_geo_address(raw)

    def test_raises_when_all_fields_empty_strings(self):
        """All fields empty/whitespace → MappingError."""
        raw = RawAddress(province="  ", city="", street="\t")
        with pytest.raises(MappingError):
            AddressMapper().to_geo_address(raw)

    def test_geo_address_has_no_coordinate_field(self):
        """FROZEN v1.2: GeoAddress does NOT carry a coordinate."""
        raw = RawAddress(
            city="Shiraz",
            latitude=29.5926,
            longitude=52.5836,
        )
        result = AddressMapper().to_geo_address(raw)
        # coordinate is NOT in GeoAddress — verify it's not there
        assert not hasattr(result, "coordinate")


class TestAddressMapperToGeoCoordinate:
    """Tests for RawAddress → GeoCoordinate mapping."""

    def test_maps_valid_coordinates(self):
        raw = RawAddress(latitude=35.6892, longitude=51.3890)
        coord = AddressMapper().to_geo_coordinate(raw)
        assert coord.latitude == Decimal("35.6892")
        assert coord.longitude == Decimal("51.3890")

    def test_raises_when_latitude_missing(self):
        raw = RawAddress(city="X", longitude=51.0)
        with pytest.raises(MappingError, match="latitude"):
            AddressMapper().to_geo_coordinate(raw)

    def test_raises_when_longitude_missing(self):
        raw = RawAddress(city="X", latitude=35.0)
        with pytest.raises(MappingError, match="longitude"):
            AddressMapper().to_geo_coordinate(raw)

    def test_raises_when_both_missing(self):
        raw = RawAddress(city="X")
        with pytest.raises(MappingError):
            AddressMapper().to_geo_coordinate(raw)


class TestAddressMapperBulk:
    """Tests for bulk conversion methods."""

    def test_to_address_list_skips_unmappable(self):
        raw_list = [
            RawAddress(city="Tehran"),
            RawAddress(latitude=1.0, longitude=2.0),  # no text → skipped
            RawAddress(city="Isfahan"),
        ]
        result = AddressMapper().to_address_list(raw_list)
        assert len(result) == 2
        assert result[0].city == "Tehran"
        assert result[1].city == "Isfahan"

    def test_to_coordinate_list_skips_unmappable(self):
        raw_list = [
            RawAddress(latitude=35.0, longitude=51.0),
            RawAddress(city="NoCoord"),  # no lat/lon → skipped
            RawAddress(latitude=36.0, longitude=52.0),
        ]
        result = AddressMapper().to_coordinate_list(raw_list)
        assert len(result) == 2


class TestCapabilityMapper:
    """Tests for RawCapability → GeoProviderCapability mapping."""

    def test_maps_capability(self):
        raw = RawCapability(
            provider_name="fimap",
            city_validation=CapabilityInfo(
                level=CapabilityLevel.FULL,
                accuracy=0.95,
                coverage="iran",
                notes="Full city coverage",
            ),
            street_validation=CapabilityInfo(
                level=CapabilityLevel.PARTIAL,
                accuracy=0.80,
                coverage="tehran",
            ),
            postal_code_validation=CapabilityInfo(
                level=CapabilityLevel.BASIC,
                accuracy=0.70,
                coverage="iran",
            ),
            reverse_geocode=CapabilityInfo(
                level=CapabilityLevel.FULL,
                accuracy=0.90,
                coverage="iran",
            ),
            coordinate_validation=CapabilityInfo(
                level=CapabilityLevel.EXPERT,
                accuracy=0.99,
                coverage="iran",
            ),
        )
        result = CapabilityMapper().to_capability(raw)

        assert result.city_validation.level == CapabilityLevel.FULL
        assert result.city_validation.accuracy == 0.95
        assert result.city_validation.coverage == "iran"

        assert result.street_validation.level == CapabilityLevel.PARTIAL
        assert result.street_validation.accuracy == 0.80

        assert result.postal_code.level == CapabilityLevel.BASIC
        assert result.postal_code.accuracy == 0.70

        assert result.reverse_geocode.level == CapabilityLevel.FULL
        assert result.reverse_geocode.accuracy == 0.90

        assert result.coordinate_check.level == CapabilityLevel.EXPERT
        assert result.coordinate_check.accuracy == 0.99

    def test_raises_when_name_empty(self):
        with pytest.raises(MappingError, match="provider_name"):
            CapabilityMapper().to_capability(RawCapability(provider_name="  "))

    def test_raises_when_name_blank(self):
        with pytest.raises(MappingError):
            CapabilityMapper().to_capability(RawCapability(provider_name=""))

    def test_default_capability_info_is_none_level(self):
        """All fields default to CapabilityLevel.NONE."""
        raw = RawCapability(provider_name="test")
        result = CapabilityMapper().to_capability(raw)
        assert result.city_validation.level == CapabilityLevel.NONE
        assert result.street_validation.level == CapabilityLevel.NONE
        assert result.postal_code.level == CapabilityLevel.NONE
        assert result.reverse_geocode.level == CapabilityLevel.NONE
        assert result.coordinate_check.level == CapabilityLevel.NONE

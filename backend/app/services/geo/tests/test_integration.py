# tests/test_integration.py
"""Integration tests for Geo layer — MockProvider + Mappers + Config end-to-end."""

import pytest

from app.services.geo.providers.mock_provider import MockGeoProvider
from app.services.geo.mappers.address_mapper import AddressMapper, RawAddress
from app.services.geo.mappers.capability_mapper import CapabilityMapper, RawCapability
from app.services.geo.geo_models import (
    GeoAddress,
    GeoCoordinate,
    CapabilityInfo,
    CapabilityLevel,
)


class TestMockProviderWithMapper:
    """
    Integration: MockGeoProvider → RawAddress → AddressMapper → GeoAddress.
    """

    @pytest.fixture
    def provider(self):
        return MockGeoProvider(seed=123, delay=0, failure_rate=0.0)

    @pytest.fixture
    def mapper(self):
        return AddressMapper()

    def test_reverse_geocode_to_geo_address_roundtrip(self, provider, mapper):
        """reverse_geocode returns GeoAddress that can be re-mapped."""
        coord = GeoCoordinate(latitude=35.6892, longitude=51.3890)
        geo_addr = provider.reverse_geocode(coord)

        assert geo_addr is not None
        assert geo_addr.province is not None
        assert geo_addr.city is not None

        # Convert back to RawAddress and re-map
        raw = RawAddress(
            province=geo_addr.province,
            city=geo_addr.city,
            street=geo_addr.street,
        )
        result = mapper.to_geo_address(raw)
        assert result.province == geo_addr.province
        assert result.city == geo_addr.city

    def test_validate_address_fields_are_consistent(self, provider):
        """Validation result fields should be internally consistent."""
        addr = GeoAddress(province="Tehran", city="Tehran", street="Valiasr")
        result = provider.validate_address(addr)

        # If province_exists is True, confidence should be > 0
        if result.province_exists:
            assert result.province_confidence > 0.0
        if result.city_exists:
            assert result.city_confidence > 0.0

    def test_deterministic_provider_same_address_same_validation(self):
        """Same seed + same address → same validation result."""
        p1 = MockGeoProvider(seed=42, delay=0, failure_rate=0.0)
        p2 = MockGeoProvider(seed=42, delay=0, failure_rate=0.0)
        addr = GeoAddress(city="Isfahan")

        r1 = p1.validate_address(addr)
        r2 = p2.validate_address(addr)
        assert r1 == r2


class TestConfigToProviderIntegration:
    """
    Integration: Config → Provider instantiation.
    """

    def test_provider_config_works_with_defaults(self, monkeypatch):
        """Provider can be instantiated with config loaded from env."""
        monkeypatch.setenv("GEO_INT_BASE_URL", "https://int-test.local/api")
        from app.services.geo.config.provider_config import ProviderConfigLoader

        loader = ProviderConfigLoader()
        config = loader.load("int")

        assert config.name == "int"
        assert config.base_url == "https://int-test.local/api"
        assert config.timeout_seconds > 0
        assert config.retry_max_retries >= 0


class TestExceptionHierarchyIntegration:
    """
    Integration: Exception translation chain works correctly.
    """

    def test_client_exceptions_are_separate_from_domain_exceptions(self):
        """Client-layer and domain-layer exceptions are distinct."""
        from app.services.geo.clients.exceptions import ProviderConnectionError as ClientConnError
        from app.services.geo.exceptions.geo_exceptions import ProviderConnectionError as DomainConnError

        # They should be different classes
        assert ClientConnError is not DomainConnError

    def test_http_provider_translates_client_to_domain(self):
        """HttpGeoProvider._execute_with_error_handling translates exceptions."""
        import httpx
        from unittest.mock import MagicMock
        from app.services.geo.providers.http_provider import HttpGeoProvider
        from app.services.geo.exceptions.geo_exceptions import ProviderTimeoutError

        adapter = MagicMock()
        adapter.provider_name = "test"
        adapter.provider_version = "1.0"
        adapter.adapter_name = "TestAdapter"
        adapter.validate_address.side_effect = httpx.TimeoutException("timed out")

        provider = HttpGeoProvider(adapter)

        with pytest.raises(ProviderTimeoutError) as exc_info:
            provider.validate_address(GeoAddress(city="X"))

        assert exc_info.value.provider_name == "test"

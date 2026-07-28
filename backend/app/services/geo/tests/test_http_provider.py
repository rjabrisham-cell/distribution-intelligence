# tests/test_http_provider.py
"""Unit tests for HttpGeoProvider — with mocked adapter."""

import pytest
from unittest.mock import MagicMock, patch
import httpx

from app.services.geo.providers.http_provider import HttpGeoProvider
from app.services.geo.geo_models import (
    GeoAddress,
    GeoCoordinate,
    AddressValidationResult,
    GeoProviderCapability,
    CapabilityInfo,
    CapabilityLevel,
    CONTRACT_VERSION,
)
from app.services.geo.exceptions.geo_exceptions import (
    ProviderTimeoutError,
    ProviderConnectionError,
    ProviderServerError,
    ProviderRateLimitError,
    ProviderResponseError,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_adapter():
    """Create a mock adapter with all required methods."""
    adapter = MagicMock()
    adapter.provider_name = "mock-adapter"
    adapter.provider_version = "1.0.0"
    adapter.adapter_name = "MockAdapter"
    return adapter


@pytest.fixture
def provider(mock_adapter):
    """Create HttpGeoProvider with mock adapter."""
    return HttpGeoProvider(mock_adapter)


@pytest.fixture
def sample_address():
    return GeoAddress(
        province="Tehran",
        city="Tehran",
        street="Valiasr Ave",
    )


@pytest.fixture
def sample_coordinate():
    return GeoCoordinate(latitude=35.6892, longitude=51.3890)


@pytest.fixture
def sample_validation_result():
    return AddressValidationResult(
        provider_name="mock-adapter",
        province_exists=True,
        province_confidence=0.95,
        city_exists=True,
        city_confidence=0.90,
    )


# ── Identification ────────────────────────────────────────────────

class TestIdentification:
    """Tests for provider identity properties."""

    def test_provider_name_from_adapter(self, provider, mock_adapter):
        assert provider.provider_name == "mock-adapter"

    def test_provider_version_from_adapter(self, provider):
        assert provider.provider_version == "1.0.0"

    def test_contract_version_is_current(self, provider):
        assert provider.contract_version == CONTRACT_VERSION

    def test_adapter_name(self, provider):
        assert provider.adapter_name == "MockAdapter"

    def test_raises_when_adapter_is_none(self):
        with pytest.raises(ValueError, match="Adapter cannot be None"):
            HttpGeoProvider(None)


# ── Core Methods ──────────────────────────────────────────────────

class TestValidateAddress:
    """Tests for validate_address()."""

    def test_delegates_to_adapter(self, provider, mock_adapter, sample_address, sample_validation_result):
        mock_adapter.validate_address.return_value = sample_validation_result
        result = provider.validate_address(sample_address)
        assert result is sample_validation_result
        mock_adapter.validate_address.assert_called_once_with(sample_address)

    def test_http_timeout_converted_to_domain_error(self, provider, mock_adapter, sample_address):
        mock_adapter.validate_address.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(ProviderTimeoutError) as exc_info:
            provider.validate_address(sample_address)
        assert exc_info.value.provider_name == "mock-adapter"

    def test_http_connect_error_converted(self, provider, mock_adapter, sample_address):
        mock_adapter.validate_address.side_effect = httpx.ConnectError("refused")
        with pytest.raises(ProviderConnectionError):
            provider.validate_address(sample_address)

    def test_http_429_converted_to_rate_limit(self, provider, mock_adapter, sample_address):
        response = MagicMock()
        response.status_code = 429
        response.headers = {"Retry-After": "30"}
        mock_adapter.validate_address.side_effect = httpx.HTTPStatusError(
            "rate limited", request=MagicMock(), response=response
        )
        with pytest.raises(ProviderRateLimitError) as exc_info:
            provider.validate_address(sample_address)
        assert exc_info.value.retry_after == "30"

    def test_http_500_converted_to_server_error(self, provider, mock_adapter, sample_address):
        response = MagicMock()
        response.status_code = 500
        mock_adapter.validate_address.side_effect = httpx.HTTPStatusError(
            "server error", request=MagicMock(), response=response
        )
        with pytest.raises(ProviderServerError) as exc_info:
            provider.validate_address(sample_address)
        assert exc_info.value.status_code == 500

    def test_unexpected_error_converted_to_response_error(self, provider, mock_adapter, sample_address):
        mock_adapter.validate_address.side_effect = RuntimeError("boom")
        with pytest.raises(ProviderResponseError):
            provider.validate_address(sample_address)


class TestValidateCoordinate:
    """Tests for validate_coordinate()."""

    def test_delegates_to_adapter(self, provider, mock_adapter, sample_coordinate, sample_validation_result):
        mock_adapter.validate_coordinate.return_value = sample_validation_result
        result = provider.validate_coordinate(sample_coordinate)
        assert result is sample_validation_result


class TestReverseGeocode:
    """Tests for reverse_geocode()."""

    def test_delegates_to_adapter(self, provider, mock_adapter, sample_coordinate):
        expected = GeoAddress(city="Tehran")
        mock_adapter.reverse_geocode.return_value = expected
        result = provider.reverse_geocode(sample_coordinate)
        assert result is expected

    def test_returns_none_when_adapter_returns_none(self, provider, mock_adapter, sample_coordinate):
        mock_adapter.reverse_geocode.return_value = None
        result = provider.reverse_geocode(sample_coordinate)
        assert result is None


class TestHealthCheck:
    """Tests for health_check()."""

    def test_returns_true_when_adapter_healthy(self, provider, mock_adapter):
        mock_adapter.health_check.return_value = True
        assert provider.health_check() is True

    def test_returns_false_when_adapter_raises(self, provider, mock_adapter):
        mock_adapter.health_check.side_effect = RuntimeError("down")
        assert provider.health_check() is False


class TestCapabilities:
    """Tests for get_capabilities()."""

    def test_delegates_to_adapter(self, provider, mock_adapter):
        caps = GeoProviderCapability(
            city_validation=CapabilityInfo(level=CapabilityLevel.FULL),
        )
        mock_adapter.get_capabilities.return_value = caps
        result = provider.get_capabilities()
        assert result is caps


class TestStrAndRepr:
    """Tests for dunder methods."""

    def test_str_contains_provider_and_adapter(self, provider):
        s = str(provider)
        assert "mock-adapter" in s
        assert "MockAdapter" in s

    def test_repr_contains_adapter_name(self, provider):
        r = repr(provider)
        assert "MockAdapter" in r

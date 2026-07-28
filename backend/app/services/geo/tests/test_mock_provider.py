# tests/test_mock_provider.py
"""Unit tests for MockGeoProvider."""

import pytest

from app.services.geo.providers.mock_provider import MockGeoProvider
from app.services.geo.geo_models import (
    GeoAddress,
    GeoCoordinate,
    CapabilityLevel,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def deterministic_provider():
    """Provider with fixed seed for reproducible tests."""
    return MockGeoProvider(provider_name="test-mock", seed=42, delay=0, failure_rate=0.0)


@pytest.fixture
def always_fail_provider():
    """Provider that always fails."""
    return MockGeoProvider(provider_name="fail-mock", seed=1, delay=0, failure_rate=1.0)


@pytest.fixture
def sample_address():
    return GeoAddress(
        province="Tehran",
        city="Tehran",
        street="Valiasr",
        postal_code="1234567890",
    )


@pytest.fixture
def sample_coordinate():
    return GeoCoordinate(latitude=35.6892, longitude=51.3890)


# ── Identification ────────────────────────────────────────────────

class TestIdentification:
    """Tests for provider identity."""

    def test_provider_name(self, deterministic_provider):
        assert deterministic_provider.provider_name == "test-mock"

    def test_provider_version(self, deterministic_provider):
        assert deterministic_provider.provider_version == "1.0.0"

    def test_contract_version(self, deterministic_provider):
        from app.services.geo.geo_models import CONTRACT_VERSION
        assert deterministic_provider.contract_version == CONTRACT_VERSION

    def test_str_and_repr(self, deterministic_provider):
        s = str(deterministic_provider)
        assert "test-mock" in s
        r = repr(deterministic_provider)
        assert "MockGeoProvider" in r


# ── validate_address ──────────────────────────────────────────────

class TestValidateAddress:
    """Tests for validate_address()."""

    def test_returns_result_with_correct_provider_name(self, deterministic_provider, sample_address):
        result = deterministic_provider.validate_address(sample_address)
        assert result.provider_name == "test-mock"

    def test_deterministic_same_input_same_output(self):
        p = MockGeoProvider(seed=99, delay=0, failure_rate=0.0)
        addr = GeoAddress(city="Shiraz")
        r1 = p.validate_address(addr)
        r2 = p.validate_address(addr)
        assert r1 == r2

    def test_different_inputs_different_outputs(self):
        p = MockGeoProvider(seed=99, delay=0, failure_rate=0.0)
        r1 = p.validate_address(GeoAddress(city="Tehran"))
        r2 = p.validate_address(GeoAddress(city="Mashhad"))
        # At least one field should differ
        fields = [
            "province_exists", "city_exists", "region_exists",
            "street_exists", "postal_code_valid", "coordinate_valid",
        ]
        any_diff = any(
            getattr(r1, f) != getattr(r2, f) for f in fields
        )
        assert any_diff, "Expected different results for different inputs"

    def test_simulated_failure(self, always_fail_provider, sample_address):
        result = always_fail_provider.validate_address(sample_address)
        assert result.provider_name == "fail-mock"
        assert result.province_exists is False
        assert result.city_exists is False
        assert "خطای شبیه‌سازی شده" in result.warnings

    def test_confidence_in_valid_range(self, deterministic_provider, sample_address):
        result = deterministic_provider.validate_address(sample_address)
        for attr in [
            "province_confidence", "city_confidence", "region_confidence",
            "street_confidence", "postal_confidence", "coordinate_confidence",
        ]:
            val = getattr(result, attr)
            assert 0.0 <= val <= 1.0, f"{attr} = {val} out of range"


# ── validate_coordinate ───────────────────────────────────────────

class TestValidateCoordinate:
    """Tests for validate_coordinate()."""

    def test_returns_result(self, deterministic_provider, sample_coordinate):
        result = deterministic_provider.validate_coordinate(sample_coordinate)
        assert result.provider_name == "test-mock"
        assert 0.0 <= result.coordinate_confidence <= 1.0

    def test_simulated_failure(self, always_fail_provider, sample_coordinate):
        result = always_fail_provider.validate_coordinate(sample_coordinate)
        assert result.coordinate_valid is False
        assert result.coordinate_confidence == 0.0


# ── reverse_geocode ───────────────────────────────────────────────

class TestReverseGeocode:
    """Tests for reverse_geocode()."""

    def test_returns_geo_address(self, deterministic_provider, sample_coordinate):
        result = deterministic_provider.reverse_geocode(sample_coordinate)
        assert result is not None
        assert result.province is not None
        assert result.city is not None

    def test_simulated_failure_returns_none(self, always_fail_provider, sample_coordinate):
        result = always_fail_provider.reverse_geocode(sample_coordinate)
        assert result is None

    def test_result_has_coordinate(self, deterministic_provider, sample_coordinate):
        result = deterministic_provider.reverse_geocode(sample_coordinate)
        if result is not None:
            assert result.coordinate == sample_coordinate


# ── health_check ──────────────────────────────────────────────────

class TestHealthCheck:
    """Tests for health_check()."""

    def test_healthy_when_no_failure(self, deterministic_provider):
        assert deterministic_provider.health_check() is True

    def test_unhealthy_when_failure(self, always_fail_provider):
        assert always_fail_provider.health_check() is False


# ── get_capabilities ──────────────────────────────────────────────

class TestGetCapabilities:
    """Tests for get_capabilities()."""

    def test_returns_capability(self, deterministic_provider):
        caps = deterministic_provider.get_capabilities()
        assert caps.provider_name == "test-mock"

    def test_address_validation_is_full(self, deterministic_provider):
        caps = deterministic_provider.get_capabilities()
        assert caps.address_validation.level == CapabilityLevel.FULL

    def test_reverse_geocoding_is_partial(self, deterministic_provider):
        caps = deterministic_provider.get_capabilities()
        assert caps.reverse_geocoding.level == CapabilityLevel.PARTIAL


# ── _safe_confidence (regression test for bug fix) ────────────────

class TestSafeConfidence:
    """Tests for _safe_confidence — regression for the min/max swap bug."""

    def test_lower_bound_not_below_zero(self, deterministic_provider):
        # Even with negative min_val, result should be >= 0
        for _ in range(50):
            val = deterministic_provider._safe_confidence(-0.5, 0.3)
            assert 0.0 <= val <= 1.0

    def test_upper_bound_not_above_one(self, deterministic_provider):
        for _ in range(50):
            val = deterministic_provider._safe_confidence(0.7, 1.5)
            assert 0.0 <= val <= 1.0

    def test_respects_min_val(self):
        p = MockGeoProvider(seed=42, delay=0, failure_rate=0.0)
        for _ in range(30):
            val = p._safe_confidence(0.8, 1.0)
            assert val >= 0.8, f"Expected >= 0.8, got {val}"

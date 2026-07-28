# tests/test_fimap_adapter.py
"""Tests for FimapAdapter — skeleton / placeholder.

NOTE: FimapAdapter is not yet fully implemented (Contract v1.2).
      These tests validate the adapter contract and error handling.
"""

import pytest

from app.services.geo.exceptions.geo_exceptions import AdapterNotImplementedError


class TestFimapAdapterContract:
    """
    Contract tests for any adapter implementing BaseGeoAdapter.
    
    These tests serve as documentation of the expected adapter interface
    and will be activated once FimapAdapter is implemented.
    """

    def test_adapter_not_implemented_error_message(self):
        """Verify AdapterNotImplementedError contains the adapter name."""
        err = AdapterNotImplementedError("fimap")
        assert "fimap" in str(err)
        assert err.adapter_name == "fimap"
        assert err.error_code == "GEO_ADAPTER_NOT_IMPLEMENTED"

    def test_adapter_not_implemented_to_dict(self):
        """Verify serialization includes adapter_name."""
        err = AdapterNotImplementedError("fimap")
        d = err.to_dict()
        assert d["adapter_name"] == "fimap"
        assert d["error_code"] == "GEO_ADAPTER_NOT_IMPLEMENTED"

    @pytest.mark.skip(reason="FimapAdapter not yet implemented")
    def test_fimap_adapter_validate_address_contract(self):
        """[SKIP] Will test: FimapAdapter.validate_address(GeoAddress) → AddressValidationResult."""
        pass

    @pytest.mark.skip(reason="FimapAdapter not yet implemented")
    def test_fimap_adapter_validate_coordinate_contract(self):
        """[SKIP] Will test: FimapAdapter.validate_coordinate(GeoCoordinate) → AddressValidationResult."""
        pass

    @pytest.mark.skip(reason="FimapAdapter not yet implemented")
    def test_fimap_adapter_reverse_geocode_contract(self):
        """[SKIP] Will test: FimapAdapter.reverse_geocode(GeoCoordinate) → GeoAddress | None."""
        pass

    @pytest.mark.skip(reason="FimapAdapter not yet implemented")
    def test_fimap_adapter_health_check_contract(self):
        """[SKIP] Will test: FimapAdapter.health_check() → bool."""
        pass

    @pytest.mark.skip(reason="FimapAdapter not yet implemented")
    def test_fimap_adapter_get_capabilities_contract(self):
        """[SKIP] Will test: FimapAdapter.get_capabilities() → GeoProviderCapability."""
        pass


class TestFimapAdapterErrorHandling:
    """
    Tests for expected error behaviour (design specification).
    """

    @pytest.mark.skip(reason="FimapAdapter not yet implemented")
    def test_http_errors_translated_to_domain_errors(self):
        """Adapter must translate raw HTTP errors to domain exceptions."""
        pass

    @pytest.mark.skip(reason="FimapAdapter not yet implemented")
    def test_malformed_response_raises_provider_response_error(self):
        """Malformed JSON/XML → ProviderResponseError."""
        pass

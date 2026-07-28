# tests/test_geo_exceptions.py
"""Unit tests for geo_exceptions hierarchy."""

import pytest

from app.services.geo.exceptions.geo_exceptions import (
    GeoException,
    GeoProviderError,
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthError,
    ProviderServerError,
    ProviderResponseError,
    MappingError,
    ConfigurationError,
    AdapterNotImplementedError,
)


class TestGeoExceptionHierarchy:
    """Verify the exception inheritance tree."""

    def test_geo_exception_is_base(self):
        assert issubclass(GeoProviderError, GeoException)
        assert issubclass(MappingError, GeoException)
        assert issubclass(ConfigurationError, GeoException)
        assert issubclass(AdapterNotImplementedError, GeoException)

    def test_provider_errors_inherit_from_geo_provider_error(self):
        for cls in [
            ProviderConnectionError,
            ProviderTimeoutError,
            ProviderRateLimitError,
            ProviderAuthError,
            ProviderServerError,
            ProviderResponseError,
        ]:
            assert issubclass(cls, GeoProviderError), f"{cls.__name__}"


class TestGeoProviderError:
    """Tests for GeoProviderError base."""

    def test_provider_name_is_stored(self):
        err = GeoProviderError("msg", provider_name="fimap")
        assert err.provider_name == "fimap"

    def test_url_is_stored(self):
        err = GeoProviderError("msg", url="https://example.com/api")
        assert err.url == "https://example.com/api"

    def test_to_dict_includes_provider_name(self):
        err = GeoProviderError("msg", provider_name="nom")
        d = err.to_dict()
        assert d["provider_name"] == "nom"


class TestProviderConnectionError:
    """Tests for ProviderConnectionError."""

    def test_host_and_port_are_stored(self):
        err = ProviderConnectionError("msg", host="api.local", port=443)
        assert err.host == "api.local"
        assert err.port == 443

    def test_to_dict_includes_host_port(self):
        err = ProviderConnectionError("msg", host="x", port=80)
        d = err.to_dict()
        assert d["host"] == "x"
        assert d["port"] == 80


class TestProviderTimeoutError:
    """Tests for ProviderTimeoutError."""

    def test_configured_timeout_is_stored(self):
        err = ProviderTimeoutError("msg", configured_timeout=15.0)
        assert err.configured_timeout == 15.0


class TestRateLimitError:
    """Tests for ProviderRateLimitError."""

    def test_retry_after_is_optional(self):
        err = ProviderRateLimitError("too many requests")
        assert err.retry_after is None

    def test_retry_after_is_stored(self):
        err = ProviderRateLimitError("too many requests", retry_after=42.0)
        assert err.retry_after == 42.0

    def test_details_are_accessible(self):
        err = ProviderRateLimitError("msg", details={"endpoint": "/search"})
        assert err.details == {"endpoint": "/search"}

    def test_limit_and_remaining_are_stored(self):
        err = ProviderRateLimitError("msg", limit=100, remaining=42)
        assert err.limit == 100
        assert err.remaining == 42


class TestProviderAuthError:
    """Tests for ProviderAuthError."""

    def test_accepts_401(self):
        err = ProviderAuthError("auth failed", status_code=401)
        assert err.status_code == 401

    def test_accepts_403(self):
        err = ProviderAuthError("forbidden", status_code=403)
        assert err.status_code == 403

    def test_rejects_invalid_status_code(self):
        with pytest.raises(ValueError, match="401 or 403"):
            ProviderAuthError("msg", status_code=500)


class TestProviderServerError:
    """Tests for ProviderServerError."""

    def test_status_code_is_stored(self):
        err = ProviderServerError("boom", status_code=500)
        assert err.status_code == 500

    def test_accepts_5xx(self):
        for code in (500, 502, 503, 504):
            err = ProviderServerError("msg", status_code=code)
            assert err.status_code == code

    def test_rejects_non_5xx(self):
        with pytest.raises(ValueError, match="5xx"):
            ProviderServerError("msg", status_code=400)


class TestProviderResponseError:
    """Tests for ProviderResponseError."""

    def test_truncates_long_body(self):
        long_body = "x" * 3000
        err = ProviderResponseError("msg", response_body=long_body)
        assert len(err.response_body) <= 2100  # max 2000 + "..."
        assert err.response_body.endswith("...")

    def test_content_type_is_stored(self):
        err = ProviderResponseError("msg", content_type="text/html")
        assert err.content_type == "text/html"


class TestMappingError:
    """Tests for MappingError."""

    def test_source_and_target_types_are_stored(self):
        err = MappingError("msg", source_type="RawAddress", target_type="GeoAddress")
        assert err.source_type == "RawAddress"
        assert err.target_type == "GeoAddress"

    def test_to_dict_includes_types(self):
        err = MappingError("msg", source_type="S", target_type="T")
        d = err.to_dict()
        assert d["source_type"] == "S"
        assert d["target_type"] == "T"


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_parameter_name_is_stored(self):
        err = ConfigurationError("msg", parameter_name="GEO_FIMAP_TIMEOUT")
        assert err.parameter_name == "GEO_FIMAP_TIMEOUT"


class TestAdapterNotImplementedError:
    """Tests for AdapterNotImplementedError."""

    def test_message_contains_adapter_name(self):
        err = AdapterNotImplementedError("fimap")
        assert "fimap" in str(err)

    def test_adapter_name_is_stored(self):
        err = AdapterNotImplementedError("nominatim")
        assert err.adapter_name == "nominatim"


class TestGeoExceptionSerialization:
    """Tests for to_dict() across all exceptions."""

    def test_base_to_dict(self):
        err = GeoException("test", error_code="GEO_TEST", details={"k": "v"})
        d = err.to_dict()
        assert d["error_code"] == "GEO_TEST"
        assert d["message"] == "test"
        assert d["details"] == {"k": "v"}

    def test_to_dict_does_not_include_cause(self):
        inner = ValueError("cause")
        err = GeoException("test", cause=inner)
        d = err.to_dict()
        assert "cause" not in d

    def test_repr_contains_all_fields(self):
        err = GeoException("msg", error_code="C1", details={"a": 1})
        r = repr(err)
        assert "C1" in r
        assert "msg" in r
        assert "a" in r

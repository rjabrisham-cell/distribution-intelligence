# tests/test_provider_config.py
"""Unit tests for ProviderConfigLoader — aligned with flat ProviderConfig fields."""

import pytest

from app.services.geo.config.provider_config import ProviderConfigLoader
from app.services.geo.exceptions.geo_exceptions import ConfigurationError


class TestProviderConfigLoader:
    """Tests for ProviderConfigLoader.load()."""

    def test_loads_minimal_config(self, monkeypatch):
        monkeypatch.setenv("GEO_FIMAP_BASE_URL", "https://fimap.local/api")
        loader = ProviderConfigLoader()
        config = loader.load("fimap")
        assert config.name == "fimap"
        assert config.base_url == "https://fimap.local/api"
        assert config.timeout_seconds == 10.0  # default
        assert config.api_key is None

    def test_raises_when_base_url_missing(self):
        loader = ProviderConfigLoader()
        with pytest.raises(ConfigurationError, match="GEO_FIMAP_BASE_URL"):
            loader.load("fimap")

    def test_loads_full_config(self, monkeypatch):
        monkeypatch.setenv("GEO_NOM_BASE_URL", "https://nominatim.example.org")
        monkeypatch.setenv("GEO_NOM_API_KEY", "secret-token")
        monkeypatch.setenv("GEO_NOM_TIMEOUT", "15.5")
        monkeypatch.setenv("GEO_NOM_MAX_RETRIES", "5")
        monkeypatch.setenv("GEO_NOM_BACKOFF_BASE", "2.0")
        monkeypatch.setenv("GEO_NOM_BACKOFF_MULTIPLIER", "3.0")
        monkeypatch.setenv("GEO_NOM_MAX_BACKOFF", "45.0")

        loader = ProviderConfigLoader()
        config = loader.load("nom")

        assert config.base_url == "https://nominatim.example.org"
        assert config.api_key == "secret-token"
        assert config.timeout_seconds == 15.5
        assert config.retry_max_retries == 5
        assert config.retry_backoff_base_seconds == 2.0
        assert config.retry_backoff_multiplier == 3.0
        assert config.retry_max_backoff_seconds == 45.0

    def test_extra_keys_are_collected(self, monkeypatch):
        monkeypatch.setenv("GEO_XYZ_BASE_URL", "https://xyz.local")
        monkeypatch.setenv("GEO_XYZ_CUSTOM_FEATURE", "enabled")
        monkeypatch.setenv("GEO_XYZ_ANOTHER", "42")

        loader = ProviderConfigLoader()
        config = loader.load("xyz")

        assert config.extra == {
            "custom_feature": "enabled",
            "another": "42",
        }

    def test_invalid_timeout_raises(self, monkeypatch):
        monkeypatch.setenv("GEO_BAD_BASE_URL", "https://bad.local")
        monkeypatch.setenv("GEO_BAD_TIMEOUT", "not-a-number")

        loader = ProviderConfigLoader()
        with pytest.raises(ConfigurationError, match="must be a number"):
            loader.load("bad")

    def test_invalid_provider_name_raises(self):
        loader = ProviderConfigLoader()
        with pytest.raises(ConfigurationError, match="Invalid provider name"):
            loader.load("123bad")

    def test_empty_provider_name_raises(self):
        loader = ProviderConfigLoader()
        with pytest.raises(ConfigurationError):
            loader.load("")

    def test_base_url_without_scheme_raises(self, monkeypatch):
        monkeypatch.setenv("GEO_XXX_BASE_URL", "just-a-host.com/api")
        loader = ProviderConfigLoader()
        with pytest.raises(ConfigurationError, match="http:// or https://"):
            loader.load("xxx")

    def test_trailing_slash_is_stripped(self, monkeypatch):
        monkeypatch.setenv("GEO_CUT_BASE_URL", "https://cut.local/api/")
        loader = ProviderConfigLoader()
        config = loader.load("cut")
        assert config.base_url == "https://cut.local/api"

    def test_api_key_empty_string_becomes_none(self, monkeypatch):
        monkeypatch.setenv("GEO_NOKEY_BASE_URL", "https://nokey.local")
        monkeypatch.setenv("GEO_NOKEY_API_KEY", "   ")
        loader = ProviderConfigLoader()
        config = loader.load("nokey")
        assert config.api_key is None

    def test_masked_api_key(self, monkeypatch):
        monkeypatch.setenv("GEO_MSK_BASE_URL", "https://msk.local")
        monkeypatch.setenv("GEO_MSK_API_KEY", "abcdefgh12345678")
        loader = ProviderConfigLoader()
        config = loader.load("msk")
        assert config.masked_api_key() == "abcdefgh********"

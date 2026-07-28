"""
config package — Geo Provider Configuration
============================================
Contract v1.2

لایه Config مستقل — هیچ وابستگی به clients/ یا adapters/ ندارد.

Provides:
    - ProviderConfig     : immutable config برای یک Provider
    - ProviderConfigLoader: خواندن config از Environment Variables
    - GeoDefaults        : مقادیر پیش‌فرض متمرکز
    - get_provider_config_loader : singleton loader
"""

from app.services.geo.config.provider_config import (
    ProviderConfig,
    ProviderConfigLoader,
    get_provider_config_loader,
)
from app.services.geo.config.geo_defaults import GeoDefaults, GEO_DEFAULTS

__all__ = [
    "ProviderConfig",
    "ProviderConfigLoader",
    "get_provider_config_loader",
    "GeoDefaults",
    "GEO_DEFAULTS",
]

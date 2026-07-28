"""
exceptions package — Geo Domain Exceptions
===========================================
Contract v1.2

تمامی Exceptionهای لایه Geo. این Exceptionها Domain Error هستند،
نه HTTP Error. هیچ وابستگی به Provider, Adapter, Client یا Config ندارند.

کاملاً مستقل — فقط توسط سایر لایه‌ها import می‌شوند.

Export All:
    - GeoException                  (base)
    - GeoProviderError              (base for provider errors)
    - ProviderConnectionError
    - ProviderTimeoutError
    - ProviderRateLimitError
    - ProviderAuthError
    - ProviderServerError
    - ProviderResponseError
    - MappingError
    - ConfigurationError
    - AdapterNotImplementedError
"""

from app.services.geo.exceptions.geo_exceptions import (
    # Base
    GeoException,
    # Provider errors
    GeoProviderError,
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthError,
    ProviderServerError,
    ProviderResponseError,
    # Internal errors
    MappingError,
    ConfigurationError,
    AdapterNotImplementedError,
)

__all__ = [
    "GeoException",
    "GeoProviderError",
    "ProviderConnectionError",
    "ProviderTimeoutError",
    "ProviderRateLimitError",
    "ProviderAuthError",
    "ProviderServerError",
    "ProviderResponseError",
    "MappingError",
    "ConfigurationError",
    "AdapterNotImplementedError",
]

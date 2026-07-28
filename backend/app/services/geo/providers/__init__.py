"""
providers package — پیاده‌سازی‌های Geo Provider
================================================
Contract v1.0 (Frozen)

این پکیج شامل تمام پیاده‌سازی‌های اینترفیس GeoProvider است.
هر Provider جدید باید در اینجا import و در __all__ ثبت شود.
"""

from app.services.geo.providers.http_provider import HttpGeoProvider
from app.services.geo.providers.mock_provider import MockGeoProvider

__all__ = [
    "HttpGeoProvider",
    "MockGeoProvider",
    # Providerهای آینده:
    # "FimapProvider",
    # "NominatimProvider",
    # "PhotonProvider",
    # "GeoServerProvider",
]

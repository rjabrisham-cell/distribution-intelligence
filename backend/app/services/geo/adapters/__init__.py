"""
adapters package — Adapters for external Geo Providers
======================================================
Contract v1.2 — Decision: Sync (گزینه A)

تمامی Adapterها از BaseGeoAdapter ارث‌بری می‌کنند که خود
پیاده‌ساز GeoProvider است. کل زنجیره Sync است.
"""

from app.services.geo.adapters.base_adapter import (
    BaseGeoAdapter,
    GeoConnectionError,
    GeoAdapterError,
)
from app.services.geo.adapters.fimap_adapter import FimapAdapter
from app.services.geo.adapters.geoserver_adapter import GeoServerAdapter
from app.services.geo.adapters.nominatim_adapter import NominatimAdapter
from app.services.geo.adapters.photon_adapter import PhotonAdapter

__all__ = [
    "BaseGeoAdapter",
    "GeoConnectionError",
    "GeoAdapterError",
    "FimapAdapter",
    "GeoServerAdapter",
    "NominatimAdapter",
    "PhotonAdapter",
]

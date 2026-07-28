"""
geo_provider.py — GeoProvider Interface
========================================
Contract v1.2 (Frozen)

Interface اصلی تمام GeoProviderها (OSM, Neshan, OSP, ...).
هر Provider باید این Interface را پیاده‌سازی کند.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.geo.geo_models import (
        GeoAddress,
        GeoCoordinate,
        GeoProviderCapability,
        AddressValidationResult,
    )


class GeoProvider(ABC):
    """
    Interface اصلی برای تمام سرویس‌های جغرافیایی.

    Contract v1.2 — Frozen.
    متدهایی که پشتیبانی نمی‌شوند باید مقدار پیش‌فرض (None/False)
    برگردانند.
    """

    # ── Identification ────────────────────────────────────

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """نام یکتای Provider — 'osm', 'neshan', 'osp'."""
        ...

    @property
    @abstractmethod
    def provider_version(self) -> str:
        """نسخه Provider."""
        ...

    @property
    @abstractmethod
    def contract_version(self) -> str:
        """نسخه Contract که Provider پشتیبانی می‌کند."""
        ...

    # ── Capabilities ─────────────────────────────────────

    @abstractmethod
    def get_capabilities(self) -> "GeoProviderCapability":
        """اعلام قابلیت‌های Provider."""
        ...

    # ── Validation Methods ───────────────────────────────

    @abstractmethod
    def validate_address(
        self,
        address: "GeoAddress",
    ) -> "AddressValidationResult":
        """اعتبارسنجی کامل یک آدرس."""
        ...

    @abstractmethod
    def validate_coordinate(
        self,
        coordinate: "GeoCoordinate",
    ) -> "AddressValidationResult":
        """اعتبارسنجی یک مختصات."""
        ...

    @abstractmethod
    def reverse_geocode(
        self,
        coordinate: "GeoCoordinate",
    ) -> "GeoAddress | None":
        """Reverse Geocoding: مختصات → آدرس."""
        ...

    # ── Health Check ─────────────────────────────────────

    @abstractmethod
    def health_check(self) -> bool:
        """بررسی سلامت Provider."""
        ...

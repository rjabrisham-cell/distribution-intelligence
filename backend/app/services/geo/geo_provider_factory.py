"""
geo_provider_factory.py — Geo Provider Factory
===============================================
Contract v1.2 (Frozen)

ثبت، مدیریت و ایجاد Providerها با استفاده از Dependency Injection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.geo.geo_provider import GeoProvider


class GeoProviderFactory:
    """
    Factory برای مدیریت Providerهای Geo.

    Providerها بر اساس provider_name ثبت می‌شوند
    و با create() نمونه‌سازی می‌شوند.
    """

    def __init__(self) -> None:
        self._registry: dict[str, type["GeoProvider"]] = {}

    # ── Registration ────────────────────────────────────

    def register(self, name: str, provider_cls: type["GeoProvider"]) -> None:
        """ثبت یک Provider class."""
        if not name or not name.strip():
            raise ValueError("Provider name must be non-empty")
        self._registry[name.strip().lower()] = provider_cls

    def unregister(self, name: str) -> None:
        self._registry.pop(name.strip().lower(), None)

    # ── Creation ────────────────────────────────────────

    def create(self, name: str, **kwargs) -> "GeoProvider":
        """
        نمونه‌سازی یک Provider با نام مشخص.

        kwargs به constructor Provider پاس داده می‌شود
        (مثلاً api_key, base_url, ...).
        """
        key = name.strip().lower()
        if key not in self._registry:
            available = list(self._registry.keys()) or ["<empty>"]
            raise ValueError(
                f"Unknown provider '{name}'. Available: {', '.join(available)}"
            )
        return self._registry[key](**kwargs)

    # ── Access ──────────────────────────────────────────

    def list_providers(self) -> list[str]:
        return sorted(self._registry.keys())

    def is_registered(self, name: str) -> bool:
        return name.strip().lower() in self._registry


# ── Module-level singleton ───────────────────────────────

_factory_instance: Optional[GeoProviderFactory] = None


def get_provider_factory() -> GeoProviderFactory:
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = GeoProviderFactory()
    return _factory_instance

# mappers/route_mapper.py
"""
Route mapper — reserved for future OSRM / routing-provider integration.
Contract v1.2 (FROZEN)

This module is a SKELETON.  The routing contract has NOT been defined
in GeoProvider yet (BaseGeoAdapter does not expose routing methods).
When routing is added to the provider layer, this mapper will
transform raw route responses into canonical Route / Waypoint DTOs.

Do NOT remove — keep as a placeholder for Sprint 4+.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RawRoute:
    """
    Placeholder intermediate representation of a routing response.

    Fields will be refined when the routing contract is defined
    in GeoProvider / BaseGeoAdapter.
    """

    provider_name: str
    distance_meters: float | None = None
    duration_seconds: float | None = None
    geometry_geojson: dict[str, Any] | None = None
    waypoints: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class RouteMapper:
    """
    SKELETON — reserved for future routing integration.

    Will transform RawRoute → canonical Route DTO once the routing
    contract is defined in GeoProvider.

    Expected canonical DTO (not yet defined in geo_models.py):
        Route(distance_meters, duration_seconds, geometry, waypoints, ...)
    """

    def to_route(self, raw: RawRoute) -> Any:
        """
        Placeholder.  Will return a canonical Route DTO in the future.

        Raises:
            NotImplementedError: always — skeleton adapter.
        """
        raise NotImplementedError(
            "RouteMapper is a skeleton. "
            "Routing DTOs have not been defined in geo_models.py yet. "
            "See: GeoProvider routing contract (not yet in BaseGeoAdapter)."
        )

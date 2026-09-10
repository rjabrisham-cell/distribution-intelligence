"""Coordinate validator for `Store` entities (Readiness Pipeline — Slice 2).

A thin, read-only wrapper over the four existing coordinate rules in
`app/core/validity_rules.py`. It reuses the baseline logic verbatim and only
aggregates the returned verdicts into one structured, immutable snapshot.

Scope (ONLY these):
  - Run `rule_coordinate_range`, `rule_coordinate_precision`,
    `rule_coordinate_in_iran`, `rule_coordinate_swap_detection` on a Store.
  - Collect per-rule verdicts for `latitude` and `longitude`.
  - Expose the coordinates exactly as received (raw pass-through).
  - Produce a per-field summary and an overall status.

Explicitly OUT of scope:
  - NO mutation of the Store (never writes lat/lon/geo_status).
  - NO auto-fix / swap / rounding of coordinates.
  - NO `geo_status` change.
  - NO geographical lookup (the rules' Iran bbox is the only geo reference).
  - NO new validity decision beyond the four existing rules.
  - NO duplicate detection or address normalization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple, Any

from app.core.field_profile import ValidationVerdict
from app.core.validity_rules import (
    rule_coordinate_in_iran,
    rule_coordinate_precision,
    rule_coordinate_range,
    rule_coordinate_swap_detection,
)
from app.models.store import Store

# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

_LAT: str = "latitude"
_LON: str = "longitude"

RuleCallable = Callable[[Store], dict[str, ValidationVerdict]]
_RULES: Tuple[Tuple[str, RuleCallable], ...] = (
    ("coordinate_range", rule_coordinate_range),
    ("coordinate_precision", rule_coordinate_precision),
    ("coordinate_in_iran", rule_coordinate_in_iran),
    ("coordinate_swap_detection", rule_coordinate_swap_detection),
)


# ---------------------------------------------------------------------------
# Immutable result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RuleVerdict:
    """Verdicts produced by one rule for both coordinate fields."""

    rule_name: str
    latitude: ValidationVerdict
    longitude: ValidationVerdict


@dataclass(frozen=True, slots=True)
class CoordinateValidationResult:
    """Immutable validation snapshot for the coordinates of one Store."""

    store_id: Any
    latitude: Any
    longitude: Any
    verdicts: Tuple[RuleVerdict, ...]
    latitude_summary: ValidationVerdict
    longitude_summary: ValidationVerdict

    @property
    def overall(self) -> ValidationVerdict:
        """Worst verdict across both coordinate fields."""
        return _worst(self.latitude_summary, self.longitude_summary)

    @property
    def overall_status(self) -> ValidationVerdict:
        """Alias for overall, useful for reporting code."""
        return self.overall

    @property
    def has_issues(self) -> bool:
        """True if any field is INVALID or WARNING."""
        return self.overall in (ValidationVerdict.INVALID, ValidationVerdict.WARNING)


# ---------------------------------------------------------------------------
# Summary aggregation
# ---------------------------------------------------------------------------

def _worst(a: ValidationVerdict, b: ValidationVerdict) -> ValidationVerdict:
    """Return the more severe of two verdicts.

    Severity order (most -> least severe):
      INVALID > WARNING > VALID > UNKNOWN
    """
    rank = {
        ValidationVerdict.UNKNOWN: 0,
        ValidationVerdict.VALID: 1,
        ValidationVerdict.WARNING: 2,
        ValidationVerdict.INVALID: 3,
    }
    return a if rank[a] >= rank[b] else b


def _summarize(verdicts: Tuple[ValidationVerdict, ...]) -> ValidationVerdict:
    """Fold per-rule verdicts for one field into a single summary."""
    if ValidationVerdict.INVALID in verdicts:
        return ValidationVerdict.INVALID
    if ValidationVerdict.WARNING in verdicts:
        return ValidationVerdict.WARNING
    if ValidationVerdict.VALID in verdicts:
        return ValidationVerdict.VALID
    return ValidationVerdict.UNKNOWN


def _store_id(store: Store) -> Any:
    """Best-effort store identifier without mutating or assuming a strict contract."""
    if hasattr(store, "id"):
        return getattr(store, "id")
    if hasattr(store, "store_id"):
        return getattr(store, "store_id")
    return None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class CoordinateValidator:
    """Stateless, read-only validator for Store coordinates."""

    def validate(self, store: Store) -> CoordinateValidationResult:
        """Run the four coordinate rules and aggregate their verdicts."""
        rule_verdicts: list[RuleVerdict] = []
        lat_verdicts: list[ValidationVerdict] = []
        lon_verdicts: list[ValidationVerdict] = []

        for rule_name, rule_fn in _RULES:
            result = rule_fn(store)

            lat_v = result.get(_LAT, ValidationVerdict.UNKNOWN)
            lon_v = result.get(_LON, ValidationVerdict.UNKNOWN)

            rule_verdicts.append(
                RuleVerdict(
                    rule_name=rule_name,
                    latitude=lat_v,
                    longitude=lon_v,
                )
            )
            lat_verdicts.append(lat_v)
            lon_verdicts.append(lon_v)

        return CoordinateValidationResult(
            store_id=_store_id(store),
            latitude=getattr(store, _LAT, None),
            longitude=getattr(store, _LON, None),
            verdicts=tuple(rule_verdicts),
            latitude_summary=_summarize(tuple(lat_verdicts)),
            longitude_summary=_summarize(tuple(lon_verdicts)),
        )

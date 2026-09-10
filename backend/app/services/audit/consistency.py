# app/services/audit/consistency.py
"""Consistency service for ``Store`` entities (Readiness Pipeline — Slice 3).

Read-only evaluation of cross-field consistency for a Store's base geography.
For the MVP, the only defined check is:

    city_id  belongs to  province_id

This intentionally mirrors the placeholder ``rule_province_city_consistency``
in ``app/core/validity_rules.py`` and keeps the exact same behavior:

  * If ``province_id`` or ``city_id`` cannot be parsed to ``int``
    (``TypeError`` / ``ValueError``), BOTH fields are reported ``INVALID``.
  * If either value is ``None`` (absent), BOTH fields are reported ``INVALID``.
  * If both values are present and parseable, the real city→province mapping
    is NOT yet validated (GeoKB not integrated), so BOTH fields are reported
    ``UNKNOWN`` — no fabricated pass/fail.

Scope (ONLY these):
  * Read the Store's ``province_id`` / ``city_id``.
  * Produce a per-field verdict and an overall verdict.

Explicitly OUT of scope:
  * NO mutation of the Store.
  * NO writes to ``geo_status`` / ``data_quality_status`` / ``duplicate_status``.
  * NO auto-correct / swap / re-mapping of ids.
  * NO GeoKB or external lookup.
  * NO address / coordinate / duplicate / validity checks beyond the above.
  * NO UI/report rendering (that belongs to ``report_builder.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from app.core.field_profile import ValidationVerdict
from app.models.store import Store

# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

_PROVINCE: str = "province_id"
_CITY: str = "city_id"

# Severity order (least -> most severe). UNKNOWN carries no failure signal,
# so it ranks below VALID.
_SEVERITY_ORDER: Tuple[ValidationVerdict, ...] = (
    ValidationVerdict.UNKNOWN,
    ValidationVerdict.VALID,
    ValidationVerdict.WARNING,
    ValidationVerdict.INVALID,
)
_SEVERITY_RANK: Dict[ValidationVerdict, int] = {
    v: i for i, v in enumerate(_SEVERITY_ORDER)
}


def _worst(a: ValidationVerdict, b: ValidationVerdict) -> ValidationVerdict:
    """Return the more severe of two verdicts."""
    return a if _SEVERITY_RANK[a] >= _SEVERITY_RANK[b] else b


# ---------------------------------------------------------------------------
# Immutable result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FieldCheck:
    """Verdict for a single consistency-checked field."""

    field: str
    verdict: ValidationVerdict


@dataclass(frozen=True)
class ConsistencyResult:
    """Immutable consistency snapshot for one ``Store``."""

    store_id: Any

    # Raw pass-through ids — deliberately untouched.
    province_id: Any
    city_id: Any

    # Per-field checks, in stable order (province_id, city_id).
    checks: Tuple[FieldCheck, ...]

    # Convenience per-field verdicts.
    province_verdict: ValidationVerdict
    city_verdict: ValidationVerdict

    @property
    def overall(self) -> ValidationVerdict:
        """Worst verdict across both fields."""
        return _worst(self.province_verdict, self.city_verdict)

    @property
    def has_issues(self) -> bool:
        """True when the overall verdict is INVALID or WARNING."""
        return self.overall in (ValidationVerdict.INVALID, ValidationVerdict.WARNING)


# ---------------------------------------------------------------------------
# Batch accumulator (mutable, mirrors BatchAccumulator / ValidityBatchAccumulator)
# ---------------------------------------------------------------------------

@dataclass
class ConsistencyBatchAccumulator:
    """Mutable batch-level counter, intended for ``AuditRunner`` integration."""

    store_count: int = 0
    issue_count: int = 0
    province_counts: Dict[str, int] = field(
        default_factory=lambda: {v.value: 0 for v in ValidationVerdict}
    )
    city_counts: Dict[str, int] = field(
        default_factory=lambda: {v.value: 0 for v in ValidationVerdict}
    )

    def add(self, result: ConsistencyResult) -> None:
        """Fold one ``ConsistencyResult`` into the running totals."""
        self.store_count += 1
        self.province_counts[result.province_verdict.value] += 1
        self.city_counts[result.city_verdict.value] += 1
        if result.has_issues:
            self.issue_count += 1


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ConsistencyService:
    """Stateless, read-only consistency evaluator.

    Accepts one ``Store`` and returns an immutable ``ConsistencyResult``.
    It never mutates the input and never fixes or swaps values.
    """

    def evaluate(self, store: Store) -> ConsistencyResult:
        """Evaluate city_id ∈ province_id consistency (placeholder semantics)."""
        province_raw = getattr(store, _PROVINCE, None)
        city_raw = getattr(store, _CITY, None)

        province: int | None = None
        city: int | None = None
        parse_error = False

        try:
            province = int(province_raw) if province_raw is not None else None
            city = int(city_raw) if city_raw is not None else None
        except (TypeError, ValueError):
            parse_error = True

        # Placeholder semantics (identical to rule_province_city_consistency):
        #   conversion failure OR missing value  -> both INVALID
        #   both present and parseable           -> both UNKNOWN (GeoKB TODO)
        if parse_error or province is None or city is None:
            p_verdict = ValidationVerdict.INVALID
            c_verdict = ValidationVerdict.INVALID
        else:
            p_verdict = ValidationVerdict.UNKNOWN
            c_verdict = ValidationVerdict.UNKNOWN

        return ConsistencyResult(
            store_id=getattr(store, "id", None),
            province_id=province_raw,
            city_id=city_raw,
            checks=(
                FieldCheck(field=_PROVINCE, verdict=p_verdict),
                FieldCheck(field=_CITY, verdict=c_verdict),
            ),
            province_verdict=p_verdict,
            city_verdict=c_verdict,
        )

    def create_accumulator(self) -> ConsistencyBatchAccumulator:
        """Return a fresh batch accumulator for ``AuditRunner`` integration."""
        return ConsistencyBatchAccumulator()

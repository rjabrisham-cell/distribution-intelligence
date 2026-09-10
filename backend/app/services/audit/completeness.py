# ============================================================================
# Distribution Intelligence Platform (DIP)
# Sprint 2 — Data Quality Audit Engine
# Contract v2.0 (Frozen)
#
# Completeness Audit — PURE, Stateless, No DB, No Business Decisions
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.field_profile import (
    FIELD_PROFILE,
    _GROUP_WEIGHTS,
    _TOTAL_WEIGHT,
    FieldGroup,
    ValidationVerdict,
)
from app.models.store import Store


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                      R E S U L T   D T O s                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@dataclass(frozen=True, slots=True)
class FieldResult:
    field_name:    str
    label_fa:      str
    group:         FieldGroup
    weight:        int
    verdict:       ValidationVerdict
    required:      bool
    current_value: Any = field(repr=False)

    @property
    def passed(self) -> bool:
        return self.verdict == ValidationVerdict.VALID

    @property
    def is_missing(self) -> bool:
        return self.verdict == ValidationVerdict.INVALID


@dataclass(frozen=True, slots=True)
class CompletenessResult:
    store_id:          int
    canonical_name:    str
    raw_score:         int
    total_weight:      int
    percentage:        float
    passed:            bool
    is_fully_complete: bool
    field_results:     tuple[FieldResult, ...]
    missing_fields:    tuple[str, ...]
    warnings:          tuple[str, ...]
    group_scores:      dict[str, float]
    metadata:          dict[str, Any] = field(default_factory=dict)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║             B A T C H   A C C U M U L A T O R   (Incremental)           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@dataclass
class BatchAccumulator:
    """
    Incremental batch aggregator.

    Call ``update(result)`` for each store — O(1) per call, constant RAM.
    Call ``finalize()`` once to produce ``BatchCompletenessResult``.
    """

    total: int = 0
    passed: int = 0
    fully_complete: int = 0
    sum_raw: float = 0.0
    sum_pct: float = 0.0
    min_pct: float = float("inf")
    max_pct: float = float("-inf")

    # streaming median: collect percentages in a sorted list
    # (still O(n) memory but single list of floats; for truly
    # constant-RAM median, swap to t-digest or reservoir later)
    _pcts: list[float] = field(default_factory=list)

    # group aggregates: {group: {"sum": x, "min": y, "max": z}}
    _group_accum: dict[str, dict[str, float]] = field(default_factory=dict)

    # field aggregates: {field: {"passed": n, "total": m}}
    _field_accum: dict[str, dict[str, int]] = field(default_factory=dict)

    def update(self, result: CompletenessResult) -> None:
        self.total += 1
        self.sum_raw += result.raw_score
        self.sum_pct += result.percentage
        self._pcts.append(result.percentage)

        if result.percentage < self.min_pct:
            self.min_pct = result.percentage
        if result.percentage > self.max_pct:
            self.max_pct = result.percentage

        if result.passed:
            self.passed += 1
        if result.is_fully_complete:
            self.fully_complete += 1

        # group scores
        for grp, score in result.group_scores.items():
            if grp not in self._group_accum:
                self._group_accum[grp] = {"sum": 0.0, "min": 100.0, "max": 0.0}
            acc = self._group_accum[grp]
            acc["sum"] += score
            if score < acc["min"]:
                acc["min"] = score
            if score > acc["max"]:
                acc["max"] = score

        # field fill rates
        for fr in result.field_results:
            if fr.field_name not in self._field_accum:
                self._field_accum[fr.field_name] = {"passed": 0, "total": 0}
            self._field_accum[fr.field_name]["total"] += 1
            if fr.passed:
                self._field_accum[fr.field_name]["passed"] += 1

    def finalize(self) -> BatchCompletenessResult:
        n = self.total
        if n == 0:
            return BatchCompletenessResult.empty()

        _pcts_sorted = sorted(self._pcts)
        mid = n // 2
        median = (
            (_pcts_sorted[mid] + _pcts_sorted[mid - 1]) / 2
            if n % 2 == 0
            else _pcts_sorted[mid]
        )

        # group summary
        group_summary: dict[str, dict[str, float]] = {}
        for grp, acc in self._group_accum.items():
            group_summary[grp] = {
                "avg": round(acc["sum"] / n, 1),
                "min": round(acc["min"], 1),
                "max": round(acc["max"], 1),
            }

        # field summary
        field_summary: dict[str, dict[str, Any]] = {}
        for fname, acc in self._field_accum.items():
            profile = FIELD_PROFILE.get(fname)
            field_summary[fname] = {
                "label_fa" : profile.label_fa if profile else fname,
                "group"    : profile.group.value if profile else "unknown",
                "weight"   : profile.weight if profile else 0,
                "required" : profile.required if profile else False,
                "passed"   : acc["passed"],
                "total"    : acc["total"],
                "fill_rate": round(acc["passed"] * 100 / acc["total"], 1),
            }

        return BatchCompletenessResult(
            total_stores          = n,
            evaluated_stores      = n,
            passed_stores         = self.passed,
            fully_complete_stores = self.fully_complete,
            overall_percentage    = round(self.sum_pct / n, 1),
            average_raw_score     = round(self.sum_raw / n, 1),
            median_percentage     = round(median, 1),
            min_percentage        = round(self.min_pct, 1) if self.min_pct != float("inf") else 0.0,
            max_percentage        = round(self.max_pct, 1) if self.max_pct != float("-inf") else 0.0,
            group_summary         = group_summary,
            field_summary         = field_summary,
        )


@dataclass(frozen=True, slots=True)
class BatchCompletenessResult:
    total_stores:          int
    evaluated_stores:      int
    passed_stores:         int
    fully_complete_stores: int
    overall_percentage:    float
    average_raw_score:     float
    median_percentage:     float
    min_percentage:        float
    max_percentage:        float
    group_summary:         dict[str, dict[str, float]]
    field_summary:         dict[str, dict[str, Any]]

    @classmethod
    def empty(cls) -> "BatchCompletenessResult":
        return cls(
            total_stores=0, evaluated_stores=0, passed_stores=0,
            fully_complete_stores=0, overall_percentage=0.0,
            average_raw_score=0.0, median_percentage=0.0,
            min_percentage=0.0, max_percentage=0.0,
            group_summary={}, field_summary={},
        )


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                        S E R V I C E                                     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class CompletenessService:
    """Stateless completeness evaluator. NO DB, NO Session, NO business logic."""

    def evaluate(self, store: Store) -> CompletenessResult:
        field_results: list[FieldResult] = []
        missing: list[str] = []
        warnings: list[str] = []

        for fname, profile in FIELD_PROFILE.items():
            raw     = getattr(store, fname, None)
            verdict = profile.validate(raw)

            field_results.append(FieldResult(
                field_name=fname,
                label_fa=profile.label_fa,
                group=profile.group,
                weight=profile.weight,
                verdict=verdict,
                required=profile.required,
                current_value=raw,
            ))

            if verdict == ValidationVerdict.INVALID:
                if profile.required:
                    missing.append(f"{profile.label_fa} ثبت نشده")
                else:
                    missing.append(f"{profile.label_fa} نامعتبر")
            elif verdict == ValidationVerdict.WARNING:
                warnings.append(f"{profile.label_fa} نیازمند بازبینی")

        raw_score  = sum(fr.weight for fr in field_results if fr.passed)
        percentage = round(raw_score * 100 / _TOTAL_WEIGHT, 1) if _TOTAL_WEIGHT else 0.0
        all_required_ok = all(fr.passed for fr in field_results if fr.required)
        all_ok          = all(fr.passed for fr in field_results)

        group_scores: dict[str, float] = {}
        for grp in FieldGroup:
            gw = _GROUP_WEIGHTS.get(grp, 1)
            gs = sum(fr.weight for fr in field_results if fr.group == grp and fr.passed)
            group_scores[grp.value] = round(gs * 100 / gw, 1) if gw else 0.0

        return CompletenessResult(
            store_id          = store.id,
            canonical_name    = store.canonical_name,
            raw_score         = raw_score,
            total_weight      = _TOTAL_WEIGHT,
            percentage        = percentage,
            passed            = all_required_ok,
            is_fully_complete = all_ok,
            field_results     = tuple(field_results),
            missing_fields    = tuple(missing),
            warnings          = tuple(warnings),
            group_scores      = group_scores,
        )

    def create_accumulator(self) -> BatchAccumulator:
        """یک BatchAccumulator نو بساز."""
        return BatchAccumulator()
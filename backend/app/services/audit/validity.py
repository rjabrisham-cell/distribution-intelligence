# ============================================================================
# Distribution Intelligence Platform (DIP)
# Sprint 2 – Data Quality Audit Engine
# Contract v1.2 (Frozen)
#
# Validity Audit – PURE, Stateless, NO DB, NO Business Decisions.
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
from app.core.validity_rules import (
    VALIDITY_RULES,
    VERDICT_PRIORITY,
    ValidityRule,
)
from app.models.store import Store


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                        R E S U L T   D T O s                             ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@dataclass(frozen=True, slots=True)
class ValidityFieldResult:
    field_name:    str
    label_fa:      str
    group:         FieldGroup
    weight:        int
    verdict:       ValidationVerdict
    required:      bool
    current_value: Any = field(repr=False)

    @property
    def is_valid(self) -> bool:
        return self.verdict == ValidationVerdict.VALID

    @property
    def is_invalid(self) -> bool:
        return self.verdict == ValidationVerdict.INVALID


@dataclass(frozen=True, slots=True)
class ValidityResult:
    store_id:          int
    shop_name:         str
    raw_score:         int           # sum of weights of VALID fields
    scored_weight:     int           # denominator: only fields not UNKNOWN
    total_weight:      int           # absolute max (all fields)
    percentage:        float         # raw_score / scored_weight * 100
    passed:            bool          # all required fields valid?
    is_fully_valid:    bool          # every non-UNKNOWN field has VALID verdict?
    field_results:     tuple[ValidityFieldResult, ...]
    invalid_fields:    tuple[str, ...]
    warnings:          tuple[str, ...]
    unknown_fields:    tuple[str, ...]
    group_scores:      dict[str, float]
    rule_results:      dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata:          dict[str, Any]             = field(default_factory=dict)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║             B A T C H   A C C U M U L A T O R   (Incremental)           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

@dataclass
class ValidityBatchAccumulator:
    """
    Incremental batch aggregator – O(1) per update, constant RAM.
    """
    total:       int = 0
    passed:      int = 0
    fully_valid: int = 0
    sum_raw:     float = 0.0
    sum_pct:     float = 0.0
    min_pct:     float = float("inf")
    max_pct:     float = float("-inf")

    # verdict counters (useful for dashboard later)
    invalid_count: int = 0
    warning_count: int = 0
    unknown_count: int = 0

    _pcts: list[float] = field(default_factory=list)

    # group aggregates
    _group_accum: dict[str, dict[str, float]] = field(default_factory=dict)

    # field validity rate
    _field_accum: dict[str, dict[str, int]] = field(default_factory=dict)

    def update(self, result: ValidityResult) -> None:
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
        if result.is_fully_valid:
            self.fully_valid += 1

        # verdict counters
        self.invalid_count += len(result.invalid_fields)
        self.warning_count += len(result.warnings)
        self.unknown_count += len(result.unknown_fields)

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

        # field rates
        for fr in result.field_results:
            fname = fr.field_name
            if fname not in self._field_accum:
                self._field_accum[fname] = {"valid": 0, "total": 0}
            self._field_accum[fname]["total"] += 1
            if fr.is_valid:
                self._field_accum[fname]["valid"] += 1

    def finalize(self) -> BatchValidityResult:
        n = self.total
        if n == 0:
            return BatchValidityResult.empty()

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
                "label_fa"    : profile.label_fa if profile else fname,
                "group"       : profile.group.value if profile else "unknown",
                "weight"      : profile.weight if profile else 0,
                "required"    : profile.required if profile else False,
                "valid_count" : acc["valid"],
                "total"       : acc["total"],
                "validity_rate": round(acc["valid"] * 100 / acc["total"], 1),
            }

        return BatchValidityResult(
            total_stores          = n,
            evaluated_stores      = n,
            passed_stores         = self.passed,
            fully_valid_stores    = self.fully_valid,
            overall_percentage    = round(self.sum_pct / n, 1),
            average_raw_score     = round(self.sum_raw / n, 1),
            median_percentage     = round(median, 1),
            min_percentage        = round(self.min_pct, 1) if self.min_pct != float("inf") else 0.0,
            max_percentage        = round(self.max_pct, 1) if self.max_pct != float("-inf") else 0.0,
            invalid_field_count   = self.invalid_count,
            warning_field_count   = self.warning_count,
            unknown_field_count   = self.unknown_count,
            group_summary         = group_summary,
            field_summary         = field_summary,
        )


@dataclass(frozen=True, slots=True)
class BatchValidityResult:
    total_stores:          int
    evaluated_stores:      int
    passed_stores:         int
    fully_valid_stores:    int
    overall_percentage:    float
    average_raw_score:     float
    median_percentage:     float
    min_percentage:        float
    max_percentage:        float
    invalid_field_count:   int
    warning_field_count:   int
    unknown_field_count:   int
    group_summary:         dict[str, dict[str, float]]
    field_summary:         dict[str, dict[str, Any]]

    @classmethod
    def empty(cls) -> "BatchValidityResult":
        return cls(
            total_stores=0, evaluated_stores=0, passed_stores=0,
            fully_valid_stores=0, overall_percentage=0.0,
            average_raw_score=0.0, median_percentage=0.0,
            min_percentage=0.0, max_percentage=0.0,
            invalid_field_count=0, warning_field_count=0, unknown_field_count=0,
            group_summary={}, field_summary={},
        )


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                     V A L I D I T Y   S E R V I C E                     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class ValidityService:
    """
    Stateless validity evaluator. Zero dependencies on DB/Session/UI.

    Key design decisions
    --------------------
    - UNKNOWN verdicts are EXCLUDED from the score denominator.
      An UNKNOWN means "insufficient information to judge" — it should
      neither help nor hurt the score.
    - Rule priority (from VERDICT_PRIORITY) is used when multiple rules
      return a verdict for the same field.
    """

    def evaluate(self, store: Store) -> ValidityResult:
        # ── 1. Run all rules and collect per-field verdicts ──────────────
        raw_verdicts:  dict[str, ValidationVerdict] = {}
        rule_meta:     dict[str, dict[str, Any]]    = {}

        for rule in VALIDITY_RULES:
            try:
                verdicts = rule.check(store)
            except Exception:
                raise  # fail-fast
            rule_meta[rule.rule_name] = {
                "description": rule.description,
                "metadata"   : rule.metadata,
                "verdicts"   : dict(verdicts),
            }
            for fname, v in verdicts.items():
                current = raw_verdicts.get(fname)
                if current is None or VERDICT_PRIORITY[v] > VERDICT_PRIORITY[current]:
                    raw_verdicts[fname] = v

        # ── 2. Build field results using FIELD_PROFILE for weight/group ──
        field_results: list[ValidityFieldResult] = []
        invalid_names: list[str] = []
        warning_names: list[str] = []
        unknown_names: list[str] = []

        for fname, profile in FIELD_PROFILE.items():
            verdict = raw_verdicts.get(fname, ValidationVerdict.UNKNOWN)
            raw_val = getattr(store, fname, None)

            field_results.append(ValidityFieldResult(
                field_name   = fname,
                label_fa     = profile.label_fa,
                group        = profile.group,
                weight       = profile.weight,
                verdict      = verdict,
                required     = profile.required,
                current_value = raw_val,
            ))

            if verdict == ValidationVerdict.INVALID:
                invalid_names.append(f"{profile.label_fa} نامعتبر است")
            elif verdict == ValidationVerdict.WARNING:
                warning_names.append(f"{profile.label_fa} نیازمند بازبینی")
            elif verdict == ValidationVerdict.UNKNOWN:
                unknown_names.append(profile.label_fa)

        # ── 3. Scoring ───────────────────────────────────────────────────
        # Only fields with a KNOWN verdict (VALID, WARNING, INVALID) count
        # toward the denominator.  UNKNOWN fields are excluded entirely.
        raw_score    = sum(fr.weight for fr in field_results if fr.is_valid)
        scored_weight = sum(
            fr.weight for fr in field_results
            if fr.verdict != ValidationVerdict.UNKNOWN
        )
        percentage = (
            round(raw_score * 100 / scored_weight, 1)
            if scored_weight > 0
            else 100.0
        )

        all_required_valid = all(
            fr.is_valid for fr in field_results if fr.required
        )
        # "fully valid" = no INVALID verdict among known fields
        all_valid = all(
            fr.is_valid
            for fr in field_results
            if fr.verdict != ValidationVerdict.UNKNOWN
        )

        group_scores: dict[str, float] = {}
        for grp in FieldGroup:
            gw = _GROUP_WEIGHTS.get(grp, 1)
            gs = sum(
                fr.weight for fr in field_results
                if fr.group == grp and fr.is_valid
            )
            group_scores[grp.value] = round(gs * 100 / gw, 1) if gw else 0.0

        return ValidityResult(
            store_id       = store.id,
            shop_name      = store.shop_name,
            raw_score      = raw_score,
            scored_weight  = scored_weight,
            total_weight   = _TOTAL_WEIGHT,
            percentage     = percentage,
            passed         = all_required_valid,
            is_fully_valid = all_valid,
            field_results  = tuple(field_results),
            invalid_fields = tuple(invalid_names),
            warnings       = tuple(warning_names),
            unknown_fields = tuple(unknown_names),
            group_scores   = group_scores,
            rule_results   = rule_meta,
        )

    def create_accumulator(self) -> ValidityBatchAccumulator:
        return ValidityBatchAccumulator()

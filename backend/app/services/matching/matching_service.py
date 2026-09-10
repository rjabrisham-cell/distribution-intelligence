"""
Distribution Intelligence Platform (DIP)
Matching Engine — Pure Orchestration Service

Stage 6
=======

Pure orchestration layer for the matching pipeline.

Responsibilities
----------------
- Coordinate CandidatePool -> scoring -> ranking -> decision.
- Support single-record matching.
- Support in-memory batch matching.
- Aggregate matching results.
- Produce no database side effects.

Out of scope
------------
- SQLAlchemy / ORM
- Database sessions or queries
- Persistence
- Geo services
- Audit services
- Import services
- Normalization
- Candidate retrieval
- Scoring implementation
- Threshold implementation
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict
from time import perf_counter
from typing import Any

from app.services.matching.matching_models import (
    CandidatePool,
    MasterStoreRecord,
    MatchingDecision,
    MatchingRunStats,
    PairScore,
    PreparedInput,
)
from app.services.matching.matching_scoring_service import (
    MatchingScoringService,
)


# ============================================================================
# Stable orchestration labels
# ============================================================================

STATUS_PRECISE = "PRECISE"
STATUS_SUGGESTED = "SUGGESTED"
STATUS_UNRESOLVED = "UNRESOLVED"

METHOD_NO_CANDIDATE_POOL = "no_candidate_pool"


# ============================================================================
# Helpers
# ============================================================================


def _status_text(value: object) -> str:
    if value is None:
        return ""

    raw = getattr(value, "value", value)

    return str(raw).strip().upper()


def _safe_score(value: object) -> float:
    if value is None:
        return 0.0

    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0

    if result != result:
        return 0.0

    if result in (float("inf"), float("-inf")):
        return 0.0

    return result


def _pair_score_value(pair_score: PairScore) -> float:
    return _safe_score(
        getattr(
            pair_score,
            "total_score",
            getattr(pair_score, "score", 0.0),
        )
    )


def _pair_master_store_id(pair_score: PairScore) -> int:
    value = getattr(pair_score, "master_store_id", 0)

    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _decision_method(decision: MatchingDecision) -> str:
    value = getattr(decision, "method", None)

    if value is None:
        value = getattr(decision, "match_method", None)

    if value is None:
        return ""

    return str(value).strip()


def _decision_score(decision: MatchingDecision) -> float:
    value = getattr(decision, "score", None)

    if value is None:
        value = getattr(decision, "confidence_score", None)

    return _safe_score(value)


def _decision_master_store_id(
    decision: MatchingDecision,
) -> int | None:
    value = getattr(decision, "matched_store_id", None)

    if value is None:
        value = getattr(decision, "master_store_id", None)

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ============================================================================
# Matching Service
# ============================================================================


class MatchingService:
    """
    Pure matching orchestrator.

    Inputs:
        PreparedInput
        CandidatePool
        MasterStoreRecord DTOs

    Output:
        MatchingDecision

    No database or persistence behavior exists here.
    """

    def __init__(
        self,
        scoring_service: MatchingScoringService | None = None,
    ) -> None:
        self.scoring_service = (
            scoring_service
            if scoring_service is not None
            else MatchingScoringService()
        )

    # ========================================================================
    # Candidate resolution
    # ========================================================================

    @staticmethod
    def resolve_candidate_masters(
        *,
        pool: CandidatePool,
        masters_by_id: Mapping[int, MasterStoreRecord],
    ) -> list[MasterStoreRecord]:
        """
        Resolve CandidatePool IDs against an already-loaded Master Store map.

        Candidate order is preserved.
        Duplicate IDs are ignored.
        Unknown IDs are ignored.

        No database query occurs.
        """

        resolved: list[MasterStoreRecord] = []
        seen: set[int] = set()

        for raw_master_id in pool.master_store_ids:
            try:
                master_id = int(raw_master_id)
            except (TypeError, ValueError):
                continue

            if master_id in seen:
                continue

            master = masters_by_id.get(master_id)

            if master is None:
                continue

            seen.add(master_id)
            resolved.append(master)

        return resolved

    # ========================================================================
    # Pairwise scoring
    # ========================================================================

    def score_candidates(
        self,
        *,
        prepared_input: PreparedInput,
        candidates: Sequence[MasterStoreRecord],
        city_phone_code: str | None = None,
    ) -> list[PairScore]:
        """
        Score all candidates.

        Runtime Stage-4 contract:

            score_pair(
                prepared_input,
                master,
                *,
                city_phone_code=None,
            ) -> PairScore
        """

        scores: list[PairScore] = []

        for candidate in candidates:
            pair_score = self.scoring_service.score_pair(
                prepared_input,
                candidate,
                city_phone_code=city_phone_code,
            )

            scores.append(pair_score)

        return scores

    # ========================================================================
    # Ranking
    # ========================================================================

    @staticmethod
    def rank_scores(
        scores: Iterable[PairScore],
    ) -> list[PairScore]:
        """
        Rank candidate scores deterministically.

        Primary:
            score descending

        Secondary:
            master_store_id ascending
        """

        return sorted(
            scores,
            key=lambda item: (
                -_pair_score_value(item),
                _pair_master_store_id(item),
            ),
        )

    # ========================================================================
    # Decision
    # ========================================================================

    def decide(
        self,
        *,
        prepared_input: PreparedInput,
        ranked_scores: Sequence[PairScore],
    ) -> MatchingDecision:
        """
        Delegate the final decision to Stage 4.

        Runtime Stage-4 contract:

            decide(
                *,
                prepared_input,
                scores,
            ) -> MatchingDecision

        Threshold, margin and safety rules are NOT duplicated here.
        """

        return self.scoring_service.decide(
            prepared_input=prepared_input,
            scores=ranked_scores,
        )

    # ========================================================================
    # Empty candidate gate
    # ========================================================================

    @staticmethod
    def _no_candidate_decision(
        *,
        prepared_input: PreparedInput,
    ) -> MatchingDecision:
        """
        Return deterministic UNRESOLVED when no candidate exists.

        Empty candidate pool is an orchestration condition, not a scoring
        decision.
        """

        return MatchingDecision(
            address_candidate_id=prepared_input.address_candidate_id,
            company_store_id=prepared_input.company_store_id,
            matched_store_id=None,
            status=STATUS_UNRESOLVED,
            score=0.0,
            method=METHOD_NO_CANDIDATE_POOL,
            top_score=None,
            second_score=None,
            metadata={
                "reason": METHOD_NO_CANDIDATE_POOL,
                "candidate_count": 0,
            },
        )

    # ========================================================================
    # Single match
    # ========================================================================

    def match_one(
        self,
        *,
        pool: CandidatePool,
        masters_by_id: Mapping[int, MasterStoreRecord],
        city_phone_code: str | None = None,
    ) -> MatchingDecision:
        """
        Execute the complete pure matching pipeline for one CandidatePool.

        Flow:
            CandidatePool
                -> resolve candidates
                -> empty-pool gate
                -> score_pair()
                -> rank
                -> decide()
                -> MatchingDecision
        """

        prepared_input = pool.input

        candidates = self.resolve_candidate_masters(
            pool=pool,
            masters_by_id=masters_by_id,
        )

        # ------------------------------------------------------------------
        # Empty candidate gate
        # ------------------------------------------------------------------

        if not candidates:
            return self._no_candidate_decision(
                prepared_input=prepared_input,
            )

        # ------------------------------------------------------------------
        # Pairwise scoring
        # ------------------------------------------------------------------

        scores = self.score_candidates(
            prepared_input=prepared_input,
            candidates=candidates,
            city_phone_code=city_phone_code,
        )

        if not scores:
            return self._no_candidate_decision(
                prepared_input=prepared_input,
            )

        # ------------------------------------------------------------------
        # Ranking
        # ------------------------------------------------------------------

        ranked_scores = self.rank_scores(scores)

        # ------------------------------------------------------------------
        # Final decision — delegated to Stage 4
        # ------------------------------------------------------------------

        return self.decide(
            prepared_input=prepared_input,
            ranked_scores=ranked_scores,
        )

    # ========================================================================
    # Batch matching
    # ========================================================================

    def match_batch(
        self,
        *,
        pools: Iterable[CandidatePool],
        masters_by_id: Mapping[int, MasterStoreRecord],
        city_phone_code: str | None = None,
    ) -> list[MatchingDecision]:
        """
        Match multiple CandidatePools entirely in memory.

        Input order is preserved.

        No database access.
        No persistence.
        No side effects.
        """

        decisions: list[MatchingDecision] = []

        for pool in pools:
            decision = self.match_one(
                pool=pool,
                masters_by_id=masters_by_id,
                city_phone_code=city_phone_code,
            )

            decisions.append(decision)

        return decisions

    # ========================================================================
    # Summary
    # ========================================================================

    @staticmethod
    def summarize(
        decisions: Iterable[MatchingDecision],
    ) -> dict[str, Any]:
        """
        Aggregate pure matching statistics.
        """

        decision_list = list(decisions)

        status_counter: Counter[str] = Counter()
        method_counter: Counter[str] = Counter()

        precise = 0
        suggested = 0
        unresolved = 0

        matched = 0
        unmatched = 0

        score_total = 0.0
        scored_count = 0

        for decision in decision_list:
            status = _status_text(
                getattr(decision, "status", None)
            )

            if not status:
                status = "UNKNOWN"

            status_counter[status] += 1

            if status == STATUS_PRECISE:
                precise += 1

            elif status == STATUS_SUGGESTED:
                suggested += 1

            elif status == STATUS_UNRESOLVED:
                unresolved += 1

            method = _decision_method(decision)

            if not method:
                method = "unknown"

            method_counter[method] += 1

            master_store_id = _decision_master_store_id(
                decision
            )

            if master_store_id is None:
                unmatched += 1
            else:
                matched += 1

            score = _decision_score(decision)

            if score > 0.0:
                score_total += score
                scored_count += 1

        total = len(decision_list)

        average_score = (
            score_total / scored_count
            if scored_count
            else 0.0
        )

        return {
            "total": total,
            "precise": precise,
            "suggested": suggested,
            "unresolved": unresolved,
            "matched": matched,
            "unmatched": unmatched,
            "status_distribution": dict(
                sorted(status_counter.items())
            ),
            "method_distribution": dict(
                sorted(method_counter.items())
            ),
            "average_score": average_score,
        }

    # ========================================================================
    # Complete in-memory run
    # ========================================================================

    def run(
        self,
        *,
        pools: Iterable[CandidatePool],
        masters_by_id: Mapping[int, MasterStoreRecord],
        city_phone_code: str | None = None,
    ) -> tuple[
        list[MatchingDecision],
        dict[str, Any],
    ]:
        """
        Execute a complete in-memory matching run.

        Returns:
            (
                decisions,
                summary,
            )
        """

        started_at = perf_counter()

        decisions = self.match_batch(
            pools=pools,
            masters_by_id=masters_by_id,
            city_phone_code=city_phone_code,
        )

        summary = self.summarize(decisions)

        summary["elapsed_seconds"] = max(
            0.0,
            perf_counter() - started_at,
        )

        return decisions, summary


# ============================================================================
# MatchingRunStats adapter
# ============================================================================


def build_matching_run_stats(
    decisions: Iterable[MatchingDecision],
    *,
    elapsed_seconds: float = 0.0,
) -> MatchingRunStats:
    """
    Convert MatchingDecision objects to the frozen MatchingRunStats DTO.

    Only fields actually present on MatchingRunStats are populated.
    """

    decision_list = list(decisions)

    precise = 0
    suggested = 0
    unresolved = 0
    failed = 0

    for decision in decision_list:
        status = _status_text(
            getattr(decision, "status", None)
        )

        if status == STATUS_PRECISE:
            precise += 1

        elif status == STATUS_SUGGESTED:
            suggested += 1

        elif status == STATUS_UNRESOLVED:
            unresolved += 1

        elif status:
            failed += 1

    available_fields = getattr(
        MatchingRunStats,
        "__dataclass_fields__",
        {},
    )

    possible_values: dict[str, Any] = {
        "total": len(decision_list),
        "processed": len(decision_list),
        "precise": precise,
        "suggested": suggested,
        "unresolved": unresolved,
        "failed": failed,
        "elapsed_seconds": max(
            0.0,
            float(elapsed_seconds),
        ),
    }

    values: dict[str, Any] = {}

    for field_name, value in possible_values.items():
        if field_name in available_fields:
            values[field_name] = value

    return MatchingRunStats(**values)


# ============================================================================
# Functional convenience API
# ============================================================================


def match_one(
    *,
    pool: CandidatePool,
    masters_by_id: Mapping[int, MasterStoreRecord],
    city_phone_code: str | None = None,
    scoring_service: MatchingScoringService | None = None,
) -> MatchingDecision:
    """
    Functional wrapper for single-record matching.
    """

    service = MatchingService(
        scoring_service=scoring_service
    )

    return service.match_one(
        pool=pool,
        masters_by_id=masters_by_id,
        city_phone_code=city_phone_code,
    )


def match_batch(
    *,
    pools: Iterable[CandidatePool],
    masters_by_id: Mapping[int, MasterStoreRecord],
    city_phone_code: str | None = None,
    scoring_service: MatchingScoringService | None = None,
) -> list[MatchingDecision]:
    """
    Functional wrapper for batch matching.
    """

    service = MatchingService(
        scoring_service=scoring_service
    )

    return service.match_batch(
        pools=pools,
        masters_by_id=masters_by_id,
        city_phone_code=city_phone_code,
    )


def decision_to_dict(
    decision: MatchingDecision,
) -> dict[str, Any]:
    """
    Convert MatchingDecision into a plain Python dictionary.

    Useful for:
    - tests
    - logging
    - API adapters
    - outer persistence wrapper

    No persistence occurs here.
    """

    try:
        return asdict(decision)

    except TypeError:
        return {
            "address_candidate_id": getattr(
                decision,
                "address_candidate_id",
                None,
            ),
            "company_store_id": getattr(
                decision,
                "company_store_id",
                None,
            ),
            "matched_store_id": _decision_master_store_id(
                decision
            ),
            "status": _status_text(
                getattr(decision, "status", None)
            ),
            "score": _decision_score(decision),
            "method": _decision_method(decision),
            "top_score": getattr(
                decision,
                "top_score",
                None,
            ),
            "second_score": getattr(
                decision,
                "second_score",
                None,
            ),
            "metadata": getattr(
                decision,
                "metadata",
                {},
            ),
        }


# ============================================================================
# Public API
# ============================================================================


__all__ = [
    "STATUS_PRECISE",
    "STATUS_SUGGESTED",
    "STATUS_UNRESOLVED",
    "METHOD_NO_CANDIDATE_POOL",
    "MatchingService",
    "build_matching_run_stats",
    "match_one",
    "match_batch",
    "decision_to_dict",
]
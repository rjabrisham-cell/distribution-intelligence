"""
DIP Matching Engine — Scoring Service

Pure, deterministic scoring engine for Candidate <-> Master Store pairs.

Responsibilities
----------------
- string similarity scoring
- coordinate proximity scoring
- phone exact-match scoring
- dynamic evidence-weighted aggregation
- PRECISE corroborating-evidence safety gate
- decision ranking
- PRECISE / SUGGESTED / UNRESOLVED classification
- match-method label generation

Non-responsibilities
--------------------
- database access
- SQLAlchemy ORM access
- candidate retrieval
- spatial indexing
- persistence
- creation/modification of Master Store records

IMPORTANT
---------
This module is part of the behavior-preserving Matching refactor.

Frozen decision contract:

    PRECISE_THRESHOLD   = 0.90
    SUGGESTED_THRESHOLD = 0.72
    MIN_DECISION_MARGIN = 0.08

Frozen evidence weights:

    coordinates = 0.40
    name        = 0.30
    phone       = 0.20
    address     = 0.10

A high aggregate score alone is NOT sufficient for automatic PRECISE
linking. The PRECISE safety gate must also pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Final, Sequence

from app.services.matching.matching_constants import (
    ADDRESS_WEIGHT,
    COORDINATE_WEIGHT,
    EVIDENCE_ADDRESS,
    EVIDENCE_GEO,
    EVIDENCE_NAME,
    EVIDENCE_PHONE,
    MATCH_METHOD_PRECISE_PREFIX,
    MATCH_METHOD_SUGGESTED_PREFIX,
    MATCH_METHOD_UNRESOLVED_PREFIX,
    MIN_DECISION_MARGIN,
    NAME_WEIGHT,
    PHONE_WEIGHT,
    PRECISE_GEO_DISTANCE_METERS,
    PRECISE_GEO_NAME_MIN_SCORE,
    PRECISE_NAME_ADDRESS_ADDRESS_MIN_SCORE,
    PRECISE_NAME_ADDRESS_NAME_MIN_SCORE,
    PRECISE_THRESHOLD,
    SUGGESTED_THRESHOLD,
)
from app.services.matching.matching_models import (
    MasterStoreRecord,
    MatchingDecision,
    PairScore,
    PreparedInput,
)
from app.services.matching.matching_utils import (
    haversine_distance_meters,
    normalize_phone,
    normalize_text,
)


# ============================================================================
# Coordinate scoring constants
# ============================================================================
#
# These values preserve the scoring profile used by the current Matching
# baseline:
#
#   <= 80m      -> 1.00
#   <= 250m     -> 0.90
#   250-1500m   -> linear decay 0.90 -> 0.20
#   > 1500m     -> 0.00
#
# They remain local to the scoring implementation for now because they are
# scoring mechanics rather than public subsystem configuration.
# ============================================================================

_DISTANCE_VERY_CLOSE_METERS: Final[float] = 80.0
_DISTANCE_NEAR_METERS: Final[float] = 250.0
_DISTANCE_MAX_USEFUL_METERS: Final[float] = 1500.0

_NEAR_SCORE: Final[float] = 0.90
_DECAY_MIN_SCORE: Final[float] = 0.20

_DECAY_DISTANCE_RANGE_METERS: Final[float] = (
    _DISTANCE_MAX_USEFUL_METERS
    - _DISTANCE_NEAR_METERS
)

_DECAY_SCORE_RANGE: Final[float] = (
    _NEAR_SCORE
    - _DECAY_MIN_SCORE
)


# ============================================================================
# Internal score bundle
# ============================================================================


@dataclass(slots=True, frozen=True)
class _ScoreEvidence:
    """
    Internal evidence container used while scoring one pair.

    None means the evidence component was unavailable.

    A numeric 0.0 means the evidence existed but did not support the match.
    """

    name_score: float | None
    phone_score: float | None
    address_score: float | None
    coordinate_score: float | None
    distance_meters: float | None


# ============================================================================
# Generic helpers
# ============================================================================


def clamp_score(value: float) -> float:
    """
    Clamp a numeric score to the matching confidence range [0.0, 1.0].
    """

    if value <= 0.0:
        return 0.0

    if value >= 1.0:
        return 1.0

    return value


def round_score(
    value: float,
    digits: int = 4,
) -> float:
    """
    Clamp and round a score for stable persistence/reporting.

    AddressCandidate.match_score uses NUMERIC(5,4), therefore the public
    matching score is kept at four decimal places.
    """

    return round(
        clamp_score(value),
        digits,
    )


# ============================================================================
# String similarity
# ============================================================================


def calculate_string_similarity(
    left: str | None,
    right: str | None,
) -> float | None:
    """
    Calculate normalized text similarity.

    Returns
    -------
    None
        when either side has no usable text.

    1.0
        for exact normalized equality.

    0.0 .. 1.0
        SequenceMatcher similarity otherwise.

    Notes
    -----
    Normalization is conservative and comes from matching_utils.normalize_text.
    Business suffix removal or aggressive token rewriting is intentionally
    NOT performed during this behavior-preserving phase.
    """

    normalized_left = normalize_text(left)
    normalized_right = normalize_text(right)

    if not normalized_left or not normalized_right:
        return None

    if normalized_left == normalized_right:
        return 1.0

    return clamp_score(
        SequenceMatcher(
            None,
            normalized_left,
            normalized_right,
            autojunk=False,
        ).ratio()
    )


# ============================================================================
# Phone scoring
# ============================================================================


def calculate_phone_score(
    candidate_phone: str | None,
    master_phone: str | None,
    city_phone_code: str | None = None,
) -> float | None:
    """
    Compare normalized phone numbers.

    Phone evidence is binary:

        exact normalized match -> 1.0
        different usable phone -> 0.0
        missing evidence        -> None

    No geographic prefix is guessed. city_phone_code must be supplied by the
    caller when it is known.
    """

    normalized_candidate = normalize_phone(
        candidate_phone,
        city_phone_code,
    )

    normalized_master = normalize_phone(
        master_phone,
        city_phone_code,
    )

    if not normalized_candidate or not normalized_master:
        return None

    if normalized_candidate == normalized_master:
        return 1.0

    return 0.0


# ============================================================================
# Coordinate scoring
# ============================================================================


def calculate_coordinate_score(
    distance_meters: float | None,
) -> float | None:
    """
    Convert geographic distance to coordinate evidence score.

    Current scoring profile:

        distance <= 80m
            1.00

        80m < distance <= 250m
            0.90

        250m < distance <= 1500m
            linear decay from 0.90 to 0.20

        distance > 1500m
            0.00

        distance unavailable
            None

    Missing coordinate evidence is excluded from the dynamic denominator.
    """

    if distance_meters is None:
        return None

    if distance_meters < 0.0:
        return None

    if distance_meters <= _DISTANCE_VERY_CLOSE_METERS:
        return 1.0

    if distance_meters <= _DISTANCE_NEAR_METERS:
        return _NEAR_SCORE

    if distance_meters <= _DISTANCE_MAX_USEFUL_METERS:
        decay_ratio = (
            distance_meters
            - _DISTANCE_NEAR_METERS
        ) / _DECAY_DISTANCE_RANGE_METERS

        score = (
            _NEAR_SCORE
            - (_DECAY_SCORE_RANGE * decay_ratio)
        )

        return clamp_score(
            max(
                _DECAY_MIN_SCORE,
                score,
            )
        )

    return 0.0


# ============================================================================
# Dynamic weighted aggregation
# ============================================================================


def calculate_weighted_score(
    *,
    coordinate_score: float | None,
    name_score: float | None,
    phone_score: float | None,
    address_score: float | None,
) -> float:
    """
    Calculate the evidence-weighted aggregate score.

    Missing evidence is excluded from the denominator.

    Example
    -------
    If coordinates and phone are missing but name/address exist:

        numerator =
            name_score    * 0.30
            +
            address_score * 0.10

        denominator =
            0.30 + 0.10

    This avoids treating unavailable evidence as negative evidence.
    """

    weighted_total = 0.0
    active_weight = 0.0

    components = (
        (
            coordinate_score,
            COORDINATE_WEIGHT,
        ),
        (
            name_score,
            NAME_WEIGHT,
        ),
        (
            phone_score,
            PHONE_WEIGHT,
        ),
        (
            address_score,
            ADDRESS_WEIGHT,
        ),
    )

    for score, weight in components:
        if score is None:
            continue

        weighted_total += (
            clamp_score(score)
            * weight
        )

        active_weight += weight

    if active_weight <= 0.0:
        return 0.0

    return round_score(
        weighted_total / active_weight
    )


# ============================================================================
# Evidence helpers
# ============================================================================


def _active_evidence_labels(
    evidence: _ScoreEvidence,
) -> tuple[str, ...]:
    """
    Return positive evidence labels in stable order.

    Stable ordering is important because match_method is persisted and used
    by diagnostics/reporting.
    """

    labels: list[str] = []

    if (
        evidence.coordinate_score is not None
        and evidence.coordinate_score > 0.0
    ):
        labels.append(
            EVIDENCE_GEO
        )

    if (
        evidence.name_score is not None
        and evidence.name_score > 0.0
    ):
        labels.append(
            EVIDENCE_NAME
        )

    if (
        evidence.phone_score is not None
        and evidence.phone_score > 0.0
    ):
        labels.append(
            EVIDENCE_PHONE
        )

    if (
        evidence.address_score is not None
        and evidence.address_score > 0.0
    ):
        labels.append(
            EVIDENCE_ADDRESS
        )

    return tuple(labels)


def build_match_method_label(
    prefix: str,
    evidence: Sequence[str],
) -> str:
    """
    Build the persisted Matching method label.

    Examples
    --------
    precise:geo+name+phone+addr
    suggested:name+addr
    unresolved:name+phone+addr
    """

    suffix = (
        "+".join(evidence)
        if evidence
        else "none"
    )

    return f"{prefix}:{suffix}"


# ============================================================================
# PRECISE safety gate
# ============================================================================


def check_precise_safety_gate(
    *,
    distance_meters: float | None,
    name_score: float | None,
    phone_score: float | None,
    address_score: float | None,
) -> bool:
    """
    Determine whether corroborating evidence is strong enough for PRECISE.

    Important
    ---------
    Aggregate score >= PRECISE_THRESHOLD is NOT sufficient by itself.

    Current confirmed safety rules are:

    1. GEO + NAME
       distance <= 80m
       name similarity >= 0.82

    2. NAME + ADDRESS
       name similarity >= 0.96
       address similarity >= 0.90

    Phone remains part of the weighted score and evidence label. We do not
    introduce additional automatic-link rules here unless they are part of
    the frozen production contract.
    """

    safe_name_score = (
        name_score
        if name_score is not None
        else 0.0
    )

    safe_address_score = (
        address_score
        if address_score is not None
        else 0.0
    )

    # ------------------------------------------------------------------
    # Rule 1 — GEO + NAME
    # ------------------------------------------------------------------

    if (
        distance_meters is not None
        and distance_meters
        <= PRECISE_GEO_DISTANCE_METERS
        and safe_name_score
        >= PRECISE_GEO_NAME_MIN_SCORE
    ):
        return True

    # ------------------------------------------------------------------
    # Rule 2 — NAME + ADDRESS
    # ------------------------------------------------------------------

    if (
        safe_name_score
        >= PRECISE_NAME_ADDRESS_NAME_MIN_SCORE
        and safe_address_score
        >= PRECISE_NAME_ADDRESS_ADDRESS_MIN_SCORE
    ):
        return True

    return False


# ============================================================================
# Pair scoring service
# ============================================================================


class MatchingScoringService:
    """
    Stateless scoring service.

    It can safely be reused by preparation/orchestration code because it has
    no mutable state and no database dependency.
    """

    @staticmethod
    def score_pair(
        prepared_input: PreparedInput,
        master: MasterStoreRecord,
        *,
        city_phone_code: str | None = None,
    ) -> PairScore:
        """
        Score one PreparedInput against one MasterStoreRecord.
        """

        # ------------------------------------------------------------------
        # Coordinates
        # ------------------------------------------------------------------

        distance_meters: float | None = None
        coordinate_score: float | None = None

        if (
            prepared_input.latitude is not None
            and prepared_input.longitude is not None
            and master.latitude is not None
            and master.longitude is not None
        ):
            distance_meters = haversine_distance_meters(
                prepared_input.latitude,
                prepared_input.longitude,
                master.latitude,
                master.longitude,
            )

            coordinate_score = (
                calculate_coordinate_score(
                    distance_meters
                )
            )

        # ------------------------------------------------------------------
        # Name
        # ------------------------------------------------------------------

        candidate_name = (
            prepared_input.normalized_name
            or normalize_text(
                prepared_input.name
            )
        )

        master_name = (
            master.normalized_name
            or normalize_text(
                master.canonical_name
            )
        )

        name_score = (
            calculate_string_similarity(
                candidate_name,
                master_name,
            )
        )

        # ------------------------------------------------------------------
        # Phone
        # ------------------------------------------------------------------

        candidate_phone = (
            prepared_input.normalized_phone
            or normalize_phone(
                prepared_input.phone,
                city_phone_code,
            )
        )

        master_phone = (
            master.normalized_phone
            or normalize_phone(
                master.canonical_phone,
                city_phone_code,
            )
        )

        phone_score: float | None

        if candidate_phone and master_phone:
            phone_score = (
                1.0
                if candidate_phone == master_phone
                else 0.0
            )
        else:
            phone_score = None

        # ------------------------------------------------------------------
        # Address
        # ------------------------------------------------------------------

        candidate_address = (
            prepared_input.normalized_address
            or normalize_text(
                prepared_input.address
            )
        )

        master_address = (
            master.normalized_address
            or normalize_text(
                master.address
            )
        )

        address_score = (
            calculate_string_similarity(
                candidate_address,
                master_address,
            )
        )

        # ------------------------------------------------------------------
        # Aggregate
        # ------------------------------------------------------------------

        total_score = calculate_weighted_score(
            coordinate_score=coordinate_score,
            name_score=name_score,
            phone_score=phone_score,
            address_score=address_score,
        )

        evidence = _ScoreEvidence(
            name_score=name_score,
            phone_score=phone_score,
            address_score=address_score,
            coordinate_score=coordinate_score,
            distance_meters=distance_meters,
        )

        evidence_labels = (
            _active_evidence_labels(
                evidence
            )
        )

        return PairScore(
            master_store_id=master.id,
            total_score=total_score,
            name_score=name_score,
            phone_score=phone_score,
            address_score=address_score,
            coordinate_score=coordinate_score,
            distance_meters=distance_meters,
            evidence=evidence_labels,
        )

    @staticmethod
    def passes_precise_safety_gate(
        score: PairScore,
    ) -> bool:
        """
        Evaluate the PRECISE corroborating-evidence gate for a PairScore.
        """

        return check_precise_safety_gate(
            distance_meters=score.distance_meters,
            name_score=score.name_score,
            phone_score=score.phone_score,
            address_score=score.address_score,
        )

    @staticmethod
    def rank_scores(
        scores: Sequence[PairScore],
    ) -> list[PairScore]:
        """
        Rank candidate scores deterministically.

        Primary key:
            total score descending

        Secondary key:
            geographic distance ascending when available

        Final tie-breaker:
            Master Store ID ascending

        Deterministic ordering prevents unstable decisions when two candidate
        stores have the same aggregate score.
        """

        def sort_key(
            score: PairScore,
        ) -> tuple[float, float, int]:
            distance = (
                score.distance_meters
                if score.distance_meters is not None
                else float("inf")
            )

            return (
                -score.total_score,
                distance,
                score.master_store_id,
            )

        return sorted(
            scores,
            key=sort_key,
        )

    @classmethod
    def decide(
        cls,
        *,
        prepared_input: PreparedInput,
        scores: Sequence[PairScore],
    ) -> MatchingDecision:
        """
        Convert ranked PairScores into the final in-memory Matching decision.

        Decision contract
        -----------------
        PRECISE:
            top score >= 0.90
            AND PRECISE safety gate passes
            AND ambiguity margin is safe

        SUGGESTED:
            top score >= 0.72
            but automatic PRECISE linking is not safe

        UNRESOLVED:
            no candidate or insufficient score

        This method performs no persistence.
        """

        ranked = cls.rank_scores(
            scores
        )

        # ------------------------------------------------------------------
        # No candidate
        # ------------------------------------------------------------------

        if not ranked:
            return MatchingDecision(
                address_candidate_id=(
                    prepared_input.address_candidate_id
                ),
                company_store_id=(
                    prepared_input.company_store_id
                ),
                matched_store_id=None,
                status="UNRESOLVED",
                score=None,
                method=(
                    f"{MATCH_METHOD_UNRESOLVED_PREFIX}:none"
                ),
                top_score=None,
                second_score=None,
                metadata={
                    "reason": "no_candidate_pool",
                },
            )

        top = ranked[0]

        second = (
            ranked[1]
            if len(ranked) > 1
            else None
        )

        # ------------------------------------------------------------------
        # Ambiguity margin
        # ------------------------------------------------------------------

        if second is None:
            decision_margin = 1.0
        else:
            decision_margin = (
                top.total_score
                - second.total_score
            )

        margin_is_safe = (
            second is None
            or decision_margin
            >= MIN_DECISION_MARGIN
        )

        precise_gate_passed = (
            cls.passes_precise_safety_gate(
                top
            )
        )

        # ------------------------------------------------------------------
        # PRECISE
        # ------------------------------------------------------------------

        if (
            top.total_score
            >= PRECISE_THRESHOLD
            and precise_gate_passed
            and margin_is_safe
        ):
            return MatchingDecision(
                address_candidate_id=(
                    prepared_input.address_candidate_id
                ),
                company_store_id=(
                    prepared_input.company_store_id
                ),
                matched_store_id=(
                    top.master_store_id
                ),
                status="PRECISE",
                score=round_score(
                    top.total_score
                ),
                method=build_match_method_label(
                    MATCH_METHOD_PRECISE_PREFIX,
                    top.evidence,
                ),
                top_score=top,
                second_score=second,
                metadata={
                    "decision_margin": round_score(
                        max(
                            0.0,
                            decision_margin,
                        )
                    ),
                    "precise_gate_passed": True,
                },
            )

        # ------------------------------------------------------------------
        # SUGGESTED
        # ------------------------------------------------------------------

        if (
            top.total_score
            >= SUGGESTED_THRESHOLD
        ):
            reason: str

            if (
                top.total_score
                >= PRECISE_THRESHOLD
                and not precise_gate_passed
            ):
                reason = (
                    "precise_safety_gate_failed"
                )

            elif (
                top.total_score
                >= PRECISE_THRESHOLD
                and not margin_is_safe
            ):
                reason = (
                    "ambiguous_top_candidates"
                )

            else:
                reason = (
                    "below_precise_threshold"
                )

            return MatchingDecision(
                address_candidate_id=(
                    prepared_input.address_candidate_id
                ),
                company_store_id=(
                    prepared_input.company_store_id
                ),
                matched_store_id=None,
                status="SUGGESTED",
                score=round_score(
                    top.total_score
                ),
                method=build_match_method_label(
                    MATCH_METHOD_SUGGESTED_PREFIX,
                    top.evidence,
                ),
                top_score=top,
                second_score=second,
                metadata={
                    "reason": reason,
                    "decision_margin": round_score(
                        max(
                            0.0,
                            decision_margin,
                        )
                    ),
                    "precise_gate_passed": (
                        precise_gate_passed
                    ),
                },
            )

        # ------------------------------------------------------------------
        # UNRESOLVED
        # ------------------------------------------------------------------

        return MatchingDecision(
            address_candidate_id=(
                prepared_input.address_candidate_id
            ),
            company_store_id=(
                prepared_input.company_store_id
            ),
            matched_store_id=None,
            status="UNRESOLVED",
            score=round_score(
                top.total_score
            ),
            method=build_match_method_label(
                MATCH_METHOD_UNRESOLVED_PREFIX,
                top.evidence,
            ),
            top_score=top,
            second_score=second,
            metadata={
                "reason": (
                    "below_suggested_threshold"
                ),
                "decision_margin": round_score(
                    max(
                        0.0,
                        decision_margin,
                    )
                ),
                "precise_gate_passed": (
                    precise_gate_passed
                ),
            },
        )
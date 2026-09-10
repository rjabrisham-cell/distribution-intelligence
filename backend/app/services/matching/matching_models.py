"""
DIP Matching Engine — Internal DTOs

Pure Python data structures used by the Matching subsystem.

Rules
-----
1. No SQLAlchemy ORM models are defined here.
2. No database Session is imported here.
3. No service imports are allowed here.
4. These objects are internal DTOs / in-memory structures.
5. Persisted domain state remains owned by:
       Store
       CompanyStore
       ProjectCompanyStore
       AddressCandidate
6. MatchStatus remains owned by app.core.enums.

Keeping this module dependency-light prevents circular imports between
preparation, scoring, and orchestration services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ============================================================================
# Master Store representation
# ============================================================================


@dataclass(slots=True, frozen=True)
class MasterStoreRecord:
    """
    Lightweight in-memory representation of one canonical Master Store.

    This is intentionally NOT an ORM object.

    The preparation layer converts Store ORM rows into these records so that
    retrieval/scoring does not repeatedly touch SQLAlchemy objects.
    """

    id: int

    canonical_name: str | None
    canonical_phone: str | None
    address: str | None

    province_id: int | None
    city_id: int | None

    latitude: float | None
    longitude: float | None

    normalized_name: str = ""
    normalized_phone: str = ""
    normalized_address: str = ""


# ============================================================================
# Master city retrieval index
# ============================================================================


@dataclass(slots=True)
class CityMasterIndex:
    """
    In-memory retrieval index for active Master Stores of one city.

    Exact indexes:
        by_name
        by_phone
        by_address

    Fallback index:
        by_name_token

    Spatial index:
        by_geo_cell

    Values contain Store IDs rather than ORM instances.
    MasterStoreRecord objects are stored once in stores_by_id.
    """

    city_id: int

    stores_by_id: dict[int, MasterStoreRecord] = field(
        default_factory=dict
    )

    by_name: dict[str, list[int]] = field(
        default_factory=dict
    )

    by_phone: dict[str, list[int]] = field(
        default_factory=dict
    )

    by_address: dict[str, list[int]] = field(
        default_factory=dict
    )

    by_name_token: dict[str, list[int]] = field(
        default_factory=dict
    )

    by_geo_cell: dict[tuple[int, int], list[int]] = field(
        default_factory=dict
    )

    def get_store(
        self,
        store_id: int,
    ) -> MasterStoreRecord | None:
        return self.stores_by_id.get(store_id)

    @property
    def store_count(self) -> int:
        return len(self.stores_by_id)

    def clear(self) -> None:
        self.stores_by_id.clear()
        self.by_name.clear()
        self.by_phone.clear()
        self.by_address.clear()
        self.by_name_token.clear()
        self.by_geo_cell.clear()


# ============================================================================
# Prepared input
# ============================================================================


@dataclass(slots=True, frozen=True)
class PreparedInput:
    """
    Normalized representation of one AddressCandidate / CompanyStore pair.

    Raw persisted values remain unchanged in the database.

    normalized_* fields exist only for retrieval and matching.
    """

    address_candidate_id: int
    company_store_id: int

    province_id: int | None
    city_id: int | None

    name: str | None
    phone: str | None
    address: str | None

    latitude: float | None
    longitude: float | None

    normalized_name: str = ""
    normalized_phone: str = ""
    normalized_address: str = ""


# ============================================================================
# Candidate pool
# ============================================================================


@dataclass(slots=True)
class CandidatePool:
    """
    Retrieval output for one input record.

    This object answers only:

        "Which Master Stores should be scored?"

    It does NOT make or persist a matching decision.
    """

    input: PreparedInput

    master_store_ids: list[int] = field(
        default_factory=list
    )

    # Master Store ID -> retrieval evidence/methods.
    #
    # Example:
    # {
    #     120: {"geo", "name"},
    #     501: {"phone"},
    # }
    retrieval_methods: dict[int, set[str]] = field(
        default_factory=dict
    )

    no_candidate_pool: bool = False
    geo_unresolved: bool = False

    def add_candidate(
        self,
        master_store_id: int,
        method: str,
    ) -> None:
        """
        Add a Master Store to the pool without duplicating the Store ID.
        """

        methods = self.retrieval_methods.setdefault(
            master_store_id,
            set(),
        )

        methods.add(method)

        if master_store_id not in self.master_store_ids:
            self.master_store_ids.append(master_store_id)

    @property
    def size(self) -> int:
        return len(self.master_store_ids)


# ============================================================================
# Pair scoring
# ============================================================================


@dataclass(slots=True, frozen=True)
class PairScore:
    """
    Detailed score for one input record against one Master Store.

    None means that evidence was unavailable and therefore must not be
    treated as a numeric zero automatically by the scoring layer.

    This preserves the existing behavior where missing evidence is removed
    from the effective scoring denominator.
    """

    master_store_id: int

    total_score: float

    name_score: float | None
    phone_score: float | None
    address_score: float | None
    coordinate_score: float | None

    distance_meters: float | None

    evidence: tuple[str, ...] = ()


# ============================================================================
# Final decision
# ============================================================================


@dataclass(slots=True)
class MatchingDecision:
    """
    Final in-memory decision before persistence.

    status must correspond to the existing MatchStatus domain values.

    Examples:
        PRECISE
        SUGGESTED
        UNRESOLVED
        MATCHED
    """

    address_candidate_id: int
    company_store_id: int

    matched_store_id: int | None

    status: str
    score: float | None
    method: str

    top_score: PairScore | None = None
    second_score: PairScore | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================================
# Preparation statistics
# ============================================================================


@dataclass(slots=True)
class MatchingPreparationStats:
    """
    Runtime statistics for the Preparation phase.

    This is intentionally independent from persistence/status APIs.
    """

    total: int = 0
    prepared: int = 0

    with_candidate_pool: int = 0
    without_candidate_pool: int = 0

    with_coordinates: int = 0
    without_coordinates: int = 0

    geo_unresolved: int = 0

    exact_name_hits: int = 0
    exact_phone_hits: int = 0
    exact_address_hits: int = 0
    spatial_hits: int = 0
    token_hits: int = 0

    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, int | float]:
        return {
            "total": self.total,
            "prepared": self.prepared,
            "with_candidate_pool": self.with_candidate_pool,
            "without_candidate_pool": self.without_candidate_pool,
            "with_coordinates": self.with_coordinates,
            "without_coordinates": self.without_coordinates,
            "geo_unresolved": self.geo_unresolved,
            "exact_name_hits": self.exact_name_hits,
            "exact_phone_hits": self.exact_phone_hits,
            "exact_address_hits": self.exact_address_hits,
            "spatial_hits": self.spatial_hits,
            "token_hits": self.token_hits,
            "elapsed_seconds": round(
                self.elapsed_seconds,
                4,
            ),
        }


# ============================================================================
# Matching run statistics
# ============================================================================


@dataclass(slots=True)
class MatchingRunStats:
    """
    Statistics returned by one Matching execution.

    Names intentionally follow the existing Matching report contract.
    """

    total: int = 0
    processed: int = 0

    precise: int = 0
    suggested: int = 0
    unresolved: int = 0

    existing_link: int = 0

    failed: int = 0

    geo_unresolved: int = 0
    no_candidate_pool: int = 0

    elapsed_seconds: float = 0.0

    started_at: datetime | None = None
    finished_at: datetime | None = None

    def to_dict(self) -> dict[str, int | float]:
        return {
            "total": self.total,
            "processed": self.processed,
            "precise": self.precise,
            "suggested": self.suggested,
            "unresolved": self.unresolved,
            "existing_link": self.existing_link,
            "failed": self.failed,
            "geo_unresolved": self.geo_unresolved,
            "no_candidate_pool": self.no_candidate_pool,
            "elapsed_seconds": round(
                self.elapsed_seconds,
                4,
            ),
        }
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from time import perf_counter
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import MatchStatus
from app.models.address_candidate import AddressCandidate
from app.models.city import City
from app.models.company_store import CompanyStore
from app.models.project_company_store import ProjectCompanyStore
from app.models.province import Province
from app.models.store import Store
from app.services.matching.matching_models import (
    CandidatePool,
    MasterStoreRecord,
    MatchingDecision,
    PreparedInput,
)
from app.services.matching.matching_preparation_service import (
    MatchingPreparationService,
)
from app.services.matching.matching_service import MatchingService


logger = logging.getLogger(__name__)


# ============================================================================
# Compatibility DTOs
# ============================================================================


@dataclass(slots=True, frozen=True)
class GeoContext:
    province_id: int | None
    city_id: int | None
    phone_code: str | None


@dataclass(slots=True, frozen=True)
class MatchDecision:
    """
    Legacy compatibility DTO.

    Kept intentionally because older code may still import MatchDecision from
    this module.

    The new matching pipeline itself uses MatchingDecision from
    app.services.matching.matching_models.
    """

    status: MatchStatus
    score: Decimal | None
    method: str
    master_store: Store | None = None


# ============================================================================
# Small helpers
# ============================================================================


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_float(value: object) -> float | None:
    if value is None:
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if result != result:
        return None

    if result in (float("inf"), float("-inf")):
        return None

    return result


def _safe_decimal(value: object) -> Decimal | None:
    if value is None:
        return None

    try:
        return Decimal(str(value))
    except Exception:
        return None


def _normalize_status_text(value: object) -> str:
    if value is None:
        return ""

    raw = getattr(value, "value", value)

    return str(raw).strip().upper()


def _match_status_from_decision(
    decision: MatchingDecision,
) -> MatchStatus:
    status = _normalize_status_text(decision.status)

    if status == "PRECISE":
        return MatchStatus.PRECISE

    if status == "MATCHED":
        return MatchStatus.MATCHED

    if status == "SUGGESTED":
        return MatchStatus.SUGGESTED

    if status == "UNMATCHED":
        return MatchStatus.UNMATCHED

    if status == "LOCATED":
        return MatchStatus.LOCATED

    if status == "PENDING":
        return MatchStatus.PENDING

    return MatchStatus.UNRESOLVED


def _chunked(
    values: list[int],
    size: int,
) -> Iterable[list[int]]:
    if size <= 0:
        size = 1000

    for start in range(0, len(values), size):
        yield values[start : start + size]


# ============================================================================
# Store Matching Service
# ============================================================================


class StoreMatchingService:
    """
    DB Adapter / Compatibility Layer for DIP Matching.

    Public compatibility contract
    -----------------------------
        StoreMatchingService(db)

        run_for_batch(
            batch_id,
            project_id,
            *,
            persist=True,
        ) -> dict[str, Any]

    Responsibilities
    ----------------
    - Scope AddressCandidate rows to import batch + project.
    - Bulk-load CompanyStore records.
    - Resolve lightweight geography.
    - Bulk-load active master Store records per required city/province.
    - Convert ORM rows to pure matching DTOs.
    - Delegate candidate preparation to Stage 5.
    - Delegate scoring/decision to Stage 6.
    - Persist MatchingDecision results.
    - Return a backward-compatible matching report.

    Explicitly NOT responsible for
    --------------------------------
    - changing scoring thresholds
    - changing scoring weights
    - external geocoding
    - FIMAP/Nominatim
    - creating master stores
    - changing master stores
    - schema changes
    - audit/readiness scoring
    """

    def __init__(self, db: Session):
        self.db = db

        self.preparation_service = (
            MatchingPreparationService()
        )

        self.matching_service = (
            MatchingService()
        )

        self._geo_cache: dict[
            tuple[str, str],
            GeoContext,
        ] = {}

    # ========================================================================
    # Public API
    # ========================================================================

    def run_for_batch(
        self,
        batch_id: int,
        project_id: int,
        *,
        persist: bool = True,
    ) -> dict[str, Any]:
        """
        Run matching for AddressCandidates belonging to one import batch and
        one project.

        Behavior-preserving source scope
        --------------------------------
        AddressCandidate.source_type == "excel"

        AddressCandidate.source_id starts with:
            import_batch:{batch_id}:row:

        Project scope is additionally enforced through:
            AddressCandidate.company_store_id
                -> ProjectCompanyStore.company_store_id
                -> project_id

        No master Store is created or modified.
        """

        started_at = perf_counter()

        batch_id = int(batch_id)
        project_id = int(project_id)

        source_prefix = (
            f"import_batch:{batch_id}:row:"
        )

        # ------------------------------------------------------------------
        # 1. Project CompanyStore scope
        # ------------------------------------------------------------------

        project_company_store_ids = (
            self._load_project_company_store_ids(
                project_id=project_id
            )
        )

        if not project_company_store_ids:
            return self._empty_report(
                batch_id=batch_id,
                project_id=project_id,
                elapsed_seconds=(
                    perf_counter() - started_at
                ),
            )

        # ------------------------------------------------------------------
        # 2. AddressCandidates
        # ------------------------------------------------------------------

        address_candidates = (
            self._load_address_candidates(
                source_prefix=source_prefix,
                company_store_ids=(
                    project_company_store_ids
                ),
            )
        )

        if not address_candidates:
            return self._empty_report(
                batch_id=batch_id,
                project_id=project_id,
                elapsed_seconds=(
                    perf_counter() - started_at
                ),
            )

        # ------------------------------------------------------------------
        # 3. CompanyStores — one bulk load
        # ------------------------------------------------------------------

        candidate_company_store_ids = sorted(
            {
                int(candidate.company_store_id)
                for candidate in address_candidates
                if candidate.company_store_id
                is not None
            }
        )

        company_stores = (
            self._load_company_stores(
                company_store_ids=(
                    candidate_company_store_ids
                )
            )
        )

        company_stores_by_id = {
            int(company_store.id): company_store
            for company_store in company_stores
        }

        # ------------------------------------------------------------------
        # 4. Build PreparedInput + resolve geography
        # ------------------------------------------------------------------

        prepared_items: list[
            tuple[
                AddressCandidate,
                CompanyStore,
                PreparedInput,
                GeoContext,
            ]
        ] = []

        failed_candidate_ids: list[int] = []

        for candidate in address_candidates:
            company_store = (
                company_stores_by_id.get(
                    int(candidate.company_store_id)
                )
                if candidate.company_store_id
                is not None
                else None
            )

            if company_store is None:
                failed_candidate_ids.append(
                    int(candidate.id)
                )
                continue

            geo = self._resolve_geography(
                province=(
                    candidate.province
                    or company_store.province
                ),
                city=(
                    candidate.city
                    or company_store.city
                ),
            )

            prepared_input = (
                self._build_prepared_input(
                    candidate=candidate,
                    company_store=company_store,
                    geo=geo,
                )
            )

            prepared_items.append(
                (
                    candidate,
                    company_store,
                    prepared_input,
                    geo,
                )
            )

        # ------------------------------------------------------------------
        # 5. Load master Store DTOs by geography
        # ------------------------------------------------------------------

        geo_groups: dict[
            tuple[int | None, int | None],
            list[
                tuple[
                    AddressCandidate,
                    CompanyStore,
                    PreparedInput,
                    GeoContext,
                ]
            ],
        ] = defaultdict(list)

        for item in prepared_items:
            geo = item[3]

            geo_groups[
                (
                    geo.province_id,
                    geo.city_id,
                )
            ].append(item)

        all_decisions: list[
            MatchingDecision
        ] = []

        pool_flags_by_candidate_id: dict[
            int,
            tuple[bool, bool]
        ] = {}

        # ------------------------------------------------------------------
        # Process each geographic group once.
        # ------------------------------------------------------------------

        for (
            province_id,
            city_id,
        ), items in geo_groups.items():

            geo = items[0][3]

            master_records = (
                self._load_master_store_records(
                    province_id=province_id,
                    city_id=city_id,
                    phone_code=geo.phone_code,
                )
            )

            masters_by_id = {
                int(master.id): master
                for master in master_records
            }

            # --------------------------------------------------------------
            # If no geography/master pool can be resolved, create empty
            # CandidatePools. Stage 6 owns the no_candidate_pool decision.
            # --------------------------------------------------------------

            if not master_records:
                pools: list[CandidatePool] = []

                for (
                    candidate,
                    _company_store,
                    prepared_input,
                    _geo,
                ) in items:
                    pool = CandidatePool(
                        input=prepared_input,
                        no_candidate_pool=True,
                        geo_unresolved=(
                            city_id is None
                            and province_id is None
                        ),
                    )

                    pools.append(pool)

                    pool_flags_by_candidate_id[
                        int(candidate.id)
                    ] = (
                        bool(pool.no_candidate_pool),
                        bool(pool.geo_unresolved),
                    )

                decisions = (
                    self.matching_service.match_batch(
                        pools=pools,
                        masters_by_id={},
                        city_phone_code=(
                            geo.phone_code
                        ),
                    )
                )

                all_decisions.extend(decisions)
                continue

            # --------------------------------------------------------------
            # Stage 5: build city/province in-memory index.
            #
            # build_city_master_index uses the DTOs only.
            # --------------------------------------------------------------

            effective_city_id = (
                int(city_id)
                if city_id is not None
                else 0
            )

            master_index = (
                self.preparation_service
                .build_city_master_index(
                    city_id=effective_city_id,
                    masters=master_records,
                    city_phone_code=(
                        geo.phone_code
                    ),
                )
            )

            pools = []

            for (
                candidate,
                _company_store,
                prepared_input,
                _geo,
            ) in items:

                pool = (
                    self.preparation_service
                    .build_candidate_pool(
                        prepared_input=prepared_input,
                        master_index=master_index,
                        city_phone_code=(
                            geo.phone_code
                        ),
                    )
                )

                pools.append(pool)

                pool_flags_by_candidate_id[
                    int(candidate.id)
                ] = (
                    bool(pool.no_candidate_pool),
                    bool(pool.geo_unresolved),
                )

            # --------------------------------------------------------------
            # Stage 6: pure orchestration.
            # --------------------------------------------------------------

            decisions = (
                self.matching_service.match_batch(
                    pools=pools,
                    masters_by_id=masters_by_id,
                    city_phone_code=(
                        geo.phone_code
                    ),
                )
            )

            all_decisions.extend(decisions)

        # ------------------------------------------------------------------
        # 6. Persistence
        # ------------------------------------------------------------------

        candidate_by_id = {
            int(candidate.id): candidate
            for candidate in address_candidates
        }

        decision_company_store_ids = {
            int(decision.company_store_id)
            for decision in all_decisions
            if decision.company_store_id
            is not None
        }

        persistence_company_stores = {
            company_store_id:
                company_stores_by_id.get(
                    company_store_id
                )
            for company_store_id
            in decision_company_store_ids
        }

        if persist:
            try:
                for decision in all_decisions:
                    candidate = candidate_by_id.get(
                        int(
                            decision.address_candidate_id
                        )
                    )

                    company_store = (
                        persistence_company_stores.get(
                            int(
                                decision.company_store_id
                            )
                        )
                    )

                    if (
                        candidate is None
                        or company_store is None
                    ):
                        continue

                    self._persist_decision(
                        candidate=candidate,
                        company_store=company_store,
                        decision=decision,
                    )

                self.db.commit()

            except Exception:
                self.db.rollback()
                logger.exception(
                    "Store matching persistence failed "
                    "for batch_id=%s project_id=%s",
                    batch_id,
                    project_id,
                )
                raise

        # ------------------------------------------------------------------
        # 7. Report
        # ------------------------------------------------------------------

        elapsed_seconds = (
            perf_counter() - started_at
        )

        return self._build_report(
            batch_id=batch_id,
            project_id=project_id,
            decisions=all_decisions,
            failed_candidate_ids=(
                failed_candidate_ids
            ),
            pool_flags_by_candidate_id=(
                pool_flags_by_candidate_id
            ),
            elapsed_seconds=elapsed_seconds,
            persist=persist,
        )

    # ========================================================================
    # Project scope
    # ========================================================================

    def _load_project_company_store_ids(
        self,
        *,
        project_id: int,
    ) -> set[int]:
        """
        Load active CompanyStore IDs associated with the project.
        """

        stmt = (
            select(
                ProjectCompanyStore.company_store_id
            )
            .where(
                ProjectCompanyStore.project_id
                == project_id,
                ProjectCompanyStore.is_active
                .is_(True),
            )
        )

        rows = self.db.execute(
            stmt
        ).scalars().all()

        return {
            int(value)
            for value in rows
            if value is not None
        }

    # ========================================================================
    # AddressCandidate bulk load
    # ========================================================================

    def _load_address_candidates(
        self,
        *,
        source_prefix: str,
        company_store_ids: set[int],
    ) -> list[AddressCandidate]:
        """
        Load AddressCandidates for the batch/project scope in one query.
        """

        if not company_store_ids:
            return []

        stmt = (
            select(AddressCandidate)
            .where(
                AddressCandidate.source_type
                == "excel",
                AddressCandidate.source_id.like(
                    f"{source_prefix}%"
                ),
                AddressCandidate.company_store_id.in_(
                    company_store_ids
                ),
            )
            .order_by(AddressCandidate.id)
        )

        return list(
            self.db.execute(
                stmt
            ).scalars().all()
        )

    # ========================================================================
    # CompanyStore bulk load
    # ========================================================================

    def _load_company_stores(
        self,
        *,
        company_store_ids: list[int],
    ) -> list[CompanyStore]:
        """
        Bulk load CompanyStore rows.
        """

        if not company_store_ids:
            return []

        results: list[
            CompanyStore
        ] = []

        # Chunking prevents oversized IN clauses for large projects.
        for ids_chunk in _chunked(
            company_store_ids,
            2000,
        ):
            stmt = (
                select(CompanyStore)
                .where(
                    CompanyStore.id.in_(
                        ids_chunk
                    )
                )
            )

            results.extend(
                self.db.execute(
                    stmt
                ).scalars().all()
            )

        return results

    # ========================================================================
    # Geography
    # ========================================================================

    def _resolve_geography(
        self,
        *,
        province: str | None,
        city: str | None,
    ) -> GeoContext:
        """
        Resolve lightweight province/city geography from local DB tables.

        No external Geo service is used.

        The lookup result is cached for the duration of this service instance.
        """

        province_text = (
            str(province).strip()
            if province
            else ""
        )

        city_text = (
            str(city).strip()
            if city
            else ""
        )

        cache_key = (
            province_text,
            city_text,
        )

        cached = self._geo_cache.get(
            cache_key
        )

        if cached is not None:
            return cached

        province_id: int | None = None
        city_id: int | None = None
        phone_code: str | None = None

        # ------------------------------------------------------------------
        # Province
        # ------------------------------------------------------------------

        province_row = None

        if province_text:
            province_stmt = (
                select(Province)
                .where(
                    Province.name
                    == province_text
                )
                .limit(1)
            )

            province_row = (
                self.db.execute(
                    province_stmt
                )
                .scalars()
                .first()
            )

            if province_row is not None:
                province_id = int(
                    province_row.id
                )

        # ------------------------------------------------------------------
        # City
        # ------------------------------------------------------------------

        if city_text:
            city_stmt = (
                select(City)
                .where(
                    City.name
                    == city_text
                )
            )

            if province_id is not None:
                city_stmt = city_stmt.where(
                    City.province_id
                    == province_id
                )

            city_row = (
                self.db.execute(
                    city_stmt.limit(1)
                )
                .scalars()
                .first()
            )

            if city_row is not None:
                city_id = int(
                    city_row.id
                )

                raw_phone_code = getattr(
                    city_row,
                    "phone_code",
                    None,
                )

                if raw_phone_code:
                    phone_code = str(
                        raw_phone_code
                    ).strip() or None

                if province_id is None:
                    raw_province_id = getattr(
                        city_row,
                        "province_id",
                        None,
                    )

                    if raw_province_id is not None:
                        province_id = int(
                            raw_province_id
                        )

        result = GeoContext(
            province_id=province_id,
            city_id=city_id,
            phone_code=phone_code,
        )

        self._geo_cache[
            cache_key
        ] = result

        return result

    # ========================================================================
    # PreparedInput adapter
    # ========================================================================

    @staticmethod
    def _build_prepared_input(
        *,
        candidate: AddressCandidate,
        company_store: CompanyStore,
        geo: GeoContext,
    ) -> PreparedInput:
        """
        Convert ORM rows into the frozen pure PreparedInput DTO.

        Raw database values remain unchanged.
        """

        latitude = _safe_float(
            candidate.latitude
        )

        longitude = _safe_float(
            candidate.longitude
        )

        if latitude is None:
            latitude = _safe_float(
                company_store.latitude
            )

        if longitude is None:
            longitude = _safe_float(
                company_store.longitude
            )

        return PreparedInput(
            address_candidate_id=int(
                candidate.id
            ),
            company_store_id=int(
                company_store.id
            ),
            province_id=(
                geo.province_id
            ),
            city_id=(
                geo.city_id
            ),
            name=(
                company_store.name
            ),
            phone=(
                company_store.phone
            ),
            address=(
                candidate.address_text
                or company_store.address
            ),
            latitude=latitude,
            longitude=longitude,
        )

    # ========================================================================
    # Master Store bulk load
    # ========================================================================

    def _load_master_store_records(
        self,
        *,
        province_id: int | None,
        city_id: int | None,
        phone_code: str | None,
    ) -> list[MasterStoreRecord]:
        """
        Bulk-load active master Stores for one geography.

        Preferred scope:
            city_id

        Fallback:
            province_id

        If neither is resolved:
            return []

        Master Store rows are never mutated.
        """

        if city_id is None and province_id is None:
            return []

        stmt = (
            select(Store)
            .where(
                Store.is_active.is_(True)
            )
        )

        if city_id is not None:
            stmt = stmt.where(
                Store.city_id == city_id
            )

        elif province_id is not None:
            stmt = stmt.where(
                Store.province_id
                == province_id
            )

        stmt = stmt.order_by(
            Store.id
        )

        stores = list(
            self.db.execute(
                stmt
            ).scalars().all()
        )

        result: list[
            MasterStoreRecord
        ] = []

        for store in stores:
            result.append(
                MasterStoreRecord(
                    id=int(store.id),
                    canonical_name=(
                        store.canonical_name
                    ),
                    canonical_phone=(
                        store.canonical_phone
                    ),
                    address=(
                        store.address
                    ),
                    province_id=(
                        int(store.province_id)
                        if store.province_id
                        is not None
                        else None
                    ),
                    city_id=(
                        int(store.city_id)
                        if store.city_id
                        is not None
                        else None
                    ),
                    latitude=_safe_float(
                        store.latitude
                    ),
                    longitude=_safe_float(
                        store.longitude
                    ),
                )
            )

        return result

    # ========================================================================
    # Persistence
    # ========================================================================

    def _persist_decision(
        self,
        *,
        candidate: AddressCandidate,
        company_store: CompanyStore,
        decision: MatchingDecision,
    ) -> None:
        """
        Persist one frozen MatchingDecision.

        PRECISE
        -------
        CompanyStore.master_store_id = matched master
        CompanyStore.match_status = PRECISE

        AddressCandidate:
            store_id = matched master
            matched_store_id = matched master
            match_found = True

        SUGGESTED
        ---------
        No master association is persisted.

        UNRESOLVED
        ----------
        No master association is persisted.

        All decisions mark AddressCandidate as processed.

        Store master rows are never modified.
        """

        status = _match_status_from_decision(
            decision
        )

        matched_store_id = (
            int(decision.matched_store_id)
            if decision.matched_store_id
            is not None
            else None
        )

        score = _safe_decimal(
            decision.score
        )

        method = (
            str(decision.method).strip()
            if decision.method
            else None
        )

        # ------------------------------------------------------------------
        # PRECISE / confirmed association
        # ------------------------------------------------------------------

        if (
            status
            in {
                MatchStatus.PRECISE,
                MatchStatus.MATCHED,
            }
            and matched_store_id
            is not None
        ):
            company_store.master_store_id = (
                matched_store_id
            )

            company_store.match_status = (
                status
            )

            candidate.store_id = (
                matched_store_id
            )

            candidate.matched_store_id = (
                matched_store_id
            )

            candidate.match_found = True

        # ------------------------------------------------------------------
        # SUGGESTED
        #
        # Important:
        # no master association before human/resolution confirmation.
        # ------------------------------------------------------------------

        elif status == MatchStatus.SUGGESTED:
            company_store.match_status = (
                MatchStatus.SUGGESTED
            )

            candidate.store_id = None
            candidate.matched_store_id = None
            candidate.match_found = False

        # ------------------------------------------------------------------
        # UNRESOLVED / other non-confirmed status
        # ------------------------------------------------------------------

        else:
            company_store.match_status = (
                MatchStatus.UNRESOLVED
            )

            candidate.store_id = None
            candidate.matched_store_id = None
            candidate.match_found = False

        # ------------------------------------------------------------------
        # Matching evidence
        # ------------------------------------------------------------------

        candidate.match_score = score
        candidate.match_method = method

        candidate.is_processed = True
        candidate.processed_at = _utcnow()

    # ========================================================================
    # Report
    # ========================================================================

    @staticmethod
    def _build_report(
        *,
        batch_id: int,
        project_id: int,
        decisions: list[MatchingDecision],
        failed_candidate_ids: list[int],
        pool_flags_by_candidate_id: dict[
            int,
            tuple[bool, bool],
        ],
        elapsed_seconds: float,
        persist: bool,
    ) -> dict[str, Any]:
        """
        Build compatibility report for project.py / Readiness.

        Existing keys from the previous matching service are preserved where
        practical, while aliases are also supplied for the newer UI contract.
        """

        status_counter: Counter[str] = (
            Counter()
        )

        method_counter: Counter[str] = (
            Counter()
        )

        precise = 0
        suggested = 0
        unresolved = 0
        existing_link = 0

        matched_count = 0

        no_candidate_pool = 0
        geo_unresolved = 0

        decision_rows: list[
            dict[str, Any]
        ] = []

        for decision in decisions:
            status = _normalize_status_text(
                decision.status
            )

            if not status:
                status = "UNRESOLVED"

            status_counter[
                status
            ] += 1

            if status == "PRECISE":
                precise += 1

            elif status == "SUGGESTED":
                suggested += 1

            elif status == "MATCHED":
                existing_link += 1

            elif status == "UNRESOLVED":
                unresolved += 1

            if (
                decision.matched_store_id
                is not None
            ):
                matched_count += 1

            method = (
                str(decision.method).strip()
                if decision.method
                else "unknown"
            )

            method_counter[
                method
            ] += 1

            flags = (
                pool_flags_by_candidate_id.get(
                    int(
                        decision.address_candidate_id
                    ),
                    (False, False),
                )
            )

            if flags[0]:
                no_candidate_pool += 1

            if flags[1]:
                geo_unresolved += 1

            decision_rows.append(
                {
                    "address_candidate_id": (
                        decision.address_candidate_id
                    ),
                    "company_store_id": (
                        decision.company_store_id
                    ),
                    "matched_store_id": (
                        decision.matched_store_id
                    ),
                    "status": status,
                    "score": _safe_float(
                        decision.score
                    ),
                    "method": method,
                    "metadata": dict(
                        decision.metadata
                        or {}
                    ),
                }
            )

        processed = len(
            decisions
        )

        failed = len(
            failed_candidate_ids
        )

        total = (
            processed
            + failed
        )

        return {
            # --------------------------------------------------------------
            # Core compatibility keys
            # --------------------------------------------------------------
            "batch_id": batch_id,
            "project_id": project_id,
            "total": total,
            "processed": processed,
            "precise": precise,
            "suggested": suggested,
            "unresolved": unresolved,
            "existing_link": existing_link,
            "failed": failed,
            "geo_unresolved": (
                geo_unresolved
            ),
            "no_candidate_pool": (
                no_candidate_pool
            ),
            "elapsed_seconds": max(
                0.0,
                float(elapsed_seconds),
            ),

            # --------------------------------------------------------------
            # Newer aliases / reporting keys
            # --------------------------------------------------------------
            "total_processed": processed,
            "matched_count": (
                matched_count
            ),
            "suggested_count": (
                suggested
            ),
            "unresolved_count": (
                unresolved
            ),

            # --------------------------------------------------------------
            # Distribution
            # --------------------------------------------------------------
            "status_distribution": dict(
                sorted(
                    status_counter.items()
                )
            ),
            "match_method_distribution": (
                dict(
                    sorted(
                        method_counter.items()
                    )
                )
            ),
            "method_distribution": dict(
                sorted(
                    method_counter.items()
                )
            ),

            # --------------------------------------------------------------
            # Diagnostics
            # --------------------------------------------------------------
            "failed_candidate_ids": (
                failed_candidate_ids
            ),
            "decisions": decision_rows,

            # --------------------------------------------------------------
            # Execution
            # --------------------------------------------------------------
            "persisted": bool(
                persist
            ),
        }

    @staticmethod
    def _empty_report(
        *,
        batch_id: int,
        project_id: int,
        elapsed_seconds: float,
    ) -> dict[str, Any]:
        """
        Stable zero-result report.
        """

        return {
            "batch_id": batch_id,
            "project_id": project_id,
            "total": 0,
            "processed": 0,
            "precise": 0,
            "suggested": 0,
            "unresolved": 0,
            "existing_link": 0,
            "failed": 0,
            "geo_unresolved": 0,
            "no_candidate_pool": 0,
            "elapsed_seconds": max(
                0.0,
                float(elapsed_seconds),
            ),
            "total_processed": 0,
            "matched_count": 0,
            "suggested_count": 0,
            "unresolved_count": 0,
            "status_distribution": {},
            "match_method_distribution": {},
            "method_distribution": {},
            "failed_candidate_ids": [],
            "decisions": [],
            "persisted": False,
        }


__all__ = [
    "GeoContext",
    "MatchDecision",
    "StoreMatchingService",
]
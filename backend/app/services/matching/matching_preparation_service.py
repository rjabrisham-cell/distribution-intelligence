from __future__ import annotations

import time
from collections import defaultdict
from typing import Iterable

from app.services.matching.matching_constants import (
    GRID_NEIGHBOR_RADIUS,
    GRID_STEP_DEGREES,
    MAX_TOKEN_POOL,
)
from app.services.matching.matching_models import (
    CandidatePool,
    CityMasterIndex,
    MasterStoreRecord,
    MatchingPreparationStats,
    PreparedInput,
)
from app.services.matching.matching_utils import (
    haversine_distance_meters,
    neighboring_grid_keys,
    normalize_phone,
    normalize_text,
    spatial_grid_key,
    tokenize,
    unique_ints,
)


class MatchingPreparationService:
    """
    Pure pre-matching preparation and candidate-retrieval service.

    Responsibilities
    ----------------
    1. Build an in-memory index for master stores of one city.
    2. Normalize retrieval keys consistently.
    3. Retrieve exact candidates by:
       - name
       - phone
       - address
    4. Retrieve nearby candidates through the spatial grid.
    5. Reduce spatial retrieval to the nearest spatial candidate.
    6. Preserve all exact candidates independently of the spatial shortlist.
    7. Use name-token retrieval only as a fallback when no other candidate
       exists.
    8. Produce CandidatePool objects for Stage 6 scoring.

    This service intentionally does NOT:
    - access the database
    - use SQLAlchemy ORM
    - persist anything
    - make matching decisions
    - modify matching thresholds
    - create or update master Store records

    MVP retrieval policy
    --------------------

        exact candidates
              UNION
        nearest spatial candidate

    The spatial grid is a coarse retrieval mechanism only.  Candidate
    reduction is performed using Haversine distance before Stage 6 scoring.

    This policy is isolated here so it can later be changed to Top-N or a
    distance-bound strategy without changing the scoring layer.
    """

    # ==================================================================
    # Master index
    # ==================================================================

    def build_city_master_index(
        self,
        *,
        city_id: int,
        masters: Iterable[MasterStoreRecord],
        city_phone_code: str | None = None,
    ) -> CityMasterIndex:
        """
        Build the in-memory master-store retrieval index for one city.
        """

        stores_by_id: dict[int, MasterStoreRecord] = {}

        by_name: dict[str, list[int]] = defaultdict(list)
        by_phone: dict[str, list[int]] = defaultdict(list)
        by_address: dict[str, list[int]] = defaultdict(list)
        by_name_token: dict[str, list[int]] = defaultdict(list)
        by_geo_cell: dict[tuple[int, int], list[int]] = defaultdict(list)

        for master in masters:
            master_id = int(master.id)

            # ----------------------------------------------------------
            # Normalize master retrieval fields
            # ----------------------------------------------------------

            normalized_name = normalize_text(
                master.canonical_name
            )

            normalized_phone = normalize_phone(
                master.canonical_phone,
                area_code=city_phone_code,
            )

            normalized_address = normalize_text(
                master.address
            )

            # ----------------------------------------------------------
            # Store normalized DTO
            # ----------------------------------------------------------

            indexed_master = MasterStoreRecord(
                id=master_id,
                canonical_name=master.canonical_name,
                canonical_phone=master.canonical_phone,
                address=master.address,
                province_id=master.province_id,
                city_id=master.city_id,
                latitude=master.latitude,
                longitude=master.longitude,
                normalized_name=normalized_name,
                normalized_phone=normalized_phone,
                normalized_address=normalized_address,
            )

            stores_by_id[master_id] = indexed_master

            # ----------------------------------------------------------
            # Exact-name index
            # ----------------------------------------------------------

            if normalized_name:
                by_name[normalized_name].append(
                    master_id
                )

            # ----------------------------------------------------------
            # Exact-phone index
            # ----------------------------------------------------------

            if normalized_phone:
                by_phone[normalized_phone].append(
                    master_id
                )

            # ----------------------------------------------------------
            # Exact-address index
            # ----------------------------------------------------------

            if normalized_address:
                by_address[normalized_address].append(
                    master_id
                )

            # ----------------------------------------------------------
            # Name-token index
            # ----------------------------------------------------------

            if normalized_name:
                seen_tokens: set[str] = set()

                for token in tokenize(
                    normalized_name
                ):
                    if not token:
                        continue

                    if token in seen_tokens:
                        continue

                    seen_tokens.add(token)

                    by_name_token[token].append(
                        master_id
                    )

            # ----------------------------------------------------------
            # Spatial-grid index
            # ----------------------------------------------------------

            if (
                master.latitude is not None
                and master.longitude is not None
            ):
                try:
                    cell = spatial_grid_key(
                        float(master.latitude),
                        float(master.longitude),
                        GRID_STEP_DEGREES,
                    )

                    by_geo_cell[cell].append(
                        master_id
                    )

                except (TypeError, ValueError):
                    # Bad coordinates must not break preparation.
                    pass

        return CityMasterIndex(
            city_id=city_id,
            stores_by_id=stores_by_id,
            by_name=dict(by_name),
            by_phone=dict(by_phone),
            by_address=dict(by_address),
            by_name_token=dict(by_name_token),
            by_geo_cell=dict(by_geo_cell),
        )

    # ==================================================================
    # Candidate retrieval
    # ==================================================================

    def build_candidate_pool(
        self,
        *,
        prepared_input: PreparedInput,
        master_index: CityMasterIndex,
        city_phone_code: str | None = None,
    ) -> CandidatePool:
        """
        Build the candidate shortlist for one PreparedInput.

        Retrieval sequence
        ------------------
        1. Exact name
        2. Exact phone
        3. Exact address
        4. Spatial-grid coarse retrieval
        5. Haversine nearest-1 spatial reduction
        6. Union exact + nearest spatial
        7. Name-token fallback only when the pool remains empty

        Exact candidates are never removed by spatial reduction.
        """

        # --------------------------------------------------------------
        # Normalize input
        # --------------------------------------------------------------

        normalized_name = (
            prepared_input.normalized_name
            or normalize_text(
                prepared_input.name
            )
        )

        normalized_phone = (
            prepared_input.normalized_phone
            or normalize_phone(
                prepared_input.phone,
                area_code=city_phone_code,
            )
        )

        normalized_address = (
            prepared_input.normalized_address
            or normalize_text(
                prepared_input.address
            )
        )

        candidate_ids: list[int] = []

        retrieval_methods: dict[int, set[str]] = defaultdict(set)

        # ==============================================================
        # 1. Exact name
        # ==============================================================

        if normalized_name:
            for master_id in master_index.by_name.get(
                normalized_name,
                [],
            ):
                candidate_ids.append(
                    master_id
                )

                retrieval_methods[
                    master_id
                ].add(
                    "exact_name"
                )

        # ==============================================================
        # 2. Exact phone
        # ==============================================================

        if normalized_phone:
            for master_id in master_index.by_phone.get(
                normalized_phone,
                [],
            ):
                candidate_ids.append(
                    master_id
                )

                retrieval_methods[
                    master_id
                ].add(
                    "exact_phone"
                )

        # ==============================================================
        # 3. Exact address
        # ==============================================================

        if normalized_address:
            for master_id in master_index.by_address.get(
                normalized_address,
                [],
            ):
                candidate_ids.append(
                    master_id
                )

                retrieval_methods[
                    master_id
                ].add(
                    "exact_address"
                )

        # ==============================================================
        # 4. Spatial coarse retrieval
        # ==============================================================

        has_coordinates = (
            prepared_input.latitude is not None
            and prepared_input.longitude is not None
        )

        spatial_candidates: list[
            tuple[float, int]
        ] = []

        if has_coordinates:
            try:
                input_latitude = float(
                    prepared_input.latitude
                )

                input_longitude = float(
                    prepared_input.longitude
                )

                # Runtime contract:
                #
                # neighboring_grid_keys(
                #     latitude,
                #     longitude,
                #     grid_step,
                #     *,
                #     radius=...
                # )

                spatial_cells = neighboring_grid_keys(
                    input_latitude,
                    input_longitude,
                    GRID_STEP_DEGREES,
                    radius=GRID_NEIGHBOR_RADIUS,
                )

                spatial_ids: list[int] = []

                for cell in spatial_cells:
                    spatial_ids.extend(
                        master_index.by_geo_cell.get(
                            cell,
                            [],
                        )
                    )

                # One master can theoretically be reached more than once
                # through retrieval composition.  Do Haversine only once.
                spatial_ids = unique_ints(
                    spatial_ids
                )

                for master_id in spatial_ids:
                    master = master_index.get_store(
                        master_id
                    )

                    if master is None:
                        continue

                    if (
                        master.latitude is None
                        or master.longitude is None
                    ):
                        continue

                    try:
                        distance = (
                            haversine_distance_meters(
                                input_latitude,
                                input_longitude,
                                float(master.latitude),
                                float(master.longitude),
                            )
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

                    spatial_candidates.append(
                        (
                            distance,
                            master_id,
                        )
                    )

            except (
                TypeError,
                ValueError,
            ):
                # Invalid input coordinates are treated as unavailable
                # spatial evidence.
                spatial_candidates = []

        # ==============================================================
        # 5. Spatial nearest-1
        # ==============================================================

        if spatial_candidates:
            spatial_candidates.sort(
                key=lambda item: (
                    item[0],
                    item[1],
                )
            )

            nearest_master_id = (
                spatial_candidates[0][1]
            )

            candidate_ids.append(
                nearest_master_id
            )

            retrieval_methods[
                nearest_master_id
            ].add(
                "spatial_grid"
            )

        # ==============================================================
        # 6. Exact + spatial union
        # ==============================================================

        candidate_ids = unique_ints(
            candidate_ids
        )

        # ==============================================================
        # 7. Name-token fallback
        #
        # Token retrieval must not expand an existing exact/spatial pool.
        # ==============================================================

        if (
            not candidate_ids
            and normalized_name
        ):
            token_candidate_ids: list[int] = []

            for token in tokenize(
                normalized_name
            ):
                if not token:
                    continue

                token_ids = (
                    master_index.by_name_token.get(
                        token,
                        [],
                    )
                )

                if not token_ids:
                    continue

                # Extremely common tokens are intentionally ignored.
                # Otherwise a generic word can recreate the same candidate
                # explosion that spatial nearest-1 is designed to remove.
                if (
                    len(token_ids)
                    > MAX_TOKEN_POOL
                ):
                    continue

                token_candidate_ids.extend(
                    token_ids
                )

            token_candidate_ids = (
                unique_ints(
                    token_candidate_ids
                )
            )

            if (
                len(token_candidate_ids)
                > MAX_TOKEN_POOL
            ):
                token_candidate_ids = (
                    token_candidate_ids[
                        :MAX_TOKEN_POOL
                    ]
                )

            for master_id in token_candidate_ids:
                candidate_ids.append(
                    master_id
                )

                retrieval_methods[
                    master_id
                ].add(
                    "name_token"
                )

            candidate_ids = unique_ints(
                candidate_ids
            )

        # ==============================================================
        # Result flags
        # ==============================================================

        no_candidate_pool = (
            len(candidate_ids) == 0
        )

        geo_unresolved = (
            not has_coordinates
        )

        return CandidatePool(
            input=prepared_input,
            master_store_ids=candidate_ids,
            retrieval_methods={
                master_id: set(methods)
                for master_id, methods
                in retrieval_methods.items()
                if master_id in candidate_ids
            },
            no_candidate_pool=no_candidate_pool,
            geo_unresolved=geo_unresolved,
        )

    # ==================================================================
    # Candidate DTO resolution
    # ==================================================================

    @staticmethod
    def resolve_pool_masters(
        *,
        pool: CandidatePool,
        master_index: CityMasterIndex,
    ) -> list[MasterStoreRecord]:
        """
        Resolve CandidatePool master IDs into MasterStoreRecord DTOs.

        Missing IDs are ignored defensively.
        """

        result: list[
            MasterStoreRecord
        ] = []

        for master_id in pool.master_store_ids:
            master = master_index.get_store(
                master_id
            )

            if master is not None:
                result.append(
                    master
                )

        return result

    # ==================================================================
    # Batch preparation
    # ==================================================================

    def prepare_batch(
        self,
        *,
        prepared_inputs: Iterable[PreparedInput],
        master_index: CityMasterIndex,
        city_phone_code: str | None = None,
    ) -> tuple[
        list[CandidatePool],
        MatchingPreparationStats,
    ]:
        """
        Prepare candidate pools for an input batch.

        Retrieval only:
        - no scoring
        - no matching decision
        - no persistence
        """

        started_at = time.perf_counter()

        pools: list[
            CandidatePool
        ] = []

        stats = MatchingPreparationStats()

        for prepared_input in prepared_inputs:
            stats.total += 1

            has_coordinates = (
                prepared_input.latitude is not None
                and prepared_input.longitude is not None
            )

            if has_coordinates:
                stats.with_coordinates += 1
            else:
                stats.without_coordinates += 1

            pool = self.build_candidate_pool(
                prepared_input=prepared_input,
                master_index=master_index,
                city_phone_code=city_phone_code,
            )

            pools.append(
                pool
            )

            stats.prepared += 1

            if pool.master_store_ids:
                stats.with_candidate_pool += 1
            else:
                stats.without_candidate_pool += 1

            if pool.geo_unresolved:
                stats.geo_unresolved += 1

            # ----------------------------------------------------------
            # Retrieval statistics
            #
            # Count inputs using each retrieval method rather than raw
            # candidate-pair memberships.
            # ----------------------------------------------------------

            methods_used: set[str] = set()

            for methods in (
                pool.retrieval_methods.values()
            ):
                methods_used.update(
                    methods
                )

            if "exact_name" in methods_used:
                stats.exact_name_hits += 1

            if "exact_phone" in methods_used:
                stats.exact_phone_hits += 1

            if "exact_address" in methods_used:
                stats.exact_address_hits += 1

            if "spatial_grid" in methods_used:
                stats.spatial_hits += 1

            if "name_token" in methods_used:
                stats.token_hits += 1

        stats.elapsed_seconds = (
            time.perf_counter()
            - started_at
        )

        return (
            pools,
            stats,
        )

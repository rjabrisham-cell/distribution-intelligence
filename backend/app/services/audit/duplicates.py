from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.core.enums import DuplicateStatus


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_value(obj: Any, *names: str) -> Any:
    if isinstance(obj, Mapping):
        for name in names:
            if name in obj:
                return obj.get(name)
        return None

    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _store_key(store: Any) -> Any:
    key = _first_value(store, "id", "store_id", "pk")
    return key if key is not None else id(store)


def _extract_signature(store: Any) -> dict[str, str | None]:
    return {
        "canonical_name": _normalize_text(_first_value(store, "canonical_name")),
        "canonical_phone": _normalize_text(_first_value(store, "canonical_phone")),
        "postal_code": _normalize_text(_first_value(store, "postal_code")),
        "address": _normalize_text(_first_value(store, "address")),
        "mobile": _normalize_text(_first_value(store, "mobile")),
        "manager_name": _normalize_text(_first_value(store, "manager_name")),
        "plaque": _normalize_text(_first_value(store, "plaque")),
        "unit": _normalize_text(_first_value(store, "unit")),
        "floor": _normalize_text(_first_value(store, "floor")),
        "latitude": _normalize_text(_first_value(store, "latitude")),
        "longitude": _normalize_text(_first_value(store, "longitude")),
        "province_id": _normalize_text(_first_value(store, "province_id")),
        "city_id": _normalize_text(_first_value(store, "city_id")),
        "county_id": _normalize_text(_first_value(store, "county_id")),
        "district_id": _normalize_text(_first_value(store, "district_id")),
        "neighborhood_id": _normalize_text(_first_value(store, "neighborhood_id")),
        "village_id": _normalize_text(_first_value(store, "village_id")),
    }


def _normalize_coord_key(value: str | None) -> str | None:
    if value is None:
        return None
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value


@dataclass(frozen=True, slots=True)
class DuplicateEvidence:
    candidate_store_id: Any
    matched_fields: tuple[str, ...]
    match_type: str


@dataclass(frozen=True, slots=True)
class DuplicateResult:
    store_id: Any
    status: DuplicateStatus
    candidate_store_ids: tuple[Any, ...]
    matched_fields: tuple[str, ...]
    evidence: tuple[DuplicateEvidence, ...]
    warnings: tuple[str, ...] = ()


@dataclass
class DuplicateBatchAccumulator:
    store_count: int = 0
    unique_count: int = 0
    possible_duplicate_count: int = 0
    duplicate_count: int = 0
    unknown_count: int = 0
    candidate_count: int = 0

    def update(self, result: DuplicateResult) -> None:
        self.store_count += 1
        self.candidate_count += len(result.candidate_store_ids)

        if result.status == DuplicateStatus.UNIQUE:
            self.unique_count += 1
        elif result.status == DuplicateStatus.POSSIBLE_DUPLICATE:
            self.possible_duplicate_count += 1
        elif result.status == DuplicateStatus.DUPLICATE:
            self.duplicate_count += 1
        else:
            self.unknown_count += 1

    def finalize(self) -> "DuplicateBatchAccumulator":
        return self

    def as_dict(self) -> dict[str, int]:
        return {
            "store_count": self.store_count,
            "unique_count": self.unique_count,
            "possible_duplicate_count": self.possible_duplicate_count,
            "duplicate_count": self.duplicate_count,
            "unknown_count": self.unknown_count,
            "candidate_count": self.candidate_count,
        }


@dataclass(slots=True)
class _DuplicateIndex:
    by_name_phone: dict[tuple[str, str], set[Any]] = field(default_factory=dict)
    by_name: dict[str, set[Any]] = field(default_factory=dict)
    by_phone: dict[str, set[Any]] = field(default_factory=dict)
    by_name_postal: dict[tuple[str, str], set[Any]] = field(default_factory=dict)
    by_name_address: dict[tuple[str, str], set[Any]] = field(default_factory=dict)


class DuplicateService:
    def __init__(self) -> None:
        self._index: _DuplicateIndex | None = None
        self._index_built: bool = False

    def create_accumulator(self) -> DuplicateBatchAccumulator:
        return DuplicateBatchAccumulator()

    def build_index(self, stores: Iterable[Any]) -> _DuplicateIndex:
        index = _DuplicateIndex()

        for store in stores:
            store_id = _store_key(store)
            sig = _extract_signature(store)

            name = sig["canonical_name"]
            phone = sig["canonical_phone"]
            postal_code = sig["postal_code"]
            address = sig["address"]

            if name and phone:
                index.by_name_phone.setdefault((name, phone), set()).add(store_id)
            if name:
                index.by_name.setdefault(name, set()).add(store_id)
            if phone:
                index.by_phone.setdefault(phone, set()).add(store_id)
            if name and postal_code:
                index.by_name_postal.setdefault((name, postal_code), set()).add(store_id)
            if name and address:
                index.by_name_address.setdefault((name, address), set()).add(store_id)

        self._index = index
        self._index_built = True
        return index

    def evaluate(self, store: Any) -> DuplicateResult:
        if not self._index_built or self._index is None:
            return DuplicateResult(
                store_id=_store_key(store),
                status=DuplicateStatus.UNKNOWN,
                candidate_store_ids=(),
                matched_fields=(),
                evidence=(),
                warnings=("duplicate index has not been built",),
            )

        store_id = _store_key(store)
        sig = _extract_signature(store)

        exact_candidates: dict[Any, set[str]] = {}
        possible_candidates: dict[Any, set[str]] = {}

        def add_candidates(
            candidate_ids: set[Any],
            matched_fields: tuple[str, ...],
            bucket: dict[Any, set[str]],
        ) -> None:
            for candidate_id in candidate_ids:
                if candidate_id == store_id:
                    continue
                bucket.setdefault(candidate_id, set()).update(matched_fields)

        name = sig["canonical_name"]
        phone = sig["canonical_phone"]
        postal_code = sig["postal_code"]
        address = sig["address"]

        if name and phone:
            add_candidates(
                self._index.by_name_phone.get((name, phone), set()),
                ("canonical_name", "canonical_phone"),
                exact_candidates,
            )

        if name:
            add_candidates(
                self._index.by_name.get(name, set()),
                ("canonical_name",),
                possible_candidates,
            )

        if phone:
            add_candidates(
                self._index.by_phone.get(phone, set()),
                ("canonical_phone",),
                possible_candidates,
            )

        if name and postal_code:
            add_candidates(
                self._index.by_name_postal.get((name, postal_code), set()),
                ("canonical_name", "postal_code"),
                possible_candidates,
            )

        if name and address:
            add_candidates(
                self._index.by_name_address.get((name, address), set()),
                ("canonical_name", "address"),
                possible_candidates,
            )

        evidence_map: dict[tuple[Any, str], DuplicateEvidence] = {}

        def register_evidence(candidates: dict[Any, set[str]], match_type: str) -> None:
            for candidate_id, fields in candidates.items():
                evidence_map[(candidate_id, match_type)] = DuplicateEvidence(
                    candidate_store_id=candidate_id,
                    matched_fields=tuple(sorted(fields)),
                    match_type=match_type,
                )

        register_evidence(exact_candidates, "exact_name_phone")
        register_evidence(possible_candidates, "possible_partial")

        evidence = tuple(
            sorted(
                evidence_map.values(),
                key=lambda item: (
                    0 if item.match_type == "exact_name_phone" else 1,
                    repr(item.candidate_store_id),
                ),
            )
        )

        candidate_store_ids = tuple(
            sorted({item.candidate_store_id for item in evidence}, key=repr)
        )

        matched_fields = tuple(
            sorted({field_name for item in evidence for field_name in item.matched_fields})
        )

        if exact_candidates:
            status = DuplicateStatus.DUPLICATE
        elif possible_candidates:
            status = DuplicateStatus.POSSIBLE_DUPLICATE
        else:
            status = DuplicateStatus.UNIQUE

        return DuplicateResult(
            store_id=store_id,
            status=status,
            candidate_store_ids=candidate_store_ids,
            matched_fields=matched_fields,
            evidence=evidence,
            warnings=(),
        )

    def evaluate_batch(self, stores: Iterable[Any]) -> tuple[DuplicateResult, ...]:
        stores = tuple(stores)
        self.build_index(stores)
        return tuple(self.evaluate(store) for store in stores)


__all__ = [
    "DuplicateBatchAccumulator",
    "DuplicateEvidence",
    "DuplicateResult",
    "DuplicateService",
]

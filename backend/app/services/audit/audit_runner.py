from __future__ import annotations

import math
import time
from dataclasses import dataclass, replace
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.address_candidate import AddressCandidate
from app.models.company_store import CompanyStore
from app.models.project_company_store import ProjectCompanyStore
from app.models.store import Store
from app.services.audit.completeness import CompletenessService
from app.services.audit.coordinate_validator import CoordinateValidator
from app.services.audit.duplicates import DuplicateService
from app.services.audit.validity import ValidityService


@dataclass(frozen=True, slots=True)
class ProjectStoreAuditView:
    """Store-shaped view: confirmed Master values, then uploaded fallbacks."""

    id: int
    company_store_id: int
    master_store_id: int | None
    canonical_name: str | None
    manager_name: str | None
    canonical_phone: str | None
    mobile: str | None
    province_id: int | None
    city_id: int | None
    address: str | None
    postal_code: str | None
    plaque: str | None
    unit: str | None
    floor: str | None
    latitude: float | None
    longitude: float | None
    source_id: str | None


class AuditRunner:
    """Run the frozen audit services for one Project and STORE Batch."""

    def __init__(
        self,
        project_id: int,
        batch_id: int,
        db: Session | None = None,
    ) -> None:
        self.project_id = int(project_id)
        self.batch_id = int(batch_id)
        self.db = db or SessionLocal()
        self._owns_session = db is None

    def run(self) -> dict[str, Any]:
        started = time.time()
        audit_run_id = uuid4().hex

        try:
            stores = self._load_project_store_views()
            completeness_svc = CompletenessService()
            validity_svc = ValidityService()
            duplicate_svc = DuplicateService()
            coordinate_svc = CoordinateValidator()
            completeness_acc = completeness_svc.create_accumulator()
            validity_acc = validity_svc.create_accumulator()
            duplicate_acc = duplicate_svc.create_accumulator()

            # Duplicate evaluation needs an index built from this project only.
            duplicate_svc.build_index(stores)

            readiness_rows: list[dict[str, Any]] = []

            for store in stores:
                completeness_result = completeness_svc.evaluate(store)
                validity_result = validity_svc.evaluate(store)
                duplicate_result = duplicate_svc.evaluate(store)
                coordinate_result = coordinate_svc.validate(store)
                completeness_acc.update(completeness_result)
                validity_acc.update(validity_result)
                duplicate_acc.update(duplicate_result)

                has_coordinates = (
                    store.latitude is not None
                    and store.longitude is not None
                )
                coordinate_status = self._verdict_name(
                    coordinate_result.overall_status
                )
                has_blocking_validity_error = any(
                    field_result.required
                    and field_result.verdict.value == "invalid"
                    for field_result in validity_result.field_results
                )
                is_duplicate = (
                    str(duplicate_result.status.value).lower() == "duplicate"
                )

                reasons: list[str] = []
                if not has_coordinates:
                    status = "MissingCoordinate"
                    if store.latitude is None:
                        reasons.append("latitude_missing")
                    if store.longitude is None:
                        reasons.append("longitude_missing")
                elif coordinate_status == "invalid":
                    status = "Invalid"
                    reasons.append("coordinate_invalid")
                elif has_blocking_validity_error:
                    status = "Invalid"
                    reasons.append("required_field_invalid")
                elif (
                    completeness_result.passed
                    and coordinate_status == "valid"
                    and not is_duplicate
                ):
                    status = "Ready"
                else:
                    status = "Review"
                    if not completeness_result.passed:
                        reasons.append("incomplete_required_data")
                    if coordinate_status in {"warning", "unknown"}:
                        reasons.append(f"coordinate_{coordinate_status}")
                    if is_duplicate:
                        reasons.append("duplicate")

                readiness_rows.append({
                    "store": store,
                    "status": status,
                    "ready": status == "Ready",
                    "reasons": reasons,
                    "coordinate": coordinate_result,
                    "coordinate_status": coordinate_status,
                    "completeness": completeness_result,
                    "validity": validity_result,
                    "duplicate": duplicate_result,
                })

            comp = completeness_acc.finalize()
            valid = validity_acc.finalize()
            duplicate = duplicate_acc.finalize()

            ready_count = sum(1 for row in readiness_rows if row["ready"])
            review_count = sum(
                1 for row in readiness_rows if row["status"] == "Review"
            )
            invalid_count = sum(
                1 for row in readiness_rows if row["status"] == "Invalid"
            )
            missing_coordinate_count = sum(
                1
                for row in readiness_rows
                if row["status"] == "MissingCoordinate"
            )
            with_coordinates = sum(
                1
                for row in readiness_rows
                if row["store"].latitude is not None
                and row["store"].longitude is not None
            )
            matched_to_master = sum(
                1 for row in readiness_rows if row["store"].master_store_id is not None
            )
            if not readiness_rows or ready_count == 0:
                readiness_status = "not_ready"
            elif ready_count == len(readiness_rows):
                readiness_status = "ready"
            else:
                readiness_status = "ready_with_warning"

            readiness_percentage = (
                round(ready_count * 100 / len(readiness_rows), 1)
                if readiness_rows
                else 0.0
            )

            results = {
                "completeness": {
                    "audit_run_id": audit_run_id,
                    "total_stores": comp.total_stores,
                    "evaluated_stores": comp.evaluated_stores,
                    "passed_stores": comp.passed_stores,
                    "fully_complete_stores": comp.fully_complete_stores,
                    "overall_percentage": comp.overall_percentage,
                    "average_raw_score": comp.average_raw_score,
                    "median_percentage": comp.median_percentage,
                    "min_percentage": comp.min_percentage,
                    "max_percentage": comp.max_percentage,
                    "group_scores": comp.group_summary,
                    "field_fill_rates": comp.field_summary,
                },
                "validity": {
                    "audit_run_id": audit_run_id,
                    "total_stores": valid.total_stores,
                    "evaluated_stores": valid.evaluated_stores,
                    "passed_stores": valid.passed_stores,
                    "fully_valid_stores": valid.fully_valid_stores,
                    "overall_percentage": valid.overall_percentage,
                    "average_raw_score": valid.average_raw_score,
                    "median_percentage": valid.median_percentage,
                    "min_percentage": valid.min_percentage,
                    "max_percentage": valid.max_percentage,
                    "invalid_field_count": valid.invalid_field_count,
                    "warning_field_count": valid.warning_field_count,
                    "unknown_field_count": valid.unknown_field_count,
                    "group_scores": valid.group_summary,
                    "field_validity_rates": valid.field_summary,
                },
                "duplicates": {
                    "audit_run_id": audit_run_id,
                    "store_count": duplicate.store_count,
                    "unique_count": duplicate.unique_count,
                    "possible_duplicate_count": duplicate.possible_duplicate_count,
                    "duplicate_count": duplicate.duplicate_count,
                    "unknown_count": duplicate.unknown_count,
                    "candidate_count": duplicate.candidate_count,
                },
                "distribution_readiness": {
                    "audit_run_id": audit_run_id,
                    "status": readiness_status,
                    "total_stores": len(readiness_rows),
                    "ready_stores": ready_count,
                    "review_stores": review_count,
                    "invalid_stores": invalid_count,
                    "missing_coordinate_stores": missing_coordinate_count,
                    "stores_with_coordinates": with_coordinates,
                    "stores_without_coordinates": len(readiness_rows) - with_coordinates,
                    "matched_to_master": matched_to_master,
                    "unmatched_to_master": len(readiness_rows) - matched_to_master,
                    "percentage": readiness_percentage,
                },
            }

            return {
                "audit_run_id": audit_run_id,
                "project_id": self.project_id,
                "batch_id": self.batch_id,
                "audited_store_count": len(stores),
                "elapsed_sec": round(time.time() - started, 3),
                "results": results,
                "map_geojson": self._build_geojson(readiness_rows),
                "missing_coordinate_rows": self._build_missing_coordinate_rows(
                    readiness_rows
                ),
            }
        finally:
            if self._owns_session:
                self.db.close()

    def _load_project_store_views(self) -> tuple[ProjectStoreAuditView, ...]:
        from app.repositories.store_dataset_repository import StoreDatasetRepository
        dataset = StoreDatasetRepository(self.db)
        views = []
        seen = set()
        for row, company, master, evidence in dataset.audit_rows(self.project_id, self.batch_id):
            if row.id in seen:
                continue
            seen.add(row.id)
            view = self._build_store_view(dataset.input_view(company, row.snapshot), master, evidence)
            views.append(replace(view, source_id=f"import_batch:{self.batch_id}:row:{row.row_number}"))
        return tuple(views)

    @classmethod
    def _build_store_view(
        cls,
        company: Any,
        master: Any | None,
        evidence: Any | None,
    ) -> ProjectStoreAuditView:
        """Compose the exact Matching -> Readiness data contract.

        A confirmed Master Store is authoritative.  For a new/unmatched store,
        normalized import evidence is preferred, followed by raw import values
        and finally CompanyStore values.  Keeping this precedence in one tested
        function prevents later geocoding work from silently changing DIP's
        business ownership rules.
        """

        first = cls._first_value
        return ProjectStoreAuditView(
            id=company.id,
            company_store_id=company.id,
            master_store_id=company.master_store_id,
            canonical_name=first(
                getattr(master, "canonical_name", None),
                company.name,
            ),
            manager_name=getattr(master, "manager_name", None),
            canonical_phone=first(
                getattr(master, "canonical_phone", None),
                company.phone,
            ),
            mobile=getattr(master, "mobile", None),
            province_id=getattr(master, "province_id", None),
            city_id=getattr(master, "city_id", None),
            address=first(
                getattr(master, "address", None),
                getattr(evidence, "normalized_address", None),
                getattr(evidence, "address_text", None),
                company.address,
            ),
            postal_code=first(
                getattr(master, "postal_code", None),
                getattr(evidence, "postal_code", None),
                company.postal_code,
            ),
            plaque=getattr(master, "plaque", None),
            unit=getattr(master, "unit", None),
            floor=getattr(master, "floor", None),
            latitude=cls._as_float(first(
                getattr(master, "latitude", None),
                getattr(evidence, "normalized_latitude", None),
                getattr(evidence, "latitude", None),
                company.latitude,
            )),
            longitude=cls._as_float(first(
                getattr(master, "longitude", None),
                getattr(evidence, "normalized_longitude", None),
                getattr(evidence, "longitude", None),
                company.longitude,
            )),
            source_id=getattr(evidence, "source_id", None),
        )

    @staticmethod
    def _build_geojson(rows: list[dict[str, Any]]) -> dict[str, Any]:
        features: list[dict[str, Any]] = []
        for row in rows:
            store = row["store"]
            if store.latitude is None or store.longitude is None:
                continue
            status = row["status"]
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [store.longitude, store.latitude],
                },
                "properties": {
                    "store_id": store.master_store_id,
                    "company_store_id": store.company_store_id,
                    "title": store.canonical_name or "فروشگاه بدون نام",
                    "readiness_status": status,
                    "coordinate_status": row["coordinate_status"],
                    "reasons": row["reasons"],
                    "matched_to_master": store.master_store_id is not None,
                    "completeness_percentage": row["completeness"].percentage,
                    "validity_percentage": row["validity"].percentage,
                    "duplicate_status": row["duplicate"].status.value,
                    "cluster_weight": 1,
                },
            })
        return {"type": "FeatureCollection", "features": features}

    @staticmethod
    def _build_missing_coordinate_rows(
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for row in rows:
            if row["status"] != "MissingCoordinate":
                continue
            store = row["store"]
            missing_fields: list[str] = []
            if store.latitude is None:
                missing_fields.append("latitude")
            if store.longitude is None:
                missing_fields.append("longitude")
            result.append({
                "source_row": AuditRunner._source_row(store.source_id),
                "company_store_id": store.company_store_id,
                "master_store_id": store.master_store_id,
                "title": store.canonical_name or "فروشگاه بدون نام",
                "address": store.address or "",
                "missing_fields": missing_fields,
                "has_address_for_geocoding": bool(
                    store.address and store.address.strip()
                ),
                "reasons": row["reasons"],
            })
        return result

    @staticmethod
    def _source_row(source_id: str | None) -> int | None:
        if not source_id:
            return None
        marker = ":row:"
        if marker not in source_id:
            return None
        try:
            return int(source_id.rsplit(marker, 1)[1])
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _verdict_name(value: Any) -> str:
        raw = getattr(value, "value", value)
        return str(raw).strip().lower()

    @staticmethod
    def _first_value(*values: Any) -> Any:
        for value in values:
            if value is not None and (not isinstance(value, str) or value.strip()):
                return value
        return None

    @staticmethod
    def _as_float(value: Any) -> float | None:
        try:
            if value is None:
                return None
            result = float(value)
            return result if math.isfinite(result) else None
        except (TypeError, ValueError):
            return None


def run(project_id: int, batch_id: int) -> dict[str, Any]:
    return AuditRunner(project_id=project_id, batch_id=batch_id).run()


__all__ = ["AuditRunner", "ProjectStoreAuditView", "run"]

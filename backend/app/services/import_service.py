from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.enums import EntityType, ImportStatus
from app.core.exceptions import FileProcessingError
from app.schemas.import_schema import (
    BatchProgressResponse,
    EntityTypeEnum,
    ImportPreviewResponse,
    ImportProgressResponse,
    ImportStartRequest,
    ImportStartResponse,
    ImportStatusEnum,
    ValidationReport,
)
from app.services.excel_service import ExcelService
from app.services.profiling_service import ProfilingService
from app.services.validation_service import ValidationService

logger = logging.getLogger(__name__)


ENTITY_TYPE_MAP: dict[EntityTypeEnum, EntityType] = {
    EntityTypeEnum.STORE: EntityType.STORE,
    EntityTypeEnum.ORDER: EntityType.ORDER,
    EntityTypeEnum.FLEET: EntityType.FLEET,
    EntityTypeEnum.DRIVER: EntityType.DRIVER,
    EntityTypeEnum.GPS: EntityType.GPS,
}


STATUS_MAP: dict[ImportStatusEnum, ImportStatus] = {
    ImportStatusEnum.PENDING: ImportStatus.PROCESSING,
    ImportStatusEnum.VALIDATING: ImportStatus.PROCESSING,
    ImportStatusEnum.VALIDATED: ImportStatus.PROCESSING,
    ImportStatusEnum.IMPORTING: ImportStatus.PROCESSING,
    ImportStatusEnum.COMPLETED: ImportStatus.COMPLETED,
    ImportStatusEnum.PARTIAL: ImportStatus.COMPLETED_WITH_ERRORS,
    ImportStatusEnum.FAILED: ImportStatus.FAILED,
}


FIELD_ALIASES: dict[EntityTypeEnum, dict[str, list[str]]] = {
    EntityTypeEnum.STORE: {
        "canonical_name": [
            "canonical_name",
            "نام فروشگاه",
            "نام",
            "name",
            "store name",
            "store_name",
        ],
        "canonical_phone": [
            "canonical_phone",
            "تلفن فروشگاه",
            "تلفن",
            "شماره تلفن",
            "شماره",
            "phone",
        ],
        "address": [
            "address",
            "آدرس",
            "نشانی",
        ],
        "shop_type": [
            "shop_type",
            "نوع فروشگاه",
            "نوع",
            "category",
            "دسته",
            "گروه",
        ],
        "postal_code": [
            "postal_code",
            "کد پستی",
            "کدپستی",
            "post code",
            "postcode",
            "zip",
            "zip code",
        ],
        "plaque": [
            "plaque",
            "پلاک",
            "شماره پلاک",
            "پلاک ساختمان",
        ],
        "unit": [
            "unit",
            "واحد",
            "شماره واحد",
        ],
        "floor": [
            "floor",
            "طبقه",
        ],
        "latitude": [
            "latitude",
            "lat",
            "عرض جغرافیایی",
            "عرض",
        ],
        "longitude": [
            "longitude",
            "lon",
            "lng",
            "long",
            "طول جغرافیایی",
            "طول",
        ],
        "manager_name": [
            "manager_name",
            "نام مدیر",
            "مدیر",
        ],
        "mobile": [
            "mobile",
            "موبایل مدیر",
            "شماره موبایل",
            "شماره همراه",
            "manager_mobile",
        ],
        "store_code": [
            "store_code",
            "code",
            "کد فروشگاه",
            "شناسه فروشگاه",
        ],
        "name": [
            "name",
            "shop_name",
            "store_name",
            "نام فروشگاه",
            "نام",
        ],
        "phone": [
            "phone",
            "telephone",
            "tel",
            "شماره تلفن",
            "تلفن",
        ],
        "province_id": [
            "province_id",
            "شناسه استان",
        ],
        "city_id": [
            "city_id",
            "شناسه شهر",
        ],
        "province_name": [
            "province_name",
            "province",
            "استان",
        ],
        "city_name": [
            "city_name",
            "city",
            "شهر",
        ],
    },

    EntityTypeEnum.ORDER: {
        "order_code": [
            "order_code",
            "کد سفارش",
            "شماره سفارش",
            "order id",
        ],
        "store_code": [
            "store_code",
            "کد فروشگاه",
            "store code",
        ],
        "store_name": [
            "store_name",
            "نام فروشگاه",
            "store name",
        ],
        "delivery_date": [
            "delivery_date",
            "تاریخ تحویل",
        ],
        "delivery_time_from": [
            "delivery_time_from",
            "شروع بازه تحویل",
        ],
        "delivery_time_to": [
            "delivery_time_to",
            "پایان بازه تحویل",
        ],
        "address": [
            "address",
            "آدرس",
            "نشانی",
        ],
        "latitude": [
            "latitude",
            "lat",
            "عرض جغرافیایی",
            "عرض",
        ],
        "longitude": [
            "longitude",
            "lon",
            "lng",
            "طول جغرافیایی",
            "طول",
        ],
        "weight_kg": [
            "weight_kg",
            "وزن",
            "weight",
        ],
        "volume_m3": [
            "volume_m3",
            "حجم",
            "volume",
        ],
        "item_count": [
            "item_count",
            "تعداد",
            "count",
            "quantity",
        ],
        "special_instructions": [
            "special_instructions",
            "توضیحات",
            "دستور خاص",
        ],
        "status": [
            "status",
            "وضعیت",
        ],
    },

    EntityTypeEnum.FLEET: {
        "plate": [
            "plate",
            "پلاک",
            "شماره پلاک",
            "license plate",
        ],
        "vehicle_type": [
            "vehicle_type",
            "نوع خودرو",
            "type",
        ],
        "model": [
            "model",
            "مدل",
            "خودرو",
        ],
        "capacity_kg": [
            "capacity_kg",
            "ظرفیت",
            "capacity",
        ],
        "volume_m3": [
            "volume_m3",
            "حجم",
            "volume",
        ],
        "cost_per_km": [
            "cost_per_km",
            "هزینه هر کیلومتر",
            "cost",
        ],
        "fixed_cost": [
            "fixed_cost",
            "هزینه ثابت",
        ],
        "latitude": [
            "latitude",
            "lat",
            "عرض جغرافیایی",
            "عرض",
        ],
        "longitude": [
            "longitude",
            "lon",
            "lng",
            "طول جغرافیایی",
            "طول",
        ],
        "available_from": [
            "available_from",
            "شروع دسترسی",
        ],
        "available_until": [
            "available_until",
            "پایان دسترسی",
        ],
        "status": [
            "status",
            "وضعیت",
        ],
    },

    EntityTypeEnum.DRIVER: {
        "driver_code": [
            "driver_code",
            "کد راننده",
            "driver code",
        ],
        "first_name": [
            "first_name",
            "نام",
        ],
        "last_name": [
            "last_name",
            "نام خانوادگی",
        ],
        "national_code": [
            "national_code",
            "کد ملی",
        ],
        "phone": [
            "phone",
            "تلفن",
            "موبایل",
            "mobile",
        ],
        "license_number": [
            "license_number",
            "شماره گواهینامه",
            "گواهینامه",
        ],
        "license_expiry": [
            "license_expiry",
            "تاریخ انقضای گواهینامه",
        ],
        "latitude": [
            "latitude",
            "lat",
            "عرض جغرافیایی",
            "عرض",
        ],
        "longitude": [
            "longitude",
            "lon",
            "lng",
            "طول جغرافیایی",
            "طول",
        ],
        "status": [
            "status",
            "وضعیت",
        ],
    },

    EntityTypeEnum.GPS: {
        "vehicle_plate": [
            "vehicle_plate",
            "پلاک",
            "plate",
        ],
        "latitude": [
            "latitude",
            "lat",
            "عرض جغرافیایی",
            "عرض",
        ],
        "longitude": [
            "longitude",
            "lon",
            "lng",
            "طول جغرافیایی",
            "طول",
        ],
        "timestamp": [
            "timestamp",
            "زمان",
            "time",
            "تاریخ",
        ],
        "speed_kmh": [
            "speed_kmh",
            "سرعت",
            "speed",
        ],
        "heading": [
            "heading",
            "جهت",
            "سمت",
        ],
        "accuracy_m": [
            "accuracy_m",
            "دقت",
            "accuracy",
        ],
    },
}


class ImportService:
    BATCH_SIZE: int = 500

    def __init__(self, db: Session) -> None:
        self.db = db
        self.excel_service = ExcelService()
        self.validation_service = ValidationService()
        self.profiling_service = ProfilingService()
        self._batches: dict[int, dict[str, Any]] = {}
        self._progress: dict[int, ImportProgressResponse] = {}

    # ==========================================================
    # Start Import
    # ==========================================================

    def start_import(
        self,
        request: ImportStartRequest,
        file_path: str,
    ) -> ImportStartResponse:
        from app.models.import_batch import ImportBatch

        entity_type = request.entity_type
        file_id = request.file_id

        if entity_type not in ENTITY_TYPE_MAP:
            raise FileProcessingError(
                f"Unsupported entity type: {entity_type}"
            )

        try:
            parsed = self.excel_service.parse(file_path)
        except FileProcessingError as exc:
            raise FileProcessingError(
                f"Cannot start import: failed to parse file: {exc}"
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected error while parsing file.")
            raise FileProcessingError(
                f"Cannot start import: unexpected parsing error: {exc}"
            ) from exc

        if not isinstance(parsed, dict):
            raise FileProcessingError(
                "ExcelService returned an invalid parsing result."
            )

        rows = parsed.get("rows", [])

        if not isinstance(rows, list):
            raise FileProcessingError(
                "Parsed file rows must be a list."
            )

        if not rows:
            raise FileProcessingError(
                "File contains no data rows."
            )

        total_rows = len(rows)
        file_name = parsed.get("file_name") or str(file_path)

        raw_mapping = request.column_mapping or {}

        suggested_mapping = self._suggest_mapping(
            headers=list(rows[0].keys()),
            entity_type=entity_type,
        )

        column_mapping = self._normalize_column_mapping(
            mapping=raw_mapping,
            entity_type=entity_type,
            headers=list(rows[0].keys()),
        )

        if not column_mapping:
            column_mapping = suggested_mapping

        batch = ImportBatch(
            file_id=file_id,
            entity_type=ENTITY_TYPE_MAP[entity_type],
            status=STATUS_MAP[ImportStatusEnum.PENDING],
            total_rows=total_rows,
            imported_rows=0,
            error_rows=0,
            column_mapping=column_mapping,
            started_at=None,
        )

        self.db.add(batch)

        try:
            self.db.commit()
            self.db.refresh(batch)
        except Exception as exc:
            self.db.rollback()
            logger.exception("Failed to create import batch.")
            raise FileProcessingError(
                f"Cannot create import batch: {exc}"
            ) from exc

        batch_id = batch.id

        self._batches[batch_id] = {
            "batch": batch,
            "file_path": file_path,
            "column_mapping": column_mapping,
            "skip_validation": bool(request.skip_validation),
            "entity_type": entity_type,
            "parsed": parsed,
            "created_at": datetime.now(timezone.utc),
        }

        self._progress[batch_id] = ImportProgressResponse(
            batch_id=batch_id,
            entity_type=entity_type,
            status=ImportStatusEnum.PENDING,
            total_rows=total_rows,
            processed_rows=0,
            error_count=0,
            progress_percent=0.0,
            current_phase="PENDING",
            started_at=None,
        )

        logger.info(
            "Import batch created: batch_id=%s entity=%s rows=%s",
            batch_id,
            entity_type.value,
            total_rows,
        )

        return ImportStartResponse(
            batch_id=batch_id,
            entity_type=entity_type,
            file_name=file_name,
            total_rows=total_rows,
            status=ImportStatusEnum.PENDING,
            message=(
                f"Import batch #{batch_id} created with "
                f"{total_rows} rows. Processing will begin shortly."
            ),
        )

    # ==========================================================
    # Preview
    # ==========================================================

    def preview_import(
        self,
        file_path: str,
        entity_type: EntityTypeEnum,
    ) -> ImportPreviewResponse:
        if entity_type not in ENTITY_TYPE_MAP:
            raise FileProcessingError(
                f"Unsupported entity type: {entity_type}"
            )

        try:
            preview = self.excel_service.preview(
                file_path,
                sample_size=10,
            )
        except FileProcessingError:
            raise
        except Exception as exc:
            logger.exception(
                "Failed to generate import preview."
            )
            raise FileProcessingError(
                f"Cannot generate import preview: {exc}"
            ) from exc

        if not isinstance(preview, dict):
            raise FileProcessingError(
                "ExcelService returned an invalid preview result."
            )

        headers = preview.get("headers", [])
        sample_rows = preview.get("sample_rows", [])
        total_rows = preview.get(
            "total_rows",
            len(sample_rows),
        )

        suggested_mapping = self._suggest_mapping(
            headers=headers,
            entity_type=entity_type,
        )

        return ImportPreviewResponse(
            file_name=preview.get("file_name") or str(file_path),
            entity_type=entity_type,
            total_rows=total_rows,
            headers=headers,
            sample_rows=sample_rows,
            suggested_mapping=suggested_mapping,
        )

    # ==========================================================
    # Validation Error Persistence
    # ==========================================================

    def _persist_validation_errors(
        self,
        batch_id: int,
        validation_report: Any,
    ) -> int:
        errors = getattr(
            validation_report,
            "errors",
            None,
        ) or []

        if not errors:
            return 0

        try:
            result = self.db.execute(
                text(
                    "SELECT column_name "
                    "FROM information_schema.columns "
                    "WHERE table_schema = current_schema() "
                    "AND table_name = 'row_errors'"
                )
            )

            table_columns = {
                row[0]
                for row in result
            }

        except Exception as exc:
            logger.exception(
                "Cannot introspect row_errors table "
                "for batch=%s: %s",
                batch_id,
                exc,
            )
            self.db.rollback()
            return 0

        if not table_columns:
            logger.warning(
                "row_errors table not found; "
                "skipping persistence for batch=%s.",
                batch_id,
            )
            return 0

        batch_column = (
            "import_batch_id"
            if "import_batch_id" in table_columns
            else "batch_id"
            if "batch_id" in table_columns
            else None
        )

        if batch_column is None:
            logger.error(
                "row_errors has no batch reference "
                "column for batch=%s.",
                batch_id,
            )
            return 0

        inserted = 0

        for error in errors:
            severity = getattr(
                error,
                "severity",
                "ERROR",
            )

            severity = getattr(
                severity,
                "value",
                severity,
            )

            error_code = (
                getattr(error, "code", None)
                or getattr(error, "error_code", None)
                or "VALIDATION_ERROR"
            )

            error_type = (
                getattr(error, "error_type", None)
                or error_code
                or "VALIDATION_ERROR"
            )

            candidates: dict[str, Any] = {
                batch_column: batch_id,
                "row_number": getattr(
                    error,
                    "row_number",
                    None,
                ),
                "column_name": (
                    getattr(error, "column_name", None)
                    or getattr(error, "field", None)
                    or getattr(error, "field_name", None)
                ),
                "field_name": (
                    getattr(error, "field", None)
                    or getattr(error, "field_name", None)
                    or getattr(error, "column_name", None)
                ),
                "raw_value": getattr(
                    error,
                    "raw_value",
                    None,
                ),
                "error_code": error_code,
                "error_type": str(error_type),
                "error_message": (
                    getattr(error, "message", None)
                    or getattr(error, "error_message", None)
                    or str(error)
                ),
                "severity": str(severity).upper(),
                "created_at": datetime.now(timezone.utc),
            }

            row_values = {
                key: value
                for key, value in candidates.items()
                if key in table_columns
                and value is not None
            }

            if batch_column not in row_values:
                continue

            try:
                with self.db.begin_nested():
                    columns_sql = ", ".join(
                        row_values
                    )

                    params_sql = ", ".join(
                        f":{key}"
                        for key in row_values
                    )

                    self.db.execute(
                        text(
                            f"INSERT INTO row_errors "
                            f"({columns_sql}) "
                            f"VALUES ({params_sql})"
                        ),
                        row_values,
                    )

                inserted += 1

            except Exception as exc:
                logger.exception(
                    "Failed to persist RowError "
                    "for batch=%s row=%s: %s",
                    batch_id,
                    getattr(
                        error,
                        "row_number",
                        "?",
                    ),
                    exc,
                )

        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.exception(
                "Failed to commit row_errors "
                "for batch=%s: %s",
                batch_id,
                exc,
            )
            return 0

        logger.info(
            "Persisted %s row_errors for batch=%s",
            inserted,
            batch_id,
        )

        return inserted

    # ==========================================================
    # STORE Ownership
    # ==========================================================

    def _resolve_store_ownership(
        self,
        batch: Any,
    ) -> tuple[int, int]:
        from app.models.file import File
        from app.models.project import Project

        source_file = self.db.get(
            File,
            batch.file_id,
        )

        if source_file is None:
            raise FileProcessingError(
                f"Source file #{batch.file_id} "
                f"not found for STORE import."
            )

        source_entity_type = str(
            source_file.entity_type or ""
        ).strip().upper()

        if source_entity_type != "PROJECT":
            raise FileProcessingError(
                "STORE imports must belong to a PROJECT file. "
                f"file_id={source_file.id} "
                f"entity_type={source_file.entity_type!r}"
            )

        project = self.db.get(
            Project,
            source_file.entity_id,
        )

        if project is None:
            raise FileProcessingError(
                f"Project #{source_file.entity_id} "
                f"not found for file #{source_file.id}."
            )

        company_id = getattr(
            project,
            "company_id",
            None,
        )

        if company_id is None:
            raise FileProcessingError(
                f"Project #{project.id} has no company_id."
            )

        return (
            int(project.id),
            int(company_id),
        )

    # ==========================================================
    # Geography
    # ==========================================================

    def _resolve_store_geography(
        self,
        province_id: int | None,
        city_id: int | None,
    ) -> tuple[str | None, str | None]:
        """
        Resolve Intake province_id / city_id to their canonical names.

        Important:
        - No deep geography is resolved here.
        - The selected city must belong to the selected province.
        - If IDs are supplied but invalid, import must fail rather than
          silently persisting incorrect geography.
        """

        if province_id is None and city_id is None:
            return None, None

        if province_id is None and city_id is not None:
            raise FileProcessingError(
                "city_id was provided without province_id."
            )

        province_row = self.db.execute(
            text(
                "SELECT id, name "
                "FROM provinces "
                "WHERE id = :province_id"
            ),
            {
                "province_id": province_id,
            },
        ).mappings().first()

        if province_row is None:
            raise FileProcessingError(
                f"Province #{province_id} not found."
            )

        province_name = self._clean_optional(
            province_row.get("name")
        )

        if city_id is None:
            return (
                str(province_name)
                if province_name is not None
                else None,
                None,
            )

        city_row = self.db.execute(
            text(
                "SELECT id, name, province_id "
                "FROM cities "
                "WHERE id = :city_id"
            ),
            {
                "city_id": city_id,
            },
        ).mappings().first()

        if city_row is None:
            raise FileProcessingError(
                f"City #{city_id} not found."
            )

        city_province_id = city_row.get(
            "province_id"
        )

        if (
            city_province_id is None
            or int(city_province_id) != int(province_id)
        ):
            raise FileProcessingError(
                f"City #{city_id} does not belong "
                f"to Province #{province_id}."
            )

        city_name = self._clean_optional(
            city_row.get("name")
        )

        return (
            str(province_name)
            if province_name is not None
            else None,
            str(city_name)
            if city_name is not None
            else None,
        )

    # ==========================================================
    # Process Batch
    # ==========================================================

    def process_batch(
        self,
        batch_id: int,
        province_id: int | None = None,
        city_id: int | None = None,
    ) -> ImportProgressResponse:
        ctx = self._batches.get(
            batch_id
        )

        if ctx is None:
            raise FileProcessingError(
                f"Batch #{batch_id} not found."
            )

        batch = ctx["batch"]
        parsed = ctx["parsed"]
        entity_type = ctx["entity_type"]
        column_mapping = ctx["column_mapping"]
        skip_validation = ctx["skip_validation"]

        rows: list[dict[str, Any]] = parsed.get(
            "rows",
            [],
        )

        total = len(rows)

        project_id: int | None = None
        company_id: int | None = None

        intake_province_name: str | None = None
        intake_city_name: str | None = None

        if entity_type == EntityTypeEnum.STORE:
            project_id, company_id = (
                self._resolve_store_ownership(
                    batch
                )
            )

            (
                intake_province_name,
                intake_city_name,
            ) = self._resolve_store_geography(
                province_id=province_id,
                city_id=city_id,
            )

            logger.info(
                "Resolved STORE context: "
                "batch=%s file_id=%s "
                "project_id=%s company_id=%s "
                "province_id=%s province=%r "
                "city_id=%s city=%r",
                batch_id,
                batch.file_id,
                project_id,
                company_id,
                province_id,
                intake_province_name,
                city_id,
                intake_city_name,
            )

        if total == 0:
            self._mark_batch_failed(
                batch,
                batch_id=batch_id,
                message=(
                    "No rows available for processing."
                ),
            )

            raise FileProcessingError(
                f"Batch #{batch_id} contains no rows."
            )

        if batch.started_at is None:
            batch.started_at = (
                datetime.now(timezone.utc)
            )

            try:
                self.db.commit()
            except Exception as exc:
                self.db.rollback()
                logger.exception(
                    "Failed to record start time "
                    "for batch %s.",
                    batch_id,
                )
                raise FileProcessingError(
                    f"Failed to record start time: {exc}"
                ) from exc

            progress = self._progress.get(
                batch_id
            )

            if progress is not None:
                progress.started_at = (
                    batch.started_at
                )

        self._update_progress(
            batch_id=batch_id,
            status=ImportStatusEnum.VALIDATING,
            phase="VALIDATING",
            processed=0,
            errors=0,
        )

        canonical_rows: list[
            dict[str, Any]
        ] = []

        for raw_row in rows:
            canonical_rows.append(
                self._apply_mapping(
                    row=raw_row,
                    mapping=column_mapping,
                    entity_type=entity_type,
                )
            )

        if skip_validation:
            validation_report = ValidationReport(
                batch_id=batch_id,
                entity_type=entity_type,
                total_rows=total,
                valid_rows=total,
                error_rows=0,
                warning_rows=0,
                errors=[],
                is_valid=True,
                validated_at=datetime.now(
                    timezone.utc
                ),
            )
        else:
            validation_report = (
                self.validation_service.validate(
                    rows=canonical_rows,
                    entity_type=entity_type,
                    column_mapping=None,
                    strict_geography=True,
                    batch_id=batch_id,
                )
            )

        if not skip_validation:
            persisted_errors = (
                self._persist_validation_errors(
                    batch_id=batch_id,
                    validation_report=validation_report,
                )
            )

            logger.info(
                "Validation error persistence: "
                "batch=%s report_errors=%s persisted=%s",
                batch_id,
                validation_report.error_rows,
                persisted_errors,
            )

        batch.status = STATUS_MAP[
            ImportStatusEnum.VALIDATED
        ]

        if hasattr(batch, "valid_rows"):
            batch.valid_rows = (
                validation_report.valid_rows
            )

        if hasattr(batch, "error_rows"):
            batch.error_rows = (
                validation_report.error_rows
            )

        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.exception(
                "Failed to persist validation "
                "result for batch %s.",
                batch_id,
            )
            raise FileProcessingError(
                f"Failed to save validation result: {exc}"
            ) from exc

        self._update_progress(
            batch_id=batch_id,
            status=ImportStatusEnum.VALIDATED,
            phase=(
                "VALIDATED"
                if validation_report.is_valid
                else "VALIDATED_WITH_ERRORS"
            ),
            processed=0,
            errors=validation_report.error_rows,
        )

        error_row_numbers: set[int] = set()

        if (
            not validation_report.is_valid
            and not skip_validation
        ):
            error_row_numbers = {
                error.row_number
                for error in validation_report.errors
                if str(
                    getattr(
                        error.severity,
                        "value",
                        error.severity,
                    )
                ).upper() == "ERROR"
            }

        self._update_progress(
            batch_id=batch_id,
            status=ImportStatusEnum.IMPORTING,
            phase="IMPORTING",
            processed=0,
            errors=validation_report.error_rows,
        )

        imported = 0
        errors_during_import = 0

        mapped_rows: list[
            tuple[int, dict[str, Any]]
        ] = []

        for row_number, canonical_row in enumerate(
            canonical_rows,
            start=1,
        ):
            if row_number in error_row_numbers:
                continue

            mapped_rows.append(
                (
                    row_number,
                    canonical_row,
                )
            )

        for chunk_start in range(
            0,
            len(mapped_rows),
            self.BATCH_SIZE,
        ):
            chunk = mapped_rows[
                chunk_start:
                chunk_start + self.BATCH_SIZE
            ]

            chunk_success_count = 0
            chunk_error_count = 0

            for row_number, mapped_row in chunk:
                try:
                    with self.db.begin_nested():
                        self._persist_row(
                            entity_type=entity_type,
                            batch_id=batch_id,
                            row_number=row_number,
                            mapped_row=mapped_row,
                            province_id=province_id,
                            city_id=city_id,
                            province_name=(
                                intake_province_name
                            ),
                            city_name=(
                                intake_city_name
                            ),
                            project_id=project_id,
                            company_id=company_id,
                        )

                        self.db.flush()

                    chunk_success_count += 1

                except Exception as exc:
                    chunk_error_count += 1

                    logger.exception(
                        "Import failed for "
                        "batch=%s row=%s: %s",
                        batch_id,
                        row_number,
                        exc,
                    )

            if chunk_success_count > 0:
                try:
                    self.db.commit()
                    imported += (
                        chunk_success_count
                    )
                except Exception as exc:
                    self.db.rollback()
                    logger.exception(
                        "Chunk commit failed "
                        "for batch=%s: %s",
                        batch_id,
                        exc,
                    )
                    chunk_error_count += (
                        chunk_success_count
                    )
            else:
                self.db.rollback()

            errors_during_import += (
                chunk_error_count
            )

            processed_rows = min(
                total,
                len(error_row_numbers)
                + imported
                + errors_during_import,
            )

            self._update_progress(
                batch_id=batch_id,
                status=ImportStatusEnum.IMPORTING,
                phase="IMPORTING",
                processed=processed_rows,
                errors=(
                    validation_report.error_rows
                    + errors_during_import
                ),
            )

        total_errors = (
            validation_report.error_rows
            + errors_during_import
        )

        if imported == 0:
            final_status = (
                ImportStatusEnum.FAILED
            )
        elif total_errors > 0:
            final_status = (
                ImportStatusEnum.PARTIAL
            )
        else:
            final_status = (
                ImportStatusEnum.COMPLETED
            )

        batch.status = STATUS_MAP[
            final_status
        ]

        if hasattr(batch, "imported_rows"):
            batch.imported_rows = imported

        if hasattr(batch, "error_rows"):
            batch.error_rows = total_errors

        batch.completed_at = (
            datetime.now(timezone.utc)
        )

        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.exception(
                "Failed to finalize batch %s.",
                batch_id,
            )
            raise FileProcessingError(
                f"Failed to finalize import batch: {exc}"
            ) from exc

        try:
            profile = (
                self.profiling_service.profile(
                    entity_type=entity_type,
                    rows=canonical_rows,
                )
            )

            ctx["profile"] = profile

            logger.info(
                "Profiling completed "
                "for batch=%s entity=%s",
                batch_id,
                entity_type.value,
            )

        except Exception as exc:
            logger.exception(
                "Profiling failed for "
                "batch=%s: %s",
                batch_id,
                exc,
            )

            ctx["profile"] = {
                "entity": entity_type.value,
                "error": str(exc),
            }

        self._update_progress(
            batch_id=batch_id,
            status=final_status,
            phase="DONE",
            processed=total,
            errors=total_errors,
        )

        logger.info(
            "Import completed: "
            "batch=%s status=%s "
            "total=%s imported=%s errors=%s",
            batch_id,
            final_status.value,
            total,
            imported,
            total_errors,
        )

        return self._progress[
            batch_id
        ]

    # ==========================================================
    # Progress
    # ==========================================================

    def get_progress(
        self,
        batch_id: int,
    ) -> ImportProgressResponse:
        progress = self._progress.get(
            batch_id
        )

        if progress is None:
            raise FileProcessingError(
                f"No progress found "
                f"for batch #{batch_id}."
            )

        started_at = progress.started_at

        if started_at is not None:
            if started_at.tzinfo is None:
                started_at = (
                    started_at.replace(
                        tzinfo=timezone.utc
                    )
                )

            elapsed = (
                datetime.now(timezone.utc)
                - started_at
            ).total_seconds()

            progress.elapsed_seconds = max(
                0.0,
                elapsed,
            )

            if (
                progress.processed_rows > 0
                and progress.progress_percent > 0
            ):
                total_estimated = (
                    elapsed
                    / (
                        progress.progress_percent
                        / 100
                    )
                )

                progress.estimated_remaining_seconds = max(
                    0.0,
                    total_estimated - elapsed,
                )

        return progress

    def get_batch_progress(
        self,
        batch_id: int,
    ) -> BatchProgressResponse:
        from app.models.import_batch import ImportBatch

        batch = (
            self.db.query(ImportBatch)
            .filter(
                ImportBatch.id == batch_id
            )
            .first()
        )

        if batch is None:
            raise FileProcessingError(
                f"Batch #{batch_id} not found."
            )

        imported_rows = (
            getattr(
                batch,
                "imported_rows",
                0,
            )
            or 0
        )

        error_rows = (
            getattr(
                batch,
                "error_rows",
                0,
            )
            or 0
        )

        total_rows = (
            getattr(
                batch,
                "total_rows",
                0,
            )
            or 0
        )

        processed_rows = min(
            total_rows,
            imported_rows + error_rows,
        )

        progress_pct = (
            processed_rows
            / total_rows
            * 100
            if total_rows > 0
            else 0.0
        )

        elapsed = None
        remaining = None

        started_at = getattr(
            batch,
            "started_at",
            None,
        )

        if started_at:
            if started_at.tzinfo is None:
                started_at = (
                    started_at.replace(
                        tzinfo=timezone.utc
                    )
                )

            elapsed = (
                datetime.now(timezone.utc)
                - started_at
            ).total_seconds()

            if (
                0 < processed_rows < total_rows
                and elapsed > 0
            ):
                rate = (
                    processed_rows / elapsed
                )

                if rate > 0:
                    remaining = (
                        total_rows
                        - processed_rows
                    ) / rate

        try:
            if isinstance(
                batch.status,
                ImportStatus,
            ):
                status = ImportStatusEnum(
                    batch.status.value
                )
            else:
                status = ImportStatusEnum(
                    batch.status
                )

        except (ValueError, TypeError):
            status = (
                ImportStatusEnum.FAILED
            )

        return BatchProgressResponse(
            batch_id=batch.id,
            status=status,
            total_rows=total_rows,
            processed_rows=processed_rows,
            error_count=error_rows,
            progress_percent=round(
                progress_pct,
                2,
            ),
            elapsed_seconds=(
                round(elapsed, 2)
                if elapsed is not None
                else None
            ),
            estimated_remaining_seconds=(
                round(remaining, 2)
                if remaining is not None
                else None
            ),
        )

    # ==========================================================
    # Cancel
    # ==========================================================

    def cancel_import(
        self,
        batch_id: int,
    ) -> None:
        from app.models.import_batch import ImportBatch

        batch = (
            self.db.query(ImportBatch)
            .filter(
                ImportBatch.id == batch_id
            )
            .first()
        )

        if batch is None:
            raise FileProcessingError(
                f"Batch #{batch_id} not found."
            )

        terminal_states = {
            ImportStatus.COMPLETED,
            ImportStatus.COMPLETED_WITH_ERRORS,
            ImportStatus.FAILED,
        }

        if batch.status in terminal_states:
            raise FileProcessingError(
                f"Cannot cancel batch #{batch_id}: "
                f"already in terminal state "
                f"'{batch.status.value}'."
            )

        batch.status = STATUS_MAP[
            ImportStatusEnum.FAILED
        ]

        batch.completed_at = (
            datetime.now(timezone.utc)
        )

        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            logger.exception(
                "Failed to cancel batch %s.",
                batch_id,
            )
            raise FileProcessingError(
                f"Failed to cancel "
                f"batch #{batch_id}: {exc}"
            ) from exc

        self._batches.pop(
            batch_id,
            None,
        )

        progress = self._progress.get(
            batch_id
        )

        if progress is not None:
            progress.status = (
                ImportStatusEnum.FAILED
            )
            progress.current_phase = (
                "CANCELLED"
            )

    # ==========================================================
    # Helpers
    # ==========================================================

    @staticmethod
    def _clean_optional(
        value: Any,
    ) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value if value else None

        return value

    @staticmethod
    def _to_trace_value(
        value: Any,
    ) -> Any:
        """
        Convert values to JSON-safe representations for source_detail.
        """
        if value is None:
            return None

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value

        if isinstance(
            value,
            (
                datetime,
            ),
        ):
            return value.isoformat()

        try:
            return str(value)
        except Exception:
            return None

    # ==========================================================
    # AddressCandidate
    # ==========================================================

    def _persist_address_candidate(
        self,
        *,
        company_store_id: int,
        batch_id: int,
        row_number: int,
        mapped_row: dict[str, Any],
        province_name: str | None,
        city_name: str | None,
    ) -> None:
        """
        Persist raw address/location evidence for Matching.

        Important boundaries:
        - Does NOT create/update Master Store.
        - Does NOT perform Matching.
        - Does NOT set matched_store_id.
        - Does NOT invent missing addresses.
        - Retry of the same batch/row does not create a duplicate candidate.
        """

        from app.models.address_candidate import AddressCandidate

        address = self._clean_optional(
            mapped_row.get("address")
        )

        if address is None:
            logger.info(
                "AddressCandidate skipped: "
                "batch=%s row=%s "
                "company_store_id=%s reason=no_address",
                batch_id,
                row_number,
                company_store_id,
            )
            return

        address_text = str(
            address
        ).strip()

        if not address_text:
            logger.info(
                "AddressCandidate skipped: "
                "batch=%s row=%s "
                "company_store_id=%s reason=blank_address",
                batch_id,
                row_number,
                company_store_id,
            )
            return

        source_id = (
            f"import_batch:{batch_id}:row:{row_number}"
        )

        existing_candidate = (
            self.db.query(AddressCandidate)
            .filter(
                AddressCandidate.company_store_id
                == company_store_id,
                AddressCandidate.source_type
                == "excel",
                AddressCandidate.source_id
                == source_id,
            )
            .one_or_none()
        )

        raw_province = self._clean_optional(
            mapped_row.get("province_name")
        )

        raw_city = self._clean_optional(
            mapped_row.get("city_name")
        )

        resolved_province = (
            province_name
            if province_name is not None
            else (
                str(raw_province).strip()
                if raw_province is not None
                else None
            )
        )

        resolved_city = (
            city_name
            if city_name is not None
            else (
                str(raw_city).strip()
                if raw_city is not None
                else None
            )
        )

        latitude = self._clean_optional(
            mapped_row.get("latitude")
        )

        longitude = self._clean_optional(
            mapped_row.get("longitude")
        )

        postal_code = self._clean_optional(
            mapped_row.get("postal_code")
        )

        source_detail_payload = {
            "batch_id": batch_id,
            "row_number": row_number,
            "source": "store_excel_import",
        }

        source_detail = json.dumps(
            {
                key: self._to_trace_value(value)
                for key, value
                in source_detail_payload.items()
            },
            ensure_ascii=False,
        )

        if existing_candidate is None:
            candidate = AddressCandidate(
                store_id=None,
                company_store_id=company_store_id,
                address_text=address_text,
                province=resolved_province,
                city=resolved_city,
                postal_code=(
                    str(postal_code).strip()
                    if postal_code is not None
                    else None
                ),
                latitude=latitude,
                longitude=longitude,
                source_type="excel",
                source_id=source_id,
                source_detail=source_detail,
                match_found=False,
                matched_store_id=None,
                match_score=None,
                match_method=None,
                validation_provider=None,
                validation_score=None,
                normalized_address=None,
                normalized_latitude=None,
                normalized_longitude=None,
                fimap_token=None,
                is_processed=False,
                is_selected=False,
                processed_at=None,
            )

            self.db.add(candidate)
            self.db.flush()

            logger.info(
                "Created AddressCandidate: "
                "batch=%s row=%s "
                "company_store_id=%s candidate_id=%s",
                batch_id,
                row_number,
                company_store_id,
                candidate.id,
            )

            return

        # Same batch + same row retry:
        # refresh only raw evidence fields.
        existing_candidate.address_text = (
            address_text
        )
        existing_candidate.province = (
            resolved_province
        )
        existing_candidate.city = (
            resolved_city
        )
        existing_candidate.postal_code = (
            str(postal_code).strip()
            if postal_code is not None
            else None
        )
        existing_candidate.latitude = (
            latitude
        )
        existing_candidate.longitude = (
            longitude
        )
        existing_candidate.source_detail = (
            source_detail
        )

        self.db.flush()

        logger.info(
            "Reused AddressCandidate: "
            "batch=%s row=%s "
            "company_store_id=%s candidate_id=%s",
            batch_id,
            row_number,
            company_store_id,
            existing_candidate.id,
        )

    # ==========================================================
    # CompanyStore Persistence
    # ==========================================================

    def _persist_company_store(
        self,
        *,
        mapped_row: dict[str, Any],
        project_id: int,
        company_id: int,
        batch_id: int,
        row_number: int,
        province_name: str | None = None,
        city_name: str | None = None,
    ) -> None:
        from app.models.company_store import CompanyStore
        from app.models.project_company_store import (
            ProjectCompanyStore,
        )

        store_code_raw = self._clean_optional(
            mapped_row.get("store_code")
        )

        store_code = (
            str(store_code_raw).strip()
            if store_code_raw is not None
            else None
        )

        name_raw = self._clean_optional(
            mapped_row.get("name")
            or mapped_row.get("canonical_name")
        )

        if name_raw is None:
            raise FileProcessingError(
                "Valid STORE row "
                f"store_code={store_code!r} "
                "has no name."
            )

        name = str(
            name_raw
        ).strip()

        phone = self._clean_optional(
            mapped_row.get("phone")
            or mapped_row.get("canonical_phone")
        )

        raw_province = self._clean_optional(
            mapped_row.get("province_name")
        )

        raw_city = self._clean_optional(
            mapped_row.get("city_name")
        )

        resolved_province = (
            province_name
            if province_name is not None
            else (
                str(raw_province).strip()
                if raw_province is not None
                else None
            )
        )

        resolved_city = (
            city_name
            if city_name is not None
            else (
                str(raw_city).strip()
                if raw_city is not None
                else None
            )
        )

        company_store = None

        # Direct matching to Master Store by store_code
        # is intentionally NOT performed.
        #
        # store_code is only a company-scoped identifier.
        if store_code is not None:
            company_store = (
                self.db.query(CompanyStore)
                .filter(
                    CompanyStore.company_id
                    == company_id,
                    CompanyStore.store_code
                    == store_code,
                )
                .one_or_none()
            )

        mutable_values = {
            "name": name,
            "phone": phone,
            "address": self._clean_optional(
                mapped_row.get("address")
            ),
            "province": resolved_province,
            "city": resolved_city,
            "postal_code": self._clean_optional(
                mapped_row.get("postal_code")
            ),
            "latitude": self._clean_optional(
                mapped_row.get("latitude")
            ),
            "longitude": self._clean_optional(
                mapped_row.get("longitude")
            ),
        }

        if company_store is None:
            create_values = {
                key: value
                for key, value
                in mutable_values.items()
                if value is not None
            }

            company_store = CompanyStore(
                company_id=company_id,
                store_code=store_code,
                **create_values,
            )

            self.db.add(
                company_store
            )

            self.db.flush()

            logger.info(
                "Created CompanyStore: "
                "company_id=%s "
                "store_code=%s "
                "company_store_id=%s "
                "batch=%s row=%s",
                company_id,
                store_code,
                company_store.id,
                batch_id,
                row_number,
            )

        else:
            for (
                field_name,
                value,
            ) in mutable_values.items():
                if value is not None:
                    setattr(
                        company_store,
                        field_name,
                        value,
                    )

            self.db.flush()

        link = (
            self.db.query(
                ProjectCompanyStore
            )
            .filter(
                ProjectCompanyStore.project_id
                == project_id,
                ProjectCompanyStore.company_store_id
                == company_store.id,
            )
            .one_or_none()
        )

        if link is None:
            link = ProjectCompanyStore(
                project_id=project_id,
                company_store_id=company_store.id,
                is_active=True,
            )

            self.db.add(
                link
            )

            logger.info(
                "Created ProjectCompanyStore: "
                "project_id=%s "
                "company_store_id=%s "
                "batch=%s row=%s",
                project_id,
                company_store.id,
                batch_id,
                row_number,
            )

        else:
            link.is_active = True

            if hasattr(
                link,
                "removed_at",
            ):
                link.removed_at = None

        self.db.flush()

        # ------------------------------------------------------
        # Evidence creation
        # ------------------------------------------------------

        self._persist_address_candidate(
            company_store_id=company_store.id,
            batch_id=batch_id,
            row_number=row_number,
            mapped_row=mapped_row,
            province_name=resolved_province,
            city_name=resolved_city,
        )

    # ==========================================================
    # Generic Row Persistence
    # ==========================================================

    def _persist_row(
        self,
        entity_type: EntityTypeEnum,
        batch_id: int,
        row_number: int,
        mapped_row: dict[str, Any],
        province_id: int | None = None,
        city_id: int | None = None,
        province_name: str | None = None,
        city_name: str | None = None,
        project_id: int | None = None,
        company_id: int | None = None,
    ) -> None:
        if entity_type == EntityTypeEnum.STORE:
            if (
                project_id is None
                or company_id is None
            ):
                raise FileProcessingError(
                    "STORE persistence requires "
                    "project_id and company_id."
                )

            self._persist_company_store(
                mapped_row=mapped_row,
                project_id=project_id,
                company_id=company_id,
                batch_id=batch_id,
                row_number=row_number,
                province_name=province_name,
                city_name=city_name,
            )

            return

        from app.models.driver import Driver
        from app.models.gps_record import GPSRecord
        from app.models.order import Order
        from app.models.vehicle import Vehicle

        model_map: dict[
            EntityTypeEnum,
            type,
        ] = {
            EntityTypeEnum.ORDER: Order,
            EntityTypeEnum.FLEET: Vehicle,
            EntityTypeEnum.DRIVER: Driver,
            EntityTypeEnum.GPS: GPSRecord,
        }

        model_cls = model_map.get(
            entity_type
        )

        if model_cls is None:
            raise ValueError(
                "No model mapped for "
                f"entity type: {entity_type}"
            )

        values = dict(
            mapped_row
        )

        values["import_batch_id"] = (
            batch_id
        )

        for field_name in (
            "raw_data",
            "column_mapping",
        ):
            if field_name not in values:
                continue

            value = values[
                field_name
            ]

            if isinstance(
                value,
                str,
            ):
                try:
                    values[field_name] = (
                        json.loads(value)
                    )
                except (
                    json.JSONDecodeError,
                    TypeError,
                ):
                    values[
                        field_name
                    ] = None

        mapper = inspect(
            model_cls
        )

        model_fields = {
            column.key
            for column in mapper.columns
        }

        filtered_values = {
            key: value
            for key, value
            in values.items()
            if key in model_fields
        }

        if (
            "import_batch_id"
            in model_fields
        ):
            filtered_values[
                "import_batch_id"
            ] = batch_id

        instance = model_cls(
            **filtered_values
        )

        self.db.add(
            instance
        )

    # ==========================================================
    # Progress Helper
    # ==========================================================

    def _update_progress(
        self,
        batch_id: int,
        status: ImportStatusEnum,
        phase: str,
        processed: int,
        errors: int = 0,
    ) -> None:
        progress = self._progress.get(
            batch_id
        )

        if progress is None:
            return

        progress.status = status
        progress.current_phase = phase
        progress.processed_rows = min(
            processed,
            progress.total_rows,
        )
        progress.error_count = max(
            0,
            errors,
        )

        if progress.total_rows > 0:
            progress.progress_percent = round(
                progress.processed_rows
                / progress.total_rows
                * 100,
                2,
            )
        else:
            progress.progress_percent = (
                0.0
            )

    # ==========================================================
    # Mapping
    # ==========================================================

    @staticmethod
    def _suggest_mapping(
        headers: list[str],
        entity_type: EntityTypeEnum,
    ) -> dict[str, str]:
        aliases = FIELD_ALIASES.get(
            entity_type,
            {},
        )

        normalized_aliases: dict[
            str,
            set[str],
        ] = {
            field_name: {
                ImportService._normalize_header(
                    alias
                )
                for alias
                in field_alias_list
            }
            for (
                field_name,
                field_alias_list,
            ) in aliases.items()
        }

        suggested: dict[
            str,
            str,
        ] = {}

        for header in headers:
            if header is None:
                continue

            raw_header = str(
                header
            ).strip()

            if "|" not in raw_header:
                continue

            parts = [
                part.strip()
                for part
                in raw_header.split("|")
            ]

            for part in reversed(
                parts
            ):
                normalized_part = (
                    ImportService._normalize_header(
                        part
                    )
                )

                for field_name in aliases:
                    if (
                        normalized_part
                        == ImportService._normalize_header(
                            field_name
                        )
                    ):
                        suggested[
                            field_name
                        ] = header
                        break

                if any(
                    suggested.get(
                        field_name
                    ) == header
                    for field_name
                    in aliases
                ):
                    break

        for header in headers:
            normalized_header = (
                ImportService._normalize_header(
                    header
                )
            )

            if not normalized_header:
                continue

            candidates = [
                normalized_header
            ]

            if "|" in normalized_header:
                candidates.extend(
                    part.strip()
                    for part
                    in normalized_header.split("|")
                    if part.strip()
                )

            for (
                field_name,
                field_alias_set,
            ) in normalized_aliases.items():
                if field_name in suggested:
                    continue

                if any(
                    candidate
                    in field_alias_set
                    for candidate
                    in candidates
                ):
                    suggested[
                        field_name
                    ] = header

        return suggested

    @staticmethod
    def _normalize_column_mapping(
        mapping: dict[str, str],
        entity_type: EntityTypeEnum,
        headers: list[str],
    ) -> dict[str, str]:
        if not mapping:
            return {}

        valid_fields = set(
            FIELD_ALIASES.get(
                entity_type,
                {},
            ).keys()
        )

        header_set = set(
            headers
        )

        result: dict[
            str,
            str,
        ] = {}

        for key, value in mapping.items():
            if (
                key is None
                or value is None
            ):
                continue

            key_str = str(
                key
            ).strip()

            value_str = str(
                value
            ).strip()

            if key_str in valid_fields:
                if value_str in header_set:
                    result[
                        key_str
                    ] = value_str
                    continue

                for header in headers:
                    if (
                        ImportService._normalize_header(
                            header
                        )
                        == ImportService._normalize_header(
                            value_str
                        )
                    ):
                        result[
                            key_str
                        ] = header
                        break

                continue

            if value_str in valid_fields:
                if key_str in header_set:
                    result[
                        value_str
                    ] = key_str
                    continue

                for header in headers:
                    if (
                        ImportService._normalize_header(
                            header
                        )
                        == ImportService._normalize_header(
                            key_str
                        )
                    ):
                        result[
                            value_str
                        ] = header
                        break

        return result

    @staticmethod
    def _apply_mapping(
        row: dict[str, Any],
        mapping: dict[str, str],
        entity_type: EntityTypeEnum | None = None,
    ) -> dict[str, Any]:
        if not row:
            return {}

        if mapping:
            result: dict[
                str,
                Any,
            ] = {}

            for (
                canonical_field,
                source_header,
            ) in mapping.items():
                if source_header in row:
                    result[
                        canonical_field
                    ] = row.get(
                        source_header
                    )

            if entity_type is not None:
                valid_fields = set(
                    FIELD_ALIASES.get(
                        entity_type,
                        {},
                    ).keys()
                )

                for (
                    key,
                    value,
                ) in row.items():
                    if key in valid_fields:
                        result.setdefault(
                            key,
                            value,
                        )

            return result

        result: dict[
            str,
            Any,
        ] = {}

        aliases = (
            FIELD_ALIASES.get(
                entity_type,
                {},
            )
            if entity_type is not None
            else {}
        )

        for header, value in row.items():
            canonical_field = (
                ImportService._resolve_header_to_canonical(
                    header=header,
                    aliases=aliases,
                )
            )

            if canonical_field:
                result[
                    canonical_field
                ] = value

        return result

    @staticmethod
    def _resolve_header_to_canonical(
        header: Any,
        aliases: dict[str, list[str]],
    ) -> str | None:
        if header is None:
            return None

        raw_header = str(
            header
        ).strip()

        if not raw_header:
            return None

        normalized_header = (
            ImportService._normalize_header(
                raw_header
            )
        )

        for field_name in aliases:
            if (
                normalized_header
                == ImportService._normalize_header(
                    field_name
                )
            ):
                return field_name

        if "|" in raw_header:
            parts = [
                part.strip()
                for part
                in raw_header.split("|")
            ]

            for part in reversed(
                parts
            ):
                normalized_part = (
                    ImportService._normalize_header(
                        part
                    )
                )

                for field_name in aliases:
                    if (
                        normalized_part
                        == ImportService._normalize_header(
                            field_name
                        )
                    ):
                        return field_name

        for (
            field_name,
            field_aliases,
        ) in aliases.items():
            normalized_aliases = {
                ImportService._normalize_header(
                    alias
                )
                for alias
                in field_aliases
            }

            if (
                normalized_header
                in normalized_aliases
            ):
                return field_name

            if "|" in normalized_header:
                for part in (
                    normalized_header.split("|")
                ):
                    if (
                        part.strip()
                        in normalized_aliases
                    ):
                        return field_name

        return None

    @staticmethod
    def _normalize_header(
        value: Any,
    ) -> str:
        if value is None:
            return ""

        text_value = str(
            value
        ).strip().lower()

        text_value = text_value.replace(
            "ي",
            "ی",
        )

        text_value = text_value.replace(
            "ى",
            "ی",
        )

        text_value = text_value.replace(
            "ك",
            "ک",
        )

        text_value = text_value.replace(
            "\u200c",
            " ",
        )

        text_value = text_value.replace(
            "\u200f",
            "",
        )

        text_value = text_value.replace(
            "\u200e",
            "",
        )

        text_value = " ".join(
            text_value.split()
        )

        return text_value

    # ==========================================================
    # Failure
    # ==========================================================

    def _mark_batch_failed(
        self,
        batch: Any,
        batch_id: int,
        message: str,
    ) -> None:
        batch.status = STATUS_MAP[
            ImportStatusEnum.FAILED
        ]

        batch.completed_at = (
            datetime.now(timezone.utc)
        )

        if hasattr(
            batch,
            "error_note",
        ):
            batch.error_note = (
                message
            )

        try:
            self.db.commit()

        except Exception as exc:
            self.db.rollback()

            logger.exception(
                "Failed to mark batch %s "
                "as failed.",
                batch_id,
            )

            raise FileProcessingError(
                f"Failed to mark "
                f"batch #{batch_id} "
                f"as failed: {exc}"
            ) from exc

        progress = self._progress.get(
            batch_id
        )

        if progress is not None:
            progress.status = (
                ImportStatusEnum.FAILED
            )

            progress.current_phase = (
                "FAILED"
            )

            progress.error_count = max(
                progress.error_count,
                1,
            )
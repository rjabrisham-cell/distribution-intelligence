"""
Import Service — Orchestrator for the Data Import Engine.

Coordinates the full import lifecycle:
    1. File parsing (ExcelService)
    2. Column mapping & preview
    3. Validation (ValidationService)
    4. Batch creation and row-by-row persisting
    5. Progress tracking
    6. Post-import profiling (ProfilingService)

Takes a SQLAlchemy Session and coordinates repositories for persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import FileProcessingError
from app.schemas.import_schema import (
    BatchProgressResponse,
    EntityTypeEnum,
    ImportPreviewResponse,
    ImportProgressResponse,
    ImportStartRequest,
    ImportStartResponse,
    ImportStatusEnum,
    RowError,
    ValidationReport,
)
from app.services.excel_service import ExcelService
from app.services.validation_service import ValidationService
from app.services.profiling_service import ProfilingService


class ImportService:
    """
    Orchestrates the data import workflow.

    Usage:
        service = ImportService(db=session)
        result = service.start_import(request)
        progress = service.get_progress(batch_id=1)
    """

    # ── Configuration ──────────────────────────────────────────

    BATCH_SIZE: int = 500  # Rows per commit during bulk import

    # ── Constructor ────────────────────────────────────────────

    def __init__(self, db: Session) -> None:
        self.db = db
        self.excel_service = ExcelService()
        self.validation_service = ValidationService()
        self.profiling_service = ProfilingService()

        # ── In-memory batch tracking (replace with Redis/DB in production) ──
        self._batches: dict[int, dict[str, Any]] = {}
        self._progress: dict[int, ImportProgressResponse] = {}

    # ── Public API: Import Workflow ────────────────────────────

    def start_import(
        self, request: ImportStartRequest, file_path: str
    ) -> ImportStartResponse:
        """
        Initiate a new import batch.

        1. Create ImportBatch record
        2. Parse file to count rows
        3. Return batch_id for tracking
        """
        entity_type = request.entity_type
        file_id = request.file_id
        skip_validation = request.skip_validation

        # 1. Parse file to get row count
        try:
            parsed = self.excel_service.parse(file_path)
            total_rows = parsed["total_rows"]
            file_name = parsed["file_name"]
        except FileProcessingError as exc:
            raise FileProcessingError(
                f"Cannot start import: failed to parse file: {exc}"
            ) from exc

        if total_rows == 0:
            raise FileProcessingError("File contains no data rows.")

        # 2. Create ImportBatch in DB  (✅ مدل واقعی: app.models.import_batch)
        from app.models.import_batch import ImportBatch

        batch = ImportBatch(
            file_id=file_id,                                     # ✅ جایگزین file_name (که وجود ندارد)
            entity_type=entity_type.value,
            status=ImportStatusEnum.PENDING.value,
            total_rows=total_rows,
            column_mapping=request.column_mapping or {},
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)

        batch_id = batch.id

        # 3. Store batch context for async processing
        self._batches[batch_id] = {
            "batch": batch,
            "file_path": file_path,
            "column_mapping": request.column_mapping or {},
            "skip_validation": skip_validation,
            "entity_type": entity_type,
            "parsed": parsed,
            "created_at": datetime.now(timezone.utc),
        }

        # 4. Initialize progress tracker
        self._progress[batch_id] = ImportProgressResponse(
            batch_id=batch_id,
            entity_type=entity_type,
            status=ImportStatusEnum.PENDING,
            total_rows=total_rows,
            processed_rows=0,
            error_count=0,
            progress_percent=0.0,
            current_phase="PENDING",
            started_at=batch.updated_at,
        )

        return ImportStartResponse(
            batch_id=batch_id,
            entity_type=entity_type,
            file_name=file_name,
            total_rows=total_rows,
            status=ImportStatusEnum.PENDING,
            message=(
                f"Import batch #{batch_id} created with {total_rows} rows. "
                "Processing will begin shortly."
            ),
        )

    def preview_import(
        self,
        file_path: str,
        entity_type: EntityTypeEnum,
    ) -> ImportPreviewResponse:
        """
        Generate a preview of file contents before starting import.

        Returns headers, sample rows, and suggested column mapping.
        """
        preview = self.excel_service.preview(file_path, sample_size=10)

        # Suggest mapping based on header name similarity to schema fields
        suggested = self._suggest_mapping(preview["headers"], entity_type)

        return ImportPreviewResponse(
            file_name=preview["file_name"],
            entity_type=entity_type,
            total_rows=preview["total_rows"],
            headers=preview["headers"],
            sample_rows=preview["sample_rows"],
            suggested_mapping=suggested,
        )

    def process_batch(self, batch_id: int) -> ImportProgressResponse:
        """
        Execute the full import pipeline for a batch:

        1. Validation phase
        2. Import phase (row-by-row persistence)
        3. Update batch status
        """
        ctx = self._batches.get(batch_id)
        if ctx is None:
            raise FileProcessingError(f"Batch #{batch_id} not found.")

        batch = ctx["batch"]
        parsed = ctx["parsed"]
        entity_type = ctx["entity_type"]
        column_mapping = ctx["column_mapping"]
        skip_validation = ctx["skip_validation"]

        rows = parsed["rows"]
        total = len(rows)

        # ── Phase 1: Validation ──
        self._update_progress(batch_id, ImportStatusEnum.VALIDATING, "VALIDATING", 0)

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
                validated_at=datetime.now(timezone.utc),
            )
        else:
            validation_report = self.validation_service.validate(
                entity_type=entity_type,
                rows=rows,
                column_mapping=column_mapping,
                strict_geography=False,
            )

        # Persist validation errors to batch record
        batch.status = ImportStatusEnum.VALIDATED.value
        batch.valid_rows = validation_report.valid_rows            # ✅
        batch.error_rows = validation_report.error_rows            # ✅ error_count → error_rows
        self.db.commit()

        self._update_progress(
            batch_id,
            ImportStatusEnum.VALIDATED,
            "VALIDATED" if validation_report.is_valid else "VALIDATED_WITH_ERRORS",
            processed=0,
            errors=validation_report.error_rows,
        )

        # If there are errors and user didn't skip, we can stop here
        # (Business decision: continue even with errors, just skip bad rows)
        if not validation_report.is_valid and not skip_validation:
            # Mark rows with errors for skipping during import
            error_row_numbers = {
                err.row_number
                for err in validation_report.errors
                if err.severity == "ERROR"
            }
        else:
            error_row_numbers: set[int] = set()

        # ── Phase 2: Import ──
        self._update_progress(batch_id, ImportStatusEnum.IMPORTING, "IMPORTING", 0)

        imported = 0
        errors_during_import = 0
        valid_rows = [
            (idx, row)
            for idx, row in enumerate(rows, start=1)
            if idx not in error_row_numbers
        ]

        # Map source rows to schema fields
        mapped_rows = []
        for idx, raw_row in valid_rows:
            mapped = self._apply_mapping(raw_row, column_mapping)
            mapped_rows.append((idx, mapped))

        # Batch-insert in chunks
        for chunk_start in range(0, len(mapped_rows), self.BATCH_SIZE):
            chunk = mapped_rows[chunk_start : chunk_start + self.BATCH_SIZE]

            for idx, mapped_row in chunk:
                try:
                    self._persist_row(entity_type, batch_id, mapped_row)
                    imported += 1
                except Exception as exc:
                    errors_during_import += 1
                    # Log error but continue
                    print(f"[ImportService] Row {idx} failed: {exc}")

            self.db.commit()

            # Update progress
            processed_so_far = chunk_start + len(chunk)
            self._update_progress(
                batch_id,
                ImportStatusEnum.IMPORTING,
                "IMPORTING",
                processed=imported,
                errors=errors_during_import,
            )

        # ── Phase 3: Finalize ──
        final_status = ImportStatusEnum.COMPLETED
        if errors_during_import > 0 and imported > 0:
            final_status = ImportStatusEnum.PARTIAL
        elif imported == 0:
            final_status = ImportStatusEnum.FAILED

        batch.status = final_status.value
        batch.imported_rows = imported                                           # ✅ processed_rows → imported_rows
        batch.error_rows = validation_report.error_rows + errors_during_import   # ✅ error_count → error_rows
        batch.completed_at = datetime.now(timezone.utc)
        self.db.commit()

        self._update_progress(
            batch_id,
            final_status,
            "DONE",
            processed=imported,
            errors=batch.error_rows,                                             # ✅
        )

        return self._progress[batch_id]

    def get_progress(self, batch_id: int) -> ImportProgressResponse:
        """
        Retrieve current progress of an import batch.
        """
        progress = self._progress.get(batch_id)
        if progress is None:
            raise FileProcessingError(f"No progress found for batch #{batch_id}.")

        # Calculate elapsed/remaining
        if progress.started_at:
            elapsed = (datetime.now(timezone.utc) - progress.started_at).total_seconds()
            progress.elapsed_seconds = elapsed

            if progress.processed_rows > 0 and progress.progress_percent > 0:
                total_estimated = elapsed / (progress.progress_percent / 100)
                progress.estimated_remaining_seconds = max(0, total_estimated - elapsed)

        return progress

    def get_batch_progress(self, batch_id: int) -> BatchProgressResponse:
        """
        Lightweight batch progress suitable for polling.
        """
        from app.models.import_batch import ImportBatch                     # ✅ مسیر تصحیح شد

        batch = self.db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()

        if batch is None:
            raise FileProcessingError(f"Batch #{batch_id} not found.")

        # ✅ تمام processed_rows → imported_rows
        progress_pct = (
            (batch.imported_rows / batch.total_rows * 100)
            if batch.total_rows > 0
            else 0.0
        )

        elapsed = None
        remaining = None
        if batch.started_at:
            elapsed = (datetime.now(timezone.utc) - batch.started_at).total_seconds()
            if 0 < batch.imported_rows < batch.total_rows:
                rate = elapsed / batch.imported_rows
                remaining = rate * (batch.total_rows - batch.imported_rows)

        return BatchProgressResponse(
            batch_id=batch.id,
            status=ImportStatusEnum(batch.status),
            total_rows=batch.total_rows,
            processed_rows=batch.imported_rows,           # ✅
            error_count=batch.error_rows,                 # ✅
            progress_percent=round(progress_pct, 2),
            elapsed_seconds=round(elapsed, 2) if elapsed else None,
            estimated_remaining_seconds=round(remaining, 2) if remaining else None,
        )

    def cancel_import(self, batch_id: int) -> None:
        """
        Cancel an in-progress import batch.
        """
        from app.models.import_batch import ImportBatch                     # ✅ مسیر تصحیح شد

        batch = self.db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()

        if batch is None:
            raise FileProcessingError(f"Batch #{batch_id} not found.")

        if batch.status in (
            ImportStatusEnum.COMPLETED.value,
            ImportStatusEnum.FAILED.value,
        ):
            raise FileProcessingError(
                f"Cannot cancel batch #{batch_id}: "
                f"already in terminal state '{batch.status}'."
            )

        batch.status = ImportStatusEnum.FAILED.value
        batch.completed_at = datetime.now(timezone.utc)
        self.db.commit()

        # Clean up tracking
        self._batches.pop(batch_id, None)
        if batch_id in self._progress:
            self._progress[batch_id].status = ImportStatusEnum.FAILED
            self._progress[batch_id].current_phase = "CANCELLED"

    # ── Private: persistence ───────────────────────────────────

    def _persist_row(
        self,
        entity_type: EntityTypeEnum,
        batch_id: int,
        mapped_row: dict[str, Any],
    ) -> None:
        """
        Persist a single row to the appropriate table.

        ✅ هر مدل از فایل جداگانهٔ خودش import می‌شود،
           نه از import_models (که وجود ندارد).
        """
        from app.models.driver import Driver
        from app.models.gps_record import GPSRecord
        from app.models.order import Order
        from app.models.store import Store
        from app.models.vehicle import Vehicle

        model_map: dict[EntityTypeEnum, type] = {
            EntityTypeEnum.STORE: Store,
            EntityTypeEnum.ORDER: Order,
            EntityTypeEnum.FLEET: Vehicle,
            EntityTypeEnum.DRIVER: Driver,
            EntityTypeEnum.GPS: GPSRecord,
        }

        model_cls = model_map.get(entity_type)
        if model_cls is None:
            raise ValueError(f"No model mapped for entity type: {entity_type}")

        # Inject batch_id
        mapped_row["import_batch_id"] = batch_id

        # Handle JSON fields
        for field_name in ("raw_data", "column_mapping"):
            if field_name in mapped_row and isinstance(mapped_row[field_name], str):
                import json

                try:
                    mapped_row[field_name] = json.loads(mapped_row[field_name])
                except (json.JSONDecodeError, TypeError):
                    mapped_row[field_name] = None

        instance = model_cls(**mapped_row)
        self.db.add(instance)

    # ── Private: helpers ───────────────────────────────────────

    def _update_progress(
        self,
        batch_id: int,
        status: ImportStatusEnum,
        phase: str,
        processed: int,
        errors: int = 0,
    ) -> None:
        """Update internal progress tracker."""
        progress = self._progress.get(batch_id)
        if progress is None:
            return

        progress.status = status
        progress.current_phase = phase
        progress.processed_rows = processed
        progress.error_count = errors

        if progress.total_rows > 0:
            progress.progress_percent = round(
                (processed / progress.total_rows) * 100, 2
            )

    @staticmethod
    def _suggest_mapping(
        headers: list[str],
        entity_type: EntityTypeEnum,
    ) -> dict[str, str]:
        """
        Suggest column mapping based on header name similarity.

        Compares file headers against known field names for the entity type
        (Persian + English aliases).
        """
        FIELD_ALIASES: dict[EntityTypeEnum, dict[str, list[str]]] = {
            EntityTypeEnum.STORE: {
                "code": ["code", "کد", "کد فروشگاه", "store code", "store_code"],
                "name": ["name", "نام", "نام فروشگاه", "store name", "store_name"],
                "phone": ["phone", "تلفن", "شماره", "mobile", "موبایل"],
                "address": ["address", "آدرس", "نشانی"],
                "latitude": ["latitude", "lat", "عرض جغرافیایی", "موقعیت"],
                "longitude": ["longitude", "lon", "lng", "long", "طول جغرافیایی"],
                "category": ["category", "دسته", "نوع", "گروه"],
                "priority": ["priority", "اولویت"],
            },
            EntityTypeEnum.ORDER: {
                "order_code": ["order_code", "کد سفارش", "شماره سفارش", "order id"],
                "store_code": ["store_code", "کد فروشگاه", "store code"],
                "store_name": ["store_name", "نام فروشگاه", "store name"],
                "delivery_date": ["delivery_date", "تاریخ تحویل"],
                "address": ["address", "آدرس", "نشانی"],
                "weight_kg": ["weight_kg", "وزن", "weight"],
                "volume_m3": ["volume_m3", "حجم", "volume"],
                "item_count": ["item_count", "تعداد", "count", "quantity"],
            },
            EntityTypeEnum.FLEET: {
                "plate": ["plate", "پلاک", "شماره پلاک", "license plate"],
                "vehicle_type": ["vehicle_type", "نوع خودرو", "type"],
                "model": ["model", "مدل", "خودرو"],
                "capacity_kg": ["capacity_kg", "ظرفیت", "capacity"],
                "cost_per_km": ["cost_per_km", "هزینه هر کیلومتر", "cost"],
            },
            EntityTypeEnum.DRIVER: {
                "driver_code": ["driver_code", "کد راننده", "driver code"],
                "first_name": ["first_name", "نام"],
                "last_name": ["last_name", "نام خانوادگی"],
                "national_code": ["national_code", "کد ملی"],
                "phone": ["phone", "تلفن", "موبایل", "mobile"],
            },
            EntityTypeEnum.GPS: {
                "vehicle_plate": ["vehicle_plate", "پلاک", "plate"],
                "latitude": ["latitude", "lat", "عرض جغرافیایی"],
                "longitude": ["longitude", "lon", "lng", "long", "طول جغرافیایی"],
                "timestamp": ["timestamp", "زمان", "time", "تاریخ"],
                "speed_kmh": ["speed_kmh", "سرعت", "speed"],
            },
        }

        entity_aliases = FIELD_ALIASES.get(entity_type, {})

        suggested: dict[str, str] = {}

        for header in headers:
            header_lower = header.lower().strip()
            for field_name, aliases in entity_aliases.items():
                if header_lower in [a.lower() for a in aliases]:
                    suggested[field_name] = header
                    break

        return suggested

    @staticmethod
    def _apply_mapping(
        row: dict[str, Any],
        mapping: dict[str, str],
    ) -> dict[str, Any]:
        """Apply column mapping: {schema_field: file_header} → {schema_field: value}."""
        if not mapping:
            return row

        return {
            schema_field: row.get(file_header)
            for schema_field, file_header in mapping.items()
            if file_header in row
        }

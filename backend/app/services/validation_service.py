"""
Validation Service for Data Import Engine.

Applies configurable validation rules to imported rows before
they are persisted. Returns detailed error reports.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

import pandas as pd

from app.schemas.import_schema import EntityTypeEnum, RowError, ValidationReport

logger = logging.getLogger(__name__)


# ── Reusable Validators ─────────────────────────────────────────────

@dataclass
class FieldRule:
    """A single validation rule for a column mapping."""
    field_name: str                # target model field name
    column_name: str               # column name in source file
    required: bool = False
    data_type: str = "str"         # str, int, float, decimal, date, datetime
    min_value: float | Decimal | None = None
    max_value: float | Decimal | None = None
    max_length: int | None = None
    pattern: str | None = None     # regex (not implemented here; extend as needed)
    allowed_values: list[str] | None = None

    def validate(self, raw_value: Any) -> str | None:
        """Return error message if invalid, else None."""
        if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
            if self.required:
                return "مقدار اجباری است (خالی)"
            return None  # optional + empty = ok

        value_str = str(raw_value).strip()

        # ── Length check ──
        if self.max_length is not None and len(value_str) > self.max_length:
            return f"طول مقدار ({len(value_str)}) بیشتر از حد مجاز ({self.max_length}) است"

        # ── Type checks ──
        if self.data_type == "int":
            try:
                val = int(value_str)
            except ValueError:
                return f"مقدار '{value_str}' عدد صحیح معتبر نیست"
            if self.min_value is not None and val < self.min_value:
                return f"مقدار باید ≥ {self.min_value} باشد"
            if self.max_value is not None and val > self.max_value:
                return f"مقدار باید ≤ {self.max_value} باشد"

        elif self.data_type == "float":
            try:
                val = float(value_str)
            except ValueError:
                return f"مقدار '{value_str}' عدد اعشاری معتبر نیست"
            if self.min_value is not None and val < self.min_value:
                return f"مقدار باید ≥ {self.min_value} باشد"
            if self.max_value is not None and val > self.max_value:
                return f"مقدار باید ≤ {self.max_value} باشد"

        elif self.data_type == "decimal":
            try:
                Decimal(value_str)
            except InvalidOperation:
                return f"مقدار '{value_str}' decimal معتبر نیست"

        elif self.data_type in ("date", "datetime"):
            try:
                pd.to_datetime(value_str)
            except (ValueError, pd.errors.OutOfBoundsDatetime):
                return f"مقدار '{value_str}' تاریخ/زمان معتبر نیست"

        # ── Allowed values ──
        if self.allowed_values and value_str not in self.allowed_values:
            return f"مقدار باید یکی از {self.allowed_values} باشد"

        return None  # passed


# ── Rule Registry per Entity Type ───────────────────────────────────

def get_rules_for_entity(entity_type: EntityTypeEnum) -> list[FieldRule]:
    """Return validation rules for a given entity type.

    Rules match the required fields in import_schema Create models.
    """

    common = {
        EntityTypeEnum.STORE: [
            FieldRule("code", "code", required=True, max_length=50),
            FieldRule("name", "name", max_length=200),
            FieldRule("phone", "phone", max_length=50),
            FieldRule("address", "address", max_length=2000),
            FieldRule("latitude", "latitude", data_type="decimal", min_value=Decimal("-90"), max_value=Decimal("90")),
            FieldRule("longitude", "longitude", data_type="decimal", min_value=Decimal("-180"), max_value=Decimal("180")),
            FieldRule("category", "category", max_length=50),
            FieldRule("priority", "priority", data_type="int", min_value=0),
            FieldRule("status", "status", max_length=30),
            FieldRule("service_time_min", "service_time_min", data_type="int", min_value=0),
        ],
        EntityTypeEnum.ORDER: [
            FieldRule("order_code", "order_code", required=True, max_length=200),
            FieldRule("store_code", "store_code", required=True, max_length=50),
            FieldRule("store_name", "store_name", max_length=200),
            FieldRule("delivery_date", "delivery_date", data_type="date"),
            FieldRule("delivery_time_from", "delivery_time_from", data_type="datetime"),
            FieldRule("delivery_time_to", "delivery_time_to", data_type="datetime"),
            FieldRule("address", "address", max_length=2000),
            FieldRule("latitude", "latitude", data_type="decimal", min_value=Decimal("-90"), max_value=Decimal("90")),
            FieldRule("longitude", "longitude", data_type="decimal", min_value=Decimal("-180"), max_value=Decimal("180")),
            FieldRule("weight_kg", "weight_kg", data_type="float", min_value=0),
            FieldRule("volume_m3", "volume_m3", data_type="float", min_value=0),
            FieldRule("item_count", "item_count", data_type="int", min_value=0),
            FieldRule("special_instructions", "special_instructions", max_length=2000),
            FieldRule("status", "status", max_length=30),
        ],
        EntityTypeEnum.FLEET: [
            FieldRule("plate", "plate", required=True, max_length=20),
            FieldRule("vehicle_type", "vehicle_type", max_length=50),
            FieldRule("model", "model", max_length=100),
            FieldRule("capacity_kg", "capacity_kg", data_type="float", min_value=0),
            FieldRule("volume_m3", "volume_m3", data_type="float", min_value=0),
            FieldRule("cost_per_km", "cost_per_km", data_type="decimal", min_value=Decimal("0")),
            FieldRule("fixed_cost", "fixed_cost", data_type="decimal", min_value=Decimal("0")),
            FieldRule("latitude", "latitude", data_type="decimal", min_value=Decimal("-90"), max_value=Decimal("90")),
            FieldRule("longitude", "longitude", data_type="decimal", min_value=Decimal("-180"), max_value=Decimal("180")),
            FieldRule("available_from", "available_from", data_type="datetime"),
            FieldRule("available_until", "available_until", data_type="datetime"),
            FieldRule("status", "status", max_length=30),
        ],
        EntityTypeEnum.DRIVER: [
            FieldRule("driver_code", "driver_code", required=True, max_length=50),
            FieldRule("first_name", "first_name", max_length=100),
            FieldRule("last_name", "last_name", max_length=100),
            FieldRule("national_code", "national_code", max_length=20),
            FieldRule("phone", "phone", max_length=50),
            FieldRule("license_number", "license_number", max_length=50),
            FieldRule("license_expiry", "license_expiry", data_type="date"),
            FieldRule("latitude", "latitude", data_type="decimal", min_value=Decimal("-90"), max_value=Decimal("90")),
            FieldRule("longitude", "longitude", data_type="decimal", min_value=Decimal("-180"), max_value=Decimal("180")),
            FieldRule("status", "status", max_length=30),
        ],
        EntityTypeEnum.GPS: [
            FieldRule("vehicle_plate", "vehicle_plate", required=True, max_length=50),
            FieldRule("latitude", "latitude", required=True, data_type="decimal", min_value=Decimal("-90"), max_value=Decimal("90")),
            FieldRule("longitude", "longitude", required=True, data_type="decimal", min_value=Decimal("-180"), max_value=Decimal("180")),
            FieldRule("timestamp", "timestamp", required=True, data_type="datetime"),
            FieldRule("speed_kmh", "speed_kmh", data_type="float", min_value=0),
            FieldRule("heading", "heading", data_type="float", min_value=0, max_value=360),
            FieldRule("accuracy_m", "accuracy_m", data_type="float", min_value=0),
        ],
    }

    return common.get(entity_type, [])


# ── Validation Service ──────────────────────────────────────────────

class ValidationService:
    """
    Applies validation rules to a DataFrame and produces a ValidationReport.

    Usage:
        service = ValidationService()
        report = service.validate(dataframe, EntityTypeEnum.ORDER, column_mapping)
    """

    def validate(
        self,
        df: pd.DataFrame,
        entity_type: EntityTypeEnum,
        column_mapping: dict[str, str],
    ) -> ValidationReport:
        """
        Validate all rows.

        Args:
            df: DataFrame where each row is a record to validate.
            entity_type: Type of entity to validate against.
            column_mapping: Dict mapping source column names → model field names.

        Returns:
            ValidationReport with detailed errors per row.
        """
        rules = get_rules_for_entity(entity_type)
        # Build a lookup: field_name → FieldRule
        rule_by_field: dict[str, FieldRule] = {r.field_name: r for r in rules}
        # Reverse mapping: model_field → source_column
        # column_mapping is source_col → model_field; we invert for validation
        inv_mapping: dict[str, str] = {v: k for k, v in column_mapping.items()}

        errors: list[RowError] = []
        total_rows = len(df)
        valid_rows = 0
        error_rows = 0
        warning_rows = 0

        for idx, (_, row) in enumerate(df.iterrows()):
            row_number = idx + 1  # 1-based for user display
            row_errors: list[RowError] = []

            for field_name, rule in rule_by_field.items():
                source_col = inv_mapping.get(field_name)
                raw_value = row.get(source_col) if source_col else None
                err = rule.validate(raw_value)
                if err:
                    row_errors.append(RowError(
                        row_number=row_number,
                        column_name=source_col or field_name,
                        raw_value=str(raw_value) if raw_value is not None else None,
                        error_message=err,
                        severity="ERROR",
                    ))

            if row_errors:
                error_rows += 1
                errors.extend(row_errors)
            else:
                valid_rows += 1

        is_valid = error_rows == 0

        logger.info(
            "Validation complete: entity=%s, rows=%d, valid=%d, errors=%d, is_valid=%s",
            entity_type.value, total_rows, valid_rows, error_rows, is_valid,
        )

        return ValidationReport(
            batch_id=0,  # will be set by caller
            entity_type=entity_type,
            total_rows=total_rows,
            valid_rows=valid_rows,
            error_rows=error_rows,
            warning_rows=warning_rows,
            errors=errors,
            is_valid=is_valid,
            validated_at=datetime.utcnow(),
        )

    def validate_single_row(
        self,
        row: dict[str, Any],
        entity_type: EntityTypeEnum,
        column_mapping: dict[str, str],
        row_number: int = 1,
    ) -> list[RowError]:
        """Validate a single row dict. Used for streaming/one-by-one import."""
        # Convert single row to tiny DataFrame
        df = pd.DataFrame([row])
        report = self.validate(df, entity_type, column_mapping)
        # Update row numbers
        for e in report.errors:
            e.row_number = row_number
        return report.errors

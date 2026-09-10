"""
Validation Service for Data Import Engine.

Validates canonical imported rows before persistence.

STORE uses an accept-with-evidence model:
- data quality issues are reported as WARNINGs,
- WARNINGs do not block persistence,
- blocking ERROR behavior is preserved for other entity types.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

from app.schemas.import_schema import EntityTypeEnum, RowError, ValidationReport

logger = logging.getLogger(__name__)


# ============================================================================
# Helpers
# ============================================================================


def _normalize_key(value: Any) -> str:
    return re.sub(r"[\s\-]+", "_", str(value).strip().lower())


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_empty(value: Any) -> bool:
    if value is None:
        return True

    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass

    if isinstance(value, str):
        return value.strip() == ""

    return False


# ============================================================================
# Field Rule
# ============================================================================


@dataclass
class FieldRule:
    field_name: str
    column_name: str
    required: bool = False
    data_type: str = "str"
    min_value: float | Decimal | None = None
    max_value: float | Decimal | None = None
    max_length: int | None = None
    pattern: str | None = None
    allowed_values: list[str] | None = None
    severity: str = "ERROR"

    def validate(self, raw_value: Any) -> str | None:
        if _is_empty(raw_value):
            if self.required:
                return "مقدار مورد انتظار خالی است"
            return None

        value_str = _clean_text(raw_value)

        if self.max_length is not None and len(value_str) > self.max_length:
            return (
                f"طول مقدار ({len(value_str)}) بیشتر از حد مجاز "
                f"({self.max_length}) است"
            )

        if self.data_type == "int":
            try:
                if isinstance(raw_value, float) and not raw_value.is_integer():
                    raise ValueError
                val = int(value_str)
            except (ValueError, TypeError):
                return f"مقدار '{value_str}' عدد صحیح معتبر نیست"

            if self.min_value is not None and val < self.min_value:
                return f"مقدار باید ≥ {self.min_value} باشد"

            if self.max_value is not None and val > self.max_value:
                return f"مقدار باید ≤ {self.max_value} باشد"

        elif self.data_type == "float":
            try:
                val = float(value_str)
            except (ValueError, TypeError):
                return f"مقدار '{value_str}' عدد اعشاری معتبر نیست"

            if self.min_value is not None and val < self.min_value:
                return f"مقدار باید ≥ {self.min_value} باشد"

            if self.max_value is not None and val > self.max_value:
                return f"مقدار باید ≤ {self.max_value} باشد"

        elif self.data_type == "decimal":
            try:
                val = Decimal(value_str)
            except (InvalidOperation, ValueError, TypeError):
                return f"مقدار '{value_str}' عدد decimal معتبر نیست"

            if self.min_value is not None and val < Decimal(str(self.min_value)):
                return f"مقدار باید ≥ {self.min_value} باشد"

            if self.max_value is not None and val > Decimal(str(self.max_value)):
                return f"مقدار باید ≤ {self.max_value} باشد"

        elif self.data_type in ("date", "datetime"):
            try:
                parsed = pd.to_datetime(value_str, errors="raise")
                if pd.isna(parsed):
                    raise ValueError
            except (
                ValueError,
                TypeError,
                pd.errors.OutOfBoundsDatetime,
            ):
                return f"مقدار '{value_str}' تاریخ/زمان معتبر نیست"

        if self.pattern:
            try:
                if not re.fullmatch(self.pattern, value_str):
                    return f"فرمت مقدار '{value_str}' معتبر نیست"
            except re.error:
                logger.warning(
                    "Invalid validation regex for field '%s': %s",
                    self.field_name,
                    self.pattern,
                )

        if self.allowed_values:
            normalized_allowed = {
                str(value).strip().lower()
                for value in self.allowed_values
            }
            if value_str.lower() not in normalized_allowed:
                return f"مقدار باید یکی از {self.allowed_values} باشد"

        return None


# ============================================================================
# Entity Validation Rules
# ============================================================================


def _phone_like_pattern() -> str:
    return r"^(?:\+98|0)?9\d{9}$|^(?:\+98|0)?[1-8]\d{9,10}$"


def _store_phone_like_pattern() -> str:
    """
    Permissive STORE intake pattern.

    Normalization belongs to ImportService. Therefore STORE intake accepts
    plausible raw numeric phone values such as:

        77269422
        02177269422
        9123456789
        09123456789
        +989123456789

    Missing values and format issues are evidence, not persistence blockers.
    """
    return r"^\+?\d{7,15}$"


def _postal_code_pattern() -> str:
    return r"^\d{10}$"


def get_rules_for_entity(entity_type: EntityTypeEnum) -> list[FieldRule]:
    rules: dict[EntityTypeEnum, list[FieldRule]] = {

        # ====================================================================
        # STORE — Frozen Intake Contract / Accept-with-Evidence
        #
        # Persistence policy:
        #   STORE quality gaps do NOT reject the row.
        #
        # Expected fields (missing => WARNING):
        #   canonical_name
        #   canonical_phone
        #   address
        #   latitude
        #   longitude
        #
        # Optional fields:
        #   store_code
        #   manager_name
        #   mobile
        #
        # store_code may be NULL.
        # Phone/mobile normalization is performed by ImportService.
        # Missing/invalid quality evidence is carried forward to Audit/Readiness.
        # ====================================================================

        EntityTypeEnum.STORE: [
            FieldRule(
                "store_code",
                "store_code",
                required=False,
                max_length=128,
                severity="WARNING",
            ),
            FieldRule(
                "canonical_name",
                "canonical_name",
                required=True,
                max_length=200,
                severity="WARNING",
            ),
            FieldRule(
                "canonical_phone",
                "canonical_phone",
                required=True,
                max_length=50,
                pattern=_store_phone_like_pattern(),
                severity="WARNING",
            ),
            FieldRule(
                "address",
                "address",
                required=True,
                max_length=2000,
                severity="WARNING",
            ),
            FieldRule(
                "latitude",
                "latitude",
                required=True,
                data_type="decimal",
                min_value=Decimal("-90"),
                max_value=Decimal("90"),
                severity="WARNING",
            ),
            FieldRule(
                "longitude",
                "longitude",
                required=True,
                data_type="decimal",
                min_value=Decimal("-180"),
                max_value=Decimal("180"),
                severity="WARNING",
            ),
            FieldRule(
                "manager_name",
                "manager_name",
                required=False,
                max_length=200,
                severity="WARNING",
            ),
            FieldRule(
                "mobile",
                "mobile",
                required=False,
                max_length=50,
                pattern=_store_phone_like_pattern(),
                severity="WARNING",
            ),
        ],

        # ====================================================================
        # ORDER
        # ====================================================================

        EntityTypeEnum.ORDER: [
            FieldRule(
                "order_code",
                "order_code",
                required=True,
                max_length=200,
            ),
            FieldRule(
                "store_code",
                "store_code",
                required=True,
                max_length=50,
            ),
            FieldRule(
                "store_name",
                "store_name",
                max_length=200,
            ),
            FieldRule(
                "delivery_date",
                "delivery_date",
                data_type="date",
            ),
            FieldRule(
                "delivery_time_from",
                "delivery_time_from",
                data_type="datetime",
            ),
            FieldRule(
                "delivery_time_to",
                "delivery_time_to",
                data_type="datetime",
            ),
            FieldRule(
                "address",
                "address",
                max_length=2000,
            ),
            FieldRule(
                "latitude",
                "latitude",
                data_type="decimal",
                min_value=Decimal("-90"),
                max_value=Decimal("90"),
            ),
            FieldRule(
                "longitude",
                "longitude",
                data_type="decimal",
                min_value=Decimal("-180"),
                max_value=Decimal("180"),
            ),
            FieldRule(
                "weight_kg",
                "weight_kg",
                data_type="float",
                min_value=0,
            ),
            FieldRule(
                "volume_m3",
                "volume_m3",
                data_type="float",
                min_value=0,
            ),
            FieldRule(
                "item_count",
                "item_count",
                data_type="int",
                min_value=0,
            ),
            FieldRule(
                "special_instructions",
                "special_instructions",
                max_length=2000,
            ),
            FieldRule(
                "status",
                "status",
                max_length=30,
            ),
        ],

        # ====================================================================
        # FLEET
        # ====================================================================

        EntityTypeEnum.FLEET: [
            FieldRule(
                "plate",
                "plate",
                required=True,
                max_length=20,
            ),
            FieldRule(
                "vehicle_type",
                "vehicle_type",
                max_length=50,
            ),
            FieldRule(
                "model",
                "model",
                max_length=100,
            ),
            FieldRule(
                "capacity_kg",
                "capacity_kg",
                data_type="float",
                min_value=0,
            ),
            FieldRule(
                "volume_m3",
                "volume_m3",
                data_type="float",
                min_value=0,
            ),
            FieldRule(
                "cost_per_km",
                "cost_per_km",
                data_type="decimal",
                min_value=Decimal("0"),
            ),
            FieldRule(
                "fixed_cost",
                "fixed_cost",
                data_type="decimal",
                min_value=Decimal("0"),
            ),
            FieldRule(
                "latitude",
                "latitude",
                data_type="decimal",
                min_value=Decimal("-90"),
                max_value=Decimal("90"),
            ),
            FieldRule(
                "longitude",
                "longitude",
                data_type="decimal",
                min_value=Decimal("-180"),
                max_value=Decimal("180"),
            ),
            FieldRule(
                "available_from",
                "available_from",
                data_type="datetime",
            ),
            FieldRule(
                "available_until",
                "available_until",
                data_type="datetime",
            ),
            FieldRule(
                "status",
                "status",
                max_length=30,
            ),
        ],

        # ====================================================================
        # DRIVER
        # ====================================================================

        EntityTypeEnum.DRIVER: [
            FieldRule(
                "driver_code",
                "driver_code",
                required=True,
                max_length=50,
            ),
            FieldRule(
                "first_name",
                "first_name",
                max_length=100,
            ),
            FieldRule(
                "last_name",
                "last_name",
                max_length=100,
            ),
            FieldRule(
                "national_code",
                "national_code",
                max_length=20,
            ),
            FieldRule(
                "phone",
                "phone",
                max_length=50,
                pattern=_phone_like_pattern(),
            ),
            FieldRule(
                "license_number",
                "license_number",
                max_length=50,
            ),
            FieldRule(
                "license_expiry",
                "license_expiry",
                data_type="date",
            ),
            FieldRule(
                "latitude",
                "latitude",
                data_type="decimal",
                min_value=Decimal("-90"),
                max_value=Decimal("90"),
            ),
            FieldRule(
                "longitude",
                "longitude",
                data_type="decimal",
                min_value=Decimal("-180"),
                max_value=Decimal("180"),
            ),
            FieldRule(
                "status",
                "status",
                max_length=30,
            ),
        ],

        # ====================================================================
        # GPS
        # ====================================================================

        EntityTypeEnum.GPS: [
            FieldRule(
                "vehicle_plate",
                "vehicle_plate",
                required=True,
                max_length=50,
            ),
            FieldRule(
                "latitude",
                "latitude",
                required=True,
                data_type="decimal",
                min_value=Decimal("-90"),
                max_value=Decimal("90"),
            ),
            FieldRule(
                "longitude",
                "longitude",
                required=True,
                data_type="decimal",
                min_value=Decimal("-180"),
                max_value=Decimal("180"),
            ),
            FieldRule(
                "timestamp",
                "timestamp",
                required=True,
                data_type="datetime",
            ),
            FieldRule(
                "speed_kmh",
                "speed_kmh",
                data_type="float",
                min_value=0,
            ),
            FieldRule(
                "heading",
                "heading",
                data_type="float",
                min_value=0,
                max_value=360,
            ),
            FieldRule(
                "accuracy_m",
                "accuracy_m",
                data_type="float",
                min_value=0,
            ),
        ],
    }

    return rules.get(entity_type, [])


# ============================================================================
# Validation Service
# ============================================================================


class ValidationService:
    """
    Validates canonical rows.

    ImportService is responsible for converting source headers into
    canonical field names before calling this service.

    STORE uses accept-with-evidence semantics:
    WARNINGs are reported but do not make a STORE row invalid.
    """

    # Current STORE Intake contract.
    #
    # Deliberately excludes legacy Intake fields such as:
    # shop_type, postal_code, plaque, unit and floor.
    #
    # canonical_phone deliberately does NOT use "mobile" as an alias.
    # Store phone and manager mobile are separate fields.

    STORE_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
        "store_code": (
            "store_code",
            "code",
        ),
        "canonical_name": (
            "canonical_name",
            "name",
            "shop_name",
            "store_name",
        ),
        "canonical_phone": (
            "canonical_phone",
            "phone",
            "telephone",
            "tel",
        ),
        "address": (
            "address",
        ),
        "latitude": (
            "latitude",
            "lat",
        ),
        "longitude": (
            "longitude",
            "long",
            "lng",
            "lon",
        ),
        "manager_name": (
            "manager_name",
            "manager",
        ),
        "mobile": (
            "mobile",
        ),
    }

    def validate(
        self,
        rows: list[dict[str, Any]],
        entity_type: EntityTypeEnum,
        column_mapping: dict[str, str] | None = None,
        strict_geography: bool = False,
        batch_id: int = 0,
    ) -> ValidationReport:
        rules = get_rules_for_entity(entity_type)

        rule_by_field = {
            rule.field_name: rule
            for rule in rules
        }

        total_rows = len(rows)
        valid_rows = 0
        error_rows = 0
        warning_rows = 0
        errors: list[RowError] = []

        for row_number, row in enumerate(rows, start=1):
            row_issues: list[RowError] = []

            for field_name, rule in rule_by_field.items():
                raw_value = self._get_field_value(
                    row=row,
                    field_name=field_name,
                    column_mapping=column_mapping,
                    entity_type=entity_type,
                )

                error_message = rule.validate(raw_value)

                if error_message:
                    row_issues.append(
                        RowError(
                            row_number=row_number,
                            column_name=field_name,
                            raw_value=self._stringify_value(raw_value),
                            error_message=error_message,
                            severity=rule.severity,
                        )
                    )

            if strict_geography:
                geo_issues = self._validate_geography(
                    row=row,
                    mapping=column_mapping,
                    row_number=row_number,
                    entity_type=entity_type,
                )
                row_issues.extend(geo_issues)

            has_error = any(
                str(issue.severity).upper() == "ERROR"
                for issue in row_issues
            )

            has_warning = any(
                str(issue.severity).upper() == "WARNING"
                for issue in row_issues
            )

            if has_error:
                error_rows += 1
            else:
                valid_rows += 1

            if has_warning:
                warning_rows += 1

            errors.extend(row_issues)

        is_valid = error_rows == 0

        logger.info(
            "Validation complete: "
            "entity=%s rows=%d valid=%d error_rows=%d "
            "warnings=%d is_valid=%s",
            entity_type.value,
            total_rows,
            valid_rows,
            error_rows,
            warning_rows,
            is_valid,
        )

        return ValidationReport(
            batch_id=batch_id,
            entity_type=entity_type,
            total_rows=total_rows,
            valid_rows=valid_rows,
            error_rows=error_rows,
            warning_rows=warning_rows,
            errors=errors,
            is_valid=is_valid,
            validated_at=datetime.now(timezone.utc),
        )

    def validate_single_row(
        self,
        row: dict[str, Any],
        entity_type: EntityTypeEnum,
        column_mapping: dict[str, str] | None = None,
        row_number: int = 1,
        strict_geography: bool = False,
    ) -> list[RowError]:
        report = self.validate(
            rows=[row],
            entity_type=entity_type,
            column_mapping=column_mapping,
            strict_geography=strict_geography,
            batch_id=0,
        )

        for error in report.errors:
            error.row_number = row_number

        return report.errors

    def _get_field_value(
        self,
        row: dict[str, Any],
        field_name: str,
        column_mapping: dict[str, str] | None,
        entity_type: EntityTypeEnum,
    ) -> Any:
        if field_name in row:
            return row.get(field_name)

        if entity_type == EntityTypeEnum.STORE:
            aliases = self.STORE_FIELD_ALIASES.get(
                field_name,
                (),
            )

            for alias in aliases:
                if alias in row:
                    return row.get(alias)

            normalized_aliases = {
                _normalize_key(alias)
                for alias in aliases
            }

            for key, value in row.items():
                if _normalize_key(key) in normalized_aliases:
                    return value

        if column_mapping:
            mapped_source_keys = [
                source_key
                for source_key, target_key in column_mapping.items()
                if target_key == field_name
            ]

            for source_key in mapped_source_keys:
                if source_key in row:
                    return row.get(source_key)

                normalized_source_key = _normalize_key(
                    source_key
                )

                for key, value in row.items():
                    if (
                        _normalize_key(key)
                        == normalized_source_key
                    ):
                        return value

        normalized_field_name = _normalize_key(
            field_name
        )

        for key, value in row.items():
            if (
                _normalize_key(key)
                == normalized_field_name
            ):
                return value

        return None

    @staticmethod
    def _validate_geography(
        row: dict[str, Any],
        mapping: dict[str, str] | None,
        row_number: int,
        entity_type: EntityTypeEnum,
    ) -> list[RowError]:
        del mapping

        issues: list[RowError] = []

        severity = (
            "WARNING"
            if entity_type == EntityTypeEnum.STORE
            else "ERROR"
        )

        latitude_raw = ValidationService._get_geography_value(
            row=row,
            primary_key="latitude",
            aliases=(
                "latitude",
                "lat",
            ),
        )

        longitude_raw = ValidationService._get_geography_value(
            row=row,
            primary_key="longitude",
            aliases=(
                "longitude",
                "long",
                "lng",
                "lon",
            ),
        )

        latitude = ValidationService._to_decimal(
            latitude_raw
        )

        longitude = ValidationService._to_decimal(
            longitude_raw
        )

        if latitude is None or longitude is None:
            return issues

        if (
            latitude < Decimal("-90")
            or latitude > Decimal("90")
        ):
            issues.append(
                RowError(
                    row_number=row_number,
                    column_name="latitude",
                    raw_value=ValidationService._stringify_value(
                        latitude_raw
                    ),
                    error_message=(
                        "عرض جغرافیایی باید بین -90 و 90 باشد"
                    ),
                    severity=severity,
                )
            )

        if (
            longitude < Decimal("-180")
            or longitude > Decimal("180")
        ):
            issues.append(
                RowError(
                    row_number=row_number,
                    column_name="longitude",
                    raw_value=ValidationService._stringify_value(
                        longitude_raw
                    ),
                    error_message=(
                        "طول جغرافیایی باید بین -180 و 180 باشد"
                    ),
                    severity=severity,
                )
            )

        if (
            latitude == Decimal("0")
            and longitude == Decimal("0")
        ):
            issues.append(
                RowError(
                    row_number=row_number,
                    column_name="latitude",
                    raw_value="0,0",
                    error_message=(
                        "مختصات (0,0) برای موقعیت عملیاتی معتبر نیست"
                    ),
                    severity=severity,
                )
            )

        return issues

    @staticmethod
    def _get_geography_value(
        row: dict[str, Any],
        primary_key: str,
        aliases: tuple[str, ...],
    ) -> Any:
        if primary_key in row:
            return row.get(primary_key)

        for alias in aliases:
            if alias in row:
                return row.get(alias)

        normalized_aliases = {
            _normalize_key(alias)
            for alias in aliases
        }

        for key, value in row.items():
            if _normalize_key(key) in normalized_aliases:
                return value

        return None

    @staticmethod
    def _to_decimal(
        value: Any,
    ) -> Decimal | None:
        if _is_empty(value):
            return None

        value_str = _clean_text(value)
        value_str = value_str.replace("،", ",")
        value_str = value_str.replace(",", "")

        try:
            return Decimal(value_str)
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ):
            return None

    @staticmethod
    def _stringify_value(
        value: Any,
    ) -> str | None:
        if _is_empty(value):
            return None

        return str(value)
"""
Pydantic schemas for Data Import Engine API.

Covers all six entities (ImportBatch, Store, Order, Vehicle, Driver, GPSRecord)
plus import workflow request/response models.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════

class EntityTypeEnum(str, Enum):
    """نوع موجودیت برای Import Batch."""
    ORDER = "ORDER"
    FLEET = "FLEET"
    DRIVER = "DRIVER"
    STORE = "STORE"
    GPS = "GPS"


class ImportStatusEnum(str, Enum):
    """وضعیت پردازش Import Batch."""
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    IMPORTING = "IMPORTING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


# ═══════════════════════════════════════════════════════════════
# ImportBatch Schemas
# ═══════════════════════════════════════════════════════════════

class ImportBatchCreate(BaseModel):
    """درخواست ایجاد یک Import Batch جدید."""
    entity_type: EntityTypeEnum = Field(..., description="نوع موجودیت (ORDER, STORE, ...)")
    file_name: str = Field(..., min_length=1, max_length=500, description="نام فایل منبع")
    total_rows: int = Field(..., ge=0, description="تعداد کل ردیف‌های فایل")
    column_mapping: dict[str, str] | None = Field(
        default=None, description="نگاشت ستون‌های فایل به فیلدهای مدل"
    )


class ImportBatchResponse(BaseModel):
    """پاسخ شامل اطلاعات یک Import Batch."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: EntityTypeEnum
    file_name: str
    status: ImportStatusEnum
    total_rows: int
    processed_rows: int = 0
    error_count: int = 0
    column_mapping: dict[str, str] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    progress_percent: float = 0.0
    success_rate: float = 100.0
    has_errors: bool = False
    is_finished: bool = False


class ImportBatchListResponse(BaseModel):
    """پاسخ لیست Import Batch‌ها."""
    items: list[ImportBatchResponse]
    total: int
    page: int = 1
    page_size: int = 20


class BatchProgressResponse(BaseModel):
    """پاسخ وضعیت پیشرفت یک Batch."""
    batch_id: int
    status: ImportStatusEnum
    total_rows: int
    processed_rows: int
    error_count: int
    progress_percent: float
    elapsed_seconds: float | None = None
    estimated_remaining_seconds: float | None = None


# ═══════════════════════════════════════════════════════════════
# Store Schemas
# ═══════════════════════════════════════════════════════════════

class StoreCreate(BaseModel):
    """یک رکورد فروشگاه برای import."""
    code: str = Field(..., min_length=1, max_length=50)
    name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = Field(default=None, max_length=2000)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_decimal_places=7)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_decimal_places=7)
    category: str | None = Field(default=None, max_length=50)
    priority: int = Field(default=0, ge=0)
    status: str = Field(default="active", max_length=30)
    service_time_min: int | None = Field(default=None, ge=0)
    error_note: str | None = Field(default=None, max_length=1000)
    raw_data: dict[str, Any] | None = None


class StoreResponse(BaseModel):
    """پاسخ شامل اطلاعات یک فروشگاه."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    import_batch_id: int
    code: str
    name: str | None = None
    phone: str | None = None
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    category: str | None = None
    priority: int = 0
    status: str = "active"
    service_time_min: int | None = None
    error_note: str | None = None
    created_at: datetime
    updated_at: datetime

    has_coordinates: bool = False
    is_geocoded: bool = False
    is_vip: bool = False
    is_active: bool = True


class StoreListResponse(BaseModel):
    """پاسخ لیست فروشگاه‌ها."""
    items: list[StoreResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ═══════════════════════════════════════════════════════════════
# Order Schemas
# ═══════════════════════════════════════════════════════════════

class OrderCreate(BaseModel):
    """یک رکورد سفارش برای import."""
    order_code: str = Field(..., min_length=1, max_length=200)
    store_code: str = Field(..., min_length=1, max_length=50)
    store_name: str | None = Field(default=None, max_length=200)
    delivery_date: datetime | None = None
    delivery_time_from: datetime | None = None
    delivery_time_to: datetime | None = None
    address: str | None = Field(default=None, max_length=2000)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_decimal_places=7)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_decimal_places=7)
    weight_kg: float | None = Field(default=None, ge=0)
    volume_m3: float | None = Field(default=None, ge=0)
    item_count: int | None = Field(default=None, ge=0)
    special_instructions: str | None = Field(default=None, max_length=2000)
    status: str = Field(default="NEW", max_length=30)
    error_note: str | None = Field(default=None, max_length=1000)
    raw_data: dict[str, Any] | None = None


class OrderResponse(BaseModel):
    """پاسخ شامل اطلاعات یک سفارش."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    import_batch_id: int
    order_code: str
    store_code: str
    store_name: str | None = None
    delivery_date: datetime | None = None
    delivery_time_from: datetime | None = None
    delivery_time_to: datetime | None = None
    address: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    weight_kg: float | None = None
    volume_m3: float | None = None
    item_count: int | None = None
    special_instructions: str | None = None
    status: str = "NEW"
    error_note: str | None = None
    created_at: datetime
    updated_at: datetime

    has_coordinates: bool = False
    is_geocoded: bool = False


class OrderListResponse(BaseModel):
    """پاسخ لیست سفارش‌ها."""
    items: list[OrderResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ═══════════════════════════════════════════════════════════════
# Vehicle Schemas
# ═══════════════════════════════════════════════════════════════

class VehicleCreate(BaseModel):
    """یک رکورد وسیله نقلیه برای import."""
    plate: str = Field(..., min_length=1, max_length=20)
    vehicle_type: str | None = Field(default=None, max_length=50)
    model: str | None = Field(default=None, max_length=100)
    capacity_kg: float | None = Field(default=None, ge=0)
    volume_m3: float | None = Field(default=None, ge=0)
    cost_per_km: Decimal | None = Field(default=None, ge=0, max_decimal_places=2)
    fixed_cost: Decimal | None = Field(default=None, ge=0, max_decimal_places=2)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_decimal_places=7)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_decimal_places=7)
    available_from: datetime | None = None
    available_until: datetime | None = None
    status: str = Field(default="active", max_length=30)
    error_note: str | None = Field(default=None, max_length=1000)
    raw_data: dict[str, Any] | None = None


class VehicleResponse(BaseModel):
    """پاسخ شامل اطلاعات یک وسیله نقلیه."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    import_batch_id: int
    plate: str
    vehicle_type: str | None = None
    model: str | None = None
    capacity_kg: float | None = None
    volume_m3: float | None = None
    cost_per_km: Decimal | None = None
    fixed_cost: Decimal | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    available_from: datetime | None = None
    available_until: datetime | None = None
    status: str = "active"
    error_note: str | None = None
    created_at: datetime
    updated_at: datetime

    has_capacity: bool = False
    has_coordinates: bool = False
    is_available_now: bool = False


class VehicleListResponse(BaseModel):
    """پاسخ لیست وسایل نقلیه."""
    items: list[VehicleResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ═══════════════════════════════════════════════════════════════
# Driver Schemas
# ═══════════════════════════════════════════════════════════════

class DriverCreate(BaseModel):
    """یک رکورد راننده برای import."""
    driver_code: str = Field(..., min_length=1, max_length=50)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    national_code: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=50)
    license_number: str | None = Field(default=None, max_length=50)
    license_expiry: datetime | None = None
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_decimal_places=7)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_decimal_places=7)
    status: str = Field(default="active", max_length=30)
    error_note: str | None = Field(default=None, max_length=1000)
    raw_data: dict[str, Any] | None = None


class DriverResponse(BaseModel):
    """پاسخ شامل اطلاعات یک راننده."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    import_batch_id: int
    driver_code: str
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    national_code: str | None = None
    phone: str | None = None
    license_number: str | None = None
    license_expiry: datetime | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    status: str = "active"
    error_note: str | None = None
    created_at: datetime
    updated_at: datetime

    is_active: bool = True
    has_start_coordinates: bool = False


class DriverListResponse(BaseModel):
    """پاسخ لیست راننده‌ها."""
    items: list[DriverResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ═══════════════════════════════════════════════════════════════
# GPSRecord Schemas
# ═══════════════════════════════════════════════════════════════

class GPSRecordCreate(BaseModel):
    """یک رکورد GPS برای import."""
    vehicle_plate: str = Field(..., min_length=1, max_length=50)
    latitude: Decimal = Field(..., ge=-90, le=90, max_decimal_places=7)
    longitude: Decimal = Field(..., ge=-180, le=180, max_decimal_places=7)
    timestamp: datetime
    speed_kmh: float | None = Field(default=None, ge=0)
    heading: float | None = Field(default=None, ge=0, le=360)
    accuracy_m: float | None = Field(default=None, ge=0)
    error_note: str | None = Field(default=None, max_length=1000)
    raw_data: dict[str, Any] | None = None


class GPSRecordResponse(BaseModel):
    """پاسخ شامل اطلاعات یک رکورد GPS."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    import_batch_id: int
    vehicle_plate: str
    latitude: Decimal
    longitude: Decimal
    timestamp: datetime
    speed_kmh: float | None = None
    heading: float | None = None
    accuracy_m: float | None = None
    error_note: str | None = None
    created_at: datetime

    is_high_accuracy: bool = False
    is_moving: bool = False


class GPSRecordListResponse(BaseModel):
    """پاسخ لیست رکوردهای GPS."""
    items: list[GPSRecordResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ═══════════════════════════════════════════════════════════════
# Import Workflow Schemas
# ═══════════════════════════════════════════════════════════════

class ImportStartRequest(BaseModel):
    """درخواست شروع فرایند import برای یک فایل."""
    entity_type: EntityTypeEnum = Field(..., description="نوع موجودیت فایل")
    file_id: int = Field(..., ge=1, description="شناسه فایل آپلودشده")
    column_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="نگاشت ستون‌های فایل به فیلدهای مدل",
    )
    skip_validation: bool = Field(
        default=False,
        description="عبور از اعتبارسنجی و import مستقیم",
    )


class ImportStartResponse(BaseModel):
    """پاسخ شروع فرایند import."""
    batch_id: int
    entity_type: EntityTypeEnum
    file_name: str
    total_rows: int
    status: ImportStatusEnum = ImportStatusEnum.PENDING
    message: str = "Import batch created successfully. Processing will begin shortly."


class ColumnMappingRequest(BaseModel):
    """درخواست به‌روزرسانی نگاشت ستون‌ها."""
    column_mapping: dict[str, str] = Field(..., description="نگاشت جدید ستون‌ها")


class RowError(BaseModel):
    """یک خطای اعتبارسنجی برای یک ردیف خاص."""
    row_number: int = Field(..., ge=1)
    column_name: str | None = None
    raw_value: str | None = None
    error_message: str
    severity: str = "ERROR"  # ERROR, WARNING


class ValidationReport(BaseModel):
    """گزارش کامل اعتبارسنجی یک فایل."""
    batch_id: int
    entity_type: EntityTypeEnum
    total_rows: int
    valid_rows: int = 0
    error_rows: int = 0
    warning_rows: int = 0
    errors: list[RowError] = Field(default_factory=list)
    is_valid: bool = False  # True اگر error_rows == 0
    validated_at: datetime | None = None


class ImportPreviewResponse(BaseModel):
    """پیش‌نمایش محتوای فایل قبل از import."""
    file_name: str
    entity_type: EntityTypeEnum
    total_rows: int
    headers: list[str] = Field(default_factory=list)
    sample_rows: list[dict[str, Any]] = Field(
        default_factory=list,
        description="تا ۱۰ ردیف نمونه از فایل",
    )
    suggested_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="نگاشت پیشنهادی بر اساس تشابه نام ستون‌ها",
    )


class ImportProgressResponse(BaseModel):
    """پاسخ وضعیت لحظه‌ای پردازش import."""
    batch_id: int
    entity_type: EntityTypeEnum
    status: ImportStatusEnum
    total_rows: int
    processed_rows: int
    error_count: int
    progress_percent: float
    current_phase: str = "IDLE"  # IDLE, VALIDATING, IMPORTING, DONE
    started_at: datetime | None = None
    elapsed_seconds: float | None = None
    estimated_remaining_seconds: float | None = None

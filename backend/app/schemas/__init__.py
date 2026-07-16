"""
Schemas package — aggregates all Pydantic schemas for API request/response.

Import order: import_schema first (Data Import Engine), then future modules.
"""

from .import_schema import (
    # ── Enums ──
    EntityTypeEnum,
    ImportStatusEnum,
    # ── Batch ──
    ImportBatchCreate,
    ImportBatchResponse,
    ImportBatchListResponse,
    BatchProgressResponse,
    # ── Store ──
    StoreCreate,
    StoreResponse,
    StoreListResponse,
    # ── Order ──
    OrderCreate,
    OrderResponse,
    OrderListResponse,
    # ── Vehicle ──
    VehicleCreate,
    VehicleResponse,
    VehicleListResponse,
    # ── Driver ──
    DriverCreate,
    DriverResponse,
    DriverListResponse,
    # ── GPS ──
    GPSRecordCreate,
    GPSRecordResponse,
    GPSRecordListResponse,
    # ── Import Workflow ──
    ImportStartRequest,
    ImportStartResponse,
    ImportPreviewResponse,
    ColumnMappingRequest,
    RowError,
    ValidationReport,
    ImportProgressResponse,
)

__all__ = [
    # ── Enums ──
    "EntityTypeEnum",
    "ImportStatusEnum",
    # ── Batch ──
    "ImportBatchCreate",
    "ImportBatchResponse",
    "ImportBatchListResponse",
    "BatchProgressResponse",
    # ── Store ──
    "StoreCreate",
    "StoreResponse",
    "StoreListResponse",
    # ── Order ──
    "OrderCreate",
    "OrderResponse",
    "OrderListResponse",
    # ── Vehicle ──
    "VehicleCreate",
    "VehicleResponse",
    "VehicleListResponse",
    # ── Driver ──
    "DriverCreate",
    "DriverResponse",
    "DriverListResponse",
    # ── GPS ──
    "GPSRecordCreate",
    "GPSRecordResponse",
    "GPSRecordListResponse",
    # ── Import Workflow ──
    "ImportStartRequest",
    "ImportStartResponse",
    "ImportPreviewResponse",
    "ColumnMappingRequest",
    "RowError",
    "ValidationReport",
    "ImportProgressResponse",
]

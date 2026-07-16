"""
Models package — aggregates all SQLAlchemy ORM models.

Import order follows DDD dependency: Base → Core → DataImport → Request.
"""

# ── Base ────────────────────────────────────────────────────
from .base import Base, BaseModel

# ── Core Business ───────────────────────────────────────────
from .account import Account
from .company import Company
from .project import Project, ProjectStatus
from .file import File

# ── Data Import Engine ──────────────────────────────────────
from .import_batch import EntityType, ImportBatch, ImportStatus
from .driver import Driver
from .gps_record import GPSRecord
from .order import Order
from .store import Store
from .vehicle import Vehicle

# ── Request System ──────────────────────────────────────────
from .request import Request
from .request_file import FileType, RequestFile

# ── Public API ──────────────────────────────────────────────
__all__ = [
    "Account",
    "Base",
    "BaseModel",
    "Company",
    "Driver",
    "EntityType",
    "File",
    "FileType",
    "GPSRecord",
    "ImportBatch",
    "ImportStatus",
    "Order",
    "Project",
    "ProjectStatus",
    "Request",
    "RequestFile",
    "Store",
    "Vehicle",
]

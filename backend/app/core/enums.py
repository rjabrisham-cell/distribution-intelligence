"""
DIP Sprint 2
Central Enum Definitions

Data Readiness Platform Contract v1.3

Purpose:
- Import supermarket/store data
- Validate data quality
- Geo reference preparation
- Prepare dataset for Distribution Engine

Do not remove existing values.
Future modules may use them.
"""

import enum


# ==================================================
# Match Status
# ==================================================

class MatchStatus(str, enum.Enum):
    PENDING = "pending"
    PRECISE = "precise"
    MATCHED = "matched"
    SUGGESTED = "suggested"
    UNMATCHED = "unmatched"
    LOCATED = "located"
    UNRESOLVED = "unresolved"


# ==================================================
# Location Confidence
# ==================================================

class LocationConfidence(str, enum.Enum):
    EXACT = "EXACT"
    DISTRICT = "DISTRICT"
    CITY = "CITY"
    UNKNOWN = "UNKNOWN"


# ==================================================
# Coordinate Source
# Technical lineage
# ==================================================

class CoordinateSource(str, enum.Enum):
    GPS = "GPS"
    MANUAL = "MANUAL"
    GEOCODE = "GEOCODE"
    REPOSITORY = "REPOSITORY"
    IMPORTED = "IMPORTED"
    UNKNOWN = "UNKNOWN"


# ==================================================
# Location Source
# Business lineage
# ==================================================

class LocationSource(str, enum.Enum):
    GPS = "GPS"
    NORMALIZER = "NORMALIZER"
    MANUAL = "MANUAL"
    IMPORT = "IMPORT"
    MASTER = "MASTER"


# ==================================================
# Repository Status
# ==================================================

class RepositoryStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    MERGED = "MERGED"
    ARCHIVED = "ARCHIVED"
    DUPLICATE = "DUPLICATE"


# ==================================================
# Store Status
# ==================================================

class StoreStatus(str, enum.Enum):
    ENABLE = "enable"
    DISABLE = "disable"


# ==================================================
# Match Log Action
# ==================================================

class MatchAction(str, enum.Enum):
    AUTO_MATCHED = "auto_matched"
    SUGGESTED = "suggested"
    NEW_MASTER = "new_master"
    UNMATCHED = "unmatched"
    MANUAL_MATCH = "manual_match"
    MANUAL_UNMATCH = "manual_unmatch"


# ==================================================
# Import Batch Status
# ==================================================

class ImportStatus(str, enum.Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


# ==================================================
# Import Entity Type
# ==================================================

class EntityType(str, enum.Enum):
    """
    Type of imported dataset.

    MVP:
        STORE

    Future:
        ORDER
        FLEET
        DRIVER
        GPS
    """

    STORE = "store"

    ORDER = "order"
    FLEET = "fleet"
    DRIVER = "driver"
    GPS = "gps"


# ==================================================
# Data Quality Status
# ==================================================

class DataQualityStatus(str, enum.Enum):
    """
    General validation result.
    """

    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


# ==================================================
# Geo Validation Status
# ==================================================

class GeoStatus(str, enum.Enum):
    """
    Geographic readiness state.
    """

    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    MISSING = "missing"


# ==================================================
# Duplicate Status
# ==================================================

class DuplicateStatus(str, enum.Enum):
    """
    Duplicate detection result.
    """

    UNIQUE = "unique"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    DUPLICATE = "duplicate"
    UNKNOWN = "unknown"


# ==================================================
# Readiness Status
# ==================================================

class ReadinessStatus(str, enum.Enum):
    """
    Dataset readiness for next engine.
    """

    NOT_READY = "not_ready"
    READY_WITH_WARNING = "ready_with_warning"
    READY = "ready"
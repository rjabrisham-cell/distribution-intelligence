"""
DIP Sprint 2
Central Enum Definitions
Database Contract v1.2 (Frozen)

DO NOT MODIFY
Changes require Database Contract v1.3
"""

import enum


# --------------------------------------------------
# Match Status
# --------------------------------------------------

class MatchStatus(str, enum.Enum):
    PENDING = "pending"
    PRECISE = "precise"
    MATCHED = "matched"
    SUGGESTED = "suggested"
    UNMATCHED = "unmatched"
    LOCATED = "located"
    UNRESOLVED = "unresolved"


# --------------------------------------------------
# Location Confidence
# --------------------------------------------------

class LocationConfidence(str, enum.Enum):
    EXACT = "EXACT"
    DISTRICT = "DISTRICT"
    CITY = "CITY"
    UNKNOWN = "UNKNOWN"


# --------------------------------------------------
# Coordinate Source (Technical Lineage)
# --------------------------------------------------

class CoordinateSource(str, enum.Enum):
    GPS = "GPS"
    MANUAL = "MANUAL"
    GEOCODE = "GEOCODE"
    REPOSITORY = "REPOSITORY"
    IMPORTED = "IMPORTED"
    UNKNOWN = "UNKNOWN"


# --------------------------------------------------
# Location Source (Business Lineage)
# --------------------------------------------------

class LocationSource(str, enum.Enum):
    GPS = "GPS"
    NORMALIZER = "NORMALIZER"
    MANUAL = "MANUAL"
    IMPORT = "IMPORT"
    MASTER = "MASTER"


# --------------------------------------------------
# Repository Status
# --------------------------------------------------

class RepositoryStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    MERGED = "MERGED"
    ARCHIVED = "ARCHIVED"
    DUPLICATE = "DUPLICATE"


# --------------------------------------------------
# Store Status
# --------------------------------------------------

class StoreStatus(str, enum.Enum):
    ENABLE = "enable"
    DISABLE = "disable"


# --------------------------------------------------
# Match Log Action
# --------------------------------------------------

class MatchAction(str, enum.Enum):
    AUTO_MATCHED = "auto_matched"
    SUGGESTED = "suggested"
    NEW_MASTER = "new_master"
    UNMATCHED = "unmatched"
    MANUAL_MATCH = "manual_match"
    MANUAL_UNMATCH = "manual_unmatch"


# --------------------------------------------------
# Import Batch Status
# --------------------------------------------------

class ImportStatus(str, enum.Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
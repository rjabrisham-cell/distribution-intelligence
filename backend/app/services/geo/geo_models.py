"""
geo_models.py — Domain Models & DTOs
====================================
Contract v1.2 (Frozen)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Optional


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class CapabilityLevel(Enum):
    NONE   = auto()
    BASIC  = auto()
    FULL   = auto()
    EXPERT = auto()


class Severity(Enum):
    INFO     = auto()
    WARNING  = auto()
    ERROR    = auto()
    CRITICAL = auto()
    HARD     = auto()   # ← Hard stop (fails validation)


class RuleCategory(Enum):
    COVERAGE        = auto()
    ACCURACY        = auto()
    COMPLETENESS    = auto()
    CONSISTENCY     = auto()
    PROVIDER_CHECKS = auto()
    BUSINESS_RULES  = auto()


class GeoValidationStatus(Enum):
    VALID      = "valid"
    INVALID    = "invalid"
    SUSPICIOUS = "suspicious"
    UNCERTAIN  = "uncertain"


# ═══════════════════════════════════════════════════════════
# Value Objects
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GeoCoordinate:
    latitude:  float
    longitude: float


@dataclass
class GeoAddress:
    province:      Optional[str] = None
    city:          Optional[str] = None
    district:      Optional[str] = None
    neighbourhood: Optional[str] = None
    street:        Optional[str] = None
    alley:         Optional[str] = None
    building_name: Optional[str] = None
    postal_code:   Optional[str] = None
    full_address:  Optional[str] = None


# ═══════════════════════════════════════════════════════════
# Capability Models
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CapabilityInfo:
    level:   CapabilityLevel = CapabilityLevel.NONE
    accuracy: float = 0.0          # 0.0 … 1.0
    coverage: str   = "none"       # e.g. "iran", "tehran"
    notes:    str   = ""


@dataclass(frozen=True)
class GeoProviderCapability:
    city_validation:     CapabilityInfo = field(default_factory=CapabilityInfo)
    street_validation:   CapabilityInfo = field(default_factory=CapabilityInfo)
    postal_code:         CapabilityInfo = field(default_factory=CapabilityInfo)
    reverse_geocode:     CapabilityInfo = field(default_factory=CapabilityInfo)
    coordinate_check:    CapabilityInfo = field(default_factory=CapabilityInfo)


# ═══════════════════════════════════════════════════════════
# Validation Results
# ═══════════════════════════════════════════════════════════

@dataclass
class FieldValidationResult:
    field_name:  str
    exists:      bool   = False
    confidence:  float  = 0.0
    value:       Optional[str] = None
    suggestion:  Optional[str] = None
    message:     str = ""


@dataclass
class AddressValidationResult:
    provider_name: str
    fields:        dict[str, FieldValidationResult] = field(default_factory=dict)
    is_valid:      bool = False
    overall_score: float = 0.0
    raw_response:  Optional[str] = None

    def add_field(self, result: FieldValidationResult) -> None:
        self.fields[result.field_name] = result


# ═══════════════════════════════════════════════════════════
# Rule Engine Models
# ═══════════════════════════════════════════════════════════

@dataclass
class RuleContext:
    """Immutable context passed to every GeoRule."""
    provider: str
    cache:    Optional[object] = None
    debug:    bool = False
    config:   dict = field(default_factory=dict)


@dataclass
class RuleEvaluation:
    rule_name:    str
    rule_category: RuleCategory = RuleCategory.COVERAGE
    passed:       bool = True
    severity:     Severity = Severity.INFO
    message:      str = ""
    details:      dict = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════
# Aggregated Results
# ═══════════════════════════════════════════════════════════

@dataclass
class ScoringResult:
    score:            float = 0.0          # 0 … 100
    status:           GeoValidationStatus = GeoValidationStatus.UNCERTAIN
    total_rules:      int = 0
    passed_rules:     int = 0
    failed_rules:     int = 0
    hard_failures:    list[RuleEvaluation] = field(default_factory=list)
    evaluations:      list[RuleEvaluation] = field(default_factory=list)
    calculated_at:    datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GeoValidationReport:
    request_id:       Optional[str] = None
    address:          Optional[GeoAddress] = None
    coordinate:       Optional[GeoCoordinate] = None
    validation_result: Optional[AddressValidationResult] = None
    scoring:          Optional[ScoringResult] = None
    status:           GeoValidationStatus = GeoValidationStatus.UNCERTAIN
    created_at:       datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    errors:           list[str] = field(default_factory=list)

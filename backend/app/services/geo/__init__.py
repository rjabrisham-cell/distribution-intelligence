"""
app.services.geo

Geo Module — DIP Geo Layer root namespace.
Contract v1.2 (Frozen)
"""

from app.services.geo.geo_models import (
    GeoAddress,
    GeoCoordinate,
    GeoProviderCapability,
    CapabilityInfo,
    CapabilityLevel,
    AddressValidationResult,
    FieldValidationResult,
    RuleContext,
    RuleEvaluation,
    RuleCategory,
    Severity,
    ScoringResult,
    GeoValidationReport,
    GeoValidationStatus,
)

from app.services.geo.geo_provider import GeoProvider
from app.services.geo.geo_provider_factory import GeoProviderFactory, get_provider_factory
from app.services.geo.geo_service import GeoValidationService, get_geo_validation_service
from app.services.geo.geo_scoring_engine import GeoScoringEngine
from app.services.geo.geo_rules import GeoRule
from app.services.geo.geo_cache import GeoCache

GEO_CONTRACT_VERSION: str = "1.2"

__all__ = [
    # Models & DTOs
    "GeoAddress",
    "GeoCoordinate",
    "GeoProviderCapability",
    "CapabilityInfo",
    "CapabilityLevel",
    "AddressValidationResult",
    "FieldValidationResult",
    "RuleContext",
    "RuleEvaluation",
    "RuleCategory",
    "Severity",
    "ScoringResult",
    "GeoValidationReport",
    "GeoValidationStatus",
    # Interfaces
    "GeoProvider",
    "GeoRule",
    "GeoCache",
    # Services & Factories
    "GeoProviderFactory",
    "get_provider_factory",
    "GeoValidationService",
    "get_geo_validation_service",
    "GeoScoringEngine",
    # Constants
    "GEO_CONTRACT_VERSION",
]

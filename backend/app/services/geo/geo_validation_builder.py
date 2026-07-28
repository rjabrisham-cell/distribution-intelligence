"""
geo_validation_builder.py — GeoValidationReport Builder
=======================================================
Contract v1.2 (Frozen)

Builder pattern for assembling GeoValidationReport step by step.
Stable — breaking change prohibited.
"""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

from app.services.geo.geo_models import (
    GeoAddress,
    GeoCoordinate,
    AddressValidationResult,
    ScoringResult,
    GeoValidationReport,
    GeoValidationStatus,
)


class GeoValidationBuilder:
    """Step-by-step constructor for GeoValidationReport."""

    def __init__(self) -> None:
        self._report = GeoValidationReport(
            request_id=str(uuid4()),
        )

    # ── Setters ─────────────────────────────────────────

    def set_address(self, address: GeoAddress) -> "GeoValidationBuilder":
        self._report.address = address
        return self

    def set_coordinate(self, coordinate: GeoCoordinate) -> "GeoValidationBuilder":
        self._report.coordinate = coordinate
        return self

    def set_validation_result(self, result: AddressValidationResult) -> "GeoValidationBuilder":
        self._report.validation_result = result
        return self

    def set_scoring(self, scoring: ScoringResult) -> "GeoValidationBuilder":
        self._report.scoring = scoring
        return self

    def add_error(self, error: str) -> "GeoValidationBuilder":
        self._report.errors.append(error)
        return self

    # ── Finalize ────────────────────────────────────────

    def build(self) -> GeoValidationReport:
        """بازگرداندن گزارش نهایی و تعیین status کلی."""
        if self._report.scoring:
            self._report.status = self._report.scoring.status
        elif self._report.errors:
            self._report.status = GeoValidationStatus.INVALID
        else:
            self._report.status = GeoValidationStatus.UNCERTAIN
        return self._report

"""
geo_service.py — Geo Validation Service
========================================
Contract v1.2 (Frozen)

Orchestrator اصلی اعتبارسنجی جغرافیایی.
ترکیب Provider → Rules → Scoring Engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.geo.geo_models import (
        GeoAddress,
        GeoCoordinate,
        GeoValidationReport,
        RuleEvaluation,
        ScoringResult,
    )
    from app.services.geo.geo_provider import GeoProvider
    from app.services.geo.geo_cache import GeoCache
    from app.services.geo.geo_rule_registry import GeoRuleRegistry
    from app.services.geo.geo_scoring_engine import GeoScoringEngine

# Runtime imports
from app.services.geo.geo_models import (
    RuleContext,
    GeoValidationReport,
    GeoValidationStatus,
    Severity,              # ✅ اصلاح ۱: Severity به runtime imports منتقل شد
)
from app.services.geo.geo_cache import GeoCache
from app.services.geo.geo_rule_registry import GeoRuleRegistry
from app.services.geo.geo_scoring_engine import GeoScoringEngine
from app.services.geo.geo_validation_builder import GeoValidationBuilder


class GeoValidationService:
    """
    سرویس اصلی اعتبارسنجی جغرافیایی.

    Flow:
        1. دریافت Provider از Factory
        2. اجرای validate_address / validate_coordinate
        3. اجرای تمام Ruleهای ثبت‌شده روی نتیجه
        4. محاسبه امتیاز نهایی با ScoringEngine
        5. ساخت GeoValidationReport با Builder
    """

    def __init__(
        self,
        rule_registry: Optional[GeoRuleRegistry] = None,
        scoring_engine: Optional[GeoScoringEngine] = None,
        cache_backend: Optional[GeoCache] = None,
        debug: bool = False,
    ) -> None:
        self._rule_registry = rule_registry or GeoRuleRegistry()
        self._scoring_engine = scoring_engine or GeoScoringEngine()
        self._cache_backend = cache_backend or GeoCache()
        self._debug = debug

    # ── Public API ───────────────────────────────────────

    def validate(
        self,
        address: Optional["GeoAddress"] = None,
        coordinate: Optional["GeoCoordinate"] = None,
        provider: Optional["GeoProvider"] = None,
    ) -> "GeoValidationReport":
        """
        اعتبارسنجی آدرس یا مختصات با Provider داده‌شده.

        حداقل یکی از address یا coordinate باید ارائه شود.
        """
        if address is None and coordinate is None:
            return GeoValidationReport(
                status=GeoValidationStatus.INVALID,
                errors=["At least one of address or coordinate must be provided."],
            )

        if provider is None:
            return GeoValidationReport(
                status=GeoValidationStatus.INVALID,
                errors=["No GeoProvider provided."],
            )

        builder = GeoValidationBuilder()

        if address:
            builder.set_address(address)
        if coordinate:
            builder.set_coordinate(coordinate)

        try:
            # Step 1: Provider validation
            if coordinate:
                validation_result = provider.validate_coordinate(coordinate)
            else:
                validation_result = provider.validate_address(address)  # type: ignore[arg-type]

            builder.set_validation_result(validation_result)

            # Step 2: Execute rules
            evaluations = self._execute_rules(
                address=address,
                validation_result=validation_result,
                provider_name=provider.provider_name,
            )

            # Step 3: Scoring
            scoring_result = self._scoring_engine.calculate(evaluations)
            builder.set_scoring(scoring_result)

        except Exception as exc:
            # ✅ اصلاح ۲: به‌جای دسترسی مستقیم به _report.status،
            # خطا رو از طریق add_error ثبت می‌کنیم و build() خودش status رو INVALID می‌کنه.
            builder.add_error(str(exc))

        return builder.build()

    # ── Internal Helpers ────────────────────────────────

    def _execute_rules(
        self,
        address: Optional["GeoAddress"],
        validation_result,
        provider_name: str,
    ) -> list["RuleEvaluation"]:
        """اجرای تمام Ruleهای ثبت‌شده روی نتیجه Provider."""
        context = RuleContext(
            provider=provider_name,
            cache=self._cache_backend,
            debug=self._debug,
            config={},
        )

        evaluations: list[RuleEvaluation] = []
        for rule in self._rule_registry.get_all():
            try:
                eval_result = rule.execute(
                    address=address,  # type: ignore[arg-type]
                    validation_result=validation_result,
                    context=context,
                )
                evaluations.append(eval_result)
            except Exception as exc:
                evaluations.append(
                    RuleEvaluation(
                        rule_name=rule.name,
                        rule_category=rule.category,
                        passed=False,
                        severity=Severity.ERROR,
                        message=f"Rule execution failed: {exc}",
                    )
                )

        return evaluations


# ── Module-level singleton ───────────────────────────────

_service_instance: Optional[GeoValidationService] = None


def get_geo_validation_service(
    debug: bool = False,
) -> GeoValidationService:
    global _service_instance
    if _service_instance is None:
        registry = GeoRuleRegistry()
        registry.auto_discover()
        _service_instance = GeoValidationService(
            rule_registry=registry,
            debug=debug,
        )
    return _service_instance

"""
geo_rules.py — GeoRule Interface
=================================
Contract v1.2 (Frozen)

هر Rule باید این Interface را پیاده‌سازی کند.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.geo.geo_models import (
        GeoAddress,
        AddressValidationResult,
        RuleContext,
        RuleEvaluation,
        RuleCategory,
        Severity,
    )


class GeoRule(ABC):
    """
    Interface یک Rule اعتبارسنجی.

    هر Rule یک جنبه از آدرس را بررسی می‌کند
    (مثلاً completeness, accuracy, consistency).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """نام یکتای Rule."""
        ...

    @property
    @abstractmethod
    def category(self) -> "RuleCategory":
        """دسته‌بندی Rule."""
        ...

    @abstractmethod
    def execute(
        self,
        address: "GeoAddress",
        validation_result: "AddressValidationResult",
        context: "RuleContext",
    ) -> "RuleEvaluation":
        """
        اجرای Rule روی آدرس و نتیجه اعتبارسنجی Provider.

        Args:
            address: آدرس ورودی
            validation_result: نتیجه دریافتی از Provider
            context: کانتکست اجرایی (provider name, cache, debug flag, ...)

        Returns:
            RuleEvaluation شامل نتیجه بررسی.
        """
        ...

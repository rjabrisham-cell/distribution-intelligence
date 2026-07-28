"""
geo_rule_registry.py — Rule Registry with Auto-Discovery
=========================================================
Contract v1.2 (Frozen)
"""

from __future__ import annotations

import inspect
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.geo.geo_rules import GeoRule
    from app.services.geo.geo_models import RuleCategory


class GeoRuleRegistry:
    """ثبت‌کننده و اجراکننده Ruleها با ترتیب اولویت."""

    def __init__(self) -> None:
        self._rules: dict[str, "GeoRule"] = {}

    # ── Registration ─────────────────────────────────────

    def register(self, rule: "GeoRule") -> None:
        """ثبت یک Rule (در صورت تکراری بودن name، overwrite می‌شود)."""
        if not rule.name:
            raise ValueError("Rule must have a non-empty name")
        self._rules[rule.name] = rule

    def unregister(self, name: str) -> None:
        self._rules.pop(name, None)

    # ── Discovery ────────────────────────────────────────

    def auto_discover(self, package_path: str = "app.services.geo.rules") -> None:
        """
        کشف خودکار Ruleها از package_path (پوشه rules/).

        هر ماژول که حاوی کلاسی با ارث‌بری از GeoRule باشد
        به صورت خودکار ثبت می‌شود.
        """
        try:
            package = __import__(package_path, fromlist=[""])
        except ModuleNotFoundError:
            return

        if not hasattr(package, "__path__"):
            return

        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            full_name = f"{package_path}.{module_name}"
            try:
                mod = __import__(full_name, fromlist=[""])
                for name, obj in inspect.getmembers(mod, inspect.isclass):
                    if (
                        obj is not GeoRule
                        and issubclass(obj, GeoRule)
                        and not inspect.isabstract(obj)
                    ):
                        self.register(obj())
            except Exception:
                continue

    # ── Access ───────────────────────────────────────────

    def get(self, name: str) -> Optional["GeoRule"]:
        return self._rules.get(name)

    def get_all(self) -> list["GeoRule"]:
        """بازگرداندن Ruleها به ترتیب ثبت."""
        return list(self._rules.values())

    def get_by_category(self, category: "RuleCategory") -> list["GeoRule"]:
        return [r for r in self._rules.values() if r.category == category]

    def __len__(self) -> int:
        return len(self._rules)

    def __iter__(self):
        return iter(self._rules.values())

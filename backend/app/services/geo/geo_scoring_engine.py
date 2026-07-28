"""
geo_scoring_engine.py — Geo Scoring Engine
============================================
Contract v1.2 (Frozen)

محاسبه امتیاز نهایی بر اساس RuleEvaluationهای دریافتی.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.geo.geo_models import RuleEvaluation, ScoringResult, GeoValidationStatus

# Runtime imports (نه TYPE_CHECKING) برای استفاده در بدنه متدها
from app.services.geo.geo_models import Severity, GeoValidationStatus, ScoringResult


class GeoScoringEngine:
    """
    امتیازدهی به نتایج Ruleها.

    LOGIC:
        - severity == HARD   → FAIL فوری (score=0, status=INVALID)
        - هر ERROR         → -25 امتیاز
        - هر WARNING       → -10 امتیاز
        - هر INFO          → -2  امتیاز
        - امتیاز اولیه = 100
        - حداقل امتیاز = 0
    """

    def calculate(
        self,
        evaluations: list["RuleEvaluation"],
    ) -> "ScoringResult":
        total = len(evaluations)
        if total == 0:
            return ScoringResult(
                score=100.0,
                status=GeoValidationStatus.VALID,
                evaluations=evaluations,
            )

        # ── Hard-stop check ──────────────────────────────
        # مقایسه مستقیم با Severity.HARD (نه str!)
        hard_evals = [e for e in evaluations if e.severity == Severity.HARD]
        if hard_evals:
            return ScoringResult(
                score=0.0,
                status=GeoValidationStatus.INVALID,
                total_rules=total,
                failed_rules=len(hard_evals) + len([e for e in evaluations if not e.passed and e.severity != Severity.HARD]),
                passed_rules=len([e for e in evaluations if e.passed]),
                hard_failures=hard_evals,
                evaluations=evaluations,
            )

        # ── Weighted scoring ─────────────────────────────
        score = 100.0
        passed = 0
        failed = 0

        penalty_map = {
            Severity.ERROR:   25,
            Severity.WARNING: 10,
            Severity.INFO:    2,
        }

        for e in evaluations:
            if e.passed:
                passed += 1
            else:
                failed += 1
                penalty = penalty_map.get(e.severity, 5)
                score -= penalty

        score = max(score, 0.0)

        # ── Status inference ─────────────────────────────
        if score >= 80:
            status = GeoValidationStatus.VALID
        elif score >= 50:
            status = GeoValidationStatus.SUSPICIOUS
        else:
            status = GeoValidationStatus.INVALID

        return ScoringResult(
            score=score,
            status=status,
            total_rules=total,
            passed_rules=passed,
            failed_rules=failed,
            evaluations=evaluations,
        )

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class SectionStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    UNKNOWN = "unknown"
    EMPTY = "empty"


@dataclass(frozen=True, slots=True)
class ReportMetric:
    key: str
    label: str
    value: Any


@dataclass(frozen=True, slots=True)
class ReportSection:
    name: str
    status: SectionStatus
    percentage: float | None
    score: float | None
    passed: int
    failed: int
    unknown: int
    summary: str
    metrics: tuple[ReportMetric, ...] = ()
    raw: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "percentage": self.percentage,
            "score": self.score,
            "passed": self.passed,
            "failed": self.failed,
            "unknown": self.unknown,
            "summary": self.summary,
            "metrics": [asdict(metric) for metric in self.metrics],
        }


@dataclass(frozen=True, slots=True)
class Report:
    audit_run_id: Any
    elapsed_sec: float | None
    overall_status: SectionStatus
    sections: tuple[ReportSection, ...]
    totals: tuple[ReportMetric, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_run_id": self.audit_run_id,
            "elapsed_sec": self.elapsed_sec,
            "overall_status": self.overall_status.value,
            "sections": [section.to_dict() for section in self.sections],
            "totals": [asdict(metric) for metric in self.totals],
        }


class ReportBuilder:
    """Build a backend-friendly report from finalized AuditRunner results.

    The builder consumes the exact AuditRunner.run() structure:

        {
            "audit_run_id": ...,
            "elapsed_sec": ...,
            "results": {...},
        }

    No new percentage thresholds or business rules are introduced here.

    For sections that do not yet have a finalized report contract
    (for example coordinate/consistency/address_standardizer), the builder
    preserves the payload and reports UNKNOWN instead of inventing PASS/FAIL.
    """

    _ORDER = (
        "completeness",
        "validity",
        "coordinate",
        "consistency",
        "duplicates",
        "address_standardizer",
    )

    def __init__(self) -> None:
        self._handlers = {
            "completeness": self._section_completeness,
            "validity": self._section_validity,
            "duplicates": self._section_duplicates,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, audit_run: dict[str, Any]) -> dict[str, Any]:
        """Build the final serializable report dictionary."""

        run_id = audit_run.get("audit_run_id")
        elapsed = audit_run.get("elapsed_sec")
        results = audit_run.get("results") or {}

        summary = self.build_summary(results)

        report = Report(
            audit_run_id=run_id,
            elapsed_sec=elapsed,
            overall_status=summary["overall_status"],
            sections=summary["sections"],
            totals=summary["totals"],
        )

        return report.to_dict()

    def build_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """Build normalized section summaries from AuditRunner results."""

        sections = tuple(
            self.build_section(name, results.get(name))
            for name in self._ORDER
        )

        return {
            "overall_status": self._overall_status(sections),
            "sections": sections,
            "totals": self._build_totals(sections),
        }

    def build_section(
        self,
        name: str,
        payload: dict[str, Any] | None,
    ) -> ReportSection:
        """Normalize one audit service result into a ReportSection."""

        # Missing result means UNKNOWN.
        # It must never be converted into FAIL.
        if payload is None:
            return ReportSection(
                name=name,
                status=SectionStatus.UNKNOWN,
                percentage=None,
                score=None,
                passed=0,
                failed=0,
                unknown=0,
                summary=f"{name}: no results available",
            )

        handler = self._handlers.get(name)

        if handler is None:
            return self._section_placeholder(name, payload)

        return handler(name, payload)

    # ------------------------------------------------------------------
    # Section handlers
    # ------------------------------------------------------------------

    def _section_completeness(
        self,
        name: str,
        payload: dict[str, Any],
    ) -> ReportSection:
        total = int(payload.get("total_stores") or 0)
        passed = int(payload.get("passed_stores") or 0)
        failed = max(total - passed, 0)

        return ReportSection(
            name=name,
            status=self._status(total, passed),
            percentage=payload.get("overall_percentage"),
            score=payload.get("average_raw_score"),
            passed=passed,
            failed=failed,
            unknown=0,
            summary=f"{passed}/{total} stores passed completeness",
            metrics=(
                ReportMetric(
                    "overall_percentage",
                    "Overall percentage",
                    payload.get("overall_percentage"),
                ),
                ReportMetric(
                    "average_raw_score",
                    "Average raw score",
                    payload.get("average_raw_score"),
                ),
                ReportMetric(
                    "median_percentage",
                    "Median percentage",
                    payload.get("median_percentage"),
                ),
                ReportMetric(
                    "fully_complete_stores",
                    "Fully complete stores",
                    payload.get("fully_complete_stores"),
                ),
            ),
            raw=payload,
        )

    def _section_validity(
        self,
        name: str,
        payload: dict[str, Any],
    ) -> ReportSection:
        total = int(payload.get("total_stores") or 0)
        passed = int(payload.get("passed_stores") or 0)
        failed = max(total - passed, 0)
        unknown = int(payload.get("unknown_field_count") or 0)

        return ReportSection(
            name=name,
            status=self._status(total, passed),
            percentage=payload.get("overall_percentage"),
            score=payload.get("average_raw_score"),
            passed=passed,
            failed=failed,
            unknown=unknown,
            summary=f"{passed}/{total} stores passed validity",
            metrics=(
                ReportMetric(
                    "overall_percentage",
                    "Overall percentage",
                    payload.get("overall_percentage"),
                ),
                ReportMetric(
                    "invalid_field_count",
                    "Invalid fields",
                    payload.get("invalid_field_count"),
                ),
                ReportMetric(
                    "warning_field_count",
                    "Warning fields",
                    payload.get("warning_field_count"),
                ),
                ReportMetric(
                    "unknown_field_count",
                    "Unknown fields",
                    payload.get("unknown_field_count"),
                ),
            ),
            raw=payload,
        )

    def _section_duplicates(
        self,
        name: str,
        payload: dict[str, Any],
    ) -> ReportSection:
        total = int(payload.get("store_count") or 0)
        unique = int(payload.get("unique_count") or 0)
        possible = int(payload.get("possible_duplicate_count") or 0)
        duplicate = int(payload.get("duplicate_count") or 0)
        unknown = int(payload.get("unknown_count") or 0)

        percentage = (
            round(unique * 100 / total, 1)
            if total > 0
            else None
        )

        return ReportSection(
            name=name,
            status=self._duplicates_status(
                total=total,
                unique=unique,
                possible=possible,
                duplicate=duplicate,
                unknown=unknown,
            ),
            percentage=percentage,
            score=None,
            passed=unique,
            failed=duplicate,
            unknown=unknown,
            summary=(
                f"{duplicate} duplicate, {possible} possible, "
                f"{unique}/{total} unique"
            ),
            metrics=(
                ReportMetric(
                    "duplicate_count",
                    "Duplicates",
                    duplicate,
                ),
                ReportMetric(
                    "possible_duplicate_count",
                    "Possible duplicates",
                    possible,
                ),
                ReportMetric(
                    "candidate_count",
                    "Candidates",
                    payload.get("candidate_count"),
                ),
            ),
            raw=payload,
        )

    def _section_placeholder(
        self,
        name: str,
        payload: dict[str, Any],
    ) -> ReportSection:
        """Keep unfinalized sections UNKNOWN without inventing semantics."""

        return ReportSection(
            name=name,
            status=SectionStatus.UNKNOWN,
            percentage=None,
            score=None,
            passed=0,
            failed=0,
            unknown=0,
            summary=f"{name}: no report mapping defined yet",
            metrics=(
                ReportMetric(
                    "payload_keys",
                    "Raw payload keys",
                    sorted(payload.keys()),
                ),
            ),
            raw=payload,
        )

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _status(
        total: int,
        passed: int,
    ) -> SectionStatus:
        """Derive PASS/FAIL without introducing a new percentage threshold."""

        if total == 0:
            return SectionStatus.EMPTY

        if passed == total:
            return SectionStatus.PASS

        return SectionStatus.FAIL

    @staticmethod
    def _duplicates_status(
        total: int,
        unique: int,
        possible: int,
        duplicate: int,
        unknown: int,
    ) -> SectionStatus:
        """Derive duplicate-section status conservatively.

        UNKNOWN is checked before WARNING/FAIL when all stores are unknown.
        Definite duplicates are FAIL.
        Possible duplicates are WARNING.
        """

        if total == 0:
            return SectionStatus.EMPTY

        if unknown == total:
            return SectionStatus.UNKNOWN

        if duplicate > 0:
            return SectionStatus.FAIL

        if possible > 0:
            return SectionStatus.WARNING

        return SectionStatus.PASS

    @staticmethod
    def _overall_status(
        sections: tuple[ReportSection, ...],
    ) -> SectionStatus:
        """Calculate overall status from sections with decisive statuses.

        UNKNOWN and EMPTY sections do not force the entire report to UNKNOWN.
        A real FAIL takes precedence over WARNING, and WARNING takes precedence
        over PASS.
        """

        decisive = [
            section
            for section in sections
            if section.status
            in (
                SectionStatus.PASS,
                SectionStatus.FAIL,
                SectionStatus.WARNING,
            )
        ]

        if not decisive:
            return SectionStatus.UNKNOWN

        if any(
            section.status == SectionStatus.FAIL
            for section in decisive
        ):
            return SectionStatus.FAIL

        if any(
            section.status == SectionStatus.WARNING
            for section in decisive
        ):
            return SectionStatus.WARNING

        return SectionStatus.PASS

    @staticmethod
    def _build_totals(
        sections: tuple[ReportSection, ...],
    ) -> tuple[ReportMetric, ...]:
        """Build aggregate counters across report sections."""

        return (
            ReportMetric(
                "passed",
                "Passed",
                sum(section.passed for section in sections),
            ),
            ReportMetric(
                "failed",
                "Failed",
                sum(section.failed for section in sections),
            ),
            ReportMetric(
                "unknown",
                "Unknown",
                sum(section.unknown for section in sections),
            ),
        )


__all__ = [
    "Report",
    "ReportBuilder",
    "ReportMetric",
    "ReportSection",
    "SectionStatus",
]
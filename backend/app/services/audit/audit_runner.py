# ============================================================================
# Distribution Intelligence Platform (DIP)
# Sprint 2 — Phase 1
#
# Data Quality Audit Runner
# Contract v1.2 (Frozen)
#
# Responsibilities:
#   - Own the database Session
#   - Stream stores with yield_per() — SINGLE stream for ALL audits
#   - Call pure audit services
#   - Accumulate results incrementally — NO materialization of all results
#
# Design decision (Sprint 2):
#   Instead of separate _run_completeness / _run_validity methods that each
#   re-query the DB, we use a SINGLE for-loop over stores and feed all
#   accumulators in one pass.  This keeps DB pressure constant regardless
#   of how many audit dimensions we add later.
# ============================================================================

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.import_batch import ImportBatch
from app.models.store import Store

from app.services.audit.completeness import CompletenessService, BatchAccumulator
from app.services.audit.validity import ValidityService, ValidityBatchAccumulator


class AuditRunner:

    def __init__(self):
        self.db: Session = SessionLocal()
        self._raw: dict[str, Any] = {}

    # ── Public API ──────────────────────────────────────────────────────
    def run(self) -> dict[str, Any]:
        started   = time.time()
        audit_run = self._create_audit_record()

        # ── Build all services & accumulators up-front ──────────────────
        completeness_svc = CompletenessService()
        completeness_acc = completeness_svc.create_accumulator()

        validity_svc = ValidityService()
        validity_acc = validity_svc.create_accumulator()

        # آینده:
        # consistency_svc = ConsistencyService()
        # consistency_acc = consistency_svc.create_accumulator()
        # duplicate_svc   = DuplicateService()
        # duplicate_acc   = duplicate_svc.create_accumulator()

        # ── SINGLE stream — stores only read ONCE from DB ───────────────
        stores = (
            self.db.query(Store)
            .order_by(Store.id)
            .yield_per(5000)
        )

        for store in stores:
            completeness_acc.update(completeness_svc.evaluate(store))
            validity_acc.update(validity_svc.evaluate(store))
            # آینده:
            # consistency_acc.update(consistency_svc.evaluate(store))
            # duplicate_acc.update(duplicate_svc.evaluate(store))

        # ── Finalize all batches ────────────────────────────────────────
        comp_batch = completeness_acc.finalize()
        valid_batch = validity_acc.finalize()

        self._raw["completeness"] = {
            "audit_run_id"         : audit_run.id,
            "total_stores"         : comp_batch.total_stores,
            "evaluated_stores"     : comp_batch.evaluated_stores,
            "passed_stores"        : comp_batch.passed_stores,
            "fully_complete_stores": comp_batch.fully_complete_stores,
            "overall_percentage"   : comp_batch.overall_percentage,
            "average_raw_score"    : comp_batch.average_raw_score,
            "median_percentage"    : comp_batch.median_percentage,
            "min_percentage"       : comp_batch.min_percentage,
            "max_percentage"       : comp_batch.max_percentage,
            "group_scores"         : comp_batch.group_summary,
            "field_fill_rates"     : comp_batch.field_summary,
        }

        self._raw["validity"] = {
            "audit_run_id"         : audit_run.id,
            "total_stores"         : valid_batch.total_stores,
            "evaluated_stores"     : valid_batch.evaluated_stores,
            "passed_stores"        : valid_batch.passed_stores,
            "fully_valid_stores"   : valid_batch.fully_valid_stores,
            "overall_percentage"   : valid_batch.overall_percentage,
            "average_raw_score"    : valid_batch.average_raw_score,
            "median_percentage"    : valid_batch.median_percentage,
            "min_percentage"       : valid_batch.min_percentage,
            "max_percentage"       : valid_batch.max_percentage,
            "invalid_field_count"  : valid_batch.invalid_field_count,
            "warning_field_count"  : valid_batch.warning_field_count,
            "unknown_field_count"  : valid_batch.unknown_field_count,
            "group_scores"         : valid_batch.group_summary,
            "field_validity_rates" : valid_batch.field_summary,
        }

        self._finalize_audit(audit_run, started)

        return {
            "audit_run_id": audit_run.id,
            "elapsed_sec" : round(time.time() - started, 2),
            "results"     : self._raw,
        }

    # ── Audit record lifecycle ──────────────────────────────────────────
    def _create_audit_record(self) -> ImportBatch:
        audit_run = ImportBatch(
            filename="GLOBAL_REPOSITORY",
            original_filename="GLOBAL_REPOSITORY",
            file_type="AUDIT",
            total_rows=0,
            status="PROCESSING",
            uploaded_by=None,
        )
        self.db.add(audit_run)
        self.db.commit()
        self.db.refresh(audit_run)
        return audit_run

    def _finalize_audit(self, audit_run: ImportBatch, started: float) -> None:
        audit_run.status = "COMPLETED"
        elapsed = round(time.time() - started, 2)
        audit_run.raw_data = {
            "elapsed_sec": elapsed,
            "completed_at": datetime.utcnow().isoformat(),
        }
        self.db.commit()
        self.db.close()


def run():
    AuditRunner().run()

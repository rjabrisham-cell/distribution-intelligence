# Milestone 2.1: active store dataset

This change preserves the existing pipeline and replaces inferred membership
with an explicit, completed store import batch.

## Schema

- `files.removed_at`: nullable timestamp; project store files are retired without
  deleting their disk contents, batches, or imported entities. Other file types
  retain their existing deletion behavior.
- `projects.active_store_batch_id`: nullable foreign key to `import_batches`.
  Successful store import publishes the batch; removing its file clears the
  pointer. There is no automatic fallback or historical backfill.
- `import_store_rows`: exact accepted input membership, including missing-address
  rows. Each row has `batch_id`, `company_store_id`, `row_number`, a JSON input
  snapshot, and timestamps. `(batch_id, row_number)` is unique. Foreign keys use
  `RESTRICT` to retain provenance.

Validation, Matching and Readiness use that boundary. Matching also checks it
under a project lock immediately before persistence. Readiness uses one scoped
read query and does not invoke Matching. Snapshots supply batch-specific input
without overwriting shared CompanyStore input fields; confirmed Master values
keep their previous precedence. Completed-import retries do not republish a
historical batch. Decision is outside this milestone.

## Isolated verification

Tests require Docker/Python 3.11 and an explicit `DIP_DATASET_TEST_URL` whose host
is `dip-m21-db` and database is `dip_m21_test`; the integration fixtures refuse
other destinations. Without that variable they skip, so a run with skips is
not evidence that the integration tests passed.

```text
python -m pytest app/services/audit/tests -q -p no:cacheprovider
```

The disposable database uses an internal Docker network and memory-backed data;
the runner mounts backend code read-only. No application dependency was changed.
The PyPI request timed out, so existing pure-Python pytest packages and its
official dependencies were copied into the temporary runner; Python 3.14 was
not used to run the application or its tests.

Migration verification runs the existing chain in `public`, tests
`upgrade → downgrade → upgrade`, nullable fields and uniqueness, and verifies
that downgrade refuses after the new history is used.

**Existing migration limitation:** a database created solely from the old
migration chain lacks existing ImportBatch model columns `readiness_score`,
`validation_summary`, `geo_summary`, and `duplicate_summary`. The initial
application integration run exposed `UndefinedColumn(readiness_score)`. Old
migrations were not rewritten. Application integration tests therefore use a
separate `dataset_contract` schema created from the existing ORM definitions,
with transactions rolled back after each test. Passing those tests does not
certify a complete fresh deployment using the historical migration chain.

Two local compatibility issues exposed during tests were corrected: the
CompanyStore model now reflects the nullable store code already established by
migration `20260831_100000`, and the CSV reader discards the Excel-only
`sheet_name` option. Regression coverage includes both CSV and XLSX uploads.

## Deployment boundary

No migration, cleanup, Matching, or backfill was executed against live DIP.
Projects 1 and 24 were not modified. The running backend was not restarted.
This code requires the additive migration before it is loaded in production.

Existing projects, including project 24, retain all their history but have a
NULL active pointer after migration. They display “no active dataset”; their
old batches are not inferred or silently reactivated. The healthy first-upload
behavior is covered with synthetic new projects. Preserving the old project 24
display after deployment requires a separately verified activation procedure,
which this change does not invent or execute.

Proposed production command, **not executed**:

```text
docker compose exec backend python -m alembic upgrade 20260912_010000
```

Production rollout and the existing migration-chain discrepancy must be reviewed
before executing that command or reloading the backend. Downgrade is deliberately
refused once it would erase dataset lineage or removal history.

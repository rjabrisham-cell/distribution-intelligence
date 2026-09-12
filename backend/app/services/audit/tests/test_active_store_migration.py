"""Migration verification against the disposable milestone database only."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


@pytest.fixture
def migration_engine():
    url = os.environ.get("DIP_DATASET_TEST_URL")
    if not url:
        pytest.skip("Requires explicit isolated DIP_DATASET_TEST_URL")
    parsed = make_url(url)
    if parsed.host != "dip-m21-db" or parsed.database != "dip_m21_test":
        pytest.fail("Refusing migration outside the disposable test database")
    engine = create_engine(url)
    yield engine
    engine.dispose()


def test_upgrade_downgrade_upgrade(migration_engine):
    env = dict(os.environ, DATABASE_URL=migration_engine.url.render_as_string(hide_password=False))
    for command in (("downgrade", "20260831_100000"), ("upgrade", "20260912_010000")):
        result = subprocess.run([sys.executable, "-m", "alembic", *command],
                                env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    inspector = inspect(migration_engine)
    assert {"batch_id", "company_store_id", "row_number", "snapshot"} <= {
        c["name"] for c in inspector.get_columns("import_store_rows")}
    assert next(c for c in inspector.get_columns("projects") if c["name"] == "active_store_batch_id")["nullable"]
    assert next(c for c in inspector.get_columns("files") if c["name"] == "removed_at")["nullable"]
    assert any(c["column_names"] == ["batch_id", "row_number"]
               for c in inspector.get_unique_constraints("import_store_rows"))


def test_downgrade_refuses_to_erase_used_history(migration_engine):
    path = Path("alembic/versions/20260912_010000_active_store_dataset.py")
    spec = importlib.util.spec_from_file_location("dataset_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with migration_engine.connect() as connection:
        transaction = connection.begin()
        connection.execute(text("""
            INSERT INTO files (entity_type, entity_id, category, original_name,
              stored_name, file_path, content_type, file_size, removed_at)
            VALUES ('PROJECT', 999999, 'stores', 'synthetic.csv',
              'synthetic-migration-guard.csv', '/tmp/synthetic.csv', 'text/csv', 0, now())
        """))
        with Operations.context(MigrationContext.configure(connection)):
            with pytest.raises(RuntimeError, match="history must be retained"):
                migration.downgrade()
        assert connection.execute(text("SELECT count(*) FROM files WHERE removed_at IS NOT NULL")).scalar() == 1
        assert inspect(connection).has_table("import_store_rows")
        transaction.rollback()

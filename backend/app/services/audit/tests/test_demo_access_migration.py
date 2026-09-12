"""Exercise upgrade/downgrade with legacy sentinels in a disposable schema."""
import importlib.util
from uuid import uuid4
from sqlalchemy import text, inspect
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.services.audit.tests.test_demo_security import engine


def test_upgrade_downgrade_preserves_legacy_rows(engine):
    schema = 'demo_migration_' + uuid4().hex[:12]
    spec = importlib.util.spec_from_file_location('demo_migration', 'alembic/versions/20260912_020000_demo_access.py')
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as c:
        c = c.execution_options(schema_translate_map=None)
        c.execute(text(f'CREATE SCHEMA {schema}'))
        c.execute(text(f'SET LOCAL search_path TO {schema}, public'))
        c.execute(text('CREATE TABLE accounts (id integer PRIMARY KEY, mobile varchar(20))'))
        c.execute(text('CREATE TABLE import_batches (id integer PRIMARY KEY)'))
        c.execute(text('CREATE TABLE projects (id integer PRIMARY KEY, name varchar(255))'))
        c.execute(text("INSERT INTO accounts VALUES (1, 'synthetic')"))
        c.execute(text("INSERT INTO projects VALUES (1, 'Legacy sentinel')"))
        with Operations.context(MigrationContext.configure(c)):
            migration.upgrade()
            assert c.execute(text('SELECT trial_owner_id, trial_state FROM projects WHERE id=1')).one() == (None, None)
            assert c.execute(text('SELECT mobile_verified_at FROM accounts WHERE id=1')).scalar() is None
            assert {'demo_sessions','demo_challenges','demo_rate_events'} <= set(inspect(c).get_table_names(schema=schema))
            migration.downgrade()
            assert c.execute(text('SELECT name FROM projects WHERE id=1')).scalar() == 'Legacy sentinel'
            assert 'trial_owner_id' not in {col['name'] for col in inspect(c).get_columns('projects',schema=schema)}
            migration.upgrade()
            assert c.execute(text('SELECT count(*) FROM projects')).scalar() == 1

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.models.base import Base
import app.models  # noqa: F401 - لازم برای ثبت تمام مدل‌ها در metadata


# ==========================================================
# Alembic Config
# ==========================================================

config = context.config


# ==========================================================
# Logging
# ==========================================================

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ==========================================================
# SQLAlchemy Metadata
# ==========================================================

# تنها منبع حقیقت برای مدل‌های SQLAlchemy
target_metadata = Base.metadata


# ==========================================================
# Database URL
# ==========================================================

# تنها منبع حقیقت:
# DATABASE_URL از settings
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL,
)


# ==========================================================
# Alembic Autogenerate Filters
# ==========================================================

def include_object(
    object_,
    name,
    type_,
    reflected,
    compare_to,
):
    """
    کنترل اشیایی که Alembic در autogenerate بررسی می‌کند.

    spatial_ref_sys متعلق به PostGIS است و نباید توسط
    Alembic به عنوان بخشی از مدل‌های برنامه مدیریت شود.

    بنابراین:
        - ایجاد نمی‌شود
        - حذف نمی‌شود
        - در alembic check اختلاف محسوب نمی‌شود
    """

    if type_ == "table" and name == "spatial_ref_sys":
        return False

    return True


# ==========================================================
# Offline Migration
# ==========================================================

def run_migrations_offline() -> None:
    """
    Run migrations in offline mode.
    """

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


# ==========================================================
# Online Migration
# ==========================================================

def run_migrations_online() -> None:
    """
    Run migrations in online mode.

    Alembic runs synchronously, therefore psycopg2
    must be used instead of asyncpg.

    DATABASE_URL remains the single source of truth.
    The URL is converted only for Alembic execution.
    """

    # ------------------------------------------------------
    # Convert asyncpg URL -> psycopg2 URL
    # ------------------------------------------------------

    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://",
        "postgresql+psycopg2://",
    )

    # ------------------------------------------------------
    # Alembic configuration
    # ------------------------------------------------------

    configuration = config.get_section(
        config.config_ini_section,
        {},
    )

    configuration["sqlalchemy.url"] = sync_url

    # ------------------------------------------------------
    # SQLAlchemy Engine
    # ------------------------------------------------------

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # ------------------------------------------------------
    # Database Connection
    # ------------------------------------------------------

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


# ==========================================================
# Entry Point
# ==========================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
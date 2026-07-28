#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ETL migration script: legacy MySQL stores -> PostgreSQL DIP stores

Model B:
- PostgreSQL stores.id remains internal and auto-generated
- MySQL source id is stored in stores.legacy_mysql_id
- mobile column is auto-created if missing
- legacy_mysql_id column is auto-created if missing
- region_id -> district_id

Improvements in this version:
- Keyset pagination on MySQL source: WHERE id > :last_id ORDER BY id LIMIT :limit
- Resume support via checkpoint file and fallback to MAX(legacy_mysql_id)
- Retry on transient MySQL connection errors
- Graceful stop on Ctrl+C / SIGTERM after current batch
- No long-lived streaming cursor against MySQL
- Batch upsert into PostgreSQL
- SQLAlchemy 2 compatible

Examples:

Fresh full load:
    docker compose exec backend sh -lc "ETL_TRUNCATE_TARGET_FIRST=true ETL_RESUME=false ETL_LIMIT_ROWS=0 ETL_BATCH_SIZE=1000 python /app/scripts/etl_migrate_stores.py"

Resume after crash:
    docker compose exec backend sh -lc "ETL_TRUNCATE_TARGET_FIRST=false ETL_RESUME=true ETL_LIMIT_ROWS=0 ETL_BATCH_SIZE=1000 python /app/scripts/etl_migrate_stores.py"

Test with 100 rows:
    docker compose exec backend sh -lc "ETL_TRUNCATE_TARGET_FIRST=false ETL_RESUME=false ETL_LIMIT_ROWS=100 ETL_BATCH_SIZE=100 python /app/scripts/etl_migrate_stores.py"
"""

from __future__ import annotations

import csv
import json
import os
import signal
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, RowMapping
from sqlalchemy.exc import DBAPIError, OperationalError


# =============================================================================
# CONFIG
# =============================================================================

MYSQL_HOST = os.getenv("MYSQL_HOST", "host.docker.internal")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB = os.getenv("MYSQL_DB", "fishopping_supermarket")
MYSQL_USER = os.getenv("MYSQL_USER", "fishopping_supermarket")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "distribution_intelligence")
POSTGRES_USER = os.getenv("POSTGRES_USER", "distribution_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

BATCH_SIZE = int(os.getenv("ETL_BATCH_SIZE", "1000"))
LOG_DIR = Path(os.getenv("ETL_LOG_DIR", "/app/scripts/logs"))
SOURCE_TABLE = os.getenv("ETL_SOURCE_TABLE", "stores")
TARGET_TABLE = os.getenv("ETL_TARGET_TABLE", "stores")
TRUNCATE_TARGET_FIRST = os.getenv("ETL_TRUNCATE_TARGET_FIRST", "false").lower() == "true"
LIMIT_ROWS = int(os.getenv("ETL_LIMIT_ROWS", "0"))

ETL_RESUME = os.getenv("ETL_RESUME", "true").lower() == "true"
ETL_RESUME_FROM_TARGET_MAX = os.getenv("ETL_RESUME_FROM_TARGET_MAX", "true").lower() == "true"
ETL_MAX_RETRIES = int(os.getenv("ETL_MAX_RETRIES", "3"))
ETL_RETRY_DELAY_SECONDS = float(os.getenv("ETL_RETRY_DELAY_SECONDS", "5"))
ETL_START_AFTER_ID = int(os.getenv("ETL_START_AFTER_ID", "0"))
ETL_CHECKPOINT_FILE = Path(
    os.getenv("ETL_CHECKPOINT_FILE", str(LOG_DIR / f"{TARGET_TABLE}_etl_checkpoint.json"))
)

MYSQL_CONNECT_TIMEOUT = int(os.getenv("MYSQL_CONNECT_TIMEOUT", "20"))
MYSQL_READ_TIMEOUT = int(os.getenv("MYSQL_READ_TIMEOUT", "600"))
MYSQL_WRITE_TIMEOUT = int(os.getenv("MYSQL_WRITE_TIMEOUT", "600"))
MYSQL_POOL_RECYCLE = int(os.getenv("MYSQL_POOL_RECYCLE", "1800"))

STOP_REQUESTED = False


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Stats:
    total_read: int = 0
    total_inserted: int = 0
    total_failed: int = 0
    total_invalid_coordinates: int = 0
    total_valid_coordinates: int = 0
    total_null_coordinates: int = 0
    total_zero_coordinates: int = 0
    total_unparseable_coordinates: int = 0
    total_outside_or_projected_coordinates: int = 0
    total_fallback_names: int = 0
    total_batches: int = 0


@dataclass
class Checkpoint:
    job_name: str
    source_table: str
    target_table: str
    last_id: int
    total_read: int
    total_inserted: int
    total_failed: int
    total_batches: int
    updated_at: str
    mode: str


# =============================================================================
# HELPERS
# =============================================================================

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def now_local_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(f"[{now_local_str()}] {msg}", flush=True)


def clean_str(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def clean_bool_from_status(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "active", "enabled"}:
        return True
    if s in {"0", "false", "no", "inactive", "disabled"}:
        return False

    return True


def parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    english_digits = "0123456789"

    trans_table = {}
    for p, e in zip(persian_digits, english_digits):
        trans_table[ord(p)] = e
    for a, e in zip(arabic_digits, english_digits):
        trans_table[ord(a)] = e

    raw = raw.translate(trans_table)
    raw = raw.replace("،", ".").replace(",", ".")
    raw = raw.replace(" ", "").strip()

    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


def is_valid_iran_lat_lon(lat: Decimal, lon: Decimal) -> bool:
    return Decimal("24") <= lat <= Decimal("40") and Decimal("44") <= lon <= Decimal("64")


def normalize_coordinates(latitude_raw: Any, longitude_raw: Any) -> tuple[Decimal | None, Decimal | None, str]:
    if latitude_raw is None or longitude_raw is None:
        return None, None, "null"

    lat_raw_str = str(latitude_raw).strip()
    lon_raw_str = str(longitude_raw).strip()

    if not lat_raw_str or not lon_raw_str:
        return None, None, "null"

    lat = parse_decimal(latitude_raw)
    lon = parse_decimal(longitude_raw)

    if lat is None or lon is None:
        return None, None, "unparseable"

    if lat == 0 or lon == 0:
        return None, None, "zero"

    if is_valid_iran_lat_lon(lat, lon):
        return lat, lon, "valid"

    return None, None, "outside_or_projected"


def choose_canonical_name(shop_name: Any, manager_name: Any, source_id: Any) -> tuple[str, bool]:
    shop = clean_str(shop_name)
    if shop:
        return shop, False

    manager = clean_str(manager_name)
    if manager:
        return f"فروشگاه {manager}", True

    return f"Unnamed Store #{source_id}", True


def safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def build_mysql_url() -> str:
    password = quote_plus(MYSQL_PASSWORD)
    return f"mysql+pymysql://{MYSQL_USER}:{password}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"


def build_postgres_url() -> str:
    password = quote_plus(POSTGRES_PASSWORD)
    return f"postgresql+psycopg://{POSTGRES_USER}:{password}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


def create_mysql_engine() -> Engine:
    return create_engine(
        build_mysql_url(),
        pool_pre_ping=True,
        pool_recycle=MYSQL_POOL_RECYCLE,
        future=True,
        connect_args={
            "connect_timeout": MYSQL_CONNECT_TIMEOUT,
            "read_timeout": MYSQL_READ_TIMEOUT,
            "write_timeout": MYSQL_WRITE_TIMEOUT,
            "charset": "utf8mb4",
        },
    )


def create_postgres_engine() -> Engine:
    return create_engine(
        build_postgres_url(),
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )


def get_mysql_columns(engine: Engine, table_name: str) -> set[str]:
    sql = text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :db_name
          AND TABLE_NAME = :table_name
        ORDER BY ORDINAL_POSITION
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"db_name": MYSQL_DB, "table_name": table_name}).fetchall()
    return {row[0] for row in rows}


def get_postgres_columns(engine: Engine, table_name: str) -> set[str]:
    sql = text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table_name
        ORDER BY ordinal_position
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"table_name": table_name}).fetchall()
    return {row[0] for row in rows}


def ensure_mobile_column(pg_engine: Engine, table_name: str) -> None:
    columns = get_postgres_columns(pg_engine, table_name)
    if "mobile" in columns:
        log(f"Column public.{table_name}.mobile already exists")
        return

    log(f"Column public.{table_name}.mobile does not exist. Creating it...")
    alter_sql = text(f"ALTER TABLE {table_name} ADD COLUMN mobile VARCHAR(20)")
    with pg_engine.begin() as conn:
        conn.execute(alter_sql)
    log(f"Column public.{table_name}.mobile created successfully")


def ensure_legacy_mysql_id_column(pg_engine: Engine, table_name: str) -> None:
    columns = get_postgres_columns(pg_engine, table_name)
    if "legacy_mysql_id" not in columns:
        log(f"Column public.{table_name}.legacy_mysql_id does not exist. Creating it...")
        alter_sql = text(f"ALTER TABLE {table_name} ADD COLUMN legacy_mysql_id BIGINT")
        with pg_engine.begin() as conn:
            conn.execute(alter_sql)
        log(f"Column public.{table_name}.legacy_mysql_id created successfully")
    else:
        log(f"Column public.{table_name}.legacy_mysql_id already exists")

    log(f"Ensuring unique index on public.{table_name}.legacy_mysql_id ...")
    index_sql = text(
        f"CREATE UNIQUE INDEX IF NOT EXISTS ux_{table_name}_legacy_mysql_id "
        f"ON {table_name} (legacy_mysql_id)"
    )
    with pg_engine.begin() as conn:
        conn.execute(index_sql)
    log(f"Unique index ensured on public.{table_name}.legacy_mysql_id")


def validate_source_schema(mysql_engine: Engine) -> None:
    required_source_columns = {
        "id",
        "shop_name",
        "manager_name",
        "phone",
        "mobile",
        "province_id",
        "city_id",
        "region_id",
        "address",
        "plaque",
        "unit",
        "floor",
        "latitude",
        "longitude",
        "postal_code",
        "source_type",
        "status",
        "created_at",
        "updated_at",
    }

    source_columns = get_mysql_columns(mysql_engine, SOURCE_TABLE)
    missing = sorted(required_source_columns - source_columns)
    if missing:
        raise RuntimeError(
            f"Missing required source columns in MySQL table {SOURCE_TABLE}: {missing}"
        )

    log(f"MySQL source columns validated successfully ({len(source_columns)} columns found)")


def validate_target_schema(pg_engine: Engine) -> None:
    required_target_columns = {
        "canonical_name",
        "canonical_phone",
        "mobile",
        "manager_name",
        "address",
        "postal_code",
        "plaque",
        "unit",
        "floor",
        "province_id",
        "city_id",
        "district_id",
        "latitude",
        "longitude",
        "master_source",
        "is_active",
        "created_at",
        "updated_at",
        "legacy_mysql_id",
    }

    target_columns = get_postgres_columns(pg_engine, TARGET_TABLE)
    missing = sorted(required_target_columns - target_columns)
    if missing:
        raise RuntimeError(
            f"Missing required target columns in PostgreSQL table {TARGET_TABLE}: {missing}"
        )

    log(f"PostgreSQL target columns validated successfully ({len(target_columns)} columns found)")


def is_retryable_mysql_exception(exc: Exception) -> bool:
    message = str(exc).lower()

    retry_tokens = [
        "lost connection to mysql server during query",
        "server has gone away",
        "connection was killed",
        "connection reset",
        "timed out",
        "timeout",
        "2013",
        "2006",
    ]

    if any(token in message for token in retry_tokens):
        return True

    if isinstance(exc, OperationalError):
        return True

    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return True

    return False


# =============================================================================
# CSV LOGGING
# =============================================================================

FAILED_ROWS_CSV = LOG_DIR / "failed_rows.csv"
INVALID_COORDS_CSV = LOG_DIR / "invalid_coordinates.csv"
SUMMARY_TXT = LOG_DIR / "etl_summary.txt"


def init_csv_files(reset: bool = True) -> None:
    ensure_log_dir()

    if reset:
        with FAILED_ROWS_CSV.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "source_id",
                "shop_name",
                "manager_name",
                "latitude",
                "longitude",
                "error_type",
                "error_message",
            ])

        with INVALID_COORDS_CSV.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "source_id",
                "shop_name",
                "manager_name",
                "raw_latitude",
                "raw_longitude",
                "reason",
            ])


def append_failed_row(row: RowMapping, exc: Exception) -> None:
    with FAILED_ROWS_CSV.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            row.get("id"),
            row.get("shop_name"),
            row.get("manager_name"),
            row.get("latitude"),
            row.get("longitude"),
            exc.__class__.__name__,
            str(exc),
        ])


def append_invalid_coordinate(row: RowMapping, reason: str) -> None:
    with INVALID_COORDS_CSV.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            row.get("id"),
            row.get("shop_name"),
            row.get("manager_name"),
            row.get("latitude"),
            row.get("longitude"),
            reason,
        ])


def write_summary(stats: Stats, started_at: datetime, finished_at: datetime, last_id: int, mode: str) -> None:
    duration = finished_at - started_at
    lines = [
        f"Started at: {started_at.isoformat()}",
        f"Finished at: {finished_at.isoformat()}",
        f"Duration: {duration}",
        f"Mode: {mode}",
        f"Last successful source id: {last_id}",
        "",
        f"Total read: {stats.total_read}",
        f"Total inserted_or_updated: {stats.total_inserted}",
        f"Total failed: {stats.total_failed}",
        f"Total batches: {stats.total_batches}",
        "",
        f"Valid coordinates: {stats.total_valid_coordinates}",
        f"Invalid coordinates: {stats.total_invalid_coordinates}",
        f"Null coordinates: {stats.total_null_coordinates}",
        f"Zero coordinates: {stats.total_zero_coordinates}",
        f"Unparseable coordinates: {stats.total_unparseable_coordinates}",
        f"Outside/projected coordinates: {stats.total_outside_or_projected_coordinates}",
        "",
        f"Fallback names used: {stats.total_fallback_names}",
        "",
        f"Checkpoint file: {ETL_CHECKPOINT_FILE}",
        f"Failed rows CSV: {FAILED_ROWS_CSV}",
        f"Invalid coordinates CSV: {INVALID_COORDS_CSV}",
    ]
    SUMMARY_TXT.write_text("\n".join(lines), encoding="utf-8")


# =============================================================================
# CHECKPOINT
# =============================================================================

def save_checkpoint(last_id: int, stats: Stats, mode: str) -> None:
    ensure_log_dir()

    checkpoint = Checkpoint(
        job_name=f"{SOURCE_TABLE}_to_{TARGET_TABLE}",
        source_table=SOURCE_TABLE,
        target_table=TARGET_TABLE,
        last_id=last_id,
        total_read=stats.total_read,
        total_inserted=stats.total_inserted,
        total_failed=stats.total_failed,
        total_batches=stats.total_batches,
        updated_at=utcnow().isoformat(),
        mode=mode,
    )

    tmp_path = ETL_CHECKPOINT_FILE.with_suffix(".tmp")
    tmp_path.write_text(
        json.dumps(asdict(checkpoint), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp_path.replace(ETL_CHECKPOINT_FILE)


def load_checkpoint() -> Checkpoint | None:
    if not ETL_CHECKPOINT_FILE.exists():
        return None

    try:
        data = json.loads(ETL_CHECKPOINT_FILE.read_text(encoding="utf-8"))
        return Checkpoint(
            job_name=data["job_name"],
            source_table=data["source_table"],
            target_table=data["target_table"],
            last_id=int(data["last_id"]),
            total_read=int(data["total_read"]),
            total_inserted=int(data["total_inserted"]),
            total_failed=int(data["total_failed"]),
            total_batches=int(data["total_batches"]),
            updated_at=data["updated_at"],
            mode=data.get("mode", "unknown"),
        )
    except Exception as exc:
        log(f"Warning: failed to load checkpoint file {ETL_CHECKPOINT_FILE}: {exc}")
        return None


def delete_checkpoint_if_exists() -> None:
    if ETL_CHECKPOINT_FILE.exists():
        ETL_CHECKPOINT_FILE.unlink()
        log(f"Deleted checkpoint file: {ETL_CHECKPOINT_FILE}")


def get_target_max_legacy_mysql_id(pg_engine: Engine) -> int:
    sql = text(f"SELECT COALESCE(MAX(legacy_mysql_id), 0) FROM {TARGET_TABLE}")
    with pg_engine.connect() as conn:
        result = conn.execute(sql).scalar_one()
    return int(result or 0)


def resolve_start_last_id(pg_engine: Engine) -> tuple[int, str]:
    if ETL_START_AFTER_ID > 0:
        return ETL_START_AFTER_ID, "explicit_start_after_id"

    if TRUNCATE_TARGET_FIRST:
        return 0, "fresh_after_truncate"

    if not ETL_RESUME:
        return 0, "fresh_no_resume"

    checkpoint = load_checkpoint()
    if checkpoint and checkpoint.last_id > 0:
        return checkpoint.last_id, "checkpoint_file"

    if ETL_RESUME_FROM_TARGET_MAX:
        max_id = get_target_max_legacy_mysql_id(pg_engine)
        if max_id > 0:
            return max_id, "target_max_legacy_mysql_id"

    return 0, "resume_start_zero"


# =============================================================================
# SQL
# =============================================================================

def build_source_batch_sql() -> str:
    return f"""
        SELECT
            id,
            shop_name,
            manager_name,
            phone,
            mobile,
            province_id,
            city_id,
            region_id,
            address,
            plaque,
            unit,
            floor,
            latitude,
            longitude,
            postal_code,
            source_type,
            status,
            created_at,
            updated_at
        FROM {SOURCE_TABLE}
        WHERE id > :last_id
        ORDER BY id
        LIMIT :limit
    """


UPSERT_SQL = text(f"""
    INSERT INTO {TARGET_TABLE} (
        legacy_mysql_id,
        canonical_name,
        canonical_phone,
        mobile,
        manager_name,
        address,
        postal_code,
        plaque,
        unit,
        floor,
        province_id,
        city_id,
        district_id,
        latitude,
        longitude,
        master_source,
        is_active,
        created_at,
        updated_at
    )
    VALUES (
        :legacy_mysql_id,
        :canonical_name,
        :canonical_phone,
        :mobile,
        :manager_name,
        :address,
        :postal_code,
        :plaque,
        :unit,
        :floor,
        :province_id,
        :city_id,
        :district_id,
        :latitude,
        :longitude,
        :master_source,
        :is_active,
        :created_at,
        :updated_at
    )
    ON CONFLICT (legacy_mysql_id)
    DO UPDATE SET
        canonical_name = EXCLUDED.canonical_name,
        canonical_phone = EXCLUDED.canonical_phone,
        mobile = EXCLUDED.mobile,
        manager_name = EXCLUDED.manager_name,
        address = EXCLUDED.address,
        postal_code = EXCLUDED.postal_code,
        plaque = EXCLUDED.plaque,
        unit = EXCLUDED.unit,
        floor = EXCLUDED.floor,
        province_id = EXCLUDED.province_id,
        city_id = EXCLUDED.city_id,
        district_id = EXCLUDED.district_id,
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        master_source = EXCLUDED.master_source,
        is_active = EXCLUDED.is_active,
        created_at = COALESCE({TARGET_TABLE}.created_at, EXCLUDED.created_at),
        updated_at = EXCLUDED.updated_at
""")

TRUNCATE_SQL = text(f"TRUNCATE TABLE {TARGET_TABLE} RESTART IDENTITY CASCADE")


# =============================================================================
# TRANSFORM
# =============================================================================

def transform_row(row: RowMapping, stats: Stats) -> tuple[dict[str, Any], str]:
    canonical_name, used_fallback = choose_canonical_name(
        row.get("shop_name"),
        row.get("manager_name"),
        row.get("id"),
    )
    if used_fallback:
        stats.total_fallback_names += 1

    lat, lon, coord_status = normalize_coordinates(
        row.get("latitude"),
        row.get("longitude"),
    )

    if coord_status == "valid":
        stats.total_valid_coordinates += 1
    else:
        stats.total_invalid_coordinates += 1
        if coord_status == "null":
            stats.total_null_coordinates += 1
        elif coord_status == "zero":
            stats.total_zero_coordinates += 1
        elif coord_status == "unparseable":
            stats.total_unparseable_coordinates += 1
        elif coord_status == "outside_or_projected":
            stats.total_outside_or_projected_coordinates += 1

    payload = {
        "legacy_mysql_id": safe_int(row.get("id")),
        "canonical_name": canonical_name,
        "canonical_phone": clean_str(row.get("phone")),
        "mobile": clean_str(row.get("mobile")),
        "manager_name": clean_str(row.get("manager_name")),
        "address": clean_str(row.get("address")),
        "postal_code": clean_str(row.get("postal_code")),
        "plaque": clean_str(row.get("plaque")),
        "unit": clean_str(row.get("unit")),
        "floor": clean_str(row.get("floor")),
        "province_id": safe_int(row.get("province_id")),
        "city_id": safe_int(row.get("city_id")),
        "district_id": safe_int(row.get("region_id")),
        "latitude": lat if coord_status == "valid" else None,
        "longitude": lon if coord_status == "valid" else None,
        "master_source": clean_str(row.get("source_type")),
        "is_active": clean_bool_from_status(row.get("status")),
        "created_at": row.get("created_at") or utcnow(),
        "updated_at": row.get("updated_at") or utcnow(),
    }

    if payload["legacy_mysql_id"] is None:
        raise ValueError("source row id is null or invalid; cannot populate legacy_mysql_id")

    return payload, coord_status


# =============================================================================
# SIGNAL HANDLING
# =============================================================================

def handle_stop_signal(signum, frame) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True
    log(f"Received signal {signum}. Graceful stop requested; current batch will finish first.")


def install_signal_handlers() -> None:
    signal.signal(signal.SIGINT, handle_stop_signal)
    signal.signal(signal.SIGTERM, handle_stop_signal)


# =============================================================================
# BATCH IO
# =============================================================================

SOURCE_BATCH_SQL = text(build_source_batch_sql())


def fetch_source_batch(mysql_engine: Engine, last_id: int, batch_size: int) -> list[RowMapping]:
    last_exc: Exception | None = None

    for attempt in range(1, ETL_MAX_RETRIES + 1):
        try:
            with mysql_engine.connect() as conn:
                rows = conn.execute(
                    SOURCE_BATCH_SQL,
                    {"last_id": last_id, "limit": batch_size},
                ).mappings().all()
                return rows

        except Exception as exc:
            last_exc = exc
            retryable = is_retryable_mysql_exception(exc)

            if attempt < ETL_MAX_RETRIES and retryable:
                log(
                    f"MySQL batch fetch failed (attempt {attempt}/{ETL_MAX_RETRIES}) "
                    f"after last_id={last_id}: {exc}. Retrying in {ETL_RETRY_DELAY_SECONDS}s ..."
                )
                time.sleep(ETL_RETRY_DELAY_SECONDS)
                continue

            raise

    if last_exc:
        raise last_exc

    return []


def upsert_batch(pg_engine: Engine, batch: list[dict[str, Any]]) -> None:
    with pg_engine.begin() as conn:
        conn.execute(UPSERT_SQL, batch)


# =============================================================================
# MAIN ETL
# =============================================================================

def run() -> int:
    started_at = utcnow()
    stats = Stats()
    last_successful_id = 0
    mode = "resume" if ETL_RESUME else "fresh"

    ensure_log_dir()
    install_signal_handlers()

    # برای سادگی فعلاً در هر اجرا فایل‌های CSV از نو ساخته می‌شوند.
    init_csv_files(reset=True)

    mysql_engine = create_mysql_engine()
    pg_engine = create_postgres_engine()

    log("Starting ETL migration: MySQL -> PostgreSQL")
    log(f"MySQL DB: {MYSQL_DB} @ {MYSQL_HOST}:{MYSQL_PORT}")
    log(f"PostgreSQL DB: {POSTGRES_DB} @ {POSTGRES_HOST}:{POSTGRES_PORT}")
    log(f"Batch size: {BATCH_SIZE}")
    log(f"Source table: {SOURCE_TABLE}")
    log(f"Target table: {TARGET_TABLE}")
    log("Model: B (PostgreSQL id is internal, MySQL id -> legacy_mysql_id)")
    log(f"Resume enabled: {ETL_RESUME}")
    log(f"Resume from target MAX enabled: {ETL_RESUME_FROM_TARGET_MAX}")
    log(f"Checkpoint file: {ETL_CHECKPOINT_FILE}")
    log(f"Max retries per source batch: {ETL_MAX_RETRIES}")
    log(f"Retry delay seconds: {ETL_RETRY_DELAY_SECONDS}")
    if LIMIT_ROWS > 0:
        log(f"Run row limit: {LIMIT_ROWS}")

    try:
        validate_source_schema(mysql_engine)

        ensure_mobile_column(pg_engine, TARGET_TABLE)
        ensure_legacy_mysql_id_column(pg_engine, TARGET_TABLE)
        validate_target_schema(pg_engine)

        if TRUNCATE_TARGET_FIRST:
            log(f"Truncating target table: {TARGET_TABLE}")
            with pg_engine.begin() as conn:
                conn.execute(TRUNCATE_SQL)

            delete_checkpoint_if_exists()
            last_successful_id = 0
            log("Fresh mode after truncate: start_after_id=0")
        else:
            last_successful_id, start_reason = resolve_start_last_id(pg_engine)
            log(f"Resolved start_after_id={last_successful_id} via {start_reason}")

        rows_processed_this_run = 0

        while True:
            if STOP_REQUESTED:
                log("Stop requested before fetching next batch. Exiting gracefully.")
                save_checkpoint(last_successful_id, stats, mode)
                break

            if LIMIT_ROWS > 0:
                remaining = LIMIT_ROWS - rows_processed_this_run
                if remaining <= 0:
                    log(f"Reached ETL_LIMIT_ROWS={LIMIT_ROWS}. Stopping normally.")
                    save_checkpoint(last_successful_id, stats, mode)
                    break
                current_batch_size = min(BATCH_SIZE, remaining)
            else:
                current_batch_size = BATCH_SIZE

            rows = fetch_source_batch(
                mysql_engine=mysql_engine,
                last_id=last_successful_id,
                batch_size=current_batch_size,
            )

            if not rows:
                log("No more source rows found. ETL completed.")
                save_checkpoint(last_successful_id, stats, mode)
                break

            batch_payloads: list[dict[str, Any]] = []
            batch_last_id = last_successful_id

            for row in rows:
                stats.total_read += 1
                rows_processed_this_run += 1

                try:
                    payload, coord_status = transform_row(row, stats)

                    if coord_status != "valid":
                        append_invalid_coordinate(row, coord_status)

                    batch_payloads.append(payload)

                    source_row_id = safe_int(row.get("id"))
                    if source_row_id is not None and source_row_id > batch_last_id:
                        batch_last_id = source_row_id

                except Exception as row_exc:
                    stats.total_failed += 1
                    append_failed_row(row, row_exc)
                    log(f"Row failed: source_id={row.get('id')} error={row_exc}")
                    continue

            if batch_payloads:
                upsert_batch(pg_engine, batch_payloads)
                stats.total_inserted += len(batch_payloads)

            last_successful_id = batch_last_id
            stats.total_batches += 1

            save_checkpoint(last_successful_id, stats, mode)

            log(
                f"Upserted batch: {len(batch_payloads)} | "
                f"last_id={last_successful_id} "
                f"read={stats.total_read} upserted={stats.total_inserted} "
                f"failed={stats.total_failed} valid_coords={stats.total_valid_coordinates} "
                f"batches={stats.total_batches}"
            )

            if STOP_REQUESTED:
                log("Stop requested after successful batch. Checkpoint saved; exiting gracefully.")
                break

    except Exception as exc:
        log("ETL crashed with fatal error:")
        log(str(exc))
        traceback.print_exc()

        try:
            save_checkpoint(last_successful_id, stats, mode)
            log(f"Checkpoint saved at last_successful_id={last_successful_id}")
        except Exception as checkpoint_exc:
            log(f"Failed to save checkpoint after crash: {checkpoint_exc}")

        finished_at = utcnow()
        write_summary(stats, started_at, finished_at, last_successful_id, mode)
        return 1

    finished_at = utcnow()
    write_summary(stats, started_at, finished_at, last_successful_id, mode)

    log("ETL completed successfully.")
    log(f"Last successful source id: {last_successful_id}")
    log(f"Total read: {stats.total_read}")
    log(f"Total upserted: {stats.total_inserted}")
    log(f"Total failed: {stats.total_failed}")
    log(f"Total batches: {stats.total_batches}")
    log(f"Valid coordinates: {stats.total_valid_coordinates}")
    log(f"Invalid coordinates: {stats.total_invalid_coordinates}")
    log(f"Fallback names used: {stats.total_fallback_names}")
    log(f"Checkpoint file: {ETL_CHECKPOINT_FILE}")
    log(f"Logs written to: {LOG_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(run())

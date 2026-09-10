#!/usr/bin/env python3
"""
Migration script for geographic data from MySQL (fishopping_supermarket)
to PostgreSQL (distribution_intelligence).

Migrates:
    provinces -> cities -> regions

Features:
- Reads connection settings from .env
- Migrates only common columns
- Uses safe SQL identifiers
- Handles NULL updated_at
- Normalizes latitude / longitude
- Validates Iran geographic coordinate ranges
- Preserves NULL coordinates instead of generating fake coordinates
- Reports missing / invalid coordinates
- Preserves foreign-key order
- Validates foreign-key integrity
- Updates PostgreSQL sequences after migration
- Uses ON CONFLICT DO NOTHING for safe re-runs
"""

import os
import sys
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime

from dotenv import load_dotenv
import pymysql
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


# ============================================================
# Environment
# ============================================================

def load_env():
    """
    Load environment variables from .env.
    """
    load_dotenv()


# ============================================================
# Database connections
# ============================================================

def get_mysql_connection():
    load_env()

    try:
        conn = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "host.docker.internal"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER", "fishopping_supermarket"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DB", "fishopping_supermarket"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

        logger.info(
            "✅ Connected to MySQL at %s:%s",
            os.getenv("MYSQL_HOST", "host.docker.internal"),
            os.getenv("MYSQL_PORT", "3306"),
        )

        return conn

    except Exception as exc:
        logger.error("❌ Failed to connect to MySQL: %s", exc)
        raise


def get_postgres_connection():
    load_env()

    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            database=os.getenv(
                "POSTGRES_DB",
                "distribution_intelligence",
            ),
            user=os.getenv(
                "POSTGRES_USER",
                "distribution_user",
            ),
            password=os.getenv(
                "POSTGRES_PASSWORD",
                "distribution_pass",
            ),
        )

        conn.autocommit = False

        logger.info(
            "✅ Connected to PostgreSQL at %s:%s",
            os.getenv("POSTGRES_HOST", "postgres"),
            os.getenv("POSTGRES_PORT", "5432"),
        )

        return conn

    except Exception as exc:
        logger.error("❌ Failed to connect to PostgreSQL: %s", exc)
        raise


# ============================================================
# Coordinate helpers
# ============================================================

# Approximate bounding box for Iran.
#
# This is intentionally used as a validation range, not
# as a replacement for actual geographic validation.
#
# latitude  : 24 .. 40
# longitude : 44 .. 64
#
IRAN_LAT_MIN = Decimal("24")
IRAN_LAT_MAX = Decimal("40")

IRAN_LON_MIN = Decimal("44")
IRAN_LON_MAX = Decimal("64")


def normalize_coordinate(value):
    """
    Convert a coordinate value safely to Decimal.

    Returns:
        Decimal or None
    """

    if value is None:
        return None

    # Handle strings
    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        # Normalize Persian/Arabic digits.
        translation_table = str.maketrans(
            "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
            "01234567890123456789",
        )

        value = value.translate(translation_table)

    try:
        coordinate = Decimal(str(value))

    except (InvalidOperation, ValueError, TypeError):
        return None

    return coordinate


def is_valid_iran_coordinate(latitude, longitude):
    """
    Validate a latitude/longitude pair against the broad Iran range.

    This function does NOT claim that a coordinate belongs to
    a specific city. It only checks that it is numerically
    plausible for Iran.
    """

    if latitude is None or longitude is None:
        return False

    return (
        IRAN_LAT_MIN <= latitude <= IRAN_LAT_MAX
        and
        IRAN_LON_MIN <= longitude <= IRAN_LON_MAX
    )


def fix_row_values(row):
    """
    Normalize row values before insertion.

    Rules:
    - updated_at NULL -> created_at or current datetime
    - latitude/longitude -> Decimal
    - invalid coordinate strings -> NULL
    """

    # --------------------------------------------------------
    # updated_at
    # --------------------------------------------------------

    if row.get("updated_at") is None:
        row["updated_at"] = (
            row.get("created_at")
            or datetime.now()
        )

    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    latitude = normalize_coordinate(
        row.get("latitude")
    )

    longitude = normalize_coordinate(
        row.get("longitude")
    )

    row["latitude"] = latitude
    row["longitude"] = longitude

    return row


# ============================================================
# Schema helpers
# ============================================================

def get_mysql_columns(cursor, table_name):
    """
    Return MySQL column names.
    """

    cursor.execute(
        f"SHOW COLUMNS FROM `{table_name}`"
    )

    return [
        col["Field"]
        for col in cursor.fetchall()
    ]


def get_postgres_columns(cursor, table_name):
    """
    Return PostgreSQL column names.
    """

    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )

    return [
        row[0]
        for row in cursor.fetchall()
    ]


def get_postgres_primary_key(
    cursor,
    table_name,
):
    """
    Return primary-key column name.
    """

    cursor.execute(
        """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = 'public'
          AND tc.table_name = %s
        ORDER BY kcu.ordinal_position
        """,
        (table_name,),
    )

    rows = cursor.fetchall()

    return rows[0][0] if rows else "id"


def get_postgres_sequence_name(
    cursor,
    table_name,
    pk_column="id",
):
    """
    Find PostgreSQL sequence associated with a serial/identity column.
    """

    cursor.execute(
        """
        SELECT pg_get_serial_sequence(%s, %s)
        """,
        (table_name, pk_column),
    )

    row = cursor.fetchone()

    return row[0] if row else None


# ============================================================
# Coordinate statistics
# ============================================================

def analyze_coordinate_rows(
    rows,
    table_name,
):
    """
    Analyze coordinate quality before insertion.

    Only meaningful for tables containing latitude/longitude.
    """

    if not rows:
        return

    has_latitude = "latitude" in rows[0]
    has_longitude = "longitude" in rows[0]

    if not has_latitude or not has_longitude:
        return

    missing_latitude = 0
    missing_longitude = 0
    missing_pair = 0
    invalid_pair = 0
    valid_pair = 0

    invalid_examples = []

    for row in rows:

        latitude = row.get("latitude")
        longitude = row.get("longitude")

        if latitude is None:
            missing_latitude += 1

        if longitude is None:
            missing_longitude += 1

        if latitude is None or longitude is None:
            missing_pair += 1
            continue

        if is_valid_iran_coordinate(
            latitude,
            longitude,
        ):
            valid_pair += 1

        else:
            invalid_pair += 1

            if len(invalid_examples) < 10:
                invalid_examples.append(
                    {
                        "id": row.get("id"),
                        "name": row.get("name"),
                        "latitude": latitude,
                        "longitude": longitude,
                    }
                )

    logger.info(
        "🗺️ Coordinate report for %s:",
        table_name,
    )

    logger.info(
        "   Total rows: %s",
        len(rows),
    )

    logger.info(
        "   Missing latitude: %s",
        missing_latitude,
    )

    logger.info(
        "   Missing longitude: %s",
        missing_longitude,
    )

    logger.info(
        "   Missing coordinate pair: %s",
        missing_pair,
    )

    logger.info(
        "   Valid Iran-range pairs: %s",
        valid_pair,
    )

    logger.info(
        "   Invalid/out-of-range pairs: %s",
        invalid_pair,
    )

    if invalid_examples:

        logger.warning(
            "⚠️ First invalid coordinate examples:"
        )

        for item in invalid_examples:
            logger.warning(
                "   id=%s | name=%s | lat=%s | lon=%s",
                item["id"],
                item["name"],
                item["latitude"],
                item["longitude"],
            )


# ============================================================
# Migration
# ============================================================

def migrate_table(
    mysql_cursor,
    pg_cursor,
    table_name,
    pg_table_name=None,
):
    """
    Migrate one table from MySQL to PostgreSQL.

    Uses only common columns.

    Returns:
        number of source rows processed
    """

    if pg_table_name is None:
        pg_table_name = table_name

    logger.info(
        "📦 Processing %s -> %s",
        table_name,
        pg_table_name,
    )

    # --------------------------------------------------------
    # Get schema information
    # --------------------------------------------------------

    mysql_columns = get_mysql_columns(
        mysql_cursor,
        table_name,
    )

    pg_columns = get_postgres_columns(
        pg_cursor,
        pg_table_name,
    )

    logger.info(
        "   MySQL columns: %s",
        ", ".join(mysql_columns),
    )

    logger.info(
        "   PostgreSQL columns: %s",
        ", ".join(pg_columns),
    )

    # --------------------------------------------------------
    # Common columns
    # --------------------------------------------------------

    common_columns = [
        col
        for col in mysql_columns
        if col in pg_columns
    ]

    if not common_columns:

        logger.error(
            "❌ No common columns between "
            "MySQL.%s and PostgreSQL.%s",
            table_name,
            pg_table_name,
        )

        return 0

    logger.info(
        "   Common columns: %s",
        ", ".join(common_columns),
    )

    # --------------------------------------------------------
    # Read MySQL
    # --------------------------------------------------------

    select_query = (
        "SELECT {} FROM `{}`"
    ).format(
        ", ".join(
            f"`{col}`"
            for col in common_columns
        ),
        table_name,
    )

    try:

        mysql_cursor.execute(
            select_query
        )

        rows = mysql_cursor.fetchall()

        logger.info(
            "📥 Fetched %s rows from MySQL.%s",
            len(rows),
            table_name,
        )

    except Exception as exc:

        logger.error(
            "❌ Error fetching from MySQL.%s: %s",
            table_name,
            exc,
        )

        return 0

    if not rows:

        logger.warning(
            "⚠️ No data fetched for %s, skipping",
            table_name,
        )

        return 0

    # --------------------------------------------------------
    # Normalize rows
    # --------------------------------------------------------

    prepared_rows = []

    for row in rows:

        fixed_row = fix_row_values(row)

        prepared_rows.append(
            fixed_row
        )

    # --------------------------------------------------------
    # Coordinate quality report
    # --------------------------------------------------------

    analyze_coordinate_rows(
        prepared_rows,
        table_name,
    )

    # --------------------------------------------------------
    # Prepare values
    # --------------------------------------------------------

    values = [
        tuple(
            row.get(column)
            for column in common_columns
        )
        for row in prepared_rows
    ]

    if not values:
        return 0

    # --------------------------------------------------------
    # INSERT
    # --------------------------------------------------------

    insert_sql = sql.SQL(
        """
        INSERT INTO {} ({})
        VALUES %s
        ON CONFLICT DO NOTHING
        """
    ).format(
        sql.Identifier(pg_table_name),
        sql.SQL(", ").join(
            sql.Identifier(column)
            for column in common_columns
        ),
    )

    try:

        execute_values(
            pg_cursor,
            insert_sql.as_string(
                pg_cursor.connection
            ),
            values,
        )

        inserted_count = pg_cursor.rowcount

        logger.info(
            "📤 PostgreSQL affected rows for %s: %s",
            pg_table_name,
            inserted_count,
        )

        # ----------------------------------------------------
        # Update sequence
        # ----------------------------------------------------

        pk_column = get_postgres_primary_key(
            pg_cursor,
            pg_table_name,
        )

        sequence_name = get_postgres_sequence_name(
            pg_cursor,
            pg_table_name,
            pk_column,
        )

        if sequence_name:

            sequence_sql = sql.SQL(
                """
                SELECT setval(
                    %s,
                    COALESCE(
                        (SELECT MAX({}) FROM {}),
                        1
                    ),
                    true
                )
                """
            ).format(
                sql.Identifier(pk_column),
                sql.Identifier(pg_table_name),
            )

            pg_cursor.execute(
                sequence_sql.as_string(
                    pg_cursor.connection
                ),
                (sequence_name,),
            )

            logger.info(
                "🔢 Sequence updated for %s.%s",
                pg_table_name,
                pk_column,
            )

        return len(rows)

    except Exception as exc:

        logger.error(
            "❌ Error inserting into PostgreSQL.%s: %s",
            pg_table_name,
            exc,
        )

        logger.error(
            "   Showing first 3 problematic rows:"
        )

        for idx, row in enumerate(
            prepared_rows[:3]
        ):
            logger.error(
                "   Row %s: %s",
                idx,
                row,
            )

        raise


# ============================================================
# Foreign key validation
# ============================================================

def validate_foreign_keys(pg_cursor):
    """
    Validate geographic foreign-key relationships.
    """

    logger.info(
        "🔗 Validating foreign key integrity..."
    )

    checks = [
        (
            "cities",
            "province_id",
            "provinces",
            "id",
        ),
        (
            "regions",
            "city_id",
            "cities",
            "id",
        ),
    ]

    for (
        child_table,
        child_col,
        parent_table,
        parent_col,
    ) in checks:

        query = sql.SQL(
            """
            SELECT COUNT(*)
            FROM {} c
            WHERE c.{} IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM {} p
                  WHERE p.{} = c.{}
              )
            """
        ).format(
            sql.Identifier(child_table),
            sql.Identifier(child_col),
            sql.Identifier(parent_table),
            sql.Identifier(parent_col),
            sql.Identifier(child_col),
        )

        pg_cursor.execute(
            query.as_string(
                pg_cursor.connection
            )
        )

        invalid_count = (
            pg_cursor.fetchone()[0]
        )

        if invalid_count == 0:

            logger.info(
                "✅ All %s rows have valid "
                "%s references",
                child_table,
                parent_table,
            )

        else:

            logger.warning(
                "⚠️ %s %s rows have invalid "
                "%s references",
                invalid_count,
                child_table,
                parent_table,
            )


# ============================================================
# PostgreSQL counts
# ============================================================

def get_postgres_count(
    pg_cursor,
    table_name,
):
    """
    Return PostgreSQL table row count.
    """

    query = sql.SQL(
        "SELECT COUNT(*) FROM {}"
    ).format(
        sql.Identifier(table_name)
    )

    pg_cursor.execute(
        query.as_string(
            pg_cursor.connection
        )
    )

    return pg_cursor.fetchone()[0]


# ============================================================
# Coordinate validation after migration
# ============================================================

def validate_postgres_coordinates(
    pg_cursor,
):
    """
    Final coordinate validation directly on PostgreSQL.
    """

    logger.info(
        "🗺️ Validating coordinates in PostgreSQL..."
    )

    # --------------------------------------------------------
    # Missing coordinates
    # --------------------------------------------------------

    pg_cursor.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN latitude IS NULL
                    THEN 1
                    ELSE 0
                END
            ) AS empty_latitude,
            SUM(
                CASE
                    WHEN longitude IS NULL
                    THEN 1
                    ELSE 0
                END
            ) AS empty_longitude
        FROM cities
        """
    )

    total, empty_latitude, empty_longitude = (
        pg_cursor.fetchone()
    )

    logger.info(
        "   cities total: %s",
        total,
    )

    logger.info(
        "   cities missing latitude: %s",
        empty_latitude or 0,
    )

    logger.info(
        "   cities missing longitude: %s",
        empty_longitude or 0,
    )

    # --------------------------------------------------------
    # Out-of-Iran coordinates
    # --------------------------------------------------------

    pg_cursor.execute(
        """
        SELECT COUNT(*)
        FROM cities
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
          AND (
              latitude < %s
              OR latitude > %s
              OR longitude < %s
              OR longitude > %s
          )
        """,
        (
            IRAN_LAT_MIN,
            IRAN_LAT_MAX,
            IRAN_LON_MIN,
            IRAN_LON_MAX,
        ),
    )

    invalid_count = pg_cursor.fetchone()[0]

    if invalid_count == 0:

        logger.info(
            "✅ No city coordinates are outside "
            "the Iran validation range"
        )

    else:

        logger.warning(
            "⚠️ %s city coordinate pairs are "
            "outside the Iran validation range",
            invalid_count,
        )

        pg_cursor.execute(
            """
            SELECT
                id,
                name,
                latitude,
                longitude
            FROM cities
            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL
              AND (
                  latitude < %s
                  OR latitude > %s
                  OR longitude < %s
                  OR longitude > %s
              )
            ORDER BY id
            LIMIT 20
            """,
            (
                IRAN_LAT_MIN,
                IRAN_LAT_MAX,
                IRAN_LON_MIN,
                IRAN_LON_MAX,
            ),
        )

        rows = pg_cursor.fetchall()

        for row in rows:

            logger.warning(
                "   id=%s | name=%s | lat=%s | lon=%s",
                row[0],
                row[1],
                row[2],
                row[3],
            )


# ============================================================
# Final geographic summary
# ============================================================

def print_final_summary(
    pg_cursor,
):
    """
    Print final PostgreSQL migration summary.
    """

    logger.info(
        "============================================================"
    )

    logger.info(
        "📊 FINAL POSTGRESQL SUMMARY"
    )

    logger.info(
        "============================================================"
    )

    for table in (
        "provinces",
        "cities",
        "regions",
    ):

        count = get_postgres_count(
            pg_cursor,
            table,
        )

        logger.info(
            "   %-12s : %s rows",
            table,
            count,
        )

    # --------------------------------------------------------
    # Cities with coordinates
    # --------------------------------------------------------

    pg_cursor.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN latitude IS NOT NULL
                     AND longitude IS NOT NULL
                    THEN 1
                    ELSE 0
                END
            ) AS complete_coordinates,
            SUM(
                CASE
                    WHEN latitude IS NULL
                      OR longitude IS NULL
                    THEN 1
                    ELSE 0
                END
            ) AS missing_coordinates
        FROM cities
        """
    )

    (
        total_cities,
        complete_coordinates,
        missing_coordinates,
    ) = pg_cursor.fetchone()

    logger.info(
        "   cities with coordinates : %s",
        complete_coordinates or 0,
    )

    logger.info(
        "   cities missing coordinates : %s",
        missing_coordinates or 0,
    )

    logger.info(
        "============================================================"
    )


# ============================================================
# Main
# ============================================================

def main():

    logger.info(
        "🚀 Starting geographic data migration "
        "from MySQL to PostgreSQL"
    )

    logger.info(
        "============================================================"
    )

    mysql_conn = None
    pg_conn = None

    try:

        # ----------------------------------------------------
        # Connections
        # ----------------------------------------------------

        mysql_conn = get_mysql_connection()
        pg_conn = get_postgres_connection()

        mysql_cursor = mysql_conn.cursor()
        pg_cursor = pg_conn.cursor()

        counts = {}

        # ----------------------------------------------------
        # Migration order
        #
        # provinces -> cities -> regions
        # ----------------------------------------------------

        counts["provinces"] = migrate_table(
            mysql_cursor,
            pg_cursor,
            "provinces",
        )

        counts["cities"] = migrate_table(
            mysql_cursor,
            pg_cursor,
            "cities",
        )

        counts["regions"] = migrate_table(
            mysql_cursor,
            pg_cursor,
            "regions",
        )

        # ----------------------------------------------------
        # Validate FK relationships
        # ----------------------------------------------------

        validate_foreign_keys(
            pg_cursor
        )

        # ----------------------------------------------------
        # Validate coordinates
        # ----------------------------------------------------

        validate_postgres_coordinates(
            pg_cursor
        )

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        pg_conn.commit()

        logger.info(
            "✅ Transaction committed"
        )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        logger.info(
            "============================================================"
        )

        logger.info(
            "🎉 Geographic data migration completed!"
        )

        logger.info(
            "📊 Source rows processed:"
        )

        for table, count in counts.items():

            logger.info(
                "   %-12s : %s",
                table,
                count,
            )

        print_final_summary(
            pg_cursor
        )

    except Exception as exc:

        logger.error(
            "❌ Migration failed: %s",
            exc,
        )

        if pg_conn:

            pg_conn.rollback()

            logger.info(
                "🔄 Transaction rolled back"
            )

        raise

    finally:

        if mysql_conn:

            mysql_conn.close()

            logger.info(
                "✅ MySQL connection closed"
            )

        if pg_conn:

            pg_conn.close()

            logger.info(
                "✅ PostgreSQL connection closed"
            )

    logger.info(
        "📁 Script finished. "
        "You can now verify the geographic data manually."
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    main()
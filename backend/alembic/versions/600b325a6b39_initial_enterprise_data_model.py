"""Initial Enterprise Data Model

Revision ID: 600b325a6b39
Revises:
Create Date: 2026-07-23 10:43:04.680074

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = "600b325a6b39"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # -------------------------------------------------------------------------
    # ACCOUNTS
    # -------------------------------------------------------------------------
    op.create_table(
        "accounts",
        sa.Column("mobile", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_accounts_mobile"),
        "accounts",
        ["mobile"],
        unique=True,
    )

    # -------------------------------------------------------------------------
    # FILES
    # -------------------------------------------------------------------------
    op.create_table(
        "files",
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("original_name", sa.String(length=500), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_name"),
    )

    op.create_index(
        op.f("ix_files_category"),
        "files",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_files_entity_id"),
        "files",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_files_entity_type"),
        "files",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_files_uploaded_by"),
        "files",
        ["uploaded_by"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # STORES
    # -------------------------------------------------------------------------
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("canonical_phone", sa.String(length=20), nullable=True),
        sa.Column("canonical_category", sa.String(length=100), nullable=True),
        sa.Column("shop_type", sa.String(length=50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("postal_code", sa.String(length=10), nullable=True),
        sa.Column("plaque", sa.String(length=20), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=True),
        sa.Column("floor", sa.String(length=20), nullable=True),
        sa.Column("province_id", sa.Integer(), nullable=True),
        sa.Column("county_id", sa.Integer(), nullable=True),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column("neighborhood_id", sa.Integer(), nullable=True),
        sa.Column("village_id", sa.Integer(), nullable=True),
        sa.Column("province_name", sa.String(length=100), nullable=True),
        sa.Column("county_name", sa.String(length=100), nullable=True),
        sa.Column("city_name", sa.String(length=100), nullable=True),
        sa.Column("district_name", sa.String(length=100), nullable=True),
        sa.Column("neighborhood_name", sa.String(length=100), nullable=True),
        sa.Column("village_name", sa.String(length=100), nullable=True),
        sa.Column(
            "latitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "longitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "confidence_score",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
        sa.Column(
            "matching_status",
            sa.String(length=20),
            nullable=True,
        ),
        sa.Column(
            "master_source",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "fimap_token",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_stores_canonical_name"),
        "stores",
        ["canonical_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stores_city_id"),
        "stores",
        ["city_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stores_fimap_token"),
        "stores",
        ["fimap_token"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stores_id"),
        "stores",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stores_is_active"),
        "stores",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stores_matching_status"),
        "stores",
        ["matching_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stores_province_id"),
        "stores",
        ["province_id"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # COMPANIES
    # -------------------------------------------------------------------------
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=True),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("national_id", sa.String(length=50), nullable=True),
        sa.Column("economic_code", sa.String(length=50), nullable=True),
        sa.Column(
            "registration_number",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("mobile", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("province", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("postal_code", sa.String(length=10), nullable=True),
        sa.Column("max_projects", sa.Integer(), nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_companies_account_id"),
        "companies",
        ["account_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_companies_code"),
        "companies",
        ["code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companies_email"),
        "companies",
        ["email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companies_id"),
        "companies",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companies_is_active"),
        "companies",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companies_mobile"),
        "companies",
        ["mobile"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companies_name"),
        "companies",
        ["name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companies_national_id"),
        "companies",
        ["national_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_companies_slug"),
        "companies",
        ["slug"],
        unique=True,
    )

    # -------------------------------------------------------------------------
    # IMPORT BATCHES
    # -------------------------------------------------------------------------
    op.create_table(
        "import_batches",
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column(
            "entity_type",
            sa.Enum(
                "ORDER",
                "FLEET",
                "DRIVER",
                "STORE",
                "GPS",
                name="entitytype",
                native_enum=False,
                length=50,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PROCESSING",
                "COMPLETED",
                "COMPLETED_WITH_ERRORS",
                "FAILED",
                name="importstatus",
                native_enum=False,
                length=50,
            ),
            nullable=False,
        ),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("valid_rows", sa.Integer(), nullable=False),
        sa.Column("error_rows", sa.Integer(), nullable=False),
        sa.Column("imported_rows", sa.Integer(), nullable=False),
        sa.Column(
            "error_log",
            sa.JSON(),
            nullable=True,
            comment="DEPRECATED — use row_errors relationship instead",
        ),
        sa.Column("column_mapping", sa.JSON(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["files.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_import_batches_entity_type"),
        "import_batches",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_batches_file_id"),
        "import_batches",
        ["file_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_batches_status"),
        "import_batches",
        ["status"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # STORE LOCATIONS
    # -------------------------------------------------------------------------
    op.create_table(
        "store_locations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column(
            "canonical_address",
            sa.Text(),
            nullable=True,
        ),
        sa.Column("postal_code", sa.String(length=10), nullable=True),
        sa.Column("province_id", sa.Integer(), nullable=True),
        sa.Column("county_id", sa.Integer(), nullable=True),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("district_id", sa.Integer(), nullable=True),
        sa.Column("neighborhood_id", sa.Integer(), nullable=True),
        sa.Column("village_id", sa.Integer(), nullable=True),
        sa.Column(
            "latitude",
            sa.Numeric(precision=10, scale=7),
            nullable=False,
        ),
        sa.Column(
            "longitude",
            sa.Numeric(precision=10, scale=7),
            nullable=False,
        ),
        sa.Column(
            "geohash",
            sa.String(length=20),
            nullable=True,
        ),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                spatial_index=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "geometry_type",
            sa.String(length=20),
            nullable=True,
        ),
        sa.Column("srid", sa.Integer(), nullable=False),
        sa.Column(
            "validation_source",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "validation_score",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
        sa.Column(
            "confidence",
            sa.Numeric(precision=5, scale=4),
            nullable=True,
        ),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_store_locations_geometry",
        "store_locations",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        op.f("ix_store_locations_city_id"),
        "store_locations",
        ["city_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_store_locations_geohash"),
        "store_locations",
        ["geohash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_store_locations_id"),
        "store_locations",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_store_locations_is_current"),
        "store_locations",
        ["is_current"],
        unique=False,
    )
    op.create_index(
        op.f("ix_store_locations_province_id"),
        "store_locations",
        ["province_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_store_locations_store_id"),
        "store_locations",
        ["store_id"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # COMPANY STORES
    # -------------------------------------------------------------------------
    op.create_table(
        "company_stores",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            comment="مالک اصلی CompanyStore",
        ),
        sa.Column(
            "master_store_id",
            sa.Integer(),
            nullable=True,
            comment=(
                "لینک به Master Store در Enterprise Truth Layer. "
                "NULL یعنی هنوز به Master Store متصل نشده است."
            ),
        ),
        sa.Column(
            "store_code",
            sa.String(length=128),
            nullable=False,
            comment="کد فروشگاه در سیستم شرکت (Company-provided Store Code)",
        ),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("address", sa.String(length=2000), nullable=True),
        sa.Column("province", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column(
            "location_confidence",
            sa.Enum(
                "EXACT",
                "DISTRICT",
                "CITY",
                "UNKNOWN",
                name="locationconfidence",
            ),
            nullable=True,
        ),
        sa.Column(
            "coordinate_source",
            sa.Enum(
                "GPS",
                "MANUAL",
                "GEOCODE",
                "REPOSITORY",
                "IMPORTED",
                "UNKNOWN",
                name="coordinatesource",
            ),
            nullable=True,
        ),
        sa.Column(
            "location_source",
            sa.Enum(
                "GPS",
                "NORMALIZER",
                "MANUAL",
                "IMPORT",
                "MASTER",
                name="locationsource",
            ),
            nullable=True,
            comment=(
                "MASTER = inherited from master_store; "
                "MANUAL = manually assigned; "
                "other values according to LocationSource enum"
            ),
        ),
        sa.Column(
            "match_status",
            sa.Enum(
                "PENDING",
                "PRECISE",
                "MATCHED",
                "SUGGESTED",
                "UNMATCHED",
                "LOCATED",
                "UNRESOLVED",
                name="matchstatus",
            ),
            nullable=False,
            comment=(
                "7-value DB enum. Business logic exposed through "
                "is_matched / is_located / is_unresolved."
            ),
        ),
        sa.Column(
            "status",
            sa.Enum(
                "ENABLE",
                "DISABLE",
                name="storestatus",
            ),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["master_store_id"],
            ["stores.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "store_code",
            name="uq_company_store_code",
        ),
    )

    op.create_index(
        op.f("ix_company_stores_city"),
        "company_stores",
        ["city"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_stores_company_id"),
        "company_stores",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_stores_coordinate_source"),
        "company_stores",
        ["coordinate_source"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_stores_district"),
        "company_stores",
        ["district"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_stores_location_confidence"),
        "company_stores",
        ["location_confidence"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_stores_location_source"),
        "company_stores",
        ["location_source"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_stores_master_store_id"),
        "company_stores",
        ["master_store_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_stores_match_status"),
        "company_stores",
        ["match_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_stores_phone"),
        "company_stores",
        ["phone"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_stores_province"),
        "company_stores",
        ["province"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_stores_status"),
        "company_stores",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_company_stores_store_code"),
        "company_stores",
        ["store_code"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # DRIVERS
    # -------------------------------------------------------------------------
    op.create_table(
        "drivers",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            comment="Company مالک این Driver",
        ),
        sa.Column(
            "import_batch_id",
            sa.Integer(),
            nullable=True,
            comment="آخرین ImportBatch که این Driver از آن وارد شده است",
        ),
        sa.Column(
            "driver_code",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "first_name",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "last_name",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column(
            "license_number",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "license_expiry",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "experience_years",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "latitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "longitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "raw_data",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "error_note",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "driver_code",
            name="uq_drivers_company_driver_code",
        ),
    )

    op.create_index(
        op.f("ix_drivers_company_id"),
        "drivers",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_drivers_driver_code"),
        "drivers",
        ["driver_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_drivers_import_batch_id"),
        "drivers",
        ["import_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_drivers_phone"),
        "drivers",
        ["phone"],
        unique=False,
    )
    op.create_index(
        op.f("ix_drivers_status"),
        "drivers",
        ["status"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # GPS RECORDS
    # -------------------------------------------------------------------------
    op.create_table(
        "gps_records",
        sa.Column(
            "import_batch_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "vehicle_plate",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "latitude",
            sa.Numeric(precision=10, scale=7),
            nullable=False,
        ),
        sa.Column(
            "longitude",
            sa.Numeric(precision=10, scale=7),
            nullable=False,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "speed_kmh",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "heading",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "accuracy_m",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "raw_data",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "error_note",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_gps_records_import_batch_id"),
        "gps_records",
        ["import_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gps_records_timestamp"),
        "gps_records",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gps_records_vehicle_plate"),
        "gps_records",
        ["vehicle_plate"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # PROJECTS
    # -------------------------------------------------------------------------
    op.create_table(
        "projects",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            comment="Company مالک این Project",
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "code",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_projects_code"),
        "projects",
        ["code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_projects_company_id"),
        "projects",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_projects_id"),
        "projects",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_projects_is_active"),
        "projects",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_projects_name"),
        "projects",
        ["name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_projects_status"),
        "projects",
        ["status"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # ROW ERRORS
    # -------------------------------------------------------------------------
    op.create_table(
        "row_errors",
        sa.Column(
            "import_batch_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "row_number",
            sa.Integer(),
            nullable=False,
            comment="شماره ردیف در فایل Excel/CSV (از ۱)",
        ),
        sa.Column(
            "error_type",
            sa.String(length=100),
            nullable=False,
            comment=(
                "نوع خطا: VALIDATION, DUPLICATE, FORMAT, "
                "MISSING_FIELD, etc."
            ),
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=False,
            comment="پیام خطای قابل نمایش به کاربر",
        ),
        sa.Column(
            "field_name",
            sa.String(length=100),
            nullable=True,
            comment="نام فیلد مشکل‌دار (در صورت مرتبط بودن با یک ستون)",
        ),
        sa.Column(
            "raw_data",
            sa.JSON(),
            nullable=True,
            comment="داده خام ردیف برای اشکال‌زدایی",
        ),
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_row_errors_error_type"),
        "row_errors",
        ["error_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_row_errors_import_batch_id"),
        "row_errors",
        ["import_batch_id"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # VEHICLES
    # -------------------------------------------------------------------------
    op.create_table(
        "vehicles",
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
            comment="Company مالک این Vehicle",
        ),
        sa.Column(
            "import_batch_id",
            sa.Integer(),
            nullable=True,
            comment="آخرین ImportBatch که این Vehicle از آن وارد شده است",
        ),
        sa.Column(
            "vehicle_code",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "plate_number",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "vehicle_type",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "capacity_kg",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "capacity_m3",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "cost_per_km",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
        sa.Column(
            "fixed_cost",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
        sa.Column(
            "latitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "longitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "available_from",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "available_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "raw_data",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "error_note",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_vehicles_company_id"),
        "vehicles",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vehicles_import_batch_id"),
        "vehicles",
        ["import_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vehicles_plate_number"),
        "vehicles",
        ["plate_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vehicles_status"),
        "vehicles",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vehicles_vehicle_code"),
        "vehicles",
        ["vehicle_code"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # ADDRESS CANDIDATES
    # -------------------------------------------------------------------------
    op.create_table(
        "address_candidates",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "store_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "company_store_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "address_text",
            sa.String(length=512),
            nullable=False,
        ),
        sa.Column(
            "province",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "county",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "city",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "district",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "neighborhood",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "village",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "postal_code",
            sa.String(length=10),
            nullable=True,
        ),
        sa.Column(
            "latitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "longitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "source_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "source_detail",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "match_found",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "matched_store_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "match_score",
            sa.Numeric(precision=5, scale=4),
            nullable=True,
        ),
        sa.Column(
            "match_method",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column(
            "validation_provider",
            sa.String(length=30),
            nullable=True,
        ),
        sa.Column(
            "validation_score",
            sa.Numeric(precision=5, scale=4),
            nullable=True,
        ),
        sa.Column(
            "normalized_address",
            sa.String(length=512),
            nullable=True,
        ),
        sa.Column(
            "normalized_latitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "normalized_longitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "fimap_token",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "is_processed",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "is_selected",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_store_id"],
            ["company_stores.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"],
            ["stores.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_address_candidates_company_store_id"),
        "address_candidates",
        ["company_store_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_address_candidates_fimap_token"),
        "address_candidates",
        ["fimap_token"],
        unique=False,
    )
    op.create_index(
        op.f("ix_address_candidates_id"),
        "address_candidates",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_address_candidates_is_processed"),
        "address_candidates",
        ["is_processed"],
        unique=False,
    )
    op.create_index(
        op.f("ix_address_candidates_matched_store_id"),
        "address_candidates",
        ["matched_store_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_address_candidates_source_type"),
        "address_candidates",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_address_candidates_store_id"),
        "address_candidates",
        ["store_id"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # ORDERS
    # -------------------------------------------------------------------------
    op.create_table(
        "orders",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            nullable=False,
            comment="Project مالک این Order",
        ),
        sa.Column(
            "import_batch_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "order_code",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "store_code",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "store_name",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "address",
            sa.String(length=2000),
            nullable=True,
        ),
        sa.Column(
            "latitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "longitude",
            sa.Numeric(precision=10, scale=7),
            nullable=True,
        ),
        sa.Column(
            "weight_kg",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "volume_m3",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "delivery_date",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "delivery_time_from",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "delivery_time_to",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "raw_data",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "error_note",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "import_batch_id",
            "order_code",
            name="uq_orders_batch_order",
        ),
    )

    op.create_index(
        op.f("ix_orders_id"),
        "orders",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_orders_import_batch_id"),
        "orders",
        ["import_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_orders_order_code"),
        "orders",
        ["order_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_orders_project_id"),
        "orders",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_orders_status"),
        "orders",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_orders_store_code"),
        "orders",
        ["store_code"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # PROJECT COMPANY STORES
    # -------------------------------------------------------------------------
    op.create_table(
        "project_company_stores",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            nullable=False,
            comment="پروژه‌ای که از CompanyStore استفاده می‌کند",
        ),
        sa.Column(
            "company_store_id",
            sa.Integer(),
            nullable=False,
            comment="CompanyStore مورد استفاده در پروژه",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            comment=(
                "آیا این CompanyStore در این Project "
                "در حال حاضر فعال و قابل استفاده است؟"
            ),
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="زمان اضافه شدن CompanyStore به Project",
        ),
        sa.Column(
            "removed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment=(
                "زمان غیرفعال شدن CompanyStore در Project. "
                "NULL یعنی هنوز فعال است."
            ),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_store_id"],
            ["company_stores.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "company_store_id",
            name="uq_project_company_store",
        ),
    )

    op.create_index(
        op.f("ix_project_company_stores_company_store_id"),
        "project_company_stores",
        ["company_store_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_company_stores_id"),
        "project_company_stores",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_company_stores_is_active"),
        "project_company_stores",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_company_stores_project_id"),
        "project_company_stores",
        ["project_id"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # PROJECT DRIVERS
    # -------------------------------------------------------------------------
    op.create_table(
        "project_drivers",
        sa.Column(
            "project_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "driver_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=50),
            nullable=True,
            comment=(
                "Project-specific driver role. "
                "Examples: DRIVER | SUPERVISOR | RELIEF"
            ),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "assigned_from",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "assigned_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["drivers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "driver_id",
            name="uq_project_driver",
        ),
    )

    op.create_index(
        op.f("ix_project_drivers_driver_id"),
        "project_drivers",
        ["driver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_drivers_is_active"),
        "project_drivers",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_drivers_project_id"),
        "project_drivers",
        ["project_id"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # PROJECT VEHICLES
    # -------------------------------------------------------------------------
    op.create_table(
        "project_vehicles",
        sa.Column(
            "project_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=50),
            nullable=True,
            comment=(
                "Project-specific vehicle role. "
                "Examples: DELIVERY | BACKUP | SUPPORT"
            ),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "cost_per_km_override",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
            comment=(
                "Optional project-specific cost per kilometer. "
                "If null, Vehicle default cost is used."
            ),
        ),
        sa.Column(
            "fixed_cost_override",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
            comment=(
                "Optional project-specific fixed cost. "
                "If null, Vehicle default fixed cost is used."
            ),
        ),
        sa.Column(
            "assigned_from",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "assigned_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "vehicle_id",
            name="uq_project_vehicle",
        ),
    )

    op.create_index(
        op.f("ix_project_vehicles_is_active"),
        "project_vehicles",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_vehicles_project_id"),
        "project_vehicles",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_vehicles_vehicle_id"),
        "project_vehicles",
        ["vehicle_id"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # REQUESTS
    # -------------------------------------------------------------------------
    op.create_table(
        "requests",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            nullable=False,
            comment="Project مالک این Request",
        ),
        sa.Column(
            "company_name",
            sa.String(length=200),
            nullable=False,
            comment="نام شرکت ثبت‌شده در درخواست",
        ),
        sa.Column(
            "contact_name",
            sa.String(length=200),
            nullable=False,
            comment="نام شخص تماس",
        ),
        sa.Column(
            "mobile",
            sa.String(length=30),
            nullable=False,
            comment="شماره موبایل شخص تماس",
        ),
        sa.Column(
            "email",
            sa.String(length=200),
            nullable=True,
            comment="ایمیل شخص تماس",
        ),
        sa.Column(
            "industry",
            sa.String(length=100),
            nullable=True,
            comment="صنعت یا حوزه فعالیت شرکت",
        ),
        sa.Column(
            "goal",
            sa.Text(),
            nullable=True,
            comment="هدف یا نیاز ثبت‌شده در درخواست",
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            comment=(
                "Request workflow status. "
                "Example: SUBMITTED | REVIEWING | APPROVED | "
                "REJECTED | COMPLETED"
            ),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_requests_company_name"),
        "requests",
        ["company_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_requests_id"),
        "requests",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_requests_mobile"),
        "requests",
        ["mobile"],
        unique=False,
    )
    op.create_index(
        op.f("ix_requests_project_id"),
        "requests",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_requests_status"),
        "requests",
        ["status"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # VEHICLE DRIVERS
    # -------------------------------------------------------------------------
    op.create_table(
        "vehicle_drivers",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "driver_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=50),
            nullable=False,
            comment=(
                "Driver role for the vehicle. "
                "Examples: PRIMARY | SECONDARY | RELIEF"
            ),
        ),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "assigned_from",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "assigned_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["driver_id"],
            ["drivers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_vehicle_drivers_company_id"),
        "vehicle_drivers",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vehicle_drivers_driver_id"),
        "vehicle_drivers",
        ["driver_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vehicle_drivers_id"),
        "vehicle_drivers",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vehicle_drivers_is_active"),
        "vehicle_drivers",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vehicle_drivers_is_primary"),
        "vehicle_drivers",
        ["is_primary"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vehicle_drivers_role"),
        "vehicle_drivers",
        ["role"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vehicle_drivers_vehicle_id"),
        "vehicle_drivers",
        ["vehicle_id"],
        unique=False,
    )

    # -------------------------------------------------------------------------
    # REQUEST FILES
    # -------------------------------------------------------------------------
    op.create_table(
        "request_files",
        sa.Column(
            "request_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "file_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "original_name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "stored_name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "file_path",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "content_type",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "file_size",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["requests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_name"),
    )

    op.create_index(
        op.f("ix_request_files_request_id"),
        "request_files",
        ["request_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    # -------------------------------------------------------------------------
    # REQUEST FILES
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_request_files_request_id"),
        table_name="request_files",
    )
    op.drop_table("request_files")

    # -------------------------------------------------------------------------
    # VEHICLE DRIVERS
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_vehicle_drivers_vehicle_id"),
        table_name="vehicle_drivers",
    )
    op.drop_index(
        op.f("ix_vehicle_drivers_role"),
        table_name="vehicle_drivers",
    )
    op.drop_index(
        op.f("ix_vehicle_drivers_is_primary"),
        table_name="vehicle_drivers",
    )
    op.drop_index(
        op.f("ix_vehicle_drivers_is_active"),
        table_name="vehicle_drivers",
    )
    op.drop_index(
        op.f("ix_vehicle_drivers_id"),
        table_name="vehicle_drivers",
    )
    op.drop_index(
        op.f("ix_vehicle_drivers_driver_id"),
        table_name="vehicle_drivers",
    )
    op.drop_index(
        op.f("ix_vehicle_drivers_company_id"),
        table_name="vehicle_drivers",
    )
    op.drop_table("vehicle_drivers")

    # -------------------------------------------------------------------------
    # REQUESTS
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_requests_status"),
        table_name="requests",
    )
    op.drop_index(
        op.f("ix_requests_project_id"),
        table_name="requests",
    )
    op.drop_index(
        op.f("ix_requests_mobile"),
        table_name="requests",
    )
    op.drop_index(
        op.f("ix_requests_id"),
        table_name="requests",
    )
    op.drop_index(
        op.f("ix_requests_company_name"),
        table_name="requests",
    )
    op.drop_table("requests")

    # -------------------------------------------------------------------------
    # PROJECT VEHICLES
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_project_vehicles_vehicle_id"),
        table_name="project_vehicles",
    )
    op.drop_index(
        op.f("ix_project_vehicles_project_id"),
        table_name="project_vehicles",
    )
    op.drop_index(
        op.f("ix_project_vehicles_is_active"),
        table_name="project_vehicles",
    )
    op.drop_table("project_vehicles")

    # -------------------------------------------------------------------------
    # PROJECT DRIVERS
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_project_drivers_project_id"),
        table_name="project_drivers",
    )
    op.drop_index(
        op.f("ix_project_drivers_is_active"),
        table_name="project_drivers",
    )
    op.drop_index(
        op.f("ix_project_drivers_driver_id"),
        table_name="project_drivers",
    )
    op.drop_table("project_drivers")

    # -------------------------------------------------------------------------
    # PROJECT COMPANY STORES
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_project_company_stores_project_id"),
        table_name="project_company_stores",
    )
    op.drop_index(
        op.f("ix_project_company_stores_is_active"),
        table_name="project_company_stores",
    )
    op.drop_index(
        op.f("ix_project_company_stores_id"),
        table_name="project_company_stores",
    )
    op.drop_index(
        op.f("ix_project_company_stores_company_store_id"),
        table_name="project_company_stores",
    )
    op.drop_table("project_company_stores")

    # -------------------------------------------------------------------------
    # ORDERS
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_orders_store_code"),
        table_name="orders",
    )
    op.drop_index(
        op.f("ix_orders_status"),
        table_name="orders",
    )
    op.drop_index(
        op.f("ix_orders_project_id"),
        table_name="orders",
    )
    op.drop_index(
        op.f("ix_orders_order_code"),
        table_name="orders",
    )
    op.drop_index(
        op.f("ix_orders_import_batch_id"),
        table_name="orders",
    )
    op.drop_index(
        op.f("ix_orders_id"),
        table_name="orders",
    )
    op.drop_table("orders")

    # -------------------------------------------------------------------------
    # ADDRESS CANDIDATES
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_address_candidates_store_id"),
        table_name="address_candidates",
    )
    op.drop_index(
        op.f("ix_address_candidates_source_type"),
        table_name="address_candidates",
    )
    op.drop_index(
        op.f("ix_address_candidates_matched_store_id"),
        table_name="address_candidates",
    )
    op.drop_index(
        op.f("ix_address_candidates_is_processed"),
        table_name="address_candidates",
    )
    op.drop_index(
        op.f("ix_address_candidates_id"),
        table_name="address_candidates",
    )
    op.drop_index(
        op.f("ix_address_candidates_fimap_token"),
        table_name="address_candidates",
    )
    op.drop_index(
        op.f("ix_address_candidates_company_store_id"),
        table_name="address_candidates",
    )
    op.drop_table("address_candidates")

    # -------------------------------------------------------------------------
    # VEHICLES
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_vehicles_vehicle_code"),
        table_name="vehicles",
    )
    op.drop_index(
        op.f("ix_vehicles_status"),
        table_name="vehicles",
    )
    op.drop_index(
        op.f("ix_vehicles_plate_number"),
        table_name="vehicles",
    )
    op.drop_index(
        op.f("ix_vehicles_import_batch_id"),
        table_name="vehicles",
    )
    op.drop_index(
        op.f("ix_vehicles_company_id"),
        table_name="vehicles",
    )
    op.drop_table("vehicles")

    # -------------------------------------------------------------------------
    # ROW ERRORS
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_row_errors_import_batch_id"),
        table_name="row_errors",
    )
    op.drop_index(
        op.f("ix_row_errors_error_type"),
        table_name="row_errors",
    )
    op.drop_table("row_errors")

    # -------------------------------------------------------------------------
    # PROJECTS
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_projects_status"),
        table_name="projects",
    )
    op.drop_index(
        op.f("ix_projects_name"),
        table_name="projects",
    )
    op.drop_index(
        op.f("ix_projects_is_active"),
        table_name="projects",
    )
    op.drop_index(
        op.f("ix_projects_id"),
        table_name="projects",
    )
    op.drop_index(
        op.f("ix_projects_company_id"),
        table_name="projects",
    )
    op.drop_index(
        op.f("ix_projects_code"),
        table_name="projects",
    )
    op.drop_table("projects")

    # -------------------------------------------------------------------------
    # GPS RECORDS
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_gps_records_vehicle_plate"),
        table_name="gps_records",
    )
    op.drop_index(
        op.f("ix_gps_records_timestamp"),
        table_name="gps_records",
    )
    op.drop_index(
        op.f("ix_gps_records_import_batch_id"),
        table_name="gps_records",
    )
    op.drop_table("gps_records")

    # -------------------------------------------------------------------------
    # DRIVERS
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_drivers_status"),
        table_name="drivers",
    )
    op.drop_index(
        op.f("ix_drivers_phone"),
        table_name="drivers",
    )
    op.drop_index(
        op.f("ix_drivers_import_batch_id"),
        table_name="drivers",
    )
    op.drop_index(
        op.f("ix_drivers_driver_code"),
        table_name="drivers",
    )
    op.drop_index(
        op.f("ix_drivers_company_id"),
        table_name="drivers",
    )
    op.drop_table("drivers")

    # -------------------------------------------------------------------------
    # COMPANY STORES
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_company_stores_store_code"),
        table_name="company_stores",
    )
    op.drop_index(
        op.f("ix_company_stores_status"),
        table_name="company_stores",
    )
    op.drop_index(
        op.f("ix_company_stores_province"),
        table_name="company_stores",
    )
    op.drop_index(
        op.f("ix_company_stores_phone"),
        table_name="company_stores",
    )
    op.drop_index(
        op.f("ix_company_stores_match_status"),
        table_name="company_stores",
    )
    op.drop_index(
        op.f("ix_company_stores_master_store_id"),
        table_name="company_stores",
    )
    op.drop_index(
        op.f("ix_company_stores_location_source"),
        table_name="company_stores",
    )
    op.drop_index(
        op.f("ix_company_stores_location_confidence"),
        table_name="company_stores",
    )
    op.drop_index(
        op.f("ix_company_stores_district"),
        table_name="company_stores",
    )
    op.drop_index(
        op.f("ix_company_stores_coordinate_source"),
        table_name="company_stores",
    )
    op.drop_index(
        op.f("ix_company_stores_company_id"),
        table_name="company_stores",
    )
    op.drop_index(
        op.f("ix_company_stores_city"),
        table_name="company_stores",
    )
    op.drop_table("company_stores")

    # -------------------------------------------------------------------------
    # STORE LOCATIONS
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_store_locations_store_id"),
        table_name="store_locations",
    )
    op.drop_index(
        op.f("ix_store_locations_province_id"),
        table_name="store_locations",
    )
    op.drop_index(
        op.f("ix_store_locations_is_current"),
        table_name="store_locations",
    )
    op.drop_index(
        op.f("ix_store_locations_id"),
        table_name="store_locations",
    )
    op.drop_index(
        op.f("ix_store_locations_geohash"),
        table_name="store_locations",
    )
    op.drop_index(
        op.f("ix_store_locations_city_id"),
        table_name="store_locations",
    )
    op.drop_index(
        "idx_store_locations_geometry",
        table_name="store_locations",
    )
    op.drop_table("store_locations")

    # -------------------------------------------------------------------------
    # IMPORT BATCHES
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_import_batches_status"),
        table_name="import_batches",
    )
    op.drop_index(
        op.f("ix_import_batches_file_id"),
        table_name="import_batches",
    )
    op.drop_index(
        op.f("ix_import_batches_entity_type"),
        table_name="import_batches",
    )
    op.drop_table("import_batches")

    # -------------------------------------------------------------------------
    # COMPANIES
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_companies_slug"),
        table_name="companies",
    )
    op.drop_index(
        op.f("ix_companies_national_id"),
        table_name="companies",
    )
    op.drop_index(
        op.f("ix_companies_name"),
        table_name="companies",
    )
    op.drop_index(
        op.f("ix_companies_mobile"),
        table_name="companies",
    )
    op.drop_index(
        op.f("ix_companies_is_active"),
        table_name="companies",
    )
    op.drop_index(
        op.f("ix_companies_id"),
        table_name="companies",
    )
    op.drop_index(
        op.f("ix_companies_email"),
        table_name="companies",
    )
    op.drop_index(
        op.f("ix_companies_code"),
        table_name="companies",
    )
    op.drop_index(
        op.f("ix_companies_account_id"),
        table_name="companies",
    )
    op.drop_table("companies")

    # -------------------------------------------------------------------------
    # STORES
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_stores_province_id"),
        table_name="stores",
    )
    op.drop_index(
        op.f("ix_stores_matching_status"),
        table_name="stores",
    )
    op.drop_index(
        op.f("ix_stores_is_active"),
        table_name="stores",
    )
    op.drop_index(
        op.f("ix_stores_id"),
        table_name="stores",
    )
    op.drop_index(
        op.f("ix_stores_fimap_token"),
        table_name="stores",
    )
    op.drop_index(
        op.f("ix_stores_city_id"),
        table_name="stores",
    )
    op.drop_index(
        op.f("ix_stores_canonical_name"),
        table_name="stores",
    )
    op.drop_table("stores")

    # -------------------------------------------------------------------------
    # FILES
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_files_uploaded_by"),
        table_name="files",
    )
    op.drop_index(
        op.f("ix_files_entity_type"),
        table_name="files",
    )
    op.drop_index(
        op.f("ix_files_entity_id"),
        table_name="files",
    )
    op.drop_index(
        op.f("ix_files_category"),
        table_name="files",
    )
    op.drop_table("files")

    # -------------------------------------------------------------------------
    # ACCOUNTS
    # -------------------------------------------------------------------------
    op.drop_index(
        op.f("ix_accounts_mobile"),
        table_name="accounts",
    )
    op.drop_table("accounts")
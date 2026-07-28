from dotenv import load_dotenv
import os

load_dotenv()


def get_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes", "on")


class Settings:
    APP_NAME = os.getenv("APP_NAME", "Distribution Intelligence")
    APP_VERSION = os.getenv("APP_VERSION", "0.2.0")
    APP_ENV = os.getenv("APP_ENV", "development")
    DEBUG = get_bool(os.getenv("DEBUG"), True)

    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    POSTGRES_DB = os.getenv("POSTGRES_DB", "distribution_intelligence")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "distribution_user")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "distribution_pass")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

    # Async URL برای آینده یا migration کامل به AsyncSession
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://distribution_user:distribution_pass@postgres:5432/distribution_intelligence",
    )

    # URL اصلی فعلی برای backend sync
    SYNC_DATABASE_URL = os.getenv(
        "SYNC_DATABASE_URL",
        "postgresql+psycopg2://distribution_user:distribution_pass@postgres:5432/distribution_intelligence",
    )

    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "host.docker.internal")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_DB = os.getenv("MYSQL_DB", "fishopping_supermarket")
    MYSQL_USER = os.getenv("MYSQL_USER", "fishopping_supermarket")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

    ETL_SOURCE_TABLE = os.getenv("ETL_SOURCE_TABLE", "stores")
    ETL_TARGET_TABLE = os.getenv("ETL_TARGET_TABLE", "stores")
    ETL_BATCH_SIZE = int(os.getenv("ETL_BATCH_SIZE", "1000"))
    ETL_LOG_DIR = os.getenv("ETL_LOG_DIR", "/app/scripts/logs")
    ETL_TRUNCATE_TARGET_FIRST = get_bool(
        os.getenv("ETL_TRUNCATE_TARGET_FIRST"), False
    )
    ETL_LIMIT_ROWS = int(os.getenv("ETL_LIMIT_ROWS", "0"))


settings = Settings()

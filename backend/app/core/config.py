from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    APP_NAME = os.getenv("APP_NAME", "Distribution Intelligence")
    APP_VERSION = os.getenv("APP_VERSION", "0.2.0")
    APP_ENV = os.getenv("APP_ENV", "development")
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://distribution_user:distribution_pass@postgres:5432/distribution_db",
    )


settings = Settings()

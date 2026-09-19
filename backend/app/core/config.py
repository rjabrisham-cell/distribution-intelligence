from dotenv import load_dotenv
import os
import ipaddress
from urllib.parse import urlsplit

load_dotenv()


def get_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes", "on")


class Settings:
    # Set only to a project explicitly approved for public demonstration.
    DEMO_SAMPLE_PROJECT_ID = int(os.getenv("DEMO_SAMPLE_PROJECT_ID", "0"))
    APP_NAME = os.getenv("APP_NAME", "Distribution Intelligence")
    APP_VERSION = os.getenv("APP_VERSION", "0.2.0")
    APP_ENV = os.getenv("APP_ENV", "development")
    DEBUG = get_bool(os.getenv("DEBUG"), True)

    MAP_BASE_URL = os.getenv("MAP_BASE_URL", "http://localhost:8082" if APP_ENV == "development" else "https://iranmaptile.ir").rstrip("/")
    MAP_ENABLED = get_bool(os.getenv("MAP_ENABLED"), True)
    MAP_CSS_URL = os.getenv("MAP_CSS_URL", MAP_BASE_URL + "/mapserver/cdn/css/map.css")
    MAP_JS_URL = os.getenv("MAP_JS_URL", MAP_BASE_URL + ("/mapserver/cdn/js/map_value.js" if APP_ENV == "development" else "/mapserver/cdn/js/map.min.js"))
    MAP_JQUERY_URL = os.getenv("MAP_JQUERY_URL", MAP_BASE_URL + "/mapserver/cdn/js/jquery-3.6.0.min.js")
    MAP_STYLE_URL = os.getenv("MAP_STYLE_URL", MAP_BASE_URL + "/mapserver/vector/styles/main/Fimap-xyz-style.json")
    MAP_TILE_URL = os.getenv("MAP_TILE_URL", MAP_BASE_URL + "/data/iran/{z}/{x}/{y}.pbf")
    MAP_GLYPH_URL = os.getenv("MAP_GLYPH_URL", MAP_BASE_URL + "/mapserver/cdn/IranSans-Noto/{fontstack}/{range}.pbf")
    MAP_SPRITE_URL = os.getenv("MAP_SPRITE_URL", MAP_BASE_URL + "/mapserver/cdn/js/prism.js")
    MAP_RTL_URL = os.getenv("MAP_RTL_URL", MAP_BASE_URL + "/mapserver/cdn/mapbox-gl-rtl-text.min.js")
    MAP_ROUTING_URL = os.getenv("MAP_ROUTING_URL", MAP_BASE_URL + "/route/v1/driving/")
    MAP_GEOCODER_ENABLED = get_bool(os.getenv("MAP_GEOCODER_ENABLED"), False)
    MAP_GEOCODER_URL = os.getenv("MAP_GEOCODER_URL", "")
    # Server-side only. Never included in the public map configuration.
    MAP_API_KEY = os.getenv("MAP_API_KEY", "")
    MAP_ALLOWED_HOSTS = os.getenv("MAP_ALLOWED_HOSTS", "iranmaptile.ir" if APP_ENV != "development" else "localhost,127.0.0.1")

    def public_map_config(self):
        """Invalid map settings disable only the map, never application pages."""
        config = {key: getattr(self, "MAP_" + key.upper() + "_URL") for key in (
            "css", "js", "jquery", "style", "tile", "glyph", "sprite", "rtl", "routing", "geocoder")}
        config.update(enabled=self.MAP_ENABLED, geocoder_enabled=self.MAP_GEOCODER_ENABLED and self.APP_ENV == "development",
                      production=self.APP_ENV != "development")
        allowed = {host.strip().lower() for host in self.MAP_ALLOWED_HOSTS.split(",") if host.strip()}
        config["allowed_hosts"] = sorted(allowed)
        if not config["geocoder_enabled"]:
            config["geocoder"] = ""
        valid = True
        for key in ("css", "js", "jquery", "style", "tile", "glyph", "sprite", "rtl", "routing", "geocoder"):
            value = config[key]
            if not value and key == "geocoder" and not config["geocoder_enabled"]:
                continue
            try:
                url = urlsplit(value)
                safe = url.scheme in ("http", "https") and url.hostname in allowed and not url.username and not url.password and not url.query and not url.fragment
                if config["production"]:
                    safe = safe and url.scheme == "https" and url.port in (None, 443)
                    host = url.hostname or ""
                    safe = safe and host != "localhost" and not host.endswith((".localhost", ".local", ".internal")) and "." in host
                    try:
                        safe = safe and ipaddress.ip_address(host).is_global
                    except ValueError:
                        pass
                if not safe:
                    config[key] = ""
                    valid = False
            except ValueError:
                config[key] = ""
                valid = False
        config["enabled"] = bool(config["enabled"] and valid)
        return config

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

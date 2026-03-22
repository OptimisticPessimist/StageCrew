from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings

# asyncpg が認識する ssl パラメータ値へのマッピング
_SSL_MAP = {"true": "require", "false": "disable", "1": "require", "0": "disable"}


class Settings(BaseSettings):
    # App
    app_name: str = "StageCrew"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://stagecrew:stagecrew@localhost:5432/stagecrew"

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """postgres:// や postgresql:// を postgresql+asyncpg:// に正規化し、
        sslmode パラメータを asyncpg 互換の ssl に変換する。"""
        parts = urlsplit(v)

        # スキーム正規化
        scheme = parts.scheme
        if scheme in ("postgres", "postgresql"):
            scheme = "postgresql+asyncpg"

        # クエリパラメータ正規化 (sslmode → ssl, bool値マッピング)
        qs = parse_qs(parts.query, keep_blank_values=True)
        new_qs: dict[str, list[str]] = {}
        for key, vals in qs.items():
            if key == "sslmode":
                new_qs["ssl"] = [_SSL_MAP.get(vals[0], vals[0])]
            elif key == "ssl":
                new_qs["ssl"] = [_SSL_MAP.get(vals[0], vals[0])]
            else:
                new_qs[key] = vals

        query = urlencode({k: vs[0] for k, vs in new_qs.items()}) if new_qs else ""
        return urlunsplit((scheme, parts.netloc, parts.path, query, parts.fragment))

    # Auth - Discord OAuth
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_redirect_uri: str = "http://localhost:8000/api/auth/discord/callback"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Frontend
    frontend_url: str = "http://localhost:5173"

    # Deadline reminder
    deadline_reminder_hour_utc: int = 0  # Check hour in UTC (0 = JST 9:00)
    deadline_reminder_days: list[int] = [3, 1]  # Notify N days before due date

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

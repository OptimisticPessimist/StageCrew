from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "StageCrew"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://stagecrew:stagecrew@localhost:5432/stagecrew"

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

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

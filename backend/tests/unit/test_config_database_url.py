from src.core.config import Settings


def test_database_url_normalizes_postgres_scheme():
    settings = Settings(database_url="postgres://user:pass@db.internal:5432/stagecrew")
    assert settings.database_url == "postgresql+asyncpg://user:pass@db.internal:5432/stagecrew"


def test_database_url_normalizes_postgresql_without_driver():
    settings = Settings(database_url="postgresql://user:pass@db.internal:5432/stagecrew")
    assert settings.database_url == "postgresql+asyncpg://user:pass@db.internal:5432/stagecrew"


def test_database_url_keeps_asyncpg_url():
    url = "postgresql+asyncpg://user:pass@db.internal:5432/stagecrew"
    settings = Settings(database_url=url)
    assert settings.database_url == url


def test_database_url_maps_sslmode_disable_for_asyncpg():
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@db.internal:5432/stagecrew?sslmode=disable",
    )
    assert settings.database_url == "postgresql+asyncpg://user:pass@db.internal:5432/stagecrew?ssl=disable"


def test_database_url_maps_sslmode_require_for_asyncpg():
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@db.internal:5432/stagecrew?sslmode=require",
    )
    assert settings.database_url == "postgresql+asyncpg://user:pass@db.internal:5432/stagecrew?ssl=require"


def test_database_url_maps_boolean_ssl_value_for_asyncpg():
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@db.internal:5432/stagecrew?ssl=false",
    )
    assert settings.database_url == "postgresql+asyncpg://user:pass@db.internal:5432/stagecrew?ssl=disable"


def test_database_url_maps_boolean_sslmode_value_for_asyncpg():
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@db.internal:5432/stagecrew?sslmode=false",
    )
    assert settings.database_url == "postgresql+asyncpg://user:pass@db.internal:5432/stagecrew?ssl=disable"

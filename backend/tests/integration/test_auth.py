"""Discord OAuth2 認証エンドポイントのテスト。"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import User


async def test_discord_login_redirects(client: AsyncClient):
    resp = await client.get("/api/auth/discord/login", follow_redirects=False)
    assert resp.status_code == 307
    assert "discord.com" in resp.headers["location"]


async def test_get_me(client: AsyncClient, test_user: User):
    resp = await client.get("/api/auth/discord/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(test_user.id)
    assert data["display_name"] == test_user.display_name


async def test_get_me_user_not_found(client: AsyncClient):
    """test_userフィクスチャなしの場合、DBにユーザーがないので404。"""
    resp = await client.get("/api/auth/discord/me")
    assert resp.status_code == 404


async def test_discord_callback_success(client: AsyncClient, db_session: AsyncSession):
    """Discord OAuthコールバックの成功パス（httpxをモック）。"""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {"access_token": "fake_token"}

    mock_user_response = MagicMock()
    mock_user_response.status_code = 200
    mock_user_response.json.return_value = {
        "id": "123456789",
        "username": "testuser",
        "global_name": "Test User",
        "email": "test@example.com",
        "avatar": "abc123",
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_token_response
    mock_client.get.return_value = mock_user_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.api.auth.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get(
            "/api/auth/discord/callback",
            params={"code": "test_code"},
            follow_redirects=False,
        )

    assert resp.status_code == 307
    location = resp.headers["location"]
    assert "token=" in location
    assert "auth/callback" in location


async def test_discord_callback_token_exchange_fails(client: AsyncClient):
    """Discordトークン交換が失敗した場合。"""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 400

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_token_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.api.auth.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get(
            "/api/auth/discord/callback",
            params={"code": "bad_code"},
            follow_redirects=False,
        )

    assert resp.status_code == 307
    assert "error=token_exchange_failed" in resp.headers["location"]

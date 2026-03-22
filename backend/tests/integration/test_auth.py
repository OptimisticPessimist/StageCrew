"""Discord OAuth2 authentication endpoint tests."""

from urllib.parse import parse_qs, urlparse
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import OAUTH_STATE_COOKIE
from src.db.models import User


async def test_discord_login_redirects(client: AsyncClient):
    resp = await client.get("/api/auth/discord/login", follow_redirects=False)
    assert resp.status_code == 307
    assert "discord.com" in resp.headers["location"]
    query = parse_qs(urlparse(resp.headers["location"]).query)
    assert "state" in query
    assert OAUTH_STATE_COOKIE in resp.headers["set-cookie"]


async def test_get_me(client: AsyncClient, test_user: User):
    resp = await client.get("/api/auth/discord/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(test_user.id)
    assert data["display_name"] == test_user.display_name


async def test_get_me_user_not_found(client: AsyncClient):
    resp = await client.get("/api/auth/discord/me")
    assert resp.status_code == 404


async def test_discord_callback_success(client: AsyncClient, db_session: AsyncSession):
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
        login_resp = await client.get("/api/auth/discord/login", follow_redirects=False)
        state = parse_qs(urlparse(login_resp.headers["location"]).query)["state"][0]
        resp = await client.get(
            "/api/auth/discord/callback",
            params={"code": "test_code", "state": state},
            follow_redirects=False,
        )

    assert resp.status_code == 307
    location = resp.headers["location"]
    assert "token=" in location
    assert "auth/callback" in location


async def test_discord_callback_token_exchange_fails(client: AsyncClient):
    mock_token_response = MagicMock()
    mock_token_response.status_code = 400

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_token_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.api.auth.httpx.AsyncClient", return_value=mock_client):
        login_resp = await client.get("/api/auth/discord/login", follow_redirects=False)
        state = parse_qs(urlparse(login_resp.headers["location"]).query)["state"][0]
        resp = await client.get(
            "/api/auth/discord/callback",
            params={"code": "bad_code", "state": state},
            follow_redirects=False,
        )

    assert resp.status_code == 307
    assert "error=token_exchange_failed" in resp.headers["location"]


async def test_discord_callback_rejects_invalid_state(client: AsyncClient):
    await client.get("/api/auth/discord/login", follow_redirects=False)

    resp = await client.get(
        "/api/auth/discord/callback",
        params={"code": "test_code", "state": "wrong-state"},
        follow_redirects=False,
    )

    assert resp.status_code == 307
    assert "error=invalid_state" in resp.headers["location"]

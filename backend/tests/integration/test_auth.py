"""認証エンドポイントのテスト (Supabase Auth 版)。

注意: OAuth フローは Supabase 側で処理されるため、
ここでは /api/auth/me エンドポイントのみテストする。
"""

from httpx import AsyncClient

from src.db.models import User


async def test_get_me(client: AsyncClient, test_user: User):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(test_user.id)
    assert data["display_name"] == test_user.display_name


async def test_get_me_user_not_found(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 404

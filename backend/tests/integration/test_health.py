"""ヘルスチェック・ルートエンドポイントのテスト。"""

from httpx import AsyncClient


async def test_root_endpoint(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["app"] == "StageCrew"
    assert "version" in data


async def test_health_check(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

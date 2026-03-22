"""公演 CRUD エンドポイントのテスト。"""

import uuid

from httpx import AsyncClient

# ---- 一覧 ----


async def test_list_productions_empty(client: AsyncClient, org_owner):
    org, _ = org_owner
    resp = await client.get(f"/api/organizations/{org.id}/productions/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_productions(client: AsyncClient, production):
    prod, pm = production
    resp = await client.get(f"/api/organizations/{prod.organization_id}/productions/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(p["name"] == prod.name for p in data)


# ---- 作成 ----


async def test_create_production(client: AsyncClient, org_owner):
    org, _ = org_owner
    resp = await client.post(
        f"/api/organizations/{org.id}/productions/",
        json={"name": "新公演", "production_type": "physical"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "新公演"


async def test_create_production_not_admin(client_as_other: AsyncClient, org_owner, org_with_member):
    org, _ = org_owner
    resp = await client_as_other.post(
        f"/api/organizations/{org.id}/productions/",
        json={"name": "拒否公演"},
    )
    assert resp.status_code == 403


# ---- 詳細 ----


async def test_get_production(client: AsyncClient, production):
    prod, _ = production
    resp = await client.get(f"/api/organizations/{prod.organization_id}/productions/{prod.id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == prod.name


async def test_get_production_not_found(client: AsyncClient, org_owner):
    org, _ = org_owner
    resp = await client.get(f"/api/organizations/{org.id}/productions/{uuid.uuid4()}")
    assert resp.status_code == 404


# ---- 更新 ----


async def test_update_production_as_manager(client: AsyncClient, production):
    prod, _ = production
    resp = await client.patch(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}",
        json={"name": "更新公演"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新公演"


async def test_update_production_as_member_forbidden(client_as_other: AsyncClient, production, org_with_member):
    prod, _ = production
    resp = await client_as_other.patch(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}",
        json={"name": "拒否"},
    )
    assert resp.status_code == 403


# ---- 削除 ----


async def test_delete_production(client: AsyncClient, production):
    prod, _ = production
    resp = await client.delete(f"/api/organizations/{prod.organization_id}/productions/{prod.id}")
    assert resp.status_code == 204


async def test_delete_production_not_admin(client_as_other: AsyncClient, production, org_with_member):
    prod, _ = production
    resp = await client_as_other.delete(f"/api/organizations/{prod.organization_id}/productions/{prod.id}")
    assert resp.status_code == 403

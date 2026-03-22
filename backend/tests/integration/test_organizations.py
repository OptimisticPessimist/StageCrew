"""団体 CRUD エンドポイントのテスト。"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Organization, OrganizationMembership, User


# ---- 一覧 ----


async def test_list_organizations_empty(client: AsyncClient, test_user: User):
    resp = await client.get("/api/organizations/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_organizations(client: AsyncClient, org_owner):
    org, _ = org_owner
    resp = await client.get("/api/organizations/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == org.name
    assert data[0]["member_count"] == 1


# ---- 作成 ----


async def test_create_organization(client: AsyncClient, test_user: User):
    resp = await client.post("/api/organizations/", json={"name": "新しい団体", "description": "説明"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "新しい団体"
    assert data["member_count"] == 1


async def test_create_organization_with_capabilities(client: AsyncClient, test_user: User):
    caps = ["task.view", "comment.create"]
    resp = await client.post(
        "/api/organizations/",
        json={"name": "能力付き団体", "cast_default_capabilities": caps},
    )
    assert resp.status_code == 201
    assert resp.json()["cast_default_capabilities"] == caps


# ---- 詳細取得 ----


async def test_get_organization(client: AsyncClient, org_owner):
    org, _ = org_owner
    resp = await client.get(f"/api/organizations/{org.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == org.name
    assert len(data["members"]) == 1


async def test_get_organization_not_found(client: AsyncClient, test_user: User):
    resp = await client.get(f"/api/organizations/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_get_organization_not_member(client_as_other: AsyncClient, org_owner, other_user: User):
    org, _ = org_owner
    resp = await client_as_other.get(f"/api/organizations/{org.id}")
    assert resp.status_code == 403


# ---- 更新 ----


async def test_update_organization_as_owner(client: AsyncClient, org_owner):
    org, _ = org_owner
    resp = await client.patch(f"/api/organizations/{org.id}", json={"name": "更新された団体"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新された団体"


async def test_update_organization_as_member_forbidden(
    client_as_other: AsyncClient, org_owner, org_with_member
):
    org, _ = org_owner
    resp = await client_as_other.patch(f"/api/organizations/{org.id}", json={"name": "拒否"})
    assert resp.status_code == 403


# ---- 削除 ----


async def test_delete_organization_as_owner(client: AsyncClient, org_owner):
    org, _ = org_owner
    resp = await client.delete(f"/api/organizations/{org.id}")
    assert resp.status_code == 204


async def test_delete_organization_as_member_forbidden(
    client_as_other: AsyncClient, org_owner, org_with_member
):
    org, _ = org_owner
    resp = await client_as_other.delete(f"/api/organizations/{org.id}")
    assert resp.status_code == 403


async def test_delete_organization_not_found(client: AsyncClient, test_user: User):
    resp = await client.delete(f"/api/organizations/{uuid.uuid4()}")
    assert resp.status_code == 404

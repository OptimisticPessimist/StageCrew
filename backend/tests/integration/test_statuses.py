"""ステータス定義 CRUD のテスト。"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Department, Production, ProductionMembership, StatusDefinition, User


def _status_url(org_id, prod_id, suffix=""):
    return f"/api/organizations/{org_id}/productions/{prod_id}/statuses{suffix}"


async def test_list_statuses_empty(client: AsyncClient, production):
    prod, _ = production
    resp = await client.get(_status_url(prod.organization_id, prod.id, "/"))
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_status(client: AsyncClient, production):
    prod, _ = production
    resp = await client.post(
        _status_url(prod.organization_id, prod.id, "/"),
        json={"name": "進行中", "color": "#FFFF00", "sort_order": 1},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "進行中"
    assert data["is_closed"] is False


async def test_list_statuses_filter_by_department(
    client: AsyncClient, production, department: Department, db_session: AsyncSession
):
    prod, _ = production
    sd = StatusDefinition(
        production_id=prod.id, department_id=department.id, name="部門ステータス", sort_order=0
    )
    db_session.add(sd)
    await db_session.flush()

    resp = await client.get(
        _status_url(prod.organization_id, prod.id, "/"),
        params={"department_id": str(department.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(s["department_id"] == str(department.id) for s in data)


async def test_update_status(client: AsyncClient, production, status_def: StatusDefinition):
    prod, _ = production
    resp = await client.patch(
        _status_url(prod.organization_id, prod.id, f"/{status_def.id}"),
        json={"name": "完了", "is_closed": True},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "完了"
    assert resp.json()["is_closed"] is True


async def test_delete_status(client: AsyncClient, production, status_def: StatusDefinition):
    prod, _ = production
    resp = await client.delete(_status_url(prod.organization_id, prod.id, f"/{status_def.id}"))
    assert resp.status_code == 204


async def test_status_not_found(client: AsyncClient, production):
    prod, _ = production
    resp = await client.patch(
        _status_url(prod.organization_id, prod.id, f"/{uuid.uuid4()}"),
        json={"name": "存在しない"},
    )
    assert resp.status_code == 404


async def test_status_crud_not_manager(client_as_other: AsyncClient, production, org_with_member):
    prod, _ = production
    resp = await client_as_other.post(
        _status_url(prod.organization_id, prod.id, "/"),
        json={"name": "拒否"},
    )
    assert resp.status_code == 403

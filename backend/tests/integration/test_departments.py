"""部門 CRUD + スタッフロール CRUD のテスト。"""

import uuid

from httpx import AsyncClient

from src.db.models import Department, StaffRole


def _dept_url(org_id, prod_id, suffix=""):
    return f"/api/organizations/{org_id}/productions/{prod_id}/departments{suffix}"


# ---- 部門一覧 ----


async def test_list_departments_empty(client: AsyncClient, production):
    prod, _ = production
    resp = await client.get(_dept_url(prod.organization_id, prod.id, "/"))
    assert resp.status_code == 200
    assert resp.json() == []


# ---- 部門作成 ----


async def test_create_department(client: AsyncClient, production):
    prod, _ = production
    resp = await client.post(
        _dept_url(prod.organization_id, prod.id, "/"),
        json={"name": "音響部", "color": "#00FF00"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "音響部"
    assert data["color"] == "#00FF00"


async def test_create_department_with_staff_roles(client: AsyncClient, production):
    prod, _ = production
    resp = await client.post(
        _dept_url(prod.organization_id, prod.id, "/"),
        json={
            "name": "舞台部",
            "staff_roles": [
                {"name": "チーフ", "sort_order": 0},
                {"name": "サブチーフ", "sort_order": 1},
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["staff_roles"]) == 2


async def test_create_department_not_manager(client_as_other: AsyncClient, production, org_with_member):
    prod, _ = production
    resp = await client_as_other.post(
        _dept_url(prod.organization_id, prod.id, "/"),
        json={"name": "拒否部門"},
    )
    assert resp.status_code == 403


# ---- 部門詳細 ----


async def test_get_department(client: AsyncClient, production, department: Department):
    prod, _ = production
    resp = await client.get(_dept_url(prod.organization_id, prod.id, f"/{department.id}"))
    assert resp.status_code == 200
    assert resp.json()["name"] == department.name


async def test_get_department_not_found(client: AsyncClient, production):
    prod, _ = production
    resp = await client.get(_dept_url(prod.organization_id, prod.id, f"/{uuid.uuid4()}"))
    assert resp.status_code == 404


# ---- 部門更新 ----


async def test_update_department(client: AsyncClient, production, department: Department):
    prod, _ = production
    resp = await client.patch(
        _dept_url(prod.organization_id, prod.id, f"/{department.id}"),
        json={"name": "更新された部門"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新された部門"


# ---- 部門削除 ----


async def test_delete_department(client: AsyncClient, production, department: Department):
    prod, _ = production
    resp = await client.delete(_dept_url(prod.organization_id, prod.id, f"/{department.id}"))
    assert resp.status_code == 204


# ============================================================
# StaffRole CRUD
# ============================================================


def _role_url(org_id, prod_id, dept_id, suffix=""):
    return f"/api/organizations/{org_id}/productions/{prod_id}/departments/{dept_id}/staff-roles{suffix}"


async def test_list_staff_roles(client: AsyncClient, production, department: Department, staff_role: StaffRole):
    prod, _ = production
    resp = await client.get(_role_url(prod.organization_id, prod.id, department.id))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(r["name"] == staff_role.name for r in data)


async def test_create_staff_role(client: AsyncClient, production, department: Department):
    prod, _ = production
    resp = await client.post(
        _role_url(prod.organization_id, prod.id, department.id),
        json={"name": "新ロール", "sort_order": 10},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "新ロール"


async def test_update_staff_role(client: AsyncClient, production, department: Department, staff_role: StaffRole):
    prod, _ = production
    resp = await client.patch(
        _role_url(prod.organization_id, prod.id, department.id, f"/{staff_role.id}"),
        json={"name": "更新ロール"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新ロール"


async def test_delete_staff_role(client: AsyncClient, production, department: Department, staff_role: StaffRole):
    prod, _ = production
    resp = await client.delete(_role_url(prod.organization_id, prod.id, department.id, f"/{staff_role.id}"))
    assert resp.status_code == 204


async def test_staff_role_not_found(client: AsyncClient, production, department: Department):
    prod, _ = production
    resp = await client.patch(
        _role_url(prod.organization_id, prod.id, department.id, f"/{uuid.uuid4()}"),
        json={"name": "存在しない"},
    )
    assert resp.status_code == 404

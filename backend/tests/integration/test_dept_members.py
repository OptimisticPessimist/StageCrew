"""部門メンバー管理のテスト。"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    Department,
    DepartmentMembership,
    StaffRole,
)


def _dm_url(org_id, prod_id, dept_id, suffix=""):
    return f"/api/organizations/{org_id}/productions/{prod_id}/departments/{dept_id}/members{suffix}"


async def test_list_dept_members(client: AsyncClient, production, department: Department):
    prod, _ = production
    resp = await client.get(_dm_url(prod.organization_id, prod.id, department.id, "/"))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_add_dept_member(client: AsyncClient, production, department: Department):
    prod, pm = production
    resp = await client.post(
        _dm_url(prod.organization_id, prod.id, department.id, "/"),
        json={"production_membership_id": str(pm.id)},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["department_id"] == str(department.id)


async def test_add_dept_member_invalid_production_membership(client: AsyncClient, production, department: Department):
    prod, _ = production
    resp = await client.post(
        _dm_url(prod.organization_id, prod.id, department.id, "/"),
        json={"production_membership_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 400


async def test_add_dept_member_duplicate(
    client: AsyncClient, production, department: Department, db_session: AsyncSession
):
    prod, pm = production
    dm = DepartmentMembership(
        production_membership_id=pm.id,
        department_id=department.id,
        capabilities=["task.view"],
    )
    db_session.add(dm)
    await db_session.flush()

    resp = await client.post(
        _dm_url(prod.organization_id, prod.id, department.id, "/"),
        json={"production_membership_id": str(pm.id)},
    )
    assert resp.status_code == 409


async def test_add_dept_member_with_staff_role(
    client: AsyncClient, production, department: Department, staff_role: StaffRole
):
    prod, pm = production
    resp = await client.post(
        _dm_url(prod.organization_id, prod.id, department.id, "/"),
        json={
            "production_membership_id": str(pm.id),
            "staff_role_id": str(staff_role.id),
        },
    )
    assert resp.status_code == 201
    assert resp.json()["staff_role_id"] == str(staff_role.id)


async def test_add_dept_member_invalid_staff_role(client: AsyncClient, production, department: Department):
    prod, pm = production
    resp = await client.post(
        _dm_url(prod.organization_id, prod.id, department.id, "/"),
        json={
            "production_membership_id": str(pm.id),
            "staff_role_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 400


async def test_add_dept_member_not_manager(
    client_as_other: AsyncClient, production, department: Department, org_with_member
):
    prod, _ = production
    resp = await client_as_other.post(
        _dm_url(prod.organization_id, prod.id, department.id, "/"),
        json={"production_membership_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 403


async def test_update_dept_member(client: AsyncClient, production, department: Department, db_session: AsyncSession):
    prod, pm = production
    dm = DepartmentMembership(
        production_membership_id=pm.id,
        department_id=department.id,
        capabilities=["task.view"],
    )
    db_session.add(dm)
    await db_session.flush()

    resp = await client.patch(
        _dm_url(prod.organization_id, prod.id, department.id, f"/{dm.id}"),
        json={"capabilities": ["task.view", "task.create"]},
    )
    assert resp.status_code == 200
    assert "task.create" in resp.json()["capabilities"]


async def test_remove_dept_member(client: AsyncClient, production, department: Department, db_session: AsyncSession):
    prod, pm = production
    dm = DepartmentMembership(
        production_membership_id=pm.id,
        department_id=department.id,
        capabilities=["task.view"],
    )
    db_session.add(dm)
    await db_session.flush()

    resp = await client.delete(_dm_url(prod.organization_id, prod.id, department.id, f"/{dm.id}"))
    assert resp.status_code == 204


async def test_dept_membership_not_found(client: AsyncClient, production, department: Department):
    prod, _ = production
    resp = await client.patch(
        _dm_url(prod.organization_id, prod.id, department.id, f"/{uuid.uuid4()}"),
        json={"capabilities": ["task.view"]},
    )
    assert resp.status_code == 404

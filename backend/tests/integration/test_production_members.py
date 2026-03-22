"""公演メンバー管理のテスト。"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ProductionMembership, User


def _pm_url(org_id, prod_id, suffix=""):
    return f"/api/organizations/{org_id}/productions/{prod_id}/members{suffix}"


async def test_list_production_members(client: AsyncClient, production):
    prod, _ = production
    resp = await client.get(_pm_url(prod.organization_id, prod.id, "/"))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


async def test_add_production_member(client: AsyncClient, production, other_user: User, org_with_member):
    prod, _ = production
    resp = await client.post(
        _pm_url(prod.organization_id, prod.id, "/"),
        json={"user_id": str(other_user.id), "production_role": "member"},
    )
    assert resp.status_code == 201
    assert resp.json()["production_role"] == "member"


async def test_add_non_org_member_rejected(client: AsyncClient, production, db_session: AsyncSession):
    prod, _ = production
    # 団体に属さないユーザーを作成
    non_member = User(id=uuid.uuid4(), display_name="非メンバー", discord_id="non_member_discord")
    db_session.add(non_member)
    await db_session.flush()

    resp = await client.post(
        _pm_url(prod.organization_id, prod.id, "/"),
        json={"user_id": str(non_member.id), "production_role": "member"},
    )
    assert resp.status_code == 400


async def test_add_duplicate_production_member(
    client: AsyncClient, production, other_user: User, org_with_member, db_session: AsyncSession
):
    prod, _ = production
    # 既に追加
    pm = ProductionMembership(user_id=other_user.id, production_id=prod.id, production_role="member")
    db_session.add(pm)
    await db_session.flush()

    resp = await client.post(
        _pm_url(prod.organization_id, prod.id, "/"),
        json={"user_id": str(other_user.id), "production_role": "member"},
    )
    assert resp.status_code == 409


async def test_add_member_not_manager(client_as_other: AsyncClient, production, org_with_member):
    prod, _ = production
    resp = await client_as_other.post(
        _pm_url(prod.organization_id, prod.id, "/"),
        json={"user_id": str(uuid.uuid4()), "production_role": "member"},
    )
    assert resp.status_code == 403


async def test_update_production_member(
    client: AsyncClient, production, other_user: User, org_with_member, db_session: AsyncSession
):
    prod, _ = production
    pm = ProductionMembership(user_id=other_user.id, production_id=prod.id, production_role="member")
    db_session.add(pm)
    await db_session.flush()

    resp = await client.patch(
        _pm_url(prod.organization_id, prod.id, f"/{pm.id}"),
        json={"production_role": "manager"},
    )
    assert resp.status_code == 200
    assert resp.json()["production_role"] == "manager"


async def test_remove_production_member(
    client: AsyncClient, production, other_user: User, org_with_member, db_session: AsyncSession
):
    prod, _ = production
    pm = ProductionMembership(user_id=other_user.id, production_id=prod.id, production_role="member")
    db_session.add(pm)
    await db_session.flush()

    resp = await client.delete(_pm_url(prod.organization_id, prod.id, f"/{pm.id}"))
    assert resp.status_code == 204


async def test_production_membership_not_found(client: AsyncClient, production):
    prod, _ = production
    resp = await client.patch(
        _pm_url(prod.organization_id, prod.id, f"/{uuid.uuid4()}"),
        json={"production_role": "manager"},
    )
    assert resp.status_code == 404

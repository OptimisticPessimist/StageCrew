"""団体メンバー管理のテスト。"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Organization, OrganizationMembership, User
from tests.conftest import OTHER_USER_ID, TEST_USER_ID


def _members_url(org_id, suffix=""):
    return f"/api/organizations/{org_id}/members{suffix}"


async def test_list_org_members(client: AsyncClient, org_owner):
    org, _ = org_owner
    resp = await client.get(_members_url(org.id, "/"))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["org_role"] == "owner"


async def test_add_org_member(client: AsyncClient, org_owner, other_user: User):
    org, _ = org_owner
    resp = await client.post(
        _members_url(org.id, "/"),
        json={"user_id": str(other_user.id), "org_role": "member"},
    )
    assert resp.status_code == 201
    assert resp.json()["org_role"] == "member"


async def test_add_org_member_user_not_found(client: AsyncClient, org_owner):
    org, _ = org_owner
    resp = await client.post(
        _members_url(org.id, "/"),
        json={"user_id": str(uuid.uuid4()), "org_role": "member"},
    )
    assert resp.status_code == 404


async def test_add_org_member_duplicate(client: AsyncClient, org_owner, other_user: User, org_with_member):
    org, _ = org_owner
    resp = await client.post(
        _members_url(org.id, "/"),
        json={"user_id": str(other_user.id), "org_role": "member"},
    )
    assert resp.status_code == 409


async def test_add_org_member_not_admin(client_as_other: AsyncClient, org_owner, org_with_member):
    org, _ = org_owner
    resp = await client_as_other.post(
        _members_url(org.id, "/"),
        json={"user_id": str(uuid.uuid4()), "org_role": "member"},
    )
    assert resp.status_code == 403


async def test_update_org_member_role(
    client: AsyncClient, org_owner, other_user: User, org_with_member: OrganizationMembership
):
    org, _ = org_owner
    resp = await client.patch(
        _members_url(org.id, f"/{org_with_member.id}"),
        json={"org_role": "admin"},
    )
    assert resp.status_code == 200
    assert resp.json()["org_role"] == "admin"


async def test_update_last_owner_prevented(client: AsyncClient, org_owner):
    org, owner_membership = org_owner
    resp = await client.patch(
        _members_url(org.id, f"/{owner_membership.id}"),
        json={"org_role": "member"},
    )
    assert resp.status_code == 400


async def test_remove_org_member(
    client: AsyncClient, org_owner, other_user: User, org_with_member: OrganizationMembership
):
    org, _ = org_owner
    resp = await client.delete(_members_url(org.id, f"/{org_with_member.id}"))
    assert resp.status_code == 204


async def test_remove_last_owner_prevented(client: AsyncClient, org_owner):
    org, owner_membership = org_owner
    resp = await client.delete(_members_url(org.id, f"/{owner_membership.id}"))
    assert resp.status_code == 400


async def test_membership_not_found(client: AsyncClient, org_owner):
    org, _ = org_owner
    resp = await client.patch(
        _members_url(org.id, f"/{uuid.uuid4()}"),
        json={"org_role": "admin"},
    )
    assert resp.status_code == 404

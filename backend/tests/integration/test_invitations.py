"""招待管理のテスト。"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Invitation, Organization, OrganizationMembership, User
from tests.conftest import OTHER_USER_ID, TEST_USER_ID


def _inv_url(org_id, suffix=""):
    return f"/api/organizations/{org_id}/invitations{suffix}"


# ---- 一覧 ----


async def test_list_invitations(client: AsyncClient, org_owner, db_session: AsyncSession, test_user: User):
    org, _ = org_owner
    inv = Invitation(
        organization_id=org.id,
        invited_by=test_user.id,
        email="test@example.com",
        token=secrets.token_urlsafe(32),
        org_role="member",
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(inv)
    await db_session.flush()

    resp = await client.get(_inv_url(org.id, "/"))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["status"] == "pending"


# ---- 作成 ----


async def test_create_invitation(client: AsyncClient, org_owner):
    org, _ = org_owner
    resp = await client.post(
        _inv_url(org.id, "/"),
        json={"email": "new@example.com", "org_role": "member"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["org_role"] == "member"
    assert data["status"] == "pending"
    assert "token" in data


async def test_create_invitation_not_admin(client_as_other: AsyncClient, org_owner, org_with_member):
    org, _ = org_owner
    resp = await client_as_other.post(
        _inv_url(org.id, "/"),
        json={"email": "reject@example.com"},
    )
    assert resp.status_code == 403


# ---- 取消 ----


async def test_cancel_invitation(client: AsyncClient, org_owner, db_session: AsyncSession, test_user: User):
    org, _ = org_owner
    inv = Invitation(
        organization_id=org.id,
        invited_by=test_user.id,
        token=secrets.token_urlsafe(32),
        org_role="member",
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(inv)
    await db_session.flush()

    resp = await client.delete(_inv_url(org.id, f"/{inv.id}"))
    assert resp.status_code == 204


async def test_cancel_invitation_not_found(client: AsyncClient, org_owner):
    org, _ = org_owner
    resp = await client.delete(_inv_url(org.id, f"/{uuid.uuid4()}"))
    assert resp.status_code == 404


# ---- 承認 ----


async def test_accept_invitation(
    client_as_other: AsyncClient, org_owner, other_user: User, db_session: AsyncSession, test_user: User
):
    org, _ = org_owner
    token = secrets.token_urlsafe(32)
    inv = Invitation(
        organization_id=org.id,
        invited_by=test_user.id,
        token=token,
        org_role="member",
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(inv)
    await db_session.flush()

    resp = await client_as_other.post(f"/api/invitations/{token}/accept")
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "団体に参加しました"
    assert data["organization_id"] == str(org.id)


async def test_accept_invitation_not_found(client: AsyncClient, test_user: User):
    resp = await client.post("/api/invitations/invalid-token/accept")
    assert resp.status_code == 404


async def test_accept_invitation_already_used(
    client_as_other: AsyncClient, org_owner, other_user: User, db_session: AsyncSession, test_user: User
):
    org, _ = org_owner
    token = secrets.token_urlsafe(32)
    inv = Invitation(
        organization_id=org.id,
        invited_by=test_user.id,
        token=token,
        org_role="member",
        status="accepted",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(inv)
    await db_session.flush()

    resp = await client_as_other.post(f"/api/invitations/{token}/accept")
    assert resp.status_code == 400


async def test_accept_invitation_expired(
    client_as_other: AsyncClient, org_owner, other_user: User, db_session: AsyncSession, test_user: User
):
    org, _ = org_owner
    token = secrets.token_urlsafe(32)
    inv = Invitation(
        organization_id=org.id,
        invited_by=test_user.id,
        token=token,
        org_role="member",
        status="pending",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # 期限切れ
    )
    db_session.add(inv)
    await db_session.flush()

    resp = await client_as_other.post(f"/api/invitations/{token}/accept")
    assert resp.status_code == 400


async def test_accept_invitation_already_member(
    client_as_other: AsyncClient, org_owner, org_with_member, other_user: User, db_session: AsyncSession, test_user: User
):
    org, _ = org_owner
    token = secrets.token_urlsafe(32)
    inv = Invitation(
        organization_id=org.id,
        invited_by=test_user.id,
        token=token,
        org_role="member",
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(inv)
    await db_session.flush()

    resp = await client_as_other.post(f"/api/invitations/{token}/accept")
    assert resp.status_code == 409

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import Invitation, OrganizationMembership
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.invitations import (
    InvitationAcceptResponse,
    InvitationCreate,
    InvitationResponse,
)

org_router = APIRouter()
accept_router = APIRouter()


# ============================================================
# 団体スコープの招待管理
# ============================================================


@org_router.get("/", response_model=list[InvitationResponse])
async def list_invitations(
    org_id: uuid.UUID,
    invitation_status: str | None = "pending",
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """招待一覧を取得"""
    await _check_admin(org_id, current_user.id, db)

    stmt = (
        select(Invitation)
        .where(Invitation.organization_id == org_id)
        .options(selectinload(Invitation.inviter))
        .order_by(Invitation.created_at.desc())
    )
    if invitation_status is not None:
        stmt = stmt.where(Invitation.status == invitation_status)

    result = await db.execute(stmt)
    invitations = result.scalars().all()

    return [
        InvitationResponse(
            id=inv.id,
            organization_id=inv.organization_id,
            email=inv.email,
            token=inv.token,
            org_role=inv.org_role,
            status=inv.status,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
            invited_by_name=inv.inviter.display_name,
        )
        for inv in invitations
    ]


@org_router.post("/", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    org_id: uuid.UUID,
    body: InvitationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """招待を作成（トークンベース、7日有効）"""
    await _check_admin(org_id, current_user.id, db)

    invitation = Invitation(
        organization_id=org_id,
        invited_by=current_user.id,
        email=body.email,
        token=secrets.token_urlsafe(32),
        org_role=body.org_role,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invitation)
    await db.flush()

    return InvitationResponse(
        id=invitation.id,
        organization_id=invitation.organization_id,
        email=invitation.email,
        token=invitation.token,
        org_role=invitation.org_role,
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        invited_by_name=current_user.display_name,
    )


@org_router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    org_id: uuid.UUID,
    invitation_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """招待を取消"""
    await _check_admin(org_id, current_user.id, db)

    result = await db.execute(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.organization_id == org_id,
        )
    )
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HTTPException(status_code=404, detail="招待が見つかりません")

    await db.delete(invitation)


# ============================================================
# 招待承認（トークンベース）
# ============================================================


@accept_router.post("/{token}/accept", response_model=InvitationAcceptResponse)
async def accept_invitation(
    token: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """招待トークンで団体に参加"""
    result = await db.execute(
        select(Invitation).where(Invitation.token == token)
    )
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HTTPException(status_code=404, detail="招待が見つかりません")

    if invitation.status != "pending":
        raise HTTPException(status_code=400, detail="この招待は既に使用済みまたは期限切れです")

    if invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = "expired"
        await db.flush()
        raise HTTPException(status_code=400, detail="招待の有効期限が切れています")

    # 既にメンバーかチェック
    existing = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == invitation.organization_id,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="既にこの団体のメンバーです")

    # メンバーシップ作成
    membership = OrganizationMembership(
        user_id=current_user.id,
        organization_id=invitation.organization_id,
        org_role=invitation.org_role,
    )
    db.add(membership)

    invitation.status = "accepted"
    await db.flush()

    return InvitationAcceptResponse(
        message="団体に参加しました",
        organization_id=invitation.organization_id,
        membership_id=membership.id,
    )


# ---- ヘルパー ----


async def _check_admin(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="この団体のメンバーではありません")
    if membership.org_role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="管理者権限が必要です")

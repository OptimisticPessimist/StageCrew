import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import Organization, OrganizationMembership, User
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.members import OrgMemberAdd, OrgMemberUpdate
from src.schemas.organizations import OrganizationMemberResponse

router = APIRouter()


@router.get("/", response_model=list[OrganizationMemberResponse])
async def list_org_members(
    org_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """団体メンバー一覧を取得"""
    await _check_membership(org_id, current_user.id, db)

    stmt = (
        select(OrganizationMembership)
        .where(OrganizationMembership.organization_id == org_id)
        .options(selectinload(OrganizationMembership.user))
        .order_by(OrganizationMembership.created_at)
    )
    result = await db.execute(stmt)
    memberships = result.scalars().all()

    return [
        OrganizationMemberResponse(
            id=m.id,
            user_id=m.user_id,
            display_name=m.user.display_name,
            org_role=m.org_role,
            created_at=m.created_at,
        )
        for m in memberships
    ]


@router.post("/", response_model=OrganizationMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_org_member(
    org_id: uuid.UUID,
    body: OrgMemberAdd,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """団体にメンバーを追加"""
    await _check_admin(org_id, current_user.id, db)

    # ユーザーの存在確認
    user_result = await db.execute(select(User).where(User.id == body.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    # 重複チェック
    existing = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == body.user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="既にメンバーです")

    membership = OrganizationMembership(
        user_id=body.user_id,
        organization_id=org_id,
        org_role=body.org_role,
    )
    db.add(membership)
    await db.flush()

    return OrganizationMemberResponse(
        id=membership.id,
        user_id=membership.user_id,
        display_name=user.display_name,
        org_role=membership.org_role,
        created_at=membership.created_at,
    )


@router.patch("/{membership_id}", response_model=OrganizationMemberResponse)
async def update_org_member(
    org_id: uuid.UUID,
    membership_id: uuid.UUID,
    body: OrgMemberUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """メンバーのロールを変更"""
    await _check_admin(org_id, current_user.id, db)
    membership = await _get_membership_or_404(membership_id, org_id, db)

    # 最後のownerを変更不可
    if membership.org_role == "owner" and body.org_role != "owner":
        owner_count = await _count_owners(org_id, db)
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="最後のオーナーのロールは変更できません")

    membership.org_role = body.org_role
    await db.flush()

    stmt = (
        select(OrganizationMembership)
        .where(OrganizationMembership.id == membership_id)
        .options(selectinload(OrganizationMembership.user))
    )
    result = await db.execute(stmt)
    m = result.scalar_one()

    return OrganizationMemberResponse(
        id=m.id,
        user_id=m.user_id,
        display_name=m.user.display_name,
        org_role=m.org_role,
        created_at=m.created_at,
    )


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_org_member(
    org_id: uuid.UUID,
    membership_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """メンバーを団体から除外"""
    await _check_admin(org_id, current_user.id, db)
    membership = await _get_membership_or_404(membership_id, org_id, db)

    # 最後のownerは削除不可
    if membership.org_role == "owner":
        owner_count = await _count_owners(org_id, db)
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="最後のオーナーは削除できません")

    await db.delete(membership)


# ---- ヘルパー ----


async def _get_membership_or_404(
    membership_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> OrganizationMembership:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="メンバーシップが見つかりません")
    return membership


async def _count_owners(org_id: uuid.UUID, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.org_role == "owner",
        )
    )
    return result.scalar_one()


async def _check_membership(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> OrganizationMembership:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="この団体のメンバーではありません")
    return membership


async def _check_admin(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> OrganizationMembership:
    membership = await _check_membership(org_id, user_id, db)
    if membership.org_role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="管理者権限が必要です")
    return membership

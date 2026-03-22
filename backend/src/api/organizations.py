import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import Organization, OrganizationMembership
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.organizations import (
    OrganizationCreate,
    OrganizationDetailResponse,
    OrganizationMemberResponse,
    OrganizationResponse,
    OrganizationUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """自分が所属する団体の一覧を取得"""
    stmt = (
        select(Organization)
        .join(OrganizationMembership)
        .where(OrganizationMembership.user_id == current_user.id)
        .order_by(Organization.created_at.desc())
    )
    result = await db.execute(stmt)
    orgs = result.scalars().all()

    responses = []
    for org in orgs:
        count_stmt = (
            select(func.count())
            .select_from(OrganizationMembership)
            .where(OrganizationMembership.organization_id == org.id)
        )
        count_result = await db.execute(count_stmt)
        member_count = count_result.scalar_one()
        resp = OrganizationResponse.model_validate(org)
        resp.member_count = member_count
        responses.append(resp)
    return responses


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrganizationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """団体を作成し、作成者をオーナーとして登録"""
    org = Organization(
        name=body.name,
        description=body.description,
    )
    if body.cast_default_capabilities is not None:
        org.cast_default_capabilities = body.cast_default_capabilities
    db.add(org)
    await db.flush()

    membership = OrganizationMembership(
        user_id=current_user.id,
        organization_id=org.id,
        org_role="owner",
    )
    db.add(membership)
    await db.flush()

    resp = OrganizationResponse.model_validate(org)
    resp.member_count = 1
    return resp


@router.get("/{org_id}", response_model=OrganizationDetailResponse)
async def get_organization(
    org_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """団体の詳細を取得（メンバー一覧含む）"""
    org = await _get_org_or_404(org_id, db)
    await _check_membership(org_id, current_user.id, db)

    stmt = (
        select(OrganizationMembership)
        .where(OrganizationMembership.organization_id == org_id)
        .options(selectinload(OrganizationMembership.user))
    )
    result = await db.execute(stmt)
    memberships = result.scalars().all()

    members = [
        OrganizationMemberResponse(
            id=m.id,
            user_id=m.user_id,
            display_name=m.user.display_name,
            org_role=m.org_role,
            created_at=m.created_at,
        )
        for m in memberships
    ]

    org_resp = OrganizationResponse.model_validate(org)
    org_resp.member_count = len(members)
    return OrganizationDetailResponse(**org_resp.model_dump(), members=members)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: uuid.UUID,
    body: OrganizationUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """団体情報を更新（admin以上）"""
    org = await _get_org_or_404(org_id, db)
    await _check_admin(org_id, current_user.id, db)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(org, key, value)
    await db.flush()
    await db.refresh(org)

    count_stmt = (
        select(func.count()).select_from(OrganizationMembership).where(OrganizationMembership.organization_id == org_id)
    )
    count_result = await db.execute(count_stmt)
    resp = OrganizationResponse.model_validate(org)
    resp.member_count = count_result.scalar_one()
    return resp


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """団体を削除（ownerのみ）"""
    org = await _get_org_or_404(org_id, db)
    await _check_owner(org_id, current_user.id, db)
    await db.delete(org)


# ---- ヘルパー ----


async def _get_org_or_404(org_id: uuid.UUID, db: AsyncSession) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="団体が見つかりません")
    return org


async def _get_membership(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> OrganizationMembership | None:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def _check_membership(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> OrganizationMembership:
    membership = await _get_membership(org_id, user_id, db)
    if membership is None:
        raise HTTPException(status_code=403, detail="この団体のメンバーではありません")
    return membership


async def _check_admin(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> OrganizationMembership:
    membership = await _check_membership(org_id, user_id, db)
    if membership.org_role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="管理者権限が必要です")
    return membership


async def _check_owner(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> OrganizationMembership:
    membership = await _check_membership(org_id, user_id, db)
    if membership.org_role != "owner":
        raise HTTPException(status_code=403, detail="オーナー権限が必要です")
    return membership

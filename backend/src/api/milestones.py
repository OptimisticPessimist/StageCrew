import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.db.models import (
    Milestone,
    OrganizationMembership,
    Production,
    ProductionMembership,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.milestones import MilestoneCreate, MilestoneResponse, MilestoneUpdate

router = APIRouter()


@router.get("/", response_model=list[MilestoneResponse])
async def list_milestones(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """マイルストーン一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    stmt = (
        select(Milestone)
        .where(Milestone.production_id == production_id)
        .order_by(Milestone.date.asc().nulls_last(), Milestone.name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=MilestoneResponse, status_code=status.HTTP_201_CREATED)
async def create_milestone(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    body: MilestoneCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """マイルストーンを作成"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    milestone = Milestone(
        production_id=production_id,
        name=body.name,
        date=body.date,
        color=body.color,
    )
    db.add(milestone)
    await db.flush()
    return milestone


@router.patch("/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    milestone_id: uuid.UUID,
    body: MilestoneUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """マイルストーンを更新"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    milestone = await _get_milestone_or_404(milestone_id, production_id, db)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(milestone, key, value)
    await db.flush()
    await db.refresh(milestone)
    return milestone


@router.delete("/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_milestone(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    milestone_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """マイルストーンを削除"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    milestone = await _get_milestone_or_404(milestone_id, production_id, db)
    await db.delete(milestone)


# ---- ヘルパー ----


async def _get_production_or_404(production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Production:
    result = await db.execute(
        select(Production).where(Production.id == production_id, Production.organization_id == org_id)
    )
    production = result.scalar_one_or_none()
    if production is None:
        raise HTTPException(status_code=404, detail="公演が見つかりません")
    return production


async def _get_milestone_or_404(milestone_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession) -> Milestone:
    result = await db.execute(
        select(Milestone).where(Milestone.id == milestone_id, Milestone.production_id == production_id)
    )
    milestone = result.scalar_one_or_none()
    if milestone is None:
        raise HTTPException(status_code=404, detail="マイルストーンが見つかりません")
    return milestone


async def _check_org_membership(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="この団体のメンバーではありません")


async def _check_org_admin_or_production_manager(
    org_id: uuid.UUID, production_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> None:
    org_result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    org_membership = org_result.scalar_one_or_none()
    if org_membership is None:
        raise HTTPException(status_code=403, detail="この団体のメンバーではありません")
    if org_membership.org_role in ("owner", "admin"):
        return

    prod_result = await db.execute(
        select(ProductionMembership).where(
            ProductionMembership.production_id == production_id,
            ProductionMembership.user_id == user_id,
        )
    )
    prod_membership = prod_result.scalar_one_or_none()
    if prod_membership is None or prod_membership.production_role != "manager":
        raise HTTPException(status_code=403, detail="公演管理者または団体管理者の権限が必要です")

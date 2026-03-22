import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.db.models import (
    OrganizationMembership,
    Production,
    ProductionMembership,
    ProductionPhase,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.phases import PhaseCreate, PhaseResponse, PhaseUpdate

router = APIRouter()


@router.get("/", response_model=list[PhaseResponse])
async def list_phases(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演フェーズ一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    stmt = (
        select(ProductionPhase)
        .where(ProductionPhase.production_id == production_id)
        .order_by(ProductionPhase.sort_order, ProductionPhase.name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=PhaseResponse, status_code=status.HTTP_201_CREATED)
async def create_phase(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    body: PhaseCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演フェーズを作成"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    phase = ProductionPhase(
        production_id=production_id,
        name=body.name,
        sort_order=body.sort_order,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    db.add(phase)
    await db.flush()
    return phase


@router.patch("/{phase_id}", response_model=PhaseResponse)
async def update_phase(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    phase_id: uuid.UUID,
    body: PhaseUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演フェーズを更新"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    phase = await _get_phase_or_404(phase_id, production_id, db)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(phase, key, value)
    await db.flush()
    await db.refresh(phase)
    return phase


@router.delete("/{phase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phase(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    phase_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演フェーズを削除"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    phase = await _get_phase_or_404(phase_id, production_id, db)
    await db.delete(phase)


# ---- ヘルパー ----


async def _get_production_or_404(production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Production:
    result = await db.execute(
        select(Production).where(Production.id == production_id, Production.organization_id == org_id)
    )
    production = result.scalar_one_or_none()
    if production is None:
        raise HTTPException(status_code=404, detail="公演が見つかりません")
    return production


async def _get_phase_or_404(phase_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession) -> ProductionPhase:
    result = await db.execute(
        select(ProductionPhase).where(ProductionPhase.id == phase_id, ProductionPhase.production_id == production_id)
    )
    phase = result.scalar_one_or_none()
    if phase is None:
        raise HTTPException(status_code=404, detail="フェーズが見つかりません")
    return phase


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

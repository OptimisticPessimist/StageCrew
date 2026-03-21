import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.db.models import (
    Organization,
    OrganizationMembership,
    Production,
    ProductionMembership,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.productions import (
    ProductionCreate,
    ProductionListResponse,
    ProductionResponse,
    ProductionUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[ProductionListResponse])
async def list_productions(
    org_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """団体内の公演一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)

    stmt = (
        select(Production)
        .where(Production.organization_id == org_id)
        .order_by(Production.opening_date.desc().nullslast(), Production.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=ProductionResponse, status_code=status.HTTP_201_CREATED)
async def create_production(
    org_id: uuid.UUID,
    body: ProductionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演を作成し、作成者をmanagerとして登録"""
    await _check_org_admin(org_id, current_user.id, db)

    production = Production(
        organization_id=org_id,
        name=body.name,
        description=body.description,
        production_type=body.production_type,
        opening_date=body.opening_date,
        closing_date=body.closing_date,
        discord_webhook_url=body.discord_webhook_url,
    )
    db.add(production)
    await db.flush()

    membership = ProductionMembership(
        user_id=current_user.id,
        production_id=production.id,
        production_role="manager",
    )
    db.add(membership)
    await db.flush()

    return production


@router.get("/{production_id}", response_model=ProductionResponse)
async def get_production(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演の詳細を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    production = await _get_production_or_404(production_id, org_id, db)
    return production


@router.patch("/{production_id}", response_model=ProductionResponse)
async def update_production(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    body: ProductionUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演情報を更新（公演managerまたは団体admin以上）"""
    production = await _get_production_or_404(production_id, org_id, db)
    await _check_production_manager_or_org_admin(org_id, production_id, current_user.id, db)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(production, key, value)
    await db.flush()
    await db.refresh(production)
    return production


@router.delete("/{production_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_production(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演を削除（団体admin以上）"""
    production = await _get_production_or_404(production_id, org_id, db)
    await _check_org_admin(org_id, current_user.id, db)
    await db.delete(production)


# ---- ヘルパー ----

async def _get_production_or_404(production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Production:
    result = await db.execute(
        select(Production).where(Production.id == production_id, Production.organization_id == org_id)
    )
    production = result.scalar_one_or_none()
    if production is None:
        raise HTTPException(status_code=404, detail="公演が見つかりません")
    return production


async def _check_org_membership(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="この団体のメンバーではありません")


async def _check_org_admin(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
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


async def _check_production_manager_or_org_admin(
    org_id: uuid.UUID, production_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> None:
    # 団体admin以上ならOK
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

    # 公演managerならOK
    prod_result = await db.execute(
        select(ProductionMembership).where(
            ProductionMembership.production_id == production_id,
            ProductionMembership.user_id == user_id,
        )
    )
    prod_membership = prod_result.scalar_one_or_none()
    if prod_membership is None or prod_membership.production_role != "manager":
        raise HTTPException(status_code=403, detail="公演管理者または団体管理者の権限が必要です")

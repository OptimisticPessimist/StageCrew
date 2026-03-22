import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.db.models import OrganizationMembership, Production, StatusDefinition
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.statuses import StatusCreate, StatusResponse, StatusUpdate

router = APIRouter()


@router.get("/", response_model=list[StatusResponse])
async def list_statuses(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    department_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演のステータス定義一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    stmt = (
        select(StatusDefinition)
        .where(StatusDefinition.production_id == production_id)
        .order_by(StatusDefinition.sort_order, StatusDefinition.name)
    )
    if department_id is not None:
        stmt = stmt.where(StatusDefinition.department_id == department_id)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_status(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    body: StatusCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ステータス定義を作成"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)

    status_def = StatusDefinition(
        production_id=production_id,
        department_id=body.department_id,
        name=body.name,
        color=body.color,
        sort_order=body.sort_order,
        is_closed=body.is_closed,
    )
    db.add(status_def)
    await db.flush()
    return status_def


@router.patch("/{status_id}", response_model=StatusResponse)
async def update_status(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    status_id: uuid.UUID,
    body: StatusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ステータス定義を更新"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    status_def = await _get_status_or_404(status_id, production_id, db)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(status_def, key, value)
    await db.flush()
    await db.refresh(status_def)
    return status_def


@router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_status(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    status_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ステータス定義を削除"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    status_def = await _get_status_or_404(status_id, production_id, db)
    await db.delete(status_def)


# ---- ヘルパー ----


async def _get_production_or_404(production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Production:
    result = await db.execute(
        select(Production).where(Production.id == production_id, Production.organization_id == org_id)
    )
    production = result.scalar_one_or_none()
    if production is None:
        raise HTTPException(status_code=404, detail="公演が見つかりません")
    return production


async def _get_status_or_404(status_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession) -> StatusDefinition:
    result = await db.execute(
        select(StatusDefinition).where(
            StatusDefinition.id == status_id, StatusDefinition.production_id == production_id
        )
    )
    status_def = result.scalar_one_or_none()
    if status_def is None:
        raise HTTPException(status_code=404, detail="ステータスが見つかりません")
    return status_def


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
    from src.db.models import ProductionMembership

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

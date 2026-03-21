import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import (
    DepartmentMembership,
    OrganizationMembership,
    Production,
    ProductionMembership,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.members import (
    DeptMembershipBrief,
    ProductionMemberAdd,
    ProductionMemberResponse,
    ProductionMemberUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[ProductionMemberResponse])
async def list_production_members(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演メンバー一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    stmt = (
        select(ProductionMembership)
        .where(ProductionMembership.production_id == production_id)
        .options(
            selectinload(ProductionMembership.user),
            selectinload(ProductionMembership.department_memberships).selectinload(
                DepartmentMembership.department
            ),
            selectinload(ProductionMembership.department_memberships).selectinload(
                DepartmentMembership.staff_role
            ),
        )
        .order_by(ProductionMembership.created_at)
    )
    result = await db.execute(stmt)
    memberships = result.scalars().all()

    return [_to_response(m) for m in memberships]


@router.post("/", response_model=ProductionMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_production_member(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    body: ProductionMemberAdd,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演にメンバーを追加（団体メンバーであること必須）"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    # 団体メンバーであることを確認
    org_membership = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == body.user_id,
        )
    )
    if org_membership.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="団体メンバーでないユーザーは追加できません")

    # 重複チェック
    existing = await db.execute(
        select(ProductionMembership).where(
            ProductionMembership.production_id == production_id,
            ProductionMembership.user_id == body.user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="既に公演メンバーです")

    membership = ProductionMembership(
        user_id=body.user_id,
        production_id=production_id,
        production_role=body.production_role,
        is_cast=body.is_cast,
    )
    db.add(membership)
    await db.flush()

    # Re-fetch with relationships
    stmt = (
        select(ProductionMembership)
        .where(ProductionMembership.id == membership.id)
        .options(
            selectinload(ProductionMembership.user),
            selectinload(ProductionMembership.department_memberships).selectinload(
                DepartmentMembership.department
            ),
            selectinload(ProductionMembership.department_memberships).selectinload(
                DepartmentMembership.staff_role
            ),
        )
    )
    result = await db.execute(stmt)
    return _to_response(result.scalar_one())


@router.patch("/{membership_id}", response_model=ProductionMemberResponse)
async def update_production_member(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    membership_id: uuid.UUID,
    body: ProductionMemberUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演メンバーのロール・キャスト設定を変更"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    membership = await _get_production_membership_or_404(membership_id, production_id, db)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(membership, key, value)
    await db.flush()

    # Re-fetch with relationships
    stmt = (
        select(ProductionMembership)
        .where(ProductionMembership.id == membership_id)
        .options(
            selectinload(ProductionMembership.user),
            selectinload(ProductionMembership.department_memberships).selectinload(
                DepartmentMembership.department
            ),
            selectinload(ProductionMembership.department_memberships).selectinload(
                DepartmentMembership.staff_role
            ),
        )
    )
    result = await db.execute(stmt)
    return _to_response(result.scalar_one())


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_production_member(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    membership_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演からメンバーを除外"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    membership = await _get_production_membership_or_404(membership_id, production_id, db)
    await db.delete(membership)


# ---- ヘルパー ----


def _to_response(m: ProductionMembership) -> ProductionMemberResponse:
    dept_briefs = [
        DeptMembershipBrief(
            id=dm.id,
            department_id=dm.department_id,
            department_name=dm.department.name,
            staff_role_id=dm.staff_role_id,
            staff_role_name=dm.staff_role.name if dm.staff_role else None,
            capabilities=dm.capabilities,
        )
        for dm in m.department_memberships
    ]
    return ProductionMemberResponse(
        id=m.id,
        user_id=m.user_id,
        display_name=m.user.display_name,
        production_role=m.production_role,
        is_cast=m.is_cast,
        cast_capabilities=m.cast_capabilities,
        created_at=m.created_at,
        department_memberships=dept_briefs,
    )


async def _get_production_or_404(
    production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> Production:
    result = await db.execute(
        select(Production).where(Production.id == production_id, Production.organization_id == org_id)
    )
    production = result.scalar_one_or_none()
    if production is None:
        raise HTTPException(status_code=404, detail="公演が見つかりません")
    return production


async def _get_production_membership_or_404(
    membership_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession
) -> ProductionMembership:
    result = await db.execute(
        select(ProductionMembership).where(
            ProductionMembership.id == membership_id,
            ProductionMembership.production_id == production_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="公演メンバーシップが見つかりません")
    return membership


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

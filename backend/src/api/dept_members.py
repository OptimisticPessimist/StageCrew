import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import (
    Department,
    DepartmentMembership,
    OrganizationMembership,
    ProductionMembership,
    StaffRole,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.members import DeptMemberAdd, DeptMemberResponse, DeptMemberUpdate

router = APIRouter()


@router.get("/", response_model=list[DeptMemberResponse])
async def list_dept_members(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    dept_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """部門メンバー一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)

    stmt = (
        select(DepartmentMembership)
        .where(DepartmentMembership.department_id == dept_id)
        .options(
            selectinload(DepartmentMembership.production_membership).selectinload(
                ProductionMembership.user
            ),
            selectinload(DepartmentMembership.staff_role),
        )
        .order_by(DepartmentMembership.created_at)
    )
    result = await db.execute(stmt)
    memberships = result.scalars().all()

    return [_to_response(m) for m in memberships]


@router.post("/", response_model=DeptMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_dept_member(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    dept_id: uuid.UUID,
    body: DeptMemberAdd,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """部門にメンバーを追加"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_department_or_404(dept_id, production_id, db)

    # production_membership_idの確認
    pm_result = await db.execute(
        select(ProductionMembership).where(
            ProductionMembership.id == body.production_membership_id,
            ProductionMembership.production_id == production_id,
        )
    )
    if pm_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=400, detail="公演メンバーシップが見つかりません")

    # 重複チェック
    existing = await db.execute(
        select(DepartmentMembership).where(
            DepartmentMembership.production_membership_id == body.production_membership_id,
            DepartmentMembership.department_id == dept_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="既にこの部門のメンバーです")

    # staff_role_idの検証
    if body.staff_role_id is not None:
        role_result = await db.execute(
            select(StaffRole).where(
                StaffRole.id == body.staff_role_id,
                StaffRole.department_id == dept_id,
            )
        )
        if role_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail="スタッフロールが見つかりません")

    membership = DepartmentMembership(
        production_membership_id=body.production_membership_id,
        department_id=dept_id,
        staff_role_id=body.staff_role_id,
        capabilities=body.capabilities or ["task.view", "task.create", "task.edit_dept", "task.assign", "comment.create"],
    )
    db.add(membership)
    await db.flush()

    # Re-fetch with relationships
    stmt = (
        select(DepartmentMembership)
        .where(DepartmentMembership.id == membership.id)
        .options(
            selectinload(DepartmentMembership.production_membership).selectinload(
                ProductionMembership.user
            ),
            selectinload(DepartmentMembership.staff_role),
        )
    )
    result = await db.execute(stmt)
    return _to_response(result.scalar_one())


@router.patch("/{membership_id}", response_model=DeptMemberResponse)
async def update_dept_member(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    dept_id: uuid.UUID,
    membership_id: uuid.UUID,
    body: DeptMemberUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """部門メンバーのロール・権限を変更"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    membership = await _get_dept_membership_or_404(membership_id, dept_id, db)

    if body.staff_role_id is not None:
        role_result = await db.execute(
            select(StaffRole).where(
                StaffRole.id == body.staff_role_id,
                StaffRole.department_id == dept_id,
            )
        )
        if role_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail="スタッフロールが見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(membership, key, value)
    await db.flush()

    # Re-fetch with relationships
    stmt = (
        select(DepartmentMembership)
        .where(DepartmentMembership.id == membership_id)
        .options(
            selectinload(DepartmentMembership.production_membership).selectinload(
                ProductionMembership.user
            ),
            selectinload(DepartmentMembership.staff_role),
        )
    )
    result = await db.execute(stmt)
    return _to_response(result.scalar_one())


@router.delete("/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_dept_member(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    dept_id: uuid.UUID,
    membership_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """部門からメンバーを除外"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    membership = await _get_dept_membership_or_404(membership_id, dept_id, db)
    await db.delete(membership)


# ---- ヘルパー ----


def _to_response(m: DepartmentMembership) -> DeptMemberResponse:
    return DeptMemberResponse(
        id=m.id,
        production_membership_id=m.production_membership_id,
        user_id=m.production_membership.user_id,
        display_name=m.production_membership.user.display_name,
        department_id=m.department_id,
        staff_role_id=m.staff_role_id,
        staff_role_name=m.staff_role.name if m.staff_role else None,
        capabilities=m.capabilities,
        created_at=m.created_at,
    )


async def _get_department_or_404(
    dept_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession
) -> Department:
    result = await db.execute(
        select(Department).where(Department.id == dept_id, Department.production_id == production_id)
    )
    dept = result.scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=404, detail="部門が見つかりません")
    return dept


async def _get_dept_membership_or_404(
    membership_id: uuid.UUID, dept_id: uuid.UUID, db: AsyncSession
) -> DepartmentMembership:
    result = await db.execute(
        select(DepartmentMembership).where(
            DepartmentMembership.id == membership_id,
            DepartmentMembership.department_id == dept_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="部門メンバーシップが見つかりません")
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

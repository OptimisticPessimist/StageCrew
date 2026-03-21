import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import (
    Department,
    OrganizationMembership,
    Production,
    ProductionMembership,
    StaffRole,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.departments import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    StaffRoleCreate,
    StaffRoleResponse,
    StaffRoleUpdate,
)

router = APIRouter()


# ============================================================
# Department CRUD
# ============================================================


@router.get("/", response_model=list[DepartmentResponse])
async def list_departments(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演の部門一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    stmt = (
        select(Department)
        .where(Department.production_id == production_id)
        .options(selectinload(Department.staff_roles))
        .order_by(Department.sort_order, Department.name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    body: DepartmentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """部門を作成（スタッフロール一括作成可）"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    dept = Department(
        production_id=production_id,
        name=body.name,
        color=body.color,
        sort_order=body.sort_order,
    )
    db.add(dept)
    await db.flush()

    if body.staff_roles:
        for role_data in body.staff_roles:
            role = StaffRole(
                department_id=dept.id,
                name=role_data.name,
                sort_order=role_data.sort_order,
            )
            db.add(role)
        await db.flush()

    # Eager load staff_roles for response
    stmt = (
        select(Department)
        .where(Department.id == dept.id)
        .options(selectinload(Department.staff_roles))
    )
    result = await db.execute(stmt)
    return result.scalar_one()


@router.get("/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    dept_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """部門の詳細を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    stmt = (
        select(Department)
        .where(Department.id == dept_id, Department.production_id == production_id)
        .options(selectinload(Department.staff_roles))
    )
    result = await db.execute(stmt)
    dept = result.scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=404, detail="部門が見つかりません")
    return dept


@router.patch("/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    dept_id: uuid.UUID,
    body: DepartmentUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """部門情報を更新"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    dept = await _get_department_or_404(dept_id, production_id, db)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dept, key, value)
    await db.flush()

    stmt = (
        select(Department)
        .where(Department.id == dept.id)
        .options(selectinload(Department.staff_roles))
    )
    result = await db.execute(stmt)
    return result.scalar_one()


@router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    dept_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """部門を削除"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    dept = await _get_department_or_404(dept_id, production_id, db)
    await db.delete(dept)


# ============================================================
# StaffRole CRUD
# ============================================================


@router.get("/{dept_id}/staff-roles", response_model=list[StaffRoleResponse])
async def list_staff_roles(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    dept_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """部門のスタッフロール一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_department_or_404(dept_id, production_id, db)

    stmt = (
        select(StaffRole)
        .where(StaffRole.department_id == dept_id)
        .order_by(StaffRole.sort_order, StaffRole.name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{dept_id}/staff-roles", response_model=StaffRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_staff_role(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    dept_id: uuid.UUID,
    body: StaffRoleCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """スタッフロールを作成"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_department_or_404(dept_id, production_id, db)

    role = StaffRole(
        department_id=dept_id,
        name=body.name,
        sort_order=body.sort_order,
    )
    db.add(role)
    await db.flush()
    return role


@router.patch("/{dept_id}/staff-roles/{role_id}", response_model=StaffRoleResponse)
async def update_staff_role(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    dept_id: uuid.UUID,
    role_id: uuid.UUID,
    body: StaffRoleUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """スタッフロールを更新"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_department_or_404(dept_id, production_id, db)
    role = await _get_staff_role_or_404(role_id, dept_id, db)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(role, key, value)
    await db.flush()
    await db.refresh(role)
    return role


@router.delete("/{dept_id}/staff-roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staff_role(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    dept_id: uuid.UUID,
    role_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """スタッフロールを削除"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_department_or_404(dept_id, production_id, db)
    role = await _get_staff_role_or_404(role_id, dept_id, db)
    await db.delete(role)


# ---- ヘルパー ----


async def _get_production_or_404(production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Production:
    result = await db.execute(
        select(Production).where(Production.id == production_id, Production.organization_id == org_id)
    )
    production = result.scalar_one_or_none()
    if production is None:
        raise HTTPException(status_code=404, detail="公演が見つかりません")
    return production


async def _get_department_or_404(dept_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession) -> Department:
    result = await db.execute(
        select(Department).where(Department.id == dept_id, Department.production_id == production_id)
    )
    dept = result.scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=404, detail="部門が見つかりません")
    return dept


async def _get_staff_role_or_404(role_id: uuid.UUID, dept_id: uuid.UUID, db: AsyncSession) -> StaffRole:
    result = await db.execute(
        select(StaffRole).where(StaffRole.id == role_id, StaffRole.department_id == dept_id)
    )
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="スタッフロールが見つかりません")
    return role


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

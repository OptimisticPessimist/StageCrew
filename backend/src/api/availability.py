import uuid
from datetime import date as date_type
from datetime import time as time_type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.db.models import (
    OrganizationMembership,
    Production,
    ProductionMembership,
    UserAvailability,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.availability import (
    AVAILABILITY_VALUES,
    AvailabilityBulkUpsert,
    AvailabilityCreate,
    AvailabilityResponse,
    AvailabilityUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[AvailabilityResponse])
async def list_availabilities(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """空き状況一覧（user_id 未指定はマネージャーのみ）"""
    # list/update/delete を統一: org owner/admin 含め全操作で production membership 必須。
    # _check_production_member が org_membership・production 存在・production_membership を一括確認。
    await _check_production_member(org_id, production_id, current_user.id, db)

    is_manager = await _is_admin_or_manager(org_id, production_id, current_user.id, db)
    target_user_id = user_id if user_id is not None else current_user.id
    if target_user_id != current_user.id and not is_manager:
        raise HTTPException(status_code=403, detail="他メンバーの空き状況閲覧には権限が必要です")

    stmt = select(UserAvailability).where(UserAvailability.production_id == production_id)
    if user_id is not None:
        stmt = stmt.where(UserAvailability.user_id == user_id)
    elif not is_manager:
        stmt = stmt.where(UserAvailability.user_id == current_user.id)
    if date_from is not None:
        stmt = stmt.where(UserAvailability.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(UserAvailability.date <= date_to)
    stmt = stmt.order_by(UserAvailability.date.asc(), UserAvailability.start_time.asc())

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=AvailabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_availability(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    body: AvailabilityCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """本人の空き状況を登録（同日のエントリがある場合は上書き）"""
    await _check_production_member(org_id, production_id, current_user.id, db)
    _validate_availability(body.availability)
    _validate_time_order(body.start_time, body.end_time)

    row = await _upsert_availability(
        user_id=current_user.id,
        production_id=production_id,
        item=body,
        db=db,
    )
    try:
        await db.flush()
    except IntegrityError as exc:
        # 並行リクエストで同一 (user, production, date) の INSERT が競合した場合
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同一日付の空き状況が同時に登録されました。再試行してください",
        ) from exc
    await db.refresh(row)
    return row


@router.post("/bulk", response_model=list[AvailabilityResponse])
async def bulk_upsert_availabilities(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    body: AvailabilityBulkUpsert,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """本人の空き状況を一括登録（同日のエントリがある場合は上書き）"""
    await _check_production_member(org_id, production_id, current_user.id, db)

    # 入力バリデーションを先に全件行う（途中失敗時の部分適用を避けるため）
    for item in body.items:
        _validate_availability(item.availability)
        _validate_time_order(item.start_time, item.end_time)

    # 同一リクエスト内で date が重複している場合は後勝ちで正規化
    by_date: dict[date_type, AvailabilityCreate] = {}
    for item in body.items:
        by_date[item.date] = item

    rows: list[UserAvailability] = []
    for item in by_date.values():
        row = await _upsert_availability(
            user_id=current_user.id,
            production_id=production_id,
            item=item,
            db=db,
        )
        rows.append(row)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同一日付の空き状況が同時に登録されました。再試行してください",
        ) from exc
    for row in rows:
        await db.refresh(row)
    rows.sort(key=lambda r: (r.date, r.start_time or time_type.min))
    return rows


@router.patch("/{availability_id}", response_model=AvailabilityResponse)
async def update_availability(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    availability_id: uuid.UUID,
    body: AvailabilityUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """空き状況を更新（本人のみ）"""
    await _check_production_member(org_id, production_id, current_user.id, db)
    row = await _get_availability_or_404(availability_id, production_id, db)
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="自分の空き状況のみ編集できます")

    update_data = body.model_dump(exclude_unset=True)
    if "availability" in update_data and update_data["availability"] is not None:
        _validate_availability(update_data["availability"])
    for key, value in update_data.items():
        setattr(row, key, value)
    _validate_time_order(row.start_time, row.end_time)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="空き状況が並行して更新されました。再試行してください",
        ) from exc
    await db.refresh(row)
    return row


@router.delete("/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_availability(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    availability_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """空き状況を削除（本人のみ）"""
    await _check_production_member(org_id, production_id, current_user.id, db)
    row = await _get_availability_or_404(availability_id, production_id, db)
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="自分の空き状況のみ削除できます")
    await db.delete(row)


# ============================================================
# ヘルパー
# ============================================================


async def _upsert_availability(
    user_id: uuid.UUID,
    production_id: uuid.UUID,
    item: AvailabilityCreate,
    db: AsyncSession,
) -> UserAvailability:
    """(user_id, production_id, date) の自然キーで upsert する。"""
    existing = await db.execute(
        select(UserAvailability).where(
            UserAvailability.user_id == user_id,
            UserAvailability.production_id == production_id,
            UserAvailability.date == item.date,
        )
    )
    row = existing.scalar_one_or_none()
    if row is None:
        row = UserAvailability(
            user_id=user_id,
            production_id=production_id,
            date=item.date,
            availability=item.availability,
            start_time=item.start_time,
            end_time=item.end_time,
            note=item.note,
        )
        db.add(row)
    else:
        row.availability = item.availability
        row.start_time = item.start_time
        row.end_time = item.end_time
        row.note = item.note
    return row


def _validate_availability(value: str) -> None:
    if value not in AVAILABILITY_VALUES:
        raise HTTPException(status_code=422, detail="availability が不正です")


def _validate_time_order(start_time, end_time) -> None:
    if start_time is not None and end_time is not None and end_time <= start_time:
        raise HTTPException(status_code=422, detail="end_time は start_time より後である必要があります")


async def _get_production_or_404(production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Production:
    result = await db.execute(
        select(Production).where(Production.id == production_id, Production.organization_id == org_id)
    )
    production = result.scalar_one_or_none()
    if production is None:
        raise HTTPException(status_code=404, detail="公演が見つかりません")
    return production


async def _get_availability_or_404(
    availability_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession
) -> UserAvailability:
    result = await db.execute(
        select(UserAvailability).where(
            UserAvailability.id == availability_id,
            UserAvailability.production_id == production_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="空き状況が見つかりません")
    return row


async def _check_org_membership(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="この団体のメンバーではありません")


async def _check_production_member(
    org_id: uuid.UUID, production_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> None:
    await _check_org_membership(org_id, user_id, db)
    await _get_production_or_404(production_id, org_id, db)
    await _check_production_membership(production_id, user_id, db)


async def _check_production_membership(production_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    """production_id への ProductionMembership 有無のみを検査する（org/production 存在は呼び出し側で確認）。"""
    result = await db.execute(
        select(ProductionMembership).where(
            ProductionMembership.production_id == production_id,
            ProductionMembership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="公演メンバーではありません")


async def _is_admin_or_manager(
    org_id: uuid.UUID, production_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> bool:
    org_result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    org_membership = org_result.scalar_one_or_none()
    if org_membership is None:
        return False
    if org_membership.org_role in ("owner", "admin"):
        return True
    prod_result = await db.execute(
        select(ProductionMembership).where(
            ProductionMembership.production_id == production_id,
            ProductionMembership.user_id == user_id,
        )
    )
    prod_membership = prod_result.scalar_one_or_none()
    return prod_membership is not None and prod_membership.production_role == "manager"

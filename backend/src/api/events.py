import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import (
    Event,
    EventAttendee,
    EventScene,
    OrganizationMembership,
    Production,
    ProductionMembership,
    Scene,
    Script,
    User,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.events import (
    ACTUAL_ATTENDANCES,
    ATTENDANCE_TYPES,
    EVENT_TYPES,
    RSVP_STATUSES,
    AttendeeAdd,
    AttendeeResponse,
    AttendeeUpdate,
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventSceneResponse,
    EventUpdate,
)

router = APIRouter()


# ============================================================
# Event CRUD
# ============================================================


@router.get("/", response_model=list[EventResponse])
async def list_events(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    start_from: datetime | None = None,
    start_to: datetime | None = None,
    event_type: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演のイベント一覧を取得（日付範囲フィルタ対応）"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)
    await _check_production_membership(production_id, current_user.id, db)

    stmt = select(Event).where(Event.production_id == production_id).order_by(Event.start_at.asc())
    if start_from is not None:
        stmt = stmt.where(Event.start_at >= start_from)
    if start_to is not None:
        stmt = stmt.where(Event.start_at < start_to)
    if event_type is not None:
        stmt = stmt.where(Event.event_type == event_type)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=EventDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    body: EventCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """イベントを作成"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)
    await _check_production_membership(production_id, current_user.id, db)
    _validate_event_type(body.event_type)
    _validate_time_range(body.start_at, body.end_at)

    event = Event(
        production_id=production_id,
        event_type=body.event_type,
        title=body.title,
        description=body.description,
        start_at=body.start_at,
        end_at=body.end_at,
        is_all_day=body.is_all_day,
        location_name=body.location_name,
        location_url=body.location_url,
        created_by=current_user.id,
    )
    db.add(event)
    try:
        await db.flush()
        if body.scene_ids:
            await _attach_scenes(event.id, production_id, body.scene_ids, db)
            await db.flush()
    except IntegrityError as exc:
        # FK 競合（scene の並行削除など）や uq_event_scene 競合を 500 化させない
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="イベント作成が並行リクエストと競合しました。再試行してください",
        ) from exc

    return await _load_event_detail(event.id, production_id, db)


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    event_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """イベント詳細を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)
    await _check_production_membership(production_id, current_user.id, db)
    return await _load_event_detail(event_id, production_id, db)


@router.patch("/{event_id}", response_model=EventDetailResponse)
async def update_event(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    event_id: uuid.UUID,
    body: EventUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """イベントを更新"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)
    await _check_production_membership(production_id, current_user.id, db)
    event = await _get_event_or_404(event_id, production_id, db)

    update_data = body.model_dump(exclude_unset=True)
    if "event_type" in update_data and update_data["event_type"] is not None:
        _validate_event_type(update_data["event_type"])

    scene_ids = update_data.pop("scene_ids", None)

    for key, value in update_data.items():
        setattr(event, key, value)

    _validate_time_range(event.start_at, event.end_at)

    if scene_ids is not None:
        await db.execute(delete(EventScene).where(EventScene.event_id == event.id))
        if scene_ids:
            await _attach_scenes(event.id, production_id, scene_ids, db)

    try:
        await db.flush()
    except IntegrityError as exc:
        # scene の並行更新で uq_event_scene / FK 競合が起きた場合に 500 を避ける
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="イベントが並行して更新されました。再試行してください",
        ) from exc
    return await _load_event_detail(event.id, production_id, db)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    event_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """イベントを削除"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)
    await _check_production_membership(production_id, current_user.id, db)
    event = await _get_event_or_404(event_id, production_id, db)
    await db.delete(event)


# ============================================================
# Attendees (RSVP)
# ============================================================


@router.post(
    "/{event_id}/attendees",
    response_model=list[AttendeeResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_attendees(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    event_id: uuid.UUID,
    body: AttendeeAdd,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """イベントに参加者（招集メンバー）を追加"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)
    await _check_production_membership(production_id, current_user.id, db)
    await _get_event_or_404(event_id, production_id, db)
    if body.attendance_type not in ATTENDANCE_TYPES:
        raise HTTPException(status_code=422, detail="attendance_type が不正です")

    # 公演メンバーのみ招集可
    valid_user_ids = await _filter_production_members(production_id, body.user_ids, db)
    if not valid_user_ids:
        raise HTTPException(status_code=422, detail="公演メンバーを指定してください")

    existing_stmt = select(EventAttendee.user_id).where(EventAttendee.event_id == event_id)
    existing = set((await db.execute(existing_stmt)).scalars().all())

    added_user_ids: list[uuid.UUID] = []
    for user_id in valid_user_ids:
        if user_id in existing:
            continue
        db.add(
            EventAttendee(
                event_id=event_id,
                user_id=user_id,
                attendance_type=body.attendance_type,
            )
        )
        added_user_ids.append(user_id)
    try:
        await db.flush()
    except IntegrityError as exc:
        # 並行追加で同一 (event_id, user_id) が競合した場合
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同じメンバーが並行して追加されました。再試行してください",
        ) from exc

    return await _load_attendees(event_id, db)


@router.patch("/{event_id}/attendees/{user_id}", response_model=AttendeeResponse)
async def update_attendee(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    body: AttendeeUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """参加者情報を更新（本人はRSVP、管理者は全て）"""
    # IDOR 対策: 認可・在籍確認を event/attendee lookup より先に行う。
    # org admin/owner を含む全ユーザーに production_membership を必須化し、
    # 未権限者に event/attendee 存在を推測させない。
    await _check_org_membership(org_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)
    await _check_production_membership(production_id, current_user.id, db)

    is_self = current_user.id == user_id
    is_manager = await _is_admin_or_manager(org_id, production_id, current_user.id, db)
    if not is_self and not is_manager:
        raise HTTPException(status_code=403, detail="権限がありません")

    await _get_event_or_404(event_id, production_id, db)

    attendee_stmt = (
        select(EventAttendee)
        .where(EventAttendee.event_id == event_id, EventAttendee.user_id == user_id)
        .options(selectinload(EventAttendee.user))
    )
    attendee = (await db.execute(attendee_stmt)).scalar_one_or_none()
    if attendee is None:
        raise HTTPException(status_code=404, detail="参加者が見つかりません")

    update_data = body.model_dump(exclude_unset=True)
    if not is_manager:
        # 本人は rsvp_status のみ変更可
        allowed = {k: v for k, v in update_data.items() if k == "rsvp_status"}
        if set(update_data.keys()) - {"rsvp_status"}:
            raise HTTPException(status_code=403, detail="本人は RSVP のみ変更できます")
        update_data = allowed

    if "rsvp_status" in update_data and update_data["rsvp_status"] is not None:
        if update_data["rsvp_status"] not in RSVP_STATUSES:
            raise HTTPException(status_code=422, detail="rsvp_status が不正です")
        attendee.rsvp_status = update_data["rsvp_status"]
        attendee.responded_at = datetime.now(UTC)

    if "attendance_type" in update_data and update_data["attendance_type"] is not None:
        if update_data["attendance_type"] not in ATTENDANCE_TYPES:
            raise HTTPException(status_code=422, detail="attendance_type が不正です")
        attendee.attendance_type = update_data["attendance_type"]

    if "actual_attendance" in update_data:
        value = update_data["actual_attendance"]
        if value is not None and value not in ACTUAL_ATTENDANCES:
            raise HTTPException(status_code=422, detail="actual_attendance が不正です")
        attendee.actual_attendance = value

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="参加者情報が並行して更新されました。再試行してください",
        ) from exc
    await db.refresh(attendee)
    return AttendeeResponse(
        id=attendee.id,
        user_id=attendee.user_id,
        display_name=attendee.user.display_name,
        attendance_type=attendee.attendance_type,
        rsvp_status=attendee.rsvp_status,
        actual_attendance=attendee.actual_attendance,
        responded_at=attendee.responded_at,
    )


@router.delete("/{event_id}/attendees/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_attendee(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """参加者を外す"""
    await _check_org_admin_or_production_manager(org_id, production_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)
    await _check_production_membership(production_id, current_user.id, db)
    await _get_event_or_404(event_id, production_id, db)

    result = await db.execute(
        select(EventAttendee).where(EventAttendee.event_id == event_id, EventAttendee.user_id == user_id)
    )
    attendee = result.scalar_one_or_none()
    if attendee is None:
        raise HTTPException(status_code=404, detail="参加者が見つかりません")
    await db.delete(attendee)


# ============================================================
# ヘルパー
# ============================================================


def _validate_event_type(event_type: str) -> None:
    if event_type not in EVENT_TYPES:
        raise HTTPException(status_code=422, detail="event_type が不正です")


def _validate_time_range(start_at: datetime | None, end_at: datetime | None) -> None:
    if start_at is not None and end_at is not None and end_at < start_at:
        raise HTTPException(status_code=422, detail="end_at は start_at 以降である必要があります")


async def _attach_scenes(
    event_id: uuid.UUID,
    production_id: uuid.UUID,
    scene_ids: list[uuid.UUID],
    db: AsyncSession,
) -> None:
    # 入力内の重複を除去（順序は維持）
    seen: set[uuid.UUID] = set()
    unique_ids: list[uuid.UUID] = []
    for sid in scene_ids:
        if sid not in seen:
            seen.add(sid)
            unique_ids.append(sid)
    if not unique_ids:
        return
    # 対象シーンが同じ公演の脚本に属するか検証
    stmt = (
        select(Scene.id)
        .join(Script, Scene.script_id == Script.id)
        .where(Scene.id.in_(unique_ids), Script.production_id == production_id)
    )
    valid = set((await db.execute(stmt)).scalars().all())
    invalid = [sid for sid in unique_ids if sid not in valid]
    if invalid:
        raise HTTPException(status_code=422, detail="対象外のシーンが含まれています")
    for sid in unique_ids:
        db.add(EventScene(event_id=event_id, scene_id=sid))


async def _filter_production_members(
    production_id: uuid.UUID, user_ids: list[uuid.UUID], db: AsyncSession
) -> list[uuid.UUID]:
    if not user_ids:
        return []
    stmt = select(ProductionMembership.user_id).where(
        ProductionMembership.production_id == production_id,
        ProductionMembership.user_id.in_(user_ids),
    )
    return list((await db.execute(stmt)).scalars().all())


async def _load_event_detail(event_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession) -> EventDetailResponse:
    stmt = (
        select(Event)
        .where(Event.id == event_id, Event.production_id == production_id)
        .options(
            selectinload(Event.attendees).selectinload(EventAttendee.user),
            selectinload(Event.event_scenes).selectinload(EventScene.scene),
        )
    )
    event = (await db.execute(stmt)).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="イベントが見つかりません")

    attendees = [
        AttendeeResponse(
            id=a.id,
            user_id=a.user_id,
            display_name=a.user.display_name,
            attendance_type=a.attendance_type,
            rsvp_status=a.rsvp_status,
            actual_attendance=a.actual_attendance,
            responded_at=a.responded_at,
        )
        for a in event.attendees
    ]
    scenes = [
        EventSceneResponse(
            scene_id=es.scene.id,
            heading=es.scene.heading,
            act_number=es.scene.act_number,
            scene_number=es.scene.scene_number,
        )
        for es in event.event_scenes
    ]
    return EventDetailResponse(
        id=event.id,
        production_id=event.production_id,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        start_at=event.start_at,
        end_at=event.end_at,
        is_all_day=event.is_all_day,
        location_name=event.location_name,
        location_url=event.location_url,
        created_by=event.created_by,
        created_at=event.created_at,
        updated_at=event.updated_at,
        attendees=attendees,
        scenes=scenes,
    )


async def _load_attendees(event_id: uuid.UUID, db: AsyncSession) -> list[AttendeeResponse]:
    stmt = (
        select(EventAttendee)
        .where(EventAttendee.event_id == event_id)
        .options(selectinload(EventAttendee.user))
        .order_by(EventAttendee.created_at)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        AttendeeResponse(
            id=a.id,
            user_id=a.user_id,
            display_name=a.user.display_name,
            attendance_type=a.attendance_type,
            rsvp_status=a.rsvp_status,
            actual_attendance=a.actual_attendance,
            responded_at=a.responded_at,
        )
        for a in rows
    ]


async def _get_production_or_404(production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Production:
    result = await db.execute(
        select(Production).where(Production.id == production_id, Production.organization_id == org_id)
    )
    production = result.scalar_one_or_none()
    if production is None:
        raise HTTPException(status_code=404, detail="公演が見つかりません")
    return production


async def _get_event_or_404(event_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession) -> Event:
    result = await db.execute(select(Event).where(Event.id == event_id, Event.production_id == production_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="イベントが見つかりません")
    return event


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
    if not await _is_admin_or_manager(org_id, production_id, user_id, db):
        raise HTTPException(status_code=403, detail="公演管理者または団体管理者の権限が必要です")


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


# ロード時の未使用インポート警告を避ける
_ = User

"""Event / EventAttendee / EventScene エンドポイントのテスト。"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Event, EventAttendee, EventScene, ProductionMembership


def _url(prod):
    return f"/api/organizations/{prod.organization_id}/productions/{prod.id}/events"


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


# ============================================================
# Event CRUD
# ============================================================


async def test_list_events_empty(client: AsyncClient, production):
    prod, _ = production
    resp = await client.get(f"{_url(prod)}/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_event_minimal(client: AsyncClient, production):
    prod, _ = production
    start = _now() + timedelta(days=1)
    resp = await client.post(
        f"{_url(prod)}/",
        json={"title": "通し稽古", "start_at": start.isoformat()},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["title"] == "通し稽古"
    assert data["event_type"] == "rehearsal"
    assert data["attendees"] == []
    assert data["scenes"] == []


async def test_create_event_with_scenes(client: AsyncClient, production, script, scene):
    prod, _ = production
    start = _now() + timedelta(days=1)
    resp = await client.post(
        f"{_url(prod)}/",
        json={
            "title": "シーン稽古",
            "event_type": "rehearsal",
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(hours=2)).isoformat(),
            "scene_ids": [str(scene.id)],
            "location_name": "スタジオA",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert len(data["scenes"]) == 1
    assert data["scenes"][0]["scene_id"] == str(scene.id)
    assert data["location_name"] == "スタジオA"


async def test_create_event_invalid_event_type(client: AsyncClient, production):
    prod, _ = production
    resp = await client.post(
        f"{_url(prod)}/",
        json={"title": "x", "event_type": "party", "start_at": _now().isoformat()},
    )
    assert resp.status_code == 422


async def test_create_event_end_before_start_rejected(client: AsyncClient, production):
    prod, _ = production
    start = _now()
    resp = await client.post(
        f"{_url(prod)}/",
        json={
            "title": "x",
            "start_at": start.isoformat(),
            "end_at": (start - timedelta(hours=1)).isoformat(),
        },
    )
    assert resp.status_code == 422


async def test_list_events_with_date_range(client: AsyncClient, production):
    prod, _ = production
    base = _now()
    for days in (1, 5, 10):
        await client.post(
            f"{_url(prod)}/",
            json={"title": f"イベント{days}", "start_at": (base + timedelta(days=days)).isoformat()},
        )
    resp = await client.get(
        f"{_url(prod)}/",
        params={
            "start_from": (base + timedelta(days=2)).isoformat(),
            "start_to": (base + timedelta(days=8)).isoformat(),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "イベント5"


async def test_update_event(client: AsyncClient, production):
    prod, _ = production
    start = _now()
    create = await client.post(f"{_url(prod)}/", json={"title": "old", "start_at": start.isoformat()})
    event_id = create.json()["id"]
    resp = await client.patch(f"{_url(prod)}/{event_id}", json={"title": "new", "description": "更新"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "new"
    assert data["description"] == "更新"


async def test_update_event_replace_scenes(client: AsyncClient, production, script, scene, db_session: AsyncSession):
    prod, _ = production
    start = _now()
    create = await client.post(
        f"{_url(prod)}/",
        json={"title": "scene-event", "start_at": start.isoformat(), "scene_ids": [str(scene.id)]},
    )
    event_id = create.json()["id"]

    resp = await client.patch(f"{_url(prod)}/{event_id}", json={"scene_ids": []})
    assert resp.status_code == 200
    assert resp.json()["scenes"] == []

    remaining = (
        await db_session.execute(EventScene.__table__.select().where(EventScene.event_id == uuid.UUID(event_id)))
    ).fetchall()
    assert len(remaining) == 0


async def test_update_event_invalid_scene(client: AsyncClient, production):
    prod, _ = production
    start = _now()
    create = await client.post(f"{_url(prod)}/", json={"title": "x", "start_at": start.isoformat()})
    event_id = create.json()["id"]
    resp = await client.patch(f"{_url(prod)}/{event_id}", json={"scene_ids": [str(uuid.uuid4())]})
    assert resp.status_code == 422


async def test_create_event_with_duplicate_scene_ids_dedupes(client: AsyncClient, production, script, scene):
    """scene_ids に同一IDが重複していても 500 にならず 1件として登録される（回帰）。"""
    prod, _ = production
    start = _now() + timedelta(days=1)
    resp = await client.post(
        f"{_url(prod)}/",
        json={
            "title": "dup",
            "start_at": start.isoformat(),
            "scene_ids": [str(scene.id), str(scene.id)],
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert len(data["scenes"]) == 1
    assert data["scenes"][0]["scene_id"] == str(scene.id)


async def test_create_event_rejects_non_http_url(client: AsyncClient, production):
    """location_url は http/https 以外のスキームを 422 で拒否する（セキュリティ回帰）。"""
    prod, _ = production
    start = _now() + timedelta(days=1)
    resp = await client.post(
        f"{_url(prod)}/",
        json={
            "title": "x",
            "start_at": start.isoformat(),
            "location_url": "javascript:alert(1)",
        },
    )
    assert resp.status_code == 422


async def test_update_event_rejects_null_for_notnull_fields(client: AsyncClient, production):
    """NOT NULL 列（title / event_type / start_at / is_all_day）への明示的 null PATCH は 422（回帰）。"""
    prod, _ = production
    start = _now() + timedelta(days=1)
    create = await client.post(f"{_url(prod)}/", json={"title": "x", "start_at": start.isoformat()})
    event_id = create.json()["id"]
    for payload in (
        {"title": None},
        {"event_type": None},
        {"start_at": None},
        {"is_all_day": None},
    ):
        resp = await client.patch(f"{_url(prod)}/{event_id}", json=payload)
        assert resp.status_code == 422, (payload, resp.text)


async def test_update_event_rejects_non_http_url(client: AsyncClient, production):
    """PATCH でも location_url は http/https 以外を拒否する。"""
    prod, _ = production
    start = _now() + timedelta(days=1)
    create = await client.post(f"{_url(prod)}/", json={"title": "x", "start_at": start.isoformat()})
    event_id = create.json()["id"]
    resp = await client.patch(
        f"{_url(prod)}/{event_id}",
        json={"location_url": "ftp://example.com/file"},
    )
    assert resp.status_code == 422


async def test_delete_event(client: AsyncClient, production):
    prod, _ = production
    start = _now()
    create = await client.post(f"{_url(prod)}/", json={"title": "del", "start_at": start.isoformat()})
    event_id = create.json()["id"]
    resp = await client.delete(f"{_url(prod)}/{event_id}")
    assert resp.status_code == 204
    get = await client.get(f"{_url(prod)}/{event_id}")
    assert get.status_code == 404


# ============================================================
# Attendees / RSVP
# ============================================================


@pytest.fixture
async def other_production_member(
    db_session: AsyncSession,
    org_with_member,
    production,
    other_user,
) -> ProductionMembership:
    """other_userを公演メンバー(member)として登録。"""
    prod, _ = production
    pm = ProductionMembership(
        user_id=other_user.id,
        production_id=prod.id,
        production_role="member",
    )
    db_session.add(pm)
    await db_session.flush()
    return pm


async def test_add_attendees(client: AsyncClient, production, other_user, other_production_member):
    prod, _ = production
    start = _now()
    ev = await client.post(f"{_url(prod)}/", json={"title": "稽古", "start_at": start.isoformat()})
    event_id = ev.json()["id"]

    resp = await client.post(
        f"{_url(prod)}/{event_id}/attendees",
        json={"user_ids": [str(other_user.id)], "attendance_type": "required"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == str(other_user.id)
    assert data[0]["rsvp_status"] == "pending"


async def test_add_attendees_non_member_filtered(client: AsyncClient, production, other_user):
    """other_userは公演メンバーでない → フィルタで除外され 422"""
    prod, _ = production
    start = _now()
    ev = await client.post(f"{_url(prod)}/", json={"title": "稽古", "start_at": start.isoformat()})
    event_id = ev.json()["id"]

    resp = await client.post(
        f"{_url(prod)}/{event_id}/attendees",
        json={"user_ids": [str(other_user.id)]},
    )
    assert resp.status_code == 422


@pytest.fixture
async def seeded_event_with_other_attendee(
    db_session: AsyncSession,
    production,
    test_user,
    other_user,
    other_production_member,
) -> Event:
    """事前にイベントと other_user の参加者をDBで直接作成（fixture競合回避）。"""
    prod, _ = production
    event = Event(
        production_id=prod.id,
        title="稽古",
        start_at=datetime.now(UTC),
        created_by=test_user.id,
    )
    db_session.add(event)
    await db_session.flush()
    db_session.add(EventAttendee(event_id=event.id, user_id=other_user.id))
    await db_session.flush()
    return event


async def test_rsvp_by_self(
    client_as_other: AsyncClient,
    production,
    other_user,
    seeded_event_with_other_attendee,
):
    """本人は rsvp_status を更新できる。"""
    prod, _ = production
    event = seeded_event_with_other_attendee

    resp = await client_as_other.patch(
        f"{_url(prod)}/{event.id}/attendees/{other_user.id}",
        json={"rsvp_status": "accepted"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["rsvp_status"] == "accepted"
    assert data["responded_at"] is not None


async def test_rsvp_by_self_cannot_change_attendance_type(
    client_as_other: AsyncClient,
    production,
    other_user,
    seeded_event_with_other_attendee,
):
    prod, _ = production
    event = seeded_event_with_other_attendee

    resp = await client_as_other.patch(
        f"{_url(prod)}/{event.id}/attendees/{other_user.id}",
        json={"attendance_type": "optional"},
    )
    assert resp.status_code == 403


async def test_manager_can_set_actual_attendance(client: AsyncClient, production, other_user, other_production_member):
    prod, _ = production
    start = _now()
    ev = await client.post(f"{_url(prod)}/", json={"title": "稽古", "start_at": start.isoformat()})
    event_id = ev.json()["id"]
    await client.post(f"{_url(prod)}/{event_id}/attendees", json={"user_ids": [str(other_user.id)]})

    resp = await client.patch(
        f"{_url(prod)}/{event_id}/attendees/{other_user.id}",
        json={"actual_attendance": "present"},
    )
    assert resp.status_code == 200
    assert resp.json()["actual_attendance"] == "present"


async def test_remove_attendee(client: AsyncClient, production, other_user, other_production_member):
    prod, _ = production
    start = _now()
    ev = await client.post(f"{_url(prod)}/", json={"title": "稽古", "start_at": start.isoformat()})
    event_id = ev.json()["id"]
    await client.post(f"{_url(prod)}/{event_id}/attendees", json={"user_ids": [str(other_user.id)]})

    resp = await client.delete(f"{_url(prod)}/{event_id}/attendees/{other_user.id}")
    assert resp.status_code == 204


async def test_non_member_cannot_access(client_as_other: AsyncClient, production):
    """団体メンバーでないユーザーは一覧取得で 403。"""
    prod, _ = production
    resp = await client_as_other.get(f"{_url(prod)}/")
    assert resp.status_code == 403


async def test_production_member_not_manager_cannot_write_events(
    client_as_other: AsyncClient,
    production,
    other_user,
    other_production_member,
    seeded_event_with_other_attendee,
):
    """公演メンバーだが manager でないユーザーは create/update/delete/add_attendee が 403（回帰）。"""
    prod, _ = production
    event = seeded_event_with_other_attendee
    start = _now()

    # CREATE — member は 403
    resp = await client_as_other.post(f"{_url(prod)}/", json={"title": "x", "start_at": start.isoformat()})
    assert resp.status_code == 403, f"member CREATE は 403 期待: {resp.text}"

    # DELETE event — member は 403
    resp = await client_as_other.delete(f"{_url(prod)}/{event.id}")
    assert resp.status_code == 403, f"member DELETE event は 403 期待: {resp.text}"

    # UPDATE event — member は 403
    resp = await client_as_other.patch(f"{_url(prod)}/{event.id}", json={"title": "hacked"})
    assert resp.status_code == 403, f"member PATCH event は 403 期待: {resp.text}"

    # ADD attendee — member は 403
    resp = await client_as_other.post(
        f"{_url(prod)}/{event.id}/attendees",
        json={"user_ids": [str(other_user.id)]},
    )
    assert resp.status_code == 403, f"member ADD attendee は 403 期待: {resp.text}"


async def test_org_member_not_production_member_cannot_list_events(
    client_as_other: AsyncClient,
    production,
    org_with_member,
):
    """団体メンバーだが公演メンバーでないユーザーは list で 403（回帰）。"""
    prod, _ = production
    resp = await client_as_other.get(f"{_url(prod)}/")
    assert resp.status_code == 403


async def test_org_admin_not_production_member_cannot_write_events(
    client_as_other: AsyncClient,
    db_session: AsyncSession,
    production,
    org_with_member,
    other_user,
):
    """org admin でも production 非在籍なら create が 403（回帰）。"""
    from sqlalchemy import update as sa_update

    from src.db.models import OrganizationMembership as OM

    prod, _ = production
    # other_user を org admin に昇格（production 非在籍のまま）
    result = await db_session.execute(
        sa_update(OM)
        .where(OM.organization_id == prod.organization_id, OM.user_id == other_user.id)
        .values(org_role="admin")
        .returning(OM.org_role)
    )
    updated_rows = result.fetchall()
    assert len(updated_rows) == 1 and updated_rows[0][0] == "admin", (
        "前提: other_user が org admin に昇格されていること"
    )

    start = _now()
    # CREATE — production 非在籍の org admin は 403 になるべき（production_membership 不足）
    resp = await client_as_other.post(f"{_url(prod)}/", json={"title": "x", "start_at": start.isoformat()})
    assert resp.status_code == 403, f"org admin 非在籍の CREATE は 403 期待: {resp.text}"
    assert "公演メンバーではありません" in resp.json().get("detail", "")


async def test_update_attendee_rejects_null_for_notnull_fields(
    client: AsyncClient, production, other_user, other_production_member
):
    """attendance_type / rsvp_status への明示的 null PATCH は 422（回帰）。"""
    prod, _ = production
    start = _now()
    ev = await client.post(f"{_url(prod)}/", json={"title": "x", "start_at": start.isoformat()})
    event_id = ev.json()["id"]
    await client.post(f"{_url(prod)}/{event_id}/attendees", json={"user_ids": [str(other_user.id)]})
    for payload in ({"attendance_type": None}, {"rsvp_status": None}):
        resp = await client.patch(f"{_url(prod)}/{event_id}/attendees/{other_user.id}", json=payload)
        assert resp.status_code == 422, (payload, resp.text)


async def test_ex_production_member_cannot_rsvp(
    client_as_other: AsyncClient,
    db_session: AsyncSession,
    production,
    other_user,
    seeded_event_with_other_attendee,
):
    """公演メンバーから外れた後は既存の attendee 行があっても RSVP 更新が 403（回帰）。"""
    from sqlalchemy import delete as sa_delete

    from src.db.models import ProductionMembership as PM

    prod, _ = production
    event = seeded_event_with_other_attendee
    # other_production_member fixture 経由で登録済みの ProductionMembership を削除
    await db_session.execute(sa_delete(PM).where(PM.production_id == prod.id, PM.user_id == other_user.id))
    await db_session.flush()
    resp = await client_as_other.patch(
        f"{_url(prod)}/{event.id}/attendees/{other_user.id}",
        json={"rsvp_status": "accepted"},
    )
    assert resp.status_code == 403

"""UserAvailability エンドポイントのテスト。"""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ProductionMembership, UserAvailability


def _url(prod):
    return f"/api/organizations/{prod.organization_id}/productions/{prod.id}/availabilities"


@pytest.fixture
async def other_production_member(
    db_session: AsyncSession,
    org_with_member,
    production,
    other_user,
) -> ProductionMembership:
    prod, _ = production
    pm = ProductionMembership(
        user_id=other_user.id,
        production_id=prod.id,
        production_role="member",
    )
    db_session.add(pm)
    await db_session.flush()
    return pm


async def test_create_availability(client: AsyncClient, production):
    prod, _ = production
    target = date.today() + timedelta(days=3)
    resp = await client.post(
        f"{_url(prod)}/",
        json={
            "date": target.isoformat(),
            "availability": "available",
            "start_time": "10:00:00",
            "end_time": "18:00:00",
            "note": "午前OK",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["date"] == target.isoformat()
    assert data["availability"] == "available"
    assert data["note"] == "午前OK"


async def test_create_availability_invalid_time_order(client: AsyncClient, production):
    prod, _ = production
    target = date.today()
    resp = await client.post(
        f"{_url(prod)}/",
        json={
            "date": target.isoformat(),
            "start_time": "18:00:00",
            "end_time": "10:00:00",
        },
    )
    assert resp.status_code == 422


async def test_create_availability_invalid_value(client: AsyncClient, production):
    prod, _ = production
    resp = await client.post(
        f"{_url(prod)}/",
        json={"date": date.today().isoformat(), "availability": "maybe"},
    )
    assert resp.status_code == 422


async def test_bulk_upsert_availability(client: AsyncClient, production):
    prod, _ = production
    base = date.today()
    resp = await client.post(
        f"{_url(prod)}/bulk",
        json={
            "items": [{"date": (base + timedelta(days=i)).isoformat(), "availability": "available"} for i in range(3)]
        },
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_create_availability_is_idempotent(client: AsyncClient, production):
    """同一 (user, production, date) への再POSTで重複作成されず、最新値で上書きされる（回帰）。"""
    prod, _ = production
    target = date.today() + timedelta(days=5)
    first = await client.post(
        f"{_url(prod)}/",
        json={"date": target.isoformat(), "availability": "available", "note": "first"},
    )
    assert first.status_code == 201, first.text
    first_id = first.json()["id"]

    second = await client.post(
        f"{_url(prod)}/",
        json={"date": target.isoformat(), "availability": "unavailable", "note": "second"},
    )
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first_id
    assert second.json()["availability"] == "unavailable"
    assert second.json()["note"] == "second"

    # 一覧でも重複レコードが存在しないことを確認
    listed = await client.get(f"{_url(prod)}/")
    assert listed.status_code == 200
    on_date = [r for r in listed.json() if r["date"] == target.isoformat()]
    assert len(on_date) == 1


async def test_update_rejects_null_availability(client: AsyncClient, production):
    """availability は NOT NULL なので明示的 null PATCH は 422（回帰）。"""
    prod, _ = production
    target = date.today() + timedelta(days=15)
    create = await client.post(
        f"{_url(prod)}/",
        json={"date": target.isoformat(), "availability": "available"},
    )
    assert create.status_code == 201
    row_id = create.json()["id"]
    resp = await client.patch(f"{_url(prod)}/{row_id}", json={"availability": None})
    assert resp.status_code == 422


async def test_bulk_upsert_is_idempotent(client: AsyncClient, production):
    """bulk も同一日付で既存行を上書きする（回帰）。"""
    prod, _ = production
    target = date.today() + timedelta(days=10)
    first = await client.post(
        f"{_url(prod)}/bulk",
        json={"items": [{"date": target.isoformat(), "availability": "available"}]},
    )
    assert first.status_code == 200
    first_id = first.json()[0]["id"]

    second = await client.post(
        f"{_url(prod)}/bulk",
        json={"items": [{"date": target.isoformat(), "availability": "tentative"}]},
    )
    assert second.status_code == 200
    assert second.json()[0]["id"] == first_id
    assert second.json()[0]["availability"] == "tentative"

    listed = await client.get(f"{_url(prod)}/")
    on_date = [r for r in listed.json() if r["date"] == target.isoformat()]
    assert len(on_date) == 1


async def test_list_own_availabilities(client: AsyncClient, production):
    prod, _ = production
    base = date.today()
    await client.post(
        f"{_url(prod)}/bulk",
        json={
            "items": [{"date": (base + timedelta(days=i)).isoformat(), "availability": "unavailable"} for i in range(2)]
        },
    )
    resp = await client.get(f"{_url(prod)}/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(row["availability"] == "unavailable" for row in data)


async def test_list_with_date_filter(client: AsyncClient, production):
    prod, _ = production
    base = date.today()
    await client.post(
        f"{_url(prod)}/bulk",
        json={
            "items": [{"date": (base + timedelta(days=i)).isoformat(), "availability": "available"} for i in range(5)]
        },
    )
    resp = await client.get(
        f"{_url(prod)}/",
        params={
            "date_from": (base + timedelta(days=1)).isoformat(),
            "date_to": (base + timedelta(days=2)).isoformat(),
        },
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_member_cannot_list_others(
    client_as_other: AsyncClient,
    db_session: AsyncSession,
    production,
    other_production_member,
    test_user,
):
    """メンバー権限ユーザーは他メンバーの空きを閲覧できない。"""
    prod, _ = production
    db_session.add(
        UserAvailability(user_id=test_user.id, production_id=prod.id, date=date.today(), availability="available")
    )
    await db_session.flush()
    resp = await client_as_other.get(f"{_url(prod)}/", params={"user_id": str(test_user.id)})
    assert resp.status_code == 403


async def test_manager_can_list_others(
    client: AsyncClient,
    db_session: AsyncSession,
    production,
    other_user,
    other_production_member,
    test_user,
):
    """マネージャー(test_user)は他メンバーの空きを閲覧でき、自分のデータと混ざらない（回帰）。"""
    prod, _ = production
    today = date.today()
    # other_user の availability を直接 DB に登録
    db_session.add(
        UserAvailability(
            user_id=other_user.id,
            production_id=prod.id,
            date=today,
            availability="available",
        )
    )
    # test_user の availability も登録（結果に混ざらないこと確認用）
    db_session.add(
        UserAvailability(
            user_id=test_user.id,
            production_id=prod.id,
            date=today + timedelta(days=1),
            availability="unavailable",
        )
    )
    await db_session.flush()

    resp = await client.get(f"{_url(prod)}/", params={"user_id": str(other_user.id)})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1, "other_user の行が返るべき"
    assert all(row["user_id"] == str(other_user.id) for row in data), "自分の行が混ざってはいけない"
    assert any(row["availability"] == "available" for row in data)


async def test_update_own_availability(client: AsyncClient, production):
    prod, _ = production
    create = await client.post(
        f"{_url(prod)}/",
        json={"date": date.today().isoformat(), "availability": "tentative"},
    )
    aid = create.json()["id"]
    resp = await client.patch(f"{_url(prod)}/{aid}", json={"availability": "available", "note": "確定"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["availability"] == "available"
    assert data["note"] == "確定"


async def test_cannot_update_others_availability(
    client_as_other: AsyncClient,
    db_session: AsyncSession,
    production,
    other_production_member,
    test_user,
):
    prod, _ = production
    row = UserAvailability(user_id=test_user.id, production_id=prod.id, date=date.today(), availability="available")
    db_session.add(row)
    await db_session.flush()
    resp = await client_as_other.patch(f"{_url(prod)}/{row.id}", json={"availability": "unavailable"})
    assert resp.status_code == 403


async def test_manager_cannot_update_others_availability(
    client: AsyncClient,
    db_session: AsyncSession,
    production,
    other_user,
    other_production_member,
):
    """manager（test_user）でも他ユーザーの availability は PATCH/DELETE できない（回帰）。"""
    prod, _ = production
    row = UserAvailability(
        user_id=other_user.id,
        production_id=prod.id,
        date=date.today() + timedelta(days=20),
        availability="available",
    )
    db_session.add(row)
    await db_session.flush()

    resp = await client.patch(f"{_url(prod)}/{row.id}", json={"availability": "unavailable"})
    assert resp.status_code == 403, f"manager の他人 PATCH は 403 期待: {resp.text}"

    resp = await client.delete(f"{_url(prod)}/{row.id}")
    assert resp.status_code == 403, f"manager の他人 DELETE は 403 期待: {resp.text}"


async def test_delete_own_availability(client: AsyncClient, production):
    prod, _ = production
    create = await client.post(
        f"{_url(prod)}/",
        json={"date": date.today().isoformat(), "availability": "available"},
    )
    aid = create.json()["id"]
    resp = await client.delete(f"{_url(prod)}/{aid}")
    assert resp.status_code == 204


async def test_non_production_member_cannot_create(client_as_other: AsyncClient, production, org_with_member):
    """団体メンバーだが公演メンバーでない → 403"""
    prod, _ = production
    resp = await client_as_other.post(
        f"{_url(prod)}/",
        json={"date": date.today().isoformat(), "availability": "available"},
    )
    assert resp.status_code == 403


async def test_org_admin_not_production_member_cannot_list(
    client_as_other: AsyncClient,
    db_session: AsyncSession,
    production,
    org_with_member,
    other_user,
):
    """org admin でも production 非所属なら list が 403（回帰）。"""
    from sqlalchemy import update as sa_update

    from src.db.models import OrganizationMembership as OM

    prod, _ = production
    # other_user を org admin に昇格（production 非所属のまま）
    result = await db_session.execute(
        sa_update(OM)
        .where(OM.organization_id == prod.organization_id, OM.user_id == other_user.id)
        .values(org_role="admin")
        .returning(OM.org_role)
    )
    updated_rows = result.fetchall()
    assert len(updated_rows) == 1 and updated_rows[0][0] == "admin", "前提: other_user が org admin に昇格されていること"

    resp = await client_as_other.get(f"{_url(prod)}/")
    assert resp.status_code == 403, f"org admin 非所属の list は 403 期待: {resp.text}"
    assert "公演メンバーではありません" in resp.json().get("detail", "")


async def test_non_production_member_cannot_list_self(
    client_as_other: AsyncClient,
    db_session: AsyncSession,
    production,
    org_with_member,
    other_user,
):
    """団体メンバーだが公演メンバーでなくなった後は list(self) でも 403（回帰）。"""
    prod, _ = production
    # other_user に過去の行があっても、公演メンバーでなければ 403 になるべき
    db_session.add(
        UserAvailability(user_id=other_user.id, production_id=prod.id, date=date.today(), availability="available")
    )
    await db_session.flush()
    resp = await client_as_other.get(f"{_url(prod)}/")
    assert resp.status_code == 403


async def test_non_production_member_cannot_update_own(
    client_as_other: AsyncClient,
    db_session: AsyncSession,
    production,
    org_with_member,
    other_user,
):
    """団体メンバーだが公演メンバーでない場合、自分の既存行でも更新できない（回帰）。"""
    prod, _ = production
    row = UserAvailability(user_id=other_user.id, production_id=prod.id, date=date.today(), availability="available")
    db_session.add(row)
    await db_session.flush()
    resp = await client_as_other.patch(f"{_url(prod)}/{row.id}", json={"availability": "unavailable"})
    assert resp.status_code == 403


async def test_non_production_member_cannot_delete_own(
    client_as_other: AsyncClient,
    db_session: AsyncSession,
    production,
    org_with_member,
    other_user,
):
    """団体メンバーだが公演メンバーでない場合、自分の既存行でも削除できない（回帰）。"""
    prod, _ = production
    row = UserAvailability(user_id=other_user.id, production_id=prod.id, date=date.today(), availability="available")
    db_session.add(row)
    await db_session.flush()
    resp = await client_as_other.delete(f"{_url(prod)}/{row.id}")
    assert resp.status_code == 403

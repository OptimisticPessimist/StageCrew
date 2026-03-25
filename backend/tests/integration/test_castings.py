"""キャスティング CRUD エンドポイントのテスト。"""

import uuid

from httpx import AsyncClient


def _base_url(prod):
    return f"/api/organizations/{prod.organization_id}/productions/{prod.id}"


# ============================================================
# 一覧
# ============================================================


async def test_list_castings_empty(client: AsyncClient, production, script):
    prod, _ = production
    resp = await client.get(f"{_base_url(prod)}/scripts/{script.id}/castings/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_castings(client: AsyncClient, production, script, casting):
    prod, _ = production
    resp = await client.get(f"{_base_url(prod)}/scripts/{script.id}/castings/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["display_name"] == "テスト芸名"
    assert "character" in data[0]
    assert "production_membership" in data[0]


# ============================================================
# 作成
# ============================================================


async def test_create_casting(client: AsyncClient, production, script, character):
    prod, pm = production
    resp = await client.post(
        f"{_base_url(prod)}/scripts/{script.id}/castings/",
        json={
            "character_id": str(character.id),
            "production_membership_id": str(pm.id),
            "display_name": "芸名A",
            "memo": "メモA",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["display_name"] == "芸名A"
    assert data["memo"] == "メモA"
    assert data["character"]["name"] == "太郎"


async def test_create_casting_minimal(client: AsyncClient, production, script, character):
    prod, pm = production
    resp = await client.post(
        f"{_base_url(prod)}/scripts/{script.id}/castings/",
        json={
            "character_id": str(character.id),
            "production_membership_id": str(pm.id),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["display_name"] is None
    assert data["memo"] is None
    assert data["sort_order"] == 0


async def test_create_casting_duplicate(client: AsyncClient, production, script, character, casting):
    """同じ character + membership の重複は 409。"""
    prod, pm = production
    resp = await client.post(
        f"{_base_url(prod)}/scripts/{script.id}/castings/",
        json={
            "character_id": str(character.id),
            "production_membership_id": str(pm.id),
        },
    )
    assert resp.status_code == 409


async def test_create_casting_invalid_character(client: AsyncClient, production, script):
    """存在しない character_id は 422。"""
    prod, pm = production
    resp = await client.post(
        f"{_base_url(prod)}/scripts/{script.id}/castings/",
        json={
            "character_id": str(uuid.uuid4()),
            "production_membership_id": str(pm.id),
        },
    )
    assert resp.status_code == 422


async def test_create_casting_invalid_membership(client: AsyncClient, production, script, character):
    """存在しない production_membership_id は 422。"""
    prod, _ = production
    resp = await client.post(
        f"{_base_url(prod)}/scripts/{script.id}/castings/",
        json={
            "character_id": str(character.id),
            "production_membership_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 422


# ============================================================
# ダブルキャスト
# ============================================================


async def test_double_casting(client: AsyncClient, production, script, character, db_session):
    """1つの役に複数メンバーを割り当て可能。"""
    from src.db.models import OrganizationMembership, ProductionMembership, User
    from tests.conftest import OTHER_USER_ID

    prod, pm = production

    # 2人目のユーザーを作成
    user2 = User(id=OTHER_USER_ID, display_name="他のユーザー", discord_id="test_discord_double")
    db_session.add(user2)
    await db_session.flush()

    org_mem2 = OrganizationMembership(user_id=user2.id, organization_id=prod.organization_id, org_role="member")
    db_session.add(org_mem2)
    await db_session.flush()

    pm2 = ProductionMembership(user_id=user2.id, production_id=prod.id, production_role="member")
    db_session.add(pm2)
    await db_session.flush()

    # 1人目を割当
    resp1 = await client.post(
        f"{_base_url(prod)}/scripts/{script.id}/castings/",
        json={
            "character_id": str(character.id),
            "production_membership_id": str(pm.id),
            "display_name": "Aキャスト",
        },
    )
    assert resp1.status_code == 201

    # 2人目を割当（ダブルキャスト）
    resp2 = await client.post(
        f"{_base_url(prod)}/scripts/{script.id}/castings/",
        json={
            "character_id": str(character.id),
            "production_membership_id": str(pm2.id),
            "display_name": "Bキャスト",
        },
    )
    assert resp2.status_code == 201

    # 一覧で2件取得
    resp_list = await client.get(f"{_base_url(prod)}/scripts/{script.id}/castings/")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 2


# ============================================================
# 更新
# ============================================================


async def test_update_casting(client: AsyncClient, production, script, casting):
    prod, _ = production
    resp = await client.patch(
        f"{_base_url(prod)}/scripts/{script.id}/castings/{casting.id}",
        json={"display_name": "更新芸名", "memo": "更新メモ"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "更新芸名"
    assert data["memo"] == "更新メモ"


async def test_update_casting_not_found(client: AsyncClient, production, script):
    prod, _ = production
    resp = await client.patch(
        f"{_base_url(prod)}/scripts/{script.id}/castings/{uuid.uuid4()}",
        json={"display_name": "存在しない"},
    )
    assert resp.status_code == 404


# ============================================================
# 削除
# ============================================================


async def test_delete_casting(client: AsyncClient, production, script, casting):
    prod, _ = production
    resp = await client.delete(f"{_base_url(prod)}/scripts/{script.id}/castings/{casting.id}")
    assert resp.status_code == 204

    # 一覧で0件
    resp_list = await client.get(f"{_base_url(prod)}/scripts/{script.id}/castings/")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 0


async def test_delete_casting_not_found(client: AsyncClient, production, script):
    prod, _ = production
    resp = await client.delete(f"{_base_url(prod)}/scripts/{script.id}/castings/{uuid.uuid4()}")
    assert resp.status_code == 404


# ============================================================
# 脚本詳細に castings が含まれる
# ============================================================


async def test_script_detail_includes_castings(client: AsyncClient, production, script, casting):
    prod, _ = production
    resp = await client.get(f"{_base_url(prod)}/scripts/{script.id}")
    assert resp.status_code == 200
    data = resp.json()
    characters = data["characters"]
    assert len(characters) >= 1
    char_with_casting = next(c for c in characters if c["name"] == "太郎")
    assert len(char_with_casting["castings"]) >= 1
    assert char_with_casting["castings"][0]["display_name"] == "テスト芸名"

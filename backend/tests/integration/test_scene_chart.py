"""香盤表（Scene Chart）エンドポイントのテスト。"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Character, SceneCharacterMapping


def _base_url(prod):
    return f"/api/organizations/{prod.organization_id}/productions/{prod.id}"


def _chart_url(prod, script):
    return f"{_base_url(prod)}/scripts/{script.id}/scene-chart"


# ============================================================
# 香盤表取得
# ============================================================


async def test_get_scene_chart_empty(client: AsyncClient, production, script):
    """マッピングがない場合は空のマトリクスを返す。"""
    prod, _ = production
    resp = await client.get(f"{_chart_url(prod, script)}/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["characters"] == []
    assert data["scenes"] == []
    assert data["matrix"] == {}


async def test_get_scene_chart_with_data(
    client: AsyncClient, production, script, scene, character, db_session: AsyncSession
):
    """マッピングがある場合はマトリクスに含まれる。"""
    prod, _ = production
    mapping = SceneCharacterMapping(
        scene_id=scene.id,
        character_id=character.id,
        appearance_type="dialogue",
        is_auto_generated=True,
    )
    db_session.add(mapping)
    await db_session.flush()

    resp = await client.get(f"{_chart_url(prod, script)}/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["scenes"]) == 1
    assert len(data["characters"]) == 1
    cell = data["matrix"][str(scene.id)][str(character.id)]
    assert cell is not None
    assert cell["appearance_type"] == "dialogue"
    assert cell["is_auto_generated"] is True


# ============================================================
# 自動生成
# ============================================================


async def test_generate_from_lines(
    client: AsyncClient, production, script, scene, character, line, db_session: AsyncSession
):
    """Line データから香盤表を自動生成する。"""
    prod, _ = production
    resp = await client.post(f"{_chart_url(prod, script)}/generate")
    assert resp.status_code == 200
    data = resp.json()
    cell = data["matrix"][str(scene.id)][str(character.id)]
    assert cell is not None
    assert cell["appearance_type"] == "dialogue"
    assert cell["is_auto_generated"] is True


async def test_generate_preserve_manual(
    client: AsyncClient, production, script, scene, character, line, db_session: AsyncSession
):
    """preserve_manual=True で手動マッピングが保持される。"""
    prod, _ = production

    # 手動マッピングを先に作成（別のキャラクター）
    char2 = Character(script_id=script.id, name="花子", sort_order=1)
    db_session.add(char2)
    await db_session.flush()

    manual = SceneCharacterMapping(
        scene_id=scene.id,
        character_id=char2.id,
        appearance_type="silent",
        is_auto_generated=False,
        note="背景にいるだけ",
    )
    db_session.add(manual)
    await db_session.flush()

    # 自動生成（preserve_manual=True がデフォルト）
    resp = await client.post(f"{_chart_url(prod, script)}/generate")
    assert resp.status_code == 200
    data = resp.json()

    # 手動マッピングが残っている
    cell_manual = data["matrix"][str(scene.id)][str(char2.id)]
    assert cell_manual is not None
    assert cell_manual["appearance_type"] == "silent"
    assert cell_manual["is_auto_generated"] is False

    # 自動生成マッピングも存在
    cell_auto = data["matrix"][str(scene.id)][str(character.id)]
    assert cell_auto is not None
    assert cell_auto["is_auto_generated"] is True


async def test_generate_no_preserve(
    client: AsyncClient, production, script, scene, character, line, db_session: AsyncSession
):
    """preserve_manual=False で全マッピングが再生成される。"""
    prod, _ = production

    # 手動マッピングを作成
    char2 = Character(script_id=script.id, name="花子", sort_order=1)
    db_session.add(char2)
    await db_session.flush()

    manual = SceneCharacterMapping(
        scene_id=scene.id,
        character_id=char2.id,
        appearance_type="silent",
        is_auto_generated=False,
    )
    db_session.add(manual)
    await db_session.flush()

    resp = await client.post(
        f"{_chart_url(prod, script)}/generate",
        json={"preserve_manual": False},
    )
    assert resp.status_code == 200
    data = resp.json()

    # 手動マッピングは削除されている（Line がないため再生成されない）
    cell_manual = data["matrix"][str(scene.id)][str(char2.id)]
    assert cell_manual is None


async def test_generate_idempotent(
    client: AsyncClient, production, script, scene, character, line, db_session: AsyncSession
):
    """自動生成を2回実行しても構造が同じ（mapping_id は再生成で変わる）。"""
    prod, _ = production
    resp1 = await client.post(f"{_chart_url(prod, script)}/generate")
    resp2 = await client.post(f"{_chart_url(prod, script)}/generate")
    assert resp1.status_code == 200
    assert resp2.status_code == 200

    def _strip_ids(matrix):
        """mapping_id を除外して比較用に変換。"""
        return {
            sk: {ck: {k: v for k, v in cell.items() if k != "mapping_id"} if cell else None for ck, cell in row.items()}
            for sk, row in matrix.items()
        }

    assert _strip_ids(resp1.json()["matrix"]) == _strip_ids(resp2.json()["matrix"])


# ============================================================
# 手動マッピング追加
# ============================================================


async def test_create_mapping(client: AsyncClient, production, script, scene, character):
    """手動でマッピングを追加できる。"""
    prod, _ = production
    resp = await client.post(
        f"{_chart_url(prod, script)}/mappings",
        json={
            "scene_id": str(scene.id),
            "character_id": str(character.id),
            "appearance_type": "silent",
            "note": "背景にいるだけ",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["appearance_type"] == "silent"
    assert data["is_auto_generated"] is False
    assert data["note"] == "背景にいるだけ"


async def test_create_mapping_duplicate(
    client: AsyncClient, production, script, scene, character, db_session: AsyncSession
):
    """同じ scene+character の重複は 409。"""
    prod, _ = production
    existing = SceneCharacterMapping(
        scene_id=scene.id,
        character_id=character.id,
        appearance_type="dialogue",
        is_auto_generated=True,
    )
    db_session.add(existing)
    await db_session.flush()

    resp = await client.post(
        f"{_chart_url(prod, script)}/mappings",
        json={
            "scene_id": str(scene.id),
            "character_id": str(character.id),
        },
    )
    assert resp.status_code == 409


async def test_create_mapping_scene_not_in_script(client: AsyncClient, production, script, character):
    """脚本に属さないシーンは 422。"""
    prod, _ = production
    resp = await client.post(
        f"{_chart_url(prod, script)}/mappings",
        json={
            "scene_id": str(uuid.uuid4()),
            "character_id": str(character.id),
        },
    )
    assert resp.status_code == 422


async def test_create_mapping_character_not_in_script(client: AsyncClient, production, script, scene):
    """脚本に属さないキャラクターは 422。"""
    prod, _ = production
    resp = await client.post(
        f"{_chart_url(prod, script)}/mappings",
        json={
            "scene_id": str(scene.id),
            "character_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 422


# ============================================================
# マッピング更新
# ============================================================


async def test_update_mapping(client: AsyncClient, production, script, scene, character, db_session: AsyncSession):
    """マッピングの note と appearance_type を更新できる。"""
    prod, _ = production
    mapping = SceneCharacterMapping(
        scene_id=scene.id,
        character_id=character.id,
        appearance_type="dialogue",
        is_auto_generated=True,
    )
    db_session.add(mapping)
    await db_session.flush()

    resp = await client.patch(
        f"{_chart_url(prod, script)}/mappings/{mapping.id}",
        json={"note": "更新メモ", "appearance_type": "silent"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["note"] == "更新メモ"
    assert data["appearance_type"] == "silent"


async def test_update_mapping_not_found(client: AsyncClient, production, script):
    prod, _ = production
    resp = await client.patch(
        f"{_chart_url(prod, script)}/mappings/{uuid.uuid4()}",
        json={"note": "存在しない"},
    )
    assert resp.status_code == 404


# ============================================================
# マッピング削除
# ============================================================


async def test_delete_mapping(client: AsyncClient, production, script, scene, character, db_session: AsyncSession):
    prod, _ = production
    mapping = SceneCharacterMapping(
        scene_id=scene.id,
        character_id=character.id,
        appearance_type="dialogue",
        is_auto_generated=True,
    )
    db_session.add(mapping)
    await db_session.flush()

    resp = await client.delete(f"{_chart_url(prod, script)}/mappings/{mapping.id}")
    assert resp.status_code == 204


async def test_delete_mapping_not_found(client: AsyncClient, production, script):
    prod, _ = production
    resp = await client.delete(f"{_chart_url(prod, script)}/mappings/{uuid.uuid4()}")
    assert resp.status_code == 404

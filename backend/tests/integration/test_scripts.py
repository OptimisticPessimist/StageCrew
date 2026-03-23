"""脚本管理 CRUD エンドポイントのテスト。"""

import uuid

from httpx import AsyncClient

# ============================================================
# Script CRUD
# ============================================================


async def test_list_scripts_empty(client: AsyncClient, production):
    prod, _ = production
    resp = await client.get(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/"
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_script(client: AsyncClient, production):
    prod, _ = production
    resp = await client.post(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/",
        json={"title": "新しい脚本", "author": "作家A", "synopsis": "あらすじテスト"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "新しい脚本"
    assert data["author"] == "作家A"
    assert data["synopsis"] == "あらすじテスト"
    assert data["revision"] == 1


async def test_create_script_minimal(client: AsyncClient, production):
    prod, _ = production
    resp = await client.post(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/",
        json={"title": "最小脚本"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "最小脚本"
    assert data["synopsis"] is None


async def test_list_scripts(client: AsyncClient, production, script):
    prod, _ = production
    resp = await client.get(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(s["title"] == "テスト脚本" for s in data)
    assert any(s["synopsis"] == "あらすじテスト" for s in data)


async def test_get_script(client: AsyncClient, production, script):
    prod, _ = production
    resp = await client.get(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "テスト脚本"
    assert data["synopsis"] == "あらすじテスト"
    assert "scenes" in data
    assert "characters" in data


async def test_get_script_not_found(client: AsyncClient, production):
    prod, _ = production
    resp = await client.get(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{uuid.uuid4()}"
    )
    assert resp.status_code == 404


async def test_update_script(client: AsyncClient, production, script):
    prod, _ = production
    resp = await client.patch(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}",
        json={"title": "更新脚本", "synopsis": "更新あらすじ"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "更新脚本"
    assert data["synopsis"] == "更新あらすじ"


async def test_delete_script(client: AsyncClient, production, script):
    prod, _ = production
    resp = await client.delete(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}"
    )
    assert resp.status_code == 204

    resp = await client.get(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}"
    )
    assert resp.status_code == 404


async def test_script_non_member_forbidden(client_as_other: AsyncClient, production, script):
    prod, _ = production
    resp = await client_as_other.get(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/"
    )
    assert resp.status_code == 403


# ============================================================
# Scene CRUD
# ============================================================


async def test_create_scene(client: AsyncClient, production, script):
    prod, _ = production
    resp = await client.post(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}/scenes",
        json={"heading": "第1幕 第1場", "act_number": 1, "scene_number": 1},
    )
    assert resp.status_code == 201
    assert resp.json()["heading"] == "第1幕 第1場"


async def test_list_scenes(client: AsyncClient, production, script, scene):
    prod, _ = production
    resp = await client.get(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}/scenes"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


async def test_update_scene(client: AsyncClient, production, script, scene):
    prod, _ = production
    resp = await client.patch(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}/scenes/{scene.id}",
        json={"heading": "更新シーン"},
    )
    assert resp.status_code == 200
    assert resp.json()["heading"] == "更新シーン"


async def test_delete_scene(client: AsyncClient, production, script, scene):
    prod, _ = production
    resp = await client.delete(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}/scenes/{scene.id}"
    )
    assert resp.status_code == 204


# ============================================================
# Character CRUD
# ============================================================


async def test_create_character(client: AsyncClient, production, script):
    prod, _ = production
    resp = await client.post(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}/characters",
        json={"name": "花子", "description": "ヒロイン"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "花子"
    assert data["description"] == "ヒロイン"


async def test_list_characters(client: AsyncClient, production, script, character):
    prod, _ = production
    resp = await client.get(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}/characters"
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_update_character(client: AsyncClient, production, script, character):
    prod, _ = production
    resp = await client.patch(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}/characters/{character.id}",
        json={"name": "次郎"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "次郎"


async def test_delete_character(client: AsyncClient, production, script, character):
    prod, _ = production
    resp = await client.delete(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}/characters/{character.id}"
    )
    assert resp.status_code == 204


# ============================================================
# Line CRUD
# ============================================================


async def test_create_line(client: AsyncClient, production, script, scene, character):
    prod, _ = production
    resp = await client.post(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}/scenes/{scene.id}/lines",
        json={"content": "おはようございます", "character_id": str(character.id)},
    )
    assert resp.status_code == 201
    assert resp.json()["content"] == "おはようございます"


async def test_list_lines(client: AsyncClient, production, script, scene, line):
    prod, _ = production
    resp = await client.get(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}/scenes/{scene.id}/lines"
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_update_line(client: AsyncClient, production, script, scene, line):
    prod, _ = production
    resp = await client.patch(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}/scenes/{scene.id}/lines/{line.id}",
        json={"content": "さようなら"},
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "さようなら"


async def test_delete_line(client: AsyncClient, production, script, scene, line):
    prod, _ = production
    resp = await client.delete(
        f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script.id}/scenes/{scene.id}/lines/{line.id}"
    )
    assert resp.status_code == 204

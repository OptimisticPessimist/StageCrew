"""脚本再アップロード（バージョン更新）エンドポイントのテスト。"""

import io
import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Casting, Scene, SceneCharacterMapping


def _fountain_v1() -> bytes:
    """初版 Fountain テキスト。"""
    return """\
Title: テスト脚本
Author: テスト作家
Draft date: 2026-03-20

# 登場人物
太郎　主人公
花子　ヒロイン

INT. 部屋 - 朝

太郎：
おはよう。

花子：
おはようございます。

EXT. 公園 - 昼

太郎：
いい天気だね。
""".encode()


def _fountain_v2() -> bytes:
    """改訂版: 花子を削除し、次郎を追加、シーン構成を変更。"""
    return """\
Title: テスト脚本 改訂版
Author: テスト作家
Draft date: 2026-03-25

# 登場人物
太郎　主人公
次郎　新キャラ

INT. リビング - 朝

太郎：
おはよう、次郎。

次郎：
おはようございます。

EXT. 公園 - 昼

太郎：
散歩しよう。

INT. カフェ - 夕方

次郎：
コーヒーをください。
""".encode()


def _fountain_v2_same_chars() -> bytes:
    """改訂版: キャラクターは同じ、シーンだけ変更。"""
    return """\
Title: テスト脚本 第2稿
Author: テスト作家

# 登場人物
太郎　主人公
花子　ヒロイン

INT. オフィス - 朝

太郎：
おはよう、花子。

花子：
おはようございます、太郎さん。
""".encode()


def _plain_text_v1() -> bytes:
    return "これは初版のテキストです。\n".encode()


def _plain_text_v2() -> bytes:
    return "これは改訂版のテキストです。\n".encode()


def _upload_url(prod) -> str:
    return f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/upload"


def _reupload_url(prod, script_id) -> str:
    return f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/{script_id}/upload"


# ============================================================
# 基本的な再アップロード
# ============================================================


async def test_reupload_increments_revision(client: AsyncClient, production):
    """再アップロードで revision が 1 → 2 に増える。"""
    prod, _ = production

    # 初回アップロード
    resp = await client.post(
        _upload_url(prod),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v1()), "text/plain")},
    )
    assert resp.status_code == 201
    data = resp.json()
    script_id = data["id"]
    assert data["revision"] == 1

    # 再アップロード
    resp = await client.put(
        _reupload_url(prod, script_id),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v2()), "text/plain")},
        data={"revision_text": "花子を削除し次郎を追加"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["revision"] == 2
    assert data["revision_text"] == "花子を削除し次郎を追加"


async def test_reupload_multiple_times(client: AsyncClient, production):
    """複数回の再アップロードで revision が正しくインクリメントされる。"""
    prod, _ = production

    resp = await client.post(
        _upload_url(prod),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v1()), "text/plain")},
    )
    script_id = resp.json()["id"]

    # 2回再アップロード
    for expected_rev in (2, 3):
        resp = await client.put(
            _reupload_url(prod, script_id),
            files={"file": ("test.fountain", io.BytesIO(_fountain_v2_same_chars()), "text/plain")},
        )
        assert resp.status_code == 200
        assert resp.json()["revision"] == expected_rev


# ============================================================
# キャラクター・キャスティング保持
# ============================================================


async def test_reupload_preserves_casting_for_matching_characters(
    client: AsyncClient, production, db_session: AsyncSession
):
    """名前が一致するキャラクターのキャスティングが保持される。"""
    prod, pm = production

    # 初回アップロード
    resp = await client.post(
        _upload_url(prod),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v1()), "text/plain")},
    )
    data = resp.json()
    script_id = data["id"]

    # 太郎のキャラクターIDを取得してキャスティングを作成
    taro = next(c for c in data["characters"] if c["name"] == "太郎")
    taro_id = taro["id"]

    casting = Casting(
        character_id=uuid.UUID(taro_id),
        production_membership_id=pm.id,
        display_name="太郎役",
        memo="主役",
        sort_order=0,
    )
    db_session.add(casting)
    await db_session.flush()
    casting_id = casting.id

    # 同じキャラクター名を含む Fountain で再アップロード
    resp = await client.put(
        _reupload_url(prod, script_id),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v2_same_chars()), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()

    # 太郎のキャラクターIDが保持されている
    taro_after = next(c for c in data["characters"] if c["name"] == "太郎")
    assert taro_after["id"] == taro_id

    # キャスティングが保持されている
    result = await db_session.execute(select(Casting).where(Casting.id == casting_id))
    preserved_casting = result.scalar_one_or_none()
    assert preserved_casting is not None
    assert preserved_casting.display_name == "太郎役"


async def test_reupload_removes_casting_for_removed_characters(
    client: AsyncClient, production, db_session: AsyncSession
):
    """削除されたキャラクターのキャスティングもカスケード削除される。"""
    prod, pm = production

    # 初回アップロード
    resp = await client.post(
        _upload_url(prod),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v1()), "text/plain")},
    )
    data = resp.json()
    script_id = data["id"]

    # 花子のキャスティングを作成
    hanako = next(c for c in data["characters"] if c["name"] == "花子")
    hanako_id = uuid.UUID(hanako["id"])

    casting = Casting(
        character_id=hanako_id,
        production_membership_id=pm.id,
        display_name="花子役",
        sort_order=0,
    )
    db_session.add(casting)
    await db_session.flush()
    casting_id = casting.id

    # 花子がいない Fountain で再アップロード
    resp = await client.put(
        _reupload_url(prod, script_id),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v2()), "text/plain")},
    )
    assert resp.status_code == 200

    # 花子のキャラクターが存在しない
    data = resp.json()
    char_names = {c["name"] for c in data["characters"]}
    assert "花子" not in char_names
    assert "次郎" in char_names

    # キャスティングも削除されている
    result = await db_session.execute(select(Casting).where(Casting.id == casting_id))
    assert result.scalar_one_or_none() is None


async def test_reupload_adds_new_characters(client: AsyncClient, production):
    """再アップロードで新しいキャラクターが追加される。"""
    prod, _ = production

    resp = await client.post(
        _upload_url(prod),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v1()), "text/plain")},
    )
    script_id = resp.json()["id"]

    resp = await client.put(
        _reupload_url(prod, script_id),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v2()), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()

    char_names = {c["name"] for c in data["characters"]}
    assert "太郎" in char_names  # 保持
    assert "次郎" in char_names  # 新規
    assert "花子" not in char_names  # 削除


# ============================================================
# シーン再構築
# ============================================================


async def test_reupload_rebuilds_scenes(client: AsyncClient, production):
    """再アップロードでシーンが再構築される。"""
    prod, _ = production

    resp = await client.post(
        _upload_url(prod),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v1()), "text/plain")},
    )
    data = resp.json()
    script_id = data["id"]
    assert len(data["scenes"]) == 2

    # v2 は 3 シーン
    resp = await client.put(
        _reupload_url(prod, script_id),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v2()), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["scenes"]) == 3
    headings = [s["heading"] for s in data["scenes"]]
    assert any("リビング" in h for h in headings)
    assert any("カフェ" in h for h in headings)


async def test_reupload_regenerates_scene_chart(
    client: AsyncClient, production, db_session: AsyncSession
):
    """再アップロードで香盤表マッピングが再生成される。"""
    prod, _ = production

    resp = await client.post(
        _upload_url(prod),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v1()), "text/plain")},
    )
    script_id = resp.json()["id"]

    # 再アップロード
    resp = await client.put(
        _reupload_url(prod, script_id),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v2()), "text/plain")},
    )
    assert resp.status_code == 200

    # 新しいシーンに対応するマッピングが存在する
    result = await db_session.execute(
        select(SceneCharacterMapping)
        .join(Scene, SceneCharacterMapping.scene_id == Scene.id)
        .where(Scene.script_id == uuid.UUID(script_id))
    )
    mappings = list(result.scalars().all())
    assert len(mappings) > 0
    assert all(m.is_auto_generated for m in mappings)


# ============================================================
# 非 Fountain 再アップロード
# ============================================================


async def test_reupload_plain_text(client: AsyncClient, production):
    """非 Fountain の再アップロードはコンテンツのみ更新される。"""
    prod, _ = production

    resp = await client.post(
        _upload_url(prod),
        files={"file": ("memo.txt", io.BytesIO(_plain_text_v1()), "text/plain")},
    )
    data = resp.json()
    script_id = data["id"]
    assert data["revision"] == 1
    assert "初版" in data["content"]

    resp = await client.put(
        _reupload_url(prod, script_id),
        files={"file": ("memo.txt", io.BytesIO(_plain_text_v2()), "text/plain")},
        data={"revision_text": "テキスト修正"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["revision"] == 2
    assert "改訂版" in data["content"]
    assert data["revision_text"] == "テキスト修正"


# ============================================================
# メタデータ更新
# ============================================================


async def test_reupload_updates_metadata(client: AsyncClient, production):
    """Fountain 再アップロードでメタデータが更新される。"""
    prod, _ = production

    resp = await client.post(
        _upload_url(prod),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v1()), "text/plain")},
    )
    data = resp.json()
    script_id = data["id"]
    assert data["title"] == "テスト脚本"

    resp = await client.put(
        _reupload_url(prod, script_id),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v2()), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "テスト脚本 改訂版"
    assert "2026-03-25" in data["draft_date"]


# ============================================================
# エラーケース
# ============================================================


async def test_reupload_nonexistent_script_404(client: AsyncClient, production):
    """存在しない script_id への再アップロードは 404。"""
    prod, _ = production
    fake_id = uuid.uuid4()

    resp = await client.put(
        _reupload_url(prod, fake_id),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v1()), "text/plain")},
    )
    assert resp.status_code == 404


async def test_reupload_requires_org_membership(client_as_other: AsyncClient, production):
    """非メンバーによる再アップロードは 403。"""
    prod, _ = production
    fake_id = uuid.uuid4()

    resp = await client_as_other.put(
        _reupload_url(prod, fake_id),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v1()), "text/plain")},
    )
    assert resp.status_code == 403


async def test_reupload_unsupported_extension(client: AsyncClient, production):
    """非対応拡張子は 400。"""
    prod, _ = production

    resp = await client.post(
        _upload_url(prod),
        files={"file": ("test.fountain", io.BytesIO(_fountain_v1()), "text/plain")},
    )
    script_id = resp.json()["id"]

    resp = await client.put(
        _reupload_url(prod, script_id),
        files={"file": ("test.pdf", io.BytesIO(b"dummy"), "application/pdf")},
    )
    assert resp.status_code == 400

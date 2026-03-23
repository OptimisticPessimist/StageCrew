"""脚本アップロードエンドポイントのテスト。"""

import io

from httpx import AsyncClient


def _make_fountain_content() -> bytes:
    """テスト用の Fountain テキストを生成する。"""
    return """\
Title: テスト脚本
Author: テスト作家
Draft date: 2026-03-20
Synopsis: テストあらすじ

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


def _make_plain_text() -> bytes:
    return "これはプレーンテキストです。\n特にフォーマットはありません。\n".encode()


def _url(prod) -> str:
    return f"/api/organizations/{prod.organization_id}/productions/{prod.id}/scripts/upload"


# ============================================================
# Fountain アップロード
# ============================================================


async def test_upload_fountain_file(client: AsyncClient, production):
    prod, _ = production
    content = _make_fountain_content()

    resp = await client.post(
        _url(prod),
        files={"file": ("test.fountain", io.BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 201
    data = resp.json()

    # メタデータ
    assert data["title"] == "テスト脚本"
    assert data["author"] == "テスト作家"
    assert "テストあらすじ" in data["synopsis"]
    assert data["draft_date"] is not None
    assert "2026-03-20" in data["draft_date"]

    # 登場人物
    chars = data["characters"]
    char_names = {c["name"] for c in chars}
    assert "太郎" in char_names
    assert "花子" in char_names

    # シーン
    scenes = data["scenes"]
    assert len(scenes) == 2
    assert "部屋" in scenes[0]["heading"]
    assert "公園" in scenes[1]["heading"]

    # セリフ
    scene1_lines = scenes[0]["lines"]
    assert len(scene1_lines) == 2
    assert "おはよう" in scene1_lines[0]["content"]


async def test_upload_fountain_txt_extension(client: AsyncClient, production):
    """拡張子が .txt でも Fountain として自動検出される。"""
    prod, _ = production
    content = _make_fountain_content()

    resp = await client.post(
        _url(prod),
        files={"file": ("script.txt", io.BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "テスト脚本"
    assert len(data["scenes"]) == 2


# ============================================================
# プレーンテキストアップロード
# ============================================================


async def test_upload_plain_text(client: AsyncClient, production):
    prod, _ = production
    content = _make_plain_text()

    resp = await client.post(
        _url(prod),
        files={"file": ("memo.txt", io.BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "memo"
    assert "プレーンテキスト" in data["content"]
    assert data["scenes"] == []
    assert data["characters"] == []


# ============================================================
# バリデーション
# ============================================================


async def test_upload_unsupported_extension(client: AsyncClient, production):
    prod, _ = production
    resp = await client.post(
        _url(prod),
        files={"file": ("script.pdf", io.BytesIO(b"dummy"), "application/pdf")},
    )
    assert resp.status_code == 400
    assert "対応していない" in resp.json()["detail"]


async def test_upload_file_too_large(client: AsyncClient, production):
    prod, _ = production
    # 10MB + 1 byte
    large_content = b"x" * (10 * 1024 * 1024 + 1)
    resp = await client.post(
        _url(prod),
        files={"file": ("large.txt", io.BytesIO(large_content), "text/plain")},
    )
    assert resp.status_code == 400
    assert "上限" in resp.json()["detail"]


# ============================================================
# Shift_JIS エンコーディング
# ============================================================


async def test_upload_shift_jis(client: AsyncClient, production):
    prod, _ = production
    text = """\
Title: シフトJISテスト
Author: テスト

# 登場人物
太郎

INT. 部屋 - 朝

太郎：
こんにちは。
"""
    content = text.encode("shift_jis")

    resp = await client.post(
        _url(prod),
        files={"file": ("sjis.fountain", io.BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "シフトJISテスト"


# ============================================================
# 権限チェック
# ============================================================


async def test_upload_requires_org_membership(client_as_other: AsyncClient, production):
    prod, _ = production
    content = _make_plain_text()

    resp = await client_as_other.post(
        _url(prod),
        files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
    )
    assert resp.status_code == 403

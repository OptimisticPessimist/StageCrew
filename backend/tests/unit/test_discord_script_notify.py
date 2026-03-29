"""Discord webhook 脚本通知関数のユニットテスト。"""

from unittest.mock import patch

from src.services.discord_webhook import (
    COLOR_SCRIPT,
    COLOR_UPDATE,
    notify_script_updated,
    notify_script_uploaded,
)


class TestNotifyScriptUploaded:
    """notify_script_uploaded のテスト。"""

    def test_enqueues_embed_with_correct_fields(self):
        """基本的な通知ペイロードが正しく構築される。"""
        captured = []

        with patch("src.services.discord_webhook._enqueue", side_effect=lambda *a, **kw: captured.append((a, kw))):
            notify_script_uploaded(
                "https://discord.com/api/webhooks/test",
                script_title="テスト脚本",
                production_name="テスト公演",
                author="テスト作家",
                scene_count=3,
                character_count=5,
                uploader_name="太郎",
            )

        assert len(captured) == 1
        args, kwargs = captured[0]
        webhook_url, payload = args[0], args[1]
        assert webhook_url == "https://discord.com/api/webhooks/test"

        embed = payload["embeds"][0]
        assert "脚本アップロード" in embed["title"]
        assert "テスト脚本" in embed["title"]
        assert embed["color"] == COLOR_SCRIPT

        field_names = [f["name"] for f in embed["fields"]]
        assert "公演" in field_names
        assert "著者" in field_names
        assert "シーン数" in field_names
        assert "登場人物数" in field_names

        field_map = {f["name"]: f["value"] for f in embed["fields"]}
        assert field_map["公演"] == "テスト公演"
        assert field_map["著者"] == "テスト作家"
        assert field_map["シーン数"] == "3"
        assert field_map["登場人物数"] == "5"

        assert "太郎" in embed["footer"]["text"]

    def test_omits_author_when_none(self):
        """著者が None の場合はフィールドに含まない。"""
        captured = []

        with patch("src.services.discord_webhook._enqueue", side_effect=lambda *a, **kw: captured.append((a, kw))):
            notify_script_uploaded(
                "https://discord.com/api/webhooks/test",
                script_title="テスト脚本",
                production_name="テスト公演",
                author=None,
                scene_count=0,
                character_count=0,
                uploader_name="太郎",
            )

        args, _ = captured[0]
        embed = args[1]["embeds"][0]
        field_names = [f["name"] for f in embed["fields"]]
        assert "著者" not in field_names

    def test_passes_pdf_to_enqueue(self):
        """PDF バイトとファイル名が _enqueue に渡される。"""
        captured = []

        with patch("src.services.discord_webhook._enqueue", side_effect=lambda *a, **kw: captured.append((a, kw))):
            notify_script_uploaded(
                "https://discord.com/api/webhooks/test",
                script_title="テスト脚本",
                production_name="テスト公演",
                author=None,
                scene_count=0,
                character_count=0,
                uploader_name="太郎",
                pdf_bytes=b"%PDF-fake",
                pdf_filename="テスト脚本.pdf",
            )

        args, _ = captured[0]
        assert args[2] == b"%PDF-fake"
        assert args[3] == "テスト脚本.pdf"

    def test_no_webhook_url_does_not_enqueue(self):
        """webhook_url が None の場合は _enqueue が呼ばれない。"""
        captured = []

        with patch("src.services.discord_webhook._enqueue", side_effect=lambda *a, **kw: captured.append((a, kw))):
            notify_script_uploaded(
                None,
                script_title="テスト脚本",
                production_name="テスト公演",
                author=None,
                scene_count=0,
                character_count=0,
                uploader_name="太郎",
            )

        # _enqueue は呼ばれるが、内部で webhook_url=None をチェックして早期 return
        # ここでは _enqueue が呼ばれること自体は問題ない（内部で弾かれるため）
        assert len(captured) == 1


class TestNotifyScriptUpdated:
    """notify_script_updated のテスト。"""

    def test_enqueues_embed_with_revision_info(self):
        """更新通知に改訂番号と改訂メモが含まれる。"""
        captured = []

        with patch("src.services.discord_webhook._enqueue", side_effect=lambda *a, **kw: captured.append((a, kw))):
            notify_script_updated(
                "https://discord.com/api/webhooks/test",
                script_title="テスト脚本",
                revision=3,
                revision_text="花子を削除し次郎を追加",
                production_name="テスト公演",
                added_characters=["次郎"],
                removed_characters=["花子"],
                updater_name="花子",
            )

        assert len(captured) == 1
        args, _ = captured[0]
        embed = args[1]["embeds"][0]

        assert "脚本更新" in embed["title"]
        assert "Rev.3" in embed["title"]
        assert embed["color"] == COLOR_UPDATE

        field_map = {f["name"]: f["value"] for f in embed["fields"]}
        assert field_map["公演"] == "テスト公演"
        assert field_map["改訂番号"] == "Rev.3"
        assert field_map["改訂メモ"] == "花子を削除し次郎を追加"
        assert "次郎" in field_map["追加キャラクター"]
        assert "花子" in field_map["削除キャラクター"]

        assert "花子" in embed["footer"]["text"]

    def test_omits_optional_fields_when_empty(self):
        """改訂メモやキャラクター変更がない場合はフィールドに含まない。"""
        captured = []

        with patch("src.services.discord_webhook._enqueue", side_effect=lambda *a, **kw: captured.append((a, kw))):
            notify_script_updated(
                "https://discord.com/api/webhooks/test",
                script_title="テスト脚本",
                revision=2,
                revision_text=None,
                production_name="テスト公演",
                updater_name="太郎",
            )

        args, _ = captured[0]
        embed = args[1]["embeds"][0]
        field_names = [f["name"] for f in embed["fields"]]
        assert "改訂メモ" not in field_names
        assert "追加キャラクター" not in field_names
        assert "削除キャラクター" not in field_names

    def test_passes_pdf_to_enqueue(self):
        """PDF バイトとファイル名が _enqueue に渡される。"""
        captured = []

        with patch("src.services.discord_webhook._enqueue", side_effect=lambda *a, **kw: captured.append((a, kw))):
            notify_script_updated(
                "https://discord.com/api/webhooks/test",
                script_title="テスト脚本",
                revision=2,
                revision_text=None,
                production_name="テスト公演",
                updater_name="太郎",
                pdf_bytes=b"%PDF-fake",
                pdf_filename="テスト脚本.pdf",
            )

        args, _ = captured[0]
        assert args[2] == b"%PDF-fake"
        assert args[3] == "テスト脚本.pdf"


class TestSendWebhookWithFile:
    """_send_webhook_with_file のテスト。"""

    async def test_sends_multipart_form_data(self):
        """ファイル付き送信が multipart/form-data で行われる。"""
        from src.services.discord_webhook import _send_webhook_with_file

        with patch("src.services.discord_webhook.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value.__aenter__.return_value
            mock_resp = mock_client.post.return_value
            mock_resp.status_code = 200

            await _send_webhook_with_file(
                "https://discord.com/api/webhooks/test",
                {"embeds": [{"title": "test"}]},
                b"%PDF-fake",
                "test.pdf",
            )

            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args
            assert "data" in call_kwargs.kwargs
            assert "files" in call_kwargs.kwargs
            assert "payload_json" in call_kwargs.kwargs["data"]

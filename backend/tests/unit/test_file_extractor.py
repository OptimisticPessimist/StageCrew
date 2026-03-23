"""ファイルエクストラクターのユニットテスト。"""

from src.services.file_extractor import decode_text, detect_fountain


# ============================================================
# エンコーディング検出・デコード
# ============================================================
class TestDecodeText:
    def test_utf8(self):
        text = "こんにちは世界"
        raw = text.encode("utf-8")
        assert decode_text(raw) == text

    def test_utf8_bom(self):
        text = "BOM付きテキスト"
        raw = b"\xef\xbb\xbf" + text.encode("utf-8")
        assert decode_text(raw) == text

    def test_shift_jis(self):
        text = "こんにちは世界"
        raw = text.encode("shift_jis")
        result = decode_text(raw)
        assert "こんにちは" in result

    def test_empty(self):
        assert decode_text(b"") == ""

    def test_ascii(self):
        assert decode_text(b"hello world") == "hello world"


# ============================================================
# Fountain 判定
# ============================================================
class TestDetectFountain:
    def test_positive_title_and_scene(self):
        text = """\
Title: テスト脚本
Author: テスト

INT. 部屋 - 朝
"""
        assert detect_fountain(text) is True

    def test_positive_title_and_characters(self):
        text = """\
Title: テスト脚本

# 登場人物
太郎
"""
        assert detect_fountain(text) is True

    def test_positive_all_indicators(self):
        text = """\
Title: テスト脚本

# 登場人物
太郎

INT. 部屋
"""
        assert detect_fountain(text) is True

    def test_positive_title_not_on_first_line(self):
        """先頭行が空行やコメントでも Title: を検出する。"""
        text = """\

Title: テスト脚本
Author: テスト

INT. 部屋 - 朝
"""
        assert detect_fountain(text) is True

    def test_negative_plain_text(self):
        text = "これはただのメモです。\n特に構造はありません。\n"
        assert detect_fountain(text) is False

    def test_negative_single_indicator(self):
        text = "Title: something\n\nJust plain text after that.\n"
        assert detect_fountain(text) is False

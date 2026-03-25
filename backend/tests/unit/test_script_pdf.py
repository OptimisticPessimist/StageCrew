"""脚本PDF生成サービスのユニットテスト。"""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from src.services.script_pdf import generate_script_pdf

_SENTINEL = object()


def _make_script(
    *,
    title="テスト脚本",
    author="山田太郎",
    revision=1,
    revision_text=None,
    draft_date=_SENTINEL,
    copyright=None,
    contact=None,
    synopsis=None,
    pdf_orientation="landscape",
    pdf_writing_direction="horizontal",
):
    return SimpleNamespace(
        id=uuid.uuid4(),
        title=title,
        author=author,
        revision=revision,
        revision_text=revision_text,
        draft_date=datetime(2026, 1, 15, tzinfo=UTC) if draft_date is _SENTINEL else draft_date,
        copyright=copyright,
        contact=contact,
        synopsis=synopsis,
        pdf_orientation=pdf_orientation,
        pdf_writing_direction=pdf_writing_direction,
    )


def _make_character(name, *, char_id=None):
    return SimpleNamespace(
        id=char_id or uuid.uuid4(),
        name=name,
        sort_order=0,
    )


def _make_line(character_id, content, *, sort_order=0):
    return SimpleNamespace(
        id=uuid.uuid4(),
        character_id=character_id,
        content=content,
        sort_order=sort_order,
    )


def _make_scene(heading, lines=None, *, act_number=1, scene_number=1, sort_order=0, description=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        act_number=act_number,
        scene_number=scene_number,
        heading=heading,
        description=description,
        sort_order=sort_order,
        lines=lines or [],
    )


# ============================================================
# 横書きテスト
# ============================================================
class TestHorizontalPDF:
    def test_basic_generation(self):
        """横書きPDFが正常に生成される"""
        char = _make_character("太郎")
        script = _make_script()
        scene = _make_scene(
            "森の中",
            lines=[
                _make_line(char.id, "こんにちは、花子さん。", sort_order=0),
                _make_line(None, "太郎が手を振る。", sort_order=1),
            ],
        )

        result = generate_script_pdf(script, [scene], [char])

        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"
        assert len(result) > 100

    def test_empty_script(self):
        """シーン・セリフなしでもエラーにならない"""
        script = _make_script()
        result = generate_script_pdf(script, [], [])
        assert result[:5] == b"%PDF-"

    def test_multiple_scenes(self):
        """複数シーンが正常に処理される"""
        char = _make_character("花子")
        script = _make_script()
        scenes = [
            _make_scene("森の中", [_make_line(char.id, "セリフ1")], scene_number=1),
            _make_scene("城の前", [_make_line(char.id, "セリフ2")], scene_number=2),
        ]

        result = generate_script_pdf(script, scenes, [char])
        assert result[:5] == b"%PDF-"

    def test_portrait_orientation(self):
        """portrait 指定で生成される"""
        script = _make_script(pdf_orientation="portrait")
        result = generate_script_pdf(script, [], [])
        assert result[:5] == b"%PDF-"


# ============================================================
# 縦書きテスト
# ============================================================
class TestVerticalPDF:
    def test_basic_generation(self):
        """縦書きPDFが正常に生成される"""
        char = _make_character("太郎")
        script = _make_script(pdf_writing_direction="vertical")
        scene = _make_scene(
            "森の中",
            lines=[
                _make_line(char.id, "こんにちは。", sort_order=0),
                _make_line(None, "太郎が歩く。", sort_order=1),
            ],
        )

        result = generate_script_pdf(script, [scene], [char])

        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_empty_script(self):
        """縦書き・シーンなしでもエラーにならない"""
        script = _make_script(pdf_writing_direction="vertical")
        result = generate_script_pdf(script, [], [])
        assert result[:5] == b"%PDF-"

    def test_long_text_wraps_columns(self):
        """長いセリフが複数列にまたがっても正常に処理される"""
        char = _make_character("太郎")
        script = _make_script(pdf_writing_direction="vertical")
        long_text = "あ" * 500
        scene = _make_scene("森の中", [_make_line(char.id, long_text)])

        result = generate_script_pdf(script, [scene], [char])
        assert result[:5] == b"%PDF-"


# ============================================================
# タイトルページテスト
# ============================================================
class TestTitlePage:
    def test_full_metadata(self):
        """全メタデータが含まれるPDFが生成される"""
        script = _make_script(
            title="夏の夜の夢",
            author="シェイクスピア",
            revision=3,
            revision_text="最終稿",
            draft_date=datetime(2026, 3, 1, tzinfo=UTC),
            copyright="(c) 2026 Example",
            contact="info@example.com",
            synopsis="妖精の森で繰り広げられる恋愛喜劇",
        )

        result = generate_script_pdf(script, [], [])
        assert result[:5] == b"%PDF-"
        assert len(result) > 100

    def test_minimal_metadata(self):
        """最小限のメタデータでも生成される"""
        script = _make_script(
            author=None,
            revision_text=None,
            draft_date=None,
            copyright=None,
            contact=None,
            synopsis=None,
        )

        result = generate_script_pdf(script, [], [])
        assert result[:5] == b"%PDF-"


# ============================================================
# ト書き（stage direction）テスト
# ============================================================
class TestStageDirection:
    def test_stage_direction_horizontal(self):
        """横書きでト書き（character_id=None）が処理される"""
        script = _make_script()
        scene = _make_scene(
            "部屋",
            lines=[_make_line(None, "幕が上がる。")],
            description="薄暗い部屋の中。",
        )

        result = generate_script_pdf(script, [scene], [])
        assert result[:5] == b"%PDF-"

    def test_stage_direction_vertical(self):
        """縦書きでト書きが処理される"""
        script = _make_script(pdf_writing_direction="vertical")
        scene = _make_scene(
            "部屋",
            lines=[_make_line(None, "幕が上がる。")],
            description="薄暗い部屋の中。",
        )

        result = generate_script_pdf(script, [scene], [])
        assert result[:5] == b"%PDF-"

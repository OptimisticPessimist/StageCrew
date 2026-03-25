"""脚本PDF生成サービス。

縦書き・横書き両対応の脚本PDFを生成する。
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fpdf import FPDF

if TYPE_CHECKING:
    from datetime import datetime

# フォントファイルのディレクトリ
_FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"
_FONT_FILE = _FONTS_DIR / "NotoSansJP-Regular.ttf"

# レイアウト定数
_TITLE_FONT_SIZE = 24
_HEADING_FONT_SIZE = 14
_BODY_FONT_SIZE = 11
_META_FONT_SIZE = 10
_STAGE_DIRECTION_FONT_SIZE = 10

# 横書きレイアウト
_H_MARGIN_LEFT = 20
_H_MARGIN_RIGHT = 20
_H_MARGIN_TOP = 20
_H_MARGIN_BOTTOM = 20
_H_CHARACTER_INDENT = 25
_H_LINE_INDENT = 35

# 縦書きレイアウト
_V_MARGIN_TOP = 15
_V_MARGIN_BOTTOM = 15
_V_MARGIN_RIGHT = 15
_V_MARGIN_LEFT = 15
_V_COL_SPACING = 4
_V_CHAR_SPACING = 2

# 縦書き用の句読点・括弧変換マップ
_VERTICAL_PUNCTUATION: dict[str, str] = {
    "\u3001": "\uFE11",  # 、→ ︑
    "\u3002": "\uFE12",  # 。→ ︒
    "\uFF0C": "\uFE10",  # ，→ ︐
    "\u300C": "\uFE41",  # 「→ ﹁
    "\u300D": "\uFE42",  # 」→ ﹂
    "\u300E": "\uFE43",  # 『→ ﹃
    "\u300F": "\uFE44",  # 』→ ﹄
    "\uFF08": "\uFE35",  # （→ ︵
    "\uFF09": "\uFE36",  # ）→ ︶
    "\u2014": "\uFE31",  # —→ ︱
    "\u2026": "\uFE19",  # …→ ︙
}

# 縦書き時に回転が必要な文字（半角英数等）
_ROTATE_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")


def _format_date(dt: datetime | None) -> str:
    """日付をフォーマットする。"""
    if dt is None:
        return ""
    return dt.strftime("%Y年%m月%d日")


class _ScriptPDF(FPDF):
    """脚本PDF用のFPDFサブクラス。"""

    def __init__(self, orientation: str, title: str) -> None:
        super().__init__(orientation=orientation, unit="mm", format="A4")
        self._script_title = title
        self._register_fonts()

    def _register_fonts(self) -> None:
        if not _FONT_FILE.exists():
            msg = f"フォントファイルが見つかりません: {_FONT_FILE}"
            raise FileNotFoundError(msg)
        self.add_font("NotoSansJP", style="", fname=str(_FONT_FILE))

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("NotoSansJP", size=8)
        self.cell(0, 10, f"- {self.page_no()} -", align="C")


def generate_script_pdf(
    script: Any,
    scenes: list[Any],
    characters: list[Any],
) -> bytes:
    """脚本のPDFバイト列を生成する。

    Args:
        script: Script ORMオブジェクト（またはダックタイプ互換オブジェクト）
        scenes: Scene のリスト（各 scene.lines がロード済み）
        characters: Character のリスト

    Returns:
        PDF のバイト列
    """
    orientation = "L" if script.pdf_orientation == "landscape" else "P"
    writing_direction = script.pdf_writing_direction  # "vertical" | "horizontal"

    pdf = _ScriptPDF(orientation=orientation, title=script.title)
    pdf.set_auto_page_break(auto=False)

    # キャラクター名マップ
    char_map: dict[uuid.UUID, str] = {}
    for ch in characters:
        char_map[ch.id] = ch.name

    # タイトルページ
    _render_title_page(pdf, script)

    # 本文
    if writing_direction == "vertical":
        _render_body_vertical(pdf, scenes, char_map)
    else:
        _render_body_horizontal(pdf, scenes, char_map)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# ============================================================
# タイトルページ
# ============================================================
def _render_title_page(pdf: _ScriptPDF, script: Any) -> None:
    """タイトルページを描画する。"""
    pdf.add_page()
    page_w = pdf.w
    page_h = pdf.h

    # タイトル
    pdf.set_font("NotoSansJP", size=_TITLE_FONT_SIZE)
    pdf.set_y(page_h * 0.3)
    pdf.cell(0, 12, script.title, align="C", new_x="LMARGIN", new_y="NEXT")

    # 著者
    if script.author:
        pdf.ln(8)
        pdf.set_font("NotoSansJP", size=_HEADING_FONT_SIZE)
        pdf.cell(0, 8, f"作：{script.author}", align="C", new_x="LMARGIN", new_y="NEXT")

    # 改訂情報
    revision_info = f"第{script.revision}稿"
    if script.revision_text:
        revision_info += f"  {script.revision_text}"
    pdf.ln(6)
    pdf.set_font("NotoSansJP", size=_META_FONT_SIZE)
    pdf.cell(0, 6, revision_info, align="C", new_x="LMARGIN", new_y="NEXT")

    # 日付
    date_str = _format_date(getattr(script, "draft_date", None))
    if date_str:
        pdf.ln(4)
        pdf.cell(0, 6, date_str, align="C", new_x="LMARGIN", new_y="NEXT")

    # 著作権・連絡先（ページ下部）
    bottom_y = page_h - 40
    if script.copyright:
        pdf.set_y(bottom_y)
        pdf.set_font("NotoSansJP", size=_META_FONT_SIZE)
        pdf.cell(0, 6, script.copyright, align="C", new_x="LMARGIN", new_y="NEXT")
        bottom_y += 8

    if script.contact:
        pdf.set_y(bottom_y)
        pdf.set_font("NotoSansJP", size=_META_FONT_SIZE)
        pdf.cell(0, 6, script.contact, align="C", new_x="LMARGIN", new_y="NEXT")

    # あらすじ
    if script.synopsis:
        pdf.set_y(page_h * 0.55)
        pdf.set_font("NotoSansJP", size=_META_FONT_SIZE)
        pdf.set_x(_H_MARGIN_LEFT + 20)
        pdf.multi_cell(page_w - _H_MARGIN_LEFT * 2 - 40, 6, script.synopsis, align="C")


# ============================================================
# 横書き本文
# ============================================================
def _render_body_horizontal(
    pdf: _ScriptPDF, scenes: list[Any], char_map: dict[uuid.UUID, str]
) -> None:
    """横書きレイアウトで本文を描画する。"""
    pdf.set_margins(_H_MARGIN_LEFT, _H_MARGIN_TOP, _H_MARGIN_RIGHT)
    usable_w = pdf.w - _H_MARGIN_LEFT - _H_MARGIN_RIGHT
    bottom_limit = pdf.h - _H_MARGIN_BOTTOM

    for scene in scenes:
        pdf.add_page()
        y = _H_MARGIN_TOP

        # シーン見出し
        pdf.set_font("NotoSansJP", size=_HEADING_FONT_SIZE)
        heading = _build_scene_heading(scene)
        pdf.set_xy(_H_MARGIN_LEFT, y)
        pdf.cell(usable_w, 8, heading, new_x="LMARGIN", new_y="NEXT")
        y = pdf.get_y() + 4

        # ト書き（シーン説明）
        if scene.description:
            pdf.set_font("NotoSansJP", size=_STAGE_DIRECTION_FONT_SIZE)
            pdf.set_xy(_H_MARGIN_LEFT, y)
            pdf.multi_cell(usable_w, 5, f"（{scene.description}）")
            y = pdf.get_y() + 4

        # セリフ
        for line in scene.lines:
            if y > bottom_limit - 20:
                pdf.add_page()
                y = _H_MARGIN_TOP

            if line.character_id is None:
                # ト書き
                pdf.set_font("NotoSansJP", size=_STAGE_DIRECTION_FONT_SIZE)
                pdf.set_xy(_H_MARGIN_LEFT + 5, y)
                pdf.multi_cell(usable_w - 10, 5, f"（{line.content}）")
                y = pdf.get_y() + 3
            else:
                # キャラクター名
                char_name = char_map.get(line.character_id, "???")
                pdf.set_font("NotoSansJP", size=_BODY_FONT_SIZE)
                pdf.set_xy(_H_MARGIN_LEFT + _H_CHARACTER_INDENT, y)
                pdf.cell(0, 6, char_name, new_x="LMARGIN", new_y="NEXT")
                y = pdf.get_y()

                # セリフ内容
                pdf.set_font("NotoSansJP", size=_BODY_FONT_SIZE)
                pdf.set_xy(_H_MARGIN_LEFT + _H_LINE_INDENT, y)
                pdf.multi_cell(usable_w - _H_LINE_INDENT - 5, 6, line.content)
                y = pdf.get_y() + 3


# ============================================================
# 縦書き本文
# ============================================================
def _render_body_vertical(
    pdf: _ScriptPDF, scenes: list[Any], char_map: dict[uuid.UUID, str]
) -> None:
    """縦書きレイアウトで本文を描画する。"""
    page_w = pdf.w
    page_h = pdf.h
    col_top = _V_MARGIN_TOP
    col_bottom = page_h - _V_MARGIN_BOTTOM
    font_size = _BODY_FONT_SIZE
    col_w = font_size * 0.6 + _V_COL_SPACING  # 1列の幅

    # 右端から開始
    pdf.add_page()
    col_x = page_w - _V_MARGIN_RIGHT - col_w
    col_y = col_top

    def _new_col() -> tuple[float, float]:
        """次の列に移動。ページ左端を超えたら改ページ。"""
        nonlocal col_x, col_y
        col_x -= col_w
        col_y = col_top
        if col_x < _V_MARGIN_LEFT:
            pdf.add_page()
            col_x = page_w - _V_MARGIN_RIGHT - col_w
        return col_x, col_y

    def _draw_text_vertical(text: str, size: float, *, is_heading: bool = False) -> None:
        """テキストを縦書きで描画する。"""
        nonlocal col_x, col_y

        step_h = size * 0.6 + _V_CHAR_SPACING
        pdf.set_font("NotoSansJP", size=size)

        for char in text:
            if col_y + step_h > col_bottom:
                col_x, col_y = _new_col()
                pdf.set_font("NotoSansJP", size=size)

            display_char = _VERTICAL_PUNCTUATION.get(char, char)
            pdf.text(col_x, col_y + step_h * 0.8, display_char)
            col_y += step_h

    for scene in scenes:
        # シーン見出しの前に少し空列を入れる
        if col_y > col_top + 5:
            col_x, col_y = _new_col()

        heading = _build_scene_heading(scene)
        _draw_text_vertical(heading, _HEADING_FONT_SIZE, is_heading=True)

        # シーン説明（ト書き）
        if scene.description:
            col_x, col_y = _new_col()
            _draw_text_vertical(f"（{scene.description}）", _STAGE_DIRECTION_FONT_SIZE)

        # セリフ
        for line in scene.lines:
            col_x, col_y = _new_col()

            if line.character_id is None:
                # ト書き
                _draw_text_vertical(f"（{line.content}）", _STAGE_DIRECTION_FONT_SIZE)
            else:
                # キャラクター名を列上部に
                char_name = char_map.get(line.character_id, "???")
                _draw_text_vertical(char_name, _BODY_FONT_SIZE)
                col_y += _V_CHAR_SPACING * 2  # 名前とセリフの間に少しスペース
                # セリフ内容
                _draw_text_vertical(line.content, _BODY_FONT_SIZE)


# ============================================================
# ユーティリティ
# ============================================================
def _build_scene_heading(scene: Any) -> str:
    """シーン見出しテキストを構築する。"""
    parts: list[str] = []
    if scene.act_number:
        parts.append(f"第{scene.act_number}幕")
    if scene.scene_number:
        parts.append(f"第{scene.scene_number}場")
    if scene.heading:
        parts.append(scene.heading)
    return "　".join(parts) if parts else "---"

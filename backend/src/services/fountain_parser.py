"""Fountain 形式の脚本テキストをパースするモジュール。

Fountain 形式のテキストからメタデータ、登場人物、シーン、セリフを抽出する。
DB やフレームワークに依存しない純粋関数で構成。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ============================================================
# データ構造
# ============================================================
@dataclass
class FountainMetadata:
    title: str | None = None
    author: str | None = None
    draft_date: str | None = None
    copyright: str | None = None
    contact: str | None = None
    notes: str | None = None
    synopsis: str | None = None


@dataclass
class FountainCharacter:
    name: str
    description: str | None = None
    sort_order: int = 0


@dataclass
class FountainLine:
    character_name: str | None
    content: str
    sort_order: int = 0


@dataclass
class FountainScene:
    heading: str
    act_number: int = 1
    scene_number: int = 1
    sort_order: int = 0
    description: str | None = None
    lines: list[FountainLine] = field(default_factory=list)


@dataclass
class FountainParseResult:
    metadata: FountainMetadata
    characters: list[FountainCharacter]
    scenes: list[FountainScene]


# ============================================================
# 正規表現
# ============================================================
_SCENE_HEADING_RE = re.compile(
    r"^(?:"
    r"(?:INT\.|EXT\.|INT\./EXT\.|I/E)\s+"  # 標準 Fountain
    r"|\.(?=[A-Z\u3000-\u9FFF])"  # 強制見出し（ピリオドプレフィックス）
    r")",
    re.IGNORECASE,
)

_TITLE_PAGE_KEYS: dict[str, str] = {
    "title": "title",
    "author": "author",
    "draft date": "draft_date",
    "copyright": "copyright",
    "contact": "contact",
    "notes": "notes",
    "synopsis": "synopsis",
}

_CHARACTERS_HEADING_RE = re.compile(r"^#\s*登場人物\s*$")

# キャラクター名のパターン: 全角文字 or 大文字英字で始まる名前
_CHARACTER_CUE_RE = re.compile(
    r"^([A-Z\u3000-\u9FFF\uFF00-\uFFEF][^\n]*?)[:：]?\s*$"
)


# ============================================================
# メイン関数
# ============================================================
def parse_fountain(text: str) -> FountainParseResult:
    """Fountain 形式のテキストをパースする。"""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    metadata, body_start = _parse_title_page(lines)
    characters = _parse_characters_section(lines[body_start:])
    known_names = {c.name for c in characters}

    scenes, synopsis_text = _parse_scenes(lines[body_start:], known_names)

    # Synopsis: タイトルページの Synopsis + Scene #0 テキスト
    if synopsis_text:
        if metadata.synopsis:
            metadata.synopsis = metadata.synopsis + "\n\n" + synopsis_text
        else:
            metadata.synopsis = synopsis_text

    return FountainParseResult(
        metadata=metadata,
        characters=characters,
        scenes=scenes,
    )


# ============================================================
# タイトルページ
# ============================================================
def _parse_title_page(lines: list[str]) -> tuple[FountainMetadata, int]:
    """ファイル先頭のタイトルページを解析する。

    Returns:
        (metadata, body_start_index)
    """
    metadata = FountainMetadata()

    if not lines:
        return metadata, 0

    # タイトルページは先頭行が "Key: Value" 形式で始まる必要がある
    first_line = lines[0].strip()
    if not re.match(r"^[A-Za-z ]+:", first_line):
        return metadata, 0

    current_key: str | None = None
    current_value_lines: list[str] = []
    end_index = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 空行でタイトルページ終了
        if stripped == "":
            if current_key is not None:
                _set_metadata_field(metadata, current_key, current_value_lines)
            end_index = i + 1
            break

        # 新しいキーの検出
        key_match = re.match(r"^([A-Za-z ]+):\s*(.*)", line)
        if key_match:
            # 前のキーを保存
            if current_key is not None:
                _set_metadata_field(metadata, current_key, current_value_lines)
            current_key = key_match.group(1).strip().lower()
            first_val = key_match.group(2).strip()
            current_value_lines = [first_val] if first_val else []
        elif current_key is not None:
            # 継続行（インデントされた行）
            current_value_lines.append(stripped)
    else:
        # ファイル全体がタイトルページ（空行なし）
        if current_key is not None:
            _set_metadata_field(metadata, current_key, current_value_lines)
        end_index = len(lines)

    return metadata, end_index


def _set_metadata_field(
    metadata: FountainMetadata, key: str, value_lines: list[str]
) -> None:
    attr = _TITLE_PAGE_KEYS.get(key)
    if attr is not None:
        value = "\n".join(value_lines).strip()
        if value:
            setattr(metadata, attr, value)


# ============================================================
# 登場人物セクション
# ============================================================
def _parse_characters_section(lines: list[str]) -> list[FountainCharacter]:
    """``# 登場人物`` セクションからキャラクター一覧を抽出する。"""
    characters: list[FountainCharacter] = []
    in_section = False
    order = 0

    for line in lines:
        stripped = line.strip()

        if _CHARACTERS_HEADING_RE.match(stripped):
            in_section = True
            continue

        if in_section:
            # 次の見出し or 空行2つで終了
            if stripped == "":
                if characters:  # セクション内の空行で終了
                    break
                continue

            if stripped.startswith("#"):
                break

            # シーン見出しで終了
            if _SCENE_HEADING_RE.match(stripped):
                break

            # 名前と説明を分割（全角/半角スペース、タブで分割）
            parts = re.split(r"[\s\t　]+", stripped, maxsplit=1)
            name = parts[0]
            description = parts[1] if len(parts) > 1 else None

            characters.append(
                FountainCharacter(name=name, description=description, sort_order=order)
            )
            order += 1

    return characters


# ============================================================
# シーンパース
# ============================================================
def _parse_scenes(
    lines: list[str], known_names: set[str]
) -> tuple[list[FountainScene], str | None]:
    """シーン見出しを検出し、各シーンのセリフを解析する。

    Returns:
        (scenes, synopsis_text): scenes はパース結果、synopsis_text は
        最初のシーン見出し前のテキスト（Scene #0）。
    """
    # 登場人物セクションの範囲を特定して除外する
    body_lines = _strip_characters_section(lines)

    scene_breaks: list[tuple[int, str]] = []  # (line_index, heading)
    for i, line in enumerate(body_lines):
        stripped = line.strip()
        if _SCENE_HEADING_RE.match(stripped):
            # 強制見出しのピリオドを除去
            heading = stripped.lstrip(".")
            scene_breaks.append((i, heading))

    # Scene #0: 最初のシーン見出し前のテキスト
    synopsis_text: str | None = None
    if scene_breaks:
        pre_scene = "\n".join(
            l.strip() for l in body_lines[: scene_breaks[0][0]]
        ).strip()
        if pre_scene:
            synopsis_text = pre_scene
    elif body_lines:
        # シーン見出しがない場合、全テキストを synopsis とする
        full_text = "\n".join(l.strip() for l in body_lines).strip()
        if full_text:
            synopsis_text = full_text

    # シーンを構築
    scenes: list[FountainScene] = []
    for idx, (start, heading) in enumerate(scene_breaks):
        end = scene_breaks[idx + 1][0] if idx + 1 < len(scene_breaks) else len(body_lines)
        scene_content = body_lines[start + 1 : end]

        scene_lines = _parse_dialogue(scene_content, known_names)

        scenes.append(
            FountainScene(
                heading=heading,
                act_number=1,
                scene_number=idx + 1,
                sort_order=idx,
                lines=scene_lines,
            )
        )

    return scenes, synopsis_text


def _strip_characters_section(lines: list[str]) -> list[str]:
    """登場人物セクションを除去したリストを返す。"""
    result: list[str] = []
    in_section = False
    found_any = False

    for line in lines:
        stripped = line.strip()

        if _CHARACTERS_HEADING_RE.match(stripped):
            in_section = True
            found_any = False
            continue

        if in_section:
            if stripped == "":
                if found_any:
                    in_section = False
                continue
            if stripped.startswith("#") or _SCENE_HEADING_RE.match(stripped):
                in_section = False
                result.append(line)
                continue
            found_any = True
            continue

        result.append(line)

    return result


# ============================================================
# セリフパース
# ============================================================
def _parse_dialogue(
    lines: list[str], known_names: set[str]
) -> list[FountainLine]:
    """シーン内のテキストからセリフを解析する。"""
    result: list[FountainLine] = []
    order = 0
    current_character: str | None = None
    dialogue_buffer: list[str] = []

    def _flush() -> None:
        nonlocal order, current_character, dialogue_buffer
        if dialogue_buffer:
            content = "\n".join(dialogue_buffer).strip()
            if content:
                result.append(
                    FountainLine(
                        character_name=current_character,
                        content=content,
                        sort_order=order,
                    )
                )
                order += 1
            dialogue_buffer = []

    for line in lines:
        stripped = line.strip()

        if stripped == "":
            _flush()
            current_character = None
            continue

        # @プレフィックス: Fountain の強制キャラクター名（@吉村 → 吉村）
        if stripped.startswith("@") and len(stripped) > 1:
            _flush()
            current_character = stripped[1:].strip()
            known_names.add(current_character)
            continue

        # キャラクター名の検出
        name_candidate = re.sub(r"[:：]\s*$", "", stripped)
        if name_candidate in known_names:
            _flush()
            current_character = name_candidate
            continue

        # 大文字のみの行もキャラクター名候補（西洋 ASCII スタイル）
        if (
            stripped == stripped.upper()
            and stripped.replace(" ", "").isascii()
            and stripped.replace(" ", "").isalpha()
            and len(stripped) > 1
        ):
            _flush()
            current_character = stripped
            known_names.add(current_character)
            continue

        # 日本語キャラクター名候補: 「名前：」または「名前:」で終わる短い行
        jp_cue_match = re.match(r"^(.+?)[:：]\s*$", stripped)
        if jp_cue_match:
            candidate = jp_cue_match.group(1).strip()
            # 短い名前（20文字以下）かつ改行を含まない → キャラクター名と判定
            if len(candidate) <= 20:
                _flush()
                current_character = candidate
                known_names.add(current_character)
                continue

        dialogue_buffer.append(stripped)

    _flush()
    return result

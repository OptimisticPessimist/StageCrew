"""アップロードファイルのテキスト抽出とFountain形式判定。"""

from __future__ import annotations

import re

import chardet


def decode_text(raw: bytes) -> str:
    """バイト列のエンコーディングを検出してデコードする。

    chardet で検出を試み、失敗時は UTF-8 (errors="replace") にフォールバック。
    """
    if not raw:
        return ""

    # BOM 付き UTF-8 を先に処理
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")

    detected = chardet.detect(raw)
    encoding = detected.get("encoding") or "utf-8"

    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return raw.decode("utf-8", errors="replace")


# Fountain 判定用のパターン
_TITLE_KEY_RE = re.compile(r"^(Title|Author|Draft date|Copyright|Contact|Notes|Synopsis):", re.IGNORECASE)
_SCENE_HEADING_RE = re.compile(
    r"^(?:INT\.|EXT\.|INT\./EXT\.|I/E)\s+",
    re.IGNORECASE | re.MULTILINE,
)
_CHARACTERS_HEADING_RE = re.compile(r"^#\s*登場人物\s*$", re.MULTILINE)


def detect_fountain(text: str) -> bool:
    """テキストが Fountain 形式かどうかをヒューリスティックに判定する。

    以下のうち 2 つ以上を満たせば Fountain と判定:
    - タイトルページキーが先頭付近にある
    - シーン見出し (INT./EXT.) がある
    - ``# 登場人物`` セクションがある
    """
    score = 0

    # タイトルページキーをチェック（先頭行が Key: Value 形式）
    # _parse_title_page と同じ前提: 1行目が Key: で始まる必要がある
    first_line = text.split("\n", 1)[0].strip()
    if _TITLE_KEY_RE.match(first_line):
        score += 1

    if _SCENE_HEADING_RE.search(text):
        score += 1

    if _CHARACTERS_HEADING_RE.search(text):
        score += 1

    return score >= 2

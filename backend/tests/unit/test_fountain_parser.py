"""Fountain パーサーのユニットテスト。"""

from src.services.fountain_parser import (
    FountainCharacter,
    FountainParseResult,
    parse_fountain,
)


# ============================================================
# タイトルページ
# ============================================================
class TestTitlePage:
    def test_full_metadata(self):
        text = """\
Title: 夏の夜の夢
Author: 山田太郎
Draft date: 2026-01-15
Copyright: (c) 2026 山田太郎
Contact: yamada@example.com
Notes: 初稿
Synopsis: 妖精の森で繰り広げられる恋愛喜劇

INT. 森 - 夜
"""
        result = parse_fountain(text)
        m = result.metadata
        assert m.title == "夏の夜の夢"
        assert m.author == "山田太郎"
        assert m.draft_date == "2026-01-15"
        assert m.copyright == "(c) 2026 山田太郎"
        assert m.contact == "yamada@example.com"
        assert m.notes == "初稿"
        assert m.synopsis == "妖精の森で繰り広げられる恋愛喜劇"

    def test_minimal_metadata(self):
        text = """\
Title: テスト脚本

INT. 部屋 - 朝
"""
        result = parse_fountain(text)
        assert result.metadata.title == "テスト脚本"
        assert result.metadata.author is None
        assert result.metadata.synopsis is None

    def test_multiline_notes(self):
        text = """\
Title: テスト
Notes: 第一稿
    改訂予定あり
    要確認事項多数

INT. 場所 - 時間
"""
        result = parse_fountain(text)
        assert "第一稿" in result.metadata.notes
        assert "改訂予定あり" in result.metadata.notes
        assert "要確認事項多数" in result.metadata.notes

    def test_no_title_page(self):
        text = "INT. 部屋 - 朝\n\n太郎：\nおはよう\n"
        result = parse_fountain(text)
        assert result.metadata.title is None


# ============================================================
# 登場人物セクション
# ============================================================
class TestCharactersSection:
    def test_parse_characters(self):
        text = """\
Title: テスト

# 登場人物
太郎　主人公の青年
花子　太郎の幼馴染
次郎

INT. 部屋 - 朝
"""
        result = parse_fountain(text)
        assert len(result.characters) == 3
        assert result.characters[0].name == "太郎"
        assert result.characters[0].description == "主人公の青年"
        assert result.characters[1].name == "花子"
        assert result.characters[1].description == "太郎の幼馴染"
        assert result.characters[2].name == "次郎"
        assert result.characters[2].description is None

    def test_character_sort_order(self):
        text = """\
Title: テスト

# 登場人物
A
B
C

INT. 場所
"""
        result = parse_fountain(text)
        assert [c.sort_order for c in result.characters] == [0, 1, 2]

    def test_no_characters_section(self):
        text = """\
Title: テスト

INT. 部屋 - 朝
"""
        result = parse_fountain(text)
        assert result.characters == []


# ============================================================
# シーン見出し検出
# ============================================================
class TestSceneHeadings:
    def test_standard_headings(self):
        text = """\
Title: テスト

INT. 部屋 - 朝

EXT. 公園 - 昼

INT./EXT. 車内 - 夕方
"""
        result = parse_fountain(text)
        assert len(result.scenes) == 3
        assert result.scenes[0].heading == "INT. 部屋 - 朝"
        assert result.scenes[1].heading == "EXT. 公園 - 昼"
        assert result.scenes[2].heading == "INT./EXT. 車内 - 夕方"

    def test_forced_heading(self):
        text = """\
Title: テスト

.第一幕 開場
"""
        result = parse_fountain(text)
        assert len(result.scenes) == 1
        assert result.scenes[0].heading == "第一幕 開場"

    def test_scene_numbering(self):
        text = """\
Title: テスト

INT. 部屋A

INT. 部屋B

INT. 部屋C
"""
        result = parse_fountain(text)
        assert len(result.scenes) == 3
        assert result.scenes[0].scene_number == 1
        assert result.scenes[1].scene_number == 2
        assert result.scenes[2].scene_number == 3
        assert [s.sort_order for s in result.scenes] == [0, 1, 2]


# ============================================================
# あらすじ (Synopsis)
# ============================================================
class TestSynopsis:
    def test_scene_zero_as_synopsis(self):
        text = """\
Title: テスト

ある夏の日の物語。
主人公は旅に出る。

INT. 駅 - 朝
"""
        result = parse_fountain(text)
        assert "ある夏の日の物語" in result.metadata.synopsis
        assert "主人公は旅に出る" in result.metadata.synopsis

    def test_synopsis_key_and_scene_zero_combined(self):
        text = """\
Title: テスト
Synopsis: 妖精の物語

序章：むかしむかし

INT. 森 - 夜
"""
        result = parse_fountain(text)
        assert "妖精の物語" in result.metadata.synopsis
        assert "序章：むかしむかし" in result.metadata.synopsis

    def test_synopsis_key_only(self):
        text = """\
Title: テスト
Synopsis: 短い説明

INT. 部屋 - 朝
"""
        result = parse_fountain(text)
        assert result.metadata.synopsis == "短い説明"

    def test_no_synopsis(self):
        text = """\
Title: テスト

INT. 部屋 - 朝
"""
        result = parse_fountain(text)
        assert result.metadata.synopsis is None


# ============================================================
# セリフ解析
# ============================================================
class TestDialogue:
    def test_character_dialogue(self):
        text = """\
Title: テスト

# 登場人物
太郎
花子

INT. 部屋 - 朝

太郎：
おはようございます。
今日はいい天気ですね。

花子：
そうですね。
"""
        result = parse_fountain(text)
        assert len(result.scenes) == 1
        lines = result.scenes[0].lines
        assert len(lines) == 2
        assert lines[0].character_name == "太郎"
        assert "おはようございます" in lines[0].content
        assert "今日はいい天気ですね" in lines[0].content
        assert lines[1].character_name == "花子"
        assert "そうですね" in lines[1].content

    def test_western_style_character(self):
        text = """\
Title: Test

INT. ROOM - DAY

JOHN
Hello, world!

MARY
Hi there!
"""
        result = parse_fountain(text)
        lines = result.scenes[0].lines
        assert len(lines) == 2
        assert lines[0].character_name == "JOHN"
        assert lines[0].content == "Hello, world!"
        assert lines[1].character_name == "MARY"

    def test_japanese_cue_without_characters_section(self):
        """# 登場人物 セクションがなくても日本語キャラ名：で検出される。"""
        text = """\
Title: テスト

INT. 部屋 - 朝

太郎：
おはよう。

花子：
おはようございます。
"""
        result = parse_fountain(text)
        lines = result.scenes[0].lines
        assert len(lines) == 2
        assert lines[0].character_name == "太郎"
        assert lines[0].content == "おはよう。"
        assert lines[1].character_name == "花子"
        assert lines[1].content == "おはようございます。"

    def test_line_sort_order(self):
        text = """\
Title: テスト

# 登場人物
太郎
花子

INT. 部屋

太郎：
セリフ1

花子：
セリフ2

太郎：
セリフ3
"""
        result = parse_fountain(text)
        lines = result.scenes[0].lines
        assert [l.sort_order for l in lines] == [0, 1, 2]


# ============================================================
# E2E パース
# ============================================================
class TestFullParse:
    def test_complete_fountain(self):
        text = """\
Title: 星の王子さま
Author: テスト作家
Draft date: 2026-03-20
Synopsis: 砂漠に不時着した飛行士と星の王子の物語

# 登場人物
飛行士　砂漠に不時着したパイロット
王子　小さな星からやってきた少年
バラ　王子の星に咲く一輪のバラ

INT. 砂漠 - 夜

飛行士：
エンジンが壊れてしまった。
水はあと一日分しかない。

王子：
ねえ、ヒツジの絵を描いて。

EXT. 小さな星 - 昼

王子：
バラ、きみを置いていくよ。

バラ：
...行ってらっしゃい。
"""
        result = parse_fountain(text)

        # メタデータ
        assert result.metadata.title == "星の王子さま"
        assert result.metadata.author == "テスト作家"
        assert result.metadata.draft_date == "2026-03-20"
        assert "砂漠に不時着した飛行士" in result.metadata.synopsis

        # 登場人物
        assert len(result.characters) == 3
        names = [c.name for c in result.characters]
        assert "飛行士" in names
        assert "王子" in names
        assert "バラ" in names

        # シーン
        assert len(result.scenes) == 2
        assert "砂漠" in result.scenes[0].heading
        assert "小さな星" in result.scenes[1].heading

        # セリフ
        scene1_lines = result.scenes[0].lines
        assert len(scene1_lines) == 2
        assert scene1_lines[0].character_name == "飛行士"
        assert scene1_lines[1].character_name == "王子"

        scene2_lines = result.scenes[1].lines
        assert len(scene2_lines) == 2
        assert scene2_lines[0].character_name == "王子"
        assert scene2_lines[1].character_name == "バラ"

    def test_unknown_character_in_dialogue(self):
        """登場人物セクションにないキャラがセリフに出現する場合。"""
        text = """\
Title: テスト

# 登場人物
太郎

INT. 部屋

太郎：
こんにちは。

NARRATOR
物語はこうして始まった。
"""
        result = parse_fountain(text)
        lines = result.scenes[0].lines
        assert len(lines) == 2
        assert lines[0].character_name == "太郎"
        assert lines[1].character_name == "NARRATOR"

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Line, Scene, SceneCharacterMapping


async def generate_scene_chart_mappings(
    script_id: uuid.UUID,
    db: AsyncSession,
    *,
    preserve_manual: bool = False,
) -> None:
    """Line データから香盤表マッピングを自動生成する。

    preserve_manual=True の場合、手動追加されたマッピングを保持し
    自動生成分のみ再作成する。
    """
    # 既存マッピングを削除
    if preserve_manual:
        del_stmt = delete(SceneCharacterMapping).where(
            SceneCharacterMapping.scene_id.in_(select(Scene.id).where(Scene.script_id == script_id)),
            SceneCharacterMapping.is_auto_generated.is_(True),
        )
    else:
        del_stmt = delete(SceneCharacterMapping).where(
            SceneCharacterMapping.scene_id.in_(select(Scene.id).where(Scene.script_id == script_id)),
        )
    await db.execute(del_stmt)

    # Line テーブルから distinct (scene_id, character_id) を取得
    pairs_stmt = (
        select(Line.scene_id, Line.character_id)
        .join(Scene, Line.scene_id == Scene.id)
        .where(Scene.script_id == script_id, Line.character_id.isnot(None))
        .distinct()
    )
    result = await db.execute(pairs_stmt)
    pairs = result.all()

    if preserve_manual:
        # 手動マッピングが残っているペアを取得
        existing_stmt = select(SceneCharacterMapping.scene_id, SceneCharacterMapping.character_id).where(
            SceneCharacterMapping.scene_id.in_(select(Scene.id).where(Scene.script_id == script_id)),
        )
        existing_result = await db.execute(existing_stmt)
        existing_pairs = {(row[0], row[1]) for row in existing_result.all()}
    else:
        existing_pairs = set()

    # 新しい auto-generated マッピングを挿入
    for scene_id, character_id in pairs:
        if (scene_id, character_id) in existing_pairs:
            continue
        mapping = SceneCharacterMapping(
            scene_id=scene_id,
            character_id=character_id,
            appearance_type="dialogue",
            is_auto_generated=True,
        )
        db.add(mapping)

    await db.flush()

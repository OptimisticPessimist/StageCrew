import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.db.models import (
    Character,
    OrganizationMembership,
    Production,
    Scene,
    SceneCharacterMapping,
    Script,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.scene_chart import (
    SceneCharacterMappingCreate,
    SceneCharacterMappingResponse,
    SceneCharacterMappingUpdate,
    SceneChartCell,
    SceneChartCharacter,
    SceneChartGenerateRequest,
    SceneChartResponse,
    SceneChartScene,
)
from src.services.scene_chart import generate_scene_chart_mappings

router = APIRouter()


# ============================================================
# エンドポイント
# ============================================================


@router.get("/", response_model=SceneChartResponse)
async def get_scene_chart(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """香盤表（シーン×登場人物マトリクス）を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, org_id, db)
    return await _build_scene_chart(script_id, db)


@router.post("/generate", response_model=SceneChartResponse)
async def generate_scene_chart(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    body: SceneChartGenerateRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Line データから香盤表を自動生成"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, org_id, db)

    preserve_manual = body.preserve_manual if body else True
    await generate_scene_chart_mappings(script_id, db, preserve_manual=preserve_manual)
    return await _build_scene_chart(script_id, db)


@router.post("/mappings", response_model=SceneCharacterMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_mapping(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    body: SceneCharacterMappingCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """手動で香盤表マッピングを追加"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, org_id, db)
    await _validate_scene_in_script(body.scene_id, script_id, db)
    await _validate_character_in_script(body.character_id, script_id, db)

    # 重複チェック
    existing = await db.execute(
        select(SceneCharacterMapping).where(
            SceneCharacterMapping.scene_id == body.scene_id,
            SceneCharacterMapping.character_id == body.character_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="このシーンには既にこの登場人物のマッピングが存在します",
        )

    mapping = SceneCharacterMapping(
        scene_id=body.scene_id,
        character_id=body.character_id,
        appearance_type=body.appearance_type.value,
        is_auto_generated=False,
        note=body.note,
    )
    db.add(mapping)
    try:
        await db.flush()
    except Exception as exc:
        from sqlalchemy.exc import IntegrityError

        if isinstance(exc, IntegrityError):
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="このシーンには既にこの登場人物のマッピングが存在します",
            ) from exc
        raise

    await db.refresh(mapping)
    return mapping


@router.patch("/mappings/{mapping_id}", response_model=SceneCharacterMappingResponse)
async def update_mapping(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    mapping_id: uuid.UUID,
    body: SceneCharacterMappingUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """香盤表マッピングを更新"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, org_id, db)
    mapping = await _get_mapping_or_404(mapping_id, script_id, db)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(mapping, key, value)

    await db.flush()
    await db.refresh(mapping)
    return mapping


@router.delete("/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    mapping_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """香盤表マッピングを削除"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, org_id, db)
    mapping = await _get_mapping_or_404(mapping_id, script_id, db)
    await db.delete(mapping)


# ============================================================
# ヘルパー
# ============================================================


async def _check_org_membership(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="この団体のメンバーではありません")


async def _get_script_or_404(
    script_id: uuid.UUID, production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> Script:
    result = await db.execute(
        select(Script)
        .join(Production, Script.production_id == Production.id)
        .where(
            Script.id == script_id,
            Script.production_id == production_id,
            Production.organization_id == org_id,
        )
    )
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="脚本が見つかりません")
    return script


async def _validate_scene_in_script(scene_id: uuid.UUID, script_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(select(Scene.id).where(Scene.id == scene_id, Scene.script_id == script_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="指定されたシーンはこの脚本に属していません",
        )


async def _validate_character_in_script(character_id: uuid.UUID, script_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(Character.id).where(Character.id == character_id, Character.script_id == script_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="指定された登場人物はこの脚本に属していません",
        )


async def _get_mapping_or_404(mapping_id: uuid.UUID, script_id: uuid.UUID, db: AsyncSession) -> SceneCharacterMapping:
    result = await db.execute(
        select(SceneCharacterMapping)
        .join(Scene, SceneCharacterMapping.scene_id == Scene.id)
        .where(SceneCharacterMapping.id == mapping_id, Scene.script_id == script_id)
    )
    mapping = result.scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=404, detail="香盤表マッピングが見つかりません")
    return mapping


async def _build_scene_chart(script_id: uuid.UUID, db: AsyncSession) -> SceneChartResponse:
    """香盤表マトリクスレスポンスを構築する。"""
    # シーン一覧
    scenes_result = await db.execute(
        select(Scene)
        .where(Scene.script_id == script_id)
        .order_by(Scene.sort_order, Scene.act_number, Scene.scene_number)
    )
    scenes = list(scenes_result.scalars().all())

    # キャラクター一覧
    chars_result = await db.execute(
        select(Character).where(Character.script_id == script_id).order_by(Character.sort_order, Character.name)
    )
    characters = list(chars_result.scalars().all())

    # マッピング一覧
    scene_ids = [s.id for s in scenes]
    if scene_ids:
        mappings_result = await db.execute(
            select(SceneCharacterMapping).where(SceneCharacterMapping.scene_id.in_(scene_ids))
        )
        mappings = list(mappings_result.scalars().all())
    else:
        mappings = []

    # マトリクス構築: {scene_id_str: {character_id_str: cell | None}}
    mapping_lookup: dict[tuple[uuid.UUID, uuid.UUID], SceneCharacterMapping] = {
        (m.scene_id, m.character_id): m for m in mappings
    }

    matrix: dict[str, dict[str, SceneChartCell | None]] = {}
    for scene in scenes:
        row: dict[str, SceneChartCell | None] = {}
        for char in characters:
            m = mapping_lookup.get((scene.id, char.id))
            if m is not None:
                row[str(char.id)] = SceneChartCell(
                    mapping_id=m.id,
                    appearance_type=m.appearance_type,
                    is_auto_generated=m.is_auto_generated,
                    note=m.note,
                )
            else:
                row[str(char.id)] = None
        matrix[str(scene.id)] = row

    return SceneChartResponse(
        characters=[SceneChartCharacter.model_validate(c) for c in characters],
        scenes=[SceneChartScene.model_validate(s) for s in scenes],
        matrix=matrix,
    )

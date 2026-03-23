import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import (
    Character,
    Line,
    OrganizationMembership,
    Production,
    Scene,
    Script,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.scripts import (
    CharacterCreate,
    CharacterResponse,
    CharacterUpdate,
    LineCreate,
    LineResponse,
    LineUpdate,
    SceneCreate,
    SceneResponse,
    SceneUpdate,
    ScriptCreate,
    ScriptDetailResponse,
    ScriptListResponse,
    ScriptUpdate,
)

router = APIRouter()


# ============================================================
# Script CRUD
# ============================================================


@router.get("/", response_model=list[ScriptListResponse])
async def list_scripts(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演の脚本一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    stmt = (
        select(Script)
        .where(Script.production_id == production_id)
        .order_by(Script.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=ScriptDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_script(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    body: ScriptCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """脚本を作成"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    script = Script(
        production_id=production_id,
        uploaded_by=current_user.id,
        **body.model_dump(),
    )
    db.add(script)
    await db.flush()

    return await _load_script_detail(script.id, production_id, db)


@router.get("/{script_id}", response_model=ScriptDetailResponse)
async def get_script(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """脚本の詳細を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    return await _load_script_detail(script_id, production_id, db)


@router.patch("/{script_id}", response_model=ScriptDetailResponse)
async def update_script(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    body: ScriptUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """脚本を更新"""
    await _check_org_membership(org_id, current_user.id, db)
    script = await _get_script_or_404(script_id, production_id, db)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(script, key, value)

    await db.flush()
    return await _load_script_detail(script.id, production_id, db)


@router.delete("/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_script(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """脚本を削除"""
    await _check_org_membership(org_id, current_user.id, db)
    script = await _get_script_or_404(script_id, production_id, db)
    await db.delete(script)


# ============================================================
# Scene CRUD
# ============================================================


@router.get("/{script_id}/scenes", response_model=list[SceneResponse])
async def list_scenes(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """シーン一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, db)

    stmt = (
        select(Scene)
        .where(Scene.script_id == script_id)
        .order_by(Scene.sort_order, Scene.act_number, Scene.scene_number)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/{script_id}/scenes", response_model=SceneResponse, status_code=status.HTTP_201_CREATED)
async def create_scene(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    body: SceneCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """シーンを作成"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, db)

    scene = Scene(script_id=script_id, **body.model_dump())
    db.add(scene)
    await db.flush()
    return scene


@router.patch("/{script_id}/scenes/{scene_id}", response_model=SceneResponse)
async def update_scene(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    scene_id: uuid.UUID,
    body: SceneUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """シーンを更新"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, db)
    scene = await _get_scene_or_404(scene_id, script_id, db)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(scene, key, value)

    await db.flush()
    return scene


@router.delete("/{script_id}/scenes/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scene(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    scene_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """シーンを削除"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, db)
    scene = await _get_scene_or_404(scene_id, script_id, db)
    await db.delete(scene)


# ============================================================
# Character CRUD
# ============================================================


@router.get("/{script_id}/characters", response_model=list[CharacterResponse])
async def list_characters(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """登場人物一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, db)

    stmt = (
        select(Character)
        .where(Character.script_id == script_id)
        .order_by(Character.sort_order, Character.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/{script_id}/characters", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    body: CharacterCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """登場人物を作成"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, db)

    character = Character(script_id=script_id, **body.model_dump())
    db.add(character)
    await db.flush()
    return character


@router.patch("/{script_id}/characters/{character_id}", response_model=CharacterResponse)
async def update_character(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    character_id: uuid.UUID,
    body: CharacterUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """登場人物を更新"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, db)
    character = await _get_character_or_404(character_id, script_id, db)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(character, key, value)

    await db.flush()
    return character


@router.delete("/{script_id}/characters/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    character_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """登場人物を削除"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, db)
    character = await _get_character_or_404(character_id, script_id, db)
    await db.delete(character)


# ============================================================
# Line CRUD
# ============================================================


@router.get("/{script_id}/scenes/{scene_id}/lines", response_model=list[LineResponse])
async def list_lines(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    scene_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """セリフ一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, db)
    await _get_scene_or_404(scene_id, script_id, db)

    stmt = (
        select(Line)
        .where(Line.scene_id == scene_id)
        .order_by(Line.sort_order)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "/{script_id}/scenes/{scene_id}/lines",
    response_model=LineResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_line(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    scene_id: uuid.UUID,
    body: LineCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """セリフを作成"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, db)
    await _get_scene_or_404(scene_id, script_id, db)

    line = Line(scene_id=scene_id, **body.model_dump())
    db.add(line)
    await db.flush()
    return line


@router.patch("/{script_id}/scenes/{scene_id}/lines/{line_id}", response_model=LineResponse)
async def update_line(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    scene_id: uuid.UUID,
    line_id: uuid.UUID,
    body: LineUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """セリフを更新"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, db)
    await _get_scene_or_404(scene_id, script_id, db)
    line = await _get_line_or_404(line_id, scene_id, db)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(line, key, value)

    await db.flush()
    return line


@router.delete("/{script_id}/scenes/{scene_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_line(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    scene_id: uuid.UUID,
    line_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """セリフを削除"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, db)
    await _get_scene_or_404(scene_id, script_id, db)
    line = await _get_line_or_404(line_id, scene_id, db)
    await db.delete(line)


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


async def _get_production_or_404(production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Production:
    result = await db.execute(
        select(Production).where(Production.id == production_id, Production.organization_id == org_id)
    )
    production = result.scalar_one_or_none()
    if production is None:
        raise HTTPException(status_code=404, detail="公演が見つかりません")
    return production


async def _get_script_or_404(script_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession) -> Script:
    result = await db.execute(
        select(Script).where(Script.id == script_id, Script.production_id == production_id)
    )
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="脚本が見つかりません")
    return script


async def _get_scene_or_404(scene_id: uuid.UUID, script_id: uuid.UUID, db: AsyncSession) -> Scene:
    result = await db.execute(
        select(Scene).where(Scene.id == scene_id, Scene.script_id == script_id)
    )
    scene = result.scalar_one_or_none()
    if scene is None:
        raise HTTPException(status_code=404, detail="シーンが見つかりません")
    return scene


async def _get_character_or_404(character_id: uuid.UUID, script_id: uuid.UUID, db: AsyncSession) -> Character:
    result = await db.execute(
        select(Character).where(Character.id == character_id, Character.script_id == script_id)
    )
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="登場人物が見つかりません")
    return character


async def _get_line_or_404(line_id: uuid.UUID, scene_id: uuid.UUID, db: AsyncSession) -> Line:
    result = await db.execute(
        select(Line).where(Line.id == line_id, Line.scene_id == scene_id)
    )
    line = result.scalar_one_or_none()
    if line is None:
        raise HTTPException(status_code=404, detail="セリフが見つかりません")
    return line


async def _load_script_detail(script_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession) -> ScriptDetailResponse:
    stmt = (
        select(Script)
        .where(Script.id == script_id, Script.production_id == production_id)
        .options(
            selectinload(Script.uploader),
            selectinload(Script.scenes).selectinload(Scene.lines),
            selectinload(Script.characters),
        )
    )
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="脚本が見つかりません")

    return ScriptDetailResponse.model_validate(script)

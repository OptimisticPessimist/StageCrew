import os
import re
import uuid
from datetime import UTC, datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
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
from src.services.file_extractor import decode_text, detect_fountain
from src.services.fountain_parser import parse_fountain
from src.services.script_pdf import generate_script_pdf

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".txt", ".fountain"}

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

    stmt = select(Script).where(Script.production_id == production_id).order_by(Script.created_at.desc())
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

    return await _load_script_detail(script.id, production_id, org_id, db)


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
    return await _load_script_detail(script_id, production_id, org_id, db)


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
    script = await _get_script_or_404(script_id, production_id, org_id, db)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(script, key, value)

    await db.flush()
    return await _load_script_detail(script.id, production_id, org_id, db)


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
    script = await _get_script_or_404(script_id, production_id, org_id, db)
    await db.delete(script)


# ============================================================
# Upload
# ============================================================


@router.post("/upload", response_model=ScriptDetailResponse, status_code=status.HTTP_201_CREATED)
async def upload_script(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    file: UploadFile,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ファイルをアップロードして脚本を作成する。

    Fountain 形式の場合はメタデータ・シーン・登場人物・セリフを自動解析する。
    それ以外のテキストファイルはコンテンツのみ保存し、シーン等は手動登録。
    """
    await _check_org_membership(org_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    # 拡張子チェック
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"対応していないファイル形式です。対応形式: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # チャンク読み込みでサイズを検証（全バッファリング前に拒否）
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(64 * 1024):
        total += len(chunk)
        if total > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="ファイルサイズが上限（10MB）を超えています")
        chunks.append(chunk)
    raw = b"".join(chunks)

    # テキストデコード
    text = decode_text(raw)

    # Fountain 判定
    is_fountain = ext == ".fountain" or detect_fountain(text)

    if is_fountain:
        parsed = parse_fountain(text)
        meta = parsed.metadata

        script = Script(
            production_id=production_id,
            uploaded_by=current_user.id,
            title=_truncate(meta.title, 256) or _truncate(os.path.splitext(filename)[0], 256) or "無題",
            content=text,
            author=_truncate(meta.author, 256),
            draft_date=_parse_draft_date(meta.draft_date),
            copyright=_truncate(meta.copyright, 512),
            contact=_truncate(meta.contact, 512),
            notes=meta.notes,
            synopsis=meta.synopsis,
        )
        db.add(script)
        await db.flush()

        # 登場人物を作成し、名前→IDのマップを構築
        char_name_to_id: dict[str, uuid.UUID] = {}
        for fc in parsed.characters:
            char = Character(
                script_id=script.id,
                name=_truncate(fc.name, 128) or fc.name[:128],
                description=fc.description,
                sort_order=fc.sort_order,
            )
            db.add(char)
            await db.flush()
            char_name_to_id[fc.name] = char.id

        # シーンとセリフを作成
        for fs in parsed.scenes:
            scene = Scene(
                script_id=script.id,
                act_number=fs.act_number,
                scene_number=fs.scene_number,
                heading=_truncate(fs.heading, 256) or fs.heading[:256],
                description=fs.description,
                sort_order=fs.sort_order,
            )
            db.add(scene)
            await db.flush()

            for fl in fs.lines:
                # 未知のキャラクターを自動作成
                char_id = None
                if fl.character_name:
                    if fl.character_name not in char_name_to_id:
                        new_char = Character(
                            script_id=script.id,
                            name=_truncate(fl.character_name, 128) or fl.character_name[:128],
                            sort_order=len(char_name_to_id),
                        )
                        db.add(new_char)
                        await db.flush()
                        char_name_to_id[fl.character_name] = new_char.id
                    char_id = char_name_to_id[fl.character_name]

                line = Line(
                    scene_id=scene.id,
                    character_id=char_id,
                    content=fl.content,
                    sort_order=fl.sort_order,
                )
                db.add(line)

        await db.flush()

        # 香盤表を自動生成
        from src.services.scene_chart import generate_scene_chart_mappings

        await generate_scene_chart_mappings(script.id, db)
    else:
        # 非 Fountain: テキストのみ保存
        title = _truncate(os.path.splitext(filename)[0], 256) or "無題"
        script = Script(
            production_id=production_id,
            uploaded_by=current_user.id,
            title=title,
            content=text,
        )
        db.add(script)
        await db.flush()

    return await _load_script_detail(script.id, production_id, org_id, db)


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
    await _get_script_or_404(script_id, production_id, org_id, db)

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
    await _get_script_or_404(script_id, production_id, org_id, db)

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
    await _get_script_or_404(script_id, production_id, org_id, db)
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
    await _get_script_or_404(script_id, production_id, org_id, db)
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
    await _get_script_or_404(script_id, production_id, org_id, db)

    stmt = (
        select(Character)
        .where(Character.script_id == script_id)
        .options(selectinload(Character.castings))
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
    await _get_script_or_404(script_id, production_id, org_id, db)

    character = Character(script_id=script_id, **body.model_dump())
    db.add(character)
    await db.flush()
    return await _load_character_with_castings(character.id, script_id, db)


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
    await _get_script_or_404(script_id, production_id, org_id, db)
    character = await _get_character_or_404(character_id, script_id, db)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(character, key, value)

    await db.flush()
    return await _load_character_with_castings(character.id, script_id, db)


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
    await _get_script_or_404(script_id, production_id, org_id, db)
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
    await _get_script_or_404(script_id, production_id, org_id, db)
    await _get_scene_or_404(scene_id, script_id, db)

    stmt = select(Line).where(Line.scene_id == scene_id).order_by(Line.sort_order)
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
    await _get_script_or_404(script_id, production_id, org_id, db)
    await _get_scene_or_404(scene_id, script_id, db)

    if body.character_id is not None:
        await _validate_character_in_script(body.character_id, script_id, db)

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
    await _get_script_or_404(script_id, production_id, org_id, db)
    await _get_scene_or_404(scene_id, script_id, db)
    line = await _get_line_or_404(line_id, scene_id, db)

    update_data = body.model_dump(exclude_unset=True)
    if "character_id" in update_data and update_data["character_id"] is not None:
        await _validate_character_in_script(update_data["character_id"], script_id, db)

    for key, value in update_data.items():
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
    await _get_script_or_404(script_id, production_id, org_id, db)
    await _get_scene_or_404(scene_id, script_id, db)
    line = await _get_line_or_404(line_id, scene_id, db)
    await db.delete(line)


# ============================================================
# PDF ダウンロード
# ============================================================


@router.get("/{script_id}/pdf")
async def download_script_pdf(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """脚本をPDFとしてダウンロード"""
    await _check_org_membership(org_id, current_user.id, db)

    # Script + scenes(lines) + characters を eager load
    stmt = (
        select(Script)
        .join(Production, Script.production_id == Production.id)
        .where(
            Script.id == script_id,
            Script.production_id == production_id,
            Production.organization_id == org_id,
        )
        .options(
            selectinload(Script.scenes).selectinload(Scene.lines),
            selectinload(Script.characters),
        )
    )
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="脚本が見つかりません")

    # ソート
    script.scenes.sort(key=lambda s: (s.sort_order, s.act_number, s.scene_number))
    for scene in script.scenes:
        scene.lines.sort(key=lambda ln: ln.sort_order)
    script.characters.sort(key=lambda c: (c.sort_order, c.name))

    pdf_bytes = generate_script_pdf(script, script.scenes, script.characters)

    # ファイル名をサニタイズ + RFC 5987 パーセントエンコード
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", script.title)
    filename_encoded = quote(f"{safe_name}.pdf")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"},
    )


# ============================================================
# ヘルパー
# ============================================================


def _truncate(value: str | None, max_len: int) -> str | None:
    """文字列を DB カラムの最大長に切り詰める。"""
    if value is None:
        return None
    return value[:max_len]


_DRAFT_DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"]


def _parse_draft_date(value: str | None) -> datetime | None:
    """Fountain の Draft date 文字列を datetime に変換する。"""
    if not value:
        return None
    for fmt in _DRAFT_DATE_FORMATS:
        try:
            dt = datetime.strptime(value.strip(), fmt)
            return dt.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


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


async def _get_scene_or_404(scene_id: uuid.UUID, script_id: uuid.UUID, db: AsyncSession) -> Scene:
    result = await db.execute(select(Scene).where(Scene.id == scene_id, Scene.script_id == script_id))
    scene = result.scalar_one_or_none()
    if scene is None:
        raise HTTPException(status_code=404, detail="シーンが見つかりません")
    return scene


async def _validate_character_in_script(character_id: uuid.UUID, script_id: uuid.UUID, db: AsyncSession) -> None:
    """character_id が指定スクリプトに属するか検証"""
    result = await db.execute(
        select(Character.id).where(Character.id == character_id, Character.script_id == script_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="指定された登場人物はこの脚本に属していません",
        )


async def _load_character_with_castings(character_id: uuid.UUID, script_id: uuid.UUID, db: AsyncSession) -> Character:
    result = await db.execute(
        select(Character)
        .where(Character.id == character_id, Character.script_id == script_id)
        .options(selectinload(Character.castings))
    )
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="登場人物が見つかりません")
    return character


async def _get_character_or_404(character_id: uuid.UUID, script_id: uuid.UUID, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.id == character_id, Character.script_id == script_id))
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=404, detail="登場人物が見つかりません")
    return character


async def _get_line_or_404(line_id: uuid.UUID, scene_id: uuid.UUID, db: AsyncSession) -> Line:
    result = await db.execute(select(Line).where(Line.id == line_id, Line.scene_id == scene_id))
    line = result.scalar_one_or_none()
    if line is None:
        raise HTTPException(status_code=404, detail="セリフが見つかりません")
    return line


async def _load_script_detail(
    script_id: uuid.UUID, production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession
) -> ScriptDetailResponse:
    stmt = (
        select(Script)
        .join(Production, Script.production_id == Production.id)
        .where(
            Script.id == script_id,
            Script.production_id == production_id,
            Production.organization_id == org_id,
        )
        .options(
            selectinload(Script.uploader),
            selectinload(Script.scenes).selectinload(Scene.lines),
            selectinload(Script.characters).selectinload(Character.castings),
        )
    )
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()
    if script is None:
        raise HTTPException(status_code=404, detail="脚本が見つかりません")

    # ネストコレクションを安定したソート順で返す
    script.scenes.sort(key=lambda s: (s.sort_order, s.act_number, s.scene_number))
    for scene in script.scenes:
        scene.lines.sort(key=lambda ln: ln.sort_order)
    script.characters.sort(key=lambda c: (c.sort_order, c.name))

    return ScriptDetailResponse.model_validate(script)

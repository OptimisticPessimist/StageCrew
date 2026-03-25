import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import (
    Casting,
    Character,
    OrganizationMembership,
    Production,
    ProductionMembership,
    Script,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.castings import (
    CastingCreate,
    CastingResponse,
    CastingUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[CastingResponse])
async def list_castings(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """キャスティング一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, org_id, db)

    stmt = (
        select(Casting)
        .join(Character, Casting.character_id == Character.id)
        .where(Character.script_id == script_id)
        .options(
            selectinload(Casting.character),
            selectinload(Casting.production_membership).selectinload(ProductionMembership.user),
        )
        .order_by(Casting.sort_order)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=CastingResponse, status_code=status.HTTP_201_CREATED)
async def create_casting(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    body: CastingCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """キャスト割当を作成"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, org_id, db)

    # character がこの脚本に属するか検証
    await _validate_character_in_script(body.character_id, script_id, db)

    # production_membership がこの公演に属するか検証
    await _validate_membership_in_production(body.production_membership_id, production_id, db)

    # 重複チェック（楽観的: race condition は DB 制約で捕捉）
    existing = await db.execute(
        select(Casting).where(
            Casting.character_id == body.character_id,
            Casting.production_membership_id == body.production_membership_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この登場人物には既にこのメンバーが割り当てられています",
        )

    casting = Casting(**body.model_dump())
    db.add(casting)
    try:
        await db.flush()
    except Exception as exc:
        # 並行リクエストで UNIQUE 制約に違反した場合
        from sqlalchemy.exc import IntegrityError

        if isinstance(exc, IntegrityError):
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="この登場人物には既にこのメンバーが割り当てられています",
            ) from exc
        raise

    return await _load_casting(casting.id, db)


@router.patch("/{casting_id}", response_model=CastingResponse)
async def update_casting(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    casting_id: uuid.UUID,
    body: CastingUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """キャスト割当を更新"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, org_id, db)
    casting = await _get_casting_or_404(casting_id, script_id, db)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(casting, key, value)

    await db.flush()
    return await _load_casting(casting.id, db)


@router.delete("/{casting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_casting(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    script_id: uuid.UUID,
    casting_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """キャスト割当を削除"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_script_or_404(script_id, production_id, org_id, db)
    casting = await _get_casting_or_404(casting_id, script_id, db)
    await db.delete(casting)


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


async def _validate_character_in_script(character_id: uuid.UUID, script_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(Character.id).where(Character.id == character_id, Character.script_id == script_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="指定された登場人物はこの脚本に属していません",
        )


async def _validate_membership_in_production(
    membership_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession
) -> None:
    result = await db.execute(
        select(ProductionMembership.id).where(
            ProductionMembership.id == membership_id,
            ProductionMembership.production_id == production_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="指定されたメンバーはこの公演に属していません",
        )


async def _get_casting_or_404(casting_id: uuid.UUID, script_id: uuid.UUID, db: AsyncSession) -> Casting:
    result = await db.execute(
        select(Casting)
        .join(Character, Casting.character_id == Character.id)
        .where(Casting.id == casting_id, Character.script_id == script_id)
    )
    casting = result.scalar_one_or_none()
    if casting is None:
        raise HTTPException(status_code=404, detail="キャスティングが見つかりません")
    return casting


async def _load_casting(casting_id: uuid.UUID, db: AsyncSession) -> Casting:
    result = await db.execute(
        select(Casting)
        .where(Casting.id == casting_id)
        .options(
            selectinload(Casting.character),
            selectinload(Casting.production_membership).selectinload(ProductionMembership.user),
        )
    )
    casting = result.scalar_one_or_none()
    if casting is None:
        raise HTTPException(status_code=404, detail="キャスティングが見つかりません")
    return casting

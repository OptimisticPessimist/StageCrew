import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import (
    Comment,
    Issue,
    OrganizationMembership,
    Production,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.comments import CommentCreate, CommentResponse, CommentUpdate
from src.services.discord_webhook import notify_comment_added

router = APIRouter()


@router.get("/", response_model=list[CommentResponse])
async def list_comments(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    issue_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """課題のコメント一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_issue_or_404(issue_id, production_id, org_id, db)

    stmt = (
        select(Comment)
        .where(Comment.issue_id == issue_id)
        .options(selectinload(Comment.user))
        .order_by(Comment.created_at.asc())
    )
    result = await db.execute(stmt)
    comments = result.scalars().all()

    return [
        CommentResponse(
            id=c.id,
            issue_id=c.issue_id,
            user_id=c.user_id,
            display_name=c.user.display_name,
            content=c.content,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in comments
    ]


@router.post("/", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    issue_id: uuid.UUID,
    body: CommentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """コメントを作成"""
    await _check_org_membership(org_id, current_user.id, db)
    issue, production = await _get_issue_or_404(issue_id, production_id, org_id, db)

    comment = Comment(
        issue_id=issue_id,
        user_id=current_user.id,
        content=body.content,
    )
    db.add(comment)
    await db.flush()

    notify_comment_added(
        production.discord_webhook_url,
        issue_title=issue.title,
        comment_content=body.content,
        commenter_name=current_user.display_name,
    )

    return CommentResponse(
        id=comment.id,
        issue_id=comment.issue_id,
        user_id=comment.user_id,
        display_name=current_user.display_name,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.patch("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    issue_id: uuid.UUID,
    comment_id: uuid.UUID,
    body: CommentUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """コメントを更新（本人のみ）"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_issue_or_404(issue_id, production_id, org_id, db)
    comment = await _get_comment_or_404(comment_id, issue_id, db)

    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="自分のコメントのみ編集できます")

    comment.content = body.content
    await db.flush()

    await db.refresh(comment)
    return CommentResponse(
        id=comment.id,
        issue_id=comment.issue_id,
        user_id=comment.user_id,
        display_name=current_user.display_name,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    issue_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """コメントを削除（本人のみ）"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_issue_or_404(issue_id, production_id, org_id, db)
    comment = await _get_comment_or_404(comment_id, issue_id, db)

    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="自分のコメントのみ削除できます")

    await db.delete(comment)


# ---- ヘルパー ----

async def _get_issue_or_404(
    issue_id: uuid.UUID,
    production_id: uuid.UUID,
    org_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[Issue, Production]:
    result = await db.execute(
        select(Production).where(Production.id == production_id, Production.organization_id == org_id)
    )
    production = result.scalar_one_or_none()
    if production is None:
        raise HTTPException(status_code=404, detail="公演が見つかりません")

    result = await db.execute(
        select(Issue).where(Issue.id == issue_id, Issue.production_id == production_id)
    )
    issue = result.scalar_one_or_none()
    if issue is None:
        raise HTTPException(status_code=404, detail="課題が見つかりません")

    return issue, production


async def _get_comment_or_404(comment_id: uuid.UUID, issue_id: uuid.UUID, db: AsyncSession) -> Comment:
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.issue_id == issue_id)
    )
    comment = result.scalar_one_or_none()
    if comment is None:
        raise HTTPException(status_code=404, detail="コメントが見つかりません")
    return comment


async def _check_org_membership(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="この団体のメンバーではありません")

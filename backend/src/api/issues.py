import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import (
    Department,
    Issue,
    IssueAssignee,
    IssueLabel,
    OrganizationMembership,
    Production,
    StatusDefinition,
    User,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.issues import (
    IssueBatchStatusUpdate,
    IssueCreate,
    IssueDetailResponse,
    IssueListResponse,
    IssueUpdate,
)
from src.services.discord_webhook import (
    notify_issue_completed,
    notify_issue_created,
    notify_issue_updated,
)

router = APIRouter()


@router.get("/", response_model=list[IssueListResponse])
async def list_issues(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    status_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    issue_type: str | None = None,
    priority: str | None = None,
    phase_id: uuid.UUID | None = None,
    milestone_id: uuid.UUID | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公演の課題一覧を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    await _get_production_or_404(production_id, org_id, db)

    stmt = (
        select(Issue)
        .where(Issue.production_id == production_id)
        .options(
            selectinload(Issue.assignees).selectinload(IssueAssignee.user),
            selectinload(Issue.issue_labels).selectinload(IssueLabel.label),
        )
        .order_by(Issue.created_at.desc())
    )

    if status_id is not None:
        stmt = stmt.where(Issue.status_id == status_id)
    if department_id is not None:
        stmt = stmt.where(Issue.department_id == department_id)
    if issue_type is not None:
        stmt = stmt.where(Issue.issue_type == issue_type)
    if priority is not None:
        stmt = stmt.where(Issue.priority == priority)
    if phase_id is not None:
        stmt = stmt.where(Issue.phase_id == phase_id)
    if milestone_id is not None:
        stmt = stmt.where(Issue.milestone_id == milestone_id)
    if assignee_id is not None:
        stmt = stmt.join(IssueAssignee).where(IssueAssignee.user_id == assignee_id)

    result = await db.execute(stmt)
    issues = result.scalars().unique().all()

    return [_issue_to_list_response(issue) for issue in issues]


@router.patch("/batch-update-status", status_code=status.HTTP_204_NO_CONTENT)
async def batch_update_status(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    body: IssueBatchStatusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """複数課題のステータスを一括更新（ドラッグ＆ドロップ用）"""
    await _check_org_membership(org_id, current_user.id, db)
    production = await _get_production_or_404(production_id, org_id, db)

    changes: list[tuple[Issue, uuid.UUID | None]] = []
    for item in body.items:
        issue = await _get_issue_or_404(item.issue_id, production_id, db)
        old_status_id = issue.status_id
        issue.status_id = item.status_id
        changes.append((issue, old_status_id))

    await db.flush()

    # Webhook notifications for completion
    for issue, old_status_id in changes:
        if issue.status_id and issue.status_id != old_status_id:
            new_status = await _get_status_definition(issue.status_id, db)
            if new_status and new_status.is_closed:
                notify_issue_completed(
                    production.discord_webhook_url,
                    title=issue.title,
                    status_name=new_status.name,
                    completer_name=current_user.display_name,
                )


@router.post("/", response_model=IssueDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    body: IssueCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """課題を作成"""
    await _check_org_membership(org_id, current_user.id, db)
    production = await _get_production_or_404(production_id, org_id, db)

    issue = Issue(
        production_id=production_id,
        title=body.title,
        description=body.description,
        issue_type=body.issue_type,
        priority=body.priority,
        status_id=body.status_id,
        department_id=body.department_id,
        due_date=body.due_date,
        start_date=body.start_date,
        parent_issue_id=body.parent_issue_id,
        phase_id=body.phase_id,
        milestone_id=body.milestone_id,
        created_by=current_user.id,
    )
    db.add(issue)
    await db.flush()

    for user_id in body.assignee_ids:
        db.add(IssueAssignee(issue_id=issue.id, user_id=user_id))

    for label_id in body.label_ids:
        db.add(IssueLabel(issue_id=issue.id, label_id=label_id))

    await db.flush()

    # Webhook notification
    dept_name = await _resolve_department_name(body.department_id, db)
    assignee_names = await _resolve_user_names(body.assignee_ids, db)
    notify_issue_created(
        production.discord_webhook_url,
        title=body.title,
        issue_type=body.issue_type,
        priority=body.priority,
        department_name=dept_name,
        assignee_names=assignee_names,
        creator_name=current_user.display_name,
    )

    return await _load_issue_detail(issue.id, production_id, db)


@router.get("/{issue_id}", response_model=IssueDetailResponse)
async def get_issue(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    issue_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """課題の詳細を取得"""
    await _check_org_membership(org_id, current_user.id, db)
    return await _load_issue_detail(issue_id, production_id, db)


@router.patch("/{issue_id}", response_model=IssueDetailResponse)
async def update_issue(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    issue_id: uuid.UUID,
    body: IssueUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """課題を更新"""
    await _check_org_membership(org_id, current_user.id, db)
    production = await _get_production_or_404(production_id, org_id, db)
    issue = await _get_issue_or_404(issue_id, production_id, db)

    update_data = body.model_dump(exclude_unset=True)

    # Snapshot old values for change detection
    old_status_id = issue.status_id
    old_priority = issue.priority

    assignee_ids = update_data.pop("assignee_ids", None)
    label_ids = update_data.pop("label_ids", None)

    for key, value in update_data.items():
        setattr(issue, key, value)

    if assignee_ids is not None:
        await db.execute(delete(IssueAssignee).where(IssueAssignee.issue_id == issue.id))
        for user_id in assignee_ids:
            db.add(IssueAssignee(issue_id=issue.id, user_id=user_id))

    if label_ids is not None:
        await db.execute(delete(IssueLabel).where(IssueLabel.issue_id == issue.id))
        for label_id in label_ids:
            db.add(IssueLabel(issue_id=issue.id, label_id=label_id))

    await db.flush()

    # Webhook notification
    await _notify_issue_changes(
        production=production,
        issue=issue,
        old_status_id=old_status_id,
        old_priority=old_priority,
        updater_name=current_user.display_name,
        db=db,
    )

    return await _load_issue_detail(issue.id, production_id, db)


@router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    issue_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """課題を削除"""
    await _check_org_membership(org_id, current_user.id, db)
    issue = await _get_issue_or_404(issue_id, production_id, db)
    await db.delete(issue)


# ---- ヘルパー ----

def _issue_to_list_response(issue: Issue) -> IssueListResponse:
    return IssueListResponse(
        id=issue.id,
        title=issue.title,
        issue_type=issue.issue_type,
        priority=issue.priority,
        status_id=issue.status_id,
        department_id=issue.department_id,
        due_date=issue.due_date,
        start_date=issue.start_date,
        assignees=[
            {"user_id": a.user_id, "display_name": a.user.display_name}
            for a in issue.assignees
        ],
        labels=[
            {"label_id": il.label_id, "name": il.label.name, "color": il.label.color}
            for il in issue.issue_labels
        ],
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )


async def _load_issue_detail(issue_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession) -> IssueDetailResponse:
    stmt = (
        select(Issue)
        .where(Issue.id == issue_id, Issue.production_id == production_id)
        .options(
            selectinload(Issue.assignees).selectinload(IssueAssignee.user),
            selectinload(Issue.issue_labels).selectinload(IssueLabel.label),
        )
    )
    result = await db.execute(stmt)
    issue = result.scalar_one_or_none()
    if issue is None:
        raise HTTPException(status_code=404, detail="課題が見つかりません")

    resp = _issue_to_list_response(issue)
    return IssueDetailResponse(
        **resp.model_dump(),
        description=issue.description,
        parent_issue_id=issue.parent_issue_id,
        phase_id=issue.phase_id,
        milestone_id=issue.milestone_id,
        created_by=issue.created_by,
    )


async def _get_production_or_404(production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Production:
    result = await db.execute(
        select(Production).where(Production.id == production_id, Production.organization_id == org_id)
    )
    production = result.scalar_one_or_none()
    if production is None:
        raise HTTPException(status_code=404, detail="公演が見つかりません")
    return production


async def _get_issue_or_404(issue_id: uuid.UUID, production_id: uuid.UUID, db: AsyncSession) -> Issue:
    result = await db.execute(
        select(Issue).where(Issue.id == issue_id, Issue.production_id == production_id)
    )
    issue = result.scalar_one_or_none()
    if issue is None:
        raise HTTPException(status_code=404, detail="課題が見つかりません")
    return issue


async def _check_org_membership(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="この団体のメンバーではありません")


async def _get_status_definition(status_id: uuid.UUID, db: AsyncSession) -> StatusDefinition | None:
    result = await db.execute(select(StatusDefinition).where(StatusDefinition.id == status_id))
    return result.scalar_one_or_none()


async def _resolve_department_name(department_id: uuid.UUID | None, db: AsyncSession) -> str | None:
    if department_id is None:
        return None
    result = await db.execute(select(Department.name).where(Department.id == department_id))
    row = result.scalar_one_or_none()
    return row


async def _resolve_user_names(user_ids: list[uuid.UUID], db: AsyncSession) -> list[str]:
    if not user_ids:
        return []
    result = await db.execute(select(User.display_name).where(User.id.in_(user_ids)))
    return list(result.scalars().all())


PRIORITY_LABELS = {"high": "高", "medium": "中", "low": "低"}


async def _notify_issue_changes(
    *,
    production: Production,
    issue: Issue,
    old_status_id: uuid.UUID | None,
    old_priority: str,
    updater_name: str,
    db: AsyncSession,
) -> None:
    """Detect changes and send appropriate webhook notification."""
    # Check for completion (status changed to is_closed=True)
    if issue.status_id and issue.status_id != old_status_id:
        new_status = await _get_status_definition(issue.status_id, db)
        if new_status and new_status.is_closed:
            notify_issue_completed(
                production.discord_webhook_url,
                title=issue.title,
                status_name=new_status.name,
                completer_name=updater_name,
            )
            return

    # Build change dict for general update notification
    changes: dict[str, tuple[str, str]] = {}

    if issue.status_id != old_status_id:
        old_name = "なし"
        new_name = "なし"
        if old_status_id:
            old_sd = await _get_status_definition(old_status_id, db)
            if old_sd:
                old_name = old_sd.name
        if issue.status_id:
            new_sd = await _get_status_definition(issue.status_id, db)
            if new_sd:
                new_name = new_sd.name
        changes["ステータス"] = (old_name, new_name)

    if issue.priority != old_priority:
        changes["優先度"] = (
            PRIORITY_LABELS.get(old_priority, old_priority),
            PRIORITY_LABELS.get(issue.priority, issue.priority),
        )

    notify_issue_updated(
        production.discord_webhook_url,
        title=issue.title,
        changes=changes,
        updater_name=updater_name,
    )

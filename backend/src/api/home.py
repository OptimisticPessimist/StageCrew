from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import Issue, IssueAssignee, OrganizationMembership, Production
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.home import HomeDeadlineWarnings, HomeIssue, HomeResponse

router = APIRouter()

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@router.get("/", response_model=HomeResponse)
async def get_home(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ホーム画面データ（全公演横断マイタスク + 期限警告）"""
    # 自分にアサインされた全Issueを取得（所属組織の課題のみ）
    # Issue -> Production -> Organization <- OrganizationMembership で所属チェック
    stmt = (
        select(Issue)
        .join(IssueAssignee, IssueAssignee.issue_id == Issue.id)
        .join(Production, Production.id == Issue.production_id)
        .join(
            OrganizationMembership,
            (OrganizationMembership.organization_id == Production.organization_id)
            & (OrganizationMembership.user_id == current_user.id),
        )
        .where(IssueAssignee.user_id == current_user.id)
        .options(
            selectinload(Issue.status),
            selectinload(Issue.department),
            selectinload(Issue.production).selectinload(Production.organization),
        )
    )
    result = await db.execute(stmt)
    issues = list(result.scalars().unique().all())

    now = datetime.now(UTC)
    near_deadline_threshold = now + timedelta(days=3)

    my_tasks: list[HomeIssue] = []
    overdue: list[HomeIssue] = []
    near_deadline: list[HomeIssue] = []

    for issue in issues:
        is_closed = issue.status is not None and issue.status.is_closed

        if is_closed:
            continue

        home_issue = _to_home_issue(issue)
        my_tasks.append(home_issue)

        if issue.due_date is not None:
            if issue.due_date < now:
                overdue.append(home_issue)
            elif issue.due_date <= near_deadline_threshold:
                near_deadline.append(home_issue)

    # ソート
    _max_dt = datetime.max.replace(tzinfo=UTC)
    _min_dt = datetime.min.replace(tzinfo=UTC)
    my_tasks.sort(key=lambda t: (t.due_date or _max_dt, PRIORITY_ORDER.get(t.priority, 9)))
    overdue.sort(key=lambda t: t.due_date or _min_dt)
    near_deadline.sort(key=lambda t: t.due_date or _max_dt)

    return HomeResponse(
        my_tasks=my_tasks,
        deadline_warnings=HomeDeadlineWarnings(
            overdue=overdue,
            near_deadline=near_deadline,
        ),
    )


def _to_home_issue(issue: Issue) -> HomeIssue:
    return HomeIssue(
        id=issue.id,
        title=issue.title,
        priority=issue.priority,
        issue_type=issue.issue_type,
        status_id=issue.status_id,
        status_name=issue.status.name if issue.status else None,
        status_color=issue.status.color if issue.status else None,
        department_id=issue.department_id,
        department_name=issue.department.name if issue.department else None,
        due_date=issue.due_date,
        production_id=issue.production_id,
        production_name=issue.production.name,
        organization_id=issue.production.organization_id,
        organization_name=issue.production.organization.name,
    )

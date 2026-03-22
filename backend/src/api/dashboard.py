import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.base import get_db
from src.db.models import (
    Department,
    Issue,
    OrganizationMembership,
    Production,
)
from src.dependencies.auth import CurrentUser, get_current_user
from src.schemas.dashboard import (
    DashboardIssue,
    DashboardResponse,
    DeadlineWarnings,
    DepartmentProgress,
    ProgressSummary,
    StatusCount,
)

router = APIRouter()

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    org_id: uuid.UUID,
    production_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ダッシュボードデータを取得"""
    await _check_org_membership(org_id, current_user.id, db)
    production = await _get_production_or_404(production_id, org_id, db)

    # 全Issue + status/department をeager loadで取得
    stmt = (
        select(Issue)
        .where(Issue.production_id == production_id)
        .options(
            selectinload(Issue.status),
            selectinload(Issue.department),
            selectinload(Issue.assignees),
        )
    )
    result = await db.execute(stmt)
    issues = list(result.scalars().unique().all())

    # 部門一覧を取得（issue が 0 件の部門も表示するため）
    dept_result = await db.execute(
        select(Department).where(Department.production_id == production_id).order_by(Department.sort_order)
    )
    all_departments = list(dept_result.scalars().all())

    now = datetime.now(UTC)
    near_deadline_threshold = now + timedelta(days=3)

    # --- 集計 ---
    total = len(issues)
    completed = 0
    dept_stats: dict[uuid.UUID | None, dict] = defaultdict(lambda: {"total": 0, "completed": 0})
    status_stats: dict[uuid.UUID | None, dict] = defaultdict(lambda: {"count": 0, "name": "", "color": None})
    my_tasks: list[DashboardIssue] = []
    overdue: list[DashboardIssue] = []
    near_deadline: list[DashboardIssue] = []

    for issue in issues:
        is_closed = issue.status is not None and issue.status.is_closed

        if is_closed:
            completed += 1

        # 部門別
        dept_stats[issue.department_id]["total"] += 1
        if is_closed:
            dept_stats[issue.department_id]["completed"] += 1

        # ステータス別
        sid = issue.status_id
        status_stats[sid]["count"] += 1
        if issue.status:
            status_stats[sid]["name"] = issue.status.name
            status_stats[sid]["color"] = issue.status.color
        else:
            status_stats[sid]["name"] = "未設定"

        # 担当タスク（自分にアサインされている & 未完了）
        assigned_to_me = any(a.user_id == current_user.id for a in issue.assignees)
        if assigned_to_me and not is_closed:
            my_tasks.append(_to_dashboard_issue(issue))

        # 期限警告（未完了のみ）
        if not is_closed and issue.due_date is not None:
            if issue.due_date < now:
                overdue.append(_to_dashboard_issue(issue))
            elif issue.due_date <= near_deadline_threshold:
                near_deadline.append(_to_dashboard_issue(issue))

    # ソート: my_tasks → priority(high>medium>low), due_date ASC (nulls last)
    _max_dt = datetime.max.replace(tzinfo=UTC)
    _min_dt = datetime.min.replace(tzinfo=UTC)
    my_tasks.sort(key=lambda t: (PRIORITY_ORDER.get(t.priority, 9), t.due_date or _max_dt))
    overdue.sort(key=lambda t: t.due_date or _min_dt)
    near_deadline.sort(key=lambda t: t.due_date or _max_dt)

    # 部門別進捗を組み立て
    by_department = []
    for dept in all_departments:
        stats = dept_stats.get(dept.id, {"total": 0, "completed": 0})
        by_department.append(
            DepartmentProgress(
                department_id=dept.id,
                department_name=dept.name,
                department_color=dept.color,
                total=stats["total"],
                completed=stats["completed"],
            )
        )
    # 部門未設定の課題がある場合
    if None in dept_stats and dept_stats[None]["total"] > 0:
        by_department.append(
            DepartmentProgress(
                department_id=uuid.UUID(int=0),
                department_name="未分類",
                department_color=None,
                total=dept_stats[None]["total"],
                completed=dept_stats[None]["completed"],
            )
        )

    # ステータス別分布
    by_status = [
        StatusCount(
            status_id=sid,
            status_name=info["name"],
            status_color=info["color"],
            count=info["count"],
        )
        for sid, info in status_stats.items()
    ]
    by_status.sort(key=lambda s: (-s.count,))

    # 日付計算
    days_to_opening = None
    days_to_closing = None
    if production.opening_date:
        days_to_opening = (production.opening_date.date() - now.date()).days
    if production.closing_date:
        days_to_closing = (production.closing_date.date() - now.date()).days

    return DashboardResponse(
        progress=ProgressSummary(
            total_issues=total,
            completed_issues=completed,
            completion_percentage=round(completed / total * 100, 1) if total > 0 else 0.0,
            current_phase=production.current_phase,
            days_to_opening=days_to_opening,
            days_to_closing=days_to_closing,
            by_department=by_department,
            by_status=by_status,
        ),
        my_tasks=my_tasks,
        deadline_warnings=DeadlineWarnings(
            overdue=overdue,
            near_deadline=near_deadline,
        ),
    )


def _to_dashboard_issue(issue: Issue) -> DashboardIssue:
    return DashboardIssue(
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
    )


async def _get_production_or_404(production_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Production:
    result = await db.execute(
        select(Production).where(Production.id == production_id, Production.organization_id == org_id)
    )
    production = result.scalar_one_or_none()
    if production is None:
        raise HTTPException(status_code=404, detail="公演が見つかりません")
    return production


async def _check_org_membership(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="この団体のメンバーではありません")

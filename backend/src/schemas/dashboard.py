import uuid
from datetime import datetime

from pydantic import BaseModel


class DashboardIssue(BaseModel):
    id: uuid.UUID
    title: str
    priority: str
    issue_type: str
    status_id: uuid.UUID | None
    status_name: str | None
    status_color: str | None
    department_id: uuid.UUID | None
    department_name: str | None
    due_date: datetime | None


class DepartmentProgress(BaseModel):
    department_id: uuid.UUID
    department_name: str
    department_color: str | None
    total: int
    completed: int


class StatusCount(BaseModel):
    status_id: uuid.UUID | None
    status_name: str
    status_color: str | None
    count: int


class ProgressSummary(BaseModel):
    total_issues: int
    completed_issues: int
    completion_percentage: float
    current_phase: str | None
    days_to_opening: int | None
    days_to_closing: int | None
    by_department: list[DepartmentProgress]
    by_status: list[StatusCount]


class DeadlineWarnings(BaseModel):
    overdue: list[DashboardIssue]
    near_deadline: list[DashboardIssue]


class DashboardResponse(BaseModel):
    progress: ProgressSummary
    my_tasks: list[DashboardIssue]
    deadline_warnings: DeadlineWarnings

import uuid
from datetime import datetime

from pydantic import BaseModel


class HomeIssue(BaseModel):
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
    production_id: uuid.UUID
    production_name: str
    organization_id: uuid.UUID
    organization_name: str


class HomeDeadlineWarnings(BaseModel):
    overdue: list[HomeIssue]
    near_deadline: list[HomeIssue]


class HomeResponse(BaseModel):
    my_tasks: list[HomeIssue]
    deadline_warnings: HomeDeadlineWarnings

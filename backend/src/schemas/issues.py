import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---- Request ----
class IssueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    issue_type: str = Field("task", pattern=r"^(task|bug|request|notice)$")
    priority: str = Field("medium", pattern=r"^(high|medium|low)$")
    status_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    due_date: datetime | None = None
    start_date: datetime | None = None
    parent_issue_id: uuid.UUID | None = None
    phase_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    assignee_ids: list[uuid.UUID] = []
    label_ids: list[uuid.UUID] = []


class IssueUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=512)
    description: str | None = None
    issue_type: str | None = Field(None, pattern=r"^(task|bug|request|notice)$")
    priority: str | None = Field(None, pattern=r"^(high|medium|low)$")
    status_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    due_date: datetime | None = None
    start_date: datetime | None = None
    parent_issue_id: uuid.UUID | None = None
    phase_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    assignee_ids: list[uuid.UUID] | None = None
    label_ids: list[uuid.UUID] | None = None


class BatchStatusUpdateItem(BaseModel):
    issue_id: uuid.UUID
    status_id: uuid.UUID | None = None


class IssueBatchStatusUpdate(BaseModel):
    items: list[BatchStatusUpdateItem] = Field(..., min_length=1)


# ---- Response ----
class IssueAssigneeResponse(BaseModel):
    user_id: uuid.UUID
    display_name: str

    model_config = {"from_attributes": True}


class IssueLabelResponse(BaseModel):
    label_id: uuid.UUID
    name: str
    color: str | None

    model_config = {"from_attributes": True}


class IssueListResponse(BaseModel):
    id: uuid.UUID
    title: str
    issue_type: str
    priority: str
    status_id: uuid.UUID | None
    department_id: uuid.UUID | None
    due_date: datetime | None
    assignees: list[IssueAssigneeResponse] = []
    labels: list[IssueLabelResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IssueDetailResponse(IssueListResponse):
    description: str | None
    start_date: datetime | None
    parent_issue_id: uuid.UUID | None
    phase_id: uuid.UUID | None
    milestone_id: uuid.UUID | None
    created_by: uuid.UUID

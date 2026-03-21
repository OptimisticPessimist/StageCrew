import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---- Staff Role ----
class StaffRoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    sort_order: int = 0


class StaffRoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    sort_order: int | None = None


class StaffRoleResponse(BaseModel):
    id: uuid.UUID
    department_id: uuid.UUID
    name: str
    sort_order: int

    model_config = {"from_attributes": True}


# ---- Department ----
class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    color: str | None = Field(None, max_length=7)
    sort_order: int = 0
    staff_roles: list[StaffRoleCreate] | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    color: str | None = Field(None, max_length=7)
    sort_order: int | None = None


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    production_id: uuid.UUID
    name: str
    color: str | None
    sort_order: int
    created_at: datetime
    staff_roles: list[StaffRoleResponse] = []

    model_config = {"from_attributes": True}

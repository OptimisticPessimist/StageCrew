import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---- Organization Member ----
class OrgMemberAdd(BaseModel):
    user_id: uuid.UUID
    org_role: str = Field("member", pattern=r"^(admin|member)$")


class OrgMemberUpdate(BaseModel):
    org_role: str = Field(..., pattern=r"^(owner|admin|member)$")


# ---- Production Member ----
class ProductionMemberAdd(BaseModel):
    user_id: uuid.UUID
    production_role: str = Field("member", pattern=r"^(manager|member)$")
    is_cast: bool = False


class ProductionMemberUpdate(BaseModel):
    production_role: str | None = Field(None, pattern=r"^(manager|member)$")
    is_cast: bool | None = None
    cast_capabilities: list[str] | None = None


class DeptMembershipBrief(BaseModel):
    id: uuid.UUID
    department_id: uuid.UUID
    department_name: str
    staff_role_id: uuid.UUID | None
    staff_role_name: str | None
    capabilities: list[str]

    model_config = {"from_attributes": True}


class ProductionMemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    production_role: str
    is_cast: bool
    cast_capabilities: list[str] | None
    created_at: datetime
    department_memberships: list[DeptMembershipBrief] = []

    model_config = {"from_attributes": True}


# ---- Department Member ----
class DeptMemberAdd(BaseModel):
    production_membership_id: uuid.UUID
    staff_role_id: uuid.UUID | None = None
    capabilities: list[str] | None = None


class DeptMemberUpdate(BaseModel):
    staff_role_id: uuid.UUID | None = None
    capabilities: list[str] | None = None


class DeptMemberResponse(BaseModel):
    id: uuid.UUID
    production_membership_id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    department_id: uuid.UUID
    staff_role_id: uuid.UUID | None
    staff_role_name: str | None
    capabilities: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}

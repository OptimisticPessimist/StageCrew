import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---- Request ----
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    cast_default_capabilities: list[str] | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None
    cast_default_capabilities: list[str] | None = None


# ---- Response ----
class OrganizationMemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    org_role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    cast_default_capabilities: list[str]
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

    model_config = {"from_attributes": True}


class OrganizationDetailResponse(OrganizationResponse):
    members: list[OrganizationMemberResponse] = []

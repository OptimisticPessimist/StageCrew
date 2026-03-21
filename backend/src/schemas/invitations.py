import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---- Request ----
class InvitationCreate(BaseModel):
    email: str | None = None
    org_role: str = Field("member", pattern=r"^(admin|member)$")


# ---- Response ----
class InvitationResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    email: str | None
    token: str
    org_role: str
    status: str
    expires_at: datetime
    created_at: datetime
    invited_by_name: str

    model_config = {"from_attributes": True}


class InvitationAcceptResponse(BaseModel):
    message: str
    organization_id: uuid.UUID
    membership_id: uuid.UUID

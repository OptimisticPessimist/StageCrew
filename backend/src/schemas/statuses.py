import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---- Request ----
class StatusCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: str | None = Field(None, max_length=7)
    sort_order: int = 0
    is_closed: bool = False
    department_id: uuid.UUID | None = None


class StatusUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    color: str | None = Field(None, max_length=7)
    sort_order: int | None = None
    is_closed: bool | None = None


# ---- Response ----
class StatusResponse(BaseModel):
    id: uuid.UUID
    production_id: uuid.UUID
    department_id: uuid.UUID | None
    name: str
    color: str | None
    sort_order: int
    is_closed: bool

    model_config = {"from_attributes": True}

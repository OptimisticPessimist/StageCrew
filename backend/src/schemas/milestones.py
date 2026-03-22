import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---- Request ----
class MilestoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    date: datetime | None = None
    color: str | None = Field(None, max_length=7)


class MilestoneUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256)
    date: datetime | None = None
    color: str | None = Field(None, max_length=7)


# ---- Response ----
class MilestoneResponse(BaseModel):
    id: uuid.UUID
    production_id: uuid.UUID
    name: str
    date: datetime | None
    color: str | None

    model_config = {"from_attributes": True}

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---- Request ----
class PhaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    sort_order: int = 0
    start_date: datetime | None = None
    end_date: datetime | None = None


class PhaseUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    sort_order: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


# ---- Response ----
class PhaseResponse(BaseModel):
    id: uuid.UUID
    production_id: uuid.UUID
    name: str
    sort_order: int
    start_date: datetime | None
    end_date: datetime | None

    model_config = {"from_attributes": True}

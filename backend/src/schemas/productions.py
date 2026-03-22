import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---- Request ----
class ProductionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    production_type: str = Field("real", pattern=r"^(real|vr|hybrid)$")
    opening_date: datetime | None = None
    closing_date: datetime | None = None
    discord_webhook_url: str | None = None


class ProductionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None
    production_type: str | None = Field(None, pattern=r"^(real|vr|hybrid)$")
    opening_date: datetime | None = None
    closing_date: datetime | None = None
    current_phase: str | None = None
    discord_webhook_url: str | None = None


# ---- Response ----
class ProductionResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    production_type: str
    opening_date: datetime | None
    closing_date: datetime | None
    current_phase: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductionWebhookResponse(BaseModel):
    discord_webhook_url: str | None

    model_config = {"from_attributes": True}


class ProductionSummaryResponse(BaseModel):
    id: uuid.UUID
    name: str
    opening_date: datetime | None
    closing_date: datetime | None
    current_phase: str | None

    model_config = {"from_attributes": True}


class ProductionListResponse(BaseModel):
    id: uuid.UUID
    name: str
    production_type: str
    opening_date: datetime | None
    closing_date: datetime | None
    current_phase: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

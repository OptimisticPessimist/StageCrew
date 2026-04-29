import uuid
from datetime import date as date_type
from datetime import datetime
from datetime import time as time_type
from typing import Any

from pydantic import BaseModel, Field, field_validator

AVAILABILITY_VALUES = {"available", "unavailable", "tentative"}


class AvailabilityCreate(BaseModel):
    date: date_type
    availability: str = "available"
    start_time: time_type | None = None
    end_time: time_type | None = None
    note: str | None = None


class AvailabilityUpdate(BaseModel):
    availability: str | None = None
    start_time: time_type | None = None
    end_time: time_type | None = None
    note: str | None = None

    @field_validator("availability", mode="before")
    @classmethod
    def _reject_null_availability(cls, v: Any) -> Any:
        # availability カラムはNOT NULL。未指定は可だが明示的 null は拒否。
        if v is None:
            raise ValueError("availability に null は指定できません（省略してください）")
        return v


class AvailabilityBulkUpsert(BaseModel):
    items: list[AvailabilityCreate] = Field(..., min_length=1)


class AvailabilityResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    production_id: uuid.UUID
    date: date_type
    availability: str
    start_time: time_type | None
    end_time: time_type | None
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

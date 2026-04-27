import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

EVENT_TYPES = {"rehearsal", "performance", "meeting", "other"}
ATTENDANCE_TYPES = {"required", "optional"}
RSVP_STATUSES = {"pending", "accepted", "declined", "tentative"}
ACTUAL_ATTENDANCES = {"present", "absent", "late"}


def _validate_http_url(value: str | None) -> str | None:
    """location_url は http/https スキームのみ受け付ける。"""
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    lower = v.lower()
    if not (lower.startswith("http://") or lower.startswith("https://")):
        raise ValueError("location_url は http/https スキームのみ許可されます")
    return v


def _reject_explicit_null(value: Any) -> Any:
    """PATCH において「未指定は可・明示的な null は不可」を強制する。"""
    if value is None:
        raise ValueError("この項目に null は指定できません（省略してください）")
    return value


# ---- Request ----
class EventCreate(BaseModel):
    event_type: str = Field("rehearsal")
    title: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    is_all_day: bool = False
    location_name: str | None = Field(None, max_length=256)
    location_url: str | None = Field(None, max_length=512)
    scene_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("location_url")
    @classmethod
    def _check_location_url(cls, v: str | None) -> str | None:
        return _validate_http_url(v)


class EventUpdate(BaseModel):
    # NOT NULL な列は "未指定は可・明示的 null は不可" に統一
    event_type: str | None = None
    title: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    is_all_day: bool | None = None
    location_name: str | None = Field(None, max_length=256)
    location_url: str | None = Field(None, max_length=512)
    scene_ids: list[uuid.UUID] | None = None

    @field_validator("event_type", "title", "start_at", "is_all_day", mode="before")
    @classmethod
    def _reject_null_for_required(cls, v: Any) -> Any:
        return _reject_explicit_null(v)

    @field_validator("location_url")
    @classmethod
    def _check_location_url(cls, v: str | None) -> str | None:
        return _validate_http_url(v)


class AttendeeAdd(BaseModel):
    user_ids: list[uuid.UUID] = Field(..., min_length=1)
    attendance_type: str = "required"


class AttendeeUpdate(BaseModel):
    # attendance_type / rsvp_status は NOT NULL。actual_attendance はクリア許容のため null 可。
    attendance_type: str | None = None
    rsvp_status: str | None = None
    actual_attendance: str | None = None

    @field_validator("attendance_type", "rsvp_status", mode="before")
    @classmethod
    def _reject_null_for_required(cls, v: Any) -> Any:
        return _reject_explicit_null(v)


# ---- Response ----
class AttendeeResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    attendance_type: str
    rsvp_status: str
    actual_attendance: str | None
    responded_at: datetime | None

    model_config = {"from_attributes": True}


class EventSceneResponse(BaseModel):
    scene_id: uuid.UUID
    heading: str
    act_number: int
    scene_number: int


class EventResponse(BaseModel):
    id: uuid.UUID
    production_id: uuid.UUID
    event_type: str
    title: str
    description: str | None
    start_at: datetime
    end_at: datetime | None
    is_all_day: bool
    location_name: str | None
    location_url: str | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventDetailResponse(EventResponse):
    attendees: list[AttendeeResponse]
    scenes: list[EventSceneResponse]

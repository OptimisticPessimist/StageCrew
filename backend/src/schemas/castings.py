import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


def _reject_null_fields(non_nullable: frozenset[str], data: Any) -> Any:
    """PATCH リクエストで NOT NULL フィールドに null が送られたら拒否する。"""
    if isinstance(data, dict):
        for key in non_nullable & data.keys():
            if data[key] is None:
                raise ValueError(f"'{key}' は null にできません")
    return data


_CASTING_NON_NULLABLE = frozenset({"sort_order"})


# ============================================================
# Nested response helpers
# ============================================================


class CastingCharacterResponse(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class CastingMemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str

    model_config = {"from_attributes": True}


class CastingMemberUserResponse(BaseModel):
    """production_membership.user から取得するユーザー情報。"""

    id: uuid.UUID
    display_name: str

    model_config = {"from_attributes": True}


class CastingMemberDetailResponse(BaseModel):
    """キャスティングレスポンスに含める production_membership 情報。"""

    id: uuid.UUID
    user: CastingMemberUserResponse

    model_config = {"from_attributes": True}


# ============================================================
# CRUD schemas
# ============================================================


class CastingCreate(BaseModel):
    character_id: uuid.UUID
    production_membership_id: uuid.UUID
    display_name: str | None = Field(None, max_length=128)
    memo: str | None = None
    sort_order: int = 0


class CastingUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=128)
    memo: str | None = None
    sort_order: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_null_non_nullable(cls, data: Any) -> Any:
        return _reject_null_fields(_CASTING_NON_NULLABLE, data)


class CastingResponse(BaseModel):
    id: uuid.UUID
    character_id: uuid.UUID
    production_membership_id: uuid.UUID
    display_name: str | None
    memo: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime
    character: CastingCharacterResponse
    production_membership: CastingMemberDetailResponse

    model_config = {"from_attributes": True}


# ============================================================
# CharacterResponse に埋め込むための軽量キャスティング情報
# ============================================================


class CastingSummaryResponse(BaseModel):
    """Character のネストレスポンスに含める軽量キャスティング情報。"""

    id: uuid.UUID
    production_membership_id: uuid.UUID
    display_name: str | None
    memo: str | None
    sort_order: int
    member_user_display_name: str | None = None

    model_config = {"from_attributes": True}

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AppearanceType(StrEnum):
    dialogue = "dialogue"  # セリフあり
    silent = "silent"  # セリフなし・舞台に登場
    off_stage = "off_stage"  # 声のみ・舞台外


# ============================================================
# Mapping CRUD schemas
# ============================================================


class SceneCharacterMappingCreate(BaseModel):
    scene_id: uuid.UUID
    character_id: uuid.UUID
    appearance_type: AppearanceType = Field(default=AppearanceType.silent)
    note: str | None = None


class SceneCharacterMappingUpdate(BaseModel):
    appearance_type: AppearanceType | None = None
    note: str | None = None


class SceneCharacterMappingResponse(BaseModel):
    id: uuid.UUID
    scene_id: uuid.UUID
    character_id: uuid.UUID
    appearance_type: str
    is_auto_generated: bool
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# Scene Chart matrix response
# ============================================================


class SceneChartCharacter(BaseModel):
    id: uuid.UUID
    name: str
    sort_order: int

    model_config = {"from_attributes": True}


class SceneChartScene(BaseModel):
    id: uuid.UUID
    act_number: int
    scene_number: int
    heading: str
    sort_order: int

    model_config = {"from_attributes": True}


class SceneChartCell(BaseModel):
    mapping_id: uuid.UUID
    appearance_type: str
    is_auto_generated: bool
    note: str | None


class SceneChartResponse(BaseModel):
    characters: list[SceneChartCharacter]
    scenes: list[SceneChartScene]
    matrix: dict[str, dict[str, SceneChartCell | None]]


class SceneChartGenerateRequest(BaseModel):
    preserve_manual: bool = True

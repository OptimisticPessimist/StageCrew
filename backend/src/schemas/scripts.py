import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ============================================================
# Line (セリフ)
# ============================================================
class LineCreate(BaseModel):
    character_id: uuid.UUID | None = None
    content: str = Field(..., min_length=1)
    sort_order: int = 0


class LineUpdate(BaseModel):
    character_id: uuid.UUID | None = None
    content: str | None = Field(None, min_length=1)
    sort_order: int | None = None


class LineResponse(BaseModel):
    id: uuid.UUID
    scene_id: uuid.UUID
    character_id: uuid.UUID | None
    content: str
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# Scene (シーン)
# ============================================================
class SceneCreate(BaseModel):
    act_number: int = 1
    scene_number: int = 1
    heading: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    sort_order: int = 0


class SceneUpdate(BaseModel):
    act_number: int | None = None
    scene_number: int | None = None
    heading: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None
    sort_order: int | None = None


class SceneResponse(BaseModel):
    id: uuid.UUID
    script_id: uuid.UUID
    act_number: int
    scene_number: int
    heading: str
    description: str | None
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SceneDetailResponse(SceneResponse):
    lines: list[LineResponse] = []


# ============================================================
# Character (登場人物)
# ============================================================
class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    sort_order: int = 0


class CharacterUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    sort_order: int | None = None


class CharacterResponse(BaseModel):
    id: uuid.UUID
    script_id: uuid.UUID
    name: str
    description: str | None
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# Script (脚本)
# ============================================================
class ScriptCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    content: str | None = None
    author: str | None = Field(None, max_length=256)
    draft_date: datetime | None = None
    revision: int = 1
    revision_text: str | None = None
    copyright: str | None = Field(None, max_length=512)
    contact: str | None = Field(None, max_length=512)
    notes: str | None = None
    pdf_orientation: str = Field("landscape", pattern=r"^(landscape|portrait)$")
    pdf_writing_direction: str = Field("vertical", pattern=r"^(vertical|horizontal)$")
    is_public: bool = False
    public_terms: str | None = None
    public_contact: str | None = Field(None, max_length=512)


class ScriptUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=256)
    content: str | None = None
    author: str | None = Field(None, max_length=256)
    draft_date: datetime | None = None
    revision: int | None = None
    revision_text: str | None = None
    copyright: str | None = Field(None, max_length=512)
    contact: str | None = Field(None, max_length=512)
    notes: str | None = None
    pdf_orientation: str | None = Field(None, pattern=r"^(landscape|portrait)$")
    pdf_writing_direction: str | None = Field(None, pattern=r"^(vertical|horizontal)$")
    is_public: bool | None = None
    public_terms: str | None = None
    public_contact: str | None = Field(None, max_length=512)


class ScriptUploaderResponse(BaseModel):
    id: uuid.UUID
    display_name: str

    model_config = {"from_attributes": True}


class ScriptListResponse(BaseModel):
    id: uuid.UUID
    title: str
    author: str | None
    revision: int
    is_public: bool
    uploaded_by: uuid.UUID
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScriptDetailResponse(ScriptListResponse):
    content: str | None
    draft_date: datetime | None
    revision_text: str | None
    copyright: str | None
    contact: str | None
    notes: str | None
    pdf_orientation: str
    pdf_writing_direction: str
    public_terms: str | None
    public_contact: str | None
    uploader: ScriptUploaderResponse
    scenes: list[SceneDetailResponse] = []
    characters: list[CharacterResponse] = []

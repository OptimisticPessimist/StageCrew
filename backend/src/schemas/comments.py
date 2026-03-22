import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---- Request ----
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


# ---- Response ----
class CommentResponse(BaseModel):
    id: uuid.UUID
    issue_id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

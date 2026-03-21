"""認証dependency。OAuth実装前は仮ユーザーを返す開発用スタブ。"""

import uuid
from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from src.db.models import User


@dataclass
class CurrentUser:
    id: uuid.UUID
    display_name: str


# 開発用の固定ユーザーID
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_current_user(db: AsyncSession = Depends(get_db)) -> CurrentUser:
    """開発用: DBに仮ユーザーがなければ作成して返す。OAuth実装時に差し替える。"""
    result = await db.execute(select(User).where(User.id == DEV_USER_ID))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(id=DEV_USER_ID, display_name="開発ユーザー")
        db.add(user)
        await db.flush()
    return CurrentUser(id=user.id, display_name=user.display_name)

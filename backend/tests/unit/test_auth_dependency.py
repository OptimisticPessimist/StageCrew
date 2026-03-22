"""認証dependency (get_current_user) のユニットテスト。"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models import User
from src.dependencies.auth import DEV_USER_ID, CurrentUser, get_current_user


def _make_jwt(user_id: str, discord_id: str = "123") -> str:
    payload = {
        "sub": user_id,
        "discord_id": discord_id,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def test_valid_jwt_returns_current_user(db_session: AsyncSession, test_user: User):
    token = _make_jwt(str(test_user.id))
    credentials = MagicMock()
    credentials.credentials = token

    result = await get_current_user(credentials=credentials, db=db_session)
    assert isinstance(result, CurrentUser)
    assert result.id == test_user.id


async def test_invalid_jwt_raises_401(db_session: AsyncSession):
    credentials = MagicMock()
    credentials.credentials = "invalid-token"

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, db=db_session)
    assert exc_info.value.status_code == 401


async def test_jwt_user_not_in_db(db_session: AsyncSession):
    """JWTは有効だがDBにユーザーがいない場合。"""
    token = _make_jwt(str(uuid.uuid4()))
    credentials = MagicMock()
    credentials.credentials = token

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=credentials, db=db_session)
    assert exc_info.value.status_code == 401


async def test_no_token_debug_mode_creates_dev_user(db_session: AsyncSession):
    with patch.object(settings, "debug", True):
        result = await get_current_user(credentials=None, db=db_session)
    assert result.id == DEV_USER_ID
    assert result.display_name == "開発ユーザー"


async def test_no_token_debug_mode_existing_dev_user(db_session: AsyncSession):
    dev_user = User(id=DEV_USER_ID, display_name="開発ユーザー")
    db_session.add(dev_user)
    await db_session.flush()

    with patch.object(settings, "debug", True):
        result = await get_current_user(credentials=None, db=db_session)
    assert result.id == DEV_USER_ID


async def test_no_token_production_raises_401(db_session: AsyncSession):
    with patch.object(settings, "debug", False):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None, db=db_session)
    assert exc_info.value.status_code == 401

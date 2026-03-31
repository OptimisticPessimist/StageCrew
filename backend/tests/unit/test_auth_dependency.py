"""認証dependency (get_current_user) のユニットテスト。RS256 + JWKS対応版。"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models import User
from src.dependencies.auth import DEV_USER_ID, CurrentUser, get_current_user

# テスト用RSAキーペア
_test_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_test_public_key = _test_private_key.public_key()


def _mock_jwks_client():
    """JWKSクライアントのモックを返す。"""
    mock_signing_key = MagicMock()
    mock_signing_key.key = _test_public_key
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_signing_key
    return mock_client


def _make_supabase_jwt(auth_user_id: str, email: str = "test@example.com") -> str:
    """Supabase形式のテスト用JWT (RS256) を生成する。"""
    payload = {
        "sub": auth_user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "email": email,
        "user_metadata": {
            "provider_id": "discord_123",
            "full_name": "Test User",
            "avatar_url": "https://cdn.example.com/avatar.png",
        },
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    return pyjwt.encode(payload, _test_private_key, algorithm="RS256")


@patch("src.dependencies.auth._get_jwks_client", return_value=_mock_jwks_client())
async def test_valid_jwt_existing_user(mock_jwks, db_session: AsyncSession, test_user: User):
    """既存ユーザーのauth_idに一致するJWTで認証が成功すること。"""
    auth_id = uuid.uuid4()
    test_user.auth_id = auth_id
    await db_session.flush()

    token = _make_supabase_jwt(str(auth_id))
    credentials = MagicMock()
    credentials.credentials = token

    result = await get_current_user(credentials=credentials, db=db_session)
    assert isinstance(result, CurrentUser)
    assert result.id == test_user.id


@patch("src.dependencies.auth._get_jwks_client", return_value=_mock_jwks_client())
async def test_valid_jwt_auto_creates_user(mock_jwks, db_session: AsyncSession):
    """auth_idが未登録の場合、user_metadataから自動的にユーザーが作成されること。"""
    auth_id = uuid.uuid4()
    token = _make_supabase_jwt(str(auth_id))
    credentials = MagicMock()
    credentials.credentials = token

    result = await get_current_user(credentials=credentials, db=db_session)
    assert isinstance(result, CurrentUser)
    assert result.display_name == "Test User"


@patch("src.dependencies.auth._get_jwks_client", return_value=_mock_jwks_client())
async def test_invalid_jwt_raises_401(mock_jwks, db_session: AsyncSession):
    credentials = MagicMock()
    credentials.credentials = "invalid-token"

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

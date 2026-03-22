"""JWTトークン生成のユニットテスト。"""

import uuid

from jose import jwt

from src.api.auth import _create_access_token
from src.core.config import settings


def test_create_access_token():
    user_id = str(uuid.uuid4())
    discord_id = "123456789"
    token = _create_access_token(user_id, discord_id)
    assert isinstance(token, str)

    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == user_id
    assert payload["discord_id"] == discord_id
    assert "exp" in payload


def test_create_access_token_different_users():
    token1 = _create_access_token("user1", "discord1")
    token2 = _create_access_token("user2", "discord2")
    assert token1 != token2

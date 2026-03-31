"""Supabase JWT (RS256) 検証のユニットテスト。"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import rsa

# テスト用RSAキーペア
_test_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_test_public_key = _test_private_key.public_key()


def test_rs256_jwt_encode_decode():
    """RS256でエンコードしたJWTを公開鍵でデコードできることを確認。"""
    auth_user_id = str(uuid.uuid4())
    payload = {
        "sub": auth_user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "email": "test@example.com",
        "user_metadata": {
            "provider_id": "123456789",
            "full_name": "Test User",
            "avatar_url": "https://cdn.example.com/avatar.png",
        },
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
    }
    token = pyjwt.encode(payload, _test_private_key, algorithm="RS256")

    decoded = pyjwt.decode(
        token,
        _test_public_key,
        algorithms=["RS256"],
        audience="authenticated",
    )
    assert decoded["sub"] == auth_user_id
    assert decoded["aud"] == "authenticated"
    assert decoded["user_metadata"]["full_name"] == "Test User"


def test_rs256_jwt_wrong_key_fails():
    """異なるRSA鍵ペアではデコードに失敗することを確認。"""
    import pytest

    wrong_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    payload = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = pyjwt.encode(payload, wrong_private_key, algorithm="RS256")

    with pytest.raises(pyjwt.InvalidSignatureError):
        pyjwt.decode(
            token,
            _test_public_key,
            algorithms=["RS256"],
            audience="authenticated",
        )

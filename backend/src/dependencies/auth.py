"""認証dependency。Supabase JWTトークン検証またはDEBUGモードの開発用スタブ。"""

import logging
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.base import get_db
from src.db.models import User

logger = logging.getLogger(__name__)


@dataclass
class CurrentUser:
    id: uuid.UUID
    display_name: str


# 開発用の固定ユーザーID
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

security = HTTPBearer(auto_error=False)

# JWKSクライアント（遅延初期化、10分キャッシュ）
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    """Supabase の JWKS エンドポイントからJWKセットを取得するクライアントを返す。"""
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=600)
    return _jwks_client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Supabase JWTトークンを検証してCurrentUserを返す。DEBUGモードではトークンなしで開発用ユーザーを返す。"""
    # トークンがある場合: Supabase JWT検証 (RS256 + JWKS)
    if credentials is not None:
        try:
            signing_key = _get_jwks_client().get_signing_key_from_jwt(credentials.credentials)
            payload = jwt.decode(
                credentials.credentials,
                signing_key.key,
                algorithms=["RS256"],
                audience="authenticated",
            )
            auth_user_id = uuid.UUID(payload["sub"])
        except (jwt.PyJWTError, KeyError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです",
            )

        result = await db.execute(select(User).where(User.auth_id == auth_user_id))
        user = result.scalar_one_or_none()
        if user is None:
            user_meta = payload.get("user_metadata", {})
            discord_id = user_meta.get("provider_id")
            email = payload.get("email")

            # 移行前の既存ユーザーを discord_id または email で検索して紐付け
            if discord_id:
                result = await db.execute(select(User).where(User.discord_id == discord_id))
                user = result.scalar_one_or_none()
            if user is None and email:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()

            if user is not None:
                # 既存ユーザーに auth_id を紐付け
                user.auth_id = auth_user_id
                user.avatar_url = user_meta.get("avatar_url") or user.avatar_url
                user.display_name = user_meta.get("full_name") or user.display_name
            else:
                # 完全に新規のユーザーを作成
                user = User(
                    auth_id=auth_user_id,
                    discord_id=discord_id,
                    display_name=user_meta.get("full_name") or user_meta.get("name", "User"),
                    email=email,
                    avatar_url=user_meta.get("avatar_url"),
                )
                db.add(user)
            await db.flush()
        return CurrentUser(id=user.id, display_name=user.display_name)

    # トークンなし + DEBUGモード: 開発用スタブ
    if settings.debug:
        logger.warning(
            "DEBUGモード: トークンなしのリクエストを開発ユーザーで処理します。"
            " 意図しない場合はAuthorizationヘッダーを確認してください。"
        )
        result = await db.execute(select(User).where(User.id == DEV_USER_ID))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(id=DEV_USER_ID, display_name="開発ユーザー")
            db.add(user)
            await db.flush()
        return CurrentUser(id=user.id, display_name=user.display_name)

    # トークンなし + 本番: 認証エラー
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証が必要です",
    )

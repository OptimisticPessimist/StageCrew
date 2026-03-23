"""認証dependency。JWTトークン検証またはDEBUGモードの開発用スタブ。"""

import logging
import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """JWTトークンを検証してCurrentUserを返す。DEBUGモードではトークンなしで開発用ユーザーを返す。"""
    # トークンがある場合: JWT検証
    if credentials is not None:
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            user_id = uuid.UUID(payload["sub"])
        except (JWTError, KeyError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです",
            )

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つかりません",
            )
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

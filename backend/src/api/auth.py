"""Discord OAuth2 認証エンドポイント。"""

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from src.core.config import settings
from src.db.base import get_db
from src.db.models import User
from src.dependencies.auth import CurrentUser, get_current_user

router = APIRouter()

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_AUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = f"{DISCORD_API_BASE}/oauth2/token"
DISCORD_USER_URL = f"{DISCORD_API_BASE}/users/@me"


def _create_access_token(user_id: str, discord_id: str) -> str:
    """JWTアクセストークンを生成する。"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": user_id, "discord_id": discord_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@router.get("/login")
async def discord_login():
    """Discord OAuth2 認可URLへリダイレクト。"""
    params = {
        "client_id": settings.discord_client_id,
        "redirect_uri": settings.discord_redirect_uri,
        "response_type": "code",
        "scope": "identify email",
    }
    return RedirectResponse(f"{DISCORD_AUTH_URL}?{urlencode(params)}")


@router.get("/callback")
async def discord_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Discord OAuth2 コールバック。code→トークン交換→ユーザーupsert→JWT発行。"""
    # 1. code → Discord アクセストークン
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            DISCORD_TOKEN_URL,
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.discord_redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            return RedirectResponse(f"{settings.frontend_url}/login?error=token_exchange_failed")

        token_data = token_resp.json()
        access_token = token_data["access_token"]

        # 2. Discord ユーザー情報取得
        user_resp = await client.get(
            DISCORD_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_resp.status_code != 200:
            return RedirectResponse(f"{settings.frontend_url}/login?error=user_fetch_failed")

        discord_user = user_resp.json()

    discord_id = discord_user["id"]
    username = discord_user.get("global_name") or discord_user["username"]
    email = discord_user.get("email")
    avatar_hash = discord_user.get("avatar")
    avatar_url = (
        f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png"
        if avatar_hash
        else None
    )

    # 3. ユーザー upsert
    result = await db.execute(select(User).where(User.discord_id == discord_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            discord_id=discord_id,
            display_name=username,
            email=email,
            avatar_url=avatar_url,
        )
        db.add(user)
    else:
        user.display_name = username
        user.email = email
        user.avatar_url = avatar_url

    await db.flush()

    # 4. JWT 発行 → フロントエンドへリダイレクト
    token = _create_access_token(str(user.id), discord_id)
    return RedirectResponse(f"{settings.frontend_url}/auth/callback?token={token}")


@router.get("/me")
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """現在のユーザー情報を返す。"""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "discord_id": user.discord_id,
    }

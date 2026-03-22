"""Discord OAuth2 authentication endpoints."""

import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
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
OAUTH_STATE_COOKIE = "stagecrew_oauth_state"
OAUTH_STATE_MAX_AGE = 600


def _create_access_token(user_id: str, discord_id: str) -> str:
    """Create a JWT access token for the authenticated user."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": user_id, "discord_id": discord_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@router.get("/login")
async def discord_login():
    """Redirect to the Discord OAuth2 authorization URL."""
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.discord_client_id,
        "redirect_uri": settings.discord_redirect_uri,
        "response_type": "code",
        "scope": "identify email",
        "state": state,
    }
    response = RedirectResponse(f"{DISCORD_AUTH_URL}?{urlencode(params)}")
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        max_age=OAUTH_STATE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,
    )
    return response


@router.get("/callback")
async def discord_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle the Discord OAuth2 callback and issue the app JWT."""
    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not cookie_state or not secrets.compare_digest(state, cookie_state):
        response = RedirectResponse(f"{settings.frontend_url}/login?error=invalid_state")
        response.delete_cookie(OAUTH_STATE_COOKIE)
        return response

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
            response = RedirectResponse(f"{settings.frontend_url}/login?error=token_exchange_failed")
            response.delete_cookie(OAUTH_STATE_COOKIE)
            return response

        token_data = token_resp.json()
        access_token = token_data["access_token"]

        user_resp = await client.get(
            DISCORD_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_resp.status_code != 200:
            response = RedirectResponse(f"{settings.frontend_url}/login?error=user_fetch_failed")
            response.delete_cookie(OAUTH_STATE_COOKIE)
            return response

        discord_user = user_resp.json()

    discord_id = discord_user["id"]
    username = discord_user.get("global_name") or discord_user["username"]
    email = discord_user.get("email")
    avatar_hash = discord_user.get("avatar")
    avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png" if avatar_hash else None

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

    token = _create_access_token(str(user.id), discord_id)
    response = RedirectResponse(f"{settings.frontend_url}/auth/callback?token={token}")
    response.delete_cookie(OAUTH_STATE_COOKIE)
    return response


@router.get("/me")
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the currently authenticated user."""
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

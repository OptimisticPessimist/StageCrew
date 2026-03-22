import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import (
    auth,
    comments,
    departments,
    dept_members,
    health,
    invitations,
    issues,
    milestones,
    org_members,
    organizations,
    phases,
    production_members,
    productions,
    statuses,
)
from src.core.config import settings
from src.services.deadline_reminder import deadline_reminder_loop

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(deadline_reminder_loop())
    logger.info("Deadline reminder background task started")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.app_name,
    description="Task management SaaS for theater production groups",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth/discord", tags=["auth"])
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(organizations.router, prefix="/api/organizations", tags=["organizations"])
app.include_router(productions.router, prefix="/api/organizations/{org_id}/productions", tags=["productions"])
app.include_router(
    statuses.router,
    prefix="/api/organizations/{org_id}/productions/{production_id}/statuses",
    tags=["statuses"],
)
app.include_router(
    issues.router,
    prefix="/api/organizations/{org_id}/productions/{production_id}/issues",
    tags=["issues"],
)
app.include_router(
    departments.router,
    prefix="/api/organizations/{org_id}/productions/{production_id}/departments",
    tags=["departments"],
)
app.include_router(
    org_members.router,
    prefix="/api/organizations/{org_id}/members",
    tags=["org-members"],
)
app.include_router(
    production_members.router,
    prefix="/api/organizations/{org_id}/productions/{production_id}/members",
    tags=["production-members"],
)
app.include_router(
    dept_members.router,
    prefix="/api/organizations/{org_id}/productions/{production_id}/departments/{dept_id}/members",
    tags=["department-members"],
)
app.include_router(
    phases.router,
    prefix="/api/organizations/{org_id}/productions/{production_id}/phases",
    tags=["phases"],
)
app.include_router(
    milestones.router,
    prefix="/api/organizations/{org_id}/productions/{production_id}/milestones",
    tags=["milestones"],
)
app.include_router(
    comments.router,
    prefix="/api/organizations/{org_id}/productions/{production_id}/issues/{issue_id}/comments",
    tags=["comments"],
)
app.include_router(
    invitations.org_router,
    prefix="/api/organizations/{org_id}/invitations",
    tags=["invitations"],
)
app.include_router(
    invitations.accept_router,
    prefix="/api/invitations",
    tags=["invitations"],
)


@app.get("/")
async def root():
    return {"app": settings.app_name, "version": "0.1.0"}

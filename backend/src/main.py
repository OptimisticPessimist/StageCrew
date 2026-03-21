from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import health, organizations, productions
from src.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="Task management SaaS for theater production groups",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(organizations.router, prefix="/api/organizations", tags=["organizations"])
app.include_router(productions.router, prefix="/api/organizations/{org_id}/productions", tags=["productions"])


@app.get("/")
async def root():
    return {"app": settings.app_name, "version": "0.1.0"}

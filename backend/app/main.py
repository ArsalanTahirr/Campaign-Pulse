"""
main.py — FastAPI application entry-point for CampaignPulse.

Start the development server from the backend/ directory:

    uvicorn app.main:app --reload --port 8000

Environment variables are loaded from the repo-root .env file by each
sub-module (database.py, auth.py, email_utils.py, routers/users.py).
"""

import os
import asyncio

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import users
from app.routers import (
    workspaces,
    invitations,
    collaborators,
    campaigns,
    sequences,
    leads,
    email_accounts,
    engine_ops,
    track,
)
from app.workers.engine_loops import imap_reply_loop, sending_loop, warmup_loop

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:3000")


def _cors_allow_origins() -> list[str]:
    """Allow the configured origin plus localhost ↔ 127.0.0.1 swap (common dev mismatch)."""
    origins: set[str] = set()
    primary = FRONTEND_URL.strip() or "http://localhost:3000"
    origins.add(primary.rstrip("/"))
    if "localhost" in primary:
        origins.add(primary.replace("localhost", "127.0.0.1").rstrip("/"))
    if "127.0.0.1" in primary:
        origins.add(primary.replace("127.0.0.1", "localhost").rstrip("/"))
    extra = os.environ.get("FRONTEND_URLS", "")
    for part in extra.split(","):
        p = part.strip().rstrip("/")
        if p:
            origins.add(p)
    return sorted(origins)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CampaignPulse API",
    description="Backend API for the CampaignPulse email outreach platform.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

_ENGINE_TASKS: list[asyncio.Task] = []

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

# Auth (existing)
app.include_router(users.router, prefix="/auth", tags=["Authentication"])

# Workspaces
app.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])

# Invitations — two sub-trees:
#   /workspaces/{id}/invitations  (workspace-scoped management)
#   /invitations/{token}          (public acceptance flow)
app.include_router(invitations.router, tags=["Invitations"])

# Collaborators  — /workspaces/{workspace_id}/collaborators
app.include_router(
    collaborators.router,
    prefix="/workspaces/{workspace_id}/collaborators",
    tags=["Collaborators"],
)

# Campaigns — /workspaces/{workspace_id}/campaigns
app.include_router(
    campaigns.router,
    prefix="/workspaces/{workspace_id}/campaigns",
    tags=["Campaigns"],
)

# Sequence steps + email variants — nested under campaign
app.include_router(
    sequences.router,
    prefix="/workspaces/{workspace_id}/campaigns/{campaign_id}",
    tags=["Sequences"],
)

# Leads — nested under campaign
app.include_router(
    leads.router,
    prefix="/workspaces/{workspace_id}/campaigns/{campaign_id}",
    tags=["Leads"],
)

# Email accounts — workspace scoped
app.include_router(
    email_accounts.router,
    prefix="/workspaces/{workspace_id}",
    tags=["Email Accounts"],
)

app.include_router(
    engine_ops.router,
    prefix="/workspaces/{workspace_id}/engine",
    tags=["Engine Ops"],
)

# Public tracking links
app.include_router(track.router, prefix="/track", tags=["Tracking"])


@app.on_event("startup")
async def startup_background_workers():
    _ENGINE_TASKS.clear()
    _ENGINE_TASKS.append(asyncio.create_task(sending_loop()))
    _ENGINE_TASKS.append(asyncio.create_task(warmup_loop()))
    _ENGINE_TASKS.append(asyncio.create_task(imap_reply_loop()))


@app.on_event("shutdown")
async def shutdown_background_workers():
    for task in _ENGINE_TASKS:
        task.cancel()
    _ENGINE_TASKS.clear()


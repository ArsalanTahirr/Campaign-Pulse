"""
main.py — FastAPI application entry-point for CampaignPulse.

Start the development server from the backend/ directory:

    uvicorn app.main:app --reload --port 8000

Environment variables are loaded from the repo-root .env file by each
sub-module (database.py, auth.py, email_utils.py, routers/users.py).
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import users
from app.routers import workspaces, invitations, collaborators, campaigns, sequences, leads

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:3000")

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

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    # In production, replace with the actual frontend origin(s).
    allow_origins=[FRONTEND_URL],
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


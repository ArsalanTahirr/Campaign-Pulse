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

# All auth routes live under /auth so they match the frontend's expected
# endpoints: POST /auth/signup, POST /auth/login, GET /auth/verify-email, etc.
app.include_router(users.router, prefix="/auth", tags=["Authentication"])

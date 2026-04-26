"""
schemas/campaign.py — Pydantic v2 models for Campaigns and CampaignRuns.

ORM column is `campaign_name`; exposed as `name` in the API via validation_alias.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------


class CampaignCreate(BaseModel):
    # Stored as `campaign_name` in the ORM; clients send/receive as `name`.
    name: str = Field(min_length=1, max_length=255)
    timezone: str = Field(
        default="UTC",
        min_length=1,
        max_length=100,
        description='IANA timezone for scheduling (e.g. "UTC", "Asia/Karachi").',
    )
    schedule: Optional[dict[str, Any]] = Field(
        None,
        description=(
            "Campaign-level send schedule. "
            'Example: {"days": ["Monday","Wednesday"], "time": "09:00", "tz": "UTC"}'
        ),
    )
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    timezone: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description='IANA timezone for scheduling (e.g. "UTC", "America/New_York").',
    )
    status: Optional[str] = Field(
        None,
        description="Allowed transitions are enforced server-side.",
    )
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CampaignOut(BaseModel):
    campaign_id: str
    workspace_id: str
    created_by: Optional[str] = None
    # ORM column is `campaign_name`; expose as `name`.
    name: str = Field(validation_alias="campaign_name")
    status: str
    timezone: str = "UTC"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Convenience counts injected by the service layer (not ORM attributes)
    step_count: int = 0
    lead_count: int = 0

    model_config = {"from_attributes": True, "populate_by_name": True}


# ---------------------------------------------------------------------------
# CampaignRun
# ---------------------------------------------------------------------------


class CampaignRunCreate(BaseModel):
    action: str = Field(
        ...,
        description="Lifecycle action: started | paused | resumed | stopped",
    )


class CampaignRunOut(BaseModel):
    run_id: str
    campaign_id: str
    triggered_by: Optional[str] = None
    action: str
    run_status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

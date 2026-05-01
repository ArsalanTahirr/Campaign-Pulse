"""
routers/analytics.py — Analytics dashboard endpoints.

All endpoints are scoped to a workspace and require the 'view_analytics'
permission (roles: Owner, Agency, Marketing Manager, Data Analyst).

Endpoints
─────────
GET /workspaces/{workspace_id}/analytics/summary
    Global KPIs aggregated across all campaigns in the workspace.

GET /workspaces/{workspace_id}/analytics/graph
    Time-series data for the four required metrics.
    Query param: ?granularity=daily|weekly|monthly  (default: monthly)

GET /workspaces/{workspace_id}/analytics/campaigns
    Per-campaign breakdown for all campaigns in the workspace.

GET /workspaces/{workspace_id}/analytics/account-performance
    Per-sender-account breakdown for a single campaign.
    Query param: ?campaign_id=<uuid>  (required)
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.models import Campaign
from app.schemas.analytics import (
    AccountPerformanceResponse,
    CampaignAnalyticsResponse,
    GlobalSummaryResponse,
    GraphDataResponse,
)
from app.services import analytics_service

router = APIRouter()


@router.get("/summary", response_model=GlobalSummaryResponse)
def get_summary(
    workspace_id: str,
    _: None = require_permission("view_analytics"),
    db: Session = Depends(get_db),
):
    """Global KPIs aggregated across all campaigns in the workspace."""
    data = analytics_service.get_global_summary(workspace_id, db)
    return GlobalSummaryResponse(**data)


@router.get("/graph", response_model=GraphDataResponse)
def get_graph(
    workspace_id: str,
    granularity: Literal["daily", "weekly", "monthly"] = Query(
        default="monthly",
        description="Time bucket granularity: daily | weekly | monthly",
    ),
    _: None = require_permission("view_analytics"),
    db: Session = Depends(get_db),
):
    """
    Time-series data for Total Emails Sent, Open Rate, Click Rate, Reply Rate.
    Returns exactly 4 series. Returns empty value arrays when no data exists.
    """
    data = analytics_service.get_graph_data(workspace_id, granularity, db)
    return GraphDataResponse.model_validate(data)


@router.get("/campaigns", response_model=CampaignAnalyticsResponse)
def get_campaign_analytics(
    workspace_id: str,
    _: None = require_permission("view_analytics"),
    db: Session = Depends(get_db),
):
    """Per-campaign analytics for all campaigns in the workspace."""
    data = analytics_service.get_campaign_analytics(workspace_id, db)
    return CampaignAnalyticsResponse.model_validate(data)


@router.get("/account-performance", response_model=AccountPerformanceResponse)
def get_account_performance(
    workspace_id: str,
    campaign_id: str = Query(
        ...,
        description="The campaign to scope account performance to (required).",
    ),
    _: None = require_permission("view_analytics"),
    db: Session = Depends(get_db),
):
    """
    Per-sender-account breakdown for a single campaign.
    Scoped exclusively to the requested campaign_id — never aggregated across campaigns.
    """
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.campaign_id == campaign_id,
            Campaign.workspace_id == workspace_id,
        )
        .first()
    )
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign '{campaign_id}' not found in this workspace.",
        )

    data = analytics_service.get_account_performance(campaign_id, db)
    return AccountPerformanceResponse.model_validate(data)

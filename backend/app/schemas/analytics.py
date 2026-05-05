"""
schemas/analytics.py — Pydantic v2 response models for the analytics API.

All percentage values are floats rounded to 2 decimal places.
All count values are integers — the service layer enforces this.
No field is ever undefined: counts default to 0, rates to 0.0, booleans are explicit.
"""

from typing import Literal, Union

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 1. Global summary
# ---------------------------------------------------------------------------


class GlobalSummaryResponse(BaseModel):
    total_sent: int
    open_rate: float
    click_rate: float
    reply_rate: float


# ---------------------------------------------------------------------------
# 2. Graph data
# ---------------------------------------------------------------------------


class GraphSeries(BaseModel):
    key: str
    label: str
    values: list[Union[int, float]]


class GraphData(BaseModel):
    labels: list[str]
    series: list[GraphSeries]


class GraphDataResponse(BaseModel):
    graph_data: GraphData


# ---------------------------------------------------------------------------
# 3. Account performance
# ---------------------------------------------------------------------------


class AccountPerformanceRow(BaseModel):
    sending_account: str
    contacted: int
    opened: int
    replied: int
    tracking_enabled: bool


class AccountPerformanceResponse(BaseModel):
    account_performance: list[AccountPerformanceRow]


# ---------------------------------------------------------------------------
# 4. Campaign analytics
# ---------------------------------------------------------------------------


class RepliedStats(BaseModel):
    count: int
    rate: float


class CampaignAnalyticsRow(BaseModel):
    campaign_id: str
    campaign_name: str
    status: Literal["active", "completed"]
    lifecycle: str
    sequence_started: int
    opened: int
    replied: RepliedStats
    opportunities: int


class CampaignAnalyticsResponse(BaseModel):
    campaigns: list[CampaignAnalyticsRow]

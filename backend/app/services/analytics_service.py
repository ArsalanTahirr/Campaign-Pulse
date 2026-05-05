"""
services/analytics_service.py — SQL aggregation logic for the analytics dashboard.

All queries join email_event → lead → campaign to scope results to a workspace.
Only events with event_scope = 'lead' are counted — warmup events are excluded.

Division-by-zero is handled in Python after fetching counts, never in SQL.
All percentage values are rounded to 2 decimal places.
All count values are integers.
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy import func, text, distinct, select, tuple_
from sqlalchemy.orm import Session

from app.models import Campaign, EmailEvent, Lead, SenderAccount, SequenceStep

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_GRANULARITY_TRUNC: dict[str, str] = {
    "daily": "day",
    "weekly": "week",
    "monthly": "month",
}


def _safe_rate(numerator: int, denominator: int) -> float:
    """Return (numerator / denominator * 100) rounded to 2 dp, or 0.0 if denominator is 0."""
    if denominator == 0:
        return 0.0
    return round(numerator / denominator * 100, 2)


def _campaign_ids_for_workspace(workspace_id: str, db: Session) -> list[str]:
    """Return a list of campaign_ids that belong to this workspace."""
    rows = (
        db.query(Campaign.campaign_id)
        .filter(Campaign.workspace_id == workspace_id)
        .all()
    )
    return [r[0] for r in rows]


def _db_statuses_for_api_filter(api_status: Optional[str]) -> Optional[list[str]]:
    """
    Map a single dashboard filter token to DB Campaign.status values.
    None / 'all' → no extra status filter.
    """
    if not api_status or str(api_status).lower() in ("all", ""):
        return None
    key = str(api_status).lower().strip()
    if key == "completed":
        return ["completed", "archived", "deleted"]
    if key in ("active", "paused", "draft", "scheduled"):
        return [key]
    return None


def _workspace_campaign_ids_filtered(
    workspace_id: str,
    db: Session,
    *,
    campaign_statuses: Optional[list[str]] = None,
) -> list[str]:
    """Campaign ids in workspace, optionally restricted by Campaign.status."""
    q = db.query(Campaign.campaign_id).filter(Campaign.workspace_id == workspace_id)
    if campaign_statuses:
        q = q.filter(Campaign.status.in_(campaign_statuses))
    return [r[0] for r in q.all()]


def _scoped_campaign_ids(
    workspace_id: str,
    db: Session,
    campaign_id: Optional[str],
    *,
    campaign_statuses: Optional[list[str]] = None,
) -> list[str]:
    """Workspace campaigns (optionally status-scoped), or one id if it matches scope."""
    all_ids = _workspace_campaign_ids_filtered(
        workspace_id, db, campaign_statuses=campaign_statuses
    )
    if not campaign_id:
        return all_ids
    return [campaign_id] if campaign_id in all_ids else []


def _apply_occurred_at_filters(q, date_from: Optional[datetime], date_to: Optional[datetime]):
    """Restrict EmailEvent rows to [date_from, date_to] on occurred_at (inclusive)."""
    if date_from is not None:
        q = q.filter(EmailEvent.occurred_at >= date_from)
    if date_to is not None:
        q = q.filter(EmailEvent.occurred_at <= date_to)
    return q


def _normalize_campaign_status(db_status: str) -> Literal["active", "completed"]:
    """
    Map the full set of DB campaign status values to the two values the
    analytics API is allowed to return: 'active' or 'completed'.
    """
    if db_status in ("completed", "archived", "deleted"):
        return "completed"
    return "active"


# ---------------------------------------------------------------------------
# 1. Global summary
# ---------------------------------------------------------------------------


def get_global_summary(
    workspace_id: str,
    db: Session,
    *,
    campaign_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    campaign_status: Optional[str] = None,
) -> dict:
    """
    Return total_sent, open_rate, click_rate, reply_rate aggregated across
    all campaigns in the workspace.

    Delivered = total sent emails minus leads that bounced at least once.

    Optional filters (industry-standard dashboard scope):
      * campaign_id — restrict to one campaign in the workspace
      * date_from / date_to — inclusive bounds on EmailEvent.occurred_at (UTC)
      * campaign_status — all | active | paused | completed (completed includes archived/deleted)
    """
    st = _db_statuses_for_api_filter(campaign_status)
    campaign_ids = _scoped_campaign_ids(
        workspace_id, db, campaign_id, campaign_statuses=st
    )

    if not campaign_ids:
        return {
            "total_sent": 0,
            "open_rate": 0.0,
            "click_rate": 0.0,
            "reply_rate": 0.0,
        }

    base = _apply_occurred_at_filters(
        db.query(EmailEvent)
        .join(Lead, Lead.lead_id == EmailEvent.lead_id)
        .filter(
            Lead.campaign_id.in_(campaign_ids),
            EmailEvent.event_scope == "lead",
        ),
        date_from,
        date_to,
    )

    total_sent: int = (
        base.filter(EmailEvent.event_type == "sent").count()
    )

    total_bounced: int = (
        base.filter(EmailEvent.event_type == "bounced")
        .with_entities(func.count(distinct(EmailEvent.lead_id)))
        .scalar() or 0
    )

    total_delivered: int = max(0, total_sent - total_bounced)

    unique_opens: int = (
        base.filter(EmailEvent.event_type == "opened")
        .with_entities(func.count(distinct(EmailEvent.lead_id)))
        .scalar() or 0
    )

    # Unique clicks: count each (lead, campaign) pair once per spec.
    clicks_q = (
        db.query(
            func.count(
                distinct(tuple_(EmailEvent.lead_id, Lead.campaign_id))
            )
        )
        .join(Lead, Lead.lead_id == EmailEvent.lead_id)
        .filter(
            Lead.campaign_id.in_(campaign_ids),
            EmailEvent.event_scope == "lead",
            EmailEvent.event_type == "clicked",
        )
    )
    clicks_q = _apply_occurred_at_filters(clicks_q, date_from, date_to)
    unique_clicks: int = clicks_q.scalar() or 0

    unique_replies: int = (
        base.filter(EmailEvent.event_type == "replied")
        .with_entities(func.count(distinct(EmailEvent.lead_id)))
        .scalar() or 0
    )

    return {
        "total_sent": total_sent,
        "open_rate": _safe_rate(unique_opens, total_delivered),
        "click_rate": _safe_rate(unique_clicks, total_delivered),
        "reply_rate": _safe_rate(unique_replies, total_delivered),
    }


# ---------------------------------------------------------------------------
# 2. Graph data
# ---------------------------------------------------------------------------


def get_graph_data(
    workspace_id: str,
    granularity: Literal["daily", "weekly", "monthly"],
    db: Session,
    *,
    campaign_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    campaign_status: Optional[str] = None,
) -> dict:
    """
    Return time-bucketed series data for the four required metrics.

    Returns empty value arrays (not errors) when no data exists.

    Optional campaign_id, date_from/date_to, and campaign_status match get_global_summary.
    """
    trunc_unit = _GRANULARITY_TRUNC.get(granularity, "day")
    st = _db_statuses_for_api_filter(campaign_status)
    campaign_ids = _scoped_campaign_ids(
        workspace_id, db, campaign_id, campaign_statuses=st
    )

    if not campaign_ids:
        return {
            "graph_data": {
                "labels": [],
                "series": [
                    {"key": "total_sent",  "label": "Total Emails Sent", "values": []},
                    {"key": "open_rate",   "label": "Open Rate (%)",     "values": []},
                    {"key": "click_rate",  "label": "Click Rate (%)",    "values": []},
                    {"key": "reply_rate",  "label": "Reply Rate (%)",    "values": []},
                ],
            }
        }

    bucket_col = func.date_trunc(trunc_unit, EmailEvent.occurred_at).label("bucket")

    rows = _apply_occurred_at_filters(
        db.query(
            bucket_col,
            EmailEvent.event_type,
            EmailEvent.lead_id,
            Lead.campaign_id,
        )
        .join(Lead, Lead.lead_id == EmailEvent.lead_id)
        .filter(
            Lead.campaign_id.in_(campaign_ids),
            EmailEvent.event_scope == "lead",
        ),
        date_from,
        date_to,
    ).order_by(bucket_col).all()

    if not rows:
        return {
            "graph_data": {
                "labels": [],
                "series": [
                    {"key": "total_sent",  "label": "Total Emails Sent", "values": []},
                    {"key": "open_rate",   "label": "Open Rate (%)",     "values": []},
                    {"key": "click_rate",  "label": "Click Rate (%)",    "values": []},
                    {"key": "reply_rate",  "label": "Reply Rate (%)",    "values": []},
                ],
            }
        }

    # Aggregate per bucket in Python.
    # Each bucket tracks: sent, bounced_leads, unique_opens, unique_clicks (lead,campaign), unique_replies
    from collections import defaultdict

    bucket_sent: dict = defaultdict(int)
    bucket_bounced: dict[str, set] = defaultdict(set)
    bucket_opens: dict[str, set] = defaultdict(set)
    bucket_clicks: dict[str, set] = defaultdict(set)
    bucket_replies: dict[str, set] = defaultdict(set)

    for row in rows:
        bucket = row.bucket
        # Normalize to a string label depending on granularity.
        if granularity == "daily":
            label = bucket.strftime("%b %d")
        elif granularity == "weekly":
            label = f"W{bucket.strftime('%U')} {bucket.strftime('%b %Y')}"
        else:
            label = bucket.strftime("%b %Y")

        et = row.event_type
        lid = row.lead_id
        cid = row.campaign_id

        if et == "sent":
            bucket_sent[label] += 1
        elif et == "bounced":
            bucket_bounced[label].add(lid)
        elif et == "opened":
            bucket_opens[label].add(lid)
        elif et == "clicked":
            bucket_clicks[label].add((lid, cid))
        elif et == "replied":
            bucket_replies[label].add(lid)

    # Build sorted unique label list (order preserved by query ORDER BY bucket).
    seen: set = set()
    labels: list[str] = []
    for row in rows:
        bucket = row.bucket
        if granularity == "daily":
            label = bucket.strftime("%b %d")
        elif granularity == "weekly":
            label = f"W{bucket.strftime('%U')} {bucket.strftime('%b %Y')}"
        else:
            label = bucket.strftime("%b %Y")
        if label not in seen:
            seen.add(label)
            labels.append(label)

    total_sent_vals: list[int] = []
    open_rate_vals: list[float] = []
    click_rate_vals: list[float] = []
    reply_rate_vals: list[float] = []

    for lbl in labels:
        sent = bucket_sent.get(lbl, 0)
        bounced = len(bucket_bounced.get(lbl, set()))
        delivered = max(0, sent - bounced)
        opens = len(bucket_opens.get(lbl, set()))
        clicks = len(bucket_clicks.get(lbl, set()))
        replies = len(bucket_replies.get(lbl, set()))

        total_sent_vals.append(sent)
        open_rate_vals.append(_safe_rate(opens, delivered))
        click_rate_vals.append(_safe_rate(clicks, delivered))
        reply_rate_vals.append(_safe_rate(replies, delivered))

    return {
        "graph_data": {
            "labels": labels,
            "series": [
                {"key": "total_sent",  "label": "Total Emails Sent", "values": total_sent_vals},
                {"key": "open_rate",   "label": "Open Rate (%)",     "values": open_rate_vals},
                {"key": "click_rate",  "label": "Click Rate (%)",    "values": click_rate_vals},
                {"key": "reply_rate",  "label": "Reply Rate (%)",    "values": reply_rate_vals},
            ],
        }
    }


# ---------------------------------------------------------------------------
# 3. Account performance (per campaign)
# ---------------------------------------------------------------------------


def get_account_performance(campaign_id: str, db: Session) -> dict:
    """
    Return per-sender-account breakdown for a single campaign.

    contacted = distinct leads emailed by that account
    opened    = distinct leads who opened at least one email from that account
    replied   = distinct leads who replied to at least one email from that account

    tracking_enabled is always True — there is no tracking-disabled flag in the
    current schema. This field will be replaced once schema change SC-REQUEST #2
    is approved.
    """
    # Find all sender accounts that sent at least one lead email in this campaign.
    sender_ids_query = (
        db.query(distinct(EmailEvent.sender_account_id))
        .join(Lead, Lead.lead_id == EmailEvent.lead_id)
        .filter(
            Lead.campaign_id == campaign_id,
            EmailEvent.event_scope == "lead",
            EmailEvent.event_type == "sent",
            EmailEvent.sender_account_id.isnot(None),
        )
    )
    sender_ids = [row[0] for row in sender_ids_query.all()]

    # Resolve tracking flag once for this campaign.
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    tracking_enabled: bool = campaign.open_tracking_enabled if campaign else True

    rows = []
    for account_id in sender_ids:
        account = db.query(SenderAccount).filter(SenderAccount.account_id == account_id).first()
        if not account:
            continue

        contacted: int = (
            db.query(func.count(distinct(EmailEvent.lead_id)))
            .join(Lead, Lead.lead_id == EmailEvent.lead_id)
            .filter(
                Lead.campaign_id == campaign_id,
                EmailEvent.event_scope == "lead",
                EmailEvent.event_type == "sent",
                EmailEvent.sender_account_id == account_id,
            )
            .scalar() or 0
        )

        # When open tracking is disabled the opens column is 0 per spec.
        opened: int = 0
        if tracking_enabled:
            opened = (
                db.query(func.count(distinct(EmailEvent.lead_id)))
                .join(Lead, Lead.lead_id == EmailEvent.lead_id)
                .filter(
                    Lead.campaign_id == campaign_id,
                    EmailEvent.event_scope == "lead",
                    EmailEvent.event_type == "opened",
                    EmailEvent.sender_account_id == account_id,
                )
                .scalar() or 0
            )

        replied: int = (
            db.query(func.count(distinct(EmailEvent.lead_id)))
            .join(Lead, Lead.lead_id == EmailEvent.lead_id)
            .filter(
                Lead.campaign_id == campaign_id,
                EmailEvent.event_scope == "lead",
                EmailEvent.event_type == "replied",
                EmailEvent.sender_account_id == account_id,
            )
            .scalar() or 0
        )

        rows.append({
            "sending_account": account.email,
            "contacted": contacted,
            "opened": opened,
            "replied": replied,
            "tracking_enabled": tracking_enabled,
        })

    return {"account_performance": rows}


# ---------------------------------------------------------------------------
# 4. Campaign analytics list
# ---------------------------------------------------------------------------


def get_campaign_analytics(workspace_id: str, db: Session) -> dict:
    """
    Return per-campaign analytics for all campaigns in the workspace.

    sequence_started = leads who received at least the first step email (step_number=1)
    opened           = unique leads who opened any email in the campaign
    replied.count    = unique leads who replied at any step
    replied.rate     = (replied.count / sequence_started) × 100, rounded to 2 dp
    opportunities    = 0  TODO: requires schema change SC-REQUEST #1 — no existing
                       flag distinguishes high-quality replies from standard ones
    status           = mapped to 'active' | 'completed' only
    """
    campaigns = (
        db.query(Campaign)
        .filter(Campaign.workspace_id == workspace_id)
        .all()
    )

    result_rows = []
    for campaign in campaigns:
        cid = campaign.campaign_id

        # sequence_started: leads with a 'sent' event on step_number=1 of this campaign
        step1_subq = (
            select(SequenceStep.step_id).where(
                SequenceStep.campaign_id == cid,
                SequenceStep.step_number == 1,
            )
        )

        sequence_started: int = (
            db.query(func.count(distinct(EmailEvent.lead_id)))
            .join(Lead, Lead.lead_id == EmailEvent.lead_id)
            .filter(
                Lead.campaign_id == cid,
                EmailEvent.event_scope == "lead",
                EmailEvent.event_type == "sent",
                EmailEvent.step_id.in_(step1_subq),
            )
            .scalar() or 0
        )

        # Respect the campaign's open tracking flag.
        opened: int = 0
        if campaign.open_tracking_enabled:
            opened = (
                db.query(func.count(distinct(EmailEvent.lead_id)))
                .join(Lead, Lead.lead_id == EmailEvent.lead_id)
                .filter(
                    Lead.campaign_id == cid,
                    EmailEvent.event_scope == "lead",
                    EmailEvent.event_type == "opened",
                )
                .scalar() or 0
            )

        replied_count: int = (
            db.query(func.count(distinct(EmailEvent.lead_id)))
            .join(Lead, Lead.lead_id == EmailEvent.lead_id)
            .filter(
                Lead.campaign_id == cid,
                EmailEvent.event_scope == "lead",
                EmailEvent.event_type == "replied",
            )
            .scalar() or 0
        )

        replied_rate: float = _safe_rate(replied_count, sequence_started)

        # Opportunities: leads in this campaign flagged as high-quality replies.
        opportunities: int = (
            db.query(func.count(Lead.lead_id))
            .filter(
                Lead.campaign_id == cid,
                Lead.is_opportunity == True,  # noqa: E712
            )
            .scalar() or 0
        )

        result_rows.append({
            "campaign_id": cid,
            "campaign_name": campaign.campaign_name,
            "status": _normalize_campaign_status(campaign.status),
            "lifecycle": campaign.status or "draft",
            "sequence_started": sequence_started,
            "opened": opened,
            "replied": {
                "count": replied_count,
                "rate": replied_rate,
            },
            "opportunities": opportunities,
        })

    return {"campaigns": result_rows}

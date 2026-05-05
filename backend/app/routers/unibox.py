"""
routers/unibox.py — Unibox (unified inbox) API endpoints.

All endpoints are scoped to a workspace and require the 'view_workspace'
permission (equivalent to being a workspace member).  Write operations
(reply, tag, mark-read, pipeline update) additionally require the
'manage_leads' permission.

Endpoints
─────────
GET  /workspaces/{workspace_id}/unibox/inboxes
    List all SenderAccounts (inboxes) in the workspace with unread counts.

GET  /workspaces/{workspace_id}/unibox/threads
    Paginated thread list with optional filters.
    Query params:
      view          : all | unread | sent  (default: all)
      pipeline_status : lead | interested | meeting-booked | meeting-completed | won
      campaign_id   : UUID
      inbox_id      : UUID (SenderAccount)
      page          : int (default: 1)
      page_size     : int (default: 25, max: 100)

GET  /workspaces/{workspace_id}/unibox/threads/{thread_id}
    Full thread detail (all messages in order).  Auto-marks inbound as read.

PATCH /workspaces/{workspace_id}/unibox/threads/{thread_id}
    Update campaign tag and/or pipeline status on a thread.

POST /workspaces/{workspace_id}/unibox/threads/{thread_id}/reply
    Compose and send a reply from the Unibox.

PATCH /workspaces/{workspace_id}/unibox/threads/{thread_id}/messages/{message_id}/read
    Mark a single message as read or unread.

GET  /workspaces/{workspace_id}/unibox/search
    Full-text search across all messages in the workspace.
    Query params:
      q             : search string (required)
      inbox_id      : UUID filter
      campaign_id   : UUID filter
      from_date     : ISO 8601 datetime filter (lower bound)
      to_date       : ISO 8601 datetime filter (upper bound)
      page          : int
      page_size     : int
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.schemas.unibox import (
    InboxListResponse,
    InboxOut,
    MarkReadOut,
    MarkReadUpdate,
    MessageOut,
    ReplyCreate,
    ReplyOut,
    SearchPaginatedResponse,
    SearchResultItem,
    ThreadDetail,
    LeadSummary,
    ThreadPaginatedResponse,
    ThreadSummary,
    ThreadUpdate,
    ThreadUpdateOut,
)
from app.services.unibox import (
    aggregation_service,
    campaign_tagging_service,
    reply_dispatch_service,
    search_service,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Inboxes
# ---------------------------------------------------------------------------


@router.get("/inboxes", response_model=InboxListResponse)
def list_inboxes(
    workspace_id: str,
    _: None = require_permission("view_workspace"),
    db: Session = Depends(get_db),
):
    """List all sender accounts (inboxes) with unread message counts."""
    items = aggregation_service.list_inboxes(workspace_id, db)
    return InboxListResponse(items=[InboxOut(**item) for item in items])


# ---------------------------------------------------------------------------
# Thread listing
# ---------------------------------------------------------------------------


@router.get("/threads", response_model=ThreadPaginatedResponse)
def list_threads(
    workspace_id: str,
    view: Literal["all", "unread", "sent"] = Query("all"),
    pipeline_status: Optional[str] = Query(None),
    campaign_id: Optional[str] = Query(None),
    inbox_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: None = require_permission("view_workspace"),
    db: Session = Depends(get_db),
):
    """Return a paginated list of threads with optional filters."""
    total, items = aggregation_service.list_threads(
        workspace_id=workspace_id,
        view=view,
        pipeline_status=pipeline_status,
        campaign_id=campaign_id,
        inbox_id=inbox_id,
        page=page,
        page_size=page_size,
        db=db,
    )
    return ThreadPaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[ThreadSummary(**item) for item in items],
    )


# ---------------------------------------------------------------------------
# Thread detail
# ---------------------------------------------------------------------------


@router.get("/threads/{thread_id}", response_model=ThreadDetail)
def get_thread(
    workspace_id: str,
    thread_id: str,
    _: None = require_permission("view_workspace"),
    db: Session = Depends(get_db),
):
    """Return full thread detail and auto-mark inbound messages as read."""
    thread = aggregation_service.get_thread_detail(thread_id, workspace_id, db)
    db.commit()
    return _thread_to_detail(thread, db)


# ---------------------------------------------------------------------------
# Thread update (tag + pipeline)
# ---------------------------------------------------------------------------


@router.patch("/threads/{thread_id}", response_model=ThreadUpdateOut)
def update_thread(
    workspace_id: str,
    thread_id: str,
    body: ThreadUpdate,
    _: None = require_permission("manage_leads"),
    db: Session = Depends(get_db),
):
    """Update campaign tag and/or pipeline status on a thread."""
    thread = campaign_tagging_service.update_thread(
        thread_id=thread_id,
        workspace_id=workspace_id,
        campaign_id=body.campaign_id if "campaign_id" in body.model_fields_set else campaign_tagging_service._UNSET,
        pipeline_status=body.pipeline_status,
        db=db,
    )
    db.commit()
    lead = thread.lead
    return ThreadUpdateOut(
        thread_id=thread.thread_id,
        campaign_id=thread.campaign_id,
        pipeline_status=lead.pipeline_status if lead else None,
    )


# ---------------------------------------------------------------------------
# Reply
# ---------------------------------------------------------------------------


@router.post("/threads/{thread_id}/reply", response_model=ReplyOut, status_code=201)
def send_reply(
    workspace_id: str,
    thread_id: str,
    body: ReplyCreate,
    _: None = require_permission("manage_leads"),
    db: Session = Depends(get_db),
):
    """Compose and send a reply email from the Unibox reply composer."""
    message = reply_dispatch_service.send_reply(
        thread_id=thread_id,
        workspace_id=workspace_id,
        sender_account_id=body.sender_account_id,
        body_text=body.body_text,
        body_html=body.body_html,
        db=db,
    )
    db.commit()
    return _message_to_reply_out(message)


# ---------------------------------------------------------------------------
# Mark read
# ---------------------------------------------------------------------------


@router.patch(
    "/threads/{thread_id}/messages/{message_id}/read",
    response_model=MarkReadOut,
)
def mark_message_read(
    workspace_id: str,
    thread_id: str,
    message_id: str,
    body: MarkReadUpdate,
    _: None = require_permission("view_workspace"),
    db: Session = Depends(get_db),
):
    """Mark a single message as read or unread."""
    message = aggregation_service.mark_message_read(
        message_id=message_id,
        thread_id=thread_id,
        workspace_id=workspace_id,
        is_read=body.is_read,
        db=db,
    )
    db.commit()
    return MarkReadOut(message_id=message.message_id, is_read=message.is_read)


# ---------------------------------------------------------------------------
# Full-text search
# ---------------------------------------------------------------------------


@router.get("/search", response_model=SearchPaginatedResponse)
def search_messages(
    workspace_id: str,
    q: str = Query(..., min_length=1, description="Search query string"),
    inbox_id: Optional[str] = Query(None),
    campaign_id: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: None = require_permission("view_workspace"),
    db: Session = Depends(get_db),
):
    """Full-text search across all messages in the workspace."""
    total, items = search_service.search(
        workspace_id=workspace_id,
        query=q,
        sender_account_id=inbox_id,
        campaign_id=campaign_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
        db=db,
    )
    return SearchPaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[SearchResultItem(**item) for item in items],
    )


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _message_to_out(msg) -> MessageOut:
    return MessageOut(
        message_id=msg.message_id,
        direction=msg.direction,
        from_address=msg.from_address,
        to_addresses=msg.to_addresses or [],
        cc_addresses=msg.cc_addresses,
        subject=msg.subject,
        body_text=msg.body_text,
        body_html=msg.body_html,
        is_read=msg.is_read,
        is_orphan=msg.is_orphan,
        status=msg.status,
        received_at=msg.received_at,
        sent_at=msg.sent_at,
        created_at=msg.created_at,
    )


def _message_to_reply_out(msg) -> ReplyOut:
    return ReplyOut(
        message_id=msg.message_id,
        thread_id=msg.thread_id,
        direction=msg.direction,
        from_address=msg.from_address,
        to_addresses=msg.to_addresses or [],
        subject=msg.subject,
        body_text=msg.body_text,
        status=msg.status,
        sent_at=msg.sent_at,
        created_at=msg.created_at,
    )


def _thread_to_detail(thread, db) -> ThreadDetail:
    campaign = thread.campaign
    lead = thread.lead

    lead_out = None
    if lead:
        lead_out = LeadSummary(
            lead_id=lead.lead_id,
            first_name=lead.first_name,
            last_name=lead.last_name,
            email=lead.email,
            company_name=getattr(lead, "company_name", None),
            pipeline_status=lead.pipeline_status,
        )

    return ThreadDetail(
        thread_id=thread.thread_id,
        subject=thread.subject,
        campaign_id=thread.campaign_id,
        campaign_name=campaign.campaign_name if campaign else None,
        pipeline_status=lead.pipeline_status if lead else None,
        lead=lead_out,
        is_orphan=thread.is_orphan,
        created_at=thread.created_at,
        messages=[_message_to_out(m) for m in thread.messages],
    )

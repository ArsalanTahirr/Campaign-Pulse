"""
services/unibox/search_service.py — Full-text search across Unibox messages.

Uses PostgreSQL native to_tsvector / plainto_tsquery for FTS. The search_vector
column on unibox_message is pre-computed at insert time and indexed with a GIN
index, so searches are fast even with large message volumes.

The service layer is thin — it delegates to the repository and then converts
raw ORM objects to the dict shape expected by SearchPaginatedResponse.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app import repositories


def search(
    *,
    workspace_id: str,
    query: str,
    sender_account_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 25,
    db: Session,
) -> tuple[int, list[dict]]:
    """
    Full-text search across all UniboxMessages in the workspace.

    Parameters
    ----------
    workspace_id       : Scope the search to this workspace.
    query              : User-provided search string (passed to plainto_tsquery).
    sender_account_id  : Optional filter by inbox.
    campaign_id        : Optional filter by campaign.
    from_date          : Optional lower bound on created_at.
    to_date            : Optional upper bound on created_at.
    page               : 1-based page number.
    page_size          : Number of results per page (capped at 100).
    db                 : SQLAlchemy Session (read-only).

    Returns
    -------
    (total, items) where items are dicts matching SearchResultItem.
    """
    if not query or not query.strip():
        return 0, []

    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    total, messages = repositories.unibox_repository.search_messages(
        workspace_id=workspace_id,
        query=query.strip(),
        sender_account_id=sender_account_id,
        campaign_id=campaign_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
        db=db,
    )

    items = [_message_to_search_result(m) for m in messages]
    return total, items


def _message_to_search_result(message) -> dict:
    """Convert a UniboxMessage ORM object to a SearchResultItem dict."""
    thread = message.thread
    campaign = thread.campaign if thread else None
    sender_account = message.sender_account

    # Build a short snippet from the body_text (first 200 chars).
    snippet: Optional[str] = None
    if message.body_text:
        snippet = message.body_text[:200].strip()
        if len(message.body_text) > 200:
            snippet += "…"

    return {
        "message_id": message.message_id,
        "thread_id": message.thread_id,
        "thread_subject": thread.subject if thread else message.subject,
        "direction": message.direction,
        "from_address": message.from_address,
        "body_snippet": snippet,
        "received_at": message.received_at,
        "created_at": message.created_at,
        "campaign_id": thread.campaign_id if thread else None,
        "campaign_name": campaign.campaign_name if campaign else None,
        "inbox_email": sender_account.email if sender_account else "",
    }

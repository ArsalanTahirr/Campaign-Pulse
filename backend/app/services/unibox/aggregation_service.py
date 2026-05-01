"""
services/unibox/aggregation_service.py — Unified inbox aggregation and mark-read.

Provides the view-layer logic that sits between the repository and the router.
Handles:
  - Listing sender accounts as "inboxes" with unread counts.
  - Fetching the full detail of a single thread.
  - Marking individual messages as read/unread.
  - Routing filter combinations (all, pipeline status, campaign, inbox,
    unread-only, sent) to the correct repository query.

All DB mutations call flush(); the caller (router) commits.
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from app import repositories
from app.models import SenderAccount, UniboxMessage, UniboxThread


FilterView = Literal["all", "unread", "sent"]


def list_inboxes(workspace_id: str, db: Session) -> list[dict]:
    """
    Return all active SenderAccounts in the workspace enriched with the
    unread message count for each inbox.
    """
    accounts = (
        db.query(SenderAccount)
        .filter(
            SenderAccount.workspace_id == workspace_id,
            SenderAccount.deleted_at.is_(None),
        )
        .order_by(SenderAccount.email.asc())
        .all()
    )
    result = []
    for account in accounts:
        unread = repositories.unibox_repository.count_unread_for_sender_account(
            account.account_id, db
        )
        result.append(
            {
                "inbox_id": account.account_id,
                "email": account.email,
                "provider_type": account.provider_type,
                "status": account.status,
                "unread_count": unread,
            }
        )
    return result


def list_threads(
    *,
    workspace_id: str,
    view: FilterView = "all",
    pipeline_status: Optional[str] = None,
    campaign_id: Optional[str] = None,
    inbox_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    db: Session,
) -> tuple[int, list[dict]]:
    """
    Return a paginated list of thread summaries based on the active filter.

    Filter precedence (highest to lowest):
    1. pipeline_status  → list_threads_for_pipeline
    2. campaign_id      → list_threads_for_campaign
    3. inbox_id         → list_threads_for_inbox
    4. view == 'unread' → list_threads_unread
    5. view == 'sent'   → list_sent_messages
    6. default          → list_threads_all

    Returns (total, items) where items are dicts matching ThreadSummary.
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 100)  # cap at 100 per page

    if pipeline_status:
        return repositories.unibox_repository.list_threads_for_pipeline(
            workspace_id, pipeline_status, page, page_size, db
        )
    if campaign_id:
        return repositories.unibox_repository.list_threads_for_campaign(
            workspace_id, campaign_id, page, page_size, db
        )
    if inbox_id:
        return repositories.unibox_repository.list_threads_for_inbox(
            workspace_id, inbox_id, page, page_size, db
        )
    if view == "unread":
        return repositories.unibox_repository.list_threads_unread(
            workspace_id, page, page_size, db
        )
    if view == "sent":
        return repositories.unibox_repository.list_sent_messages(
            workspace_id, page, page_size, db
        )
    return repositories.unibox_repository.list_threads_all(
        workspace_id, page, page_size, db
    )


def get_thread_detail(thread_id: str, workspace_id: str, db: Session) -> UniboxThread:
    """
    Return the full UniboxThread with its messages loaded, or raise 404.
    Also marks all inbound messages as read on the first open.
    """
    thread = repositories.unibox_repository.get_thread_by_id(thread_id, workspace_id, db)
    if thread is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found.",
        )
    # Auto-mark all inbound messages as read when the thread is opened.
    _mark_all_read(thread, db)
    return thread


def mark_message_read(
    *,
    message_id: str,
    thread_id: str,
    workspace_id: str,
    is_read: bool,
    db: Session,
) -> UniboxMessage:
    """
    Set is_read on a single message.  Validates workspace membership via
    the parent thread before updating.

    Returns the updated UniboxMessage.
    """
    # Validate that thread belongs to workspace.
    thread = repositories.unibox_repository.get_thread_by_id(thread_id, workspace_id, db)
    if thread is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found.",
        )

    message = repositories.unibox_repository.get_message_by_id(message_id, db)
    if message is None or message.thread_id != thread_id:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found in thread {thread_id}.",
        )

    message.is_read = is_read
    db.flush()
    return message


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _mark_all_read(thread: UniboxThread, db: Session) -> None:
    """Mark all inbound messages in the thread as read (batch update)."""
    db.query(UniboxMessage).filter(
        UniboxMessage.thread_id == thread.thread_id,
        UniboxMessage.direction == "inbound",
        UniboxMessage.is_read.is_(False),
    ).update({"is_read": True})
    db.flush()

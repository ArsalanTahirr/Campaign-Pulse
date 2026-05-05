"""
repositories/unibox_repository.py — All database access for UniboxThread and
UniboxMessage.  No business logic lives here; this layer is purely about
translating between the application's data-access needs and SQL.

All public functions accept a SQLAlchemy Session and return ORM objects or
scalars.  Callers are responsible for committing or rolling back transactions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Campaign,
    Lead,
    SenderAccount,
    UniboxMessage,
    UniboxThread,
)


# ---------------------------------------------------------------------------
# UniboxThread queries
# ---------------------------------------------------------------------------


def get_thread_by_id(thread_id: str, workspace_id: str, db: Session) -> Optional[UniboxThread]:
    """
    Return the thread with the given ID scoped to the workspace, or None.
    Eagerly loads messages, lead, and campaign for the detail view.
    """
    return (
        db.query(UniboxThread)
        .options(
            joinedload(UniboxThread.messages),
            joinedload(UniboxThread.lead),
            joinedload(UniboxThread.campaign),
        )
        .filter(
            UniboxThread.thread_id == thread_id,
            UniboxThread.workspace_id == workspace_id,
        )
        .first()
    )


def find_thread_by_message_id_header(
    message_id_header: str, workspace_id: str, db: Session
) -> Optional[UniboxThread]:
    """
    Find an existing thread that contains a message with the given
    RFC 2822 Message-ID header.  Used by ThreadingService to detect
    if a reply belongs to an existing conversation.
    """
    return (
        db.query(UniboxThread)
        .join(UniboxMessage, UniboxMessage.thread_id == UniboxThread.thread_id)
        .filter(
            UniboxMessage.message_id_header == message_id_header,
            UniboxThread.workspace_id == workspace_id,
        )
        .first()
    )


def list_threads_for_pipeline(
    workspace_id: str,
    pipeline_status: str,
    page: int,
    page_size: int,
    db: Session,
) -> tuple[int, list[dict]]:
    """
    Return threads where the linked lead has the given pipeline_status,
    ordered by last_message_at DESC.  Returns (total, rows).
    """
    base = (
        db.query(UniboxThread, Lead, SenderAccount, Campaign)
        .join(Lead, Lead.lead_id == UniboxThread.lead_id)
        .join(
            SenderAccount,
            SenderAccount.account_id == db.query(UniboxMessage.sender_account_id)
            .filter(UniboxMessage.thread_id == UniboxThread.thread_id)
            .order_by(UniboxMessage.created_at.asc())
            .limit(1)
            .scalar_subquery(),
        )
        .outerjoin(Campaign, Campaign.campaign_id == UniboxThread.campaign_id)
        .filter(
            UniboxThread.workspace_id == workspace_id,
            UniboxThread.is_orphan.is_(False),
            Lead.pipeline_status == pipeline_status,
        )
        .order_by(UniboxThread.last_message_at.desc())
    )
    total = base.count()
    rows = base.offset((page - 1) * page_size).limit(page_size).all()
    return total, _rows_to_dicts(rows, db)


def list_threads_for_campaign(
    workspace_id: str,
    campaign_id: str,
    page: int,
    page_size: int,
    db: Session,
) -> tuple[int, list[dict]]:
    """Return threads tagged with the given campaign, ordered by recency."""
    base = (
        db.query(UniboxThread, Lead, SenderAccount, Campaign)
        .outerjoin(Lead, Lead.lead_id == UniboxThread.lead_id)
        .join(
            SenderAccount,
            SenderAccount.account_id == db.query(UniboxMessage.sender_account_id)
            .filter(UniboxMessage.thread_id == UniboxThread.thread_id)
            .order_by(UniboxMessage.created_at.asc())
            .limit(1)
            .scalar_subquery(),
        )
        .outerjoin(Campaign, Campaign.campaign_id == UniboxThread.campaign_id)
        .filter(
            UniboxThread.workspace_id == workspace_id,
            UniboxThread.campaign_id == campaign_id,
        )
        .order_by(UniboxThread.last_message_at.desc())
    )
    total = base.count()
    rows = base.offset((page - 1) * page_size).limit(page_size).all()
    return total, _rows_to_dicts(rows, db)


def list_threads_for_inbox(
    workspace_id: str,
    sender_account_id: str,
    page: int,
    page_size: int,
    db: Session,
) -> tuple[int, list[dict]]:
    """Return threads that have at least one message through the given inbox."""
    thread_ids_sq = (
        db.query(UniboxMessage.thread_id)
        .filter(UniboxMessage.sender_account_id == sender_account_id)
        .distinct()
        .subquery()
    )
    base = (
        db.query(UniboxThread, Lead, SenderAccount, Campaign)
        .outerjoin(Lead, Lead.lead_id == UniboxThread.lead_id)
        .join(
            SenderAccount,
            SenderAccount.account_id == db.query(UniboxMessage.sender_account_id)
            .filter(UniboxMessage.thread_id == UniboxThread.thread_id)
            .order_by(UniboxMessage.created_at.asc())
            .limit(1)
            .scalar_subquery(),
        )
        .outerjoin(Campaign, Campaign.campaign_id == UniboxThread.campaign_id)
        .filter(
            UniboxThread.workspace_id == workspace_id,
            UniboxThread.thread_id.in_(thread_ids_sq),
        )
        .order_by(UniboxThread.last_message_at.desc())
    )
    total = base.count()
    rows = base.offset((page - 1) * page_size).limit(page_size).all()
    return total, _rows_to_dicts(rows, db)


def list_threads_all(
    workspace_id: str,
    page: int,
    page_size: int,
    db: Session,
) -> tuple[int, list[dict]]:
    """Return all threads in the workspace ordered by recency."""
    base = (
        db.query(UniboxThread, Lead, SenderAccount, Campaign)
        .outerjoin(Lead, Lead.lead_id == UniboxThread.lead_id)
        .join(
            SenderAccount,
            SenderAccount.account_id == db.query(UniboxMessage.sender_account_id)
            .filter(UniboxMessage.thread_id == UniboxThread.thread_id)
            .order_by(UniboxMessage.created_at.asc())
            .limit(1)
            .scalar_subquery(),
        )
        .outerjoin(Campaign, Campaign.campaign_id == UniboxThread.campaign_id)
        .filter(UniboxThread.workspace_id == workspace_id)
        .order_by(UniboxThread.last_message_at.desc())
    )
    total = base.count()
    rows = base.offset((page - 1) * page_size).limit(page_size).all()
    return total, _rows_to_dicts(rows, db)


def list_threads_unread(
    workspace_id: str,
    page: int,
    page_size: int,
    db: Session,
) -> tuple[int, list[dict]]:
    """Return threads that have at least one unread message."""
    unread_thread_ids_sq = (
        db.query(UniboxMessage.thread_id)
        .filter(UniboxMessage.is_read.is_(False))
        .distinct()
        .subquery()
        .element
    )
    base = (
        db.query(UniboxThread, Lead, SenderAccount, Campaign)
        .outerjoin(Lead, Lead.lead_id == UniboxThread.lead_id)
        .join(
            SenderAccount,
            SenderAccount.account_id == db.query(UniboxMessage.sender_account_id)
            .filter(UniboxMessage.thread_id == UniboxThread.thread_id)
            .order_by(UniboxMessage.created_at.asc())
            .limit(1)
            .scalar_subquery(),
        )
        .outerjoin(Campaign, Campaign.campaign_id == UniboxThread.campaign_id)
        .filter(
            UniboxThread.workspace_id == workspace_id,
            UniboxThread.thread_id.in_(unread_thread_ids_sq),
        )
        .order_by(UniboxThread.last_message_at.desc())
    )
    total = base.count()
    rows = base.offset((page - 1) * page_size).limit(page_size).all()
    return total, _rows_to_dicts(rows, db)


def list_sent_messages(
    workspace_id: str,
    page: int,
    page_size: int,
    db: Session,
) -> tuple[int, list[dict]]:
    """Return threads that contain at least one outbound message."""
    sent_thread_ids_sq = (
        db.query(UniboxMessage.thread_id)
        .filter(UniboxMessage.direction == "outbound")
        .distinct()
        .subquery()
        .element
    )
    base = (
        db.query(UniboxThread, Lead, SenderAccount, Campaign)
        .outerjoin(Lead, Lead.lead_id == UniboxThread.lead_id)
        .join(
            SenderAccount,
            SenderAccount.account_id == db.query(UniboxMessage.sender_account_id)
            .filter(UniboxMessage.thread_id == UniboxThread.thread_id)
            .order_by(UniboxMessage.created_at.asc())
            .limit(1)
            .scalar_subquery(),
        )
        .outerjoin(Campaign, Campaign.campaign_id == UniboxThread.campaign_id)
        .filter(
            UniboxThread.workspace_id == workspace_id,
            UniboxThread.thread_id.in_(sent_thread_ids_sq),
        )
        .order_by(UniboxThread.last_message_at.desc())
    )
    total = base.count()
    rows = base.offset((page - 1) * page_size).limit(page_size).all()
    return total, _rows_to_dicts(rows, db)


# ---------------------------------------------------------------------------
# UniboxMessage queries
# ---------------------------------------------------------------------------


def get_message_by_id(message_id: str, db: Session) -> Optional[UniboxMessage]:
    """Return a message by its PK, or None."""
    return db.query(UniboxMessage).filter(UniboxMessage.message_id == message_id).first()


def message_exists_by_header(message_id_header: str, db: Session) -> bool:
    """Return True if a message with the given RFC 2822 Message-ID already exists."""
    return (
        db.query(UniboxMessage.message_id)
        .filter(UniboxMessage.message_id_header == message_id_header)
        .first()
        is not None
    )


def get_messages_for_thread(thread_id: str, db: Session) -> list[UniboxMessage]:
    """Return all messages for a thread ordered chronologically."""
    return (
        db.query(UniboxMessage)
        .filter(UniboxMessage.thread_id == thread_id)
        .order_by(UniboxMessage.created_at.asc())
        .all()
    )


def count_unread_for_thread(thread_id: str, db: Session) -> int:
    """Return the number of unread messages in a thread."""
    return (
        db.query(func.count(UniboxMessage.message_id))
        .filter(
            UniboxMessage.thread_id == thread_id,
            UniboxMessage.is_read.is_(False),
        )
        .scalar()
        or 0
    )


def count_unread_for_sender_account(sender_account_id: str, db: Session) -> int:
    """Return total unread inbound message count for a given inbox."""
    return (
        db.query(func.count(UniboxMessage.message_id))
        .filter(
            UniboxMessage.sender_account_id == sender_account_id,
            UniboxMessage.is_read.is_(False),
            UniboxMessage.direction == "inbound",
        )
        .scalar()
        or 0
    )


def search_messages(
    workspace_id: str,
    query: str,
    sender_account_id: Optional[str],
    campaign_id: Optional[str],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    page: int,
    page_size: int,
    db: Session,
) -> tuple[int, list[UniboxMessage]]:
    """
    Full-text search across unibox_message.search_vector using PostgreSQL FTS.
    Returns (total, messages) where messages include their parent thread.
    """
    tsquery = func.plainto_tsquery(text("'english'"), query)

    base = (
        db.query(UniboxMessage)
        .join(UniboxThread, UniboxThread.thread_id == UniboxMessage.thread_id)
        .options(joinedload(UniboxMessage.thread).joinedload(UniboxThread.campaign))
        .options(joinedload(UniboxMessage.sender_account))
        .filter(
            UniboxThread.workspace_id == workspace_id,
            UniboxMessage.search_vector.op("@@")(tsquery),
        )
    )

    if sender_account_id:
        base = base.filter(UniboxMessage.sender_account_id == sender_account_id)
    if campaign_id:
        base = base.filter(UniboxThread.campaign_id == campaign_id)
    if from_date:
        base = base.filter(UniboxMessage.created_at >= from_date)
    if to_date:
        base = base.filter(UniboxMessage.created_at <= to_date)

    base = base.order_by(
        func.ts_rank(UniboxMessage.search_vector, tsquery).desc(),
        UniboxMessage.created_at.desc(),
    )

    total = base.count()
    messages = base.offset((page - 1) * page_size).limit(page_size).all()
    return total, messages


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------


def create_thread(thread: UniboxThread, db: Session) -> UniboxThread:
    """Persist a new UniboxThread and flush to get server defaults."""
    db.add(thread)
    db.flush()
    return thread


def create_message(message: UniboxMessage, db: Session) -> UniboxMessage:
    """Persist a new UniboxMessage and flush to get server defaults."""
    db.add(message)
    db.flush()
    return message


def update_thread_last_message_at(
    thread_id: str, ts: datetime, db: Session
) -> None:
    """Update last_message_at on the thread to reflect the newest message."""
    db.query(UniboxThread).filter(UniboxThread.thread_id == thread_id).update(
        {"last_message_at": ts}
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _rows_to_dicts(
    rows: list[tuple[UniboxThread, Lead | None, SenderAccount, Campaign | None]],
    db: Session,
) -> list[dict]:
    """
    Convert raw ORM row tuples (thread, lead, sender_account, campaign) to
    plain dicts matching the ThreadSummary schema shape.
    """
    result = []
    for thread, lead, sender_account, campaign in rows:
        unread = count_unread_for_thread(thread.thread_id, db)
        # is_read at thread level: True only when ALL messages are read.
        is_read = unread == 0
        contact_name = (
            f"{lead.first_name or ''} {lead.last_name or ''}".strip()
            if lead
            else thread.subject
        )
        contact_email = lead.email if lead else "unknown"
        result.append(
            {
                "thread_id": thread.thread_id,
                "subject": thread.subject,
                "contact_name": contact_name or "Unknown",
                "contact_email": contact_email,
                "last_message_at": thread.last_message_at,
                "is_read": is_read,
                "is_orphan": thread.is_orphan,
                "pipeline_status": lead.pipeline_status if lead else None,
                "campaign_id": thread.campaign_id,
                "campaign_name": campaign.campaign_name if campaign else None,
                "inbox_id": sender_account.account_id,
                "inbox_email": sender_account.email,
                "unread_count": unread,
            }
        )
    return result

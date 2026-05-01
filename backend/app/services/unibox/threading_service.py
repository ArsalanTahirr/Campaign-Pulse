"""
services/unibox/threading_service.py — Resolve which UniboxThread a new
inbound or outbound message belongs to, using RFC 2822 threading headers.

Threading algorithm
───────────────────
When a new message arrives (inbound or outbound) we:

1. If the message carries In-Reply-To or References headers, check whether any
   existing message in the workspace already has one of those Message-ID values
   in its message_id_header column.  If found, the new message joins that
   existing thread.

2. If no match is found, create a new UniboxThread for this message.

The algorithm deliberately does NOT rely on subject-line matching.  RFC 2822
header-based threading is precise and avoids false-positive groupings.

All DB mutations (flush only, no commit) are delegated to the repository.
The caller is responsible for committing the session.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app import repositories
from app.models import UniboxThread


def resolve_or_create_thread(
    *,
    workspace_id: str,
    subject: str,
    lead_id: Optional[str],
    campaign_id: Optional[str],
    is_orphan: bool,
    in_reply_to: Optional[str],
    references_header: Optional[str],
    db: Session,
) -> UniboxThread:
    """
    Return the existing thread this message belongs to, or create a new one.

    Parameters
    ----------
    workspace_id   : Workspace the message arrived in.
    subject        : The email subject line (used if we create a new thread).
    lead_id        : FK to Lead — None for orphan messages.
    campaign_id    : FK to Campaign — None if not yet tagged.
    is_orphan      : True when no matching lead exists for the sender.
    in_reply_to    : Value of the RFC 2822 In-Reply-To header (may be None).
    references_header : Value of the RFC 2822 References header (may be None).
    db             : SQLAlchemy Session (not committed here).

    Returns
    -------
    UniboxThread — either an existing thread or a newly flushed thread.
    """
    thread = _find_existing_thread(
        workspace_id=workspace_id,
        in_reply_to=in_reply_to,
        references_header=references_header,
        db=db,
    )

    if thread is not None:
        # Update thread metadata if richer information has arrived.
        # E.g. a reply that finally identifies the lead.
        _maybe_upgrade_thread(
            thread=thread,
            lead_id=lead_id,
            campaign_id=campaign_id,
            is_orphan=is_orphan,
            db=db,
        )
        return thread

    # No existing thread found — create one.
    return _create_thread(
        workspace_id=workspace_id,
        subject=_strip_re_prefix(subject),
        lead_id=lead_id,
        campaign_id=campaign_id,
        is_orphan=is_orphan,
        db=db,
    )


def _find_existing_thread(
    *,
    workspace_id: str,
    in_reply_to: Optional[str],
    references_header: Optional[str],
    db: Session,
) -> Optional[UniboxThread]:
    """
    Search for an existing thread by looking up any of the Message-ID values
    present in the In-Reply-To and References headers.

    We check In-Reply-To first (immediate parent), then iterate over
    References (ancestor chain) from right to left (most recent first).
    """
    candidates: list[str] = []

    if in_reply_to:
        candidates.append(in_reply_to.strip())

    if references_header:
        # References is a whitespace-separated list of Message-IDs.
        for mid in reversed(references_header.split()):
            mid = mid.strip()
            if mid and mid not in candidates:
                candidates.append(mid)

    for candidate_mid in candidates:
        thread = repositories.unibox_repository.find_thread_by_message_id_header(
            message_id_header=candidate_mid,
            workspace_id=workspace_id,
            db=db,
        )
        if thread is not None:
            return thread

    return None


def _create_thread(
    *,
    workspace_id: str,
    subject: str,
    lead_id: Optional[str],
    campaign_id: Optional[str],
    is_orphan: bool,
    db: Session,
) -> UniboxThread:
    """Instantiate and flush a new UniboxThread."""
    now = datetime.now(timezone.utc)
    thread = UniboxThread(
        workspace_id=workspace_id,
        lead_id=lead_id,
        campaign_id=campaign_id,
        subject=subject or "(no subject)",
        last_message_at=now,
        is_orphan=is_orphan,
    )
    return repositories.unibox_repository.create_thread(thread, db)


def _maybe_upgrade_thread(
    *,
    thread: UniboxThread,
    lead_id: Optional[str],
    campaign_id: Optional[str],
    is_orphan: bool,
    db: Session,
) -> None:
    """
    If the incoming message provides lead or campaign info that the existing
    thread lacks, update the thread in place (still not committed here).
    """
    changed = False

    # An orphan thread that now has a matching lead — upgrade it.
    if thread.is_orphan and not is_orphan and lead_id is not None:
        thread.is_orphan = False
        thread.lead_id = lead_id
        changed = True

    if thread.campaign_id is None and campaign_id is not None:
        thread.campaign_id = campaign_id
        changed = True

    if changed:
        db.flush()


def _strip_re_prefix(subject: str) -> str:
    """Remove leading Re:, RE:, Fwd:, FWD: prefixes for cleaner thread subjects."""
    import re
    return re.sub(r"^(Re|RE|Fwd|FWD|Fw|FW)\s*:\s*", "", subject, flags=re.IGNORECASE).strip()

"""
services/unibox/ingestion_service.py — Ingest inbound emails from IMAP into the
Unibox (UniboxThread + UniboxMessage tables).

This service is called by the extended imap_reply_loop in engine_loops.py once
per SenderAccount per poll cycle.  It replaces (and supersedes) the lightweight
FROM-header-only logic previously inside run_imap_reply_iteration — the old path
still fires EmailEvent('replied') records for campaign tracking, while this new
path stores full message content for the Unibox.

Responsibilities
────────────────
1. Fetch all new UIDs from the IMAP server (start_uid onwards).
2. Download the full RFC 822 payload for each UID.
3. Parse headers (Message-ID, In-Reply-To, References, From, To, CC, Subject,
   Date) and body (plain-text and HTML alternatives).
4. Deduplicate by message_id_header — skip if already ingested.
5. Resolve lead and campaign by matching From address against Lead.email
   within the workspace.
6. Delegate thread resolution to ThreadingService.
7. Persist UniboxMessage; build search_vector.
8. Update SenderAccount.last_imap_uid.

All DB mutations call flush() not commit() — the caller (engine loop) commits
after each account's batch.

Idempotency: if the same Message-ID is fetched twice, the second call is a
no-op (checked via repository.message_exists_by_header).
"""

from __future__ import annotations

import email
import imaplib
import uuid
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app import repositories
from app.models import (
    EmailEvent,
    Lead,
    SenderAccount,
    UniboxMessage,
)
from app.services.unibox import threading_service


def ingest_account(account: SenderAccount, db: Session) -> int:
    """
    Poll one SenderAccount's IMAP inbox and ingest all new messages.

    Returns the number of new messages ingested (0 if nothing new or on
    error — errors are swallowed so a single bad account doesn't halt the
    loop).
    """
    if not _is_imap_configured(account):
        return 0

    try:
        with imaplib.IMAP4_SSL(account.imap_host, int(account.imap_port)) as client:
            client.login(account.email, account.app_password)
            client.select("INBOX")
            ingested = _process_inbox(account, client, db)
        return ingested
    except Exception:
        db.rollback()
        return 0


def _is_imap_configured(account: SenderAccount) -> bool:
    return bool(
        account.imap_host
        and account.imap_port
        and account.app_password
        and account.status in ("active", "warming_up")
        and not account.deleted_at
    )


def _process_inbox(
    account: SenderAccount, client: imaplib.IMAP4_SSL, db: Session
) -> int:
    start_uid = int(account.last_imap_uid or 0) + 1
    status_value, data = client.uid("SEARCH", None, f"UID {start_uid}:*")
    if status_value != "OK":
        return 0

    uid_strings = [u.decode() for u in (data[0] or b"").split()]
    max_fetch = int(getattr(account, "max_imap_fetch", None) or 100)
    uid_strings = uid_strings[:max_fetch]

    max_seen_uid = int(account.last_imap_uid or 0)
    ingested = 0

    for uid in uid_strings:
        try:
            count = _ingest_one_uid(uid, account, client, db)
            ingested += count
        except Exception:
            db.rollback()
        max_seen_uid = max(max_seen_uid, int(uid))

    account.last_imap_uid = max_seen_uid or account.last_imap_uid
    db.flush()
    db.commit()
    return ingested


def _ingest_one_uid(
    uid: str,
    account: SenderAccount,
    client: imaplib.IMAP4_SSL,
    db: Session,
) -> int:
    """Download, parse, and persist one IMAP message. Returns 1 if ingested, 0 if skipped."""
    status_fetch, msg_data = client.uid("FETCH", uid, "(RFC822)")
    if status_fetch != "OK" or not msg_data:
        return 0

    raw_bytes = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
    if not raw_bytes:
        return 0

    msg = email.message_from_bytes(raw_bytes)

    # --- Extract headers ---
    message_id_header = (msg.get("Message-ID") or "").strip()
    if not message_id_header:
        # Synthesise a stable synthetic ID from uid + account so we can
        # still ingest messages that are missing the header.
        message_id_header = f"<synthetic-{uid}-{account.account_id}@campaignpulse.local>"

    # Idempotency check.
    if repositories.unibox_repository.message_exists_by_header(message_id_header, db):
        return 0

    in_reply_to = (msg.get("In-Reply-To") or "").strip() or None
    references_header = (msg.get("References") or "").strip() or None
    subject = _decode_header(msg.get("Subject", "")) or "(no subject)"

    from_raw = msg.get("From", "")
    from_address = parseaddr(from_raw)[1].lower() or from_raw

    to_addresses = _parse_address_list(msg.get("To", ""))
    cc_addresses = _parse_address_list(msg.get("CC", "")) or None

    received_at = _parse_date(msg.get("Date")) or datetime.now(timezone.utc)

    # --- Resolve lead and campaign ---
    lead, campaign_id = _resolve_lead_and_campaign(from_address, account.workspace_id, db)
    is_orphan = lead is None
    lead_id = lead.lead_id if lead else None

    # --- Resolve or create thread ---
    thread = threading_service.resolve_or_create_thread(
        workspace_id=account.workspace_id,
        subject=subject,
        lead_id=lead_id,
        campaign_id=campaign_id,
        is_orphan=is_orphan,
        in_reply_to=in_reply_to,
        references_header=references_header,
        db=db,
    )

    # --- Parse body ---
    body_text, body_html = _extract_body(msg)

    # --- Build search vector ---
    search_vector = _build_search_vector(subject, body_text, from_address, db)

    # --- Persist message ---
    message = UniboxMessage(
        thread_id=thread.thread_id,
        sender_account_id=account.account_id,
        lead_id=lead_id,
        email_event_id=None,
        direction="inbound",
        message_id_header=message_id_header,
        in_reply_to=in_reply_to,
        references_header=references_header,
        from_address=from_address,
        to_addresses=to_addresses,
        cc_addresses=cc_addresses,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        is_read=False,
        is_orphan=is_orphan,
        status="received",
        received_at=received_at,
        search_vector=search_vector,
    )
    repositories.unibox_repository.create_message(message, db)

    # Update thread's last_message_at.
    repositories.unibox_repository.update_thread_last_message_at(
        thread.thread_id, received_at, db
    )

    # If the sender is a known lead, also fire an EmailEvent('replied') so
    # that existing campaign analytics continue to work.
    if lead is not None:
        _maybe_fire_reply_event(lead, account, uid, db)

    return 1


def _resolve_lead_and_campaign(
    from_address: str, workspace_id: str, db: Session
) -> tuple[Optional[Lead], Optional[str]]:
    """
    Find a Lead in the workspace whose email matches the from_address.
    Returns (lead, campaign_id) or (None, None) for orphan messages.
    """
    lead = (
        db.query(Lead)
        .join(Lead.campaign)
        .filter(
            Lead.campaign.has(workspace_id=workspace_id),
            func.lower(Lead.email) == from_address.lower(),
        )
        .order_by(Lead.created_at.desc())
        .first()
    )
    if lead is None:
        return None, None
    return lead, lead.campaign_id


def _maybe_fire_reply_event(
    lead: Lead, account: SenderAccount, uid: str, db: Session
) -> None:
    """
    Create an EmailEvent('replied') for known-lead replies so that campaign
    analytics (reply rate, etc.) remain accurate.

    Only fires if a 'replied' event for this lead+account has not already been
    recorded within the last hour (to avoid double-counting on re-polls).
    """
    from datetime import timedelta

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = (
        db.query(EmailEvent.event_id)
        .filter(
            EmailEvent.lead_id == lead.lead_id,
            EmailEvent.event_type == "replied",
            EmailEvent.sender_account_id == account.account_id,
            EmailEvent.occurred_at >= one_hour_ago,
            EmailEvent.event_metadata["imap_uid"].astext == uid,
        )
        .first()
    )
    if recent:
        return

    db.add(
        EmailEvent(
            lead_id=lead.lead_id,
            event_type="replied",
            event_scope="lead",
            sender_account_id=account.account_id,
            occurred_at=datetime.now(timezone.utc),
            event_metadata={"imap_uid": uid},
        )
    )
    lead.lead_status = "replied"
    lead.delivery_state = "paused"
    db.flush()


# ---------------------------------------------------------------------------
# IMAP / email parsing helpers
# ---------------------------------------------------------------------------


def _decode_header(raw: str) -> str:
    """Decode RFC 2047-encoded email header values into a plain string."""
    from email.header import decode_header
    parts = decode_header(raw)
    decoded_parts = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded_parts.append(part)
    return "".join(decoded_parts).strip()


def _parse_address_list(raw: str) -> list[str]:
    """Parse a comma-separated address list into a list of bare email addresses."""
    if not raw:
        return []
    addresses = []
    for part in raw.split(","):
        addr = parseaddr(part.strip())[1].lower()
        if addr:
            addresses.append(addr)
    return addresses or [raw.strip()]


def _parse_date(raw: Optional[str]) -> Optional[datetime]:
    """Parse the Date header to a timezone-aware datetime, or return None."""
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _extract_body(msg: email.message.Message) -> tuple[Optional[str], Optional[str]]:
    """
    Walk the MIME structure and extract plain-text and HTML parts.
    Returns (body_text, body_html).
    """
    body_text: Optional[str] = None
    body_html: Optional[str] = None

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition") or "")
            if "attachment" in cd:
                continue
            if ct == "text/plain" and body_text is None:
                body_text = _decode_payload(part)
            elif ct == "text/html" and body_html is None:
                body_html = _decode_payload(part)
    else:
        ct = msg.get_content_type()
        if ct == "text/plain":
            body_text = _decode_payload(msg)
        elif ct == "text/html":
            body_html = _decode_payload(msg)

    return body_text, body_html


def _decode_payload(part: email.message.Message) -> Optional[str]:
    """Decode a message part payload to a Unicode string."""
    payload = part.get_payload(decode=True)
    if not isinstance(payload, bytes):
        return None
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _build_search_vector(
    subject: str,
    body_text: Optional[str],
    from_address: str,
    db: Session,
) -> object:
    """
    Compute a PostgreSQL tsvector from subject + body_text + from_address.
    Executed as a scalar SQL expression so the DB handles the NLP.
    """
    combined = (
        (subject or "")
        + " "
        + (body_text or "")
        + " "
        + (from_address or "")
    )
    result = db.execute(
        text("SELECT to_tsvector('english', :content)"),
        {"content": combined},
    ).scalar()
    return result

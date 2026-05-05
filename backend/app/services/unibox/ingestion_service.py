"""
services/unibox/ingestion_service.py — Ingest inbound emails from IMAP into the
Unibox (UniboxThread + UniboxMessage tables).

This service is called by the extended imap_reply_loop in engine_loops.py once
per SenderAccount per poll cycle (often in parallel across accounts). It is the
single source of truth for both Unibox persistence and EmailEvent('replied')
rows for inbound lead mail.

Responsibilities
────────────────
1. Fetch all new UIDs from the IMAP server (start_uid onwards).
2. Batch-fetch small HEADER.FIELDS slices per UID; skip full RFC822 download when
   From is not a workspace lead (or Message-ID already ingested).
3. Download full RFC 822 only for candidate lead messages.
4. Parse headers (Message-ID, In-Reply-To, References, From, To, CC, Subject,
   Date) and body (plain-text and HTML alternatives).
5. Deduplicate by message_id_header — skip if already ingested.
6. Resolve lead and campaign by matching From address against Lead.email
   within the workspace.
7. **If From does not match any lead in the workspace, skip persistence** (do not
   store newsletters, social alerts, etc. in Unibox). The IMAP UID cursor still
   advances so those messages are not re-fetched forever.
8. Delegate thread resolution to ThreadingService.
9. Persist UniboxMessage; build search_vector.
10. Update SenderAccount.last_imap_uid.

All DB mutations call flush() not commit() — the caller (engine loop) commits
after each account's batch.

Idempotency: if the same Message-ID is fetched twice, the second call is a
no-op (checked via repository.message_exists_by_header).
"""

from __future__ import annotations

import email
import imaplib
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session, joinedload

from app import repositories
from app.models import (
    Campaign,
    EmailEvent,
    Lead,
    SenderAccount,
    UniboxMessage,
)
from app.services.unibox import threading_service


def ingest_account(account: SenderAccount, db: Session) -> tuple[int, int]:
    """
    Poll one SenderAccount's IMAP inbox and ingest all new messages.

    Returns (messages_ingested, reply_events_recorded). On error returns (0, 0).
    """
    if not _is_imap_configured(account):
        return 0, 0

    try:
        from app.services import sending_engine_service as _ses

        with imaplib.IMAP4_SSL(
            account.imap_host, int(account.imap_port), timeout=_ses.IMAP_SOCKET_TIMEOUT
        ) as client:
            client.login(account.email, account.app_password)
            if account.warmup_settings and getattr(
                account.warmup_settings, "is_warmup_active", False
            ):
                pool = _ses.load_global_warmup_pool(db)
                peers = _ses.global_warmup_peer_emails_lower(pool)
                _ses._imap_rescue_warmup_spam_on_client(client, account, peers)
            client.select("INBOX")
            ingested, replies = _process_inbox(account, client, db)
        return ingested, replies
    except Exception:
        db.rollback()
        return 0, 0


_IMAP_ACCOUNT_PARALLEL_MAX = int(os.environ.get("IMAP_ACCOUNT_PARALLEL_MAX", "6"))


def ingest_account_by_id(account_id: str) -> tuple[int, int]:
    """
    Load a sender by id in a fresh Session and run ingest_account.
    Used by parallel IMAP workers (each thread must use its own DB session).
    """
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        acc = (
            db.query(SenderAccount)
            .options(joinedload(SenderAccount.warmup_settings))
            .filter(SenderAccount.account_id == account_id)
            .first()
        )
        if not acc:
            return 0, 0
        return ingest_account(acc, db)
    except Exception:
        db.rollback()
        return 0, 0
    finally:
        db.close()


def ingest_accounts_parallel(account_ids: list[str]) -> tuple[int, int]:
    """Run ingest_account across many senders with a thread pool (isolated sessions)."""
    if not account_ids:
        return 0, 0
    n_workers = max(1, min(_IMAP_ACCOUNT_PARALLEL_MAX, len(account_ids)))
    if n_workers == 1:
        ti, tr = 0, 0
        for aid in account_ids:
            i, r = ingest_account_by_id(aid)
            ti += i
            tr += r
        return ti, tr
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        parts = list(pool.map(ingest_account_by_id, account_ids))
    return sum(p[0] for p in parts), sum(p[1] for p in parts)


def _is_imap_configured(account: SenderAccount) -> bool:
    return bool(
        account.imap_host
        and account.imap_port
        and account.app_password
        and account.status in ("active", "warming_up")
        and not account.deleted_at
    )


def _workspace_lead_emails_lower(workspace_id: str, db: Session) -> set[str]:
    """Lowercased lead emails for all campaigns in the workspace (for IMAP pre-filter)."""
    rows = (
        db.query(func.lower(Lead.email))
        .join(Campaign, Campaign.campaign_id == Lead.campaign_id)
        .filter(Campaign.workspace_id == workspace_id)
        .distinct()
        .all()
    )
    return {str(em).lower() for (em,) in rows if em}


def _message_from_header_fields_bytes(blob: bytes) -> email.message.Message:
    """Parse IMAP BODY.PEEK[HEADER.FIELDS (...)] payload into a header-only Message."""
    raw = blob.strip()
    if not raw:
        return email.message_from_bytes(b"From: \r\n\r\n")
    if b"\r\n\r\n" not in raw:
        raw = raw + b"\r\n\r\n"
    return email.message_from_bytes(raw)


def _from_address_from_header_fetch_blob(blob: bytes) -> str:
    """
    Extract the first mailbox address from a HEADER.FIELDS blob, including
    RFC822 folded ``From:`` continuation lines (some mobile clients use these).
    """
    text = blob.decode("utf-8", errors="ignore")
    lines = text.splitlines()
    parts: list[str] = []
    in_from = False
    for line in lines:
        if line[:5].lower() == "from:":
            in_from = True
            parts.append(line[5:].strip())
        elif in_from and line and line[0] in " \t":
            parts.append(line.strip())
        elif in_from:
            break
    if parts:
        combined = " ".join(parts)
        return (parseaddr(combined)[1] or "").strip().lower()
    return (parseaddr(text.replace("From:", "").strip())[1] or "").strip().lower()


def _process_inbox(
    account: SenderAccount, client: imaplib.IMAP4_SSL, db: Session
) -> tuple[int, int]:
    from app.services import sending_engine_service as _ses

    start_uid = int(account.last_imap_uid or 0) + 1
    status_value, data = client.uid("SEARCH", None, f"UID {start_uid}:*")
    if status_value != "OK":
        return 0, 0

    uid_strings = [u.decode() for u in (data[0] or b"").split()]
    max_fetch = int(getattr(account, "max_imap_fetch", None) or 100)
    # Scan the newest UIDs first so fresh replies are detected quickly even when
    # there is a large unseen backlog.
    uid_strings = uid_strings[-max_fetch:]

    lead_emails = _workspace_lead_emails_lower(account.workspace_id, db)
    fetch_batch = max(1, _ses._IMAP_FETCH_BATCH)

    uids_need_full: list[str] = []
    for bi in range(0, len(uid_strings), fetch_batch):
        chunk = uid_strings[bi : bi + fetch_batch]
        hdr_by_uid = _ses._imap_batch_fetch_uid_header_fields(
            client,
            chunk,
            "FROM MESSAGE-ID DATE SUBJECT IN-REPLY-TO REFERENCES",
        )
        for uid in chunk:
            blob = hdr_by_uid.get(uid)
            if not blob:
                uids_need_full.append(uid)
                continue
            try:
                hmsg = _message_from_header_fields_bytes(blob)
                from_address = _from_address_from_header_fetch_blob(blob)
                if not from_address:
                    from_raw = hmsg.get("From", "") or ""
                    from_address = (parseaddr(from_raw)[1] or "").strip().lower()
                    if not from_address:
                        from_address = from_raw.strip().lower()
                mid = (hmsg.get("Message-ID") or "").strip()
            except Exception:
                uids_need_full.append(uid)
                continue

            if not lead_emails or from_address not in lead_emails:
                continue

            if mid and repositories.unibox_repository.message_exists_by_header(mid, db):
                continue

            uids_need_full.append(uid)

    need_full = set(uids_need_full)
    max_seen_uid = int(account.last_imap_uid or 0)
    ingested = 0
    replies = 0

    for uid in uid_strings:
        try:
            if uid in need_full:
                n, r = _ingest_one_uid(uid, account, client, db)
                ingested += n
                replies += r
        except Exception:
            db.rollback()
        max_seen_uid = max(max_seen_uid, int(uid))

    account.last_imap_uid = max_seen_uid or account.last_imap_uid
    db.flush()
    db.commit()
    return ingested, replies


def _ingest_one_uid(
    uid: str,
    account: SenderAccount,
    client: imaplib.IMAP4_SSL,
    db: Session,
) -> tuple[int, int]:
    """Download, parse, and persist one IMAP message. Returns (1, reply?) if ingested, (0, 0) if skipped."""
    status_fetch, msg_data = client.uid("FETCH", uid, "(RFC822)")
    if status_fetch != "OK" or not msg_data:
        return 0, 0

    raw_bytes = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
    if not raw_bytes:
        return 0, 0

    msg = email.message_from_bytes(raw_bytes)

    # --- Extract headers ---
    message_id_header = (msg.get("Message-ID") or "").strip()
    if not message_id_header:
        # Synthesise a stable synthetic ID from uid + account so we can
        # still ingest messages that are missing the header.
        message_id_header = f"<synthetic-{uid}-{account.account_id}@campaignpulse.local>"

    # Idempotency check.
    if repositories.unibox_repository.message_exists_by_header(message_id_header, db):
        return 0, 0

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
    if lead is None:
        # Unibox is for campaign conversations only — not the full mailbox.
        return 0, 0

    lead_id = lead.lead_id
    is_orphan = False

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
    reply_fired = 0
    if lead is not None:
        if _maybe_fire_reply_event(lead, account, uid, db):
            reply_fired = 1

    return 1, reply_fired


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
) -> bool:
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
        return False

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
    return True


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
    # Cap body size for tsvector generation (large newsletters were slow on INSERT).
    bt = body_text or ""
    if len(bt) > 24000:
        bt = bt[:24000]

    combined = (
        (subject or "")
        + " "
        + bt
        + " "
        + (from_address or "")
    )
    result = db.execute(
        text("SELECT to_tsvector('english', :content)"),
        {"content": combined},
    ).scalar()
    return result

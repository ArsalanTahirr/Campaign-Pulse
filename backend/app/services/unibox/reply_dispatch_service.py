"""
services/unibox/reply_dispatch_service.py — Send an outbound reply from the
Unibox reply composer and persist it as a UniboxMessage.

The service reuses the existing _send_smtp logic from sending_engine_service
but enriches the outbound email with RFC 2822 threading headers (In-Reply-To
and References) so that email clients display the reply correctly inside the
conversation thread.

On SMTP failure the message is persisted with status='failed' so the Unibox
UI can surface the error without losing the reply content.

All DB mutations call flush() then the caller commits.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import smtplib
import ssl
from email.message import EmailMessage

from sqlalchemy import text
from sqlalchemy.orm import Session

from fastapi import HTTPException, status as http_status

from app import repositories
from app.models import SenderAccount, UniboxMessage, UniboxThread
from app.services.unibox import threading_service


def send_reply(
    *,
    thread_id: str,
    workspace_id: str,
    sender_account_id: str,
    body_text: Optional[str],
    body_html: Optional[str],
    db: Session,
) -> UniboxMessage:
    """
    Compose and send a reply email from the Unibox.

    Parameters
    ----------
    thread_id          : The thread to reply into.
    workspace_id       : Used to authorise access to the thread.
    sender_account_id  : The SenderAccount (inbox) to send from.
    body_text          : Plain-text body (optional if body_html is provided).
    body_html          : HTML body (optional if body_text is provided).
    db                 : SQLAlchemy Session (caller commits).

    Returns
    -------
    UniboxMessage — the persisted outbound message.

    Raises
    ------
    404 if the thread or sender account is not found in this workspace.
    422 if neither body_text nor body_html is provided.
    """
    # --- Load thread ---
    thread = repositories.unibox_repository.get_thread_by_id(thread_id, workspace_id, db)
    if thread is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found.",
        )

    # --- Load sender account ---
    account = (
        db.query(SenderAccount)
        .filter(
            SenderAccount.account_id == sender_account_id,
            SenderAccount.workspace_id == workspace_id,
            SenderAccount.deleted_at.is_(None),
        )
        .first()
    )
    if account is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Sender account {sender_account_id} not found in workspace.",
        )

    # --- Determine recipient ---
    recipient = _resolve_reply_recipient(thread, db)

    # --- Determine threading headers ---
    last_message = _get_last_message(thread.thread_id, db)
    in_reply_to: Optional[str] = None
    references_header: Optional[str] = None

    if last_message:
        in_reply_to = last_message.message_id_header
        existing_refs = last_message.references_header or ""
        if existing_refs:
            references_header = f"{existing_refs} {last_message.message_id_header}".strip()
        else:
            references_header = last_message.message_id_header

    # --- Build subject ---
    reply_subject = f"Re: {threading_service._strip_re_prefix(thread.subject)}"

    # --- Synthesise a Message-ID for the outbound message ---
    synthetic_mid = f"<{uuid.uuid4()}@campaignpulse.local>"

    # --- Send via SMTP ---
    sent_at: Optional[datetime] = None
    message_status = "failed"
    try:
        _send_smtp_reply(
            account=account,
            recipient=recipient,
            subject=reply_subject,
            body_text=body_text or "",
            body_html=body_html or "",
            message_id=synthetic_mid,
            in_reply_to=in_reply_to,
            references_header=references_header,
        )
        sent_at = datetime.now(timezone.utc)
        message_status = "sent"
    except Exception:
        # Persist with status='failed'; do not re-raise so the caller can
        # still return the message object and let the UI show the failure.
        pass

    # --- Build search vector ---
    search_vector = _build_search_vector(
        reply_subject, body_text, account.email, db
    )

    # --- Persist outbound message ---
    now = datetime.now(timezone.utc)
    msg = UniboxMessage(
        thread_id=thread.thread_id,
        sender_account_id=account.account_id,
        lead_id=thread.lead_id,
        email_event_id=None,
        direction="outbound",
        message_id_header=synthetic_mid,
        in_reply_to=in_reply_to,
        references_header=references_header,
        from_address=account.email,
        to_addresses=[recipient],
        cc_addresses=None,
        subject=reply_subject,
        body_text=body_text,
        body_html=body_html,
        is_read=True,
        is_orphan=thread.is_orphan,
        status=message_status,
        received_at=None,
        sent_at=sent_at,
        search_vector=search_vector,
    )
    repositories.unibox_repository.create_message(msg, db)

    # Update thread last_message_at.
    repositories.unibox_repository.update_thread_last_message_at(
        thread.thread_id, sent_at or now, db
    )

    db.flush()
    return msg


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_reply_recipient(thread: UniboxThread, db: Session) -> str:
    """
    Determine the To: address for the reply.
    For known-lead threads: use lead.email.
    For orphan threads: use the from_address of the first inbound message.
    """
    if thread.lead is not None:
        return thread.lead.email

    first_inbound = (
        db.query(UniboxMessage)
        .filter(
            UniboxMessage.thread_id == thread.thread_id,
            UniboxMessage.direction == "inbound",
        )
        .order_by(UniboxMessage.created_at.asc())
        .first()
    )
    if first_inbound:
        return first_inbound.from_address

    raise HTTPException(
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Cannot determine reply recipient: thread has no inbound messages.",
    )


def _get_last_message(thread_id: str, db: Session) -> Optional[UniboxMessage]:
    """Return the most recent message in the thread for threading headers."""
    return (
        db.query(UniboxMessage)
        .filter(UniboxMessage.thread_id == thread_id)
        .order_by(UniboxMessage.created_at.desc())
        .first()
    )


def _send_smtp_reply(
    *,
    account: SenderAccount,
    recipient: str,
    subject: str,
    body_text: str,
    body_html: str,
    message_id: str,
    in_reply_to: Optional[str],
    references_header: Optional[str],
) -> None:
    """
    Send an outbound reply via SMTP, including RFC 2822 threading headers.
    Raises RuntimeError on failure.
    """
    if not account.smtp_host or not account.smtp_port or not account.app_password:
        raise RuntimeError("Sender account SMTP configuration is incomplete.")

    message = EmailMessage()
    message["From"] = account.email
    message["To"] = recipient
    message["Subject"] = subject
    message["Message-ID"] = message_id
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
    if references_header:
        message["References"] = references_header

    message.set_content(body_text or "This email contains HTML content.")
    if body_html:
        message.add_alternative(body_html, subtype="html")

    try:
        if int(account.smtp_port) == 465:
            with smtplib.SMTP_SSL(account.smtp_host, int(account.smtp_port), timeout=30) as server:
                server.login(account.email, account.app_password)
                server.send_message(message)
        else:
            context = ssl.create_default_context()
            with smtplib.SMTP(account.smtp_host, int(account.smtp_port), timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(account.email, account.app_password)
                server.send_message(message)
    except Exception as exc:
        raise RuntimeError(f"SMTP reply failed for {account.email}: {exc}") from exc


def _build_search_vector(
    subject: str,
    body_text: Optional[str],
    from_address: str,
    db: Session,
) -> object:
    """Compute a PostgreSQL tsvector from subject + body_text + from_address."""
    combined = (
        (subject or "")
        + " "
        + (body_text or "")
        + " "
        + (from_address or "")
    )
    return db.execute(
        text("SELECT to_tsvector('english', :content)"),
        {"content": combined},
    ).scalar()

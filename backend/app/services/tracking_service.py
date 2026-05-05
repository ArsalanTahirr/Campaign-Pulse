"""
services/tracking_service.py — Open/click tracking handlers over EMAIL_EVENT.
"""

import base64
import hashlib
import hmac
import os
import urllib.parse
from datetime import datetime, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.models import EmailEvent

TRACKING_SECRET = os.environ.get("TRACKING_SIGNING_SECRET", "dev-tracking-secret")


def _resolve_sent_event(event_id: str, db: Session) -> EmailEvent:
    source = db.query(EmailEvent).filter(EmailEvent.event_id == event_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracking event not found.")
    if source.event_type != "sent":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid tracking source event.")
    # Warmup traffic is not instrumented and must not create open/click engagement rows.
    if source.event_scope != "lead":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tracking is only supported for campaign (lead) sends.",
        )
    return source


def _request_metadata(request: Request) -> dict:
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


def log_open_event(source_event_id: str, request: Request, db: Session) -> EmailEvent | None:
    """
    Record a single open per sent event (idempotent on pixel re-fetch / prefetch).

    Returns the new EmailEvent, or None if this sent_id was already counted.
    """
    source = _resolve_sent_event(source_event_id, db)
    sent_key = str(source.event_id)
    existing = (
        db.query(EmailEvent.event_id)
        .filter(
            EmailEvent.event_type == "opened",
            EmailEvent.event_metadata["source_sent_event_id"].astext == sent_key,
        )
        .first()
    )
    if existing:
        return None

    meta = _request_metadata(request)
    meta["source_sent_event_id"] = sent_key
    evt = EmailEvent(
        lead_id=source.lead_id,
        step_id=source.step_id,
        event_type="opened",
        event_scope=source.event_scope,
        sender_account_id=source.sender_account_id,
        recipient_account_id=source.recipient_account_id,
        warmup_thread_id=source.warmup_thread_id,
        occurred_at=datetime.now(timezone.utc),
        event_metadata=meta,
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt


def sign_click_target(source_event_id: str, target_url: str) -> str:
    payload = f"{source_event_id}:{target_url}".encode("utf-8")
    digest = hmac.new(TRACKING_SECRET.encode("utf-8"), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def verify_click_signature(source_event_id: str, target_url: str, signature: str) -> bool:
    expected = sign_click_target(source_event_id, target_url)
    return hmac.compare_digest(expected, signature)


def log_click_event(source_event_id: str, target_url: str, request: Request, db: Session) -> EmailEvent:
    source = _resolve_sent_event(source_event_id, db)
    metadata = _request_metadata(request)
    metadata["url"] = target_url
    metadata["source_sent_event_id"] = str(source.event_id)

    # If image-pixel open tracking is blocked/unreachable, a real click still
    # proves the email was opened. Backfill one "opened" event idempotently.
    sent_key = str(source.event_id)
    existing_open = (
        db.query(EmailEvent.event_id)
        .filter(
            EmailEvent.event_type == "opened",
            EmailEvent.event_metadata["source_sent_event_id"].astext == sent_key,
        )
        .first()
    )
    if not existing_open:
        open_meta = _request_metadata(request)
        open_meta["source_sent_event_id"] = sent_key
        open_meta["via"] = "click_backfill"
        db.add(
            EmailEvent(
                lead_id=source.lead_id,
                step_id=source.step_id,
                event_type="opened",
                event_scope=source.event_scope,
                sender_account_id=source.sender_account_id,
                recipient_account_id=source.recipient_account_id,
                warmup_thread_id=source.warmup_thread_id,
                occurred_at=datetime.now(timezone.utc),
                event_metadata=open_meta,
            )
        )

    evt = EmailEvent(
        lead_id=source.lead_id,
        step_id=source.step_id,
        event_type="clicked",
        event_scope=source.event_scope,
        sender_account_id=source.sender_account_id,
        recipient_account_id=source.recipient_account_id,
        warmup_thread_id=source.warmup_thread_id,
        occurred_at=datetime.now(timezone.utc),
        event_metadata=metadata,
    )
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt


def decode_click_target(raw_target: str) -> str:
    decoded = urllib.parse.unquote(raw_target)
    parsed = urllib.parse.urlparse(decoded)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid redirect URL.")
    return decoded

"""
services/email_account_service.py — Sender account and warmup configuration CRUD.
"""

import imaplib
import os
import smtplib
import ssl
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import CampaignSenderPool, SenderAccount, WarmupSettings

PROVIDER_HOST_DEFAULTS = {
    "google": {"smtp_host": "smtp.gmail.com", "imap_host": "imap.gmail.com", "smtp_port": 587, "imap_port": 993},
    "microsoft": {"smtp_host": "smtp.office365.com", "imap_host": "outlook.office365.com", "smtp_port": 587, "imap_port": 993},
}

GOOGLE_CONSUMER_DOMAINS = {"gmail.com", "googlemail.com"}
MICROSOFT_CONSUMER_DOMAINS = {
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
}


def _reconcile_account_status(account: SenderAccount) -> None:
    """
    System-owned status transitions for sender accounts.

    - warmup active   => warming_up
    - warmup inactive => active
    - suspended is preserved so automation/ops can hold an account.
    """
    if account.status == "inactive":
        account.status = "disconnected"
    if account.deleted_at is not None:
        account.status = "disconnected"
        account.is_verified = False
        return
    if account.status == "suspended":
        return
    is_warmup_active = bool(account.warmup_settings and account.warmup_settings.is_warmup_active)
    account.status = "warming_up" if is_warmup_active else "active"


def _apply_provider_defaults(payload: dict) -> dict:
    provider_type = payload.get("provider_type")
    defaults = PROVIDER_HOST_DEFAULTS.get(provider_type)
    if not defaults:
        return payload
    payload.setdefault("smtp_host", defaults["smtp_host"])
    payload.setdefault("imap_host", defaults["imap_host"])
    payload.setdefault("smtp_port", defaults["smtp_port"])
    payload.setdefault("imap_port", defaults["imap_port"])
    return payload


def _assert_required_connection_fields(payload: dict) -> None:
    required = ["email", "smtp_host", "smtp_port", "imap_host", "imap_port", "app_password"]
    missing = []
    for field in required:
        value = payload.get(field)
        if isinstance(value, str):
            value = value.strip()
            payload[field] = value
        if value in (None, ""):
            missing.append(field)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required connection fields: {', '.join(missing)}",
        )


def _assert_provider_matches_email(payload: dict) -> None:
    provider_type = payload.get("provider_type")
    email = str(payload.get("email") or "").strip().lower()
    if "@" not in email:
        return
    domain = email.rsplit("@", 1)[1]

    # Guard against obvious provider mismatches for consumer domains.
    if provider_type == "microsoft" and domain in GOOGLE_CONSUMER_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Gmail addresses must use provider type 'google', not 'microsoft'.",
        )
    if provider_type == "google" and domain in MICROSOFT_CONSUMER_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Outlook/Hotmail addresses must use provider type 'microsoft', not 'google'.",
        )


def _normalize_email_in_payload(payload: dict) -> None:
    email = payload.get("email")
    if isinstance(email, str):
        payload["email"] = email.strip().lower()


def _ensure_unique_email(
    workspace_id: str,
    email: str,
    db: Session,
    *,
    exclude_account_id: str | None = None,
) -> None:
    query = db.query(SenderAccount.account_id).filter(
        SenderAccount.workspace_id == workspace_id,
        func.lower(SenderAccount.email) == email.lower(),
        SenderAccount.deleted_at.is_(None),
    )
    if exclude_account_id:
        query = query.filter(SenderAccount.account_id != exclude_account_id)
    exists = query.first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Sender account '{email}' already exists in this workspace.",
        )


def _verify_sender_connectivity(payload: dict) -> None:
    try:
        smtp_port = int(payload["smtp_port"])
        if smtp_port == 465:
            with smtplib.SMTP_SSL(payload["smtp_host"], smtp_port, timeout=10) as client:
                client.login(payload["email"], payload["app_password"])
        else:
            with smtplib.SMTP(payload["smtp_host"], smtp_port, timeout=10) as client:
                client.ehlo()
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
                client.login(payload["email"], payload["app_password"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"SMTP verification failed: {exc}",
        )

    try:
        with imaplib.IMAP4_SSL(payload["imap_host"], int(payload["imap_port"]), timeout=10) as client:
            client.login(payload["email"], payload["app_password"])
            client.logout()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"IMAP verification failed: {exc}",
        )


def _should_verify_connectivity(db: Session) -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    try:
        return db.bind is not None and db.bind.dialect.name != "sqlite"
    except Exception:
        return True


def _get_account_or_404(workspace_id: str, account_id: str, db: Session) -> SenderAccount:
    account = (
        db.query(SenderAccount)
        .options(joinedload(SenderAccount.warmup_settings))
        .filter(
            SenderAccount.workspace_id == workspace_id,
            SenderAccount.account_id == account_id,
            SenderAccount.deleted_at.is_(None),
        )
        .first()
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender account not found.")
    return account


def list_accounts(workspace_id: str, db: Session) -> list[SenderAccount]:
    return (
        db.query(SenderAccount)
        .options(joinedload(SenderAccount.warmup_settings))
        .filter(SenderAccount.workspace_id == workspace_id, SenderAccount.deleted_at.is_(None))
        .order_by(SenderAccount.created_at.desc())
        .all()
    )


def create_account(workspace_id: str, payload: dict, db: Session) -> SenderAccount:
    warmup_payload = payload.pop("warmup_settings", None)
    payload.pop("status", None)
    payload.pop("is_verified", None)
    _normalize_email_in_payload(payload)
    payload = _apply_provider_defaults(payload)
    _assert_required_connection_fields(payload)
    _assert_provider_matches_email(payload)
    _ensure_unique_email(workspace_id, payload["email"], db)
    if _should_verify_connectivity(db):
        _verify_sender_connectivity(payload)
    account = SenderAccount(
        account_id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        sent_count_today=0,
        status="active",
        is_verified=True,
        **payload,
    )
    db.add(account)

    if warmup_payload:
        warmup = WarmupSettings(
            account_id=account.account_id,
            **warmup_payload,
        )
        db.add(warmup)
        # warmup object exists before commit, so status can be reconciled now.
        account.warmup_settings = warmup

    _reconcile_account_status(account)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Could not create sender account: {exc.orig}",
        )

    return _get_account_or_404(workspace_id, account.account_id, db)


def update_account(workspace_id: str, account_id: str, updates: dict, db: Session) -> SenderAccount:
    account = _get_account_or_404(workspace_id, account_id, db)
    updates.pop("status", None)
    updates.pop("is_verified", None)
    _normalize_email_in_payload(updates)
    if updates.get("app_password", None) == "":
        updates.pop("app_password", None)

    merged = {
        "provider_type": updates.get("provider_type", account.provider_type),
        "email": updates.get("email", account.email),
        "smtp_host": updates.get("smtp_host", account.smtp_host),
        "smtp_port": updates.get("smtp_port", account.smtp_port),
        "imap_host": updates.get("imap_host", account.imap_host),
        "imap_port": updates.get("imap_port", account.imap_port),
        "app_password": updates.get("app_password", account.app_password),
    }
    merged = _apply_provider_defaults(merged)
    _assert_required_connection_fields(merged)
    _assert_provider_matches_email(merged)
    _ensure_unique_email(
        workspace_id,
        merged["email"],
        db,
        exclude_account_id=account_id,
    )
    if _should_verify_connectivity(db):
        _verify_sender_connectivity(merged)
    updates.update(
        smtp_host=merged["smtp_host"],
        smtp_port=merged["smtp_port"],
        imap_host=merged["imap_host"],
        imap_port=merged["imap_port"],
    )
    for field, value in updates.items():
        if hasattr(account, field):
            setattr(account, field, value)

    account.is_verified = True
    _reconcile_account_status(account)
    db.commit()
    db.refresh(account)
    return _get_account_or_404(workspace_id, account_id, db)


def delete_account(workspace_id: str, account_id: str, db: Session) -> None:
    account = _get_account_or_404(workspace_id, account_id, db)
    account.deleted_at = datetime.now(timezone.utc)
    account.is_verified = False
    account.status = "disconnected"
    db.query(CampaignSenderPool).filter(CampaignSenderPool.sender_account_id == account.account_id).delete(
        synchronize_session=False
    )
    db.commit()


def patch_warmup_settings(workspace_id: str, account_id: str, payload: dict, db: Session) -> WarmupSettings:
    account = _get_account_or_404(workspace_id, account_id, db)
    warmup = account.warmup_settings
    if not warmup:
        warmup = WarmupSettings(account_id=account.account_id)
        db.add(warmup)
        db.flush()

    for field, value in payload.items():
        setattr(warmup, field, value)

    # Default warmup start anchor when enabling warmup and no date supplied.
    if warmup.is_warmup_active and warmup.warmup_started_at is None:
        warmup.warmup_started_at = datetime.now(timezone.utc)

    _reconcile_account_status(account)
    db.commit()
    db.refresh(warmup)
    return warmup

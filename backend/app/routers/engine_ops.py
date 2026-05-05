"""
routers/engine_ops.py — Operator endpoints for on-demand sending engine actions.
"""

from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal, get_db
from app.dependencies import require_permission
from app.models import Campaign, Lead, SenderAccount
from app.services import sending_engine_service
from app.services.unibox import ingestion_service
from app.workers.engine_loops import is_engine_enabled, set_engine_enabled

router = APIRouter()
SEND_WORKER_COUNT = 4


class EngineToggleIn(BaseModel):
    enabled: bool


@router.get("/status")
def engine_status(
    workspace_id: str,
    _: None = require_permission("manage_email_accounts"),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    queued = (
        db.query(Lead)
        .join(Campaign, Campaign.campaign_id == Lead.campaign_id)
        .filter(
            Campaign.workspace_id == workspace_id,
            Campaign.status == "active",
            Lead.delivery_state == "queued",
        )
        .count()
    )
    queued_ready = (
        db.query(Lead)
        .join(Campaign, Campaign.campaign_id == Lead.campaign_id)
        .filter(
            Campaign.workspace_id == workspace_id,
            Campaign.status == "active",
            Lead.lead_status == "active",
            Lead.delivery_state == "queued",
            Lead.next_eligible_at.isnot(None),
            Lead.next_eligible_at <= now,
        )
        .count()
    )
    sending = (
        db.query(Lead)
        .join(Campaign, Campaign.campaign_id == Lead.campaign_id)
        .filter(
            Campaign.workspace_id == workspace_id,
            Lead.delivery_state == "sending",
        )
        .count()
    )
    return {
        "engine_enabled": is_engine_enabled(),
        "queued_leads": queued,
        "queued_ready": queued_ready,
        "sending_leads": sending,
    }


@router.patch("/enabled")
def set_engine_runtime_enabled(
    workspace_id: str,
    body: EngineToggleIn,
    _: None = require_permission("manage_email_accounts"),
):
    set_engine_enabled(body.enabled)
    return {"engine_enabled": is_engine_enabled()}


@router.post("/run-send-once")
def run_send_once(
    workspace_id: str,
    _: None = require_permission("manage_email_accounts"),
    db: Session = Depends(get_db),
):
    completed_leads = (
        db.query(Lead)
        .join(Campaign, Campaign.campaign_id == Lead.campaign_id)
        .filter(
            Campaign.workspace_id == workspace_id,
            Campaign.status == "active",
            Lead.lead_status == "active",
            Lead.delivery_state == "completed",
            Lead.next_eligible_at.is_(None),
        )
        .count()
    )
    claims = sending_engine_service.claim_queued_leads(
        batch_size=20, db=db, workspace_id=workspace_id
    )
    def _process_one(claim: tuple[str, str, str]) -> bool:
        lead_id, token, sender_id = claim
        with SessionLocal() as worker_db:
            sending_engine_service.process_claimed_lead(lead_id, token, sender_id, worker_db)
        return True

    processed = 0
    if claims:
        with ThreadPoolExecutor(max_workers=SEND_WORKER_COUNT) as executor:
            futures = [executor.submit(_process_one, claim) for claim in claims]
            for fut in as_completed(futures):
                _ = fut.result()
                processed += 1
    hint = None
    if not claims:
        total_queued = (
            db.query(Lead)
            .join(Campaign, Campaign.campaign_id == Lead.campaign_id)
            .filter(
                Campaign.workspace_id == workspace_id,
                Campaign.status == "active",
                Lead.delivery_state == "queued",
            )
            .count()
        )
        if total_queued == 0:
            if completed_leads > 0:
                hint = (
                    f"No leads are queued right now. {completed_leads} lead(s) are already completed "
                    "with no next step scheduled. Add another sequence step (or add new leads) to create queue."
                )
            else:
                hint = (
                    "No leads are queued in active campaigns for this workspace. "
                    "Enroll leads and ensure the campaign is active with a sender pool."
                )
        else:
            hint = (
                f"{total_queued} lead(s) are queued but none are ready to send right now "
                "(paused lead, missing next send time, or next send time is still in the future)."
            )
    return {"claimed": len(claims), "processed": processed, "hint": hint}


@router.post("/run-warmup-once")
def run_warmup_once(
    workspace_id: str,
    _: None = require_permission("manage_email_accounts"),
    db: Session = Depends(get_db),
):
    sent = sending_engine_service.run_warmup_iteration(db)
    return {"warmup_sent": sent}


@router.post("/run-imap-once")
def run_imap_once(
    workspace_id: str,
    _: None = require_permission("manage_email_accounts"),
    db: Session = Depends(get_db),
):
    """
    Poll all configured sender inboxes: parallel Unibox ingestion (replies +
    messages), then warmup spam rescue. Reply events are only recorded during
    ingestion so they stay aligned with Unibox rows.
    """
    ingested = 0
    replies_from_ingest = 0
    accounts = (
        db.query(SenderAccount)
        .options(joinedload(SenderAccount.warmup_settings))
        .filter(
            SenderAccount.imap_host.isnot(None),
            SenderAccount.imap_port.isnot(None),
            SenderAccount.app_password.isnot(None),
            SenderAccount.status == "active",
            SenderAccount.deleted_at.is_(None),
        )
        .all()
    )
    accounts = [
        a
        for a in accounts
        if not (a.warmup_settings and getattr(a.warmup_settings, "is_warmup_active", False))
    ]
    try:
        ingested, replies_from_ingest = ingestion_service.ingest_accounts_parallel(
            [a.account_id for a in accounts]
        )
    except Exception:
        db.rollback()
        ingested, replies_from_ingest = 0, 0

    # Workers committed updated last_imap_uid; expire cached SenderAccount rows
    # on this request session so any future reads see fresh DB state.
    db.expire_all()

    # Do not scan warmup inboxes during lead IMAP scans.

    scan_note = None
    if ingested == 0 and replies_from_ingest == 0:
        scan_note = (
            "No new lead mail in the scanned UID range. Inbox scan only records messages "
            "whose From address matches a lead email in this workspace. "
            'The "Queue" badge is the outbound send queue (leads waiting to be emailed), not IMAP. '
            "If you expected new mail, verify IMAP credentials, that the lead exists with the same address as From, or reset last_imap_uid (see backend/scripts/reset_unibox_imap_test.py)."
        )
    return {
        "replies_detected": replies_from_ingest,
        "messages_ingested": ingested,
        "scan_note": scan_note,
    }

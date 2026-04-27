"""
routers/engine_ops.py — Operator endpoints for on-demand sending engine actions.
"""

import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.models import Campaign, Lead
from app.services import sending_engine_service

router = APIRouter()


@router.get("/status")
def engine_status(
    workspace_id: str,
    _: None = require_permission("manage_email_accounts"),
    db: Session = Depends(get_db),
):
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
        "engine_enabled": os.environ.get("ENABLE_SENDING_ENGINE", "false").lower() == "true",
        "queued_leads": queued,
        "sending_leads": sending,
    }


@router.post("/run-send-once")
def run_send_once(
    workspace_id: str,
    _: None = require_permission("manage_email_accounts"),
    db: Session = Depends(get_db),
):
    claims = sending_engine_service.claim_queued_leads(batch_size=20, db=db)
    processed = 0
    for lead_id, token in claims:
        sending_engine_service.process_claimed_lead(lead_id, token, db)
        processed += 1
    return {"claimed": len(claims), "processed": processed}


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
    replies = sending_engine_service.run_imap_reply_iteration(db)
    return {"replies_detected": replies}

"""
services/campaign_service.py — Campaign CRUD and lifecycle transitions.

ORM column: Campaign.campaign_name (not .name)
ORM column: Collaborator.member_id (not .collaborator_id)
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Campaign, CampaignRun, CampaignSenderPool, Collaborator, Lead, SenderAccount, SequenceStep, StepEmail
from app.services.audit_log_service import write_audit_log

VALID_TRANSITIONS: dict[str, dict] = {
    "started": {"from": {"draft", "scheduled", "paused"}, "to": "active", "run_status": "running"},
    "paused": {"from": {"active"}, "to": "paused", "run_status": "paused"},
    "resumed": {"from": {"paused"}, "to": "active", "run_status": "running"},
    "stopped": {"from": {"active", "paused"}, "to": "completed", "run_status": "completed"},
}

LEGACY_STATUS_ALIASES = {
    "running": "active",
    "stopped": "completed",
}


def _normalize_status(status_value: str) -> str:
    return LEGACY_STATUS_ALIASES.get(status_value, status_value)


def _assert_has_email_variants(campaign_id: str, db: Session) -> None:
    step_count = (
        db.query(func.count(SequenceStep.step_id))
        .filter(SequenceStep.campaign_id == campaign_id)
        .scalar()
        or 0
    )
    if step_count == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Campaign must have at least one step before starting.",
        )

    steps_without_emails = (
        db.query(SequenceStep)
        .filter(SequenceStep.campaign_id == campaign_id)
        .filter(
            ~db.query(StepEmail)
            .filter(StepEmail.step_id == SequenceStep.step_id)
            .exists()
        )
        .all()
    )
    if steps_without_emails:
        nums = [str(s.step_number) for s in steps_without_emails]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Steps {', '.join(nums)} have no email variants. Add at least one before starting.",
        )


def _assert_has_sender_pool(campaign_id: str, db: Session) -> None:
    sender_count = (
        db.query(func.count(CampaignSenderPool.sender_account_id))
        .filter(CampaignSenderPool.campaign_id == campaign_id)
        .scalar()
        or 0
    )
    if sender_count == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Campaign must have at least one sender account before starting.",
        )


def _assert_has_leads(campaign_id: str, db: Session) -> None:
    lead_count = (
        db.query(func.count(Lead.lead_id)).filter(Lead.campaign_id == campaign_id).scalar() or 0
    )
    if lead_count == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Campaign must have at least one lead before starting or resuming.",
        )


def get_campaign_or_404(campaign_id: str, workspace_id: str, db: Session) -> Campaign:
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.campaign_id == campaign_id,
            Campaign.workspace_id == workspace_id,
            Campaign.status != "deleted",
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    return campaign


def get_campaign_sender_accounts(campaign_id: str, db: Session) -> list[dict]:
    rows = (
        db.query(SenderAccount.account_id, SenderAccount.email)
        .join(CampaignSenderPool, CampaignSenderPool.sender_account_id == SenderAccount.account_id)
        .filter(CampaignSenderPool.campaign_id == campaign_id)
        .order_by(SenderAccount.email.asc())
        .all()
    )
    return [{"account_id": account_id, "email": email} for account_id, email in rows]


def get_campaign_sender_pool_view(campaign_id: str, workspace_id: str, db: Session) -> dict:
    get_campaign_or_404(campaign_id, workspace_id, db)
    connected = get_campaign_sender_accounts(campaign_id, db)
    available_rows = (
        db.query(SenderAccount.account_id, SenderAccount.email)
        .filter(
            SenderAccount.workspace_id == workspace_id,
            SenderAccount.deleted_at.is_(None),
        )
        .order_by(SenderAccount.email.asc())
        .all()
    )
    available = [{"account_id": account_id, "email": email} for account_id, email in available_rows]
    return {"connected": connected, "available": available}


def replace_campaign_sender_pool(campaign_id: str, workspace_id: str, account_ids: list[str], db: Session) -> list[dict]:
    get_campaign_or_404(campaign_id, workspace_id, db)
    normalized_ids = list(dict.fromkeys([a for a in account_ids if a]))
    if normalized_ids:
        valid_count = (
            db.query(func.count(SenderAccount.account_id))
            .filter(
                SenderAccount.workspace_id == workspace_id,
                SenderAccount.account_id.in_(normalized_ids),
                SenderAccount.deleted_at.is_(None),
            )
            .scalar()
            or 0
        )
        if valid_count != len(normalized_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="One or more sender accounts are invalid for this workspace.",
            )

    db.query(CampaignSenderPool).filter(CampaignSenderPool.campaign_id == campaign_id).delete(synchronize_session=False)
    for account_id in normalized_ids:
        db.add(CampaignSenderPool(campaign_id=campaign_id, sender_account_id=account_id))
    db.commit()
    return get_campaign_sender_accounts(campaign_id, db)


def list_campaigns(workspace_id: str, db: Session) -> list[dict]:
    campaigns = (
        db.query(Campaign)
        .filter(Campaign.workspace_id == workspace_id, Campaign.status != "deleted")
        .order_by(Campaign.created_at.desc())
        .all()
    )
    result = []
    for c in campaigns:
        step_count = db.query(func.count(SequenceStep.step_id)).filter(
            SequenceStep.campaign_id == c.campaign_id
        ).scalar() or 0
        lead_count = db.query(func.count(Lead.lead_id)).filter(
            Lead.campaign_id == c.campaign_id
        ).scalar() or 0
        result.append({
            "campaign_id": c.campaign_id,
            "workspace_id": c.workspace_id,
            "created_by": c.created_by,
            # Use campaign_name — the schema maps it to `name` via validation_alias
            "campaign_name": c.campaign_name,
            "status": _normalize_status(c.status),
            "timezone": c.timezone,
            "start_date": c.start_date,
            "end_date": c.end_date,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "step_count": step_count,
            "lead_count": lead_count,
            "sender_accounts": get_campaign_sender_accounts(c.campaign_id, db),
        })
    return result


def create_campaign(
    workspace_id: str,
    creator_member_id: Optional[str],
    name: str,
    timezone: str,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    db: Session,
) -> Campaign:
    try:
        campaign = Campaign(
            campaign_id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            created_by=creator_member_id,
            campaign_name=name,
            status="draft",
            timezone=timezone,
            schedule=None,
            start_date=start_date,
            end_date=end_date,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'A campaign named "{name}" already exists in this workspace.',
        )


def update_campaign(
    campaign_id: str,
    workspace_id: str,
    updates: dict,
    db: Session,
) -> Campaign:
    campaign = get_campaign_or_404(campaign_id, workspace_id, db)
    if campaign.status in {"completed", "deleted"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed or deleted campaigns are view-only and cannot be edited.",
        )
    updates.pop("schedule", None)
    # Map `name` from request to ORM column `campaign_name`
    if "name" in updates:
        campaign.campaign_name = updates.pop("name")
    for field, value in updates.items():
        if value is not None and hasattr(campaign, field):
            setattr(campaign, field, value)
    campaign.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another campaign with this name already exists in this workspace.",
        )
    db.refresh(campaign)
    return campaign


def delete_campaign(campaign_id: str, workspace_id: str, db: Session) -> None:
    campaign = get_campaign_or_404(campaign_id, workspace_id, db)
    campaign.status = "deleted"
    campaign.updated_at = datetime.now(timezone.utc)
    db.commit()


def transition_campaign(
    campaign_id: str,
    workspace_id: str,
    action: str,
    actor_user_id: str,
    db: Session,
) -> CampaignRun:
    if action not in VALID_TRANSITIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown action '{action}'. Allowed: {list(VALID_TRANSITIONS)}.",
        )

    campaign = get_campaign_or_404(campaign_id, workspace_id, db)
    transition = VALID_TRANSITIONS[action]

    current_status = _normalize_status(campaign.status)
    if current_status not in transition["from"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot perform '{action}' on a campaign in '{current_status}' status. "
                f"Allowed from: {transition['from']}."
            ),
        )

    if action == "started":
        _assert_has_email_variants(campaign_id, db)
        _assert_has_sender_pool(campaign_id, db)
        _assert_has_leads(campaign_id, db)

    if action == "resumed":
        _assert_has_leads(campaign_id, db)

    old_status = current_status
    campaign.status = transition["to"]
    campaign.updated_at = datetime.now(timezone.utc)

    run = CampaignRun(
        run_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        triggered_by=actor_user_id,
        action=action,
        run_status=transition["run_status"],
        started_at=datetime.now(timezone.utc) if action in ("started", "resumed") else None,
        ended_at=datetime.now(timezone.utc) if action == "stopped" else None,
    )
    db.add(run)

    write_audit_log(
        db=db,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action=f"campaign_{action}",
        target_type="campaign",
        target_id=campaign_id,
        old_value={"status": old_status},
        new_value={"status": campaign.status},
    )

    db.commit()
    db.refresh(run)
    return run


def get_campaign_runs(campaign_id: str, workspace_id: str, db: Session) -> list[CampaignRun]:
    get_campaign_or_404(campaign_id, workspace_id, db)
    return (
        db.query(CampaignRun)
        .filter(CampaignRun.campaign_id == campaign_id)
        .order_by(CampaignRun.created_at.desc())
        .all()
    )

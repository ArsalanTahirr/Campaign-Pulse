"""
routers/campaigns.py — Campaign CRUD and lifecycle endpoints.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import Collaborator, User
from app.schemas.campaign import (
    CampaignCreate,
    CampaignOut,
    CampaignRunCreate,
    CampaignRunOut,
    CampaignUpdate,
)
from app.services import campaign_service

router = APIRouter()


def _resolve_member_id(user_id: str, workspace_id: str, db: Session) -> str | None:
    collab = (
        db.query(Collaborator)
        .filter(
            Collaborator.user_id == user_id,
            Collaborator.workspace_id == workspace_id,
        )
        .first()
    )
    return collab.member_id if collab else None


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    workspace_id: str,
    _: None = require_permission("view_workspace"),
    db: Session = Depends(get_db),
):
    rows = campaign_service.list_campaigns(workspace_id, db)
    return [CampaignOut.model_validate(r) for r in rows]


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(
    workspace_id: str,
    body: CampaignCreate,
    _: None = require_permission("create_campaign"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member_id = _resolve_member_id(user.user_id, workspace_id, db)
    campaign = campaign_service.create_campaign(
        workspace_id=workspace_id,
        creator_member_id=member_id,
        name=body.name,
        schedule=body.schedule,
        start_date=body.start_date,
        end_date=body.end_date,
        db=db,
    )
    return CampaignOut.model_validate(campaign)


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    workspace_id: str,
    campaign_id: str,
    _: None = require_permission("view_workspace"),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func
    from app.models import SequenceStep, Lead

    campaign = campaign_service.get_campaign_or_404(campaign_id, workspace_id, db)
    step_count = db.query(func.count(SequenceStep.step_id)).filter(
        SequenceStep.campaign_id == campaign_id
    ).scalar() or 0
    lead_count = db.query(func.count(Lead.lead_id)).filter(
        Lead.campaign_id == campaign_id
    ).scalar() or 0

    out = CampaignOut.model_validate(campaign)
    out.step_count = step_count
    out.lead_count = lead_count
    return out


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    workspace_id: str,
    campaign_id: str,
    body: CampaignUpdate,
    _: None = require_permission("edit_campaign"),
    db: Session = Depends(get_db),
):
    updates = body.model_dump(exclude_unset=True)
    campaign = campaign_service.update_campaign(campaign_id, workspace_id, updates, db)
    return CampaignOut.model_validate(campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    workspace_id: str,
    campaign_id: str,
    _: None = require_permission("delete_campaign"),
    db: Session = Depends(get_db),
):
    campaign_service.delete_campaign(campaign_id, workspace_id, db)


@router.post("/{campaign_id}/runs", response_model=CampaignRunOut, status_code=status.HTTP_201_CREATED)
def run_campaign(
    workspace_id: str,
    campaign_id: str,
    body: CampaignRunCreate,
    _: None = require_permission("start_campaign"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return campaign_service.transition_campaign(
        campaign_id=campaign_id,
        workspace_id=workspace_id,
        action=body.action,
        actor_user_id=user.user_id,
        db=db,
    )


@router.get("/{campaign_id}/runs", response_model=list[CampaignRunOut])
def list_runs(
    workspace_id: str,
    campaign_id: str,
    _: None = require_permission("view_analytics"),
    db: Session = Depends(get_db),
):
    return campaign_service.get_campaign_runs(campaign_id, workspace_id, db)

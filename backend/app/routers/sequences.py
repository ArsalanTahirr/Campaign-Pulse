"""
routers/sequences.py — SequenceStep and StepEmail endpoints.

Routes (mounted under /workspaces/{workspace_id}/campaigns/{campaign_id}):
    GET    /steps                               — list all steps with variants
    POST   /steps                               — create step (+ inline variants)
    PATCH  /steps/{step_id}                     — update step metadata
    DELETE /steps/{step_id}                     — delete step + cascade variants

    GET    /steps/{step_id}/emails              — list email variants for a step
    POST   /steps/{step_id}/emails              — add a variant to a step
    PATCH  /steps/{step_id}/emails/{email_id}   — update a variant
    DELETE /steps/{step_id}/emails/{email_id}   — delete a variant
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.schemas.sequence import (
    SequenceStepCreate,
    SequenceStepOut,
    SequenceStepUpdate,
    StepEmailCreate,
    StepEmailOut,
    StepEmailUpdate,
)
from app.services import sequence_service

router = APIRouter()


# ---------------------------------------------------------------------------
# SequenceStep
# ---------------------------------------------------------------------------


@router.get("/steps", response_model=list[SequenceStepOut])
def list_steps(
    workspace_id: str,
    campaign_id: str,
    _: None = require_permission("view_workspace"),
    db: Session = Depends(get_db),
):
    return sequence_service.list_steps(campaign_id, db)


@router.post("/steps", response_model=SequenceStepOut, status_code=status.HTTP_201_CREATED)
def create_step(
    workspace_id: str,
    campaign_id: str,
    body: SequenceStepCreate,
    _: None = require_permission("manage_sequence"),
    db: Session = Depends(get_db),
):
    variants_data = [v.model_dump() for v in body.email_variants]
    return sequence_service.create_step(
        campaign_id=campaign_id,
        step_number=body.step_number,
        wait_days=body.wait_days,
        send_time=body.send_time,
        send_days=body.send_days,
        email_variants_data=variants_data,
        db=db,
    )


@router.patch("/steps/{step_id}", response_model=SequenceStepOut)
def update_step(
    workspace_id: str,
    campaign_id: str,
    step_id: str,
    body: SequenceStepUpdate,
    _: None = require_permission("manage_sequence"),
    db: Session = Depends(get_db),
):
    updates = body.model_dump(exclude_unset=True)
    return sequence_service.update_step(step_id, campaign_id, updates, db)


@router.delete("/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_step(
    workspace_id: str,
    campaign_id: str,
    step_id: str,
    _: None = require_permission("manage_sequence"),
    db: Session = Depends(get_db),
):
    sequence_service.delete_step(step_id, campaign_id, db)


# ---------------------------------------------------------------------------
# StepEmail variants
# ---------------------------------------------------------------------------


@router.get("/steps/{step_id}/emails", response_model=list[StepEmailOut])
def list_variants(
    workspace_id: str,
    campaign_id: str,
    step_id: str,
    _: None = require_permission("view_workspace"),
    db: Session = Depends(get_db),
):
    return sequence_service.list_variants(step_id, campaign_id, db)


@router.post(
    "/steps/{step_id}/emails",
    response_model=StepEmailOut,
    status_code=status.HTTP_201_CREATED,
)
def create_variant(
    workspace_id: str,
    campaign_id: str,
    step_id: str,
    body: StepEmailCreate,
    _: None = require_permission("manage_sequence"),
    db: Session = Depends(get_db),
):
    return sequence_service.create_variant(
        step_id=step_id,
        campaign_id=campaign_id,
        subject_line=body.subject_line,
        email_body=body.email_body,
        from_name=body.from_name,
        db=db,
    )


@router.patch("/steps/{step_id}/emails/{email_id}", response_model=StepEmailOut)
def update_variant(
    workspace_id: str,
    campaign_id: str,
    step_id: str,
    email_id: str,
    body: StepEmailUpdate,
    _: None = require_permission("manage_sequence"),
    db: Session = Depends(get_db),
):
    updates = body.model_dump(exclude_unset=True)
    return sequence_service.update_variant(email_id, step_id, campaign_id, updates, db)


@router.delete("/steps/{step_id}/emails/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant(
    workspace_id: str,
    campaign_id: str,
    step_id: str,
    email_id: str,
    _: None = require_permission("manage_sequence"),
    db: Session = Depends(get_db),
):
    sequence_service.delete_variant(email_id, step_id, campaign_id, db)

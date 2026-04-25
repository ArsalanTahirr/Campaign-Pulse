"""
services/sequence_service.py — SequenceStep and StepEmail management.
"""

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models import Campaign, SequenceStep, StepEmail


def _get_step_or_404(step_id: str, campaign_id: str, db: Session) -> SequenceStep:
    step = (
        db.query(SequenceStep)
        .filter(
            SequenceStep.step_id == step_id,
            SequenceStep.campaign_id == campaign_id,
        )
        .first()
    )
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence step not found.")
    return step


def list_steps(campaign_id: str, db: Session) -> list[SequenceStep]:
    return (
        db.query(SequenceStep)
        .options(joinedload(SequenceStep.email_variants))
        .filter(SequenceStep.campaign_id == campaign_id)
        .order_by(SequenceStep.step_number)
        .all()
    )


def create_step(
    campaign_id: str,
    step_number: int,
    wait_days: int,
    send_time: Optional[str],
    send_days: Optional[list],
    email_variants_data: list[dict],
    db: Session,
) -> SequenceStep:
    # Prevent duplicate step_number in the same campaign
    existing = (
        db.query(SequenceStep)
        .filter(
            SequenceStep.campaign_id == campaign_id,
            SequenceStep.step_number == step_number,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step number {step_number} already exists in this campaign.",
        )

    step = SequenceStep(
        step_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        step_number=step_number,
        wait_days=wait_days,
        send_time=send_time,
        send_days=send_days,
    )
    db.add(step)
    db.flush()

    for variant_data in email_variants_data:
        variant = StepEmail(
            email_id=str(uuid.uuid4()),
            step_id=step.step_id,
            **variant_data,
        )
        db.add(variant)

    db.commit()
    db.refresh(step)
    return step


def update_step(
    step_id: str,
    campaign_id: str,
    updates: dict,
    db: Session,
) -> SequenceStep:
    step = _get_step_or_404(step_id, campaign_id, db)

    # Prevent duplicate step_number if being changed
    new_num = updates.get("step_number")
    if new_num and new_num != step.step_number:
        conflict = (
            db.query(SequenceStep)
            .filter(
                SequenceStep.campaign_id == campaign_id,
                SequenceStep.step_number == new_num,
                SequenceStep.step_id != step_id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Step number {new_num} is already taken.",
            )

    for field, value in updates.items():
        if value is not None:
            setattr(step, field, value)
    db.commit()
    db.refresh(step)
    return step


def delete_step(step_id: str, campaign_id: str, db: Session) -> None:
    step = _get_step_or_404(step_id, campaign_id, db)
    db.delete(step)
    db.commit()


# ---------------------------------------------------------------------------
# StepEmail
# ---------------------------------------------------------------------------


def _get_variant_or_404(email_id: str, step_id: str, db: Session) -> StepEmail:
    variant = (
        db.query(StepEmail)
        .filter(StepEmail.email_id == email_id, StepEmail.step_id == step_id)
        .first()
    )
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email variant not found.")
    return variant


def list_variants(step_id: str, campaign_id: str, db: Session) -> list[StepEmail]:
    _get_step_or_404(step_id, campaign_id, db)
    return (
        db.query(StepEmail)
        .filter(StepEmail.step_id == step_id)
        .order_by(StepEmail.created_at)
        .all()
    )


def create_variant(
    step_id: str,
    campaign_id: str,
    subject_line: str,
    email_body: str,
    from_name: Optional[str],
    sender_account_id: Optional[str],
    db: Session,
) -> StepEmail:
    _get_step_or_404(step_id, campaign_id, db)
    variant = StepEmail(
        email_id=str(uuid.uuid4()),
        step_id=step_id,
        subject_line=subject_line,
        email_body=email_body,
        from_name=from_name,
        sender_account_id=sender_account_id,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


def update_variant(
    email_id: str,
    step_id: str,
    campaign_id: str,
    updates: dict,
    db: Session,
) -> StepEmail:
    _get_step_or_404(step_id, campaign_id, db)
    variant = _get_variant_or_404(email_id, step_id, db)
    for field, value in updates.items():
        if value is not None:
            setattr(variant, field, value)
    db.commit()
    db.refresh(variant)
    return variant


def delete_variant(email_id: str, step_id: str, campaign_id: str, db: Session) -> None:
    _get_step_or_404(step_id, campaign_id, db)
    variant = _get_variant_or_404(email_id, step_id, db)
    db.delete(variant)
    db.commit()

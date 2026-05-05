"""
services/sequence_service.py — SequenceStep and StepEmail management.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import Campaign, Lead, SequenceStep, StepEmail
from app.services import sending_engine_service


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


def _get_campaign_status(campaign_id: str, db: Session) -> str:
    status_value = (
        db.query(Campaign.status)
        .filter(Campaign.campaign_id == campaign_id)
        .scalar()
    )
    if not status_value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    return status_value


def _assert_send_window_times(send_time: str | None, send_window_end: str | None) -> None:
    if not send_time:
        return
    end = send_window_end or send_time
    if end < send_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="send_window_end must be greater than or equal to send_time.",
        )


def _assert_sequence_editable(campaign_id: str, db: Session) -> None:
    campaign_status = _get_campaign_status(campaign_id, db)
    if campaign_status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed campaigns are view-only. Pause/Draft is required to edit sequence.",
        )
    if campaign_status not in {"draft", "paused"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sequence can only be edited when campaign status is draft or paused.",
        )


def _assert_variant_content_unique(step_id: str, subject_line: str, email_body: str, db: Session, *, exclude_email_id: str | None = None) -> None:
    q = db.query(StepEmail).filter(
        StepEmail.step_id == step_id,
        func.lower(func.trim(StepEmail.subject_line)) == subject_line.strip().lower(),
        func.trim(StepEmail.email_body) == email_body.strip(),
    )
    if exclude_email_id:
        q = q.filter(StepEmail.email_id != exclude_email_id)
    if q.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate variant content is not allowed in the same step.",
        )


def list_steps(campaign_id: str, db: Session) -> list[SequenceStep]:
    return (
        db.query(SequenceStep)
        .options(joinedload(SequenceStep.email_variants))
        .filter(SequenceStep.campaign_id == campaign_id)
        .order_by(SequenceStep.step_number)
        .all()
    )


def _reconcile_lead_schedules_after_sequence_change(campaign_id: str, db: Session) -> None:
    """
    Keep lead scheduling aligned with sequence edits.

    Cases covered:
    - New step added after leads were completed (next_step_id/next_eligible_at NULL)
    - Step removed causing leads to reference a missing next_step_id

    Important: do not rewrite leads that already have a valid next_step_id,
    otherwise queue ordering gets reset unexpectedly.
    """
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    if not campaign:
        return

    steps = (
        db.query(SequenceStep)
        .filter(SequenceStep.campaign_id == campaign_id)
        .order_by(SequenceStep.step_number.asc())
        .all()
    )
    step_by_id = {step.step_id: step for step in steps}
    first_step = steps[0] if steps else None
    last_step = steps[-1] if steps else None
    now = datetime.now(timezone.utc)

    leads = (
        db.query(Lead)
        .filter(
            Lead.campaign_id == campaign_id,
            Lead.lead_status == "active",
        )
        .all()
    )

    for lead in leads:
        # In-flight workers should not be rewritten.
        if lead.delivery_state == "sending":
            continue

        if not steps:
            lead.next_step_id = None
            lead.next_eligible_at = None
            if lead.delivery_state == "queued":
                lead.delivery_state = "completed"
            continue

        current_step = step_by_id.get(lead.next_step_id) if lead.next_step_id else None
        if current_step:
            # Preserve existing queue state/schedule for leads that already
            # point to a valid step.
            continue

        if lead.delivery_state == "completed":
            # Sequence was extended after completion: continue at new last step.
            lead.next_step_id = last_step.step_id
            lead.next_eligible_at = sending_engine_service._next_step_schedule_utc(
                campaign,
                last_step,
                now,
            )
            lead.delivery_state = "queued"
            continue

        if lead.delivery_state in {"queued", "failed", "paused", "sent"}:
            # Missing/removed step pointer: recover to first step so lead remains schedulable.
            lead.next_step_id = first_step.step_id
            lead.next_eligible_at = sending_engine_service._next_step_schedule_utc(
                campaign,
                first_step,
                now,
            )
            lead.delivery_state = "queued"


def create_step(
    campaign_id: str,
    step_number: int,
    wait_days: int,
    send_time: Optional[str],
    send_window_end: Optional[str],
    send_days: list,
    email_variants_data: list[dict],
    db: Session,
) -> SequenceStep:
    _assert_sequence_editable(campaign_id, db)
    if send_time is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="send_time is required when creating a step.",
        )
    _assert_send_window_times(send_time, send_window_end)
    if not send_days:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="send_days must include at least one weekday.",
        )
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
        send_window_end=send_window_end,
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

    _reconcile_lead_schedules_after_sequence_change(campaign_id, db)
    db.commit()
    db.refresh(step)
    return step


def update_step(
    step_id: str,
    campaign_id: str,
    updates: dict,
    db: Session,
) -> SequenceStep:
    _assert_sequence_editable(campaign_id, db)
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

    # Apply explicit PATCH fields. Allow null for send_time / send_window_end only. Ignore send_days=null.
    nullable_step_fields = frozenset({"send_time", "send_window_end"})
    for field, value in updates.items():
        if field == "send_days" and value is None:
            continue
        if value is None and field not in nullable_step_fields:
            continue
        setattr(step, field, value)
    _assert_send_window_times(step.send_time, step.send_window_end)
    db.commit()
    db.refresh(step)
    return step


def delete_step(step_id: str, campaign_id: str, db: Session) -> None:
    _assert_sequence_editable(campaign_id, db)
    step = _get_step_or_404(step_id, campaign_id, db)
    db.delete(step)
    db.flush()
    _reconcile_lead_schedules_after_sequence_change(campaign_id, db)
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
    db: Session,
) -> StepEmail:
    _assert_sequence_editable(campaign_id, db)
    _get_step_or_404(step_id, campaign_id, db)
    _assert_variant_content_unique(step_id, subject_line, email_body, db)
    variant = StepEmail(
        email_id=str(uuid.uuid4()),
        step_id=step_id,
        subject_line=subject_line,
        email_body=email_body,
        from_name=from_name,
    )
    db.add(variant)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate variant content is not allowed in the same step.",
        )
    db.refresh(variant)
    return variant


def update_variant(
    email_id: str,
    step_id: str,
    campaign_id: str,
    updates: dict,
    db: Session,
) -> StepEmail:
    _assert_sequence_editable(campaign_id, db)
    _get_step_or_404(step_id, campaign_id, db)
    variant = _get_variant_or_404(email_id, step_id, db)
    next_subject = updates.get("subject_line", variant.subject_line)
    next_body = updates.get("email_body", variant.email_body)
    if next_subject is not None and next_body is not None:
        _assert_variant_content_unique(
            step_id,
            next_subject,
            next_body,
            db,
            exclude_email_id=email_id,
        )
    for field, value in updates.items():
        if value is not None:
            setattr(variant, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate variant content is not allowed in the same step.",
        )
    db.refresh(variant)
    return variant


def delete_variant(email_id: str, step_id: str, campaign_id: str, db: Session) -> None:
    _assert_sequence_editable(campaign_id, db)
    _get_step_or_404(step_id, campaign_id, db)
    variant = _get_variant_or_404(email_id, step_id, db)
    db.delete(variant)
    db.commit()

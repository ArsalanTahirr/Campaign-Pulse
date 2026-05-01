"""
services/unibox/campaign_tagging_service.py — Attach or remove a campaign tag
on a UniboxThread, and update lead pipeline_status.

Campaign Tagging
────────────────
Any thread can be tagged with a Campaign to group it in the Campaigns sidebar
view.  A tag is a simple nullable FK (unibox_thread.campaign_id) — no
separate join table needed.  Rules:
  - campaign_id must belong to the same workspace as the thread.
  - Passing campaign_id=None removes the tag.

Pipeline Status
───────────────
The Unibox Status sidebar shows leads grouped by pipeline stage.
Allowed values: lead | interested | meeting-booked | meeting-completed | won
Updating pipeline_status on a thread is done by updating the linked
lead.pipeline_status.  Orphan threads (no lead) cannot have a pipeline status.
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy.orm import Session

from app import repositories
from app.models import Campaign, Lead, UniboxThread

PIPELINE_STATUSES = frozenset(
    {"lead", "interested", "meeting-booked", "meeting-completed", "won"}
)


def update_thread(
    *,
    thread_id: str,
    workspace_id: str,
    campaign_id,  # Optional[str] | _UnsetType  — use _UNSET if caller didn't provide it
    pipeline_status: Optional[str],
    db: Session,
) -> UniboxThread:
    """
    Apply a campaign tag and/or pipeline status update to a thread.

    Parameters
    ----------
    thread_id       : Target thread.
    workspace_id    : Authorisation scope.
    campaign_id     : New campaign FK (None to untag; _UNSET means "do not change").
    pipeline_status : New pipeline stage for the linked lead.
    db              : SQLAlchemy Session (caller commits).

    Returns
    -------
    Updated UniboxThread.

    Raises
    ------
    404 if thread or campaign not found in workspace.
    422 if pipeline_status value is invalid, or if setting pipeline on orphan thread.
    """
    thread = repositories.unibox_repository.get_thread_by_id(thread_id, workspace_id, db)
    if thread is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Thread {thread_id} not found.",
        )

    if campaign_id is _UNSET:
        pass  # Not provided — don't touch campaign_id.
    elif campaign_id is not None:
        _validate_campaign(campaign_id, workspace_id, db)
        thread.campaign_id = campaign_id
    else:
        # caller explicitly passed campaign_id=None → remove tag
        thread.campaign_id = None

    if pipeline_status is not None:
        if pipeline_status not in PIPELINE_STATUSES:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid pipeline_status. Must be one of: {sorted(PIPELINE_STATUSES)}",
            )
        if thread.is_orphan or thread.lead_id is None:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot set pipeline_status on an orphan thread (no linked lead).",
            )
        lead = db.query(Lead).filter(Lead.lead_id == thread.lead_id).first()
        if lead:
            lead.pipeline_status = pipeline_status

    db.flush()
    return thread


def _validate_campaign(campaign_id: str, workspace_id: str, db: Session) -> None:
    """Raise 404 if the campaign does not belong to the workspace."""
    exists = (
        db.query(Campaign.campaign_id)
        .filter(
            Campaign.campaign_id == campaign_id,
            Campaign.workspace_id == workspace_id,
        )
        .first()
    )
    if not exists:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found in workspace.",
        )


class _UnsetType:
    """Sentinel singleton to distinguish 'not provided' from 'explicitly None'."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


_UNSET = _UnsetType()

"""
services/invitation_service.py — Token-based workspace invitation logic.
"""

import secrets
import uuid
import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models import (
    Collaborator,
    Invitation,
    Role,
    User,
    Workspace,
)
from app.email_utils import send_invitation_email

INVITE_TOKEN_EXPIRE_HOURS = 72
logger = logging.getLogger(__name__)
DEFAULT_ROLE_NAMES = ("Owner", "Agency", "Marketing Manager", "Data Analyst")


def _send_invitation_email_safe(
    to_email: str,
    token: str,
    workspace_name: str,
    inviter_name: str,
    role_name: str,
) -> None:
    try:
        send_invitation_email(
            to_email=to_email,
            token=token,
            workspace_name=workspace_name,
            inviter_name=inviter_name,
            role_name=role_name,
        )
    except Exception:
        # Invitation persistence must not fail when SMTP is down/misconfigured.
        logger.exception("Failed to send invitation email to %s", to_email)


def _ensure_default_roles(db: Session) -> None:
    """
    Runtime safety net: ensure default dimension roles exist.
    The canonical source is Alembic seed migration, but this protects older DBs.
    """
    db.execute(
        text(
            """
            INSERT INTO role (role_id, role_name, permissions)
            VALUES
                (gen_random_uuid(), 'Owner', '{}'::jsonb),
                (gen_random_uuid(), 'Agency', '{}'::jsonb),
                (gen_random_uuid(), 'Marketing Manager', '{}'::jsonb),
                (gen_random_uuid(), 'Data Analyst', '{}'::jsonb)
            ON CONFLICT (role_name) DO NOTHING;
            """
        )
    )
    db.commit()


def _active_invite_exists(workspace_id: str, invitee_email: str, db: Session) -> bool:
    return (
        db.query(Invitation)
        .filter(
            Invitation.workspace_id == workspace_id,
            Invitation.invitee_email == invitee_email,
            Invitation.status == "pending",
        )
        .first()
        is not None
    )


def create_invitation(
    workspace_id: str,
    invited_by_user_id: str,
    invitee_email: str,
    role_id: str,
    db: Session,
) -> Invitation:
    _ensure_default_roles(db)
    invitee_email = invitee_email.strip().lower()

    role = db.query(Role).filter(Role.role_id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")

    invitee_user = db.query(User).filter(User.email == invitee_email).first()
    if not invitee_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitee email does not exist. Ask the user to sign up first.",
        )

    if _active_invite_exists(workspace_id, invitee_email, db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active invitation for this email already exists.",
        )

    # Block if they are already an accepted collaborator
    already_member = (
        db.query(Collaborator)
        .join(User, User.user_id == Collaborator.user_id)
        .filter(
            Collaborator.workspace_id == workspace_id,
            User.email == invitee_email,
            Collaborator.invite_status == "accepted",
        )
        .first()
    )
    if already_member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user is already a member of the workspace.",
        )

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=INVITE_TOKEN_EXPIRE_HOURS)

    inv = Invitation(
        invitation_id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        invited_by=invited_by_user_id,
        invitee_email=invitee_email,
        role_id=role_id,
        token=token,
        status="pending",
        expires_at=expires_at,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    inviter = db.query(User).filter(User.user_id == invited_by_user_id).first()
    workspace = db.query(Workspace).filter(Workspace.workspace_id == workspace_id).first()
    inviter_name = (
        f"{(inviter.first_name or '').strip()} {(inviter.last_name or '').strip()}".strip()
        if inviter else ""
    ) or "A teammate"
    workspace_name = workspace.workspace_name if workspace else "your workspace"
    _send_invitation_email_safe(
        to_email=invitee_email,
        token=token,
        workspace_name=workspace_name,
        inviter_name=inviter_name,
        role_name=role.role_name,
    )
    return inv


def list_invitable_roles(db: Session) -> list[Role]:
    _ensure_default_roles(db)
    # Owner role is intentionally excluded from invite assignment.
    return (
        db.query(Role)
        .filter(Role.role_name.in_(["Agency", "Marketing Manager", "Data Analyst"]))
        .order_by(Role.role_name)
        .all()
    )


def get_invitation_by_token(token: str, db: Session) -> Invitation:
    inv = db.query(Invitation).filter(Invitation.token == token).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found."
        )
    if inv.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invitation has already been {inv.status}.",
        )
    if datetime.now(timezone.utc) > inv.expires_at:
        inv.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Invitation token has expired."
        )
    return inv


def accept_invitation(token: str, accepting_user_id: str, db: Session) -> Workspace:
    inv = get_invitation_by_token(token, db)

    accepting_user = db.query(User).filter(User.user_id == accepting_user_id).first()
    if not accepting_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if accepting_user.email.strip().lower() != inv.invitee_email.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sign in with the email address this invitation was sent to.",
        )

    existing = (
        db.query(Collaborator)
        .filter(
            Collaborator.workspace_id == inv.workspace_id,
            Collaborator.user_id == accepting_user_id,
        )
        .first()
    )
    if existing and existing.invite_status == "accepted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already a member of this workspace.",
        )

    if existing:
        existing.invite_status = "accepted"
        existing.role_id = inv.role_id
        collab = existing
    else:
        collab = Collaborator(
            member_id=str(uuid.uuid4()),
            workspace_id=inv.workspace_id,
            user_id=accepting_user_id,
            role_id=inv.role_id,
            invite_status="accepted",
        )
        db.add(collab)
        db.flush()

    inv.status = "accepted"
    inv.responded_at = datetime.now(timezone.utc)
    db.commit()

    workspace = db.query(Workspace).filter(Workspace.workspace_id == inv.workspace_id).first()
    return workspace


def cancel_invitation(invitation_id: str, workspace_id: str, db: Session) -> None:
    inv = (
        db.query(Invitation)
        .filter(
            Invitation.invitation_id == invitation_id,
            Invitation.workspace_id == workspace_id,
        )
        .first()
    )
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found."
        )
    if inv.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invitation is already {inv.status} and cannot be cancelled.",
        )
    inv.status = "cancelled"
    db.commit()


def list_workspace_invitations(workspace_id: str, db: Session) -> list[Invitation]:
    return (
        db.query(Invitation)
        .filter(Invitation.workspace_id == workspace_id)
        .order_by(Invitation.created_at.desc())
        .all()
    )

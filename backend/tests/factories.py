"""
tests/factories.py — Helper functions for creating test data.

Key ORM naming conventions mirrored here:
  Workspace.workspace_name   (not .name)
  Collaborator.member_id     (not .collaborator_id)
  Collaborator.role_id       (single-role model)
  Role.role_name             (not .name)
  Campaign.campaign_name     (not .name)
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.auth import create_access_token, hash_password
from app.models import (
    Campaign,
    CampaignSenderPool,
    Collaborator,
    EmailEvent,
    Invitation,
    Lead,
    LocalAuth,
    Role,
    SenderAccount,
    SequenceStep,
    StepEmail,
    User,
    Workspace,
)


def make_user(db, email=None, first_name="Test", last_name="User", verified=True):
    email = email or f"user_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        user_id=str(uuid.uuid4()),
        email=email,
        first_name=first_name,
        last_name=last_name,
        is_verified=verified,
    )
    db.add(user)
    # LocalAuth PK is user_id (shared 1:1 with users — no separate auth_id column)
    local = LocalAuth(
        user_id=user.user_id,
        password_hash=hash_password("Test1234!"),
        verification_token=None,
    )
    db.add(local)
    db.commit()
    return user


def make_role(db, name):
    role = db.query(Role).filter(Role.role_name == name).first()
    if not role:
        role = Role(
            role_id=str(uuid.uuid4()),
            role_name=name,
            permissions={},
        )
        db.add(role)
        db.commit()
    return role


def make_workspace(db, owner_user):
    ws = Workspace(
        workspace_id=str(uuid.uuid4()),
        workspace_name="Test Workspace",
    )
    db.add(ws)
    db.flush()

    owner_role = make_role(db, "Owner")
    collab = Collaborator(
        member_id=str(uuid.uuid4()),
        workspace_id=ws.workspace_id,
        user_id=owner_user.user_id,
        role_id=owner_role.role_id,
        invite_status="accepted",
    )
    db.add(collab)
    db.commit()
    return ws


def add_member(db, workspace_id, user, role_name):
    role = make_role(db, role_name)
    collab = (
        db.query(Collaborator)
        .filter(
            Collaborator.workspace_id == workspace_id,
            Collaborator.user_id == user.user_id,
        )
        .first()
    )
    if not collab:
        collab = Collaborator(
            member_id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            user_id=user.user_id,
            role_id=role.role_id,
            invite_status="accepted",
        )
        db.add(collab)
    else:
        collab.role_id = role.role_id
    db.commit()
    return collab


def auth_cookies(user):
    """Return a dict of cookies that authenticates the given user."""
    token = create_access_token({"sub": user.user_id, "email": user.email})
    return {"access_token": token}


def make_campaign(
    db,
    workspace_id,
    creator_id=None,
    name="Test Campaign",
    status="draft",
    open_tracking_enabled=True,
):
    campaign = Campaign(
        campaign_id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        created_by=creator_id,
        campaign_name=name,
        status=status,
        open_tracking_enabled=open_tracking_enabled,
    )
    db.add(campaign)
    db.commit()
    return campaign


def make_sender_account(db, workspace_id, email=None, provider_type="smtp"):
    email = email or f"sender_{uuid.uuid4().hex[:8]}@example.com"
    account = SenderAccount(
        account_id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        provider_type=provider_type,
        email=email,
        status="active",
        is_verified=True,
    )
    db.add(account)
    db.commit()
    return account


def attach_sender_to_campaign(db, campaign_id, sender_account_id):
    row = CampaignSenderPool(
        campaign_id=campaign_id,
        sender_account_id=sender_account_id,
    )
    db.add(row)
    db.commit()
    return row


def make_step(db, campaign_id, step_number=1, wait_days=0):
    step = SequenceStep(
        step_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        step_number=step_number,
        wait_days=wait_days,
    )
    db.add(step)
    db.commit()
    return step


def make_step_email(db, step_id, subject="Subject", body="Body text"):
    variant = StepEmail(
        email_id=str(uuid.uuid4()),
        step_id=step_id,
        subject_line=subject,
        email_body=body,
    )
    db.add(variant)
    db.commit()
    return variant


def make_lead(db, campaign_id, email=None, lead_status="active", is_opportunity=False):
    email = email or f"lead_{uuid.uuid4().hex[:8]}@example.com"
    lead = Lead(
        lead_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        email=email,
        lead_status=lead_status,
        is_opportunity=is_opportunity,
    )
    db.add(lead)
    db.commit()
    return lead


def make_email_event(
    db,
    lead_id,
    event_type,
    sender_account_id=None,
    step_id=None,
    occurred_at=None,
):
    """
    Create and persist a single EmailEvent row for use in analytics tests.

    event_type examples: 'sent', 'opened', 'clicked', 'replied', 'bounced'
    event_scope is always 'lead' (warmup events are excluded from analytics).
    occurred_at defaults to now if not provided.
    """
    event = EmailEvent(
        event_id=str(uuid.uuid4()),
        lead_id=lead_id,
        step_id=step_id,
        event_type=event_type,
        event_scope="lead",
        sender_account_id=sender_account_id,
        occurred_at=occurred_at or datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    return event


def make_invitation(db, workspace_id, invited_by, invitee_email, role, status="pending", expired=False):
    delta = timedelta(hours=-1) if expired else timedelta(hours=72)
    inv = Invitation(
        invitation_id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        invited_by=invited_by,
        invitee_email=invitee_email,
        role_id=role.role_id,
        token=secrets.token_urlsafe(32),
        status=status,
        expires_at=datetime.now(timezone.utc) + delta,
    )
    db.add(inv)
    db.commit()
    return inv

"""
services/workspace_service.py — Workspace CRUD and membership helpers.

Key ORM naming to remember:
  Workspace.workspace_name  (not .name)
  Collaborator.member_id    (not .collaborator_id)
  CollaboratorRole.member_id (not .collaborator_id)
  Role.role_name            (not .name)

Ownership is expressed via CollaboratorRole(role.role_name = 'Owner'),
not via a dedicated owner_id column on Workspace.
"""

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Collaborator, CollaboratorRole, Role, Workspace


def get_workspace_or_404(workspace_id: str, db: Session) -> Workspace:
    ws = db.query(Workspace).filter(Workspace.workspace_id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    return ws


def list_user_workspaces(user_id: str, db: Session) -> list[Workspace]:
    """Return all workspaces the user is an accepted collaborator in."""
    return (
        db.query(Workspace)
        .join(Collaborator, Collaborator.workspace_id == Workspace.workspace_id)
        .filter(
            Collaborator.user_id == user_id,
            Collaborator.invite_status == "accepted",
        )
        .all()
    )


def create_workspace(name: str, owner_user_id: str, db: Session) -> Workspace:
    ws = Workspace(
        workspace_id=str(uuid.uuid4()),
        workspace_name=name,
    )
    db.add(ws)
    db.flush()

    # Resolve the Owner role — create it if it doesn't exist yet (idempotent seed)
    owner_role = db.query(Role).filter(Role.role_name == "Owner").first()
    if not owner_role:
        owner_role = Role(role_id=str(uuid.uuid4()), role_name="Owner")
        db.add(owner_role)
        db.flush()

    # Add the creator as an accepted collaborator with the Owner role
    collab = Collaborator(
        member_id=str(uuid.uuid4()),
        workspace_id=ws.workspace_id,
        user_id=owner_user_id,
        invite_status="accepted",
    )
    db.add(collab)
    db.flush()

    collab_role = CollaboratorRole(
        member_id=collab.member_id,
        role_id=owner_role.role_id,
    )
    db.add(collab_role)
    db.commit()
    return ws


def ensure_default_owner_workspace(user_id: str, first_name: str | None, db: Session) -> Workspace:
    """
    Ensure every user owns at least one workspace.
    Ownership is defined by accepted collaborator membership with Owner role.
    """
    owner_workspace = (
        db.query(Workspace)
        .join(Collaborator, Collaborator.workspace_id == Workspace.workspace_id)
        .join(CollaboratorRole, CollaboratorRole.member_id == Collaborator.member_id)
        .join(Role, Role.role_id == CollaboratorRole.role_id)
        .filter(
            Collaborator.user_id == user_id,
            Collaborator.invite_status == "accepted",
            Role.role_name == "Owner",
        )
        .first()
    )
    if owner_workspace:
        return owner_workspace

    base = (first_name or "").strip()
    workspace_name = f"{base}'s Workspace" if base else "My Workspace"
    return create_workspace(name=workspace_name, owner_user_id=user_id, db=db)


def update_workspace(workspace_id: str, name: str, actor_user_id: str, db: Session) -> Workspace:
    ws = get_workspace_or_404(workspace_id, db)

    # Only Owner-role collaborators can rename the workspace
    actor_collab = (
        db.query(Collaborator)
        .filter(
            Collaborator.workspace_id == workspace_id,
            Collaborator.user_id == actor_user_id,
        )
        .first()
    )
    if not actor_collab:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member.")

    actor_role_assignment = (
        db.query(CollaboratorRole)
        .join(Role, Role.role_id == CollaboratorRole.role_id)
        .filter(
            CollaboratorRole.member_id == actor_collab.member_id,
            Role.role_name == "Owner",
        )
        .first()
    )
    if not actor_role_assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace Owner can rename it.",
        )

    ws.workspace_name = name
    db.commit()
    db.refresh(ws)
    return ws

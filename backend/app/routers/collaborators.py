"""
routers/collaborators.py — Workspace collaborator management.

Routes (all under /workspaces/{workspace_id}/collaborators):
    GET    /                              — list accepted collaborators
    PATCH  /{collaborator_id}/role        — change role
    DELETE /{collaborator_id}             — remove from workspace

Note: path param is `collaborator_id` (the API-facing name); the ORM PK is
`member_id`.  We pass it directly to service functions which accept `member_id`.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import Collaborator, User
from app.schemas.collaborator import CollaboratorOut, CollaboratorRoleUpdate, RoleOut
from app.services import collaborator_service

router = APIRouter()


def _to_out(collab: Collaborator) -> CollaboratorOut:
    """Map ORM Collaborator → CollaboratorOut, resolving user fields."""
    full_name: str | None = None
    email: str | None = None
    if collab.user:
        first = collab.user.first_name or ""
        last = collab.user.last_name or ""
        full_name = f"{first} {last}".strip() or None
        email = collab.user.email

    role = RoleOut.model_validate(collab.role) if collab.role else None

    return CollaboratorOut(
        member_id=collab.member_id,      # maps to `collaborator_id` via validation_alias
        user_id=collab.user_id,
        workspace_id=collab.workspace_id,
        invite_status=collab.invite_status,
        joined_at=collab.joined_at,
        full_name=full_name,
        email=email,
        role=role,
    )


@router.get("", response_model=list[CollaboratorOut])
def list_collaborators(
    workspace_id: str,
    _: None = require_permission("view_workspace"),
    db: Session = Depends(get_db),
):
    collabs = collaborator_service.list_collaborators(workspace_id, db)
    return [_to_out(c) for c in collabs]


@router.patch("/{collaborator_id}/role", response_model=CollaboratorOut)
def update_role(
    workspace_id: str,
    collaborator_id: str,
    body: CollaboratorRoleUpdate,
    _: None = require_permission("change_role"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collab = collaborator_service.update_collaborator_role(
        workspace_id=workspace_id,
        member_id=collaborator_id,   # path param name is `collaborator_id`, ORM uses `member_id`
        new_role_id=body.role_id,
        actor_user=user,
        db=db,
    )
    return _to_out(collab)


@router.delete("/{collaborator_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_collaborator(
    workspace_id: str,
    collaborator_id: str,
    _: None = require_permission("remove_collaborator"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collaborator_service.remove_collaborator(
        workspace_id=workspace_id,
        member_id=collaborator_id,
        actor_user=user,
        db=db,
    )

"""
routers/invitations.py — Workspace invitation endpoints.

Routes:
    POST   /workspaces/{workspace_id}/invitations            — send invite
    GET    /workspaces/{workspace_id}/invitations            — list invites
    DELETE /workspaces/{workspace_id}/invitations/{inv_id}   — cancel invite
    GET    /invitations/validate/{token}                     — check token (public)
    POST   /invitations/accept/{token}                       — accept invite (auth required)
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import User
from app.schemas.collaborator import RoleOut
from app.schemas.invitation import InvitationAcceptResponse, InvitationCreate, InvitationOut
from app.services import invitation_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Workspace-scoped invitation management
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/invitations",
    response_model=InvitationOut,
    status_code=status.HTTP_201_CREATED,
)
def send_invitation(
    workspace_id: str,
    body: InvitationCreate,
    _: None = require_permission("invite_collaborator"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return invitation_service.create_invitation(
        workspace_id=workspace_id,
        invited_by_user_id=user.user_id,
        invitee_email=body.invitee_email,
        role_id=body.role_id,
        db=db,
    )


@router.get(
    "/workspaces/{workspace_id}/invitations",
    response_model=list[InvitationOut],
)
def list_invitations(
    workspace_id: str,
    _: None = require_permission("invite_collaborator"),
    db: Session = Depends(get_db),
):
    return invitation_service.list_workspace_invitations(workspace_id, db)


@router.get(
    "/workspaces/{workspace_id}/invitations/roles",
    response_model=list[RoleOut],
)
def list_invitable_roles(
    workspace_id: str,
    _: None = require_permission("invite_collaborator"),
    db: Session = Depends(get_db),
):
    # workspace_id is authorization context; roles are global across workspaces.
    return invitation_service.list_invitable_roles(db)


@router.delete(
    "/workspaces/{workspace_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_invitation(
    workspace_id: str,
    invitation_id: str,
    _: None = require_permission("invite_collaborator"),
    db: Session = Depends(get_db),
):
    invitation_service.cancel_invitation(invitation_id, workspace_id, db)


# ---------------------------------------------------------------------------
# Public / semi-public acceptance flow
# ---------------------------------------------------------------------------


@router.get("/invitations/validate/{token}", response_model=InvitationOut)
def validate_token(token: str, db: Session = Depends(get_db)):
    """
    Called by the frontend before showing the accept UI.
    Returns the invitation details so the page can display workspace name,
    invited role, and expiry.  Does NOT consume the token.
    """
    return invitation_service.get_invitation_by_token(token, db)


@router.post("/invitations/accept/{token}", response_model=InvitationAcceptResponse)
def accept_invitation(
    token: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Authenticated endpoint — the signed-in user accepts the invitation.
    Creates a Collaborator row, assigns the offered role, marks token accepted.
    """
    workspace = invitation_service.accept_invitation(token, user.user_id, db)
    return InvitationAcceptResponse(
        message="Invitation accepted. Welcome to the workspace!",
        workspace_id=workspace.workspace_id,
        workspace_name=workspace.workspace_name,
    )

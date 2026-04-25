"""
dependencies/permissions.py — RBAC permission gate for CampaignPulse.

ORM key names used here:
  Collaborator.member_id    (PK, not collaborator_id)
  CollaboratorRole.member_id (FK, not collaborator_id)
  Role.role_name             (not .name)
"""

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Collaborator, CollaboratorRole, Role, User

# ---------------------------------------------------------------------------
# Permission matrix
# ---------------------------------------------------------------------------

PERMISSION_MATRIX: dict[str, set[str]] = {
    "create_campaign":        {"Owner", "Agency", "Marketing Manager"},
    "edit_campaign":          {"Owner", "Agency", "Marketing Manager"},
    "delete_campaign":        {"Owner", "Agency"},
    "start_campaign":         {"Owner", "Agency", "Marketing Manager"},
    "pause_campaign":         {"Owner", "Agency", "Marketing Manager"},
    "stop_campaign":          {"Owner", "Agency", "Marketing Manager"},
    "manage_sequence":        {"Owner", "Agency", "Marketing Manager"},
    "import_leads":           {"Owner", "Agency", "Marketing Manager"},
    "export_leads":           {"Owner", "Agency", "Marketing Manager", "Data Analyst"},
    "view_leads":             {"Owner", "Agency", "Marketing Manager", "Data Analyst"},
    "view_analytics":         {"Owner", "Agency", "Marketing Manager", "Data Analyst"},
    "invite_collaborator":    {"Owner", "Agency"},
    "remove_collaborator":    {"Owner", "Agency"},
    "change_role":            {"Owner", "Agency"},
    "manage_email_accounts":  {"Owner", "Agency"},
    "view_workspace":         {"Owner", "Agency", "Marketing Manager", "Data Analyst"},
    "edit_workspace":         {"Owner"},
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_user_role_in_workspace(
    user_id: str,
    workspace_id: str,
    db: Session,
) -> str | None:
    """Return the role name for `user_id` in `workspace_id`, or None."""
    row = (
        db.query(Role.role_name)
        .join(CollaboratorRole, CollaboratorRole.role_id == Role.role_id)
        .join(Collaborator, Collaborator.member_id == CollaboratorRole.member_id)
        .filter(
            Collaborator.user_id == user_id,
            Collaborator.workspace_id == workspace_id,
            Collaborator.invite_status == "accepted",
        )
        .first()
    )
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Dependency factory
# ---------------------------------------------------------------------------


def require_permission(action: str):
    """
    Return a FastAPI dependency that enforces `action` from PERMISSION_MATRIX.
    Reads `workspace_id` from the path, resolves the caller's role, and raises
    HTTP 403 if the role is not in the allowed set.
    """
    allowed_roles = PERMISSION_MATRIX.get(action, set())

    def _dependency(
        workspace_id: str = Path(...),
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> None:
        role_name = _get_user_role_in_workspace(user.user_id, workspace_id, db)

        if role_name is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this workspace.",
            )

        if role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your role '{role_name}' cannot perform '{action}'.",
            )

    return Depends(_dependency)

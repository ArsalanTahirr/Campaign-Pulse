"""
services/collaborator_service.py — Collaborator listing and role management.

ORM key names:
  Collaborator.member_id       (PK, not collaborator_id)
  CollaboratorRole.member_id   (FK, not collaborator_id)
  Role.role_name               (not .name)
  Collaborator.role_assignments (relationship name, not .roles)
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models import (
    AuditLog,
    Collaborator,
    CollaboratorRole,
    Role,
    User,
    Workspace,
)
from app.services.audit_log_service import write_audit_log


def list_collaborators(workspace_id: str, db: Session) -> list[Collaborator]:
    return (
        db.query(Collaborator)
        .options(
            joinedload(Collaborator.user),
            joinedload(Collaborator.role_assignments).joinedload(CollaboratorRole.role),
        )
        .filter(
            Collaborator.workspace_id == workspace_id,
            Collaborator.invite_status == "accepted",
        )
        .order_by(Collaborator.joined_at)
        .all()
    )


def _resolve_role_name(collaborator: Collaborator) -> str | None:
    if collaborator.role_assignments:
        return collaborator.role_assignments[0].role.role_name
    return None


def update_collaborator_role(
    workspace_id: str,
    member_id: str,
    new_role_id: str,
    actor_user: User,
    db: Session,
) -> Collaborator:
    collab = (
        db.query(Collaborator)
        .options(joinedload(Collaborator.role_assignments).joinedload(CollaboratorRole.role))
        .filter(
            Collaborator.member_id == member_id,
            Collaborator.workspace_id == workspace_id,
        )
        .first()
    )
    if not collab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collaborator not found.")

    # Business rule:
    # Once an invitation is accepted, role mutation is intentionally disabled.
    # To change access level, remove collaborator membership and invite again
    # with the desired role. This keeps invitation-to-membership flow simple.
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Role changes are disabled after acceptance. "
            "Remove the collaborator and send a new invitation with the new role."
        ),
    )

    new_role = db.query(Role).filter(Role.role_id == new_role_id).first()
    if not new_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")

    old_role_name = _resolve_role_name(collab)

    actor_collab = (
        db.query(Collaborator)
        .options(joinedload(Collaborator.role_assignments).joinedload(CollaboratorRole.role))
        .filter(
            Collaborator.workspace_id == workspace_id,
            Collaborator.user_id == actor_user.user_id,
        )
        .first()
    )
    actor_role_name = _resolve_role_name(actor_collab) if actor_collab else None

    if actor_role_name == "Agency":
        if old_role_name == "Owner" or new_role.role_name == "Owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agency role cannot modify the Owner role.",
            )

    existing_cr = (
        db.query(CollaboratorRole)
        .filter(CollaboratorRole.member_id == member_id)
        .first()
    )
    if existing_cr:
        old_role_id = existing_cr.role_id
        existing_cr.role_id = new_role_id
    else:
        old_role_id = None
        db.add(
            CollaboratorRole(
                member_id=member_id,
                role_id=new_role_id,
            )
        )

    db.flush()

    write_audit_log(
        db=db,
        workspace_id=workspace_id,
        actor_user_id=actor_user.user_id,
        action="role_changed",
        target_type="collaborator",
        target_id=member_id,
        old_value={"role_id": str(old_role_id)} if old_role_id else None,
        new_value={"role_id": new_role_id, "role_name": new_role.role_name},
    )

    db.commit()
    db.refresh(collab)
    return collab


def remove_collaborator(
    workspace_id: str,
    member_id: str,
    actor_user: User,
    db: Session,
) -> None:
    collab = (
        db.query(Collaborator)
        .options(joinedload(Collaborator.role_assignments).joinedload(CollaboratorRole.role))
        .filter(
            Collaborator.member_id == member_id,
            Collaborator.workspace_id == workspace_id,
        )
        .first()
    )
    if not collab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collaborator not found.")

    if collab.user_id == actor_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot remove yourself from the workspace.",
        )

    target_role_name = _resolve_role_name(collab)

    actor_collab = (
        db.query(Collaborator)
        .options(joinedload(Collaborator.role_assignments).joinedload(CollaboratorRole.role))
        .filter(
            Collaborator.workspace_id == workspace_id,
            Collaborator.user_id == actor_user.user_id,
        )
        .first()
    )
    actor_role_name = _resolve_role_name(actor_collab) if actor_collab else None

    if actor_role_name == "Agency" and target_role_name == "Owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agency role cannot remove an Owner.",
        )

    if target_role_name == "Owner":
        owner_count = (
            db.query(Collaborator)
            .join(CollaboratorRole, CollaboratorRole.member_id == Collaborator.member_id)
            .join(Role, Role.role_id == CollaboratorRole.role_id)
            .filter(
                Collaborator.workspace_id == workspace_id,
                Collaborator.invite_status == "accepted",
                Role.role_name == "Owner",
            )
            .count()
        )
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the last Owner of a workspace.",
            )

    write_audit_log(
        db=db,
        workspace_id=workspace_id,
        actor_user_id=actor_user.user_id,
        action="collaborator_removed",
        target_type="collaborator",
        target_id=member_id,
        old_value={"role": target_role_name, "user_id": str(collab.user_id)},
        new_value=None,
    )

    db.delete(collab)
    db.commit()

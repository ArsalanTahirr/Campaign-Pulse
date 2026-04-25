"""
routers/workspaces.py — Workspace management endpoints.

Routes (all mounted under /workspaces by main.py):
    GET    /workspaces                       — list workspaces for current user
    POST   /workspaces                       — create a workspace
    GET    /workspaces/{workspace_id}        — get a single workspace
    PATCH  /workspaces/{workspace_id}        — rename (Owner only)
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import User
from app.schemas.workspace import WorkspaceCreate, WorkspaceOut, WorkspaceUpdate
from app.services import workspace_service

router = APIRouter()


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return workspace_service.list_user_workspaces(user.user_id, db)


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    body: WorkspaceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return workspace_service.create_workspace(body.name, user.user_id, db)


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(
    workspace_id: str,
    _: None = require_permission("view_workspace"),
    db: Session = Depends(get_db),
):
    return workspace_service.get_workspace_or_404(workspace_id, db)


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def update_workspace(
    workspace_id: str,
    body: WorkspaceUpdate,
    _: None = require_permission("edit_workspace"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.name:
        return workspace_service.get_workspace_or_404(workspace_id, db)
    return workspace_service.update_workspace(workspace_id, body.name, user.user_id, db)

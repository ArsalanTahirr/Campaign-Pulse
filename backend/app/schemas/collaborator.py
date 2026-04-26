"""
schemas/collaborator.py — Pydantic v2 models for workspace collaborators.

ORM primary key is `member_id`; exposed as `collaborator_id` in the API.
`joined_at` is the ORM timestamp column (not `created_at`).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RoleOut(BaseModel):
    role_id: str
    # ORM column is `role_name`; exposed as `name`.
    name: str = Field(validation_alias="role_name")

    model_config = {"from_attributes": True, "populate_by_name": True}


class CollaboratorOut(BaseModel):
    # ORM primary key is `member_id`; expose as `collaborator_id`.
    collaborator_id: str = Field(validation_alias="member_id")
    user_id: str
    workspace_id: str
    invite_status: str
    joined_at: Optional[datetime] = None

    # Resolved from the User relationship
    full_name: Optional[str] = None
    email: Optional[str] = None

    # Single role assigned to this collaborator membership.
    role: Optional[RoleOut] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class CollaboratorRoleUpdate(BaseModel):
    role_id: str = Field(..., description="UUID of the new role to assign.")

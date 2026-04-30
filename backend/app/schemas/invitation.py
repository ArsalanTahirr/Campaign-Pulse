"""
schemas/invitation.py — Pydantic v2 models for the invitation flow.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class InvitationCreate(BaseModel):
    invitee_email: EmailStr
    role_id: str = Field(..., description="UUID of the role to grant upon acceptance.")


class InvitationOut(BaseModel):
    invitation_id: str
    workspace_id: str
    invitee_email: str
    role_id: str
    status: str
    expires_at: datetime
    created_at: datetime
    responded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class InvitationAcceptResponse(BaseModel):
    """Returned after a successful token acceptance."""
    message: str
    workspace_id: str
    workspace_name: str

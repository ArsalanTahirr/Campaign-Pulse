"""
schemas/ — Pydantic v2 request / response models for CampaignPulse.

This package replaces the former top-level schemas.py module.  All auth
schemas are re-exported here for backward-compatibility with routers/users.py
which does `from app.schemas import LoginRequest, SignupRequest, ...`.
"""

# Auth schemas (re-exported for backward-compat with routers/users.py)
from app.schemas.auth import (
    GenderEnum,
    LoginRequest,
    ResetPasswordConfirmRequest,
    ResetPasswordRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)

from app.schemas.workspace import WorkspaceOut, WorkspaceCreate, WorkspaceUpdate
from app.schemas.invitation import (
    InvitationCreate,
    InvitationOut,
    InvitationAcceptResponse,
)
from app.schemas.collaborator import (
    CollaboratorOut,
    CollaboratorRoleUpdate,
)
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignOut,
    CampaignRunOut,
)
from app.schemas.sequence import (
    StepEmailCreate,
    StepEmailUpdate,
    StepEmailOut,
    SequenceStepCreate,
    SequenceStepUpdate,
    SequenceStepOut,
)
from app.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadOut,
    LeadImportSessionOut,
)

__all__ = [
    # workspace
    "WorkspaceOut",
    "WorkspaceCreate",
    "WorkspaceUpdate",
    # invitation
    "InvitationCreate",
    "InvitationOut",
    "InvitationAcceptResponse",
    # collaborator
    "CollaboratorOut",
    "CollaboratorRoleUpdate",
    # campaign
    "CampaignCreate",
    "CampaignUpdate",
    "CampaignOut",
    "CampaignRunOut",
    # sequence
    "StepEmailCreate",
    "StepEmailUpdate",
    "StepEmailOut",
    "SequenceStepCreate",
    "SequenceStepUpdate",
    "SequenceStepOut",
    # lead
    "LeadCreate",
    "LeadUpdate",
    "LeadOut",
    "LeadImportSessionOut",
]

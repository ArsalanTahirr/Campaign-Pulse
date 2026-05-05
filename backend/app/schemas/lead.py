"""
schemas/lead.py — Pydantic v2 models for Leads and LeadImportSessions.

ORM column is `lead_status`; exposed as `status` in the API via validation_alias.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------


class LeadCreate(BaseModel):
    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    custom_variables: Optional[dict[str, Any]] = Field(
        None,
        description="Arbitrary merge-tag values stored as JSONB.",
    )


class LeadUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(
        None,
        description="Lead delivery status (active | replied | unsubscribed | bounced | completed).",
    )
    custom_variables: Optional[dict[str, Any]] = None


class LeadOut(BaseModel):
    lead_id: str
    campaign_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    # ORM column is `lead_status`; exposed as `status` for a clean API surface.
    status: str = Field(validation_alias="lead_status")
    custom_variables: Optional[dict[str, Any]] = None
    import_session_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


# ---------------------------------------------------------------------------
# LeadImportSession
# ---------------------------------------------------------------------------


class LeadImportSessionOut(BaseModel):
    session_id: str
    campaign_id: str
    imported_by: str
    file_name: str
    row_count: int
    imported_count: int
    skipped_count: int
    error_count: int
    error_details: Optional[Any] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

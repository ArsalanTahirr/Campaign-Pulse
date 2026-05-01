"""
schemas/unibox.py — Pydantic v2 request/response schemas for the Unibox feature.

All UUIDs are represented as plain strings (consistent with the rest of the
project's schema conventions).  Timestamps are returned as ISO 8601 strings
via FastAPI's default JSON serialisation of datetime objects.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Shared / embedded schemas
# ---------------------------------------------------------------------------


class LeadSummary(BaseModel):
    """Minimal lead context embedded inside thread responses."""

    lead_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    company_name: Optional[str] = None
    pipeline_status: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Thread schemas
# ---------------------------------------------------------------------------

PIPELINE_STATUSES = frozenset(
    {"lead", "interested", "meeting-booked", "meeting-completed", "won"}
)


class ThreadSummary(BaseModel):
    """
    One item in the paginated thread list returned by GET /unibox/threads.
    Contains just enough data to render the conversation card in the sidebar.
    """

    thread_id: str
    subject: str
    contact_name: str
    contact_email: str
    last_message_at: datetime
    is_read: bool
    is_orphan: bool
    pipeline_status: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    inbox_id: str
    inbox_email: str
    unread_count: int

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    """A single email message as returned inside a thread detail response."""

    message_id: str
    direction: str
    from_address: str
    to_addresses: list[str]
    cc_addresses: Optional[list[str]] = None
    subject: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    is_read: bool
    is_orphan: bool
    status: str
    received_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadDetail(BaseModel):
    """
    Full thread detail returned by GET /unibox/threads/{thread_id}.
    Includes the complete ordered list of messages.
    """

    thread_id: str
    subject: str
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    pipeline_status: Optional[str] = None
    lead: Optional[LeadSummary] = None
    is_orphan: bool
    created_at: datetime
    messages: list[MessageOut]

    model_config = {"from_attributes": True}


class ThreadPaginatedResponse(BaseModel):
    """Paginated response for GET /unibox/threads."""

    total: int
    page: int
    page_size: int
    items: list[ThreadSummary]


class ThreadUpdate(BaseModel):
    """
    PATCH /unibox/threads/{thread_id} — update campaign tag or pipeline status.
    All fields are optional; only provided fields are updated.
    """

    campaign_id: Optional[str] = None
    pipeline_status: Optional[str] = None

    @field_validator("pipeline_status")
    @classmethod
    def validate_pipeline_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PIPELINE_STATUSES:
            raise ValueError(
                f"pipeline_status must be one of: {sorted(PIPELINE_STATUSES)}"
            )
        return v


class ThreadUpdateOut(BaseModel):
    """Response for PATCH /unibox/threads/{thread_id}."""

    thread_id: str
    campaign_id: Optional[str] = None
    pipeline_status: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Reply schemas
# ---------------------------------------------------------------------------


class ReplyCreate(BaseModel):
    """
    POST /unibox/threads/{thread_id}/reply — compose and send an outbound reply.
    At least one of body_text or body_html must be non-empty.
    """

    body_text: Optional[str] = None
    body_html: Optional[str] = None
    sender_account_id: str

    @model_validator(mode="after")
    def at_least_one_body(self) -> "ReplyCreate":
        if not (self.body_text or "").strip() and not (self.body_html or "").strip():
            raise ValueError("At least one of body_text or body_html must be provided and non-empty.")
        return self


class ReplyOut(BaseModel):
    """Response for POST /unibox/threads/{thread_id}/reply."""

    message_id: str
    thread_id: str
    direction: str
    from_address: str
    to_addresses: list[str]
    subject: str
    body_text: Optional[str] = None
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Mark-read schema
# ---------------------------------------------------------------------------


class MarkReadUpdate(BaseModel):
    """PATCH /unibox/threads/{thread_id}/messages/{message_id}/read"""

    is_read: bool


class MarkReadOut(BaseModel):
    """Response for the mark-read endpoint."""

    message_id: str
    is_read: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Search schemas
# ---------------------------------------------------------------------------


class SearchResultItem(BaseModel):
    """One item in the full-text search result list."""

    message_id: str
    thread_id: str
    thread_subject: str
    direction: str
    from_address: str
    body_snippet: Optional[str] = None
    received_at: Optional[datetime] = None
    created_at: datetime
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    inbox_email: str

    model_config = {"from_attributes": True}


class SearchPaginatedResponse(BaseModel):
    """Paginated response for GET /unibox/search."""

    total: int
    page: int
    page_size: int
    items: list[SearchResultItem]


# ---------------------------------------------------------------------------
# Inbox list schema
# ---------------------------------------------------------------------------


class InboxOut(BaseModel):
    """One sender account as returned by GET /unibox/inboxes."""

    inbox_id: str
    email: str
    provider_type: str
    status: str
    unread_count: int

    model_config = {"from_attributes": True}


class InboxListResponse(BaseModel):
    """Response for GET /unibox/inboxes."""

    items: list[InboxOut]

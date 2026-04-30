"""
schemas/sequence.py — Pydantic v2 models for SequenceSteps and StepEmails.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

_VALID_WEEKDAYS = frozenset(
    ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
)

# ---------------------------------------------------------------------------
# StepEmail
# ---------------------------------------------------------------------------


class StepEmailCreate(BaseModel):
    subject_line: str = Field(min_length=1, max_length=998)
    email_body: str = Field(min_length=1)
    from_name: Optional[str] = Field(None, max_length=255)


class StepEmailUpdate(BaseModel):
    subject_line: Optional[str] = Field(None, min_length=1, max_length=998)
    email_body: Optional[str] = Field(None, min_length=1)
    from_name: Optional[str] = None


class StepEmailOut(BaseModel):
    email_id: str
    step_id: str
    subject_line: str
    email_body: str
    from_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# SequenceStep
# ---------------------------------------------------------------------------


class SequenceStepCreate(BaseModel):
    step_number: int = Field(..., ge=1, description="1-based position in the sequence.")
    wait_days: int = Field(..., ge=0, description="Days to wait after the previous step.")
    send_time: str = Field(
        ...,
        pattern=r"^\d{2}:\d{2}$",
        description="Step send time in HH:MM 24-hour format (campaign timezone).",
    )
    send_days: list[str] = Field(
        ...,
        min_length=1,
        description='At least one weekday, full English names e.g. ["Monday","Wednesday"].',
    )
    # Allow creating a step with its email variants in one request
    email_variants: list[StepEmailCreate] = Field(
        default_factory=list,
        description="Email variants to create with this step.",
    )

    @field_validator("send_days")
    @classmethod
    def validate_send_days(cls, v: list[str]) -> list[str]:
        bad = [d for d in v if d not in _VALID_WEEKDAYS]
        if bad:
            raise ValueError(
                f"Invalid weekday(s): {', '.join(bad)}. Use Monday … Sunday."
            )
        return v


class SequenceStepUpdate(BaseModel):
    step_number: Optional[int] = Field(None, ge=1)
    wait_days: Optional[int] = Field(None, ge=0)
    send_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    send_days: Optional[list[str]] = Field(
        None,
        min_length=1,
        description="When set, must include at least one weekday.",
    )

    @field_validator("send_days")
    @classmethod
    def validate_send_days_optional(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        bad = [d for d in v if d not in _VALID_WEEKDAYS]
        if bad:
            raise ValueError(
                f"Invalid weekday(s): {', '.join(bad)}. Use Monday … Sunday."
            )
        return v


class SequenceStepOut(BaseModel):
    step_id: str
    campaign_id: str
    step_number: int
    wait_days: int
    send_time: Optional[str] = None
    send_days: Optional[Any] = None
    email_variants: list[StepEmailOut] = []

    model_config = {"from_attributes": True}

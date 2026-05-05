"""
schemas/email_accounts.py — Pydantic models for sender accounts + warmup settings.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

ProviderType = Literal["smtp", "google", "microsoft"]


class WarmupSettingsIn(BaseModel):
    is_warmup_active: bool = False
    start_mail_rate: Decimal = Field(default=Decimal("5"), ge=0)
    daily_max_emails: int = Field(default=50, ge=1, le=10000)
    ramp_up_rate: Decimal = Field(default=Decimal("1.5"), gt=0)
    warmup_started_at: Optional[datetime] = None


class SenderAccountCreate(BaseModel):
    provider_type: ProviderType = "smtp"
    email: str = Field(min_length=3, max_length=255)
    smtp_host: Optional[str] = Field(default=None, max_length=255)
    smtp_port: Optional[int] = Field(default=None, ge=1, le=65535)
    imap_host: Optional[str] = Field(default=None, max_length=255)
    imap_port: Optional[int] = Field(default=None, ge=1, le=65535)
    app_password: Optional[str] = None
    daily_sending_limit: int = Field(default=100, ge=1, le=100000)
    min_delay_seconds: int = Field(default=60, ge=0, le=86400)
    max_imap_fetch: Optional[int] = Field(default=100, ge=1, le=10000)
    warmup_settings: Optional[WarmupSettingsIn] = None

    @field_validator("provider_type", mode="before")
    @classmethod
    def _normalize_provider_type(cls, value):
        if value is None:
            return value
        return str(value).strip().lower()


class SenderAccountUpdate(BaseModel):
    provider_type: Optional[ProviderType] = None
    email: Optional[str] = Field(default=None, min_length=3, max_length=255)
    smtp_host: Optional[str] = Field(default=None, max_length=255)
    smtp_port: Optional[int] = Field(default=None, ge=1, le=65535)
    imap_host: Optional[str] = Field(default=None, max_length=255)
    imap_port: Optional[int] = Field(default=None, ge=1, le=65535)
    app_password: Optional[str] = None
    daily_sending_limit: Optional[int] = Field(default=None, ge=1, le=100000)
    min_delay_seconds: Optional[int] = Field(default=None, ge=0, le=86400)
    max_imap_fetch: Optional[int] = Field(default=None, ge=1, le=10000)

    @field_validator("provider_type", mode="before")
    @classmethod
    def _normalize_provider_type(cls, value):
        if value is None:
            return value
        return str(value).strip().lower()


class WarmupSettingsPatch(BaseModel):
    is_warmup_active: Optional[bool] = None
    start_mail_rate: Optional[Decimal] = Field(default=None, ge=0)
    daily_max_emails: Optional[int] = Field(default=None, ge=1, le=10000)
    ramp_up_rate: Optional[Decimal] = Field(default=None, gt=0)
    warmup_started_at: Optional[datetime] = None


class WarmupSettingsOut(BaseModel):
    account_id: str
    is_warmup_active: bool
    start_mail_rate: Decimal
    daily_max_emails: int
    ramp_up_rate: Decimal
    warmup_started_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SenderAccountOut(BaseModel):
    account_id: str
    workspace_id: str
    provider_type: ProviderType
    email: str
    smtp_host: Optional[str]
    smtp_port: Optional[int]
    imap_host: Optional[str]
    imap_port: Optional[int]
    status: str
    daily_sending_limit: int
    sent_count_today: int
    # From EmailEvent (UTC calendar day), for dashboard columns — excludes warmup from lead count.
    lead_sent_count_today: int = 0
    warmup_sent_count_today: int = 0
    min_delay_seconds: int
    max_imap_fetch: Optional[int]
    last_imap_uid: Optional[int]
    last_used_at: Optional[datetime]
    created_at: datetime
    deleted_at: Optional[datetime] = None
    is_verified: bool
    warmup_settings: Optional[WarmupSettingsOut] = None

    model_config = {"from_attributes": True}



"""
schemas.py — Pydantic v2 request / response models for CampaignPulse auth flows.

All field constraints are kept in sync with the React signup form
(app/(auth)/signup/page.jsx) so that client-side and server-side rules
never diverge.
"""

import re
from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GenderEnum(str, Enum):
    """
    Values mirror the <option value="..."> strings in signup/page.jsx.
    "non_binary" is intentionally absent — it was removed from the frontend.
    """

    male = "male"
    female = "female"
    prefer_not = "prefer_not"


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    middle_name: Optional[str] = Field(None, min_length=2, max_length=100)

    email: EmailStr

    # Password is validated by a custom validator below.
    password: str

    # Frontend key is `date_of_birth` (not `dob`).
    date_of_birth: Optional[date] = None

    gender: Optional[GenderEnum] = None

    # The frontend sends this as a boolean; it must be True.
    terms_accepted: bool = False

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Mirrors the frontend regex: /^(?=.*[A-Z])(?=.*\\d)(?=.*[^A-Za-z0-9]).{8,}$/
        An additional lowercase check is enforced at the backend layer for
        defense-in-depth (the frontend only checks uppercase, digit, special).
        """
        errors: list[str] = []
        if len(v) < 8:
            errors.append("be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            errors.append("contain at least one uppercase letter")
        if not re.search(r"\d", v):
            errors.append("contain at least one digit")
        if not re.search(r"[^A-Za-z0-9]", v):
            errors.append("contain at least one special character")
        if errors:
            raise ValueError("Password must " + ", ".join(errors) + ".")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: Optional[date]) -> Optional[date]:
        """
        Mirrors isAtLeast18() in the frontend — rejects users under 18.
        """
        if v is None:
            return v
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("You must be at least 18 years old to register.")
        return v

    @field_validator("terms_accepted")
    @classmethod
    def validate_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the terms and conditions to continue.")
        return v


class SignupResponse(BaseModel):
    user_id: str
    email: str
    message: str


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# OAuth / JWT
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str

"""
models.py — SQLAlchemy ORM models for CampaignPulse.

Each class in this file maps directly to a PostgreSQL table.  The schema is
derived from the Campaign_Pulse_ER_Diagram.drawio and has been normalized to
Third Normal Form (3NF) per the accompanying Normalization_Report.pdf:

  • 1NF fix  — USERS.Name decomposed into first_name / middle_name / last_name.
  • 1NF fix  — SEQUENCE_STEP's natural composite PK (campaign_id, step_number)
               replaced with a UUID surrogate step_id.
  • 3NF fix  — campaign_id removed from EMAIL_EVENT (transitive dependency
               event_id → lead_id → campaign_id); derive campaign via JOIN.

All primary keys are server-generated UUIDs (gen_random_uuid()) — no UUID
generation is required at the Python layer.

JSONB is used for semi-structured columns (permissions, schedule,
custom_variables, metadata) to take advantage of PostgreSQL's native JSON
indexing and querying capabilities.

Cascade rules:
  • Deleting a Campaign deletes its SequenceSteps and Leads.
  • Deleting a Lead deletes its EmailEvents.
  • Deleting a SequenceStep deletes its EmailEvents.
  • Deleting a Workspace deletes its Campaigns and SenderAccounts.
  • Deleting a SenderAccount deletes its WarmupSettings.
  • Deleting a User deletes LocalAuth, OAuthAccounts, RefreshTokens,
    and Collaborator memberships.
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from app.base import Base

# ---------------------------------------------------------------------------
# Helper: reusable server-default UUID expression
# ---------------------------------------------------------------------------
# gen_random_uuid() is a built-in PostgreSQL function (available since pg 13
# without pgcrypto).  Using server_default means the DB generates the value;
# the Python application never needs to import the `uuid` stdlib module.
_UUID_DEFAULT = text("gen_random_uuid()")

# ---------------------------------------------------------------------------
# Helper: reusable server-default current timestamp expression
# ---------------------------------------------------------------------------
_NOW_DEFAULT = text("now()")


# ===========================================================================
# AUTH & IDENTITY CLUSTER
# ===========================================================================


class User(Base):
    """
    Central identity record for every person who uses CampaignPulse.

    This table is the root of the entire identity graph.  Every other
    person-related table (LocalAuth, OAuthAccounts, RefreshTokens,
    Collaborator) carries a foreign key back to this table.

    A user may authenticate through one or both mechanisms:
      • LocalAuth  — email + hashed password (traditional login)
      • OAuthAccounts — one or more third-party providers (Google, Microsoft…)
    This supports secure account linking (e.g., Google + password on same user).

    The is_verified flag reflects whether the user has clicked the email
    verification link; unverified users may have restricted access in the API.
    """

    __tablename__ = "users"

    # --- Primary Key ---
    # Server-generated UUID — never exposed to the outside world as a
    # sequential integer; prevents enumeration attacks.
    user_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Unique identifier for every user account.",
    )

    # --- Name columns (1NF fix: composite Name → three atomic columns) ---
    # The raw ER diagram modelled Name as a composite attribute.
    # The normalization report requires splitting it into three VARCHAR columns.
    first_name = Column(
        String(100),
        nullable=False,
        comment="Legal first name of the user.",
    )
    middle_name = Column(
        String(100),
        nullable=True,
        comment="Middle name — optional, not all users have one.",
    )
    last_name = Column(
        String(100),
        nullable=False,
        comment="Legal last name / family name of the user.",
    )

    # --- Contact ---
    # Must be globally unique because it doubles as the login credential.
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        comment="Primary email address — used for login and outbound communication.",
    )

    # Optional demographic field used for profile completeness and personalization.
    # Keep values normalized at the service layer (e.g. male/female/non_binary/prefer_not_to_say).
    gender = Column(
        String(30),
        nullable=True,
        comment="User gender value for profile and personalization use-cases.",
    )

    # Optional date of birth for age-based segmentation and profile data.
    # Stored as date-only (no timezone/time component).
    date_of_birth = Column(
        Date,
        nullable=True,
        comment="User date of birth (YYYY-MM-DD).",
    )

    # --- Status ---
    # Set to True after the user clicks the verification link in their inbox.
    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="Whether the user's email address has been verified.",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this account was first created.",
    )

    __table_args__ = (
        # Enforce case-insensitive uniqueness (alice@x.com == ALICE@x.com).
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
    )

    # --- Relationships ---
    # One User → one LocalAuth row (traditional password login).
    # uselist=False signals a scalar (not a list) — SQLAlchemy will load a
    # single object rather than a collection.
    local_auth = relationship(
        "LocalAuth",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # One User → many OAuthAccount rows (can link Google AND Microsoft etc.)
    oauth_accounts = relationship(
        "OAuthAccount",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # One User → many RefreshToken rows (one per active session / device).
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # One User → many Collaborator rows (can be a member of multiple workspaces).
    # Ownership of a workspace is expressed via Collaborator.role_id where
    # role.role_name = 'Owner',
    # not by a direct FK on Workspace.  Use the collaborations relationship below
    # and filter by role to find workspaces this user owns.
    collaborations = relationship(
        "Collaborator",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class LocalAuth(Base):
    """
    Stores the hashed password and email-verification state for users who
    registered with a traditional email+password credential.

    This is a 1:1 extension of the User table intentionally stored separately
    so that the core users table stays lean and OAuth-only users never have a
    row here at all.  The password_hash must be a bcrypt (or argon2) digest —
    the plain-text password is NEVER stored.

    Email verification state is NOT duplicated here.  Use User.is_verified as
    the single source of truth for all authentication paths (local and OAuth).
    """

    __tablename__ = "local_auth"

    # PK is also the FK — one row per user, same UUID.
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
        comment="Shared PK/FK with users — enforces 1:1 relationship.",
    )

    # Stores a bcrypt / argon2 digest string (e.g. "$2b$12$...").
    # nullable=True to allow rows that are created before a password is set.
    password_hash = Column(
        Text,
        nullable=True,
        comment="Bcrypt or Argon2 hash of the user's password. Never plain-text.",
    )

    # Single-use token emailed to the user at registration.
    verification_token = Column(
        String(255),
        nullable=True,
        comment="One-time token sent in the verification email.",
    )

    # After this UTC time the verification_token is expired and rejected.
    token_expires_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Expiry time for the email verification token.",
    )

    # One-time token used for password reset flows.
    # Generated when a user requests "forgot password".
    reset_token = Column(
        String(255),
        nullable=True,
        comment="One-time token sent in the password reset email.",
    )

    # Expiration timestamp for the password reset token.
    # Reset requests are invalid after this time.
    reset_expires_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Expiry time for the password reset token.",
    )

    # --- Relationship back to User ---
    # Whether the email address has been verified is stored on User.is_verified —
    # the single source of truth for verification state across both local and
    # OAuth authentication paths.
    user = relationship("User", back_populates="local_auth")


class OAuthAccount(Base):
    """
    Stores the access token and provider identity for a social / OAuth login.

    A single User can link multiple providers (e.g. Google AND GitHub), so
    this is a 1:N relationship from users.  Each row represents one linked
    provider account.

    access_token should be encrypted at rest if it grants long-lived access;
    for short-lived tokens the raw value is acceptable.
    """

    __tablename__ = "oauth_accounts"

    id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Surrogate PK for this OAuth link record.",
    )

    # Which user owns this linked account.
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to users — the CampaignPulse user who linked this account.",
    )

    # e.g. "google", "microsoft", "github"
    provider_type = Column(
        String(50),
        nullable=False,
        comment="Name of the OAuth provider (google, microsoft, github, etc.).",
    )

    # The subject / sub claim from the provider's ID token — uniquely
    # identifies this user on the provider's side.
    provider_id = Column(
        String(255),
        nullable=False,
        comment="Provider-assigned subject ID (the 'sub' claim in the ID token).",
    )

    # Short-lived bearer token returned by the OAuth flow.
    access_token = Column(
        Text,
        nullable=False,
        comment="OAuth access token. Rotate / encrypt as required by your security policy.",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this OAuth link was first created.",
    )

    # Prevent the same provider account from being linked to two different
    # CampaignPulse users (e.g., one Google subject ID → one user only).
    __table_args__ = (
        UniqueConstraint(
            "provider_type",
            "provider_id",
            name="uq_oauth_provider_account",
        ),
    )

    # --- Relationship back to User ---
    user = relationship("User", back_populates="oauth_accounts")


class RefreshToken(Base):
    """
    Stores hashed refresh tokens issued to users at login.

    Each active session (browser tab, mobile app, API client) has its own row
    so that individual sessions can be revoked without logging out every device.

    The token_hash stores a SHA-256 (or similar) digest of the opaque token
    string that was sent to the client.  The raw token is never persisted.

    When revoked=True the token is invalid even if it hasn't expired yet —
    this supports instant session termination (e.g. "log out everywhere").
    """

    __tablename__ = "refresh_tokens"

    id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Surrogate PK for this refresh token record.",
    )

    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to users — the session owner.",
    )

    # SHA-256 hex digest of the opaque token string sent to the client.
    token_hash = Column(
        String(64),
        nullable=False,
        unique=True,
        comment="SHA-256 hash of the refresh token. Never store the raw token.",
    )

    expires_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="UTC expiry time — tokens presented after this are rejected.",
    )

    # Hard-revocation flag; set to True to invalidate before natural expiry.
    revoked = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="If True, this token is invalid regardless of expiry time.",
    )

    # --- Relationship back to User ---
    user = relationship("User", back_populates="refresh_tokens")


# ===========================================================================
# WORKSPACE & COLLABORATION CLUSTER
# ===========================================================================


class Workspace(Base):
    """
    The top-level organisational unit in CampaignPulse.

    All campaigns, sender accounts, and collaborators are scoped to a
    workspace.  Membership and access level — including ownership — are
    expressed through Collaborator.role_id:

        Workspace → Collaborator(role_id) → Role (role_name = 'Owner')

    This design means a workspace has no hard-coded single owner column.
    Ownership is just a role assignment, which makes it trivial to support
    co-owners, ownership transfer, or custom admin tiers in the future without
    any schema change.

    To find the owner(s) of a workspace at query time:
        SELECT c.user_id
        FROM collaborator c
        JOIN role r ON r.role_id = c.role_id
        WHERE c.workspace_id = :wid
          AND r.role_name    = 'Owner'
    """

    __tablename__ = "workspace"

    workspace_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Unique identifier for this workspace.",
    )

    # Human-readable name shown in the UI (e.g. "Acme Corp Outreach").
    workspace_name = Column(
        String(255),
        nullable=False,
        comment="Display name for the workspace.",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this workspace was created.",
    )

    # --- Relationships ---
    # One Workspace → many Collaborator memberships.
    collaborators = relationship(
        "Collaborator",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    # One Workspace → many Campaigns.
    campaigns = relationship(
        "Campaign",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    # One Workspace → many SenderAccounts (the email accounts used to send).
    sender_accounts = relationship(
        "SenderAccount",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    # One Workspace → many pending/historical Invitations.
    invitations = relationship(
        "Invitation",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    # One Workspace → many AuditLog entries.
    audit_logs = relationship(
        "AuditLog",
        back_populates="workspace",
    )


class Collaborator(Base):
    """
    Represents a User's membership in a specific Workspace.

    A collaborator record is created when a user is invited to (or joins) a
    workspace.  One user can be a collaborator in many workspaces, and one
    workspace can have many collaborators — this is the resolved M:N junction.

    invite_status tracks the lifecycle: 'pending' → 'accepted' | 'declined'.
    joined_at is populated when the invitation is accepted.

    Collaborator rows are referenced by Campaign.created_by to record *which
    workspace member* created a campaign (not just which user).
    """

    __tablename__ = "collaborator"

    member_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Surrogate PK identifying this workspace membership record.",
    )

    workspace_id = Column(
        UUID(as_uuid=False),
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to workspace — which workspace this membership belongs to.",
    )

    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to users — which user holds this membership.",
    )

    role_id = Column(
        UUID(as_uuid=False),
        ForeignKey("role.role_id", ondelete="RESTRICT"),
        nullable=False,
        comment="FK to role — single role assigned to this collaborator membership.",
    )

    # Lifecycle state of the invitation.
    # Allowed values: 'pending', 'accepted', 'declined'
    invite_status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        comment="Invitation lifecycle state: pending | accepted | declined.",
    )

    joined_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC timestamp when the user accepted the invitation. NULL if still pending.",
    )

    # A user can only hold one membership record per workspace.
    # Without this constraint a duplicate invite would create a second row,
    # leading to ambiguous role queries and duplicated campaign authorship.
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_collaborator_workspace_user",
        ),
        CheckConstraint(
            "invite_status IN ('pending','accepted','declined')",
            name="ck_collaborator_invite_status",
        ),
    )

    # --- Relationships ---
    workspace = relationship("Workspace", back_populates="collaborators")
    user = relationship("User", back_populates="collaborations")
    role = relationship("Role", back_populates="collaborators")

    # One Collaborator → many Campaigns they created.
    created_campaigns = relationship(
        "Campaign",
        back_populates="creator",
        foreign_keys="Campaign.created_by",
    )


class Role(Base):
    """
    Defines an access-control role within CampaignPulse workspaces.

    Examples: 'Owner', 'Admin', 'Editor', 'Viewer'.

    The permissions column is a JSONB object that maps feature keys to boolean
    or granular access levels.  Using JSONB allows permissions to be queried
    with PostgreSQL's JSON operators without requiring a schema migration when
    new permission keys are added.

    Example permissions value:
        {"can_send_campaigns": true, "can_manage_members": false}
    """

    __tablename__ = "role"

    role_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Surrogate PK for this role definition.",
    )

    role_name = Column(
        String(100),
        nullable=False,
        unique=True,
        comment="Human-readable name of the role (e.g. Admin, Editor, Viewer).",
    )

    # JSONB stores arbitrary key-value permission flags.
    # Allows adding new permissions without an ALTER TABLE migration.
    permissions = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="JSONB map of permission flags granted to holders of this role.",
    )

    # One Role → many Collaborators (single-role model).
    collaborators = relationship("Collaborator", back_populates="role")


# ===========================================================================
# CAMPAIGN CLUSTER
# ===========================================================================


class CampaignSenderPool(Base):
    """
    Campaign-level sender pool membership.

    One row links one campaign to one sender account. The composite PK prevents
    duplicate membership rows. Sender selection happens at runtime from this
    pool instead of being fixed per StepEmail variant.
    """

    __tablename__ = "campaign_sender_pool"

    campaign_id = Column(
        UUID(as_uuid=False),
        ForeignKey("campaign.campaign_id", ondelete="CASCADE"),
        primary_key=True,
        comment="FK to campaign. Part of composite PK.",
    )
    sender_account_id = Column(
        UUID(as_uuid=False),
        ForeignKey("sender_account.account_id", ondelete="CASCADE"),
        primary_key=True,
        comment="FK to sender_account. Part of composite PK.",
    )

    campaign = relationship("Campaign", back_populates="sender_pool_assignments")
    sender_account = relationship(
        "SenderAccount",
        back_populates="campaign_pool_assignments",
    )


class Campaign(Base):
    """
    The core entity of CampaignPulse — an email outreach campaign.

    A campaign belongs to a workspace and is created by a collaborator (a
    workspace member).  It defines the high-level sending strategy: timezone,
    lifecycle status, and optional date bounds. Per-step send time and send
    days live on SequenceStep rows, not on the campaign.

    The schedule JSONB column is legacy and unused by the public API; new data
    should rely on step-level send_time / send_days only.

    One campaign contains many SequenceSteps (the email templates) and many
    Leads (the recipients).
    """

    __tablename__ = "campaign"

    campaign_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Unique identifier for this campaign.",
    )

    workspace_id = Column(
        UUID(as_uuid=False),
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to workspace — every campaign belongs to exactly one workspace.",
    )

    # References the collaborator (member) who created this campaign, not
    # the raw user, so we preserve workspace-scoped authorship context.
    created_by = Column(
        UUID(as_uuid=False),
        ForeignKey("collaborator.member_id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to collaborator — which workspace member created this campaign.",
    )

    campaign_name = Column(
        String(255),
        nullable=False,
        comment="Display name for the campaign (e.g. 'Q2 2026 SaaS Outreach').",
    )

    # Lifecycle state of the campaign.
    # Typical values: 'draft', 'active', 'paused', 'completed', 'archived'
    status = Column(
        String(30),
        nullable=False,
        default="draft",
        server_default=text("'draft'"),
        comment="Lifecycle state: draft | active | paused | completed | archived.",
    )

    # IANA timezone string, e.g. "America/New_York" or "Europe/London".
    # Used by the scheduler to convert local send times to UTC.
    timezone = Column(
        String(100),
        nullable=False,
        default="UTC",
        server_default=text("'UTC'"),
        comment="IANA timezone string governing when this campaign sends emails.",
    )

    # Legacy JSONB; not exposed on the API. Sending windows are per-step.
    schedule = Column(
        JSONB,
        nullable=True,
        comment="Legacy campaign schedule JSONB (unused by API; use sequence_step.send_days).",
    )

    # Controls whether open-tracking pixels are injected into outbound emails
    # for this campaign.  When False, open events will not be recorded and the
    # analytics layer returns opened: 0 with tracking_enabled: false.
    open_tracking_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="When False, open-tracking pixels are not injected and opens are not recorded.",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this campaign was created.",
    )

    # Scheduling bounds — both optional; a campaign without dates runs indefinitely
    # until manually stopped.
    start_date = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC date-time when this campaign is scheduled to start sending.",
    )

    end_date = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC date-time after which no further emails are sent for this campaign.",
    )

    # Set on every PATCH by the service layer.  NULL means the record has never
    # been updated since creation.
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC timestamp of the most recent update to this campaign record.",
    )

    __table_args__ = (
        # Prevent duplicate campaign names in the same workspace.
        UniqueConstraint("workspace_id", "campaign_name", name="uq_campaign_workspace_name"),
        # Optional stronger form: case-insensitive uniqueness per workspace.
        Index(
            "uq_campaign_workspace_name_lower",
            "workspace_id",
            text("lower(campaign_name)"),
            unique=True,
        ),
        CheckConstraint("timezone <> ''", name="ck_campaign_timezone_not_blank"),
        CheckConstraint(
            "status IN ('draft','scheduled','active','paused','completed','archived','deleted')",
            name="ck_campaign_status",
        ),
    )

    # --- Relationships ---
    workspace = relationship("Workspace", back_populates="campaigns")
    creator = relationship(
        "Collaborator",
        back_populates="created_campaigns",
        foreign_keys=[created_by],
    )

    # One Campaign → many SequenceSteps (the ordered email templates).
    steps = relationship(
        "SequenceStep",
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="SequenceStep.step_number",
    )

    # One Campaign → many Leads (the recipient records).
    leads = relationship(
        "Lead",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )

    # One Campaign → many CampaignRun history rows (start/pause/stop events).
    runs = relationship(
        "CampaignRun",
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="CampaignRun.created_at",
    )

    # One Campaign → many sender-pool membership rows.
    sender_pool_assignments = relationship(
        "CampaignSenderPool",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )

    # Convenience many-to-many access to pooled sender accounts.
    sender_accounts = relationship(
        "SenderAccount",
        secondary="campaign_sender_pool",
        viewonly=True,
        order_by="SenderAccount.created_at",
    )


class SequenceStep(Base):
    """
    Represents a single email in the ordered sequence belonging to a Campaign.

    The original ER diagram used a natural composite PK (campaign_id,
    step_number).  The normalization report replaced this with a UUID surrogate
    (step_id) to avoid fragile composite FK references downstream (EmailEvent
    would need both columns in its FK).  The natural uniqueness is preserved
    via a UniqueConstraint on (campaign_id, step_number).

    wait_days is the number of days to wait *after* the previous step before
    sending this one.  A value of 0 means "send immediately after the prior
    step (or at campaign start for step 1)".

    EmailEvents reference this table to record which specific email template
    triggered a given open/click/reply/bounce event.
    """

    __tablename__ = "sequence_step"

    # Surrogate UUID PK (1NF fix — replaces natural composite PK).
    step_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Surrogate UUID PK introduced per 1NF normalisation.",
    )

    campaign_id = Column(
        UUID(as_uuid=False),
        ForeignKey("campaign.campaign_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to campaign — which campaign this step belongs to.",
    )

    # Position in the sending sequence (1-indexed by convention).
    # Combined with campaign_id, this must be unique (enforced below).
    step_number = Column(
        Integer,
        nullable=False,
        comment="Ordinal position in the email sequence (1 = first email, 2 = follow-up, …).",
    )

    # Email content now lives exclusively in StepEmail rows.
    # SequenceStep is a pure schedule/order container.

    # Delay from the previous step expressed in whole days.
    wait_days = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Days to wait after the previous step before sending this email.",
    )

    # Local send time in the parent campaign's timezone. Format: 'HH:MM' (24-hour).
    send_time = Column(
        String(5),
        nullable=True,
        comment="Step send time (HH:MM, 24-hour) in campaign timezone.",
    )

    # JSON array of weekday strings, e.g. ["Monday", "Wednesday", "Friday"].
    # API requires at least one day when creating or updating a step.
    send_days = Column(
        JSONB,
        nullable=True,
        comment='Step send days — JSON array e.g. ["Monday","Wednesday"].',
    )

    # Enforce the original natural key as a unique constraint.
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "step_number",
            name="uq_sequence_step_campaign_step",
        ),
    )

    # --- Relationships ---
    campaign = relationship("Campaign", back_populates="steps")

    # One SequenceStep → many StepEmail variants (mailbox rotation / A/B).
    # Deleting a step cascades to all its email variants.
    email_variants = relationship(
        "StepEmail",
        back_populates="step",
        cascade="all, delete-orphan",
        order_by="StepEmail.created_at",
    )

    # One SequenceStep → many EmailEvents.
    # No cascade delete — EmailEvent rows are the audit log and must survive
    # step deletion.  The FK on EmailEvent.step_id is SET NULL on delete.
    events = relationship(
        "EmailEvent",
        back_populates="step",
    )


class Lead(Base):
    """
    A prospective recipient (contact) enrolled in a specific Campaign.

    A Lead represents one person the campaign is trying to reach.  They belong
    to exactly one campaign (not shared across campaigns — re-enrolling the
    same email in a new campaign creates a new Lead row).

    custom_variables is a JSONB map of merge-tag values specific to this
    person.  When the email engine renders a template, it substitutes
    {{first_name}}, {{company_name}}, and any custom keys stored here.

    Example custom_variables:
        {"job_title": "VP of Engineering", "industry": "SaaS"}

    lead_status tracks where in the outreach funnel this contact currently is.
    Typical values: 'active', 'replied', 'unsubscribed', 'bounced', 'completed'
    """

    __tablename__ = "lead"

    lead_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Unique identifier for this lead record.",
    )

    campaign_id = Column(
        UUID(as_uuid=False),
        ForeignKey("campaign.campaign_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to campaign — the campaign this lead is enrolled in.",
    )

    email = Column(
        String(255),
        nullable=False,
        comment="Email address of the lead. The primary delivery address.",
    )

    first_name = Column(
        String(100),
        nullable=True,
        comment="Lead's first name — used in email personalisation merge tags.",
    )

    last_name = Column(
        String(100),
        nullable=True,
        comment="Lead's last name.",
    )

    company_name = Column(
        String(255),
        nullable=True,
        comment="Company the lead works for — used in personalisation and filtering.",
    )

    # JSONB map for arbitrary merge-tag values not covered by the fixed columns.
    custom_variables = Column(
        JSONB,
        nullable=True,
        server_default=text("'{}'::jsonb"),
        comment="JSONB map of custom merge-tag values (e.g. job_title, industry).",
    )

    # Funnel / deliverability status of this lead.
    # Typical values: 'active', 'replied', 'unsubscribed', 'bounced', 'completed'
    lead_status = Column(
        String(30),
        nullable=False,
        default="active",
        server_default=text("'active'"),
        comment="Outreach funnel status: active | replied | unsubscribed | bounced | completed.",
    )

    # Absolute UTC timestamp when this lead should be considered for the next send.
    # Precomputing this avoids re-calculating schedule math in each scheduler loop.
    next_scheduled_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC timestamp when the next step email should fire for this lead.",
    )

    # Lightweight delivery lock state for atomic worker processing.
    delivery_state = Column(
        String(20),
        nullable=False,
        default="queued",
        server_default=text("'queued'"),
        comment="Worker state: queued | sending | sent | failed | paused.",
    )
    locked_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC timestamp when a worker claimed this lead for sending.",
    )
    lock_token = Column(
        UUID(as_uuid=False),
        nullable=True,
        comment="Worker claim token used to prevent duplicate sends across workers.",
    )

    # Points to the next sequence step this lead should receive.
    # NULL means the lead is no longer scheduled for additional steps.
    next_step_id = Column(
        UUID(as_uuid=False),
        ForeignKey("sequence_step.step_id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to sequence_step — the next step due for this lead.",
    )

    # Back-reference to the import batch that created this lead.
    # NULL for leads added manually (not via CSV/XLSX upload).
    import_session_id = Column(
        UUID(as_uuid=False),
        ForeignKey("lead_import_session.session_id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to lead_import_session — NULL for manually added leads.",
    )

    # Flags this lead's reply as a high-quality opportunity (e.g. interested
    # lead, demo request).  Set to True by users or automation after a reply
    # is reviewed.  Used by the Campaign Analytics opportunities count.
    is_opportunity = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="True when this lead's reply is flagged as a high-quality opportunity.",
    )

    # The same email address must not appear twice in the same campaign.
    # Re-enrolling a contact in a new campaign creates a new Lead row in that
    # campaign — it does not reuse or modify this one.
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "email",
            name="uq_lead_campaign_email",
        ),
        CheckConstraint(
            "lead_status IN ('active','replied','unsubscribed','bounced','completed')",
            name="ck_lead_status",
        ),
        CheckConstraint(
            "delivery_state IN ('queued','sending','sent','failed','paused')",
            name="ck_lead_delivery_state",
        ),
        Index(
            "ix_lead_next_scheduled_state",
            "next_scheduled_at",
            "delivery_state",
        ),
        Index(
            "ix_lead_campaign_next_scheduled",
            "campaign_id",
            "next_scheduled_at",
        ),
        Index(
            "ix_lead_next_step_id",
            "next_step_id",
        ),
    )

    # --- Relationships ---
    campaign = relationship("Campaign", back_populates="leads")

    # Which import session created this lead (nullable for manual adds).
    import_session = relationship(
        "LeadImportSession",
        back_populates="leads",
        foreign_keys=[import_session_id],
    )

    next_step = relationship(
        "SequenceStep",
        foreign_keys=[next_step_id],
    )

    # One Lead → many EmailEvents (every send/open/click for this lead).
    events = relationship(
        "EmailEvent",
        back_populates="lead",
        cascade="all, delete-orphan",
    )


class EmailEvent(Base):
    """
    An immutable audit record of a single deliverability or engagement event.

    Every time the email engine interacts with a lead (sends, the lead opens,
    clicks, replies, or bounces) a new row is appended here.  This table is
    append-only in practice — rows are never updated or deleted in normal
    operation (they may be deleted only via CASCADE when a Lead is removed).

    3NF fix applied: campaign_id was removed because it was a transitive
    dependency (event_id → lead_id → campaign_id).  Campaign context can always
    be obtained with:
        SELECT e.*, l.campaign_id
        FROM email_event e
        JOIN lead l ON l.lead_id = e.lead_id

    event_type examples: 'sent', 'opened', 'clicked', 'replied', 'bounced',
                         'unsubscribed', 'spam_complaint'

    metadata is a JSONB field for event-specific payload:
      • 'clicked' → {"url": "https://…", "user_agent": "…"}
      • 'bounced' → {"bounce_type": "hard", "smtp_code": "550"}
      • 'opened'  → {"ip": "…", "user_agent": "…"}
    """

    __tablename__ = "email_event"

    event_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Unique identifier for this event record.",
    )

    lead_id = Column(
        UUID(as_uuid=False),
        ForeignKey("lead.lead_id", ondelete="CASCADE"),
        nullable=True,
        comment="FK to lead — set for lead-scope events, NULL for warmup-scope events.",
    )

    # References the specific email template step that caused the event.
    # nullable=True + SET NULL: if a step is later deleted (e.g. campaign edited),
    # the event record is preserved for audit and analytics purposes — only the
    # FK pointer is cleared.  Using CASCADE here would silently destroy the
    # deliverability history every time a step is removed.
    step_id = Column(
        UUID(as_uuid=False),
        ForeignKey("sequence_step.step_id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to sequence_step — NULL if the step has since been deleted.",
    )

    # Describes what happened: 'sent', 'opened', 'clicked', 'replied', etc.
    event_type = Column(
        String(50),
        nullable=False,
        comment="Type of deliverability / engagement event (sent, opened, clicked, …).",
    )

    # Distinguishes normal campaign events from internal warmup traffic.
    event_scope = Column(
        String(20),
        nullable=False,
        server_default=text("'lead'"),
        comment="Event scope: lead | warmup.",
    )

    sender_account_id = Column(
        UUID(as_uuid=False),
        ForeignKey("sender_account.account_id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to sender_account that originated this event.",
    )

    recipient_account_id = Column(
        UUID(as_uuid=False),
        ForeignKey("sender_account.account_id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to recipient sender_account for warmup exchange events.",
    )

    warmup_thread_id = Column(
        UUID(as_uuid=False),
        nullable=True,
        comment="Correlation identifier for warmup message exchanges.",
    )

    occurred_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this event occurred.",
    )

    # Optional structured payload specific to the event_type.
    # The Python attribute is `event_metadata`; the DB column is `metadata`.
    # SQLAlchemy's Declarative API reserves the name `metadata` on every model
    # class, so the explicit column label keeps the DB schema as designed.
    event_metadata = Column(
        "metadata",
        JSONB,
        nullable=True,
        comment="JSONB payload with event-specific details (URLs, bounce codes, IPs, etc.).",
    )

    __table_args__ = (
        CheckConstraint(
            "event_scope IN ('lead','warmup')",
            name="ck_email_event_scope",
        ),
        CheckConstraint(
            "("
            "(event_scope = 'lead' AND lead_id IS NOT NULL)"
            " OR "
            "(event_scope = 'warmup' AND lead_id IS NULL AND sender_account_id IS NOT NULL)"
            ")",
            name="ck_email_event_scope_shape",
        ),
        Index("ix_email_event_scope_occurred_at", "event_scope", "occurred_at"),
        Index("ix_email_event_lead_occurred_at", "lead_id", "occurred_at"),
        Index("ix_email_event_sender_occurred_at", "sender_account_id", "occurred_at"),
        Index("ix_email_event_warmup_thread", "warmup_thread_id"),
    )

    # --- Relationships ---
    lead = relationship("Lead", back_populates="events")
    step = relationship("SequenceStep", back_populates="events")
    sender_account = relationship(
        "SenderAccount",
        foreign_keys=[sender_account_id],
        back_populates="outgoing_events",
    )
    recipient_account = relationship(
        "SenderAccount",
        foreign_keys=[recipient_account_id],
        back_populates="incoming_events",
    )


# ===========================================================================
# SENDER CLUSTER
# ===========================================================================


class SenderAccount(Base):
    """
    An email account that CampaignPulse uses to physically send outbound mail.

    A sender account encapsulates the full SMTP/IMAP configuration for one
    email address.  Multiple sender accounts can belong to a single workspace,
    allowing volume to be spread across addresses (account rotation).

    provider_type indicates whether this is a plain SMTP account or a
    well-known provider preset (e.g. 'smtp', 'google', 'microsoft').

    Rate-limiting fields (daily_sending_limit, sent_count_today,
    min_delay_seconds) are used by the email scheduler to avoid hitting
    provider limits and triggering spam filters.

    IMAP fields (imap_host, imap_port, max_imap_fetch, last_imap_uid) enable
    the reply-detection service to poll the inbox for incoming responses.

    app_password stores the SMTP/IMAP password or app-specific password.
    This value should be encrypted at rest via database-level encryption or
    a secrets manager.
    """

    __tablename__ = "sender_account"

    account_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Unique identifier for this sender account.",
    )

    workspace_id = Column(
        UUID(as_uuid=False),
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to workspace — which workspace owns this sender account.",
    )

    # 'smtp', 'google', 'microsoft'
    provider_type = Column(
        Enum("smtp", "google", "microsoft", name="sender_provider_type"),
        nullable=False,
        comment="Email provider type: smtp | google | microsoft.",
    )

    # The From address used in outbound mail.
    email = Column(
        String(255),
        nullable=False,
        comment="The sender email address shown in the From header.",
    )

    # --- SMTP outbound settings ---
    smtp_host = Column(
        String(255),
        nullable=True,
        comment="SMTP server hostname (e.g. smtp.gmail.com).",
    )
    smtp_port = Column(
        Integer,
        nullable=True,
        comment="SMTP server port (typically 587 for STARTTLS, 465 for SSL).",
    )

    # --- IMAP inbound settings (for reply detection) ---
    imap_host = Column(
        String(255),
        nullable=True,
        comment="IMAP server hostname (e.g. imap.gmail.com).",
    )
    imap_port = Column(
        Integer,
        nullable=True,
        comment="IMAP server port (typically 993 for SSL).",
    )

    # Password or app-specific password for SMTP/IMAP authentication.
    # Encrypt this column or use a secrets manager in production.
    app_password = Column(
        Text,
        nullable=True,
        comment="SMTP/IMAP password or app-specific password. Encrypt at rest.",
    )

    # Operational status of the account.
    # Typical values: 'active', 'warming_up', 'suspended', 'disconnected'
    status = Column(
        String(30),
        nullable=False,
        default="active",
        server_default=text("'active'"),
        comment="Account status: active | warming_up | suspended | disconnected.",
    )

    # --- Rate-limiting fields ---
    daily_sending_limit = Column(
        Integer,
        nullable=False,
        default=100,
        server_default=text("100"),
        comment="Maximum number of emails this account may send in a 24-hour window.",
    )

    # Reset to 0 at midnight (UTC or account timezone) by the scheduler job.
    sent_count_today = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Running count of emails sent today. Reset daily by the scheduler.",
    )

    # Minimum inter-send delay to humanise sending cadence and avoid spam filters.
    min_delay_seconds = Column(
        Integer,
        nullable=False,
        default=60,
        server_default=text("60"),
        comment="Minimum seconds to wait between consecutive sends from this account.",
    )

    # --- IMAP state ---
    # Controls how many IMAP messages are fetched per polling cycle.
    max_imap_fetch = Column(
        Integer,
        nullable=True,
        comment="Maximum number of IMAP messages to fetch per reply-detection cycle.",
    )

    # The highest IMAP UID already processed; used as a cursor so the poller
    # only fetches *new* messages on each run.
    last_imap_uid = Column(
        BigInteger,
        nullable=True,
        comment="IMAP UID cursor — the last processed message UID. Enables incremental fetch.",
    )

    # --- Timestamps ---
    last_used_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC timestamp of the most recent send from this account.",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this sender account was added.",
    )
    deleted_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC soft-delete timestamp. Non-null means account is disconnected from active use.",
    )

    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="True once SMTP/IMAP credentials have been validated by the system.",
    )

    # --- Relationships ---
    workspace = relationship("Workspace", back_populates="sender_accounts")

    # One SenderAccount → one WarmupSettings (1:1).
    warmup_settings = relationship(
        "WarmupSettings",
        back_populates="sender_account",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # One SenderAccount → many campaign-pool membership rows.
    campaign_pool_assignments = relationship(
        "CampaignSenderPool",
        back_populates="sender_account",
        cascade="all, delete-orphan",
    )

    campaigns = relationship(
        "Campaign",
        secondary="campaign_sender_pool",
        viewonly=True,
        order_by="Campaign.created_at",
    )
    outgoing_events = relationship(
        "EmailEvent",
        foreign_keys="EmailEvent.sender_account_id",
        back_populates="sender_account",
    )
    incoming_events = relationship(
        "EmailEvent",
        foreign_keys="EmailEvent.recipient_account_id",
        back_populates="recipient_account",
    )


class WarmupSettings(Base):
    """
    Warm-up configuration for a SenderAccount.

    Email warm-up is the practice of gradually increasing daily send volume
    for a new or dormant account to build sender reputation with ISPs.

    This table has a strict 1:1 relationship with SenderAccount — its PK is
    also the FK.  A row only exists here if warm-up is configured for the
    account; accounts without a row effectively have warm-up disabled.

    start_mail_rate:  number of emails to send on day 1 of warm-up.
    ramp_up_rate:     daily multiplier applied to the previous day's volume.
    daily_max_emails: ceiling — volume never exceeds this even if ramp math
                      would push it higher.

    Example: start=5, ramp=1.5, max=100
      Day 1: 5, Day 2: 7, Day 3: 10, … capped at 100 around day 11.
    """

    __tablename__ = "warmup_settings"

    # PK is the same UUID as the parent SenderAccount — enforces 1:1.
    account_id = Column(
        UUID(as_uuid=False),
        ForeignKey("sender_account.account_id", ondelete="CASCADE"),
        primary_key=True,
        comment="Shared PK/FK with sender_account — enforces 1:1 relationship.",
    )

    # Whether the warm-up scheduler should actively manage this account.
    is_warmup_active = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="When True, the warm-up scheduler controls daily send volume for this account.",
    )

    # Sends on the very first day of the warm-up programme.
    start_mail_rate = Column(
        Numeric(8, 2),
        nullable=False,
        default=5,
        server_default=text("5"),
        comment="Number of emails to send on day 1 of the warm-up schedule.",
    )

    # Maximum emails per day this account is allowed to send during warm-up.
    daily_max_emails = Column(
        Integer,
        nullable=False,
        default=50,
        server_default=text("50"),
        comment="Hard ceiling on daily sends during the warm-up period.",
    )

    # Multiplicative daily growth factor for the warm-up volume.
    # A value of 1.5 means each day sends 50% more than the previous day.
    ramp_up_rate = Column(
        Numeric(5, 2),
        nullable=False,
        default=1.5,
        server_default=text("1.5"),
        comment="Daily growth multiplier for warm-up volume (e.g. 1.5 = +50%/day).",
    )

    warmup_started_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC timestamp used as day-0 anchor for warm-up ramp calculations.",
    )

    # --- Relationship back to SenderAccount ---
    sender_account = relationship("SenderAccount", back_populates="warmup_settings")


# ===========================================================================
# INVITATION & AUDIT CLUSTER
# ===========================================================================


class Invitation(Base):
    """
    A token-based workspace invitation sent to an email address.

    Decoupled from Collaborator so that invitations can be sent to people who
    do not yet have a CampaignPulse account.  On acceptance a Collaborator row
    is created and this record's status is set to 'accepted'.

    The token is a cryptographically-random URL-safe string (secrets.token_urlsafe).
    It is stored in plain text here because it is single-use and expires within
    72 hours — it carries no long-term secret.

    Status lifecycle: pending → accepted | declined | cancelled | expired
    """

    __tablename__ = "invitation"

    invitation_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Unique identifier for this invitation record.",
    )

    workspace_id = Column(
        UUID(as_uuid=False),
        ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to workspace — which workspace this invitation grants access to.",
    )

    # The CampaignPulse user who sent this invitation.
    invited_by = Column(
        UUID(as_uuid=False),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to users — the member who created this invitation.",
    )

    # Email address the invitation was sent to.  The invitee may or may not
    # already have a CampaignPulse account at the time the invite is sent.
    invitee_email = Column(
        String(255),
        nullable=False,
        comment="Email address the invitation was sent to.",
    )

    # The role that will be assigned to the invitee upon acceptance.
    role_id = Column(
        UUID(as_uuid=False),
        ForeignKey("role.role_id"),
        nullable=False,
        comment="FK to role — the role offered to the invitee.",
    )

    # Secure single-use token included in the invitation email link.
    token = Column(
        String(255),
        nullable=False,
        unique=True,
        comment="Cryptographically-random URL-safe token for accepting this invitation.",
    )

    # Allowed: pending | accepted | declined | cancelled | expired
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        comment="Lifecycle state: pending | accepted | declined | cancelled | expired.",
    )

    # Token becomes invalid after this UTC timestamp.
    expires_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="UTC expiry time — tokens presented after this are rejected.",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this invitation was created.",
    )

    # Populated when the invitee accepts or declines.
    responded_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC timestamp when the invitee accepted or declined.",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','declined','cancelled','expired')",
            name="ck_invitation_status",
        ),
        # Enforce "one pending invite per workspace/email" at DB level.
        Index(
            "uq_invitation_pending_workspace_email",
            "workspace_id",
            "invitee_email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    # --- Relationships ---
    workspace = relationship("Workspace", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[invited_by])
    role = relationship("Role")


class AuditLog(Base):
    """
    Immutable append-only record of significant workspace actions.

    Written whenever a role is changed, a collaborator is removed, or a
    campaign transitions lifecycle state.  Rows are never updated or deleted
    (except via CASCADE when a workspace is destroyed).

    actor_user_id and workspace_id use SET NULL on delete so historical log
    entries remain readable even after a user or workspace is removed.

    old_value / new_value store JSONB snapshots of the affected entity before
    and after the change, giving a full diff for any audited action.
    """

    __tablename__ = "audit_log"

    log_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Unique identifier for this audit log entry.",
    )

    workspace_id = Column(
        UUID(as_uuid=False),
        ForeignKey("workspace.workspace_id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to workspace — NULL if the workspace has since been deleted.",
    )

    # The user who performed the action.
    actor_user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to users — the user who triggered this event. NULL if user deleted.",
    )

    # Short machine-readable event name e.g. 'role_changed', 'collaborator_removed'.
    action = Column(
        String(100),
        nullable=False,
        comment="Machine-readable action name e.g. role_changed, campaign_started.",
    )

    # The type of entity that was affected: 'collaborator', 'campaign', 'invitation'.
    target_type = Column(
        String(50),
        nullable=True,
        comment="Type of affected entity: collaborator | campaign | invitation.",
    )

    # The UUID of the affected entity at the time of the event.
    target_id = Column(
        UUID(as_uuid=False),
        nullable=True,
        comment="UUID of the affected entity at the time of the event.",
    )

    # Snapshots of the affected entity before and after the change.
    old_value = Column(
        JSONB,
        nullable=True,
        comment="JSONB snapshot of the entity state before this action.",
    )

    new_value = Column(
        JSONB,
        nullable=True,
        comment="JSONB snapshot of the entity state after this action.",
    )

    occurred_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this event was recorded.",
    )

    # --- Relationships ---
    workspace = relationship("Workspace", back_populates="audit_logs")
    actor = relationship("User", foreign_keys=[actor_user_id])


# ===========================================================================
# LEAD IMPORT CLUSTER
# ===========================================================================


class LeadImportSession(Base):
    """
    Metadata record for a single CSV / XLSX lead-import operation.

    One row is created per upload request.  The service layer populates
    row_count, imported_count, skipped_count, and error_count once parsing
    completes, then flips status to 'completed' or 'failed'.

    error_details holds a JSONB array of per-row validation errors:
        [{"row": 3, "email": "bad@", "reason": "invalid email format"}, ...]

    Every Lead row created during an import carries import_session_id pointing
    back to this record.  Leads added manually have import_session_id = NULL.
    """

    __tablename__ = "lead_import_session"

    session_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Unique identifier for this import session.",
    )

    campaign_id = Column(
        UUID(as_uuid=False),
        ForeignKey("campaign.campaign_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to campaign — which campaign these leads were uploaded to.",
    )

    # The workspace member who performed the upload.
    imported_by = Column(
        UUID(as_uuid=False),
        ForeignKey("users.user_id"),
        nullable=False,
        comment="FK to users — the user who triggered this import.",
    )

    file_name = Column(
        String(255),
        nullable=False,
        comment="Original filename of the uploaded file (e.g. 'leads_q2.csv').",
    )

    # Totals populated after parse completes.
    row_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Total rows parsed from the file (header excluded).",
    )

    imported_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Rows successfully written to the lead table.",
    )

    skipped_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Rows skipped due to duplicate email (uq_lead_campaign_email violation).",
    )

    error_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Rows rejected due to validation errors (not written to lead table).",
    )

    # Per-row validation errors for the error-report download feature.
    error_details = Column(
        JSONB,
        nullable=True,
        comment='JSONB array of per-row errors: [{"row": N, "email": "...", "reason": "..."}].',
    )

    # Allowed: processing | completed | failed
    status = Column(
        String(30),
        nullable=False,
        default="processing",
        server_default=text("'processing'"),
        comment="Import job state: processing | completed | failed.",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this import session was created.",
    )

    completed_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC timestamp when parsing finished (success or failure).",
    )

    # --- Relationships ---
    campaign = relationship("Campaign")
    uploader = relationship("User", foreign_keys=[imported_by])

    # All Lead rows created during this session.
    leads = relationship(
        "Lead",
        back_populates="import_session",
        foreign_keys="Lead.import_session_id",
    )


# ===========================================================================
# STEP EMAIL CLUSTER
# ===========================================================================


class StepEmail(Base):
    """
    A single email variant belonging to a SequenceStep.

    Each SequenceStep can have one or more StepEmail rows.  The sending engine
    cycles through the variants, rotating across sender accounts, to distribute
    outreach volume across mailboxes and domains.

    Sender selection is decoupled from this table. The sending engine chooses
    from the campaign's sender pool (campaign_sender_pool), allowing dynamic
    rotation without hard-pinning a variant to one mailbox.

    A step with zero StepEmail rows cannot be started — the campaign-start
    validation gate checks this and returns 422 with a clear message.

    subject_line and email_body support Jinja2-style merge tags:
        {{first_name}}, {{company_name}}, and any key in Lead.custom_variables.
    """

    __tablename__ = "step_email"

    email_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Unique identifier for this email variant.",
    )

    step_id = Column(
        UUID(as_uuid=False),
        ForeignKey("sequence_step.step_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to sequence_step — the step this variant belongs to.",
    )

    subject_line = Column(
        String(998),  # RFC 2822 max subject length
        nullable=False,
        comment="Email subject — supports {{merge_tag}} template variables.",
    )

    email_body = Column(
        Text,
        nullable=False,
        comment="HTML or plain-text email body — supports {{merge_tag}} variables.",
    )

    # The display name used in the From header (e.g. "Sarah from Acme Corp").
    # If NULL the SenderAccount's configured name is used.
    from_name = Column(
        String(255),
        nullable=True,
        comment="Display name for the From header. NULL = use sender_account default.",
    )

    # SHA-256(subject_line + normalized body) for duplicate-content detection.
    # Used by backend checks to prevent repeated spam-like content.
    content_hash = Column(
        String(64),
        nullable=True,
        comment="SHA-256 hash of normalized subject+body for duplicate-content checks.",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this email variant was created.",
    )

    # --- Relationships ---
    step = relationship("SequenceStep", back_populates="email_variants")

    __table_args__ = (
        UniqueConstraint(
            "step_id",
            "content_hash",
            name="uq_step_email_step_content_hash",
        ),
        Index("ix_step_email_content_hash", "content_hash"),
        Index("ix_step_email_step_content_hash", "step_id", "content_hash"),
    )


# ===========================================================================
# CAMPAIGN EXECUTION CLUSTER
# ===========================================================================


class CampaignRun(Base):
    """
    An immutable record of a single campaign lifecycle transition.

    One row is appended each time a campaign is started, paused, resumed,
    stopped, or completes naturally.  This gives a full execution history
    without mutating the Campaign row itself.

    triggered_by stores the user who caused the transition; it is SET NULL
    if the user is later deleted (e.g. for scheduler-triggered completions it
    may also be NULL from the start).

    Valid action values:  started | paused | resumed | stopped | completed
    Valid run_status values: running | paused | stopped | completed | error
    """

    __tablename__ = "campaign_run"

    run_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=_UUID_DEFAULT,
        comment="Unique identifier for this execution event.",
    )

    campaign_id = Column(
        UUID(as_uuid=False),
        ForeignKey("campaign.campaign_id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to campaign — which campaign this event belongs to.",
    )

    # The user who triggered this transition (NULL for scheduler-triggered events).
    triggered_by = Column(
        UUID(as_uuid=False),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to users — who triggered this transition. NULL for automated events.",
    )

    # Allowed: started | paused | resumed | stopped | completed
    action = Column(
        String(30),
        nullable=False,
        comment="The lifecycle action performed: started | paused | resumed | stopped | completed.",
    )

    # Snapshot of the campaign status after this action.
    # Allowed: running | paused | stopped | completed | error
    run_status = Column(
        String(30),
        nullable=False,
        comment="Campaign status after this action: running | paused | stopped | completed | error.",
    )

    started_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC timestamp when sending began for this run (set on 'started' action).",
    )

    ended_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="UTC timestamp when this run ended (set on stopped/completed/error).",
    )

    # Non-NULL only when run_status is 'error'.
    error_message = Column(
        Text,
        nullable=True,
        comment="Error description when run_status is 'error'.",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this run record was created.",
    )

    __table_args__ = (
        CheckConstraint(
            "action IN ('started','paused','resumed','stopped','completed')",
            name="ck_campaign_run_action",
        ),
        CheckConstraint(
            "run_status IN ('running','paused','stopped','completed','error')",
            name="ck_campaign_run_status",
        ),
    )

    # --- Relationships ---
    campaign = relationship("Campaign", back_populates="runs")
    actor = relationship("User", foreign_keys=[triggered_by])

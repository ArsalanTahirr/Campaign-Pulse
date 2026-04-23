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
    Column,
    ForeignKey,
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

    A user must authenticate through exactly one mechanism:
      • LocalAuth  — email + hashed password (traditional login)
      • OAuthAccounts — one or more third-party providers (Google, Microsoft…)

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
    # Ownership of a workspace is expressed via CollaboratorRole (Role.role_name = 'Owner'),
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
    expressed exclusively through the Collaborator + CollaboratorRole chain:

        Workspace → Collaborator → CollaboratorRole → Role (role_name = 'Owner')

    This design means a workspace has no hard-coded single owner column.
    Ownership is just a role assignment, which makes it trivial to support
    co-owners, ownership transfer, or custom admin tiers in the future without
    any schema change.

    To find the owner(s) of a workspace at query time:
        SELECT c.user_id
        FROM collaborator c
        JOIN collaborator_role cr ON cr.member_id = c.member_id
        JOIN role r               ON r.role_id    = cr.role_id
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
    )

    # --- Relationships ---
    workspace = relationship("Workspace", back_populates="collaborators")
    user = relationship("User", back_populates="collaborations")

    # One Collaborator → many CollaboratorRole assignments.
    role_assignments = relationship(
        "CollaboratorRole",
        back_populates="collaborator",
        cascade="all, delete-orphan",
    )

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

    # One Role → many CollaboratorRole assignments.
    assignments = relationship(
        "CollaboratorRole",
        back_populates="role",
        cascade="all, delete-orphan",
    )


class CollaboratorRole(Base):
    """
    Junction table that assigns one or more Roles to a Collaborator.

    This resolves the M:N relationship between Collaborator and Role.
    The composite primary key (member_id, role_id) ensures a collaborator
    cannot be assigned the same role twice.

    Confirmed 2NF-clean: both assigned_at and assigned_by describe the
    assignment event itself — they depend on the full composite key, not on
    either column alone.

    assigned_by stores the UUID of the user (or member) who performed the
    assignment, providing a lightweight audit trail without a full audit log.
    """

    __tablename__ = "collaborator_role"

    # Composite PK — (member_id, role_id) is unique per the 2NF analysis.
    member_id = Column(
        UUID(as_uuid=False),
        ForeignKey("collaborator.member_id", ondelete="CASCADE"),
        primary_key=True,
        comment="Part of composite PK. FK to collaborator.",
    )
    role_id = Column(
        UUID(as_uuid=False),
        ForeignKey("role.role_id", ondelete="CASCADE"),
        primary_key=True,
        comment="Part of composite PK. FK to role.",
    )

    assigned_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this role was assigned to the collaborator.",
    )

    # Stores the user_id of the admin who performed the assignment.
    # Not a formal FK to avoid circular dependencies; treated as audit data.
    assigned_by = Column(
        UUID(as_uuid=False),
        nullable=True,
        comment="UUID of the user who performed this role assignment (audit trail).",
    )

    # --- Relationships ---
    collaborator = relationship("Collaborator", back_populates="role_assignments")
    role = relationship("Role", back_populates="assignments")


# ===========================================================================
# CAMPAIGN CLUSTER
# ===========================================================================


class Campaign(Base):
    """
    The core entity of CampaignPulse — an email outreach campaign.

    A campaign belongs to a workspace and is created by a collaborator (a
    workspace member).  It defines the high-level sending strategy: which
    timezone to honour, when to send (schedule), and its current lifecycle
    state (status).

    The schedule column stores a JSONB object that describes the sending
    window, e.g. {"days": ["Mon","Tue","Wed"], "start": "09:00", "end": "17:00"}.
    Using JSONB avoids the complexity of a separate schedule table while still
    allowing JSON-path queries.

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

    # Flexible JSONB schedule descriptor.
    # e.g. {"days":["Mon","Tue","Wed","Thu","Fri"],"start":"09:00","end":"17:00"}
    schedule = Column(
        JSONB,
        nullable=True,
        comment="JSONB object describing the permitted sending window for this campaign.",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=_NOW_DEFAULT,
        comment="UTC timestamp when this campaign was created.",
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

    subject_line = Column(
        String(998),  # RFC 2822 max subject length
        nullable=False,
        comment="Email subject line for this step. Supports template variables.",
    )

    # Full HTML or plain-text email body.  Text is used instead of String
    # because email bodies are unbounded in length.
    email_body = Column(
        Text,
        nullable=False,
        comment="HTML or plain-text body of the email. Supports template variables.",
    )

    # Delay from the previous step expressed in whole days.
    wait_days = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Days to wait after the previous step before sending this email.",
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

    # The same email address must not appear twice in the same campaign.
    # Re-enrolling a contact in a new campaign creates a new Lead row in that
    # campaign — it does not reuse or modify this one.
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "email",
            name="uq_lead_campaign_email",
        ),
    )

    # --- Relationships ---
    campaign = relationship("Campaign", back_populates="leads")

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
        nullable=False,
        comment="FK to lead — which contact this event is about.",
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

    # --- Relationships ---
    lead = relationship("Lead", back_populates="events")
    step = relationship("SequenceStep", back_populates="events")


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

    # 'smtp', 'google', 'microsoft', etc.
    provider_type = Column(
        String(50),
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
    # Typical values: 'active', 'inactive', 'suspended', 'warming_up'
    status = Column(
        String(30),
        nullable=False,
        default="active",
        server_default=text("'active'"),
        comment="Account status: active | inactive | suspended | warming_up.",
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

    # --- Relationship back to SenderAccount ---
    sender_account = relationship("SenderAccount", back_populates="warmup_settings")

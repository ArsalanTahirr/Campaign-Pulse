"""Create unibox_message table

Revision ID: f7a8b9c0d1e2
Revises: e1f2a3b4c5d6
Create Date: 2026-05-01 19:05:00.000000

Creates the unibox_message table that stores the full content of every
individual email — both inbound (from leads/unknown senders) and outbound
(manual replies sent from the Unibox). Includes a GIN-indexed tsvector
column for full-text search.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create unibox_message table with all indexes including GIN for FTS."""
    op.create_table(
        "unibox_message",
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Unique identifier for this email message.",
        ),
        sa.Column(
            "thread_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("unibox_thread.thread_id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to unibox_thread — the conversation this message belongs to.",
        ),
        sa.Column(
            "sender_account_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("sender_account.account_id", ondelete="RESTRICT"),
            nullable=False,
            comment="FK to sender_account — which inbox received or sent this message.",
        ),
        sa.Column(
            "lead_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("lead.lead_id", ondelete="SET NULL"),
            nullable=True,
            comment="FK to lead — NULL for orphan messages from unknown senders.",
        ),
        sa.Column(
            "email_event_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("email_event.event_id", ondelete="SET NULL"),
            nullable=True,
            comment="FK to email_event — optional cross-link for campaign send events.",
        ),
        sa.Column(
            "direction",
            sa.String(10),
            nullable=False,
            comment="Message direction: inbound (received) or outbound (sent).",
        ),
        sa.Column(
            "message_id_header",
            sa.Text(),
            nullable=False,
            unique=True,
            comment="RFC 2822 Message-ID header value. UNIQUE enforces idempotent ingestion.",
        ),
        sa.Column(
            "in_reply_to",
            sa.Text(),
            nullable=True,
            comment="RFC 2822 In-Reply-To header — references the immediate parent message.",
        ),
        sa.Column(
            "references_header",
            sa.Text(),
            nullable=True,
            comment="RFC 2822 References header — full ancestor Message-ID chain.",
        ),
        sa.Column(
            "from_address",
            sa.Text(),
            nullable=False,
            comment="Sender email address (the From header value).",
        ),
        sa.Column(
            "to_addresses",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            comment="Array of recipient email addresses (the To header value).",
        ),
        sa.Column(
            "cc_addresses",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
            comment="Array of CC email addresses (nullable).",
        ),
        sa.Column(
            "subject",
            sa.Text(),
            nullable=False,
            comment="Email subject line.",
        ),
        sa.Column(
            "body_text",
            sa.Text(),
            nullable=True,
            comment="Plain-text body of the email.",
        ),
        sa.Column(
            "body_html",
            sa.Text(),
            nullable=True,
            comment="HTML body of the email.",
        ),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether this message has been read by a workspace member.",
        ),
        sa.Column(
            "is_orphan",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="True when the sender does not match any known lead in the workspace.",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            comment="Message status: received | sent | failed | draft.",
        ),
        sa.Column(
            "received_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="UTC timestamp when this inbound message was received.",
        ),
        sa.Column(
            "sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="UTC timestamp when this outbound message was sent.",
        ),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            nullable=True,
            comment="PostgreSQL tsvector for full-text search. Populated at insert time.",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="UTC timestamp when this message record was created.",
        ),
        sa.CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="ck_unibox_message_direction",
        ),
        sa.CheckConstraint(
            "status IN ('received', 'sent', 'failed', 'draft')",
            name="ck_unibox_message_status",
        ),
        sa.CheckConstraint(
            "(direction = 'inbound' AND status IN ('received', 'failed'))"
            " OR "
            "(direction = 'outbound' AND status IN ('sent', 'failed', 'draft'))",
            name="ck_unibox_message_direction_status",
        ),
    )

    # Fast chronological message loading within a thread.
    op.create_index(
        "idx_unibox_message_thread_created",
        "unibox_message",
        ["thread_id", "created_at"],
    )

    # Filter messages by inbox (sender account).
    op.create_index(
        "idx_unibox_message_sender_account",
        "unibox_message",
        ["sender_account_id"],
    )

    # Filter messages by lead.
    op.create_index(
        "idx_unibox_message_lead_id",
        "unibox_message",
        ["lead_id"],
    )

    # Powers the "Sent" view (outbound messages).
    op.create_index(
        "idx_unibox_message_direction_created",
        "unibox_message",
        ["direction", "created_at"],
    )

    # Partial index: only unread rows, for fast unread count queries.
    op.create_index(
        "idx_unibox_message_unread",
        "unibox_message",
        ["thread_id", "is_read"],
        postgresql_where=sa.text("is_read = false"),
    )

    # GIN index for full-text search.
    op.create_index(
        "idx_unibox_message_search_vector",
        "unibox_message",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Drop unibox_message table and all its indexes."""
    op.drop_index("idx_unibox_message_search_vector", table_name="unibox_message")
    op.drop_index("idx_unibox_message_unread", table_name="unibox_message")
    op.drop_index("idx_unibox_message_direction_created", table_name="unibox_message")
    op.drop_index("idx_unibox_message_lead_id", table_name="unibox_message")
    op.drop_index("idx_unibox_message_sender_account", table_name="unibox_message")
    op.drop_index("idx_unibox_message_thread_created", table_name="unibox_message")
    op.drop_table("unibox_message")

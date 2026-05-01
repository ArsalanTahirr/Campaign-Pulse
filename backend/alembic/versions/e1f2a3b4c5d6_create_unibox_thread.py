"""Create unibox_thread table

Revision ID: e1f2a3b4c5d6
Revises: a3f7c2e9b015
Create Date: 2026-05-01 19:00:00.000000

Creates the unibox_thread table that groups individual email messages into
conversation threads for the Unibox feature. Each thread is scoped to a
workspace and optionally linked to a lead and/or campaign.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "a3f7c2e9b015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create unibox_thread table with indexes."""
    op.create_table(
        "unibox_thread",
        sa.Column(
            "thread_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Unique identifier for this conversation thread.",
        ),
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey("workspace.workspace_id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to workspace — every thread belongs to exactly one workspace.",
        ),
        sa.Column(
            "lead_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey("lead.lead_id", ondelete="SET NULL"),
            nullable=True,
            comment="FK to lead — NULL for orphan threads (unknown sender).",
        ),
        sa.Column(
            "campaign_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey("campaign.campaign_id", ondelete="SET NULL"),
            nullable=True,
            comment="FK to campaign — optional campaign tag on this thread.",
        ),
        sa.Column(
            "subject",
            sa.Text(),
            nullable=False,
            comment="Thread subject line (from the first message).",
        ),
        sa.Column(
            "last_message_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="UTC timestamp of the most recent message in this thread.",
        ),
        sa.Column(
            "is_orphan",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="True when no matching lead was found for any message in this thread.",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="UTC timestamp when this thread record was created.",
        ),
        sa.CheckConstraint(
            "(is_orphan = false AND lead_id IS NOT NULL) OR (is_orphan = true AND lead_id IS NULL)",
            name="ck_unibox_thread_orphan_lead",
        ),
    )

    # Primary listing query: all threads in workspace ordered by most-recent first.
    op.create_index(
        "idx_unibox_thread_workspace_last_msg",
        "unibox_thread",
        ["workspace_id", sa.text("last_message_at DESC")],
    )

    # Filter threads by lead (pipeline status view).
    op.create_index(
        "idx_unibox_thread_lead_id",
        "unibox_thread",
        ["lead_id"],
    )

    # Filter threads by campaign (campaign view).
    op.create_index(
        "idx_unibox_thread_campaign_id",
        "unibox_thread",
        ["campaign_id"],
    )

    # Fast isolation of orphan vs known-lead threads.
    op.create_index(
        "idx_unibox_thread_workspace_orphan",
        "unibox_thread",
        ["workspace_id", "is_orphan"],
    )


def downgrade() -> None:
    """Drop unibox_thread table and all its indexes."""
    op.drop_index("idx_unibox_thread_workspace_orphan", table_name="unibox_thread")
    op.drop_index("idx_unibox_thread_campaign_id", table_name="unibox_thread")
    op.drop_index("idx_unibox_thread_lead_id", table_name="unibox_thread")
    op.drop_index("idx_unibox_thread_workspace_last_msg", table_name="unibox_thread")
    op.drop_table("unibox_thread")

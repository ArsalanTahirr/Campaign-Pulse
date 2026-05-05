"""pool driven scheduling fields

Revision ID: e8f1a2b3c4d5
Revises: d4e5f6a7b8c9
Create Date: 2026-05-05 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e8f1a2b3c4d5"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sender_account",
        sa.Column(
            "next_ready_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment="UTC timestamp when this sender is next eligible to send.",
        ),
    )

    op.alter_column(
        "lead",
        "next_scheduled_at",
        new_column_name="next_eligible_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
        existing_comment="UTC timestamp when the next step email should fire for this lead.",
    )

    op.drop_index("ix_lead_next_scheduled_state", table_name="lead")
    op.drop_index("ix_lead_campaign_next_scheduled", table_name="lead")
    op.create_index(
        "ix_lead_next_eligible_state",
        "lead",
        ["next_eligible_at", "delivery_state"],
        unique=False,
    )
    op.create_index(
        "ix_lead_campaign_next_eligible",
        "lead",
        ["campaign_id", "next_eligible_at"],
        unique=False,
    )

    op.drop_constraint("ck_lead_delivery_state", "lead", type_="check")
    op.create_check_constraint(
        "ck_lead_delivery_state",
        "lead",
        "delivery_state IN ('queued','sending','sent','failed','paused','completed')",
    )

    op.execute(
        """
        UPDATE sender_account
        SET next_ready_at = now()
        WHERE next_ready_at IS NULL
          AND status IN ('active', 'warming_up')
          AND is_verified = true
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_lead_delivery_state", "lead", type_="check")
    op.create_check_constraint(
        "ck_lead_delivery_state",
        "lead",
        "delivery_state IN ('queued','sending','sent','failed','paused')",
    )

    op.drop_index("ix_lead_next_eligible_state", table_name="lead")
    op.drop_index("ix_lead_campaign_next_eligible", table_name="lead")
    op.create_index(
        "ix_lead_next_scheduled_state",
        "lead",
        ["next_scheduled_at", "delivery_state"],
        unique=False,
    )
    op.create_index(
        "ix_lead_campaign_next_scheduled",
        "lead",
        ["campaign_id", "next_scheduled_at"],
        unique=False,
    )

    op.alter_column(
        "lead",
        "next_eligible_at",
        new_column_name="next_scheduled_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )
    op.drop_column("sender_account", "next_ready_at")

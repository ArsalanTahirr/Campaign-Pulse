"""sender account soft delete and status rules

Revision ID: a9c4d8e2f1b0
Revises: 7c1e9f4a2b11
Create Date: 2026-04-27 06:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a9c4d8e2f1b0"
down_revision: Union[str, None] = "7c1e9f4a2b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sender_account",
        sa.Column(
            "deleted_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment="UTC soft-delete timestamp. Non-null means account is disconnected from active use.",
        ),
    )


def downgrade() -> None:
    op.drop_column("sender_account", "deleted_at")

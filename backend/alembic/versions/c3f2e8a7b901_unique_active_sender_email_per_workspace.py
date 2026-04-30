"""unique active sender email per workspace

Revision ID: c3f2e8a7b901
Revises: a9c4d8e2f1b0
Create Date: 2026-04-27 06:50:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c3f2e8a7b901"
down_revision: Union[str, None] = "a9c4d8e2f1b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_sender_account_workspace_email_active "
        "ON sender_account (workspace_id, lower(email)) "
        "WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_sender_account_workspace_email_active")

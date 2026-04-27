"""enforce sender provider enum

Revision ID: 7c1e9f4a2b11
Revises: 0f3251e8c547
Create Date: 2026-04-27 05:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c1e9f4a2b11"
down_revision: Union[str, None] = "0f3251e8c547"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "CREATE TYPE sender_provider_type AS ENUM ('smtp', 'google', 'microsoft')"
    )
    op.execute(
        "ALTER TABLE sender_account "
        "ALTER COLUMN provider_type TYPE sender_provider_type "
        "USING lower(trim(provider_type))::sender_provider_type"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TABLE sender_account "
        "ALTER COLUMN provider_type TYPE VARCHAR(50) "
        "USING provider_type::text"
    )
    op.execute("DROP TYPE sender_provider_type")

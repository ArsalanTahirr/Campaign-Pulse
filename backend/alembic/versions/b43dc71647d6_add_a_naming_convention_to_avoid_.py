"""Add a naming convention to avoid downgrade errors

Revision ID: b43dc71647d6
Revises: e7a1f3c9d4b2
Create Date: 2026-04-25 21:17:38.428624

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b43dc71647d6'
down_revision: Union[str, None] = 'e7a1f3c9d4b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Robust constraint renames (safe across environments).
    op.execute("ALTER TABLE invitation DROP CONSTRAINT IF EXISTS invitation_token_key")
    op.execute("ALTER TABLE invitation DROP CONSTRAINT IF EXISTS uq_invitation_token")
    op.execute("ALTER TABLE invitation ADD CONSTRAINT uq_invitation_token UNIQUE (token)")

    op.execute("ALTER TABLE refresh_tokens DROP CONSTRAINT IF EXISTS refresh_tokens_token_hash_key")
    op.execute("ALTER TABLE refresh_tokens DROP CONSTRAINT IF EXISTS uq_refresh_tokens_token_hash")
    op.execute("ALTER TABLE refresh_tokens ADD CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash)")

    op.execute("ALTER TABLE role DROP CONSTRAINT IF EXISTS role_role_name_key")
    op.execute("ALTER TABLE role DROP CONSTRAINT IF EXISTS uq_role_role_name")
    op.execute("ALTER TABLE role ADD CONSTRAINT uq_role_role_name UNIQUE (role_name)")

    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_email")
    op.execute("ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_email")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key")
    op.execute("ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email)")

    op.execute("ALTER TABLE role DROP CONSTRAINT IF EXISTS uq_role_role_name")
    op.execute("ALTER TABLE role DROP CONSTRAINT IF EXISTS role_role_name_key")
    op.execute("ALTER TABLE role ADD CONSTRAINT role_role_name_key UNIQUE (role_name)")

    op.execute("ALTER TABLE refresh_tokens DROP CONSTRAINT IF EXISTS uq_refresh_tokens_token_hash")
    op.execute("ALTER TABLE refresh_tokens DROP CONSTRAINT IF EXISTS refresh_tokens_token_hash_key")
    op.execute("ALTER TABLE refresh_tokens ADD CONSTRAINT refresh_tokens_token_hash_key UNIQUE (token_hash)")

    op.execute("ALTER TABLE invitation DROP CONSTRAINT IF EXISTS uq_invitation_token")
    op.execute("ALTER TABLE invitation DROP CONSTRAINT IF EXISTS invitation_token_key")
    op.execute("ALTER TABLE invitation ADD CONSTRAINT invitation_token_key UNIQUE (token)")

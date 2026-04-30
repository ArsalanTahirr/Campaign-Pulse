"""seed_default_workspace_roles

Revision ID: d6b3e1f2a4c8
Revises: c2e7f9a1b4d3
Create Date: 2026-04-25 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d6b3e1f2a4c8"
down_revision: Union[str, None] = "c2e7f9a1b4d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Seed default workspace roles as dimension data (idempotent).
    op.execute(
        """
        INSERT INTO role (role_id, role_name, permissions)
        VALUES
            (gen_random_uuid(), 'Owner', '{}'::jsonb),
            (gen_random_uuid(), 'Agency', '{}'::jsonb),
            (gen_random_uuid(), 'Marketing Manager', '{}'::jsonb),
            (gen_random_uuid(), 'Data Analyst', '{}'::jsonb)
        ON CONFLICT (role_name)
        DO NOTHING;
        """
    )


def downgrade() -> None:
    # Safe rollback: only delete seeded roles when they are not referenced.
    # In real databases, invitations/collaborator_role rows may point to these
    # role_ids, so unconditional DELETE causes FK violations.
    op.execute(
        """
        DELETE FROM role r
        WHERE r.role_name IN ('Owner', 'Agency', 'Marketing Manager', 'Data Analyst')
          AND NOT EXISTS (
              SELECT 1 FROM invitation i WHERE i.role_id = r.role_id
          )
          AND NOT EXISTS (
              SELECT 1 FROM collaborator_role cr WHERE cr.role_id = r.role_id
          );
        """
    )

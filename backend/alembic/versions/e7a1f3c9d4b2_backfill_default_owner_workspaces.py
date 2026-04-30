"""backfill_default_owner_workspaces

Revision ID: e7a1f3c9d4b2
Revises: d6b3e1f2a4c8
Create Date: 2026-04-25 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e7a1f3c9d4b2"
down_revision: Union[str, None] = "d6b3e1f2a4c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfill: every user must own at least one workspace.
    op.execute(
        """
        DO $$
        DECLARE
            rec RECORD;
            owner_role_id UUID;
            ws_id UUID;
            member_id UUID;
            ws_name TEXT;
        BEGIN
            SELECT role_id INTO owner_role_id
            FROM role
            WHERE role_name = 'Owner'
            LIMIT 1;

            IF owner_role_id IS NULL THEN
                INSERT INTO role (role_id, role_name, permissions)
                VALUES (gen_random_uuid(), 'Owner', '{}'::jsonb)
                RETURNING role_id INTO owner_role_id;
            END IF;

            FOR rec IN
                SELECT u.user_id, COALESCE(NULLIF(TRIM(u.first_name), ''), 'My') AS first_name
                FROM users u
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM collaborator c
                    JOIN collaborator_role cr ON cr.member_id = c.member_id
                    JOIN role r ON r.role_id = cr.role_id
                    WHERE c.user_id = u.user_id
                      AND c.invite_status = 'accepted'
                      AND r.role_name = 'Owner'
                )
            LOOP
                ws_id := gen_random_uuid();
                member_id := gen_random_uuid();
                ws_name := rec.first_name || '''s Workspace';

                INSERT INTO workspace (workspace_id, workspace_name, created_at)
                VALUES (ws_id, ws_name, now());

                INSERT INTO collaborator (member_id, workspace_id, user_id, invite_status, joined_at)
                VALUES (member_id, ws_id, rec.user_id, 'accepted', now());

                INSERT INTO collaborator_role (member_id, role_id, assigned_at)
                VALUES (member_id, owner_role_id, now());
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    # Intentionally no-op: cannot safely distinguish user-created workspaces from
    # auto-backfilled defaults after deployment.
    pass

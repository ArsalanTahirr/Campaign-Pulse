"""
services/audit_log_service.py — Append-only audit trail writer.

write_audit_log() is called by other service functions, never directly by
route handlers.  It always flushes but never commits so the caller controls
the transaction boundary.
"""

import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit_log(
    db: Session,
    workspace_id: Optional[str],
    actor_user_id: Optional[str],
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
) -> AuditLog:
    log = AuditLog(
        log_id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(log)
    db.flush()
    return log

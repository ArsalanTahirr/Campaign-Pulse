"""
dependencies/ — FastAPI dependency factories for CampaignPulse.

Exports:
  get_current_user   — resolves the authenticated User from the JWT cookie.
  require_permission — returns a Depends factory that gates an action by role.
"""

from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permission

__all__ = ["get_current_user", "require_permission"]

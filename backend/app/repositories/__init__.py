"""
repositories/ — Data-access layer for CampaignPulse.

Exports all repository modules so callers can do:
    from app import repositories
    repositories.unibox_repository.get_thread_by_id(...)
"""

from app.repositories import unibox_repository

__all__ = ["unibox_repository"]

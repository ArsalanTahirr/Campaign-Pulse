"""
schemas/workspace.py — Pydantic v2 models for Workspace CRUD.

The ORM column is `workspace_name`; we expose it as `name` in the API via
validation_alias so clients use the cleaner field name.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)


class WorkspaceOut(BaseModel):
    workspace_id: str
    # ORM attribute is `workspace_name`; serialize as `name` for a clean API surface.
    name: str = Field(validation_alias="workspace_name")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}

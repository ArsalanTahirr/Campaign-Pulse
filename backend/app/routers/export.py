"""
routers/export.py — Streaming CSV export for leads.

Routes (mounted at root /workspaces/{workspace_id}/campaigns/{campaign_id}):
    GET /leads/export   — stream all leads for a campaign as CSV
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.services.export_service import generate_leads_csv

router = APIRouter()


@router.get("/leads/export")
def export_leads_csv(
    workspace_id: str,
    campaign_id: str,
    _: None = require_permission("export_leads"),
    db: Session = Depends(get_db),
):
    """
    Stream all leads for `campaign_id` as a UTF-8 CSV file.
    Uses yield_per(500) so memory stays constant regardless of lead count.
    """
    filename = f"leads_{campaign_id}.csv"
    return StreamingResponse(
        generate_leads_csv(campaign_id, db),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

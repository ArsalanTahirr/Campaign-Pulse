"""
routers/leads.py — Lead CRUD, bulk import, and CSV export endpoints.

Routes (mounted under /workspaces/{workspace_id}/campaigns/{campaign_id}):
    GET    /leads                    — paginated lead list
    POST   /leads                    — create single lead
    GET    /leads/export             — stream CSV (MUST be before {lead_id} wildcard)
    POST   /leads/import             — bulk CSV/XLSX upload
    GET    /leads/import/{session_id}— import session status (MUST be before {lead_id})
    GET    /leads/{lead_id}          — get lead
    PATCH  /leads/{lead_id}          — update lead
    DELETE /leads/{lead_id}          — delete lead

IMPORTANT: Static paths (/export, /import, /import/{id}) are declared BEFORE the
{lead_id} wildcard so FastAPI's first-match routing resolves them correctly.
"""

from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import LeadImportSession, User
from app.schemas.lead import LeadCreate, LeadImportSessionOut, LeadOut, LeadUpdate
from app.services import lead_service
from app.services.export_service import generate_leads_csv

router = APIRouter()


# ---------------------------------------------------------------------------
# Collection endpoints
# ---------------------------------------------------------------------------


@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    workspace_id: str,
    campaign_id: str,
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    _: None = require_permission("view_leads"),
    db: Session = Depends(get_db),
):
    return lead_service.list_leads(campaign_id, db, status_filter, skip, limit)


@router.post("/leads", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead(
    workspace_id: str,
    campaign_id: str,
    body: LeadCreate,
    _: None = require_permission("import_leads"),
    db: Session = Depends(get_db),
):
    return lead_service.create_lead(
        campaign_id=campaign_id,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        custom_variables=body.custom_variables,
        db=db,
    )


# ---------------------------------------------------------------------------
# Static sub-paths — MUST come before /leads/{lead_id} wildcard
# ---------------------------------------------------------------------------


@router.get("/leads/export")
def export_leads_csv(
    workspace_id: str,
    campaign_id: str,
    _: None = require_permission("export_leads"),
    db: Session = Depends(get_db),
):
    """Stream all leads for campaign_id as a UTF-8 CSV file."""
    filename = f"leads_{campaign_id}.csv"
    return StreamingResponse(
        generate_leads_csv(campaign_id, db),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/leads/import",
    response_model=LeadImportSessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def import_leads(
    workspace_id: str,
    campaign_id: str,
    file: UploadFile = File(...),
    _: None = require_permission("import_leads"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await lead_service.import_leads_from_file(
        campaign_id=campaign_id,
        importer_user_id=user.user_id,
        file=file,
        db=db,
    )


@router.get("/leads/import/{session_id}", response_model=LeadImportSessionOut)
def get_import_session(
    workspace_id: str,
    campaign_id: str,
    session_id: str,
    _: None = require_permission("view_leads"),
    db: Session = Depends(get_db),
):
    session = (
        db.query(LeadImportSession)
        .filter(
            LeadImportSession.session_id == session_id,
            LeadImportSession.campaign_id == campaign_id,
        )
        .first()
    )
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import session not found.")
    return session


# ---------------------------------------------------------------------------
# Single-lead endpoints — wildcard MUST be last
# ---------------------------------------------------------------------------


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(
    workspace_id: str,
    campaign_id: str,
    lead_id: str,
    _: None = require_permission("view_leads"),
    db: Session = Depends(get_db),
):
    return lead_service.get_lead_or_404(lead_id, campaign_id, db)


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(
    workspace_id: str,
    campaign_id: str,
    lead_id: str,
    body: LeadUpdate,
    _: None = require_permission("import_leads"),
    db: Session = Depends(get_db),
):
    updates = body.model_dump(exclude_unset=True)
    return lead_service.update_lead(lead_id, campaign_id, updates, db)


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    workspace_id: str,
    campaign_id: str,
    lead_id: str,
    _: None = require_permission("import_leads"),
    db: Session = Depends(get_db),
):
    lead_service.delete_lead(lead_id, campaign_id, db)

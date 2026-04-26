"""
services/lead_service.py — Lead CRUD and CSV/XLSX bulk import.

ORM column: Lead.lead_status  (not .status)
Lead has no created_at column — ordering uses lead_id (insertion order).
"""

import io
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Campaign, Lead, LeadImportSession


ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def get_lead_or_404(lead_id: str, campaign_id: str, db: Session) -> Lead:
    lead = (
        db.query(Lead)
        .filter(Lead.lead_id == lead_id, Lead.campaign_id == campaign_id)
        .first()
    )
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    return lead


def _assert_campaign_not_completed_or_deleted(campaign_id: str, db: Session) -> None:
    campaign_status = (
        db.query(Campaign.status)
        .filter(Campaign.campaign_id == campaign_id)
        .scalar()
    )
    if not campaign_status:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
    if campaign_status in {"completed", "deleted"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed or deleted campaigns are view-only for lead mutations.",
        )


def list_leads(
    campaign_id: str,
    db: Session,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Lead]:
    q = db.query(Lead).filter(Lead.campaign_id == campaign_id)
    if status_filter:
        # ORM column is lead_status
        q = q.filter(Lead.lead_status == status_filter)
    # Lead has no created_at; order by the natural insertion key
    return q.order_by(Lead.lead_id).offset(skip).limit(limit).all()


def create_lead(
    campaign_id: str,
    email: str,
    first_name: Optional[str],
    last_name: Optional[str],
    custom_variables: Optional[dict],
    db: Session,
) -> Lead:
    _assert_campaign_not_completed_or_deleted(campaign_id, db)
    try:
        lead = Lead(
            lead_id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            custom_variables=custom_variables,
            lead_status="active",
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Lead with email '{email}' already exists in this campaign.",
        )


def update_lead(lead_id: str, campaign_id: str, updates: dict, db: Session) -> Lead:
    _assert_campaign_not_completed_or_deleted(campaign_id, db)
    lead = get_lead_or_404(lead_id, campaign_id, db)
    # Map the API field `status` to the ORM column `lead_status`
    if "status" in updates:
        updates["lead_status"] = updates.pop("status")
    for field, value in updates.items():
        if value is not None and hasattr(lead, field):
            setattr(lead, field, value)
    db.commit()
    db.refresh(lead)
    return lead


def delete_lead(lead_id: str, campaign_id: str, db: Session) -> None:
    _assert_campaign_not_completed_or_deleted(campaign_id, db)
    lead = get_lead_or_404(lead_id, campaign_id, db)
    db.delete(lead)
    db.commit()


# ---------------------------------------------------------------------------
# Bulk CSV / XLSX import
# ---------------------------------------------------------------------------


def _parse_csv_rows(content: bytes) -> list[dict]:
    import csv
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def _parse_xlsx_rows(content: bytes) -> list[dict]:
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="openpyxl is not installed. Cannot process XLSX files.",
        )
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    return [
        {headers[i]: (str(cell).strip() if cell is not None else "") for i, cell in enumerate(row)}
        for row in rows[1:]
    ]


async def import_leads_from_file(
    campaign_id: str,
    importer_user_id: str,
    file: UploadFile,
    db: Session,
) -> LeadImportSession:
    _assert_campaign_not_completed_or_deleted(campaign_id, db)
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES and not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only CSV and XLSX files are supported.",
        )

    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 10 MB size limit.",
        )

    session = LeadImportSession(
        session_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        imported_by=importer_user_id,
        file_name=file.filename or "upload",
        status="processing",
    )
    db.add(session)
    db.flush()

    try:
        if file.filename and file.filename.endswith(".xlsx"):
            rows = _parse_xlsx_rows(raw)
        else:
            rows = _parse_csv_rows(raw)
    except Exception as exc:
        session.status = "failed"
        session.completed_at = datetime.now(timezone.utc)
        session.error_details = [{"reason": str(exc)}]
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse file: {exc}",
        )

    session.row_count = len(rows)
    errors: list[dict] = []
    imported = 0
    skipped = 0

    for row_num, row in enumerate(rows, start=2):  # row 1 = header
        email = (row.get("email") or row.get("Email") or "").strip().lower()
        if not email or "@" not in email:
            errors.append({"row": row_num, "email": email or "(empty)", "reason": "Invalid or missing email."})
            continue

        first_name = (row.get("first_name") or row.get("First Name") or "").strip() or None
        last_name = (row.get("last_name") or row.get("Last Name") or "").strip() or None

        reserved = {"email", "first_name", "last_name", "Email", "First Name", "Last Name"}
        custom = {k: v for k, v in row.items() if k not in reserved and v}

        try:
            # Use a savepoint so that rolling back a duplicate only undoes
            # this single INSERT, leaving the LeadImportSession persistent.
            sp = db.begin_nested()
            lead = Lead(
                lead_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                custom_variables=custom if custom else None,
                import_session_id=session.session_id,
                lead_status="active",
            )
            db.add(lead)
            db.flush()
            sp.commit()
            imported += 1
        except IntegrityError:
            sp.rollback()
            skipped += 1

    session.imported_count = imported
    session.skipped_count = skipped
    session.error_count = len(errors)
    session.error_details = errors if errors else None
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)

    db.commit()
    return session

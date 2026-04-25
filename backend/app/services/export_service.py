"""
services/export_service.py — CSV streaming export for leads.

ORM column: Lead.lead_status  (not .status)
Lead has no created_at column.
"""

import csv
import io
from typing import Generator

from sqlalchemy.orm import Session

from app.models import Lead


def generate_leads_csv(campaign_id: str, db: Session) -> Generator[str, None, None]:
    """
    Yield CSV rows as strings for streaming.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "lead_id", "email", "first_name", "last_name",
        "status", "import_session_id", "custom_variables",
    ])
    yield output.getvalue()
    output.truncate(0)
    output.seek(0)

    leads = (
        db.query(Lead)
        .filter(Lead.campaign_id == campaign_id)
        .order_by(Lead.lead_id)
        .yield_per(500)
    )

    for lead in leads:
        writer.writerow([
            lead.lead_id,
            lead.email,
            lead.first_name or "",
            lead.last_name or "",
            lead.lead_status,
            lead.import_session_id or "",
            str(lead.custom_variables) if lead.custom_variables else "",
        ])
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)

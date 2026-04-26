"""
tests/test_leads.py — Lead CRUD, CSV import edge cases, and export tests.

CSV import/export behaviour is defined in app.services.lead_service and
app.services.export_service; tests here lock in the contract (headers, counts,
errors, permissions, and round-trips).
"""

import io
import csv

import pytest
from tests.factories import (
    add_member,
    auth_cookies,
    make_campaign,
    make_lead,
    make_user,
    make_workspace,
)


@pytest.fixture
def owner(db):
    return make_user(db)


@pytest.fixture
def ws(db, owner):
    return make_workspace(db, owner)


@pytest.fixture
def campaign(db, ws):
    return make_campaign(db, ws.workspace_id)


@pytest.fixture
def analyst(db, ws):
    user = make_user(db)
    add_member(db, ws.workspace_id, user, "Data Analyst")
    return user


# ---------------------------------------------------------------------------
# Single lead CRUD
# ---------------------------------------------------------------------------


def test_create_lead(client, db, owner, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads",
        json={"email": "john@example.com", "first_name": "John", "last_name": "Doe"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    assert res.json()["email"] == "john@example.com"
    assert res.json()["status"] == "active"


def test_duplicate_email_in_same_campaign(client, db, owner, ws, campaign):
    client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads",
        json={"email": "dup@example.com"},
        cookies=auth_cookies(owner),
    )
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads",
        json={"email": "dup@example.com"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 409


def test_same_email_different_campaigns(client, db, owner, ws):
    """The same email address is valid in two different campaigns."""
    c1 = make_campaign(db, ws.workspace_id, name="Campaign 1")
    c2 = make_campaign(db, ws.workspace_id, name="Campaign 2")
    for cid in [c1.campaign_id, c2.campaign_id]:
        res = client.post(
            f"/workspaces/{ws.workspace_id}/campaigns/{cid}/leads",
            json={"email": "shared@example.com"},
            cookies=auth_cookies(owner),
        )
        assert res.status_code == 201


def test_invalid_email_rejected(client, db, owner, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads",
        json={"email": "not-an-email"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 422


def test_list_leads_pagination(client, db, owner, ws, campaign):
    for i in range(5):
        make_lead(db, campaign.campaign_id, email=f"lead{i}@example.com")
    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads?skip=0&limit=3",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_analyst_can_view_leads(client, db, analyst, ws, campaign):
    make_lead(db, campaign.campaign_id)
    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads",
        cookies=auth_cookies(analyst),
    )
    assert res.status_code == 200


def test_analyst_cannot_create_lead(client, db, analyst, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads",
        json={"email": "x@x.com"},
        cookies=auth_cookies(analyst),
    )
    assert res.status_code == 403


def test_delete_lead(client, db, owner, ws, campaign):
    lead = make_lead(db, campaign.campaign_id)
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/{lead.lead_id}",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 204


def test_delete_nonexistent_lead(client, db, owner, ws, campaign):
    import uuid
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/{uuid.uuid4()}",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# CSV import
# ---------------------------------------------------------------------------


def _make_csv(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _make_csv_with_bom(rows: list[dict]) -> bytes:
    """UTF-8 with BOM — lead_service decodes with utf-8-sig."""
    return b"\xef\xbb\xbf" + _make_csv(rows)


def _parse_export_csv(text: str) -> tuple[list[str], list[dict]]:
    """Parse streamed export body: header row + dict rows."""
    lines = [ln for ln in text.strip().split("\n") if ln.strip()]
    if not lines:
        return [], []
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    return reader.fieldnames or [], list(reader)


def test_import_csv_success(client, db, owner, ws, campaign):
    csv_data = _make_csv([
        {"email": "a@example.com", "first_name": "Alice", "last_name": "Smith"},
        {"email": "b@example.com", "first_name": "Bob",   "last_name": "Jones"},
    ])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["imported_count"] == 2
    assert data["skipped_count"] == 0
    assert data["status"] == "completed"


def test_import_csv_deduplicates(client, db, owner, ws, campaign):
    """Duplicate emails in the file should be skipped (not cause a 500)."""
    csv_data = _make_csv([
        {"email": "dup@example.com"},
        {"email": "dup@example.com"},
    ])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("dups.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["imported_count"] == 1
    assert data["skipped_count"] == 1


def test_import_csv_skips_bad_emails(client, db, owner, ws, campaign):
    csv_data = _make_csv([
        {"email": "good@example.com"},
        {"email": "not-valid"},
        {"email": ""},
    ])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("mixed.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["imported_count"] == 1
    assert data["error_count"] == 2


def test_import_csv_unsupported_type(client, db, owner, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.txt", b"email\n", "text/plain")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 415


def test_analyst_cannot_import(client, db, analyst, ws, campaign):
    csv_data = _make_csv([{"email": "x@x.com"}])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(analyst),
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


def test_export_csv_streams(client, db, owner, ws, campaign):
    for i in range(3):
        make_lead(db, campaign.campaign_id, email=f"export{i}@example.com")

    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/export",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    lines = res.text.strip().split("\n")
    assert len(lines) == 4  # 1 header + 3 leads


def test_analyst_can_export(client, db, analyst, ws, campaign):
    make_lead(db, campaign.campaign_id)
    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/export",
        cookies=auth_cookies(analyst),
    )
    assert res.status_code == 200


def test_import_custom_variables_preserved(client, db, owner, ws, campaign):
    """Arbitrary CSV columns beyond the standard fields should be stored in custom_variables."""
    csv_data = _make_csv([
        {"email": "cv@example.com", "first_name": "Val", "company": "Acme", "title": "CEO"},
    ])
    client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    from app.models import Lead
    lead = db.query(Lead).filter(Lead.campaign_id == campaign.campaign_id).first()
    assert lead is not None
    assert lead.custom_variables is not None
    assert lead.custom_variables.get("company") == "Acme"


# ---------------------------------------------------------------------------
# CSV import — additional formats & edge cases
# ---------------------------------------------------------------------------


def test_import_csv_utf8_bom(client, db, owner, ws, campaign):
    csv_data = _make_csv_with_bom([{"email": "bom@example.com", "first_name": "Bom"}])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    assert res.json()["imported_count"] == 1


def test_import_csv_title_case_headers(client, db, owner, ws, campaign):
    csv_data = _make_csv([
        {"Email": "title@example.com", "First Name": "Pat", "Last Name": "Lee"},
    ])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["imported_count"] == 1
    from app.models import Lead
    lead = db.query(Lead).filter(Lead.email == "title@example.com").first()
    assert lead.first_name == "Pat"
    assert lead.last_name == "Lee"


def test_import_csv_email_normalized_to_lowercase(client, db, owner, ws, campaign):
    csv_data = _make_csv([{"email": "MiXeD@Example.COM"}])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    from app.models import Lead
    lead = db.query(Lead).filter(Lead.campaign_id == campaign.campaign_id).first()
    assert lead.email == "mixed@example.com"


def test_import_csv_trims_email_whitespace(client, db, owner, ws, campaign):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["email", "first_name"])
    writer.writeheader()
    writer.writerow({"email": "  spaced@example.com  ", "first_name": "S"})
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", buf.getvalue().encode("utf-8"), "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    assert res.json()["imported_count"] == 1
    from app.models import Lead
    assert (
        db.query(Lead).filter(Lead.email == "spaced@example.com").first() is not None
    )


def test_import_csv_header_only_no_data_rows(client, db, owner, ws, campaign):
    csv_data = b"email,first_name,last_name\n"
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("empty.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["imported_count"] == 0
    assert data["row_count"] == 0
    assert data["error_count"] == 0


def test_import_csv_empty_custom_columns_omitted(client, db, owner, ws, campaign):
    """Empty string custom fields should not appear in custom_variables (falsy values skipped)."""
    csv_data = _make_csv([
        {
            "email": "emptycol@example.com",
            "first_name": "E",
            "industry": "",
            "notes": "has note",
        },
    ])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    from app.models import Lead
    lead = db.query(Lead).filter(Lead.email == "emptycol@example.com").first()
    assert lead.custom_variables == {"notes": "has note"}


def test_import_csv_skips_when_email_already_in_campaign(client, db, owner, ws, campaign):
    make_lead(db, campaign.campaign_id, email="already@example.com")
    csv_data = _make_csv([{"email": "already@example.com", "first_name": "New"}])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["imported_count"] == 0
    assert data["skipped_count"] == 1


def test_import_csv_bad_rows_populate_error_details(client, db, owner, ws, campaign):
    csv_data = _make_csv([
        {"email": "ok@example.com"},
        {"email": "bad"},
    ])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["imported_count"] == 1
    assert data["error_count"] == 1
    errors = data["error_details"]
    assert isinstance(errors, list)
    assert any(e.get("row") == 3 and "Invalid" in e.get("reason", "") for e in errors)


def test_import_csv_accepts_filename_when_content_type_not_csv(client, db, owner, ws, campaign):
    """Backend allows upload when filename ends in .csv even if browser sends a generic type."""
    csv_data = _make_csv([{"email": "ctype@example.com"}])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "application/octet-stream")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    assert res.json()["imported_count"] == 1


def test_import_csv_rejects_file_over_max_size(client, db, owner, ws, campaign):
    from app.services.lead_service import MAX_FILE_SIZE_BYTES

    oversized = b"email\n" + b"x" * (MAX_FILE_SIZE_BYTES + 1)
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("big.csv", oversized, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 413


@pytest.mark.parametrize("campaign_status", ["completed", "deleted"])
def test_import_csv_rejects_view_only_campaign(
    client, db, owner, ws, campaign_status
):
    c = make_campaign(db, ws.workspace_id, name="Frozen", status=campaign_status)
    csv_data = _make_csv([{"email": "no@example.com"}])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{c.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 409


def test_get_import_session_after_upload(client, db, owner, ws, campaign):
    csv_data = _make_csv([{"email": "sess@example.com"}])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    session_id = res.json()["session_id"]
    get_res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import/{session_id}",
        cookies=auth_cookies(owner),
    )
    assert get_res.status_code == 200
    body = get_res.json()
    assert body["session_id"] == session_id
    assert body["imported_count"] == 1
    assert body["status"] == "completed"


def test_get_import_session_404_wrong_id(client, db, owner, ws, campaign):
    import uuid

    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import/{uuid.uuid4()}",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 404


def test_import_sets_import_session_id_on_leads(client, db, owner, ws, campaign):
    csv_data = _make_csv([{"email": "linked@example.com"}])
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    session_id = res.json()["session_id"]
    from app.models import Lead

    lead = db.query(Lead).filter(Lead.email == "linked@example.com").first()
    assert lead.import_session_id == session_id


# ---------------------------------------------------------------------------
# CSV export — additional cases
# ---------------------------------------------------------------------------


def test_export_csv_empty_campaign_header_only(client, db, owner, ws, campaign):
    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/export",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200
    fieldnames, rows = _parse_export_csv(res.text)
    assert fieldnames == [
        "lead_id",
        "email",
        "first_name",
        "last_name",
        "status",
        "import_session_id",
        "custom_variables",
    ]
    assert rows == []


def test_export_csv_columns_match_created_lead(client, db, owner, ws, campaign):
    client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads",
        json={
            "email": "full@example.com",
            "first_name": "Full",
            "last_name": "Export",
            "custom_variables": {"tier": "pro"},
        },
        cookies=auth_cookies(owner),
    )
    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/export",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200
    _, rows = _parse_export_csv(res.text)
    assert len(rows) == 1
    r = rows[0]
    assert r["email"] == "full@example.com"
    assert r["first_name"] == "Full"
    assert r["last_name"] == "Export"
    assert r["status"] == "active"
    assert "tier" in (r.get("custom_variables") or "") or r.get("custom_variables")


def test_export_import_roundtrip_emails(client, db, owner, ws, campaign):
    """Export after import should list the same addresses (one row per lead)."""
    csv_data = _make_csv(
        [
            {"email": "r1@example.com", "first_name": "One"},
            {"email": "r2@example.com", "first_name": "Two"},
        ]
    )
    imp = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.csv", csv_data, "text/csv")},
        cookies=auth_cookies(owner),
    )
    assert imp.status_code == 201
    exp = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/export",
        cookies=auth_cookies(owner),
    )
    assert exp.status_code == 200
    _, rows = _parse_export_csv(exp.text)
    emails = sorted(r["email"] for r in rows)
    assert emails == ["r1@example.com", "r2@example.com"]


def test_export_csv_includes_leads_for_completed_campaign(client, db, owner, ws):
    """Leads on a completed campaign are still readable and exportable."""
    c = make_campaign(db, ws.workspace_id, status="completed")
    make_lead(db, c.campaign_id, email="arch@example.com")
    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{c.campaign_id}/leads/export",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200
    _, rows = _parse_export_csv(res.text)
    assert len(rows) == 1
    assert rows[0]["email"] == "arch@example.com"


# ---------------------------------------------------------------------------
# XLSX import (optional dependency)
# ---------------------------------------------------------------------------


def test_import_xlsx_basic(client, db, owner, ws, campaign):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wsx = wb.active
    wsx.append(["email", "first_name", "last_name"])
    wsx.append(["xlsx@example.com", "Excel", "User"])
    buf = io.BytesIO()
    wb.save(buf)
    raw = buf.getvalue()
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/leads/import",
        files={"file": ("leads.xlsx", raw, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    assert res.json()["imported_count"] == 1
    from app.models import Lead

    lead = db.query(Lead).filter(Lead.email == "xlsx@example.com").first()
    assert lead.first_name == "Excel"
    assert lead.last_name == "User"

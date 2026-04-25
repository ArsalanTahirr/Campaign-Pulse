"""
tests/test_leads.py — Lead CRUD, CSV import edge cases, and export tests.
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

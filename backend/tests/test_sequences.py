"""
tests/test_sequences.py — SequenceStep and StepEmail management tests.
"""

import pytest
from tests.factories import (
    add_member,
    auth_cookies,
    make_campaign,
    make_step,
    make_step_email,
    make_user,
    make_workspace,
)

SEND_DAYS_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


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
# SequenceStep CRUD
# ---------------------------------------------------------------------------


def test_create_step(client, db, owner, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps",
        json={
            "step_number": 1,
            "wait_days": 0,
            "send_time": "09:00",
            "send_days": SEND_DAYS_WEEKDAYS,
            "email_variants": [],
        },
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    assert res.json()["step_number"] == 1


def test_create_step_with_variant_inline(client, db, owner, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps",
        json={
            "step_number": 1,
            "wait_days": 2,
            "send_time": "09:00",
            "send_days": SEND_DAYS_WEEKDAYS,
            "email_variants": [{"subject_line": "Hi there", "email_body": "Body text"}],
        },
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data["email_variants"]) == 1
    assert data["email_variants"][0]["subject_line"] == "Hi there"


def test_duplicate_step_number_rejected(client, db, owner, ws, campaign):
    make_step(db, campaign.campaign_id, step_number=1)
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps",
        json={
            "step_number": 1,
            "wait_days": 0,
            "send_time": "09:00",
            "send_days": SEND_DAYS_WEEKDAYS,
        },
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 409


def test_analyst_cannot_create_step(client, db, analyst, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps",
        json={
            "step_number": 1,
            "wait_days": 0,
            "send_time": "09:00",
            "send_days": SEND_DAYS_WEEKDAYS,
        },
        cookies=auth_cookies(analyst),
    )
    assert res.status_code == 403


def test_list_steps(client, db, owner, ws, campaign):
    make_step(db, campaign.campaign_id, step_number=1)
    make_step(db, campaign.campaign_id, step_number=2)

    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200
    assert len(res.json()) == 2
    assert res.json()[0]["step_number"] == 1


def test_delete_step_cascades_variants(client, db, owner, ws, campaign):
    step = make_step(db, campaign.campaign_id)
    make_step_email(db, step.step_id)

    res = client.delete(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps/{step.step_id}",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 204

    # Variant must be gone too (cascade)
    from app.models import StepEmail
    assert db.query(StepEmail).filter(StepEmail.step_id == step.step_id).count() == 0


def test_send_time_format_validated(client, db, owner, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps",
        json={
            "step_number": 1,
            "wait_days": 0,
            "send_time": "9:00",
            "send_days": SEND_DAYS_WEEKDAYS,
        },  # invalid — not HH:MM
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 422


def test_valid_send_time(client, db, owner, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps",
        json={
            "step_number": 1,
            "wait_days": 0,
            "send_time": "09:00",
            "send_days": SEND_DAYS_WEEKDAYS,
        },
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    assert res.json()["send_time"] == "09:00"


def test_wait_days_required_on_create(client, db, owner, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps",
        json={"step_number": 1, "send_time": "09:00"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 422


def test_send_time_required_on_create(client, db, owner, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps",
        json={"step_number": 1, "wait_days": 0},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 422


def test_send_days_required_on_create(client, db, owner, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps",
        json={"step_number": 1, "wait_days": 0, "send_time": "09:00"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 422


def test_send_days_empty_list_rejected(client, db, owner, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps",
        json={
            "step_number": 1,
            "wait_days": 0,
            "send_time": "09:00",
            "send_days": [],
        },
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 422


def test_send_days_invalid_weekday_rejected(client, db, owner, ws, campaign):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps",
        json={
            "step_number": 1,
            "wait_days": 0,
            "send_time": "09:00",
            "send_days": ["Mon"],
        },
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# StepEmail variants
# ---------------------------------------------------------------------------


def test_add_variant_to_step(client, db, owner, ws, campaign):
    step = make_step(db, campaign.campaign_id)
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps/{step.step_id}/emails",
        json={"subject_line": "Hello", "email_body": "Body"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    assert res.json()["subject_line"] == "Hello"


def test_update_variant(client, db, owner, ws, campaign):
    step = make_step(db, campaign.campaign_id)
    variant = make_step_email(db, step.step_id)
    res = client.patch(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps/{step.step_id}/emails/{variant.email_id}",
        json={"subject_line": "Updated Subject"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200
    assert res.json()["subject_line"] == "Updated Subject"


def test_delete_variant(client, db, owner, ws, campaign):
    step = make_step(db, campaign.campaign_id)
    variant = make_step_email(db, step.step_id)
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps/{step.step_id}/emails/{variant.email_id}",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 204


def test_variant_wrong_step_404(client, db, owner, ws, campaign):
    import uuid
    step = make_step(db, campaign.campaign_id)
    res = client.patch(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps/{step.step_id}/emails/{uuid.uuid4()}",
        json={"subject_line": "X"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 404


def test_multiple_variants_rotation_setup(client, db, owner, ws, campaign):
    """A step can hold multiple variants for mailbox rotation."""
    step = make_step(db, campaign.campaign_id)
    for i in range(3):
        client.post(
            f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps/{step.step_id}/emails",
            json={"subject_line": f"Subject {i}", "email_body": f"Body {i}"},
            cookies=auth_cookies(owner),
        )

    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps/{step.step_id}/emails",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_duplicate_variant_content_rejected(client, db, owner, ws, campaign):
    step = make_step(db, campaign.campaign_id)
    payload = {"subject_line": "Duplicate Subject", "email_body": "Duplicate Body"}

    first = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps/{step.step_id}/emails",
        json=payload,
        cookies=auth_cookies(owner),
    )
    assert first.status_code == 201

    duplicate = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/steps/{step.step_id}/emails",
        json=payload,
        cookies=auth_cookies(owner),
    )
    assert duplicate.status_code == 409

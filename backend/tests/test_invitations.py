"""
tests/test_invitations.py — Invitation lifecycle + edge cases.
"""

import pytest
from tests.factories import (
    add_member,
    auth_cookies,
    make_invitation,
    make_role,
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
def agency_role(db):
    return make_role(db, "Agency")


@pytest.fixture
def agency_user(db, ws, agency_role):
    user = make_user(db)
    add_member(db, ws.workspace_id, user, "Agency")
    return user


@pytest.fixture
def analyst_user(db, ws):
    user = make_user(db)
    add_member(db, ws.workspace_id, user, "Data Analyst")
    return user


# ---------------------------------------------------------------------------
# Sending invitations
# ---------------------------------------------------------------------------


def test_owner_can_invite(client, db, owner, ws, agency_role):
    invitee = make_user(db, email="newbie@example.com")
    res = client.post(
        f"/workspaces/{ws.workspace_id}/invitations",
        json={"invitee_email": invitee.email, "role_id": agency_role.role_id},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    assert res.json()["status"] == "pending"
    assert res.json()["invitee_email"] == "newbie@example.com"


def test_agency_can_invite(client, db, agency_user, ws, agency_role):
    invitee = make_user(db, email="another@example.com")
    res = client.post(
        f"/workspaces/{ws.workspace_id}/invitations",
        json={"invitee_email": invitee.email, "role_id": agency_role.role_id},
        cookies=auth_cookies(agency_user),
    )
    assert res.status_code == 201


def test_analyst_cannot_invite(client, db, analyst_user, ws, agency_role):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/invitations",
        json={"invitee_email": "hacker@example.com", "role_id": agency_role.role_id},
        cookies=auth_cookies(analyst_user),
    )
    assert res.status_code == 403


def test_duplicate_pending_invite_rejected(client, db, owner, ws, agency_role):
    email = make_user(db, email="dup@example.com").email
    client.post(
        f"/workspaces/{ws.workspace_id}/invitations",
        json={"invitee_email": email, "role_id": agency_role.role_id},
        cookies=auth_cookies(owner),
    )
    res = client.post(
        f"/workspaces/{ws.workspace_id}/invitations",
        json={"invitee_email": email, "role_id": agency_role.role_id},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 409


def test_cannot_invite_existing_member(client, db, owner, ws, agency_role, agency_user):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/invitations",
        json={"invitee_email": agency_user.email, "role_id": agency_role.role_id},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 409


def test_invalid_role_id_returns_404(client, db, owner, ws):
    import uuid
    invitee = make_user(db, email="x@x.com")
    res = client.post(
        f"/workspaces/{ws.workspace_id}/invitations",
        json={"invitee_email": invitee.email, "role_id": str(uuid.uuid4())},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 404


def test_invite_nonexistent_email_returns_404(client, db, owner, ws, agency_role):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/invitations",
        json={"invitee_email": "doesnotexist@example.com", "role_id": agency_role.role_id},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------


def test_validate_valid_token(client, db, owner, ws, agency_role):
    inv = make_invitation(db, ws.workspace_id, owner.user_id, "valid@example.com", agency_role)
    res = client.get(f"/invitations/validate/{inv.token}")
    assert res.status_code == 200
    assert res.json()["status"] == "pending"


def test_validate_expired_token(client, db, owner, ws, agency_role):
    inv = make_invitation(
        db, ws.workspace_id, owner.user_id, "expired@example.com", agency_role, expired=True
    )
    res = client.get(f"/invitations/validate/{inv.token}")
    assert res.status_code == 410


def test_validate_nonexistent_token(client):
    res = client.get("/invitations/validate/totallymadeuptoken")
    assert res.status_code == 404


def test_validate_already_accepted_token(client, db, owner, ws, agency_role):
    inv = make_invitation(
        db, ws.workspace_id, owner.user_id, "done@example.com", agency_role, status="accepted"
    )
    res = client.get(f"/invitations/validate/{inv.token}")
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# Accepting invitations
# ---------------------------------------------------------------------------


def test_accept_valid_invitation(client, db, owner, ws, agency_role):
    invitee = make_user(db, email="invitee@example.com")
    inv = make_invitation(db, ws.workspace_id, owner.user_id, invitee.email, agency_role)

    res = client.post(
        f"/invitations/accept/{inv.token}",
        cookies=auth_cookies(invitee),
    )
    assert res.status_code == 200
    assert res.json()["workspace_id"] == ws.workspace_id


def test_accept_expired_token_fails(client, db, owner, ws, agency_role):
    invitee = make_user(db)
    inv = make_invitation(
        db, ws.workspace_id, owner.user_id, invitee.email, agency_role, expired=True
    )
    res = client.post(f"/invitations/accept/{inv.token}", cookies=auth_cookies(invitee))
    assert res.status_code == 410


def test_double_accept_fails(client, db, owner, ws, agency_role):
    invitee = make_user(db, email="double@example.com")
    inv = make_invitation(db, ws.workspace_id, owner.user_id, invitee.email, agency_role)

    client.post(f"/invitations/accept/{inv.token}", cookies=auth_cookies(invitee))
    res = client.post(f"/invitations/accept/{inv.token}", cookies=auth_cookies(invitee))
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# Cancelling invitations
# ---------------------------------------------------------------------------


def test_owner_can_cancel_pending(client, db, owner, ws, agency_role):
    inv = make_invitation(db, ws.workspace_id, owner.user_id, "cancel@example.com", agency_role)
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/invitations/{inv.invitation_id}",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 204


def test_cancel_already_accepted_fails(client, db, owner, ws, agency_role):
    inv = make_invitation(
        db, ws.workspace_id, owner.user_id, "acc@example.com", agency_role, status="accepted"
    )
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/invitations/{inv.invitation_id}",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 409

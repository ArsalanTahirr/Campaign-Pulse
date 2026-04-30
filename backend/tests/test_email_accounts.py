from app.models import SenderAccount
from tests.factories import auth_cookies, make_user, make_workspace


def test_email_accounts_crud_and_warmup_patch(client, db):
    user = make_user(db)
    ws = make_workspace(db, user)
    cookies = auth_cookies(user)

    create_payload = {
        "provider_type": "smtp",
        "email": "sender@example.com",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "imap_host": "imap.example.com",
        "imap_port": 993,
        "app_password": "secret",
        "status": "active",
        "daily_sending_limit": 120,
        "min_delay_seconds": 30,
        "max_imap_fetch": 200,
        "is_verified": True,
        "warmup_settings": {
            "is_warmup_active": True,
            "start_mail_rate": 10,
            "daily_max_emails": 100,
            "ramp_up_rate": 1.7,
        },
    }
    res = client.post(
        f"/workspaces/{ws.workspace_id}/email-accounts",
        json=create_payload,
        cookies=cookies,
    )
    assert res.status_code == 201, res.text
    created = res.json()
    assert created["email"] == "sender@example.com"
    assert created["warmup_settings"]["is_warmup_active"] is True

    list_res = client.get(f"/workspaces/{ws.workspace_id}/email-accounts", cookies=cookies)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    patch_warmup = client.patch(
        f"/workspaces/{ws.workspace_id}/email-accounts/{created['account_id']}/warmup",
        json={"is_warmup_active": False, "daily_max_emails": 80},
        cookies=cookies,
    )
    assert patch_warmup.status_code == 200, patch_warmup.text
    assert patch_warmup.json()["is_warmup_active"] is False
    assert patch_warmup.json()["daily_max_emails"] == 80

    delete_res = client.delete(
        f"/workspaces/{ws.workspace_id}/email-accounts/{created['account_id']}",
        cookies=cookies,
    )
    assert delete_res.status_code == 204
    assert db.query(SenderAccount).count() == 1
    deleted = db.query(SenderAccount).first()
    assert deleted.deleted_at is not None
    assert deleted.status == "disconnected"


def test_email_accounts_duplicate_email_rejected(client, db):
    user = make_user(db, email="dup-owner@example.com")
    ws = make_workspace(db, user)
    cookies = auth_cookies(user)

    payload = {
        "provider_type": "smtp",
        "email": "sender@example.com",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "imap_host": "imap.example.com",
        "imap_port": 993,
        "app_password": "secret",
        "daily_sending_limit": 120,
        "min_delay_seconds": 30,
        "max_imap_fetch": 200,
    }

    first = client.post(f"/workspaces/{ws.workspace_id}/email-accounts", json=payload, cookies=cookies)
    assert first.status_code == 201, first.text

    second = client.post(
        f"/workspaces/{ws.workspace_id}/email-accounts",
        json={**payload, "email": "SENDER@example.com"},
        cookies=cookies,
    )
    assert second.status_code == 409, second.text


def test_email_accounts_reject_provider_domain_mismatch(client, db):
    user = make_user(db, email="provider-check@example.com")
    ws = make_workspace(db, user)
    cookies = auth_cookies(user)

    bad = client.post(
        f"/workspaces/{ws.workspace_id}/email-accounts",
        json={
            "provider_type": "microsoft",
            "email": "example@gmail.com",
            "smtp_host": "smtp.office365.com",
            "smtp_port": 587,
            "imap_host": "outlook.office365.com",
            "imap_port": 993,
            "app_password": "secret",
            "daily_sending_limit": 50,
            "min_delay_seconds": 60,
            "max_imap_fetch": 100,
        },
        cookies=cookies,
    )
    assert bad.status_code == 422, bad.text

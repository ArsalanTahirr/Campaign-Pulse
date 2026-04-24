import uuid
from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy.exc import IntegrityError


def _unique_email() -> str:
    return f"robust_{uuid.uuid4().hex[:12]}@example.com"


def _valid_payload(**overrides) -> dict:
    payload = {
        "first_name": "Robust",
        "last_name": "Tester",
        "middle_name": None,
        "email": _unique_email(),
        "password": "SecurePass1!",
        "date_of_birth": (date.today() - timedelta(days=365 * 25)).isoformat(),
        "gender": "male",
        "terms_accepted": True,
    }
    payload.update(overrides)
    return payload


def _mock_google_http(mocker, token_json: dict, userinfo_json: dict):
    mock_token = mocker.MagicMock()
    mock_token.status_code = 200
    mock_token.json.return_value = token_json

    mock_userinfo = mocker.MagicMock()
    mock_userinfo.status_code = 200
    mock_userinfo.json.return_value = userinfo_json

    mock_http = mocker.MagicMock()
    mock_http.post.return_value = mock_token
    mock_http.get.return_value = mock_userinfo

    mock_client = mocker.MagicMock()
    mock_client.return_value.__enter__.return_value = mock_http
    mock_client.return_value.__exit__.return_value = False

    mocker.patch("app.routers.users.httpx.Client", mock_client)


def test_signup_rejects_sql_injection_like_email(client, mocker):
    mocker.patch("app.routers.users.send_verification_email", return_value=None)
    payload = _valid_payload(email="' OR 1=1--@example.com")
    resp = client.post("/auth/signup", json=payload)
    assert resp.status_code == 422


def test_signup_missing_required_fields_returns_422(client):
    resp = client.post("/auth/signup", json={"email": _unique_email()})
    assert resp.status_code == 422


def test_login_wrong_password_never_leaks_detail(client, mocker):
    mocker.patch("app.routers.users.send_verification_email", return_value=None)
    payload = _valid_payload()
    signup = client.post("/auth/signup", json=payload)
    assert signup.status_code == 201

    resp = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": "WrongPass1!"},
    )
    assert resp.status_code == 401
    assert "invalid email or password" in resp.json()["detail"].lower()


def test_signup_handles_smtp_timeout_without_crashing(client, mocker):
    # Simulate provider outage inside background task.
    mocker.patch(
        "app.routers.users.send_verification_email",
        side_effect=TimeoutError("smtp timeout"),
    )
    resp = client.post("/auth/signup", json=_valid_payload())
    assert resp.status_code == 201


def test_google_callback_network_error_returns_502(client, mocker):
    mock_client = mocker.MagicMock()
    mock_client.return_value.__enter__.return_value.post.side_effect = httpx.ConnectTimeout(
        "boom"
    )
    mock_client.return_value.__exit__.return_value = False
    mocker.patch("app.routers.users.httpx.Client", mock_client)

    resp = client.get("/auth/google/callback?code=fake_code", follow_redirects=False)
    assert resp.status_code == 502
    assert "network error" in resp.json()["detail"].lower()


def test_google_callback_incomplete_userinfo_returns_400(client, mocker):
    _mock_google_http(
        mocker,
        token_json={"access_token": "goog_at"},
        userinfo_json={"sub": "", "email": ""},
    )
    resp = client.get("/auth/google/callback?code=fake_code", follow_redirects=False)
    assert resp.status_code == 400
    assert "incomplete" in resp.json()["detail"].lower()


def test_verify_email_invalid_token_redirects_clean_error_page(client):
    resp = client.get(
        "/auth/verify-email?token=this.is.not.valid",
        follow_redirects=False,
    )
    assert resp.status_code == 307
    assert "status=error" in resp.headers["location"]


def test_campaign_insert_with_invalid_fk_fails_integrity(db):
    from app.models import Campaign

    campaign = Campaign(
        campaign_id=str(uuid.uuid4()),
        workspace_id=str(uuid.uuid4()),
        campaign_name="Broken FK campaign",
        status="draft",
        timezone="UTC",
    )
    db.add(campaign)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.parametrize(
    "overrides",
    [
        {"first_name": "A"},
        {"last_name": "B"},
        {"middle_name": "X"},
        {"gender": "invalid_value"},
        {"date_of_birth": "not-a-date"},
        {"email": "plainaddress"},
    ],
)
def test_signup_rejects_invalid_field_shapes(client, overrides):
    resp = client.post("/auth/signup", json=_valid_payload(**overrides))
    assert resp.status_code == 422


def test_signup_accepts_exact_minimum_valid_password(client, mocker):
    mocker.patch("app.routers.users.send_verification_email", return_value=None)
    resp = client.post("/auth/signup", json=_valid_payload(password="Aa1!aaaa"))
    assert resp.status_code == 201


def test_signup_rejects_underage_boundary(client):
    underage_dob = (date.today() - timedelta(days=365 * 17 + 364)).isoformat()
    resp = client.post("/auth/signup", json=_valid_payload(date_of_birth=underage_dob))
    assert resp.status_code == 422


def test_signup_accepts_exactly_18_years_old(client, mocker):
    mocker.patch("app.routers.users.send_verification_email", return_value=None)
    today = date.today()
    try:
        exactly_18_date = today.replace(year=today.year - 18)
    except ValueError:
        # Handles Feb 29 on non-leap target year.
        exactly_18_date = today.replace(month=2, day=28, year=today.year - 18)
    exactly_18 = exactly_18_date.isoformat()
    resp = client.post("/auth/signup", json=_valid_payload(date_of_birth=exactly_18))
    assert resp.status_code == 201


def test_login_rejects_unverified_user(client, mocker):
    mocker.patch("app.routers.users.send_verification_email", return_value=None)
    payload = _valid_payload()
    signup = client.post("/auth/signup", json=payload)
    assert signup.status_code == 201

    login_resp = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_resp.status_code == 403
    assert "verify" in login_resp.json()["detail"].lower()


def test_verify_email_reuse_redirects_error(client, db, mocker):
    from app.models import LocalAuth, User

    mocker.patch("app.routers.users.send_verification_email", return_value=None)
    payload = _valid_payload()
    signup = client.post("/auth/signup", json=payload)
    assert signup.status_code == 201

    user = db.query(User).filter(User.email == payload["email"]).first()
    local_auth = db.query(LocalAuth).filter(LocalAuth.user_id == user.user_id).first()
    token = local_auth.verification_token

    first = client.get(f"/auth/verify-email?token={token}", follow_redirects=False)
    assert first.status_code == 307
    second = client.get(f"/auth/verify-email?token={token}", follow_redirects=False)
    assert second.status_code == 307
    assert "status=error" in second.headers["location"]


def test_google_callback_non_200_token_exchange_returns_400(client, mocker):
    mock_token = mocker.MagicMock()
    mock_token.status_code = 401
    mock_token.json.return_value = {}

    mock_http = mocker.MagicMock()
    mock_http.post.return_value = mock_token

    mock_client = mocker.MagicMock()
    mock_client.return_value.__enter__.return_value = mock_http
    mock_client.return_value.__exit__.return_value = False
    mocker.patch("app.routers.users.httpx.Client", mock_client)

    resp = client.get("/auth/google/callback?code=bad_code", follow_redirects=False)
    assert resp.status_code == 400
    assert "exchange authorization code" in resp.json()["detail"].lower()


def test_google_callback_non_200_userinfo_returns_400(client, mocker):
    mock_token = mocker.MagicMock()
    mock_token.status_code = 200
    mock_token.json.return_value = {"access_token": "ok"}

    mock_userinfo = mocker.MagicMock()
    mock_userinfo.status_code = 401
    mock_userinfo.json.return_value = {}

    mock_http = mocker.MagicMock()
    mock_http.post.return_value = mock_token
    mock_http.get.return_value = mock_userinfo

    mock_client = mocker.MagicMock()
    mock_client.return_value.__enter__.return_value = mock_http
    mock_client.return_value.__exit__.return_value = False
    mocker.patch("app.routers.users.httpx.Client", mock_client)

    resp = client.get("/auth/google/callback?code=ok_code", follow_redirects=False)
    assert resp.status_code == 400
    assert "retrieve user information" in resp.json()["detail"].lower()


def test_google_callback_requires_code_param(client):
    resp = client.get("/auth/google/callback", follow_redirects=False)
    assert resp.status_code == 422


def test_oauth_unique_constraint_blocks_duplicate_provider_identity(db):
    from app.models import OAuthAccount, User

    user_1 = User(
        user_id=str(uuid.uuid4()),
        first_name="U1",
        last_name="T",
        email=_unique_email(),
        is_verified=True,
    )
    user_2 = User(
        user_id=str(uuid.uuid4()),
        first_name="U2",
        last_name="T",
        email=_unique_email(),
        is_verified=True,
    )
    db.add(user_1)
    db.add(user_2)
    db.flush()

    provider_sub = f"google_sub_{uuid.uuid4().hex}"
    db.add(
        OAuthAccount(
            id=str(uuid.uuid4()),
            user_id=user_1.user_id,
            provider_type="google",
            provider_id=provider_sub,
            access_token="tok1",
        )
    )
    db.commit()

    db.add(
        OAuthAccount(
            id=str(uuid.uuid4()),
            user_id=user_2.user_id,
            provider_type="google",
            provider_id=provider_sub,
            access_token="tok2",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_lead_unique_constraint_blocks_duplicate_email_per_campaign(db):
    from app.models import Campaign, Lead, Workspace

    workspace = Workspace(
        workspace_id=str(uuid.uuid4()),
        workspace_name="QA Workspace",
    )
    db.add(workspace)
    db.flush()

    campaign = Campaign(
        campaign_id=str(uuid.uuid4()),
        workspace_id=workspace.workspace_id,
        campaign_name="QA Campaign",
        status="draft",
        timezone="UTC",
    )
    db.add(campaign)
    db.flush()

    email = _unique_email()
    db.add(
        Lead(
            lead_id=str(uuid.uuid4()),
            campaign_id=campaign.campaign_id,
            email=email,
        )
    )
    db.commit()

    db.add(
        Lead(
            lead_id=str(uuid.uuid4()),
            campaign_id=campaign.campaign_id,
            email=email,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

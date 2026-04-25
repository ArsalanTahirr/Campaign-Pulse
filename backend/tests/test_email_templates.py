from app import email_utils


def _capture_message(mocker):
    smtp = mocker.MagicMock()
    smtp.__enter__.return_value = smtp
    smtp.__exit__.return_value = False
    mocker.patch("app.email_utils.smtplib.SMTP_SSL", return_value=smtp)
    return smtp


def _prepare_email_env(monkeypatch):
    monkeypatch.setattr(email_utils, "SMTP_EMAIL", "smtp@example.com")
    monkeypatch.setattr(email_utils, "SMTP_APP_PASSWORD", "app-password")
    monkeypatch.setattr(email_utils, "EMAIL_FROM", "")
    monkeypatch.setattr(email_utils, "FRONTEND_URL", "https://campaignpulse.example")
    monkeypatch.setattr(
        email_utils,
        "LOGO_URL",
        "https://campaignpulse.example/icon.png",
    )


def test_password_reset_email_uses_shared_gradient_shell(mocker, monkeypatch):
    _prepare_email_env(monkeypatch)
    smtp = _capture_message(mocker)

    email_utils.send_password_reset_email(
        to_email="user@example.com",
        token="reset-token",
        first_name="Arsalan",
    )

    message = smtp.send_message.call_args.args[0]
    html_body = message.get_body(preferencelist=("html",)).get_content()

    assert "linear-gradient(135deg,#4f46e5 0%,#6366f1 55%,#38bdf8 100%)" in html_body
    assert 'src="https://campaignpulse.example/icon.png"' in html_body
    assert "Reset your password" in html_body
    assert "Reset Password" in html_body
    assert "This link expires in 60 minutes." in html_body
    assert "Button not working? Copy and paste the link below into your browser:" in html_body
    assert "https://campaignpulse.example/reset-password?token=reset-token" in html_body
    assert "123 Growth Street, San Francisco, CA" in html_body


def test_account_link_email_uses_shared_gradient_shell(mocker, monkeypatch):
    _prepare_email_env(monkeypatch)
    smtp = _capture_message(mocker)

    email_utils.send_account_link_email(
        to_email="user@example.com",
        token="link-token",
        first_name="Arsalan",
        base_url="https://backend.example",
    )

    message = smtp.send_message.call_args.args[0]
    html_body = message.get_body(preferencelist=("html",)).get_content()

    assert "linear-gradient(135deg,#4f46e5 0%,#6366f1 55%,#38bdf8 100%)" in html_body
    assert 'src="https://campaignpulse.example/icon.png"' in html_body
    assert "Verify your email" in html_body
    assert "Verify Email &amp; Link Password Sign-In" in html_body
    assert "This link expires in 24 hours." in html_body
    assert "Button not working? Copy and paste the link below into your browser:" in html_body
    assert "https://backend.example/auth/link-local-account?token=link-token" in html_body
    assert "You are receiving this email because you have a" in html_body

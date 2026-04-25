"""
email_utils.py — Email delivery and template rendering for CampaignPulse.

Uses SMTP (smtplib) for transactional email delivery.
Credentials are read from SMTP_EMAIL and SMTP_APP_PASSWORD in the .env file.

Email deliverability best practices applied:
  - Multipart message: HTML + plain-text alternative.
  - Inline CSS only (no external stylesheets) — Gmail strips <style> blocks.
  - Hidden pre-header text for inbox preview snippets.
  - No JavaScript, no tracking pixels, no external image dependencies beyond
    the hosted app icon.
  - CAN-SPAM compliant footer with physical address.
  - Mobile-responsive 600 px centered table layout.
  - Single clear CTA button with sufficient colour contrast.
"""

import os
import smtplib
from email.message import EmailMessage
from html import escape as html_escape

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

SMTP_HOST: str = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "465"))
SMTP_EMAIL: str = os.environ.get("SMTP_EMAIL", "")
SMTP_APP_PASSWORD: str = os.environ.get("SMTP_APP_PASSWORD", "")
EMAIL_FROM: str = os.environ.get("EMAIL_FROM", "")
FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:3000")
FRONTEND_RESET_PASSWORD_PATH: str = os.environ.get("FRONTEND_RESET_PASSWORD_PATH", "/reset-password")

# The icon lives at public/icon.png in the Next.js project, served at /icon.png.
LOGO_URL: str = f"{FRONTEND_URL.rstrip('/')}/icon.png"


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------


def _build_transactional_html(
    *,
    document_title: str,
    preheader: str,
    heading: str,
    first_name: str,
    intro_paragraphs: list[str],
    button_label: str,
    button_url: str,
    expiry_text: str,
    fallback_intro: str,
) -> str:
    """
    Return a fully self-contained HTML email body.

    Designed to render correctly in Gmail, Outlook, Apple Mail, and
    mobile clients.  All styles are inlined; no JavaScript is used.
    """
    safe_first_name = html_escape(first_name)
    safe_heading = html_escape(heading)
    safe_intro_paragraphs = [html_escape(paragraph) for paragraph in intro_paragraphs]
    safe_button_label = html_escape(button_label)
    safe_button_url = html_escape(button_url, quote=True)
    safe_expiry_text = expiry_text
    safe_fallback_intro = html_escape(fallback_intro)

    intro_html = "\n              ".join(
        f'<p style="margin:0 0 12px;font-size:15px;color:#334155;line-height:1.75;">{paragraph}</p>'
        for paragraph in safe_intro_paragraphs
    )

    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <title>{html_escape(document_title)}</title>
  <!--[if mso]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#f8fafc;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,
             'Helvetica Neue',Arial,sans-serif;-webkit-text-size-adjust:100%;
             -ms-text-size-adjust:100%;">

  <!-- Hidden pre-header text displayed as inbox preview snippet -->
  <div style="display:none;max-height:0;overflow:hidden;mso-hide:all;
              font-size:1px;color:#f8fafc;line-height:1px;">
    {html_escape(preheader)}
    &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
    &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
  </div>

  <!-- Outer wrapper table -->
  <table role="presentation" cellspacing="0" cellpadding="0" border="0"
         width="100%" style="background-color:#f8fafc;">
    <tr>
      <td align="center" style="padding:48px 16px;">

        <!-- Email card (max-width 600 px) -->
        <table role="presentation" cellspacing="0" cellpadding="0" border="0"
               width="600"
               style="max-width:600px;width:100%;background-color:#ffffff;
                      border-radius:16px;
                      box-shadow:0 4px 24px rgba(15,23,42,0.08);
                      overflow:hidden;">

          <!-- Header gradient banner -->
          <tr>
            <td style="background:linear-gradient(135deg,#4f46e5 0%,#6366f1 55%,#38bdf8 100%);
                        padding:32px 40px;text-align:center;">
              <table role="presentation" cellspacing="0" cellpadding="0"
                     border="0" style="margin:0 auto;">
                <tr>
                  <td style="vertical-align:middle;padding-right:12px;">
                    <img src="{LOGO_URL}" alt="CampaignPulse logo" width="40" height="40"
                         style="display:block;border-radius:9px;
                                border:0;outline:none;text-decoration:none;" />
                  </td>
                  <td style="vertical-align:middle;">
                    <span style="color:#ffffff;font-size:20px;font-weight:700;
                                 letter-spacing:-0.3px;white-space:nowrap;">
                      CampaignPulse
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px;">
              <h1 style="margin:0 0 16px;font-size:24px;font-weight:700;
                         color:#0f172a;letter-spacing:-0.4px;line-height:1.3;">
                {safe_heading}
              </h1>
              <p style="margin:0 0 12px;font-size:15px;color:#334155;line-height:1.75;">
                Hi {safe_first_name},
              </p>
              {intro_html}

              <!-- CTA button -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0;">
                <tr>
                  <td style="border-radius:8px;background-color:#4f46e5;">
                    <a href="{safe_button_url}"
                       target="_blank"
                       style="display:inline-block;padding:14px 36px;
                              font-size:15px;font-weight:700;
                              color:#ffffff;text-decoration:none;
                              border-radius:8px;letter-spacing:0.1px;
                              mso-padding-alt:14px 36px;">
                      <!--[if mso]>&nbsp;<![endif]-->
                      {safe_button_label}
                      <!--[if mso]>&nbsp;<![endif]-->
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Expiry notice -->
              <p style="margin:28px 0 0;font-size:13px;color:#64748b;line-height:1.65;">
                {safe_expiry_text}
              </p>

              <!-- Fallback plain-text URL -->
              <p style="margin:20px 0 0;font-size:12px;color:#94a3b8;line-height:1.6;">
                {safe_fallback_intro}
              </p>
              <p style="margin:6px 0 0;font-size:12px;line-height:1.6;word-break:break-all;">
                <a href="{safe_button_url}"
                   style="color:#4f46e5;text-decoration:underline;">
                  {safe_button_url}
                </a>
              </p>
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <div style="border-top:1px solid #e2e8f0;"></div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:24px 40px 36px;text-align:center;">
              <p style="margin:0 0 6px;font-size:12px;color:#94a3b8;line-height:1.6;">
                You are receiving this email because you have a
                <a href="{FRONTEND_URL}"
                   style="color:#4f46e5;text-decoration:none;">
                  CampaignPulse
                </a> account.
              </p>
              <p style="margin:0;font-size:11px;color:#cbd5e1;line-height:1.6;">
                CampaignPulse &middot; 123 Growth Street, San Francisco, CA&nbsp;94107
              </p>
            </td>
          </tr>

        </table>
        <!-- /Email card -->

      </td>
    </tr>
  </table>

</body>
</html>"""


def _build_verification_html(verification_url: str, first_name: str) -> str:
    return _build_transactional_html(
        document_title="Verify your CampaignPulse email",
        preheader="Confirm your email address to activate your CampaignPulse account.",
        heading="Verify your email address",
        first_name=first_name,
        intro_paragraphs=[
            "Thanks for creating a CampaignPulse account. To activate your account and start building high-converting email campaigns, please confirm your email address by clicking the button below.",
        ],
        button_label="Verify Email Address",
        button_url=verification_url,
        expiry_text=(
            "This link is valid for <strong>24&nbsp;hours</strong>. If you did not create a CampaignPulse account, you can safely ignore this email — no action is required."
        ),
        fallback_intro="Button not working? Copy and paste the link below into your browser:",
    )


# ---------------------------------------------------------------------------
# Plain-text fallback
# ---------------------------------------------------------------------------


def _build_verification_text(verification_url: str, first_name: str) -> str:
    return (
        f"Hi {first_name},\n\n"
        "Thanks for signing up for CampaignPulse.\n\n"
        "Please verify your email address by visiting the link below:\n\n"
        f"{verification_url}\n\n"
        "This link expires in 24 hours.\n\n"
        "If you did not create a CampaignPulse account, you can safely ignore "
        "this email.\n\n"
        "— The CampaignPulse Team\n\n"
        "CampaignPulse · 123 Growth Street, San Francisco, CA 94107"
    )


def _build_password_reset_text(reset_url: str, first_name: str) -> str:
    return (
        f"Hi {first_name},\n\n"
        "We received a request to reset your CampaignPulse password.\n\n"
        f"Reset your password here:\n{reset_url}\n\n"
        "This link expires in 60 minutes.\n\n"
        "If you did not request this, you can ignore this email.\n\n"
        "CampaignPulse · 123 Growth Street, San Francisco, CA 94107"
    )


def _build_account_link_text(link_url: str, first_name: str) -> str:
    return (
        f"Hi {first_name},\n\n"
        "We received a request to add password sign-in to your CampaignPulse account.\n\n"
        f"Confirm your email and link password sign-in here:\n{link_url}\n\n"
        "This link expires in 24 hours.\n\n"
        "If you did not request this, you can ignore this email.\n\n"
        "CampaignPulse · 123 Growth Street, San Francisco, CA 94107"
    )


# ---------------------------------------------------------------------------
# Public send function
# ---------------------------------------------------------------------------


def send_verification_email(
    to_email: str,
    token: str,
    first_name: str,
    base_url: str,
) -> None:
    """
    Send a transactional verification email via SMTP.

    This function is designed to be called as a FastAPI BackgroundTask so
    that the /signup response is returned to the client immediately without
    waiting for SMTP network I/O.

    Args:
        to_email:   Recipient's email address.
        token:      The itsdangerous signed verification token.
        first_name: Recipient's first name (used in the email greeting).
        base_url:   Base URL of the backend API (e.g. "http://localhost:8000").
                    The verification link will be appended as
                    /auth/verify-email?token=<token>.
    """
    verification_url = f"{base_url}/auth/verify-email?token={token}"
    sender = EMAIL_FROM or SMTP_EMAIL
    if not sender:
        raise RuntimeError("SMTP sender is not configured. Set EMAIL_FROM or SMTP_EMAIL.")
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        raise RuntimeError("SMTP credentials missing. Set SMTP_EMAIL and SMTP_APP_PASSWORD.")

    message = EmailMessage()
    message["From"] = f"CampaignPulse <{sender}>"
    message["To"] = to_email
    message["Subject"] = "Verify your CampaignPulse email address"
    message.set_content(_build_verification_text(verification_url, first_name))
    message.add_alternative(
        _build_verification_html(verification_url, first_name),
        subtype="html",
    )

    # Gmail app-password setups typically use SSL on 465.
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        smtp.send_message(message)


def send_password_reset_email(
    to_email: str,
    token: str,
    first_name: str,
) -> None:
    """
    Send a password-reset email via SMTP.
    """
    reset_url = f"{FRONTEND_URL}{FRONTEND_RESET_PASSWORD_PATH}?token={token}"
    sender = EMAIL_FROM or SMTP_EMAIL
    if not sender:
        raise RuntimeError("SMTP sender is not configured. Set EMAIL_FROM or SMTP_EMAIL.")
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        raise RuntimeError("SMTP credentials missing. Set SMTP_EMAIL and SMTP_APP_PASSWORD.")

    text_body = (
        _build_password_reset_text(reset_url, first_name)
    )
    html_body = _build_transactional_html(
        document_title="Reset your CampaignPulse password",
        preheader="Reset your CampaignPulse password.",
        heading="Reset your password",
        first_name=first_name,
        intro_paragraphs=[
            "We received a request to reset your CampaignPulse password.",
        ],
        button_label="Reset Password",
        button_url=reset_url,
        expiry_text="This link expires in 60 minutes.",
        fallback_intro="Button not working? Copy and paste the link below into your browser:",
    )

    message = EmailMessage()
    message["From"] = f"CampaignPulse <{sender}>"
    message["To"] = to_email
    message["Subject"] = "Reset your CampaignPulse password"
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        smtp.send_message(message)


def send_account_link_email(
    to_email: str,
    token: str,
    first_name: str,
    base_url: str,
) -> None:
    """
    Send account-link verification email for OAuth-to-local linking.
    """
    link_url = f"{base_url}/auth/link-local-account?token={token}"
    sender = EMAIL_FROM or SMTP_EMAIL
    if not sender:
        raise RuntimeError("SMTP sender is not configured. Set EMAIL_FROM or SMTP_EMAIL.")
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        raise RuntimeError("SMTP credentials missing. Set SMTP_EMAIL and SMTP_APP_PASSWORD.")

    text_body = (
        _build_account_link_text(link_url, first_name)
    )
    html_body = _build_transactional_html(
        document_title="Verify your email to link password sign-in",
        preheader="Verify your email to add password sign-in to your account.",
        heading="Verify your email",
        first_name=first_name,
        intro_paragraphs=[
            "We received a request to add password sign-in to your CampaignPulse account.",
            "To keep your account secure, please verify your email before we enable password sign-in.",
        ],
        button_label="Verify Email & Link Password Sign-In",
        button_url=link_url,
        expiry_text="This link expires in 24 hours.",
        fallback_intro="Button not working? Copy and paste the link below into your browser:",
    )

    message = EmailMessage()
    message["From"] = f"CampaignPulse <{sender}>"
    message["To"] = to_email
    message["Subject"] = "Verify your email to link password sign-in"
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        smtp.send_message(message)

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
FRONTEND_INVITATION_ACCEPT_PATH: str = os.environ.get(
    "FRONTEND_INVITATION_ACCEPT_PATH",
    "/invitations/accept",
)

# The icon lives at public/icon.png in the Next.js project, served at /icon.png.
LOGO_URL: str = f"{FRONTEND_URL}/icon.png"


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------


def _build_verification_html(verification_url: str, first_name: str) -> str:
    """
    Return a fully self-contained HTML email body.

    Designed to render correctly in Gmail, Outlook, Apple Mail, and
    mobile clients.  All styles are inlined; no JavaScript is used.
    """
    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <title>Verify your CampaignPulse email</title>
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
<body style="margin:0;padding:0;background-color:#f1f5f9;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,
             'Helvetica Neue',Arial,sans-serif;-webkit-text-size-adjust:100%;
             -ms-text-size-adjust:100%;">

  <!-- Hidden pre-header text displayed as inbox preview snippet -->
  <div style="display:none;max-height:0;overflow:hidden;mso-hide:all;
              font-size:1px;color:#f1f5f9;line-height:1px;">
    Confirm your email address to activate your CampaignPulse account.
    &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
    &nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
  </div>

  <!-- Outer wrapper table -->
  <table role="presentation" cellspacing="0" cellpadding="0" border="0"
         width="100%" style="background-color:#f1f5f9;">
    <tr>
      <td align="center" style="padding:48px 16px;">

        <!-- Email card (max-width 600 px) -->
        <table role="presentation" cellspacing="0" cellpadding="0" border="0"
               width="600"
               style="max-width:600px;width:100%;background-color:#ffffff;
                      border-radius:16px;
                      box-shadow:0 4px 24px rgba(15,23,42,0.08);
                      overflow:hidden;">

          <!-- ── Header gradient banner ── -->
          <tr>
            <td style="background:linear-gradient(135deg,#4f46e5 0%,#6366f1 55%,#38bdf8 100%);
                        padding:32px 40px;text-align:center;">
              <table role="presentation" cellspacing="0" cellpadding="0"
                     border="0" style="margin:0 auto;">
                <tr>
                  <td style="vertical-align:middle;padding-right:12px;">
                    <img src="{LOGO_URL}" alt="" width="40" height="40"
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

          <!-- ── Body ── -->
          <tr>
            <td style="padding:44px 40px 32px;">
              <h1 style="margin:0 0 16px;font-size:24px;font-weight:700;
                         color:#0f172a;letter-spacing:-0.4px;line-height:1.3;">
                Verify your email address
              </h1>
              <p style="margin:0 0 12px;font-size:15px;color:#334155;line-height:1.75;">
                Hi {first_name},
              </p>
              <p style="margin:0 0 28px;font-size:15px;color:#334155;line-height:1.75;">
                Thanks for creating a CampaignPulse account. To activate your account
                and start building high-converting email campaigns, please confirm your
                email address by clicking the button below.
              </p>

              <!-- CTA button -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td style="border-radius:10px;background-color:#4f46e5;">
                    <a href="{verification_url}"
                       target="_blank"
                       style="display:inline-block;padding:14px 36px;
                              font-size:15px;font-weight:600;
                              color:#ffffff;text-decoration:none;
                              border-radius:10px;letter-spacing:0.1px;
                              mso-padding-alt:14px 36px;">
                      <!--[if mso]>&nbsp;<![endif]-->
                      Verify Email Address
                      <!--[if mso]>&nbsp;<![endif]-->
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Expiry notice -->
              <p style="margin:28px 0 0;font-size:13px;color:#64748b;line-height:1.65;">
                This link is valid for <strong>24&nbsp;hours</strong>.
                If you did not create a CampaignPulse account, you can safely ignore
                this email — no action is required.
              </p>

              <!-- Fallback plain-text URL -->
              <p style="margin:20px 0 0;font-size:12px;color:#94a3b8;line-height:1.6;">
                Button not working? Copy and paste the link below into your browser:
              </p>
              <p style="margin:6px 0 0;font-size:12px;line-height:1.6;word-break:break-all;">
                <a href="{verification_url}"
                   style="color:#4f46e5;text-decoration:underline;">
                  {verification_url}
                </a>
              </p>
            </td>
          </tr>

          <!-- ── Divider ── -->
          <tr>
            <td style="padding:0 40px;">
              <div style="border-top:1px solid #e2e8f0;"></div>
            </td>
          </tr>

          <!-- ── Footer ── -->
          <tr>
            <td style="padding:24px 40px 36px;text-align:center;">
              <p style="margin:0 0 6px;font-size:12px;color:#94a3b8;line-height:1.6;">
                You are receiving this email because you registered at
                <a href="{FRONTEND_URL}"
                   style="color:#4f46e5;text-decoration:none;">
                  CampaignPulse
                </a>.
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
        f"Hi {first_name},\n\n"
        "We received a request to reset your CampaignPulse password.\n\n"
        f"Reset your password here:\n{reset_url}\n\n"
        "This link expires in 60 minutes.\n"
        "If you did not request this, you can ignore this email."
    )
    html_body = f"""
<html>
  <body style="font-family:Arial,sans-serif;color:#1f2937;">
    <h2>Reset your password</h2>
    <p>Hi {first_name},</p>
    <p>We received a request to reset your CampaignPulse password.</p>
    <p><a href="{reset_url}" style="display:inline-block;padding:10px 16px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:8px;">Reset Password</a></p>
    <p style="font-size:13px;color:#6b7280;">This link expires in 60 minutes.</p>
    <p style="font-size:13px;color:#6b7280;">If you did not request this, you can ignore this email.</p>
  </body>
</html>
""".strip()

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
        f"Hi {first_name},\n\n"
        "We detected an attempt to add password login to your Google account.\n\n"
        f"Confirm account linking here:\n{link_url}\n\n"
        "This link expires in 24 hours. If this wasn't you, ignore this email."
    )
    html_body = f"""
<html>
  <body style="font-family:Arial,sans-serif;color:#1f2937;">
    <h2>Confirm account linking</h2>
    <p>Hi {first_name},</p>
    <p>We detected a request to add password login to your Google account.</p>
    <p><a href="{link_url}" style="display:inline-block;padding:10px 16px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:8px;">Verify Email & Link Account</a></p>
    <p style="font-size:13px;color:#6b7280;">This link expires in 24 hours.</p>
    <p style="font-size:13px;color:#6b7280;">If you did not request this, ignore this email.</p>
  </body>
</html>
""".strip()

    message = EmailMessage()
    message["From"] = f"CampaignPulse <{sender}>"
    message["To"] = to_email
    message["Subject"] = "Verify to link password login"
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        smtp.send_message(message)


def send_invitation_email(
    to_email: str,
    token: str,
    workspace_name: str,
    inviter_name: str,
    role_name: str,
) -> None:
    """
    Send workspace invitation email containing token acceptance URL.
    """
    invite_url = f"{FRONTEND_URL}{FRONTEND_INVITATION_ACCEPT_PATH}/{token}"
    sender = EMAIL_FROM or SMTP_EMAIL
    if not sender:
        raise RuntimeError("SMTP sender is not configured. Set EMAIL_FROM or SMTP_EMAIL.")
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        raise RuntimeError("SMTP credentials missing. Set SMTP_EMAIL and SMTP_APP_PASSWORD.")

    text_body = (
        f"Hi,\n\n"
        f"{inviter_name} invited you to join '{workspace_name}' as {role_name} on CampaignPulse.\n\n"
        f"Accept invitation:\n{invite_url}\n\n"
        "This invite expires in 72 hours."
    )
    html_body = f"""
<html>
  <body style="font-family:Arial,sans-serif;color:#1f2937;">
    <h2>You are invited to CampaignPulse</h2>
    <p>{inviter_name} invited you to join <strong>{workspace_name}</strong> as <strong>{role_name}</strong>.</p>
    <p>
      <a href="{invite_url}" style="display:inline-block;padding:10px 16px;background:#4f46e5;color:#fff;text-decoration:none;border-radius:8px;">
        Accept Invitation
      </a>
    </p>
    <p style="font-size:13px;color:#6b7280;">This invitation expires in 72 hours.</p>
  </body>
</html>
""".strip()

    message = EmailMessage()
    message["From"] = f"CampaignPulse <{sender}>"
    message["To"] = to_email
    message["Subject"] = f"You are invited to {workspace_name} on CampaignPulse"
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        smtp.send_message(message)

"""
PrimeEdge Email Notification Service
Sends institutional HTML emails via SMTP when founder cohort events occur.
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

def _get_smtp_config():
    return {
        "host": os.getenv("SMTP_HOST", "smtppro.zoho.com"),
        "port": int(os.getenv("SMTP_PORT", "465")),
        "user": os.getenv("SMTP_USER", "abu@primeedge.app"),
        "password": os.getenv("SMTP_PASS", ""),
        "from_addr": os.getenv("SMTP_FROM", "abu@primeedge.app"),
        "admin_notify": os.getenv("ADMIN_NOTIFY_EMAIL", "abu@primeedge.app")
    }


def _send_email(to: str, subject: str, html_body: str) -> bool:
    """Send a single HTML email via Resend API (fastest, modern HTTP) or fallback to SMTP."""
    resend_key = os.getenv("RESEND_API_KEY", "")
    from_email = os.getenv("EMAIL_FROM", "PrimeEdge <abu@primeedge.app>")

    if resend_key:
        try:
            import httpx
            resp = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_email,
                    "to": [to],
                    "subject": subject,
                    "html": html_body,
                },
                timeout=10,
            )
            if resp.status_code in (200, 201):
                logger.info(f"Email sent successfully via Resend to {to}: {subject}")
                return True
            else:
                logger.warning(f"Resend send returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Resend API error: {e}")

    # Fallback to SMTP
    cfg = _get_smtp_config()
    if not cfg["user"] or not cfg["password"]:
        logger.warning("SMTP credentials not configured. Skipping SMTP email send.")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg["from_addr"]
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))

        if cfg["port"] == 465:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"]) as server:
                server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["from_addr"], [to], msg.as_string())
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
                server.ehlo()
                server.starttls()
                server.login(cfg["user"], cfg["password"])
                server.sendmail(cfg["from_addr"], [to], msg.as_string())
        logger.info(f"Email sent successfully via SMTP to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False


def notify_admin_new_waitlist_lead(
    full_name: str,
    email: str,
    broker_platform: Optional[str],
    contact_method: Optional[str],
    why_interested: Optional[str],
    spot_number: int,
    remaining_spots: int,
):
    """Notify admin immediately when a new founder cohort application arrives."""
    subject = f"\U0001f6a8 New Founder Alpha Application #{spot_number} \u2014 {full_name}"

    urgency_color = "#10b981" if remaining_spots > 5 else ("#f59e0b" if remaining_spots > 2 else "#ef4444")
    spots_text = f"<strong style='color:{urgency_color};'>{remaining_spots} spots remaining</strong>"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <title>New Founder Alpha Application</title>
    </head>
    <body style="margin:0;padding:0;background:#08090d;font-family:Outfit,Arial,sans-serif;">
      <div style="max-width:620px;margin:32px auto;background:#111318;border:1px solid #242936;border-radius:12px;overflow:hidden;">

        <!-- Header -->
        <div style="background:linear-gradient(135deg,#0d1520,#111827);border-bottom:1px solid #242936;padding:24px 32px;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
            <div style="width:32px;height:32px;background:linear-gradient(135deg,#00f2fe,#38bdf8);border-radius:7px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:16px;color:#08090d;">P</div>
            <span style="font-size:18px;font-weight:800;color:#fff;letter-spacing:-0.3px;">PrimeEdge</span>
          </div>
          <div style="color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:0.8px;">Founder Operations Command Center</div>
        </div>

        <!-- Alert Banner -->
        <div style="background:rgba(0,242,254,0.08);border-left:4px solid #00f2fe;padding:16px 32px;">
          <div style="font-size:14px;font-weight:800;color:#00f2fe;text-transform:uppercase;letter-spacing:0.5px;">\U0001f6a8 New Founder Alpha Application Received</div>
          <div style="font-size:12px;color:#94a3b8;margin-top:4px;">{spots_text} \u00b7 Seat #{spot_number} of 20 \u00b7 {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>
        </div>

        <!-- Applicant Details -->
        <div style="padding:24px 32px;">
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <tr style="border-bottom:1px solid #1e2532;">
              <td style="padding:10px 0;color:#64748b;font-weight:600;width:40%;">Full Name</td>
              <td style="padding:10px 0;color:#f1f5f9;font-weight:700;">{full_name}</td>
            </tr>
            <tr style="border-bottom:1px solid #1e2532;">
              <td style="padding:10px 0;color:#64748b;font-weight:600;">Email Address</td>
              <td style="padding:10px 0;color:#00f2fe;"><a href="mailto:{email}" style="color:#00f2fe;text-decoration:none;">{email}</a></td>
            </tr>
            <tr style="border-bottom:1px solid #1e2532;">
              <td style="padding:10px 0;color:#64748b;font-weight:600;">Primary Broker</td>
              <td style="padding:10px 0;color:#f1f5f9;">{broker_platform or '—'}</td>
            </tr>
            <tr style="border-bottom:1px solid #1e2532;">
              <td style="padding:10px 0;color:#64748b;font-weight:600;">Preferred Contact</td>
              <td style="padding:10px 0;color:#f1f5f9;">{contact_method or '—'}</td>
            </tr>
            <tr>
              <td style="padding:10px 0;color:#64748b;font-weight:600;vertical-align:top;">Why Interested</td>
              <td style="padding:10px 0;color:#f1f5f9;line-height:1.5;">{why_interested or '—'}</td>
            </tr>
          </table>
        </div>

        <!-- CTA -->
        <div style="padding:0 32px 28px;">
          <a href="https://ops.primeedge.app" style="display:inline-block;background:linear-gradient(135deg,#00f2fe,#38bdf8);color:#08090d;padding:12px 24px;border-radius:8px;font-weight:800;font-size:13px;text-decoration:none;">Open Founder Dashboard \u2192</a>
        </div>

        <!-- Footer -->
        <div style="background:#0c0e14;border-top:1px solid #1e2532;padding:16px 32px;font-size:11px;color:#64748b;">
          This is an automated notification from PrimeEdge Founder Operations. Reply directly to the applicant's email to respond.
        </div>
      </div>
    </body>
    </html>
    """

    cfg = _get_smtp_config()
    return _send_email(cfg["admin_notify"], subject, html_body)


def send_applicant_invite_email(
    full_name: str,
    email: str,
    invite_token: str,
    spot_number: int,
) -> bool:
    """Send an institutional invitation email with a secure link to activate their account."""
    activation_url = f"https://primeedge.app/activate?token={invite_token}"
    first_name = full_name.split()[0] if full_name else "Trader"
    subject = f"Your PrimeEdge Founder Alpha Access — Seat #{spot_number} Reserved"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <title>PrimeEdge Founder Alpha Invitation</title>
    </head>
    <body style="margin:0;padding:0;background:#08090d;font-family:Outfit,-apple-system,BlinkMacSystemFont,Arial,sans-serif;color:#f1f5f9;">
      <div style="max-width:600px;margin:36px auto;background:#111318;border:1px solid #242936;border-radius:14px;overflow:hidden;box-shadow:0 20px 40px rgba(0,0,0,0.6);">

        <!-- Header -->
        <div style="background:linear-gradient(135deg,#0d1520,#111827);border-bottom:1px solid #242936;padding:28px 32px;">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
            <div style="width:34px;height:34px;background:linear-gradient(135deg,#00f2fe,#38bdf8);border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:17px;color:#08090d;">P</div>
            <span style="font-size:20px;font-weight:800;color:#fff;letter-spacing:-0.4px;">PrimeEdge</span>
          </div>
          <div style="color:#00f2fe;font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:700;">Founder Alpha Cohort · Verified Allocation</div>
        </div>

        <!-- Welcome Banner -->
        <div style="background:rgba(0,242,254,0.06);border-left:4px solid #00f2fe;padding:20px 32px;">
          <div style="font-size:16px;font-weight:800;color:#fff;">Welcome to the Private Alpha, {first_name}.</div>
          <div style="font-size:13px;color:#94a3b8;margin-top:4px;">Your application has been accepted. Seat #{spot_number} of 20 is secured for your account.</div>
        </div>

        <!-- Body Content -->
        <div style="padding:28px 32px;font-size:14px;line-height:1.7;color:#cbd5e1;">
          <p style="margin-top:0;">
            You now have access to PrimeEdge — our proprietary decision intelligence platform with institutional Opportunity Radar scanning, empirical P90 invalidation boundaries, and isolated MT5 process guardrails.
          </p>
          <p>
            Please use the secure invitation link below to set your account password and activate your personal trading terminal:
          </p>

          <!-- Action Button -->
          <div style="text-align:center;margin:32px 0;">
            <a href="{activation_url}" style="display:inline-block;background:linear-gradient(135deg,#00f2fe,#38bdf8);color:#08090d;padding:14px 34px;border-radius:10px;font-weight:800;font-size:14px;text-decoration:none;box-shadow:0 4px 20px rgba(0,242,254,0.35);">
              Create Your Password &amp; Enter Workspace &rarr;
            </a>
          </div>

          <!-- Important Note -->
          <div style="background:rgba(255,255,255,0.03);border:1px solid #1e2532;border-radius:8px;padding:14px 18px;font-size:12px;color:#94a3b8;">
            <strong style="color:#f1f5f9;">Security Note:</strong> This invitation link is unique to <strong>{email}</strong> and expires in 7 days. Do not forward or share this link.
          </div>
        </div>

        <!-- Direct URL fallback -->
        <div style="padding:0 32px 24px;font-size:11px;color:#64748b;word-break:break-all;">
          If the button above does not work, copy and paste this URL into your browser:<br />
          <a href="{activation_url}" style="color:#00f2fe;text-decoration:none;">{activation_url}</a>
        </div>

        <!-- Footer -->
        <div style="background:#0c0e14;border-top:1px solid #1e2532;padding:18px 32px;font-size:11px;color:#64748b;display:flex;justify-content:space-between;align-items:center;">
          <div>PrimeEdge Institutional Decision Systems</div>
          <div>support@primeedge.app</div>
        </div>

      </div>
    </body>
    </html>
    """

    return _send_email(email, subject, html_body)

def send_password_reset_email(email: str, reset_token: str, full_name: str = "") -> bool:
    """Send a branded password-reset email with a secure one-hour link."""
    reset_url = f"https://primeedge.app/reset-password?token={reset_token}"
    first_name = (full_name.split()[0] if full_name else "") or "Trader"
    subject = "Reset Your PrimeEdge Password"

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>PrimeEdge â€” Password Reset</title>
</head>
<body style="margin:0;padding:0;background:#08090d;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;color:#f1f5f9;">
  <div style="max-width:580px;margin:36px auto;background:#111318;border:1px solid #242936;border-radius:14px;overflow:hidden;box-shadow:0 20px 40px rgba(0,0,0,.6);">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#0d1520,#111827);border-bottom:1px solid #242936;padding:28px 32px;">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
        <div style="width:34px;height:34px;background:linear-gradient(135deg,#00f2fe,#38bdf8);border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:17px;color:#08090d;">P</div>
        <span style="font-size:20px;font-weight:800;color:#fff;letter-spacing:-.4px;">PrimeEdge</span>
      </div>
      <div style="color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.8px;">Institutional Decision Intelligence Platform</div>
    </div>

    <!-- Banner -->
    <div style="background:rgba(0,242,254,.06);border-left:4px solid #00f2fe;padding:20px 32px;">
      <div style="font-size:15px;font-weight:800;color:#fff;">Password Reset Requested</div>
      <div style="font-size:13px;color:#94a3b8;margin-top:3px;">Hi {first_name} â€” we received a request to reset your password.</div>
    </div>

    <!-- Body -->
    <div style="padding:28px 32px;font-size:14px;line-height:1.7;color:#cbd5e1;">
      <p style="margin-top:0;">
        Click the button below to set a new password. This link is valid for <strong style="color:#f1f5f9;">1 hour</strong> and can only be used once.
      </p>

      <!-- CTA Button -->
      <div style="text-align:center;margin:32px 0;">
        <a href="{reset_url}"
           style="display:inline-block;background:linear-gradient(135deg,#00f2fe,#38bdf8);color:#08090d;padding:14px 36px;border-radius:10px;font-weight:800;font-size:14px;text-decoration:none;box-shadow:0 4px 20px rgba(0,242,254,.35);">
          Reset My Password &rarr;
        </a>
      </div>

      <!-- Security note -->
      <div style="background:rgba(255,255,255,.03);border:1px solid #1e2532;border-radius:8px;padding:14px 18px;font-size:12px;color:#94a3b8;">
        <strong style="color:#f1f5f9;">Didn't request this?</strong>
        You can safely ignore this email â€” your password will not change unless you click the link above.
      </div>
    </div>

    <!-- URL fallback -->
    <div style="padding:0 32px 24px;font-size:11px;color:#64748b;word-break:break-all;">
      If the button doesn't work, copy and paste this URL into your browser:<br/>
      <a href="{reset_url}" style="color:#00f2fe;text-decoration:none;">{reset_url}</a>
    </div>

    <!-- Footer -->
    <div style="background:#0c0e14;border-top:1px solid #1e2532;padding:16px 32px;font-size:11px;color:#64748b;display:flex;justify-content:space-between;align-items:center;">
      <span>PrimeEdge Institutional Decision Systems</span>
      <span>support@primeedge.app</span>
    </div>
  </div>
</body>
</html>"""

    return _send_email(email, subject, html_body)

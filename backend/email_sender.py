"""
email_sender.py — Send PDF report to prospect via email.
Supports Resend (preferred) and SMTP fallback.
"""

import os
import smtplib
import logging
import base64
import os
from dotenv import load_dotenv

load_dotenv()
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)


def _html_template(lead: dict, enriched: dict) -> str:
    company = enriched.get("company_name", lead["company"])
    tagline = enriched.get("tagline", "")
    solutions = enriched.get("recommended_ai_solutions", [])[:3]
    sol_items = "".join(
        f'<li style="margin-bottom:8px;"><strong style="color:#1E6FFF;">{s.get("title","")}</strong>'
        f' — {s.get("rationale","")}</li>'
        for s in solutions
    )

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0A0E1A;font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0A0E1A;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#131929;border-radius:12px;overflow:hidden;border:1px solid #3A4255;">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0F1724 0%,#1A2A50 100%);padding:36px 40px;border-bottom:3px solid #1E6FFF;">
            <p style="margin:0 0 8px 0;color:#00C9FF;font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:700;">SimplifIQ™ Intelligence</p>
            <h1 style="margin:0 0 6px 0;color:#FFFFFF;font-size:26px;font-weight:800;">{company}</h1>
            <p style="margin:0;color:#8892A4;font-size:13px;">{tagline}</p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:36px 40px;">
            <p style="color:#E8EDF5;font-size:15px;margin:0 0 20px 0;">Hi <strong>{lead["name"]}</strong>,</p>
            <p style="color:#8892A4;font-size:14px;line-height:1.7;margin:0 0 24px 0;">
              Thank you for your interest in SimplifIQ. We've completed a personalised business intelligence 
              analysis of <strong style="color:#E8EDF5;">{company}</strong> and your audit report is attached.
            </p>

            <!-- Highlights box -->
            <div style="background:#1A2035;border-radius:8px;border:1px solid #3A4255;padding:24px;margin-bottom:28px;">
              <p style="color:#00C9FF;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;font-weight:700;margin:0 0 16px 0;">What's Inside Your Report</p>
              <ul style="color:#E8EDF5;font-size:13px;line-height:1.8;padding-left:20px;margin:0;">
                <li>Executive intelligence summary</li>
                <li>Company profile & market positioning</li>
                <li>Digital maturity & AI readiness assessment</li>
                <li>Tailored AI solution recommendations</li>
                <li>Identified growth opportunities</li>
              </ul>
            </div>

            <!-- Recommended solutions -->
            {"<div style='background:#0D2040;border-radius:8px;border:1px solid #1E6FFF;padding:24px;margin-bottom:28px;'><p style='color:#1E6FFF;font-size:11px;letter-spacing:1.5px;text-transform:uppercase;font-weight:700;margin:0 0 16px 0;'>Top AI Recommendations For You</p><ul style='color:#E8EDF5;font-size:13px;line-height:1.8;padding-left:20px;margin:0;'>" + sol_items + "</ul></div>" if solutions else ""}

            <!-- CTA -->
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr><td align="center" style="padding:20px 0;">
                <a href="mailto:hello@simplifiq.ai?subject=Discovery Call — {company}"
                   style="background:#1E6FFF;color:#FFFFFF;text-decoration:none;padding:14px 36px;border-radius:6px;font-size:14px;font-weight:700;display:inline-block;letter-spacing:0.5px;">
                  Schedule a Free Discovery Call →
                </a>
              </td></tr>
            </table>

            <p style="color:#8892A4;font-size:13px;line-height:1.7;margin:0;">
              We look forward to exploring these opportunities with you.
            </p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#0A0E1A;padding:24px 40px;border-top:1px solid #3A4255;text-align:center;">
            <p style="color:#8892A4;font-size:11px;margin:0 0 4px 0;"><strong style="color:#00C9FF;">SimplifIQ™</strong> — AI-Powered Business Intelligence</p>
            <p style="color:#3A4255;font-size:10px;margin:0;">This report is confidential and prepared exclusively for {lead["name"]}.</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def send_via_resend(lead: dict, pdf_path: str, enriched: dict) -> bool:
    """Send using Resend API."""
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        return False
    try:
        import requests
        with open(pdf_path, "rb") as f:
            pdf_b64 = base64.b64encode(f.read()).decode()

        import os as _os
        fname = _os.path.basename(pdf_path)
        company = enriched.get("company_name", lead["company"])
        from_email = os.environ.get("FROM_EMAIL", "reports@simplifiq.ai")

        payload = {
            "from": f"SimplifIQ Intelligence <{from_email}>",
            "to": [lead["email"]],
            "subject": f"Your {company} Business Intelligence Report — SimplifIQ",
            "html": _html_template(lead, enriched),
            "attachments": [{"filename": fname, "content": pdf_b64}],
        }
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload, timeout=15
        )
        if r.status_code in (200, 201):
            logger.info(f"Email sent via Resend to {lead['email']}")
            return True
        else:
            logger.error(f"Resend error {r.status_code}: {r.text}")
    except Exception as e:
        logger.error(f"Resend failed: {e}")
    return False


def send_via_smtp(lead: dict, pdf_path: str, enriched: dict) -> bool:
    """Send using SMTP (Gmail / any SMTP)."""
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    from_email = os.environ.get("FROM_EMAIL", smtp_user)

    if not (smtp_user and smtp_pass):
        return False

    try:
        company = enriched.get("company_name", lead["company"])
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your {company} Intelligence Report — SimplifIQ"
        msg["From"] = f"SimplifIQ Intelligence <{from_email}>"
        msg["To"] = lead["email"]

        msg.attach(MIMEText(_html_template(lead, enriched), "html"))

        with open(pdf_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        import os as _os
        part.add_header("Content-Disposition", f'attachment; filename="{_os.path.basename(pdf_path)}"')
        msg.attach(part)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, lead["email"], msg.as_string())

        logger.info(f"Email sent via SMTP to {lead['email']}")
        return True
    except Exception as e:
        logger.error(f"SMTP failed: {e}")
        return False


def send_report_email(lead: dict, pdf_path: str, enriched: dict) -> bool:
    """Try Resend first, then SMTP."""
    if send_via_resend(lead, pdf_path, enriched):
        return True
    if send_via_smtp(lead, pdf_path, enriched):
        return True
    logger.warning("All email methods failed — report generated but not emailed.")
    return False

print(os.getenv("RESEND_API_KEY"))
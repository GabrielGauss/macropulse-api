"""
Transactional email service for MacroPulse.

Handles user-facing emails (welcome + API key delivery).
Uses the same SMTP transport as the alerting service but sends
to the individual user, not the operator alert recipients.

If SMTP is not configured the email is silently skipped and
the registration still succeeds — key is always returned in the
HTTP response as the primary delivery channel.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.settings import get_settings

logger = logging.getLogger(__name__)


def _send(to: str, subject: str, html: str, text: str) -> None:
    """Send a single email to `to`. Swallows all exceptions — never blocks registration."""
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_user:
        logger.debug("SMTP not configured; skipping transactional email to %s", to)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"MacroPulse <{settings.smtp_user}>"
    msg["To"]      = to
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, [to], msg.as_string())
        logger.info("Welcome email sent to %s", to)
    except Exception:
        logger.error("Failed to send welcome email to %s", to, exc_info=True)


def send_welcome_email(to: str, api_key: str, tier: str = "free") -> None:
    """
    Send the post-registration welcome email containing the user's API key.

    Called immediately after account creation.  Fire-and-forget — exceptions
    are caught internally so registration always succeeds.
    """
    tier_label   = tier.capitalize()
    daily_limits = {"free": "50 requests/day", "starter": "500 requests/day", "pro": "Unlimited"}
    limit_str    = daily_limits.get(tier, "50 requests/day")

    subject = "Your MacroPulse API key"

    # ── Plain text fallback ──────────────────────────────────────────
    text = f"""Welcome to MacroPulse.

Your API key ({tier_label} tier · {limit_str}):

  {api_key}

This key is shown once only. Store it securely.

Quick start:
  curl -H "X-MacroPulse-Key: {api_key}" https://api.macropulse.live/v1/signals/latest

Dashboard:  https://api.macropulse.live/dashboard
API docs:   https://api.macropulse.live/docs

Questions? support@macropulse.live
"""

    # ── HTML email ───────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Your MacroPulse API key</title>
</head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Inter',Arial,sans-serif;color:#f0f0f0;">

  <!-- wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:48px 16px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

        <!-- logo row -->
        <tr>
          <td style="padding-bottom:32px;">
            <table cellpadding="0" cellspacing="0">
              <tr>
                <td style="width:8px;height:8px;border-radius:50%;background:#22c55e;vertical-align:middle;"></td>
                <td style="padding-left:8px;font-size:15px;font-weight:600;letter-spacing:-0.02em;vertical-align:middle;">MacroPulse</td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- headline -->
        <tr>
          <td style="padding-bottom:8px;">
            <h1 style="margin:0;font-size:28px;font-weight:700;letter-spacing:-0.03em;line-height:1.2;">Your API key is ready.</h1>
          </td>
        </tr>
        <tr>
          <td style="padding-bottom:32px;">
            <p style="margin:0;font-size:15px;color:#888;line-height:1.6;">
              {tier_label} tier &middot; {limit_str}
            </p>
          </td>
        </tr>

        <!-- key box -->
        <tr>
          <td style="padding-bottom:8px;">
            <p style="margin:0 0 10px 0;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#555;">Your API Key</p>
            <div style="background:#111;border:1px solid #1f1f1f;border-radius:8px;padding:16px 20px;">
              <code style="font-family:'JetBrains Mono','Courier New',monospace;font-size:13px;color:#22c55e;word-break:break-all;letter-spacing:0.02em;">{api_key}</code>
            </div>
          </td>
        </tr>
        <tr>
          <td style="padding-bottom:32px;">
            <p style="margin:6px 0 0 0;font-size:12px;color:#555;">
              This key is shown <strong style="color:#888;">once only</strong>. Store it somewhere safe — rotate via the API if lost.
            </p>
          </td>
        </tr>

        <!-- divider -->
        <tr><td style="height:1px;background:#1f1f1f;padding:0;margin-bottom:32px;"></td></tr>

        <!-- usage -->
        <tr>
          <td style="padding-top:32px;padding-bottom:32px;">
            <p style="margin:0 0 16px 0;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#555;">Quick Start</p>

            <!-- step 1 -->
            <table cellpadding="0" cellspacing="0" style="margin-bottom:16px;width:100%;">
              <tr>
                <td style="width:28px;vertical-align:top;font-family:'JetBrains Mono','Courier New',monospace;font-size:11px;color:#444;padding-top:2px;">01</td>
                <td>
                  <p style="margin:0 0 4px 0;font-size:13px;font-weight:600;color:#f0f0f0;">Make your first call</p>
                  <div style="background:#111;border:1px solid #1f1f1f;border-radius:6px;padding:10px 14px;margin-top:6px;">
                    <code style="font-family:'JetBrains Mono','Courier New',monospace;font-size:11px;color:#888;">curl -H <span style="color:#22c55e;">"X-MacroPulse-Key: {api_key[:20]}..."</span> \\<br>&nbsp;&nbsp;https://api.macropulse.live/v1/signals/latest</code>
                  </div>
                </td>
              </tr>
            </table>

            <!-- step 2 -->
            <table cellpadding="0" cellspacing="0" style="margin-bottom:16px;width:100%;">
              <tr>
                <td style="width:28px;vertical-align:top;font-family:'JetBrains Mono','Courier New',monospace;font-size:11px;color:#444;padding-top:2px;">02</td>
                <td>
                  <p style="margin:0 0 4px 0;font-size:13px;font-weight:600;color:#f0f0f0;">Open the live dashboard</p>
                  <p style="margin:4px 0 0 0;font-size:12px;color:#666;">Real-time regime signals, liquidity gauges, and the macro heatmap.</p>
                </td>
              </tr>
            </table>

            <!-- step 3 -->
            <table cellpadding="0" cellspacing="0" style="width:100%;">
              <tr>
                <td style="width:28px;vertical-align:top;font-family:'JetBrains Mono','Courier New',monospace;font-size:11px;color:#444;padding-top:2px;">03</td>
                <td>
                  <p style="margin:0 0 4px 0;font-size:13px;font-weight:600;color:#f0f0f0;">Browse the API docs</p>
                  <p style="margin:4px 0 0 0;font-size:12px;color:#666;">Full reference at <code style="font-family:monospace;color:#888;">api.macropulse.live/docs</code></p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- divider -->
        <tr><td style="height:1px;background:#1f1f1f;padding:0;"></td></tr>

        <!-- CTA -->
        <tr>
          <td style="padding-top:32px;padding-bottom:32px;">
            <a href="https://api.macropulse.live/dashboard"
               style="display:inline-block;background:#f0f0f0;color:#0a0a0a;font-size:13px;font-weight:600;padding:10px 24px;border-radius:7px;text-decoration:none;">
              Open Dashboard &rarr;
            </a>
            &nbsp;
            <a href="https://api.macropulse.live/docs"
               style="display:inline-block;background:transparent;color:#666;font-size:13px;font-weight:500;padding:10px 24px;border-radius:7px;text-decoration:none;border:1px solid #2a2a2a;">
              API Docs
            </a>
          </td>
        </tr>

        <!-- footer -->
        <tr>
          <td style="padding-top:16px;border-top:1px solid #1a1a1a;">
            <p style="margin:0;font-size:11px;color:#444;line-height:1.8;">
              MacroPulse · Probabilistic macro regime intelligence<br>
              Questions? <a href="mailto:support@macropulse.live" style="color:#555;text-decoration:none;">support@macropulse.live</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>"""

    _send(to=to, subject=subject, html=html, text=text)

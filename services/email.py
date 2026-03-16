"""
Transactional email via Brevo (formerly Sendinblue) HTTP API.

Sends welcome + API key delivery emails to new users.
Falls back silently if the API key is not configured — registration
always succeeds and the key is returned in the HTTP response.
"""

from __future__ import annotations

import json
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError

from config.settings import get_settings

logger = logging.getLogger(__name__)

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"
SENDER = {"name": "MacroPulse", "email": "noreply@macropulse.live"}


def _post(payload: dict) -> None:
    """POST to Brevo API. Swallows all exceptions."""
    settings = get_settings()
    if not settings.brevo_api_key:
        logger.debug("BREVO_API_KEY not set; skipping transactional email.")
        return

    data = json.dumps(payload).encode()
    req = Request(
        BREVO_SEND_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept":        "application/json",
            "api-key":       settings.brevo_api_key,
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            logger.info("Brevo email sent (status %d)", resp.status)
    except URLError as exc:
        logger.error("Brevo email failed: %s", exc)
    except Exception:
        logger.error("Brevo email unexpected error", exc_info=True)


def send_welcome_email(to: str, api_key: str, tier: str = "free") -> None:
    """
    Send post-registration welcome email with the user's API key.
    Fire-and-forget — never blocks or raises.
    """
    tier_label   = tier.capitalize()
    daily_limits = {"free": "50 req/day", "starter": "500 req/day", "pro": "Unlimited"}
    limit_str    = daily_limits.get(tier, "50 req/day")

    text_content = f"""Welcome to MacroPulse.

Your API key ({tier_label} · {limit_str}):

  {api_key}

This key is shown once. Store it securely.

Quick start:
  curl -H "X-MacroPulse-Key: {api_key}" https://api.macropulse.live/v1/signals/latest

Dashboard:  https://api.macropulse.live/dashboard
API docs:   https://api.macropulse.live/docs

Questions? support@macropulse.live
"""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Inter',Arial,sans-serif;color:#f0f0f0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:48px 16px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

  <!-- logo -->
  <tr><td style="padding-bottom:32px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="width:8px;height:8px;border-radius:50%;background:#22c55e;vertical-align:middle;"></td>
      <td style="padding-left:8px;font-size:15px;font-weight:600;letter-spacing:-0.02em;vertical-align:middle;">MacroPulse</td>
    </tr></table>
  </td></tr>

  <!-- headline -->
  <tr><td style="padding-bottom:6px;">
    <h1 style="margin:0;font-size:26px;font-weight:700;letter-spacing:-0.03em;line-height:1.2;">Your API key is ready.</h1>
  </td></tr>
  <tr><td style="padding-bottom:28px;">
    <p style="margin:0;font-size:14px;color:#888;">{tier_label} &middot; {limit_str}</p>
  </td></tr>

  <!-- key box -->
  <tr><td style="padding-bottom:6px;">
    <p style="margin:0 0 8px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#555;">Your API Key</p>
    <div style="background:#111;border:1px solid #1f1f1f;border-radius:8px;padding:16px 20px;">
      <code style="font-family:'Courier New',monospace;font-size:13px;color:#22c55e;word-break:break-all;">{api_key}</code>
    </div>
  </td></tr>
  <tr><td style="padding-bottom:28px;">
    <p style="margin:6px 0 0;font-size:11px;color:#555;">Shown <strong style="color:#888;">once only</strong> — store it securely. Rotate via <code style="font-family:monospace;color:#666;">POST /v1/auth/rotate</code> if lost.</p>
  </td></tr>

  <tr><td style="height:1px;background:#1f1f1f;"></td></tr>

  <!-- steps -->
  <tr><td style="padding:28px 0;">
    <p style="margin:0 0 16px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#555;">Quick Start</p>

    <table cellpadding="0" cellspacing="0" style="margin-bottom:14px;width:100%;"><tr>
      <td style="width:24px;vertical-align:top;font-family:monospace;font-size:10px;color:#444;padding-top:2px;">01</td>
      <td>
        <p style="margin:0 0 6px;font-size:13px;font-weight:600;">Fetch current signals</p>
        <div style="background:#111;border:1px solid #1f1f1f;border-radius:6px;padding:10px 14px;">
          <code style="font-family:monospace;font-size:11px;color:#888;">curl -H <span style="color:#22c55e;">"X-MacroPulse-Key: {api_key[:20]}..."</span><br>&nbsp;&nbsp;https://api.macropulse.live/v1/signals/latest</code>
        </div>
      </td>
    </tr></table>

    <table cellpadding="0" cellspacing="0" style="margin-bottom:14px;width:100%;"><tr>
      <td style="width:24px;vertical-align:top;font-family:monospace;font-size:10px;color:#444;padding-top:2px;">02</td>
      <td>
        <p style="margin:0 0 4px;font-size:13px;font-weight:600;">Open the dashboard</p>
        <p style="margin:0;font-size:12px;color:#666;">Live regime signals, liquidity gauges, macro heatmap.</p>
      </td>
    </tr></table>

    <table cellpadding="0" cellspacing="0" style="width:100%;"><tr>
      <td style="width:24px;vertical-align:top;font-family:monospace;font-size:10px;color:#444;padding-top:2px;">03</td>
      <td>
        <p style="margin:0 0 4px;font-size:13px;font-weight:600;">Read the API docs</p>
        <p style="margin:0;font-size:12px;color:#666;"><code style="font-family:monospace;color:#888;">api.macropulse.live/docs</code> — full reference with examples.</p>
      </td>
    </tr></table>
  </td></tr>

  <tr><td style="height:1px;background:#1f1f1f;"></td></tr>

  <!-- CTA -->
  <tr><td style="padding:28px 0;">
    <a href="https://api.macropulse.live/dashboard"
       style="display:inline-block;background:#f0f0f0;color:#0a0a0a;font-size:13px;font-weight:600;padding:10px 22px;border-radius:7px;text-decoration:none;">
      Open Dashboard &rarr;
    </a>
    &nbsp;
    <a href="https://api.macropulse.live/docs"
       style="display:inline-block;background:transparent;color:#666;font-size:13px;font-weight:500;padding:10px 22px;border-radius:7px;text-decoration:none;border:1px solid #2a2a2a;">
      API Docs
    </a>
  </td></tr>

  <!-- footer -->
  <tr><td style="padding-top:16px;border-top:1px solid #1a1a1a;">
    <p style="margin:0;font-size:11px;color:#444;line-height:1.8;">
      MacroPulse &middot; Probabilistic macro regime intelligence<br>
      <a href="mailto:support@macropulse.live" style="color:#555;text-decoration:none;">support@macropulse.live</a>
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    _post({
        "sender":      SENDER,
        "to":          [{"email": to}],
        "subject":     "Your MacroPulse API key",
        "htmlContent": html_content,
        "textContent": text_content,
    })

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


def _get_sender() -> dict:
    """Return sender dict, using BREVO_SENDER_EMAIL env override if set."""
    settings = get_settings()
    email = getattr(settings, "brevo_sender_email", "") or "noreply@macropulse.live"
    return {"name": "MacroPulse", "email": email}


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


def send_email(to: str, subject: str, html: str) -> None:
    """
    Generic transactional email helper.
    Used by the alert system for regime change notifications.
    Fire-and-forget — never blocks or raises.
    """
    _post({
        "sender":      _get_sender(),
        "to":          [{"email": to}],
        "subject":     subject,
        "htmlContent": html,
    })


def send_newsletter_confirmation(to: str) -> None:
    """
    Send newsletter subscription confirmation email.
    Fire-and-forget — never blocks or raises.
    """
    text_content = """Welcome to the MacroPulse Weekly Brief.

Every Monday you'll receive the current macro regime classification,
liquidity state, and key signals — no API key needed.

macropulse.live
"""

    html_content = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Inter',Arial,sans-serif;color:#f0f0f0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:48px 16px;">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="max-width:480px;width:100%;">

  <tr><td style="padding-bottom:32px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="width:8px;height:8px;border-radius:50%;background:#22c55e;vertical-align:middle;"></td>
      <td style="padding-left:8px;font-size:15px;font-weight:600;letter-spacing:-0.02em;vertical-align:middle;">MacroPulse</td>
    </tr></table>
  </td></tr>

  <tr><td style="padding-bottom:20px;">
    <h1 style="margin:0;font-size:22px;font-weight:700;letter-spacing:-0.03em;">You're in.</h1>
    <p style="margin:10px 0 0;font-size:13px;color:#888;line-height:1.7;">
      Every Monday you'll receive the current macro regime classification,
      liquidity state, and key signals — no API key needed.
    </p>
  </td></tr>

  <tr><td style="padding-bottom:24px;">
    <div style="background:#111;border:1px solid #1f1f1f;border-radius:10px;padding:20px 24px;">
      <p style="margin:0 0 10px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#555;">What you'll get</p>
      <p style="margin:0 0 8px;font-size:13px;color:#aaa;">&#x2713; &nbsp;Regime classification (Expansion / Tightening / Recovery / Risk-Off)</p>
      <p style="margin:0 0 8px;font-size:13px;color:#aaa;">&#x2713; &nbsp;Net liquidity state + trend</p>
      <p style="margin:0;font-size:13px;color:#aaa;">&#x2713; &nbsp;Key macro signals to watch</p>
    </div>
  </td></tr>

  <tr><td style="padding-bottom:24px;">
    <a href="https://macropulse.live"
       style="display:inline-block;background:#f0f0f0;color:#0a0a0a;font-size:13px;font-weight:600;padding:10px 22px;border-radius:7px;text-decoration:none;">
      View Live Dashboard &rarr;
    </a>
  </td></tr>

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
        "sender":      _get_sender(),
        "to":          [{"email": to}],
        "subject":     "You're in — MacroPulse Weekly Brief",
        "htmlContent": html_content,
        "textContent": text_content,
    })


def send_verification_email(to: str, code: str) -> None:
    """
    Send a 6-digit email verification code to the registrant.
    Fire-and-forget — never blocks or raises.
    """
    text_content = f"""MacroPulse — verify your email

Your verification code:  {code}

This code expires in 15 minutes.

If you didn't request this, ignore this email.
"""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Inter',Arial,sans-serif;color:#f0f0f0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:48px 16px;">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="max-width:480px;width:100%;">

  <!-- logo -->
  <tr><td style="padding-bottom:32px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="width:8px;height:8px;border-radius:50%;background:#22c55e;vertical-align:middle;"></td>
      <td style="padding-left:8px;font-size:15px;font-weight:600;letter-spacing:-0.02em;vertical-align:middle;">MacroPulse</td>
    </tr></table>
  </td></tr>

  <!-- headline -->
  <tr><td style="padding-bottom:24px;">
    <h1 style="margin:0;font-size:22px;font-weight:700;letter-spacing:-0.03em;">Verify your email</h1>
    <p style="margin:8px 0 0;font-size:13px;color:#888;">Enter this code on the MacroPulse site to receive your API key.</p>
  </td></tr>

  <!-- code box -->
  <tr><td style="padding-bottom:28px;">
    <div style="background:#111;border:1px solid #1f1f1f;border-radius:12px;padding:28px;text-align:center;">
      <p style="margin:0 0 8px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.12em;color:#555;">Verification Code</p>
      <code style="font-family:'Courier New',monospace;font-size:36px;font-weight:700;letter-spacing:0.3em;color:#22c55e;">{code}</code>
    </div>
  </td></tr>

  <tr><td style="padding-bottom:24px;">
    <p style="margin:0;font-size:12px;color:#555;line-height:1.7;">
      This code expires in <strong style="color:#888;">15 minutes</strong>.<br>
      If you didn't request this, you can safely ignore this email.
    </p>
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
        "sender":      _get_sender(),
        "to":          [{"email": to}],
        "subject":     f"MacroPulse verification code: {code}",
        "htmlContent": html_content,
        "textContent": text_content,
    })


def send_key_recovery_email(to: str, api_key: str, tier: str = "free") -> None:
    """
    Send key recovery email with the new API key after a successful recovery.
    The old key has already been revoked. Fire-and-forget — never blocks or raises.
    """
    tier_label   = tier.capitalize()
    daily_limits = {"free": "50 req/day", "starter": "500 req/day", "pro": "Unlimited"}
    limit_str    = daily_limits.get(tier, "50 req/day")

    text_content = f"""MacroPulse — your new API key.

Your previous key has been revoked. Your new key ({tier_label} · {limit_str}):

  {api_key}

This key is shown once. Store it securely.

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

  <tr><td style="padding-bottom:32px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="width:8px;height:8px;border-radius:50%;background:#22c55e;vertical-align:middle;"></td>
      <td style="padding-left:8px;font-size:15px;font-weight:600;letter-spacing:-0.02em;vertical-align:middle;">MacroPulse</td>
    </tr></table>
  </td></tr>

  <tr><td style="padding-bottom:6px;">
    <h1 style="margin:0;font-size:26px;font-weight:700;letter-spacing:-0.03em;line-height:1.2;">Key recovered.</h1>
  </td></tr>
  <tr><td style="padding-bottom:28px;">
    <p style="margin:0;font-size:14px;color:#888;">{tier_label} &middot; {limit_str} &middot; Previous key revoked.</p>
  </td></tr>

  <tr><td style="padding-bottom:6px;">
    <p style="margin:0 0 8px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#555;">Your New API Key</p>
    <div style="background:#111;border:1px solid #1f1f1f;border-radius:8px;padding:16px 20px;">
      <code style="font-family:'Courier New',monospace;font-size:13px;color:#22c55e;word-break:break-all;">{api_key}</code>
    </div>
  </td></tr>
  <tr><td style="padding-bottom:28px;">
    <p style="margin:6px 0 0;font-size:11px;color:#555;">Shown <strong style="color:#888;">once only</strong> — store it securely.</p>
  </td></tr>

  <tr><td style="height:1px;background:#1f1f1f;"></td></tr>

  <tr><td style="padding:28px 0;">
    <a href="https://api.macropulse.live/dashboard"
       style="display:inline-block;background:#f0f0f0;color:#0a0a0a;font-size:13px;font-weight:600;padding:10px 22px;border-radius:7px;text-decoration:none;">
      Open Dashboard &rarr;
    </a>
  </td></tr>

  <tr><td style="padding-top:16px;border-top:1px solid #1a1a1a;">
    <p style="margin:0;font-size:11px;color:#444;line-height:1.8;">
      If you didn't request this recovery, contact us immediately.<br>
      MacroPulse &middot; <a href="mailto:support@macropulse.live" style="color:#555;text-decoration:none;">support@macropulse.live</a>
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    _post({
        "sender":      _get_sender(),
        "to":          [{"email": to}],
        "subject":     "MacroPulse — your new API key",
        "htmlContent": html_content,
        "textContent": text_content,
    })


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
        "sender":      _get_sender(),
        "to":          [{"email": to}],
        "subject":     "Your MacroPulse API key",
        "htmlContent": html_content,
        "textContent": text_content,
    })


def send_irl_welcome_email(
    to: str,
    license_key: str,
    tier: str,
    agent_count: int = 1,
    is_upgrade: bool = False,
) -> None:
    """
    Send IRL Engine onboarding email after Stripe payment.
    Covers IRL Sidecar L1 and IRL Audit Platform L2.
    Fire-and-forget — never blocks or raises.
    """
    is_audit = tier == "irl_audit"
    tier_label = "IRL Audit Platform L2" if is_audit else "IRL Sidecar L1"
    tier_short = "L2" if is_audit else "L1"
    price_per = "$1,200" if is_audit else "$500"
    action_word = "Upgraded" if is_upgrade else "Welcome to"
    shown_once = "Shown once — store it securely." if not is_upgrade else "Use your existing license key."

    text_content = f"""{action_word} IRL Engine — {tier_label}

License key ({tier_short} · {agent_count} agent{'s' if agent_count != 1 else ''} · {price_per}/agent/mo):

  {license_key}

{shown_once}

Quick start:
  docker pull macropulse/irl-engine:{tier_short.lower()}
  IRL_LICENSE={license_key} IRL_AGENTS={agent_count} docker-compose up

SDK:
  pip install irl-sdk
  npm install irl-sdk

Onboarding guide:
  https://macropulse.live/irl-welcome.html

Whitepaper:
  https://macropulse.live/irl-whitepaper.html

Questions?  licensing@macropulse.live
"""

    key_display = license_key if not is_upgrade else f"{license_key} (unchanged)"
    agent_label = f"{agent_count} agent{'s' if agent_count != 1 else ''}"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Inter',Arial,sans-serif;color:#f0f0f0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:48px 16px;">
<tr><td align="center">
<table width="580" cellpadding="0" cellspacing="0" style="max-width:580px;width:100%;">

  <!-- logo -->
  <tr><td style="padding-bottom:32px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="width:8px;height:8px;border-radius:50%;background:#f59e0b;vertical-align:middle;"></td>
      <td style="padding-left:8px;font-size:15px;font-weight:600;letter-spacing:-0.02em;vertical-align:middle;">IRL Engine &middot; MacroPulse</td>
    </tr></table>
  </td></tr>

  <!-- badge -->
  <tr><td style="padding-bottom:20px;">
    <span style="font-family:'Courier New',monospace;font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;background:#1a1400;color:#f59e0b;border:1px solid #3a2800;padding:4px 10px;">{tier_short} · {tier_label.upper()}</span>
  </td></tr>

  <!-- headline -->
  <tr><td style="padding-bottom:6px;">
    <h1 style="margin:0;font-size:26px;font-weight:700;letter-spacing:-0.03em;line-height:1.2;">{"Your IRL license is active." if not is_upgrade else "IRL plan upgraded."}</h1>
  </td></tr>
  <tr><td style="padding-bottom:28px;">
    <p style="margin:0;font-size:14px;color:#888;">{tier_label} &middot; {agent_label} &middot; {price_per}/agent/mo</p>
  </td></tr>

  <!-- license key -->
  <tr><td style="padding-bottom:6px;">
    <p style="margin:0 0 8px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#555;">Your IRL License Key</p>
    <div style="background:#111;border:1px solid #3a2800;border-radius:8px;padding:16px 20px;">
      <code style="font-family:'Courier New',monospace;font-size:13px;color:#f59e0b;word-break:break-all;">{key_display}</code>
    </div>
  </td></tr>
  <tr><td style="padding-bottom:28px;">
    <p style="margin:6px 0 0;font-size:11px;color:#555;">{shown_once}</p>
  </td></tr>

  <!-- divider -->
  <tr><td style="height:1px;background:#1f1f1f;"></td></tr>

  <!-- quick start -->
  <tr><td style="padding:28px 0;">
    <p style="margin:0 0 16px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#555;">Deploy in 3 Steps</p>

    <table cellpadding="0" cellspacing="0" style="margin-bottom:14px;width:100%;"><tr>
      <td style="width:24px;vertical-align:top;font-family:monospace;font-size:10px;color:#444;padding-top:2px;">01</td>
      <td>
        <p style="margin:0 0 6px;font-size:13px;font-weight:600;">Pull the engine image</p>
        <div style="background:#111;border:1px solid #1f1f1f;border-radius:6px;padding:10px 14px;">
          <code style="font-family:monospace;font-size:11px;color:#888;">docker pull <span style="color:#f59e0b;">macropulse/irl-engine:{tier_short.lower()}</span></code>
        </div>
      </td>
    </tr></table>

    <table cellpadding="0" cellspacing="0" style="margin-bottom:14px;width:100%;"><tr>
      <td style="width:24px;vertical-align:top;font-family:monospace;font-size:10px;color:#444;padding-top:2px;">02</td>
      <td>
        <p style="margin:0 0 6px;font-size:13px;font-weight:600;">Set your environment</p>
        <div style="background:#111;border:1px solid #1f1f1f;border-radius:6px;padding:10px 14px;">
          <code style="font-family:monospace;font-size:11px;color:#888;">IRL_LICENSE=<span style="color:#f59e0b;">{license_key[:20]}...</span><br>IRL_AGENTS=<span style="color:#f59e0b;">{agent_count}</span><br>MTA_MODE=<span style="color:#f59e0b;">macropulse</span> &nbsp;<span style="color:#444;"># or 'custom' / 'none'</span></code>
        </div>
      </td>
    </tr></table>

    <table cellpadding="0" cellspacing="0" style="width:100%;"><tr>
      <td style="width:24px;vertical-align:top;font-family:monospace;font-size:10px;color:#444;padding-top:2px;">03</td>
      <td>
        <p style="margin:0 0 4px;font-size:13px;font-weight:600;">Run the sandbox</p>
        <p style="margin:0;font-size:12px;color:#666;">Open <code style="font-family:monospace;color:#888;">irl.macropulse.live/swagger-ui/</code> — three demo agents pre-seeded. Try <code style="font-family:monospace;color:#888;">POST /v1/authorize</code> and <code style="font-family:monospace;color:#888;">POST /v1/bind-execution</code> before deploying your own fleet.</p>
      </td>
    </tr></table>
  </td></tr>

  <tr><td style="height:1px;background:#1f1f1f;"></td></tr>

  <!-- SDK row -->
  <tr><td style="padding:20px 0;">
    <p style="margin:0 0 10px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#555;">SDK</p>
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="padding-right:16px;">
        <div style="background:#111;border:1px solid #1f1f1f;border-radius:6px;padding:8px 14px;">
          <code style="font-family:monospace;font-size:11px;color:#888;">pip install <span style="color:#f59e0b;">irl-sdk</span></code>
        </div>
      </td>
      <td>
        <div style="background:#111;border:1px solid #1f1f1f;border-radius:6px;padding:8px 14px;">
          <code style="font-family:monospace;font-size:11px;color:#888;">npm install <span style="color:#f59e0b;">irl-sdk</span></code>
        </div>
      </td>
    </tr></table>
  </td></tr>

  <tr><td style="height:1px;background:#1f1f1f;"></td></tr>

  <!-- CTA -->
  <tr><td style="padding:28px 0;">
    <a href="https://macropulse.live/irl-welcome.html"
       style="display:inline-block;background:#f59e0b;color:#000;font-size:13px;font-weight:700;padding:10px 22px;text-decoration:none;letter-spacing:0.01em;">
      Open Onboarding Guide &rarr;
    </a>
    &nbsp;
    <a href="https://macropulse.live/irl-whitepaper.html"
       style="display:inline-block;background:transparent;color:#666;font-size:13px;font-weight:500;padding:10px 22px;text-decoration:none;border:1px solid #2a2a2a;">
      Read Whitepaper
    </a>
  </td></tr>

  <!-- footer -->
  <tr><td style="padding-top:16px;border-top:1px solid #1a1a1a;">
    <p style="margin:0;font-size:11px;color:#444;line-height:1.8;">
      IRL Engine &middot; MacroPulse &middot; <a href="mailto:licensing@macropulse.live" style="color:#555;text-decoration:none;">licensing@macropulse.live</a>
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    _post({
        "sender":      _get_sender(),
        "to":          [{"email": to}],
        "subject":     f"IRL Engine {tier_short} — your license is active",
        "htmlContent": html_content,
        "textContent": text_content,
    })


def send_upgrade_email(to: str, tier: str, key_prefix: str) -> None:
    """
    Notify an existing user that their plan was upgraded after a successful payment.
    We only have the key prefix (not the plaintext key), so we link to the dashboard.
    Fire-and-forget — never blocks or raises.
    """
    tier_label   = tier.capitalize()
    daily_limits = {"starter": "500 req/day", "pro": "Unlimited"}
    limit_str    = daily_limits.get(tier, "increased")
    dashboard    = "https://api.macropulse.live/dashboard"

    text_content = f"""MacroPulse — plan upgraded.

Your account has been upgraded to {tier_label} ({limit_str}).
Your existing API key (prefix: {key_prefix}...) is unchanged and active immediately.

Dashboard: {dashboard}

Questions? support@macropulse.live
"""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Inter',Arial,sans-serif;color:#f0f0f0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:48px 16px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

  <tr><td style="padding-bottom:32px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="width:8px;height:8px;border-radius:50%;background:#22c55e;vertical-align:middle;"></td>
      <td style="padding-left:8px;font-size:15px;font-weight:600;letter-spacing:-0.02em;vertical-align:middle;">MacroPulse</td>
    </tr></table>
  </td></tr>

  <tr><td style="padding-bottom:6px;">
    <h1 style="margin:0;font-size:26px;font-weight:700;letter-spacing:-0.03em;line-height:1.2;">You&rsquo;re on {tier_label}.</h1>
  </td></tr>
  <tr><td style="padding-bottom:28px;">
    <p style="margin:0;font-size:14px;color:#888;">{tier_label} &middot; {limit_str} &middot; Active immediately.</p>
  </td></tr>

  <tr><td style="padding-bottom:24px;">
    <div style="background:#111;border:1px solid #1c2a1c;border-radius:8px;padding:16px 20px;">
      <p style="margin:0 0 6px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#555;">Your API Key</p>
      <p style="margin:0;font-size:13px;color:#888;">
        Your existing key <code style="font-family:monospace;color:#22c55e;">{key_prefix}...</code> is unchanged
        and active at your new plan limits right now.
      </p>
    </div>
  </td></tr>

  <tr><td style="height:1px;background:#1f1f1f;"></td></tr>

  <tr><td style="padding:28px 0;">
    <a href="{dashboard}"
       style="display:inline-block;background:#22c55e;color:#000;font-size:13px;font-weight:600;padding:10px 22px;border-radius:7px;text-decoration:none;">
      Open Dashboard &rarr;
    </a>
  </td></tr>

  <tr><td style="padding-top:16px;border-top:1px solid #1a1a1a;">
    <p style="margin:0;font-size:11px;color:#444;line-height:1.8;">
      To manage or cancel your subscription, reply to this email.<br>
      MacroPulse &middot; <a href="mailto:support@macropulse.live" style="color:#555;text-decoration:none;">support@macropulse.live</a>
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""

    _post({
        "sender":      _get_sender(),
        "to":          [{"email": to}],
        "subject":     f"You're on MacroPulse {tier_label}",
        "htmlContent": html_content,
        "textContent": text_content,
    })

"""
Regime change alert delivery.

Called by the daily pipeline when a regime transition is detected.
Sends email alerts to all Starter/Pro users and webhook POSTs to Pro users
who have configured a webhook_url.  Also posts to X and Discord.
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_REGIME_LABELS = {
    "expansion":  "Expansion",
    "recovery":   "Recovery",
    "tightening": "Tightening",
    "risk_off":   "Risk-Off",
}

_EXPOSURE = {
    "expansion":  "100%",
    "recovery":   "75%",
    "tightening": "25%",
    "risk_off":   "0%",
}

_REGIME_EMOJI = {
    "expansion":  "🟢",
    "recovery":   "🔵",
    "tightening": "🟡",
    "risk_off":   "🔴",
}

_REGIME_COLOR_HEX = {
    "expansion":  "#22c55e",
    "recovery":   "#3b82f6",
    "tightening": "#f59e0b",
    "risk_off":   "#ef4444",
}

_REGIME_BG = {
    "expansion":  "rgba(34,197,94,0.08)",
    "recovery":   "rgba(59,130,246,0.08)",
    "tightening": "rgba(245,158,11,0.08)",
    "risk_off":   "rgba(239,68,68,0.08)",
}

_WHAT_IT_MEANS = {
    "expansion": (
        "Fed liquidity is ample, credit spreads are tight, volatility is suppressed. "
        "This is the highest-return macro environment across asset classes — "
        "full equity exposure is warranted."
    ),
    "recovery": (
        "Liquidity is re-injecting after stress. Risk appetite is healing but not fully "
        "restored. Positive bias with elevated caution — 75% equity exposure."
    ),
    "tightening": (
        "The Fed is draining liquidity or hiking. Credit spreads are widening. "
        "Defensive positioning is appropriate — reduce duration and leveraged exposure. "
        "25% equity exposure."
    ),
    "risk_off": (
        "Acute stress or crisis conditions. Emergency liquidity injections, spiking spreads "
        "and volatility. Capital preservation is the only objective — 0% equity exposure."
    ),
}


async def send_regime_change_alerts(
    prev_regime: str,
    new_regime: str,
    risk_score: float,
    date: str,
) -> None:
    """
    Notify all eligible users of a regime change.

    Async — must be awaited. Calls the async get_alert_recipients() query
    and optionally posts to X and Discord for public visibility.
    """
    from database.queries import get_alert_recipients

    prev_label   = _REGIME_LABELS.get(prev_regime, prev_regime)
    new_label    = _REGIME_LABELS.get(new_regime, new_regime)
    new_exposure = _EXPOSURE.get(new_regime, "—")
    new_emoji    = _REGIME_EMOJI.get(new_regime, "⚪")
    prev_emoji   = _REGIME_EMOJI.get(prev_regime, "⚪")
    accent_color = _REGIME_COLOR_HEX.get(new_regime, "#22c55e")
    accent_bg    = _REGIME_BG.get(new_regime, "rgba(34,197,94,0.08)")
    what_it_means = _WHAT_IT_MEANS.get(new_regime, "")

    subject = f"{new_emoji} MacroPulse: Regime shift → {new_label}"

    body_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#080808;font-family:'Inter',system-ui,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#080808;padding:40px 0;">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

      <!-- Header -->
      <tr><td style="padding-bottom:28px;">
        <div style="font-size:11px;color:#555;letter-spacing:0.12em;text-transform:uppercase;font-family:'Courier New',monospace;">
          MacroPulse · Regime Alert · {date}
        </div>
      </td></tr>

      <!-- Shift card -->
      <tr><td style="background:#0d0d0d;border:1px solid #1f1f1f;border-left:3px solid {accent_color};padding:28px 32px;margin-bottom:24px;">
        <div style="font-size:12px;color:#666;letter-spacing:0.1em;text-transform:uppercase;font-family:'Courier New',monospace;margin-bottom:12px;">
          Regime Transition
        </div>
        <div style="font-size:28px;font-weight:700;color:#f0f0f0;letter-spacing:-0.03em;margin-bottom:4px;">
          {prev_emoji}&nbsp;{prev_label} <span style="color:#444;font-weight:400;">→</span> {new_emoji}&nbsp;{new_label}
        </div>
        <div style="font-size:13px;color:#888;margin-top:10px;font-family:'Courier New',monospace;">
          Risk score:&nbsp;<strong style="color:#f0f0f0;">{risk_score:+.1f}</strong>
          &nbsp;&nbsp;·&nbsp;&nbsp;
          Equity exposure:&nbsp;<strong style="color:{accent_color};">{new_exposure}</strong>
        </div>
      </td></tr>

      <!-- Spacer -->
      <tr><td style="height:20px;"></td></tr>

      <!-- What it means -->
      <tr><td style="background:#0d0d0d;border:1px solid #1f1f1f;padding:24px 32px;">
        <div style="font-size:11px;color:#555;letter-spacing:0.1em;text-transform:uppercase;font-family:'Courier New',monospace;margin-bottom:10px;">
          What this means
        </div>
        <div style="font-size:14px;color:#b0b0b0;line-height:1.7;">
          {what_it_means}
        </div>
      </td></tr>

      <!-- Spacer -->
      <tr><td style="height:28px;"></td></tr>

      <!-- CTA -->
      <tr><td>
        <table cellpadding="0" cellspacing="0">
          <tr>
            <td style="padding-right:12px;">
              <a href="https://api.macropulse.live"
                 style="display:inline-block;background:{accent_color};color:#000;
                        padding:11px 26px;font-size:13px;font-weight:700;
                        text-decoration:none;letter-spacing:0.01em;">
                Open Dashboard →
              </a>
            </td>
            <td>
              <a href="https://macropulse.live"
                 style="display:inline-block;background:transparent;color:#888;
                        border:1px solid #2a2a2a;padding:10px 24px;
                        font-size:13px;text-decoration:none;">
                Full Signal
              </a>
            </td>
          </tr>
        </table>
      </td></tr>

      <!-- Footer -->
      <tr><td style="padding-top:40px;border-top:1px solid #1a1a1a;margin-top:40px;">
        <div style="font-size:11px;color:#444;line-height:1.7;">
          You're receiving this because you have an active MacroPulse Starter or Pro subscription.<br/>
          <a href="https://api.macropulse.live" style="color:#555;">Manage alerts &amp; subscription →</a>
        </div>
        <div style="font-size:10px;color:#333;margin-top:8px;font-family:'Courier New',monospace;">
          MacroPulse · api.macropulse.live · PCA + HMM · Updated 18:30 UTC daily
        </div>
      </td></tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""

    webhook_payload = {
        "regime_change": {
            "from": prev_regime,
            "to": new_regime,
            "from_label": prev_label,
            "to_label": new_label,
            "equity_exposure": new_exposure,
            "risk_score": risk_score,
            "date": date,
        }
    }

    # ── Fetch recipients (async) ─────────────────────────────────
    try:
        recipients = await get_alert_recipients()
    except Exception as exc:
        logger.error("alerts: failed to fetch recipients: %s", exc)
        recipients = []

    for user in recipients:
        # Email — all starter/pro users
        try:
            from services.email import send_email
            send_email(to=user["email"], subject=subject, html=body_html)
            logger.info("regime alert email → %s", user["email"])
        except Exception as exc:
            logger.warning("alert email failed for %s: %s", user["email"], exc)

        # Webhook — pro/owner users with webhook_url configured
        if user.get("tier") in ("pro", "owner") and user.get("webhook_url"):
            try:
                resp = httpx.post(
                    user["webhook_url"],
                    json=webhook_payload,
                    timeout=10.0,
                    headers={"User-Agent": "MacroPulse-Alerts/1.0", "Content-Type": "application/json"},
                )
                logger.info("webhook delivered → %s (%d)", user["webhook_url"][:40], resp.status_code)
            except Exception as exc:
                logger.warning("webhook failed for user %s: %s", user["id"], exc)

    # ── X (Twitter) — regime change post ────────────────────────
    try:
        from services.twitter import post_regime_change_tweet
        post_regime_change_tweet(prev_regime, new_regime, risk_score, date)
    except Exception as exc:
        logger.warning("regime change tweet failed: %s", exc)

    # ── Discord — regime change embed ───────────────────────────
    try:
        from services.discord import post_regime_change
        post_regime_change(prev_regime, new_regime, risk_score, date)
    except Exception as exc:
        logger.warning("regime change Discord post failed: %s", exc)

    logger.info(
        "Regime change alerts dispatched: %s → %s (%d recipients)",
        prev_regime, new_regime, len(recipients),
    )


def alert_drift_warning(
    metric_name: str,
    value: float,
    threshold: float,
    timestamp: str,
) -> None:
    """
    Notify the owner when a model drift metric exceeds its warning threshold.

    Sends to settings.pipeline_alert_email via Brevo (fire-and-forget).
    Also POSTs to settings.webhook_url if configured (Discord / Slack).
    """
    from config.settings import get_settings
    settings = get_settings()

    subject = f"[MacroPulse] Drift Warning: {metric_name} = {value:.4f}"
    body_html = f"""
<div style="font-family:monospace;background:#0a0a0a;color:#f0f0f0;padding:32px;max-width:480px;">
  <div style="font-size:11px;color:#666;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:16px;">MacroPulse · Model Drift Warning</div>
  <div style="font-size:18px;font-weight:700;color:#f59e0b;margin-bottom:12px;">⚠ {metric_name}</div>
  <div style="font-size:13px;color:#aaa;margin-bottom:8px;">Value: <strong style="color:#f0f0f0;">{value:.4f}</strong></div>
  <div style="font-size:13px;color:#aaa;margin-bottom:8px;">Threshold: <strong style="color:#f0f0f0;">{threshold:.4f}</strong></div>
  <div style="font-size:13px;color:#aaa;margin-bottom:24px;">Timestamp: {timestamp}</div>
  <div style="font-size:12px;color:#666;">Consider retraining the model. Check the dashboard drift panel.</div>
</div>
"""

    if settings.pipeline_alert_email:
        try:
            from services.email import send_email
            send_email(to=settings.pipeline_alert_email, subject=subject, html=body_html)
            logger.info("drift alert email sent: %s=%.4f", metric_name, value)
        except Exception as exc:
            logger.warning("drift alert email failed: %s", exc)

    if settings.webhook_url:
        try:
            import httpx as _httpx
            _httpx.post(
                settings.webhook_url,
                json={"text": f"⚠️ *MacroPulse Drift Warning*\n`{metric_name}` = {value:.4f} (threshold: {threshold:.4f})"},
                timeout=10.0,
            )
        except Exception as exc:
            logger.warning("drift alert webhook failed: %s", exc)

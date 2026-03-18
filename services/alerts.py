"""
Regime change alert delivery.

Called by the daily pipeline when a regime transition is detected.
Sends email alerts to all Starter/Pro users and webhook POSTs to Pro users
who have configured a webhook_url.
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
    "expansion": "100%",
    "recovery":  "75%",
    "tightening": "25%",
    "risk_off":  "0%",
}

_REGIME_EMOJI = {
    "expansion":  "🟢",
    "recovery":   "🔵",
    "tightening": "🟡",
    "risk_off":   "🔴",
}


def send_regime_change_alerts(prev_regime: str, new_regime: str, risk_score: float, date: str) -> None:
    """
    Notify all eligible users of a regime change.
    Called by the pipeline after a regime transition is confirmed.
    """
    from database.queries import get_alert_recipients

    prev_label   = _REGIME_LABELS.get(prev_regime, prev_regime)
    new_label    = _REGIME_LABELS.get(new_regime, new_regime)
    new_exposure = _EXPOSURE.get(new_regime, "—")
    emoji        = _REGIME_EMOJI.get(new_regime, "⚪")

    subject = f"{emoji} MacroPulse: Regime shift → {new_label}"
    body_html = f"""
<div style="font-family:monospace;background:#0a0a0a;color:#f0f0f0;padding:32px;max-width:560px;">
  <div style="font-size:11px;color:#666;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:16px;">MacroPulse · Regime Alert · {date}</div>
  <div style="font-size:22px;font-weight:700;margin-bottom:8px;">{prev_label} → {new_label}</div>
  <div style="font-size:13px;color:#aaa;margin-bottom:24px;">Equity exposure: <strong style="color:#f0f0f0;">{new_exposure}</strong> &nbsp;·&nbsp; Risk score: <strong style="color:#f0f0f0;">{risk_score:+.1f}</strong></div>
  <a href="https://api.macropulse.live" style="display:inline-block;background:#f0f0f0;color:#0a0a0a;padding:10px 24px;border-radius:6px;font-weight:600;text-decoration:none;font-size:13px;">Open Dashboard →</a>
  <div style="margin-top:32px;font-size:11px;color:#444;border-top:1px solid #1f1f1f;padding-top:16px;">
    MacroPulse · <a href="https://macropulse.live" style="color:#666;">macropulse.live</a>
  </div>
</div>
"""

    payload = {
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

    try:
        recipients = get_alert_recipients()
    except Exception as exc:
        logger.error("alerts: failed to fetch recipients: %s", exc)
        return

    for user in recipients:
        # Email alert — all starter/pro users
        try:
            from services.email import send_email
            send_email(
                to=user["email"],
                subject=subject,
                html=body_html,
            )
            logger.info("alert email sent to %s", user["email"])
        except Exception as exc:
            logger.warning("alert email failed for %s: %s", user["email"], exc)

        # Webhook — pro/owner users with webhook_url configured
        if user.get("tier") in ("pro", "owner") and user.get("webhook_url"):
            try:
                resp = httpx.post(
                    user["webhook_url"],
                    json=payload,
                    timeout=10.0,
                    headers={"User-Agent": "MacroPulse-Alerts/1.0", "Content-Type": "application/json"},
                )
                logger.info("webhook delivered to %s → %d", user["webhook_url"][:40], resp.status_code)
            except Exception as exc:
                logger.warning("webhook failed for user %s: %s", user["id"], exc)

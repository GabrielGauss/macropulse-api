"""
Daily email digest for MacroPulse subscribers.

Sends a formatted MacroPulse Daily Brief to all active users via Brevo.
Called once daily after the pipeline run.  Fire-and-forget — never raises.
"""

from __future__ import annotations

import logging
from typing import Any

from database import queries
from services.email import _post

logger = logging.getLogger(__name__)

_REGIME_LABEL = {
    "expansion":  "Expansion",
    "recovery":   "Recovery",
    "tightening": "Tightening",
    "risk_off":   "Risk-Off",
}

_REGIME_COLOR = {
    "expansion":  "#22c55e",
    "recovery":   "#3b82f6",
    "tightening": "#eab308",
    "risk_off":   "#ef4444",
}

_SENDER = {"name": "MacroPulse", "email": "noreply@macropulse.live"}


def _gauge_html(value: float) -> str:
    """Render a compact colored bar for [-1,1] value."""
    pct = abs(value) * 100
    color = "#22c55e" if value >= 0 else "#ef4444"
    sign = "+" if value >= 0 else ""
    return (
        f'<span style="font-family:monospace;font-size:11px;color:#888;">'
        f'{sign}{value:.2f}&nbsp;</span>'
        f'<span style="display:inline-block;width:{pct:.0f}px;max-width:80px;'
        f'height:6px;background:{color};border-radius:3px;vertical-align:middle;"></span>'
    )


def _build_html(
    regime: str,
    risk_score: float,
    ts: str,
    scorecard: dict[str, Any],
    narrative: str,
) -> str:
    label = _REGIME_LABEL.get(regime, regime.title())
    color = _REGIME_COLOR.get(regime, "#888888")

    signals = [
        ("Growth Momentum",    scorecard.get("growth_momentum",    0)),
        ("Inflation Pressure", scorecard.get("inflation_momentum", 0)),
        ("Liquidity",          scorecard.get("liquidity",          0)),
        ("Financial Stress",   scorecard.get("financial_stress",   0)),
        ("Dollar Strength",    scorecard.get("dollar_strength",    0)),
    ]

    signal_rows = ""
    for name, val in signals:
        signal_rows += (
            f'<tr>'
            f'<td style="padding:5px 0;font-size:12px;color:#aaa;width:160px;">{name}</td>'
            f'<td style="padding:5px 0;">{_gauge_html(float(val))}</td>'
            f'</tr>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Inter',Arial,sans-serif;color:#f0f0f0;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:48px 16px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

  <!-- logo -->
  <tr><td style="padding-bottom:24px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="width:8px;height:8px;border-radius:50%;background:#22c55e;vertical-align:middle;"></td>
      <td style="padding-left:8px;font-size:15px;font-weight:600;letter-spacing:-0.02em;vertical-align:middle;">MacroPulse</td>
    </tr></table>
  </td></tr>

  <!-- date + headline -->
  <tr><td style="padding-bottom:4px;">
    <p style="margin:0;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;color:#555;font-family:monospace;">Daily Brief &middot; {ts}</p>
  </td></tr>
  <tr><td style="padding-bottom:20px;">
    <h1 style="margin:0;font-size:22px;font-weight:700;letter-spacing:-0.03em;">
      <span style="color:{color};">{label}</span>
      <span style="color:#555;font-size:14px;font-weight:400;margin-left:10px;">Risk Score {risk_score:+.0f}</span>
    </h1>
  </td></tr>

  <!-- narrative -->
  <tr><td style="padding-bottom:24px;">
    <p style="margin:0;font-size:13px;line-height:1.7;color:#ccc;">{narrative}</p>
  </td></tr>

  <tr><td style="height:1px;background:#1f1f1f;padding:0;"></td></tr>

  <!-- signal gauges -->
  <tr><td style="padding:24px 0;">
    <p style="margin:0 0 12px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#555;">Signal Gauges</p>
    <table cellpadding="0" cellspacing="0" style="width:100%;">
      {signal_rows}
    </table>
  </td></tr>

  <tr><td style="height:1px;background:#1f1f1f;padding:0;"></td></tr>

  <!-- CTA -->
  <tr><td style="padding:24px 0;">
    <a href="https://api.macropulse.live/dashboard"
       style="display:inline-block;background:#f0f0f0;color:#0a0a0a;font-size:12px;font-weight:600;padding:9px 20px;border-radius:7px;text-decoration:none;">
      Open Dashboard &rarr;
    </a>
    &nbsp;
    <a href="https://api.macropulse.live/docs"
       style="display:inline-block;background:transparent;color:#666;font-size:12px;font-weight:500;padding:9px 20px;border-radius:7px;text-decoration:none;border:1px solid #2a2a2a;">
      API Docs
    </a>
  </td></tr>

  <!-- footer -->
  <tr><td style="padding-top:16px;border-top:1px solid #1a1a1a;">
    <p style="margin:0;font-size:11px;color:#444;line-height:1.8;">
      MacroPulse &middot; Probabilistic macro regime intelligence<br>
      <a href="mailto:support@macropulse.live" style="color:#555;text-decoration:none;">support@macropulse.live</a>
      &nbsp;&middot;&nbsp;
      <a href="https://macropulse.live" style="color:#555;text-decoration:none;">macropulse.live</a>
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def _build_text(
    regime: str,
    risk_score: float,
    ts: str,
    scorecard: dict[str, Any],
    narrative: str,
) -> str:
    label = _REGIME_LABEL.get(regime, regime.title())
    signals = (
        f"  Growth Momentum    {scorecard.get('growth_momentum', 0):+.2f}\n"
        f"  Inflation Pressure {scorecard.get('inflation_momentum', 0):+.2f}\n"
        f"  Liquidity          {scorecard.get('liquidity', 0):+.2f}\n"
        f"  Financial Stress   {scorecard.get('financial_stress', 0):+.2f}\n"
        f"  Dollar Strength    {scorecard.get('dollar_strength', 0):+.2f}"
    )
    return (
        f"MacroPulse Daily Brief — {ts}\n\n"
        f"Regime: {label}  |  Risk Score: {risk_score:+.0f}\n\n"
        f"{narrative}\n\n"
        f"SIGNAL GAUGES\n{signals}\n\n"
        f"Dashboard: https://api.macropulse.live/dashboard\n"
        f"API Docs:  https://api.macropulse.live/docs\n\n"
        f"— MacroPulse  support@macropulse.live"
    )


async def send_daily_digest(
    regime_row: dict[str, Any],
    scorecard: dict[str, Any],
    narrative: str,
) -> None:
    """
    Send the daily brief to all active subscribers.

    Fetches subscriber list from DB, sends one email per recipient via Brevo.
    Silently skips if Brevo key is not configured.  Never raises.
    """
    try:
        emails = await queries.fetch_subscriber_emails()
    except Exception:
        logger.error("Could not fetch subscriber emails", exc_info=True)
        return

    if not emails:
        logger.info("No active subscribers — skipping daily digest.")
        return

    regime = str(regime_row.get("regime", "unknown")).lower()
    risk_score = float(regime_row.get("risk_score", 0))
    ts = str(regime_row.get("time", ""))[:10]

    html = _build_html(regime, risk_score, ts, scorecard, narrative)
    text = _build_text(regime, risk_score, ts, scorecard, narrative)

    subject = f"MacroPulse Daily Brief — {ts} · {_REGIME_LABEL.get(regime, regime.title())}"

    # Brevo supports up to 50 recipients per call; batch to be safe
    BATCH = 50
    for i in range(0, len(emails), BATCH):
        batch = emails[i : i + BATCH]
        to_list = [{"email": e} for e in batch]
        try:
            _post({
                "sender":      _SENDER,
                "to":          to_list,
                "subject":     subject,
                "htmlContent": html,
                "textContent": text,
            })
            logger.info("Daily digest sent to %d subscribers (batch %d)", len(batch), i // BATCH + 1)
        except Exception:
            logger.error("Daily digest batch %d failed", i // BATCH + 1, exc_info=True)

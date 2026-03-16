"""
Discord webhook integration for MacroPulse.

Posts a formatted daily signal brief to a Discord channel via
an incoming webhook URL.  Fire-and-forget — never raises.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from config.settings import get_settings

logger = logging.getLogger(__name__)

# Regime display config
_REGIME_EMOJI = {
    "expansion":  "🟢",
    "recovery":   "🔵",
    "tightening": "🟡",
    "risk_off":   "🔴",
}

_REGIME_LABEL = {
    "expansion":  "Expansion",
    "recovery":   "Recovery",
    "tightening": "Tightening",
    "risk_off":   "Risk-Off",
}

_REGIME_COLOR = {
    "expansion":  0x22C55E,   # green
    "recovery":   0x3B82F6,   # blue
    "tightening": 0xEAB308,   # yellow
    "risk_off":   0xEF4444,   # red
}


def _gauge_bar(value: float, width: int = 10) -> str:
    """Return a compact ASCII bar for a [-1, 1] value."""
    filled = round(abs(value) * width)
    bar = "█" * filled + "░" * (width - filled)
    arrow = "+" if value >= 0 else "-"
    return f"{arrow}{bar} {value:+.2f}"


def post_daily_signal(
    regime_row: dict[str, Any],
    scorecard: dict[str, Any],
    narrative: str | None = None,
) -> None:
    """
    Post a MacroPulse Daily Brief embed to a Discord channel.

    Parameters
    ----------
    regime_row : dict from macro_regimes table (current regime data).
    scorecard  : dict from build_scorecard() with 5 signal gauges.
    narrative  : optional LLM-generated macro interpretation string.
    """
    settings = get_settings()
    if not settings.discord_webhook_url:
        logger.debug("DISCORD_WEBHOOK_URL not set; skipping Discord post.")
        return

    regime = str(regime_row.get("regime", "unknown")).lower()
    risk_score = float(regime_row.get("risk_score", 0))
    ts = str(regime_row.get("time", ""))[:10]  # YYYY-MM-DD

    emoji = _REGIME_EMOJI.get(regime, "⚪")
    label = _REGIME_LABEL.get(regime, regime.title())
    color = _REGIME_COLOR.get(regime, 0x888888)

    # Build signal fields
    signal_lines = []
    signal_map = {
        "Growth":     scorecard.get("growth_momentum", 0),
        "Inflation":  scorecard.get("inflation_momentum", 0),
        "Liquidity":  scorecard.get("liquidity", 0),
        "Stress":     scorecard.get("financial_stress", 0),
        "Dollar":     scorecard.get("dollar_strength", 0),
    }
    for name, val in signal_map.items():
        signal_lines.append(f"`{name:<10}` {_gauge_bar(float(val))}")

    signals_block = "\n".join(signal_lines)

    description = f"{emoji} **{label}** · Risk Score `{risk_score:+.0f}`\n\n"
    if narrative:
        description += f"_{narrative}_\n\n"
    description += f"**Signal Gauges**\n```\n{signals_block}\n```"

    embed = {
        "title": f"MacroPulse Daily Brief — {ts}",
        "description": description,
        "color": color,
        "footer": {
            "text": "api.macropulse.live  ·  /v1/signals/latest for full data"
        },
    }

    payload = {"embeds": [embed]}
    data = json.dumps(payload).encode()
    req = Request(
        settings.discord_webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            logger.info("Discord signal posted (status %d)", resp.status)
    except URLError as exc:
        logger.error("Discord webhook failed: %s", exc)
    except Exception:
        logger.error("Discord webhook unexpected error", exc_info=True)

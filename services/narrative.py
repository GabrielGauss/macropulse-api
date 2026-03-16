"""
LLM-generated macro narrative via Anthropic Claude.

Produces a concise 2-3 sentence human-readable interpretation of the
current macro regime and signal gauges.  Falls back to a rule-based
template if the API key is not configured or the call fails.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from config.settings import get_settings

logger = logging.getLogger(__name__)

_API_URL = "https://api.anthropic.com/v1/messages"
_MODEL = "claude-haiku-4-5-20251001"


def _rule_based_narrative(
    regime: str,
    risk_score: float,
    scorecard: dict[str, Any],
) -> str:
    """Deterministic fallback when Anthropic API is unavailable."""
    growth = scorecard.get("growth_momentum", 0)
    liquidity = scorecard.get("liquidity", 0)
    stress = scorecard.get("financial_stress", 0)
    inflation = scorecard.get("inflation_momentum", 0)

    regime_desc = {
        "expansion":  "Growth momentum is accelerating and financial conditions remain supportive.",
        "recovery":   "The economy is transitioning from contraction toward expansion as growth signals stabilize.",
        "tightening": "Monetary tightening is compressing financial conditions as inflation pressures persist.",
        "risk_off":   "Risk sentiment has deteriorated sharply; defensive positioning is indicated.",
    }.get(regime, "The macro regime is in transition.")

    liquidity_desc = (
        "Fed liquidity is expanding, supporting risk assets."
        if liquidity > 0.2
        else "Fed liquidity is contracting, a headwind for risk assets."
        if liquidity < -0.2
        else "Fed liquidity is neutral."
    )

    stress_desc = (
        "Credit and volatility conditions remain calm."
        if stress > 0.2
        else "Stress indicators are elevated — monitor credit spreads and volatility."
        if stress < -0.2
        else ""
    )

    parts = [regime_desc, liquidity_desc]
    if stress_desc:
        parts.append(stress_desc)
    return " ".join(parts)


def generate_narrative(
    regime_row: dict[str, Any],
    scorecard: dict[str, Any],
) -> str:
    """
    Generate a concise macro narrative for the current signal state.

    Uses Anthropic claude-haiku for low latency and cost.
    Falls back to rule-based text if API is unavailable.

    Returns
    -------
    str — 2-3 sentence macro interpretation (plain text).
    """
    settings = get_settings()
    regime = str(regime_row.get("regime", "unknown")).lower()
    risk_score = float(regime_row.get("risk_score", 0))

    if not settings.anthropic_api_key:
        logger.debug("ANTHROPIC_API_KEY not set; using rule-based narrative.")
        return _rule_based_narrative(regime, risk_score, scorecard)

    # Build a compact signal summary for the prompt
    signal_summary = (
        f"Growth: {scorecard.get('growth_momentum', 0):+.2f}, "
        f"Inflation: {scorecard.get('inflation_momentum', 0):+.2f}, "
        f"Liquidity: {scorecard.get('liquidity', 0):+.2f}, "
        f"Stress: {scorecard.get('financial_stress', 0):+.2f} (positive=calm), "
        f"Dollar: {scorecard.get('dollar_strength', 0):+.2f}"
    )

    prompt = (
        f"You are a macro analyst writing a daily brief for institutional traders.\n\n"
        f"Current macro regime: {regime} (risk score {risk_score:+.0f}/100)\n"
        f"Signal gauges (range -1 to +1): {signal_summary}\n\n"
        f"Write exactly 2-3 sentences interpreting these signals for traders. "
        f"Be direct and analytical. No bullet points, no headers. Plain prose only."
    )

    body = json.dumps({
        "model": _MODEL,
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = Request(
        _API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            text = result["content"][0]["text"].strip()
            logger.info("Narrative generated (%d chars)", len(text))
            return text
    except URLError as exc:
        logger.warning("Anthropic API call failed: %s — using fallback", exc)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        logger.warning("Anthropic response parse error: %s — using fallback", exc)
    except Exception:
        logger.warning("Anthropic unexpected error — using fallback", exc_info=True)

    return _rule_based_narrative(regime, risk_score, scorecard)

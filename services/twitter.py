"""
X (Twitter) integration for MacroPulse.

Posts a daily regime update tweet via the Twitter API v2
using OAuth 1.0a (User Auth) — required for write access.
Fire-and-forget — never raises.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.parse
import uuid
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from config.settings import get_settings

logger = logging.getLogger(__name__)

_TWEET_URL = "https://api.twitter.com/2/tweets"

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

_EXPOSURE = {
    "expansion":  "100%",
    "recovery":   "75%",
    "tightening": "25%",
    "risk_off":   "0%",
}


def _percent_encode(s: str) -> str:
    return urllib.parse.quote(str(s), safe="")


def _oauth1_header(method: str, url: str, settings) -> str:
    """Build OAuth 1.0a Authorization header (HMAC-SHA1)."""
    params = {
        "oauth_consumer_key":     settings.x_api_key,
        "oauth_nonce":            uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        str(int(time.time())),
        "oauth_token":            settings.x_access_token,
        "oauth_version":          "1.0",
    }

    # Signature base string
    sorted_params = "&".join(
        f"{_percent_encode(k)}={_percent_encode(v)}"
        for k, v in sorted(params.items())
    )
    base = "&".join([
        _percent_encode(method.upper()),
        _percent_encode(url),
        _percent_encode(sorted_params),
    ])

    # Signing key
    signing_key = (
        _percent_encode(settings.x_api_secret) + "&" +
        _percent_encode(settings.x_access_token_secret)
    )

    sig = base64.b64encode(
        hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()
    ).decode()

    params["oauth_signature"] = sig

    header = "OAuth " + ", ".join(
        f'{_percent_encode(k)}="{_percent_encode(v)}"'
        for k, v in sorted(params.items())
    )
    return header


def post_daily_tweet(regime_row: dict[str, Any], scorecard: dict[str, Any]) -> None:
    """
    Post a daily macro regime tweet to @macropulselv.
    Fire-and-forget — never raises.
    """
    settings = get_settings()
    if not all([
        settings.x_api_key, settings.x_api_secret,
        settings.x_access_token, settings.x_access_token_secret,
    ]):
        logger.debug("X credentials not configured; skipping tweet.")
        return

    regime = str(regime_row.get("regime", "unknown")).lower()
    risk_score = float(regime_row.get("risk_score", 0))
    ts = str(regime_row.get("time", ""))[:10]

    emoji = _REGIME_EMOJI.get(regime, "⚪")
    label = _REGIME_LABEL.get(regime, regime.title())
    exposure = _EXPOSURE.get(regime, "—")

    liq_trend = ""
    liq = scorecard.get("liquidity", 0)
    if liq > 0.2:
        liq_trend = "Liquidity expanding"
    elif liq < -0.2:
        liq_trend = "Liquidity contracting"
    else:
        liq_trend = "Liquidity stable"

    score_str = f"{risk_score:+.0f}"
    tweet = (
        f"{emoji} Macro Regime · {ts}\n\n"
        f"Regime: {label}\n"
        f"Risk Score: {score_str}\n"
        f"Equity Exposure: {exposure}\n"
        f"{liq_trend}\n\n"
        f"Full signal → macropulse.live\n"
        f"#macro #quant #trading"
    )

    payload = json.dumps({"text": tweet}).encode()
    auth_header = _oauth1_header("POST", _TWEET_URL, settings)

    req = Request(
        _TWEET_URL,
        data=payload,
        headers={
            "Authorization":  auth_header,
            "Content-Type":   "application/json",
            "User-Agent":     "MacroPulse/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
            tweet_id = body.get("data", {}).get("id", "?")
            logger.info("Tweet posted (id=%s): %s", tweet_id, label)
    except URLError as exc:
        logger.error("Twitter API failed: %s", exc)
    except Exception:
        logger.error("Twitter unexpected error", exc_info=True)

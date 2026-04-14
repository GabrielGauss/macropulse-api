"""
IRL Heartbeat Service — issues signed heartbeats for the IRL Engine L2 protocol.

mta_ref = SHA-256 of the raw /v1/regime/current HTTP response body.
This is identical to the hash the IRL Engine computes when it independently
fetches the same endpoint, so the binding is cryptographically verifiable.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import time
from dataclasses import dataclass

import httpx

import services.mta_signer as _mta_signer

logger = logging.getLogger(__name__)

_sequence: int = int(time.time() * 1000)
_REGIME_URL = "http://localhost:8000/v1/regime/current"
_http_client: httpx.AsyncClient | None = None


def _get_http() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=2.0)
    return _http_client


@dataclass
class Heartbeat:
    sequence_id: int
    timestamp_ms: int
    regime_id: int
    mta_ref: str
    signature: str


def _next_sequence() -> int:
    global _sequence
    _sequence += 1
    return _sequence


async def issue_heartbeat() -> Heartbeat:
    """Generate and sign the next heartbeat.

    Fetches /v1/regime/current and hashes the raw response bytes so that
    mta_ref exactly matches the hash the IRL Engine will compute when it
    independently calls the same endpoint for each /irl/authorize request.
    """
    resp = await _get_http().get(_REGIME_URL)
    resp.raise_for_status()

    raw_bytes = resp.content
    regime_data = resp.json()

    mta_ref = hashlib.sha256(raw_bytes).hexdigest()

    _REGIME_ID = {"expansion": 0, "recovery": 1, "tightening": 2, "risk_off": 3}
    regime_id = int(
        regime_data.get("regime_id")
        if regime_data.get("regime_id") is not None
        else _REGIME_ID.get(regime_data.get("macro_regime", ""), 3)
    )

    seq = _next_sequence()
    timestamp_ms = int(time.time() * 1000)

    payload = (
        seq.to_bytes(8, "big")
        + timestamp_ms.to_bytes(8, "big")
        + bytes([regime_id])
        + mta_ref.encode("utf-8")
    )

    signing_key = _mta_signer._signing_key
    if signing_key is None:
        raise RuntimeError(
            "MTA_SIGNING_KEY_HEX not initialised — cannot sign heartbeat. "
            "Ensure init_signer() is called at startup."
        )

    raw_sig = signing_key.sign(payload)
    sig_b64 = base64.b64encode(raw_sig).decode("ascii")

    return Heartbeat(
        sequence_id=seq,
        timestamp_ms=timestamp_ms,
        regime_id=regime_id,
        mta_ref=mta_ref,
        signature=sig_b64,
    )

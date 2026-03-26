"""
MTA Signer — Ed25519 signing for /regime/current responses.

Signs the canonical JSON payload so the IRL Engine can verify that every
MacroPulse regime response is authentic and unmodified.

Signing contract (must match IRL Engine src/mta.rs verify_signature):
  1. Build the response dict WITHOUT the "signature" field.
  2. Serialize to canonical JSON: sorted keys, no whitespace.
  3. Sign the UTF-8 bytes with Ed25519.
  4. Base64-encode the 64-byte signature and include it as "signature".

The IRL Engine reverses steps 1–3 to verify.
"""

from __future__ import annotations

import base64
import json
import logging

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

logger = logging.getLogger(__name__)

_signing_key: Ed25519PrivateKey | None = None


def init_signer(private_key_hex: str) -> None:
    """Load the Ed25519 private key from a hex string.

    Call once at application startup (e.g., in main.py lifespan).
    If the key is empty or invalid, signing is disabled and responses
    will be returned without a signature (dev mode).
    """
    global _signing_key
    if not private_key_hex:
        logger.warning(
            "MTA_SIGNING_KEY_HEX not set — regime responses will not be signed. "
            "IRL Engine will reject all MTA responses in production."
        )
        _signing_key = None
        return

    try:
        key_bytes = bytes.fromhex(private_key_hex)
        _signing_key = Ed25519PrivateKey.from_private_bytes(key_bytes)
        pub = _signing_key.public_key()
        pub_hex = pub.public_bytes_raw().hex()
        logger.info("MTA signer initialised. Public key: %s", pub_hex)
    except Exception as exc:
        logger.error("Failed to load MTA signing key: %s", exc)
        _signing_key = None


def sign_regime_payload(payload: dict) -> str | None:
    """Sign a regime response payload and return the base64-encoded signature.

    Args:
        payload: The response dict WITHOUT the "signature" field.

    Returns:
        Base64-encoded Ed25519 signature, or None if signing is disabled.
    """
    if _signing_key is None:
        return None

    canonical = _canonical_json(payload)
    raw_sig = _signing_key.sign(canonical.encode("utf-8"))
    return base64.b64encode(raw_sig).decode("ascii")


def get_public_key_hex() -> str | None:
    """Return the hex-encoded public key for display / config checking."""
    if _signing_key is None:
        return None
    return _signing_key.public_key().public_bytes_raw().hex()


def _canonical_json(obj: object) -> str:
    """Serialize to canonical JSON: sorted keys, no whitespace.

    Matches Rust's seal::canonicalize_json and Python's json.dumps with
    sort_keys=True, separators=(',', ':').
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)

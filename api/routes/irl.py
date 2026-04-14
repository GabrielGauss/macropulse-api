"""
IRL Engine API routes.

  GET /v1/irl/heartbeat   — L2 anti-replay signed heartbeat (all IRL tiers)
  GET /v1/irl/audit       — L2 deep factor + stress attribution (irl_audit only)
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth import require_api_key
from services.heartbeat_service import issue_heartbeat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/irl", tags=["IRL"])


# ── Auth helpers ─────────────────────────────────────────────────

def _require_irl(key_record: dict = Depends(require_api_key)) -> dict:
    """Block non-IRL keys (MacroPulse users have no business calling IRL endpoints)."""
    tier = key_record.get("tier", "")
    if tier not in ("irl_sidecar", "irl_audit", "owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires an IRL Engine licence. Visit macropulse.live/irl",
        )
    return key_record


def _require_irl_audit(key_record: dict = Depends(require_api_key)) -> dict:
    """L2 Audit endpoints — irl_audit tier only."""
    tier = key_record.get("tier", "")
    if tier not in ("irl_audit", "owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This endpoint requires an IRL Engine Audit (L2) licence. "
                "Your current plan is Sidecar (L1). Upgrade at macropulse.live/irl"
            ),
        )
    return key_record


# ── Response models ──────────────────────────────────────────────

class HeartbeatResponse(BaseModel):
    sequence_id: int
    timestamp_ms: int
    regime_id: int
    mta_ref: str
    signature: str


class FactorAttribution(BaseModel):
    """Single PCA factor with its loading and current value."""
    factor: str          # "PC1" … "PC4"
    description: str
    value: float
    direction: str       # "bullish" | "bearish" | "neutral"


class StressIndicator(BaseModel):
    name: str
    value: float | None
    z_score: float | None   # z-score vs 90-day window (None if insufficient history)
    flag: str               # "elevated" | "normal" | "suppressed"


class AuditResponse(BaseModel):
    generated_at: str
    date: str
    regime: str
    risk_score: float
    agent_count: int
    # Factor decomposition
    factor_attribution: list[FactorAttribution]
    # Stress decomposition
    stress_indicators: list[StressIndicator]
    # Liquidity attribution
    liquidity: dict[str, Any]
    # Regime transition risk
    transition_risk: dict[str, Any]
    # Drift health
    model_health: dict[str, Any]


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/heartbeat", response_model=HeartbeatResponse)
async def get_heartbeat(
    key_record: dict = Depends(_require_irl),
) -> HeartbeatResponse:
    """Issue a fresh signed heartbeat for use in /irl/authorize requests.

    Agents must include the returned heartbeat in every POST /irl/authorize
    call when LAYER2_ENABLED=true on the IRL Engine. Each call returns a
    new heartbeat with a strictly increasing sequence_id — do not reuse.
    """
    try:
        hb = await issue_heartbeat()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return HeartbeatResponse(
        sequence_id=hb.sequence_id,
        timestamp_ms=hb.timestamp_ms,
        regime_id=hb.regime_id,
        mta_ref=hb.mta_ref,
        signature=hb.signature,
    )


@router.get("/audit", response_model=AuditResponse, summary="L2 deep factor & stress audit")
async def get_audit(
    key_record: dict = Depends(_require_irl_audit),
) -> AuditResponse:
    """
    L2 Audit endpoint — deep decomposition of the current macro regime signal.

    Returns:
    - PCA factor attribution with directional interpretation
    - Stress indicator z-scores (credit spreads, VIX, yield curve)
    - Liquidity attribution (FedAssets, TGA, RRP breakdown)
    - Regime transition probability matrix (next-state risk)
    - Model drift health metrics

    Requires IRL Engine Audit (L2) licence (min 3 agents).
    """
    from database import queries
    from models.pca_model import PCAModel
    from models.hmm_model import HMMModel
    from models.regime_classifier import RegimeClassifier
    from config.settings import get_settings
    import numpy as np

    settings = get_settings()
    version = settings.default_model_version

    # ── Load data ────────────────────────────────────────────────
    regime_row = await queries.fetch_current_regime()
    if regime_row is None:
        raise HTTPException(status_code=503, detail="No regime data available. Pipeline not yet run.")

    factors_hist = await queries.fetch_latest_factors(limit=90)
    liquidity_hist = await queries.fetch_latest_liquidity(limit=90)
    drift_hist = await queries.fetch_latest_drift(limit=30)
    features_hist = await queries.fetch_latest_features(limit=90)

    # ── Load models ──────────────────────────────────────────────
    try:
        pca_model = PCAModel.load(version)
        hmm_model = HMMModel.load(version)
        classifier = RegimeClassifier.load(version)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Model artifacts unavailable: {exc}")

    current_regime = regime_row["regime"]
    risk_score = float(regime_row.get("risk_score") or 0)

    # ── Factor attribution ───────────────────────────────────────
    _FACTOR_DESC = {
        "PC1": "Liquidity & rates — primary driver of risk-on/risk-off",
        "PC2": "Risk appetite — equity momentum vs credit stress",
        "PC3": "Credit stress — HY spreads vs investment grade",
        "PC4": "Dollar & momentum — DXY and cross-asset momentum",
    }

    factor_attribution = []
    if factors_hist:
        latest_f = factors_hist[0]
        for i, key in enumerate(["factor_1", "factor_2", "factor_3", "factor_4"], start=1):
            val = latest_f.get(key)
            if val is None:
                continue
            val = float(val)
            direction = "bullish" if val > 0.15 else "bearish" if val < -0.15 else "neutral"
            factor_attribution.append(FactorAttribution(
                factor=f"PC{i}",
                description=_FACTOR_DESC.get(f"PC{i}", ""),
                value=round(val, 4),
                direction=direction,
            ))

    # ── Stress indicators ────────────────────────────────────────
    # Z-score each feature vs its 90-day window
    _STRESS_COLS = {
        "d_vix":        "VIX (equity vol)",
        "d_hy_spread":  "HY credit spread",
        "yield_curve":  "Yield curve (10Y-2Y)",
        "d_dxy":        "DXY (dollar index)",
        "net_liquidity": "Net Fed liquidity",
    }

    stress_indicators = []
    if features_hist:
        feat_vals: dict[str, list[float]] = {col: [] for col in _STRESS_COLS}
        for row in features_hist:
            for col in _STRESS_COLS:
                v = row.get(col)
                if v is not None:
                    feat_vals[col].append(float(v))

        latest_feat = features_hist[0]
        for col, label in _STRESS_COLS.items():
            series = feat_vals[col]
            latest_val = latest_feat.get(col)
            z = None
            if latest_val is not None and len(series) >= 10:
                arr = np.array(series)
                mu, sigma = arr.mean(), arr.std()
                z = float((float(latest_val) - mu) / sigma) if sigma > 0 else 0.0
                z = round(z, 2)

            flag = "normal"
            if z is not None:
                if col in ("d_vix", "d_hy_spread"):
                    flag = "elevated" if z > 1.5 else "suppressed" if z < -1.5 else "normal"
                else:
                    flag = "elevated" if abs(z) > 1.5 else "normal"

            stress_indicators.append(StressIndicator(
                name=label,
                value=round(float(latest_val), 4) if latest_val is not None else None,
                z_score=z,
                flag=flag,
            ))

    # ── Liquidity attribution ────────────────────────────────────
    liquidity_out: dict[str, Any] = {"trend": "unknown", "latest_bn_usd": None, "30d_change_bn_usd": None}
    if liquidity_hist:
        latest_liq = liquidity_hist[0]
        liq_val = latest_liq.get("net_liquidity")
        if liq_val is not None:
            liquidity_out["latest_bn_usd"] = round(float(liq_val) / 1000, 1)
        if len(liquidity_hist) >= 30:
            older = liquidity_hist[29].get("net_liquidity")
            if liq_val is not None and older is not None:
                delta = float(liq_val) - float(older)
                liquidity_out["30d_change_bn_usd"] = round(delta / 1000, 1)
                liquidity_out["trend"] = "expanding" if delta > 0 else "contracting"

    # ── Transition risk ──────────────────────────────────────────
    label_map = classifier.label_map  # {state_idx: regime_name}
    reverse_map = {v: k for k, v in label_map.items()}
    current_idx = reverse_map.get(current_regime, 0)
    trans_row = hmm_model.transition_matrix[current_idx]
    transition_risk = {
        label_map.get(i, f"state_{i}"): round(float(p), 4)
        for i, p in enumerate(trans_row)
    }

    # ── Model health ─────────────────────────────────────────────
    model_health: dict[str, Any] = {"status": "unknown"}
    if drift_hist:
        latest_drift = drift_hist[0]
        pca_var = latest_drift.get("pca_explained_variance")
        persistence = latest_drift.get("regime_persistence")
        mean_shift = latest_drift.get("feature_mean_shift")
        warn_var = settings.pipeline_drift_variance_warn
        warn_shift = settings.pipeline_drift_feature_shift_warn
        flags = []
        if pca_var is not None and pca_var > warn_var:
            flags.append("pca_variance_drift")
        if mean_shift is not None and mean_shift > warn_shift:
            flags.append("feature_mean_shift")
        model_health = {
            "status": "degraded" if flags else "healthy",
            "flags": flags,
            "pca_explained_variance": round(float(pca_var), 4) if pca_var is not None else None,
            "regime_persistence": round(float(persistence), 4) if persistence is not None else None,
            "feature_mean_shift": round(float(mean_shift), 4) if mean_shift is not None else None,
        }

    return AuditResponse(
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        date=str(regime_row["time"])[:10],
        regime=current_regime,
        risk_score=risk_score,
        agent_count=key_record.get("agent_count", 1),
        factor_attribution=factor_attribution,
        stress_indicators=stress_indicators,
        liquidity=liquidity_out,
        transition_risk=transition_risk,
        model_health=model_health,
    )

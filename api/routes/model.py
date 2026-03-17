"""
Model introspection endpoints — expose HMM and PCA internals for the Quant HUD.

GET /v1/model/transition-matrix  — HMM state transition probability matrix (4×4)
GET /v1/model/feature-loadings   — PCA component loadings (n_components × n_features)
GET /v1/model/probabilities       — Full daily probability time series (soft state timeline)

All endpoints require authentication (any tier).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.auth import require_api_key
from config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/model", tags=["Model"])

# Canonical feature names (v2 — 10 features)
_FEATURE_NAMES = [
    "d_liquidity", "d_sp500", "d_vix", "d_dxy",
    "d_hy_spread", "d_yield_curve", "d_10y", "d_2y",
    "d_gold", "d_oil",
]

_REGIME_LABELS = ["expansion", "recovery", "tightening", "risk_off"]


def _load_service():
    """Lazy-load the inference service (avoids import at startup)."""
    from services.inference import RegimeInferenceService
    settings = get_settings()
    return RegimeInferenceService(model_version=settings.default_model_version)


@router.get("/transition-matrix")
def get_transition_matrix(key_record: dict = Depends(require_api_key)) -> dict:
    """
    Return the HMM state transition probability matrix.

    Each cell [from_regime][to_regime] is the daily probability of transitioning
    from one macro regime to another given the current state.

    Rows sum to 1.0 (row-stochastic matrix).
    """
    try:
        svc = _load_service()
        transmat = svc.hmm.transition_matrix          # (n_states, n_states) numpy array
        label_map = svc.classifier.label_map          # {state_idx: regime_name}
        n_states = transmat.shape[0]

        # Build ordered label list by state index
        state_labels = [label_map.get(i, f"state_{i}") for i in range(n_states)]

        matrix = []
        for i in range(n_states):
            row = {
                "from": state_labels[i],
                "to": {state_labels[j]: round(float(transmat[i, j]), 4) for j in range(n_states)},
            }
            matrix.append(row)

        return {
            "regimes": state_labels,
            "matrix": matrix,
            "interpretation": "Row = current regime. Values = daily P(transition to column regime).",
        }
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Model artifacts not found. Run the pipeline first.")
    except Exception as exc:
        logger.error("transition-matrix error: %s", exc)
        raise HTTPException(status_code=503, detail="Model temporarily unavailable.")


@router.get("/feature-loadings")
def get_feature_loadings(key_record: dict = Depends(require_api_key)) -> dict:
    """
    Return PCA component loadings (factor × feature weights).

    Each row is a latent factor. Each column is a raw input feature.
    Large absolute values indicate the features that drive that factor.
    """
    try:
        svc = _load_service()
        components = svc.pca.pca.components_          # (n_components, n_features)
        evr = svc.pca.explained_variance_ratio        # [f1_var, f2_var, ...]
        n_components, n_features = components.shape

        feature_names = _FEATURE_NAMES[:n_features]  # align to however many were used

        factors = []
        for i in range(n_components):
            factors.append({
                "factor": f"F{i + 1}",
                "explained_variance": round(evr[i] if i < len(evr) else 0.0, 4),
                "loadings": {
                    feature_names[j]: round(float(components[i, j]), 4)
                    for j in range(n_features)
                },
            })

        return {
            "n_components": n_components,
            "n_features": n_features,
            "feature_names": feature_names,
            "factors": factors,
            "total_variance_explained": round(sum(evr), 4),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Model artifacts not found. Run the pipeline first.")
    except Exception as exc:
        logger.error("feature-loadings error: %s", exc)
        raise HTTPException(status_code=503, detail="Model temporarily unavailable.")


@router.get("/probabilities")
def get_probability_series(
    limit: int = 365,
    key_record: dict = Depends(require_api_key),
) -> dict:
    """
    Return the full daily soft-state probability time series from the DB.

    Suitable for rendering a stacked-area timeline of regime probabilities.
    All 4 prob_ columns are returned per row.
    """
    try:
        from database.queries import fetch_regime_history
        rows = fetch_regime_history(limit=limit)
    except Exception as exc:
        logger.error("probabilities DB error: %s", exc)
        raise HTTPException(status_code=503, detail="Data temporarily unavailable.")

    series = []
    for row in reversed(rows):  # oldest first for charting
        series.append({
            "date": row["time"].strftime("%Y-%m-%d") if hasattr(row.get("time"), "strftime") else str(row["time"])[:10],
            "regime": row.get("regime"),
            "prob_expansion":  round(float(row.get("prob_expansion")  or 0), 4),
            "prob_recovery":   round(float(row.get("prob_recovery")   or 0), 4),
            "prob_tightening": round(float(row.get("prob_tightening") or 0), 4),
            "prob_risk_off":   round(float(row.get("prob_risk_off")   or 0), 4),
        })

    return {"days": len(series), "series": series}

# MacroPulse API

> Macro regime classification as an API. PCA + Gaussian HMM on 10 macro inputs, updated daily at 21:00 UTC.

**Base URL:** `https://macropulse.live`  
**Docs:** [macropulse.live](https://macropulse.live) · **X:** [@macropulselv](https://x.com/macropulselv)

---

## The Four Regimes

| Regime | Equity Exposure | Description |
|--------|----------------|-------------|
| `expansion` | 100% | Broad risk-on — momentum and carry thrive |
| `recovery` | 75% | Post-stress rebound — selectivity still warranted |
| `tightening` | 25% | Fed pressure or credit stress — reduce beta |
| `risk_off` | 0% | Macro deterioration — capital preservation mode |

Regimes are identified by a Hidden Markov Model operating on a PCA-compressed latent factor extracted from 10 macroeconomic inputs (yield curve, credit spreads, volatility, momentum, liquidity indicators).

---

## Endpoints

### Public (no auth)

#### `GET /v1/public/signal`
Current macro regime and risk score.

```json
{
  "macro_regime": "recovery",
  "risk_score": 34.1,
  "equity_exposure": 0.75,
  "timestamp": "2026-04-06T00:00:00Z"
}
```

#### `GET /v1/public/chart-data`
730-day series for charting. Returns `date`, `regime`, `risk_score`, `sp500`, `gold`, `strategy` (all rebased to 100).

#### `GET /v1/pipeline/status`
Last pipeline run timestamp and data freshness.

```json
{
  "last_run_at": "2026-04-06T21:00:00Z",
  "status": "success",
  "data_lag": false,
  "model_version": "v1"
}
```

---

### Authenticated

**Authentication:** Pass your API key as a header:
```
X-API-Key: mp_your_key_here
```

#### `GET /v1/regime/current`
Same as public signal, authenticated.

#### `GET /v1/regime/history`
Full regime history with timestamps and risk scores.

#### `GET /v1/regime/stats`
Aggregate statistics: Sharpe ratio, max drawdown, regime distribution, average persistence.

#### `GET /v1/forecast`
Short-term regime probability forecast (5-day horizon).

#### `GET /v1/analysis/composite`
Composite macro score with factor breakdown.

---

## Quick Start

```bash
# Get current regime (no auth)
curl https://macropulse.live/v1/public/signal

# Authenticated call
curl https://macropulse.live/v1/regime/history \
  -H "X-API-Key: mp_your_key_here"
```

```python
import requests

signal = requests.get("https://macropulse.live/v1/public/signal").json()
print(f"Regime: {signal['macro_regime']}, Risk score: {signal['risk_score']}")
```

---

## Get an API Key

[macropulse.live/pricing](https://macropulse.live/pricing) — free tier, no credit card required.

---

## Rate Limits

| Tier | Requests/day | Price |
|------|-------------|-------|
| Free | 50 | — |
| Starter | 500 | $49/mo |
| Pro | Unlimited | $199/mo |

---

## Status & Updates

Follow [@macropulselv](https://x.com/macropulselv) for regime updates and release notes.

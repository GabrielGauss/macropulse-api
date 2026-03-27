# MacroPulse — Content & Social Posts

## Instructions for Claude
- This file is the single source of truth for all social/content drafts.
- Each post has a header block with metadata, then the body below it.
- Do NOT rewrite a post marked `[PUBLISHED]`. Do NOT delete any entry.
- When drafting a new post: add it at the bottom of the relevant platform section.
- Status lifecycle: `[DRAFT]` → `[READY]` → `[PUBLISHED: YYYY-MM-DD]`
- When the user says "write the Substack post" or "draft a tweet", append here.
- Platform tone guidelines are in the ## Tone section below.
- Target audience: quant developers, systematic traders, macro discretionary PMs, fintech builders.
- MacroPulse pitch in one sentence: daily PCA + HMM macro regime classification via REST API — four states, one endpoint, free tier.

---

## Tone

**Substack** — technical, authoritative, no fluff. Show the model output, explain *why* it works, give real numbers (Sharpe, max DD, regime dates). End with a soft CTA to the free API key. Length: 600–1200 words. Include charts or ASCII tables where possible.

**Twitter / X** — punchy, data-first. Lead with the finding, not the methodology. Threads work better than single tweets for technical content. Max 280 chars per tweet. Use `$SPX`, `$VIX`, `#MacroTrading` sparingly.

**LinkedIn** — slightly more polished than Twitter, still technical. Fine to mention "I built this." Developers and PMs both read it.

**Hacker News (Show HN)** — matter-of-fact, no marketing language. Lead with what it does, how it works, what's free. Invite technical critique.

---

## Substack

### POST-001 — HMM Regime Teardown: What the Model Saw in 2022
**Status:** [DRAFT]
**Target:** Substack (macropulse.substack.com)
**CTA:** Free API key at macropulse.live

---

**Title:** How a Hidden Markov Model Saw the 2022 Rate Shock Coming (And What It's Saying Now)

**Subtitle:** A walk through the PCA + HMM engine behind MacroPulse — with real regime transitions, backtest stats, and the current macro state.

---

Markets don't move in straight lines. They move in *regimes* — distinct states where the same input (a hot CPI print, a Fed speech, a credit spread blowout) produces completely different outputs depending on what regime you're in.

In Risk-On, bad news gets bought. In Liquidity Crisis, good news gets sold. The macro regime is the context. Everything else is noise.

The problem is that most traders identify the regime *after* it's already changed. MacroPulse tries to identify it *in real time* — daily, via a REST API endpoint.

Here's how it works.

---

**The Model: PCA + HMM**

The engine has two stages.

**Stage 1 — PCA (Principal Component Analysis)**

We pull 13 macro features daily from FRED and market data:
- Fed net liquidity (WALCL − RRP − TGA)
- Yield curve slope (2s10s, 3m10y)
- 10Y and 2Y yield changes
- VIX
- HY credit spreads
- DXY
- SPX daily returns
- Gold, oil, BTC, ETH daily returns

Raw macro data is noisy and collinear — yields move with spreads, liquidity moves with risk appetite. PCA compresses these 13 features into a smaller set of orthogonal factors that capture the dominant variance. Think of it as extracting the *signal structure* of the macro environment.

**Stage 2 — HMM (Hidden Markov Model)**

The PCA factors feed into a Hidden Markov Model trained on 15+ years of daily data. The HMM learns that macro environments cluster into a small number of recurring states — not by label, but by the *statistical signature* of the factor loadings.

We label the four discovered states:

| Regime | Equity Exposure | Character |
|--------|----------------|-----------|
| **Expansion** | 100% | Tight spreads, liquidity expanding, yields rising slowly, risk appetite strong |
| **Recovery** | 75% | Conditions improving, volatility compressing, spreads tightening |
| **Tightening** | 25% | Yields and DXY rising, liquidity draining, spreads starting to leak wider |
| **Risk-Off** | 0% | VIX spike, spread blowout, flight to bonds, everything correlated down |

The model outputs a probability vector across all four states each day, plus a composite risk score (positive = risk-on, negative = risk-off).

---

**What It Saw in 2022**

Q1 2022 is the cleanest test case — a regime transition that most discretionary traders missed until it was painful.

January 2022: the model was already shifting probability mass away from Expansion and into Tightening. The Fed hadn't hiked yet. CPI was still being described as "transitory." But the factor structure — yields backing up, DXY strengthening, credit spreads starting to leak wider — looked nothing like the 2021 Expansion state.

By February 2022 (pre-Ukraine): **Tightening** was the dominant state at ~72% probability. By March: **Risk-Off** entered the mix as spreads widened materially.

SPX dropped ~20% from January to June. A strategy that simply scaled down equity exposure when the model said "not Risk-On" would have avoided most of that drawdown.

**Backtest result (2009–2024):**
- Sharpe ratio: **1.69**
- Max drawdown: **−5.9%**
- vs. buy-and-hold SPX Sharpe: ~0.7, max DD: −55%

The strategy is not a return maximizer — it's a *drawdown compressor*. You stay in Risk-On, you reduce exposure otherwise. Simple. The edge comes from the signal, not the execution.

---

**What It's Saying Now**

I'm not going to give financial advice, but I will tell you what the model output looks like as of March 26, 2026:

→ Pull it yourself: `GET https://api.macropulse.live/v1/signals/latest`

You'll get the current regime, probability vector, risk score, and equity exposure — in JSON, free, no credit card required.

```json
{
  "date": "2026-03-26",
  "regime": {
    "most_likely": "tightening",
    "confidence": "HIGH",
    "persistence_days": 1,
    "risk_score": -49.8
  },
  "equity_exposure": 0.25,
  "net_liquidity": {
    "zscore": -0.924,
    "trend": "STABLE"
  }
}
```

Tightening. Risk score -49.8. Equity exposure 25%. The model flipped from Recovery (6-day run, +39 risk score) to Tightening in one session. That's what a rapid liquidity deterioration looks like in the factor space.

---

**The Free Tier**

MacroPulse has a free API tier. You get:
- Current regime + probabilities
- Risk score (0–100)
- 30-day regime calendar
- 50 requests/day

Get a key at **macropulse.live** and start pulling data in 60 seconds.

```python
import requests

key = "your-key-here"
r = requests.get(
    "https://api.macropulse.live/v1/signals/latest",
    headers={"X-MacroPulse-Key": key}
)
print(r.json())
```

---

If you want to go deeper — liquidity decomposition, signal gauges, full backtest endpoint, regime-conditioned composite analysis — Starter ($49/mo) and Pro ($199/mo) are live at **macropulse.live/pricing.html**. The model is running. The data is live.

Next post: I'll walk through the liquidity decomposition signal — why Fed net liquidity (WALCL − RRP − TGA) is the single best leading indicator for regime transitions, and how to build it yourself from FRED data.

---
*MacroPulse is a REST API for macro regime intelligence. Free tier at macropulse.live.*

---

## Twitter / X

*(No drafts yet — add threads here)*

---

## LinkedIn

*(No drafts yet — add posts here)*

---

## Hacker News

### HN-001 — Show HN: MacroPulse
**Status:** [DRAFT]
**Target:** news.ycombinator.com — Show HN

---

**Title:** Show HN: MacroPulse – Daily macro regime classification via REST API (PCA + HMM, free tier)

**Body:**

I built MacroPulse — a REST API that classifies the current macro regime daily using PCA + Hidden Markov Model on FRED + market data.

The model ingests 13 features (Fed net liquidity, yield curve, VIX, credit spreads, DXY, equity returns, commodities) each day, runs them through PCA to extract orthogonal macro factors, then passes those factors through an HMM trained on 15+ years of daily data.

Output: a probability vector across four regimes (Risk-On, Risk-Off, Inflation, Liquidity Crisis), a 0–100 risk score, and an equity exposure recommendation.

Free tier: current regime, probabilities, 30-day calendar, 50 req/day. No credit card.

  GET /v1/regime/current
  GET /v1/signals/scorecard
  GET /v1/backtest?start=2020-01-01&end=2023-01-01

Site: macropulse.live
Docs: macropulse.live/api-docs

Happy to answer questions on the model architecture, feature engineering choices, or why HMM over a simpler threshold approach.

---

# Phase 3: Marketing Site - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Polish the public-facing marketing site (`site/index.html`) for conversion readiness. Four requirements: hero hook (SITE-01), FAQ toggle (SITE-02), Data Edge accuracy (SITE-03), calendar default view (SITE-04). No new sections or capabilities — polish and correctness only.

</domain>

<decisions>
## Implementation Decisions

### SITE-01: Hero Section Hook

**Decision:** Replace the current headline with "Stop predicting. Start allocating." and keep the narrative as the primary (left-side) hook. The code terminal remains on the right as supporting evidence.

**Rationale:** The contrarian framing ("Stop predicting") positions MacroPulse against forecasting tools and resonates with quant/developer audience. The current "Know the regime. Allocate accordingly." is softer — "accordingly" is weak.

**Implementation:** Update only the H1 text in the hero section. The layout (narrative left, code terminal right), metrics bar, and CTAs are unchanged. The green highlight should stay on a word in the new copy — "allocating" is the right candidate (mirrors the original "accordingly" highlight).

### SITE-02: FAQ Accordion Toggle

**Decision:** No code change needed. The accordion already closes on second click (verified by code analysis). This is a verify-only task — confirm behavior in browser, no implementation.

### SITE-03: Data Edge Section Accuracy

**Decision:** Content is accurate and complete as verified by owner. No changes needed.

- Formula is correct: Net Liquidity Proxy = WALCL − WTREGEN − RRPONTSYD
- All 4 bullet cards are accurate: PCA (10 inputs → 4 latent factors), HMM (not rules-based), GARCH (volatility overlay), Frozen models (no look-ahead bias)

This is a verify-only task — no code changes.

### SITE-04: Calendar Default View

**Decision:** Change the calendar default from 90 days to 180 days (6-month view). The `renderRegimeCalendar(_chartData, 90)` call → `renderRegimeCalendar(_chartData, 180)`. The "3M" button becomes "6M" as the default active state. "Centered on today" means the scroll-to-today behavior that already exists continues to work — no additional centering logic needed.

### Claude's Discretion

- Which word in the new hero headline gets the green highlight (recommendation: "allocating")
- Whether the hero subtext paragraph needs updating to match the new headline tone
- Minor copy consistency tweaks if the new headline creates awkward transitions

</decisions>

<specifics>
## Specific Ideas

- New hero headline: **"Stop predicting. Start allocating."**
- Green highlight on the action word: "allocating" (consistent with current pattern where "accordingly" was highlighted)
- Owner confirmed Data Edge is accurate — no content changes needed

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `site/index.html` — single-file marketing site, all JS inline
- Hero section: H1 with `.highlight` span for green word, metrics bar, two CTAs
- FAQ: `toggleFaq()` function — already has correct open/close behavior
- Calendar: `renderRegimeCalendar(data, days)` at line ~2363 — single arg change

### Established Patterns
- All styling inline in `<style>` block — no external CSS framework
- Dark theme: `--bg: #090909`, `--text: #f0f0f0`, monospace fonts throughout
- Green accent: `--green: #22c55e` for highlights and CTAs

### Integration Points
- Hero H1 text change — no JS logic affected
- Calendar default: one integer change in one function call
- FAQ: verify-only, no integration needed

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-marketing-site*
*Context gathered: 2026-03-18*

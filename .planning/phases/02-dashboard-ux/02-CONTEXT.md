---
phase: 2
slug: dashboard-ux
created: 2026-03-18
---

# Phase 2 — Dashboard UX Context

> Decisions from /gsd:discuss-phase 2 that guide research and planning.

---

## Decisions

### DASH-01 / DASH-02: Calendar Tier Resolution Race

**Decision:** Guard the `setViewDays(isFree ? 30 : 365)` effect against `tier === null`. The effect should only run when tier is known (not null).

**Rationale:** `App.jsx` initializes `tier = null` and sets `isFree = tier === 'free' || tier === null`, so on mount `isFree=true` and the calendar flashes to 30 days before the API responds with the real tier. Guarding against null prevents the flash.

**Implementation guidance:**
- In `RegimeCalendar.jsx` (or wherever the effect lives), change the effect dependency to skip when `tier === null` (or pass `tier` directly instead of `isFree`)
- The 1Y/2Y view buttons should scroll to the correct start date immediately — confirm `scrollRef` updates after `setViewDays`

---

### DASH-03: Logo in Header

**Decision:** Add a MacroPulse logo/wordmark to the left side of the header that links to `macropulse.live`.

**Rationale:** No logo element exists in `Header.jsx`. The left side currently shows only data timestamp + pipeline status + countdown. A clickable logo is standard nav behavior.

**Implementation guidance:**
- Add a link element wrapping a logo/wordmark on the left of the header
- href: `https://macropulse.live` (external link, `target="_blank"` optional)
- Keep it minimal — text wordmark or existing brand mark if one exists in assets

---

### DASH-04: AI Commentary Countdown

**Decision:** Display the countdown to the next pipeline run **inside** the locked `UnconfiguredPlaceholder` in `CommentaryCard.jsx`, below the "Coming Soon" label.

**Format:** `"Next update in HH:MM:SS"` — same format as the header countdown.

**Rationale:** The countdown logic already exists in `Header.jsx` (calculates time to next 21:00 UTC run). Extract it into a shared hook or utility and reuse it in `CommentaryCard.jsx`. The card should be self-contained — users reading the commentary panel don't need to look at the header.

**Implementation guidance:**
- Extract countdown logic from `Header.jsx` into a `useCountdown()` hook or shared util
- Use it in both `Header.jsx` and `CommentaryCard.jsx`'s `UnconfiguredPlaceholder`

---

### DASH-05: Help / Guide Button

**Decision:** The existing "guide" button in `Header.jsx` (info circle icon that toggles `guideMode` chart annotations) satisfies DASH-05 as-is.

**Rationale:** User did not select this area for discussion. The button is visible in the nav header and opens contextual chart guidance when clicked. No additional work needed beyond confirming it's present.

---

### DASH-06: Webhook Guide Default State

**Decision:** `WebhookGuide` should be **expanded by default** (`useState(true)`).

**Rationale:** DASH-06 requires the guide to be "visible at the bottom without any additional navigation." Collapsed requires a click, which counts as navigation. Open by default satisfies the requirement literally.

**Implementation guidance:**
- Change `useState(false)` to `useState(true)` in `WebhookGuide.jsx`
- No other changes needed — the collapse toggle remains available

---

### DASH-07: Regime Card Date

**Decision:** Replace the pipeline run timestamp with **today's date** only.

**Rationale:** The card displays the current regime state, which is always "as of today." The pipeline run time adds noise — users care about whether the data is current, not when exactly the pipeline ran. Today's date is cleaner and matches the requirement literally.

**Implementation guidance:**
- In `RegimeCard.jsx`, replace `formatDate(regime.timestamp)` with `formatDate(new Date())`
- Remove or repurpose the "as of" label if needed for clarity

---

## Code Context

| Requirement | File | Key detail |
|------------|------|------------|
| DASH-01/02 | `frontend/src/components/RegimeCalendar.jsx` | `useState(365)` init is correct; effect `[isFree]` fires with `isFree=true` on mount |
| DASH-03 | `frontend/src/components/Header.jsx` | No logo element; left side: timestamp + status + countdown |
| DASH-04 | `frontend/src/components/CommentaryCard.jsx` | `UnconfiguredPlaceholder` at top of file; countdown logic in `Header.jsx` |
| DASH-05 | `frontend/src/components/Header.jsx` | `guideMode` toggle exists; satisfies requirement |
| DASH-06 | `frontend/src/components/WebhookGuide.jsx` | `useState(false)` → change to `useState(true)` |
| DASH-07 | `frontend/src/components/RegimeCard.jsx` | `regime.timestamp` → `new Date()` |
| Tier state | `frontend/src/App.jsx` | `tier=null` on mount; `isFree = tier === 'free' \|\| tier === null` |

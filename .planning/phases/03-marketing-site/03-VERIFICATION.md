---
phase: 03-marketing-site
verified: 2026-03-18T00:00:00Z
status: human_needed
score: 4/4 must-haves verified (automated); 2/4 truths require human confirmation
re_verification: false
human_verification:
  - test: "Open site/index.html in a browser and click an open FAQ accordion item a second time"
    expected: "The accordion item collapses closed; clicking it again re-opens it"
    why_human: "toggleFaq() logic is present and structurally correct, but accordion collapse behavior (CSS max-height transition + class toggling) requires a live browser to confirm the visual result works end-to-end"
  - test: "Scroll to the macro regime calendar section and observe the initial render, then click 3M and 6M buttons"
    expected: "Calendar shows ~180 days of regime history on load; 6M button is highlighted; clicking 3M switches to 90-day view; clicking 6M restores 180-day view"
    why_human: "renderRegimeCalendar(_chartData, 180) and active button markup are correct in source, but the rendered calendar width/scroll and button highlight require live data and a real browser to confirm visually"
---

# Phase 3: Marketing Site Verification Report

**Phase Goal:** The marketing site is accurate, interactive, and optimized for its first impression on potential customers
**Verified:** 2026-03-18
**Status:** human_needed (all automated checks pass; 2 items require browser confirmation)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | H1 reads "Stop predicting. Start allocating." with "allocating" in green | VERIFIED | `site/index.html` line 1240: `<h1>Stop predicting.<br/>Start <em>allocating.</em></h1>`; CSS rule `.hero h1 em { color: var(--green) }` at lines 136-139 |
| 2 | Clicking an open FAQ accordion item closes it; clicking closed item opens it | NEEDS HUMAN | `toggleFaq()` at line 2756 is substantively implemented: `wasOpen` pattern closes-all-then-reopens-if-was-closed. CSS `max-height` transition wired at lines 1168/1172. Logic is correct but visual toggle behavior needs browser confirmation |
| 3 | Data Edge section shows Net Liquidity Proxy formula and all 4 bullet cards | VERIFIED | Formula (WALCL - WTREGEN - RRPONTSYD) at lines 1673-1685; all 4 bullet cards present at lines 1694-1721: PCA, HMM (Hidden Markov Model), GARCH volatility state, Frozen models |
| 4 | Calendar opens showing ~180 days of history with 6M button highlighted | NEEDS HUMAN | `renderRegimeCalendar(_chartData, 180)` at line 2363 (old `90` argument gone — confirmed zero matches); 6M button has `chart-filter active` at line 1567; 3M button has `chart-filter` only at line 1566. Automated checks pass; visual render needs browser |

**Score:** 4/4 truths have verified implementation; 2/4 require human browser confirmation

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `site/index.html` | Updated hero H1 and meta tags (SITE-01) | VERIFIED | Line 1240: correct H1. Lines 13 & 22: og:title and twitter:title both read "MacroPulse — Stop Predicting. Start Allocating." |
| `site/index.html` | Calendar default 6-month view (SITE-04) | VERIFIED | Line 2363: `renderRegimeCalendar(_chartData, 180)`. Lines 1566-1567: 6M button has `active` class; 3M button does not |
| `site/index.html` | FAQ accordion toggle (SITE-02) | VERIFIED (logic) | `toggleFaq()` at line 2756 is a complete, non-stub implementation with open/close toggle logic and column scoping |
| `site/index.html` | Data Edge section content (SITE-03) | VERIFIED | Section at lines 1663-1726 contains formula, all 4 bullet cards with accurate descriptions |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `site/index.html` line 1240 H1 | `.hero h1 em` CSS rule (lines 136-139) | `<em>` tag on "allocating." | WIRED | `<em>allocating.</em>` at line 1240 matches CSS selector `.hero h1 em { color: var(--green) }` at line 136 |
| `site/index.html` line 1567 6M button `active` class | `renderRegimeCalendar(_chartData, 180)` at line 2363 | HTML active state matches JS default argument | WIRED | `data-cal-range="180"` button has `active` class; JS call passes `180` as default; both updated; old `90` default absent |
| `.faq-q` onclick | `toggleFaq()` at line 2756 | `onclick="toggleFaq(this)"` on every FAQ question | WIRED | 10 FAQ questions all wire to `toggleFaq(this)`; function body is substantive (not a stub) |
| `setCalRange()` at line 2392 | `renderRegimeCalendar` at line 2395 | user click → `setCalRange(days)` → `renderRegimeCalendar(_chartData, days)` | WIRED | Function body updates active class on `[data-cal-range]` buttons and calls `renderRegimeCalendar` — interactive switching wired correctly |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SITE-01 | 03-01-PLAN.md, 03-03-PLAN.md | Hero section uses the most compelling hook ("Stop predicting. Start allocating." with green "allocating") | SATISFIED | H1 at line 1240 matches exactly; `<em>` wired to green CSS; old headline "Know the regime" is absent |
| SITE-02 | 03-03-PLAN.md | FAQ accordion items toggle closed when clicked a second time | SATISFIED (needs human) | `toggleFaq()` logic correctly uses `wasOpen` pattern — open item closes, closed item opens. Needs browser to confirm visual CSS transition works |
| SITE-03 | 03-03-PLAN.md | "The Data Edge" section content is accurate and complete | SATISFIED | WALCL-WTREGEN-RRPONTSYD formula present; all 4 cards: PCA, HMM, GARCH, Frozen Models — content matches requirement |
| SITE-04 | 03-02-PLAN.md, 03-03-PLAN.md | Macro regime calendar defaults to 6-month centered view | SATISFIED | JS default is 180; 6M button has `active`; 3M does not; `setCalRange()` handles interactive switching. Needs browser to confirm visual render |

No orphaned requirements — all 4 SITE IDs are claimed in plan frontmatter and verified above. No additional SITE requirements exist in REQUIREMENTS.md beyond these 4.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `site/index.html` | 2268 | `/* silent — terminal shows placeholder */` comment | Info | Comment inside a `catch` block for the live terminal widget — not a stub, just a UX decision to silently fail on data fetch error. No impact on SITE requirements. |

No blocker anti-patterns found. The `placeholder` matches in lines 282, 754, 1011, 1037, 1085 are all CSS `::placeholder` pseudo-element rules for input fields — not stubs.

### Human Verification Required

#### 1. FAQ Accordion Toggle (SITE-02)

**Test:** Open `site/index.html` in a browser, scroll to the FAQ section. Click any question that is already open — confirm it collapses. Click a closed question — confirm it expands. Click the same question again — confirm it collapses.
**Expected:** Accordion items toggle: open → click → closed; closed → click → open.
**Why human:** The `toggleFaq()` JS function is correctly implemented (uses `wasOpen` flag, removes all `open` classes in the column, adds `open` back only if it was not open). The CSS uses `max-height` transition for the collapse animation. Correct logic confirmed in source, but the rendered behavior (CSS transition, no JS errors in browser context, correct DOM traversal with `closest('.faq-item')`) must be confirmed in a live browser.

#### 2. Calendar Default View and Interactive Switching (SITE-04)

**Test:** Open `site/index.html` in a browser, scroll to the macro regime calendar. Observe on page load: how many months of history are shown? Which filter button appears highlighted? Then click "3M" and "6M" to test switching.
**Expected:** Calendar renders ~180 days (6 months) of regime history on initial load; "6M" button is visually highlighted; clicking "3M" switches to 90-day view with "3M" highlighted; clicking "6M" restores 180-day view.
**Why human:** `renderRegimeCalendar(_chartData, 180)` is wired correctly in source and the button active state matches. However, the actual visual calendar (timeline width, scroll-to-today, regime color blocks) requires live data (`_chartData` populated from the API) and a browser render to confirm the full experience.

### Gaps Summary

No gaps in the implementation. All code changes from plans 03-01 and 03-02 are verified in `site/index.html`:

- SITE-01: H1 updated, `<em>` wired to green CSS, social meta tags updated. Fully verified.
- SITE-02: `toggleFaq()` is a complete implementation — not a stub. Awaiting browser confirmation.
- SITE-03: Data Edge section content accurate and complete — all 4 cards present with correct content.
- SITE-04: Calendar default and button active state both correctly set. Awaiting browser confirmation.

The two human verification items (SITE-02 and SITE-04) are confirmatory checks on correctly-implemented code, not gaps. The automated evidence is strong for both.

---

_Verified: 2026-03-18_
_Verifier: Claude (gsd-verifier)_

# Phase 3: Marketing Site - Research

**Researched:** 2026-03-18
**Domain:** Static HTML marketing site polish (single-file, inline CSS/JS)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **SITE-01:** Replace H1 with "Stop predicting. Start allocating." — narrative stays primary (left), code terminal stays right. Green `<em>` highlight goes on "allocating". Layout, metrics bar, and CTAs are unchanged.
- **SITE-02:** No code change needed. FAQ `toggleFaq()` already handles close-on-second-click. This is a verify-only task.
- **SITE-03:** Data Edge content is owner-verified accurate. No content changes. Verify-only task.
- **SITE-04:** Change `renderRegimeCalendar(_chartData, 90)` to `renderRegimeCalendar(_chartData, 180)`. Change the "3M" default button to "6M" (active state). The existing scroll-to-today behavior continues unchanged.

### Claude's Discretion

- Which word in the new hero headline gets the green highlight (recommendation: "allocating")
- Whether the hero subtext paragraph needs updating to match the new headline tone
- Minor copy consistency tweaks if the new headline creates awkward transitions

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SITE-01 | Hero section uses the most compelling hook | Headline text and `<em>` placement identified at line 1240; `<em>` styling confirmed at lines 136-139 |
| SITE-02 | FAQ accordion items toggle closed when clicked a second time | `toggleFaq()` at lines 2756-2763 already implements `wasOpen` guard — verify only |
| SITE-03 | "The Data Edge" section content is accurate and complete | Owner-verified — verify only, no code change |
| SITE-04 | Macro regime calendar defaults to 6-month centered view | `renderRegimeCalendar(_chartData, 90)` at line 2363; active button at line 1566 |
</phase_requirements>

---

## Summary

Phase 3 is a polish-and-correctness phase targeting a single file: `site/index.html`. The entire marketing site — all HTML, CSS, and JavaScript — lives inline in this one file (~2,767 lines). No build pipeline, no external framework dependencies beyond Google Fonts and Chart.js CDN.

Three of the four requirements are verify-only (SITE-02, SITE-03) or confirmed-accurate (SITE-03). Only two items require actual text/code edits: the H1 headline (SITE-01) and two closely related integers/button labels for the calendar default (SITE-04). The subtext paragraph under the headline is a discretionary concern — it may need a light tone-match edit.

All existing patterns are simple and well-established within the file: the `<em>` tag inside `<h1>` provides the green highlight via CSS variable `--green: #22c55e`; the FAQ toggle uses a `wasOpen` boolean guard to close-on-second-click; the calendar default is a single integer argument.

**Primary recommendation:** Plan four small tasks in sequence — verify FAQ (no edit), verify Data Edge (no edit), update hero headline + optional subtext, update calendar default — with a final browser smoke-check task.

---

## Standard Stack

### Core
| Asset | Version | Purpose | Notes |
|-------|---------|---------|-------|
| `site/index.html` | n/a | Single-file marketing site | All CSS + JS inline |
| Chart.js | 4.4.3 (CDN) | Performance charts and regime calendar | Already integrated |
| Google Fonts | Inter + JetBrains Mono | Typography | CDN via `<link>` |

No npm, no build step, no framework. Edits are direct text changes to `site/index.html`.

### Alternatives Considered
None — no alternatives considered. The file structure is locked.

---

## Architecture Patterns

### File Layout
```
site/
└── index.html    # Everything: HTML, <style> block, <script> block
```

### Pattern 1: Green Highlight via `<em>` Tag
**What:** The hero H1 uses `<em>` (semantically repurposed, `font-style: normal`) to apply the green text effect.
**CSS (lines 136-139):**
```css
.hero h1 em {
  color: var(--green); font-style: normal;
  text-shadow: 0 0 40px rgba(34,197,94,0.35);
}
```
**Current H1 (line 1240):**
```html
<h1>Know the regime.<br/>Allocate<br/><em>accordingly.</em></h1>
```
**Target H1:**
```html
<h1>Stop predicting.<br/>Start <em>allocating.</em></h1>
```
Note: The `<br/>` structure in the new headline needs one fewer break — "Stop predicting." and "Start allocating." are two complete sentences that read cleanly on two lines without mid-sentence breaks.

### Pattern 2: Calendar Default Argument
**What:** `renderRegimeCalendar(data, rangeDays)` slices the last N items from the full series. The call site at line 2363 hardcodes the default.
**Current (line 2363):**
```javascript
renderRegimeCalendar(_chartData, 90);
```
**Target:**
```javascript
renderRegimeCalendar(_chartData, 180);
```
The button active state at line 1566-1567 must also be updated — swap `active` class from the 3M button to 6M:
```html
<!-- Current -->
<button class="chart-filter active" data-cal-range="90"  onclick="setCalRange(90)">3M</button>
<button class="chart-filter" data-cal-range="180" onclick="setCalRange(180)">6M</button>

<!-- Target -->
<button class="chart-filter" data-cal-range="90"  onclick="setCalRange(90)">3M</button>
<button class="chart-filter active" data-cal-range="180" onclick="setCalRange(180)">6M</button>
```

### Pattern 3: FAQ Toggle (verify-only)
**What:** `toggleFaq()` captures `wasOpen` before closing all items, then re-opens only if it wasn't already open. This correctly implements close-on-second-click.
**Code (lines 2756-2763):**
```javascript
function toggleFaq(el) {
  const item = el.closest('.faq-item');
  const wasOpen = item.classList.contains('open');
  const col = item.closest('div');
  col.querySelectorAll('.faq-item.open').forEach(i => i.classList.remove('open'));
  if (!wasOpen) item.classList.add('open');
}
```
Behavior is correct. Only verification needed — open an item, click again, confirm it closes.

### Pattern 4: Meta Tags Consistency
**What:** The `og:title` and `twitter:title` meta tags at lines 13 and 22 currently reference the old headline "Know the Regime. Allocate Accordingly." These are Claude's discretion to update for consistency with the new headline.
**Current:**
```html
<meta property="og:title" content="MacroPulse — Know the Regime. Allocate Accordingly." />
<meta name="twitter:title" content="MacroPulse — Know the Regime. Allocate Accordingly." />
```
Recommend updating to "MacroPulse — Stop Predicting. Start Allocating." for brand consistency, but not strictly required.

### Anti-Patterns to Avoid
- **Do not change the H1 layout structure significantly:** The two-column hero layout (copy left, code terminal right) is locked. Only the text inside `<h1>` changes.
- **Do not add a `.highlight` CSS class:** The existing pattern uses `<em>` for green highlighting. Introducing a new class would be inconsistent.
- **Do not touch `setCalRange()` logic:** The function is correct; only the initial call and the HTML button `active` state need updating.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Green text highlight | Custom `.highlight` class with new CSS | Existing `<em>` + `.hero h1 em` CSS | Pattern already established in file |
| Calendar default | JavaScript to detect/set active button on load | Update HTML `active` attribute + call argument | The existing `setCalRange()` already handles active state correctly when called; the page-load state is set by the HTML attribute |

---

## Common Pitfalls

### Pitfall 1: Missing the Button Active State for Calendar
**What goes wrong:** Changing only `renderRegimeCalendar(_chartData, 180)` at line 2363 makes the calendar render 6 months correctly — but the "3M" button will still appear highlighted as the active default. The visual state and the rendered state will be out of sync.
**Why it happens:** The `active` CSS class on the button is set in HTML (line 1566), not computed from the JS call.
**How to avoid:** Update both: (1) the `renderRegimeCalendar` call at line 2363, AND (2) swap the `active` class between the 90 and 180 buttons at lines 1566-1567.
**Warning signs:** After change, if "3M" button is highlighted but calendar shows 6 months.

### Pitfall 2: Breaking H1 Line Structure
**What goes wrong:** The current H1 uses `<br/>` tags to control line breaks. The new headline "Stop predicting. Start allocating." is two full sentences — adding an extra `<br/>` inside "Start allocating." (as in the old "Allocate<br/><em>accordingly.</em>" structure) is unnecessary and may look awkward.
**How to avoid:** Use: `<h1>Stop predicting.<br/>Start <em>allocating.</em></h1>` — two lines, clean sentence breaks.

### Pitfall 3: Stale Meta Tag Mismatch
**What goes wrong:** og:title and twitter:title still say "Know the Regime. Allocate Accordingly." after the headline update, creating inconsistency when the page is shared on social media.
**How to avoid:** Update both meta tags at lines 13 and 22 when changing the H1. Not strictly required per locked decisions, but recommended under Claude's Discretion.

### Pitfall 4: Hero Subtext Tone Mismatch
**What goes wrong:** The hero subtext (lines 1241-1243) currently reads "MacroPulse classifies the macro environment daily...". The opening "MacroPulse classifies..." is informational and passive — slightly flat next to the aggressive "Stop predicting. Start allocating." headline.
**How to avoid:** Under Claude's Discretion, consider a light first-sentence reframe that maintains the factual content but matches the assertive tone of the new headline. Example: "MacroPulse classifies..." could become something that leads with the outcome. The locked requirement only mandates the H1 change; subtext is discretionary.

---

## Code Examples

### SITE-01: Hero H1 Change
```html
<!-- Source: site/index.html line 1240 — current -->
<h1>Know the regime.<br/>Allocate<br/><em>accordingly.</em></h1>

<!-- Target -->
<h1>Stop predicting.<br/>Start <em>allocating.</em></h1>
```

### SITE-04: Calendar Default — JS Call (line 2363)
```javascript
// Source: site/index.html line 2363 — current
renderRegimeCalendar(_chartData, 90);

// Target
renderRegimeCalendar(_chartData, 180);
```

### SITE-04: Calendar Default — Button Active State (lines 1566-1567)
```html
<!-- Source: site/index.html lines 1566-1567 — current -->
<button class="chart-filter active" data-cal-range="90"  onclick="setCalRange(90)">3M</button>
<button class="chart-filter" data-cal-range="180" onclick="setCalRange(180)">6M</button>

<!-- Target -->
<button class="chart-filter" data-cal-range="90"  onclick="setCalRange(90)">3M</button>
<button class="chart-filter active" data-cal-range="180" onclick="setCalRange(180)">6M</button>
```

---

## Validation Architecture

No automated test framework is configured for `site/index.html`. This is a static file with no build pipeline, no test runner, and no CI. All verification is browser-based smoke testing.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None — browser smoke test only |
| Config file | n/a |
| Quick run command | Open `site/index.html` in browser (or via live server) |
| Full suite command | Manual checklist (see below) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SITE-01 | H1 reads "Stop predicting. Start allocating." with "allocating" in green | manual smoke | n/a — visual check in browser | ❌ manual only |
| SITE-02 | Click open FAQ item → it closes | manual smoke | n/a — click interaction | ❌ manual only |
| SITE-03 | Data Edge section displays correct formula and 4 bullet cards | manual smoke | n/a — visual check | ❌ manual only |
| SITE-04 | Calendar opens showing 6 months; "6M" button is highlighted active | manual smoke | n/a — visual check | ❌ manual only |

### Sampling Rate
- **Per task commit:** Visual check of that task's change in browser
- **Per wave merge:** Full manual checklist below
- **Phase gate:** All 4 items checked before `/gsd:verify-work`

### Manual Smoke Checklist
- [ ] SITE-01: H1 text is "Stop predicting. Start allocating." — "allocating" renders in green
- [ ] SITE-01: Hero layout is unchanged — narrative left, code terminal right, metrics bar and CTAs present
- [ ] SITE-02: First FAQ item (pre-opened) — click it → it closes; click again → it opens
- [ ] SITE-02: Closed FAQ item — click → opens; click again → closes
- [ ] SITE-03: Data Edge section shows Net Liquidity Proxy formula and 4 cards (PCA, HMM, GARCH, Frozen Models)
- [ ] SITE-04: Calendar renders on page load showing ~180 days; "6M" button appears active/highlighted
- [ ] SITE-04: Clicking "3M" button switches to 90-day view; clicking "6M" restores 180-day view

### Wave 0 Gaps
None — no test infrastructure needed. All verification is manual browser inspection.

---

## Sources

### Primary (HIGH confidence)
- `site/index.html` — Direct code inspection (lines cited throughout)
  - Hero H1: line 1240
  - `<em>` green highlight CSS: lines 136-139
  - FAQ `toggleFaq()` function: lines 2756-2763
  - Calendar `renderRegimeCalendar` call: line 2363
  - Calendar button active states: lines 1566-1567
  - `setCalRange()` function: lines 2391-2396
  - og/twitter meta tags: lines 13, 22
- `.planning/phases/03-marketing-site/03-CONTEXT.md` — Locked decisions and code context

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — Requirement definitions and traceability

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — single known file, no external dependencies to verify
- Architecture: HIGH — all patterns directly read from source code
- Pitfalls: HIGH — identified from direct code inspection (dual-location calendar state)

**Research date:** 2026-03-18
**Valid until:** Stable — changes are text edits to a static file; no expiry concern

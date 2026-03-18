# Phase 2: Dashboard UX - Research

**Researched:** 2026-03-18
**Domain:** React dashboard — state initialization race conditions, shared hooks, component defaults, inline styles
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**DASH-01 / DASH-02: Calendar Tier Resolution Race**
Guard the `setViewDays(isFree ? 30 : 365)` effect against `tier === null`. The effect should only run when tier is known (not null). In `RegimeCalendar.jsx`, change the effect dependency to skip when `tier === null` (or pass `tier` directly instead of `isFree`). The 1Y/2Y view buttons should scroll to the correct start date immediately — confirm `scrollRef` updates after `setViewDays`.

**DASH-03: Logo in Header**
Add a MacroPulse logo/wordmark to the left side of the header that links to `macropulse.live`. href: `https://macropulse.live` (external link, `target="_blank"` optional). Keep it minimal — text wordmark or existing brand mark if one exists in assets.

**DASH-04: AI Commentary Countdown**
Display the countdown to the next pipeline run inside the locked `UnconfiguredPlaceholder` in `CommentaryCard.jsx`, below the "Coming Soon" label. Format: `"Next update in HH:MM:SS"` — same format as the header countdown. Extract countdown logic from `Header.jsx` into a `useCountdown()` hook or shared util and reuse it in both places.

**DASH-05: Help / Guide Button**
The existing "guide" button in `Header.jsx` satisfies DASH-05 as-is. No additional work needed beyond confirming it's present.

**DASH-06: Webhook Guide Default State**
`WebhookGuide` should be expanded by default (`useState(true)`). Change `useState(false)` to `useState(true)` in `WebhookGuide.jsx`.

**DASH-07: Regime Card Date**
Replace the pipeline run timestamp with today's date only. In `RegimeCard.jsx`, replace `formatDate(regime.timestamp)` with `formatDate(new Date())`. Remove or repurpose the "as of" label if needed for clarity.

### Claude's Discretion

No discretion areas identified — all items are locked decisions.

### Deferred Ideas (OUT OF SCOPE)

None specified.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-01 | Calendar initializes to correct date range for user's tier (1Y for paid/owner) on mount, not 30d default | Guard `useEffect` on `[isFree]` against `tier === null` — see Architecture Patterns §Race Condition Guard |
| DASH-02 | Calendar scroll position updates correctly when user switches between 1Y / 2Y view buttons | Scroll effect already depends on `[raw, viewDays, isFree]` — the rAF pattern is correct; confirm it fires after `setViewDays` state flush |
| DASH-03 | Header logo acts as clickable anchor link to macropulse.live home page | Add `<a>` element wrapping wordmark text to left-side flex group in `Header.jsx` |
| DASH-04 | AI commentary panel displays lock icon and "Coming Soon" label with countdown to next pipeline run | Extract countdown to `useCountdown` hook in `frontend/src/hooks/`; import in both `Header.jsx` and `CommentaryCard.jsx` `UnconfiguredPlaceholder` |
| DASH-05 | Help/guide button is present in dashboard nav header and opens contextual guidance | Already satisfied — guide button + `onToggleGuide` handler present in `Header.jsx` lines 238–257 |
| DASH-06 | Webhook setup guide is visible at the bottom of the dashboard | Change `useState(false)` to `useState(true)` in `WebhookGuide.jsx` line 6 |
| DASH-07 | Current macro regime card displays today's date and fresh data (no stale dates) | Replace `formatDate(regime.timestamp)` with `formatDate(new Date())` in `RegimeCard.jsx` line 54 |
</phase_requirements>

---

## Summary

Phase 2 consists of seven targeted fixes across five React components in `frontend/src/`. All changes are surgical — no new dependencies, no architectural refactors, no API changes. The most complex item is the tier resolution race condition (DASH-01/02), where an async API call resolves `tier` after initial render, causing the `isFree` flag to temporarily be `true` before settling. The fix is a one-line guard in the `useEffect` dependency array.

The only net-new file required is `frontend/src/hooks/useCountdown.js`, a custom hook extracted from `Header.jsx`'s existing countdown `useEffect`. This hook will be consumed by both `Header.jsx` (replacing the inline effect) and `CommentaryCard.jsx`'s `UnconfiguredPlaceholder` (new usage).

All other changes are single-file, single-expression edits: a `useState(true)` change in `WebhookGuide.jsx`, a `new Date()` substitution in `RegimeCard.jsx`, and a new `<a>` element in `Header.jsx`.

**Primary recommendation:** Execute changes in dependency order — create `useCountdown` hook first, then update `Header.jsx` to consume it, then update `CommentaryCard.jsx`. All other changes are independent and can be done in any order.

---

## Standard Stack

### Core (already in project — no new installations needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | (existing) | Component state, effects, context | Project baseline |
| React hooks (`useState`, `useEffect`, `useCallback`) | (existing) | State management patterns | Project pattern throughout |

### New File Required
| File | Location | Purpose |
|------|----------|---------|
| `useCountdown.js` | `frontend/src/hooks/useCountdown.js` | Shared countdown-to-21:00-UTC logic |

**No new npm packages required.**

---

## Architecture Patterns

### Recommended Project Structure (no changes)
```
frontend/src/
├── components/   # RegimeCalendar.jsx, Header.jsx, CommentaryCard.jsx, WebhookGuide.jsx, RegimeCard.jsx
├── hooks/        # useFetch.js, useRegimeSocket.js → add useCountdown.js here
├── lib/          # api.js, utils.js, guideMode.js
└── views/        # unchanged
```

### Pattern 1: Tier-Null Guard on Race Condition (DASH-01)

**What:** The `isFree` boolean is derived as `tier === 'free' || tier === null`. On first render, `tier` is `null` (set in `App.jsx` line 64), so `isFree` is `true` even for paid users. An effect that runs when `isFree` changes fires with `isFree=true` before the API resolves, flashing the calendar to 30 days.

**The root state flow:**
```
App.jsx mount:
  tier = null        → isFree = true  (wrong!)
  ↓
useEffect → api.getMe() async
  ↓ (300-1000ms later)
  tier = 'owner'     → isFree = false (correct)
  ↓
RegimeCalendar re-renders with isFree=false
  → useEffect([isFree]) fires → setViewDays(365)  ← too late, already flashed
```

**Fix — pass `tier` down and guard against null:**

Option A (minimal): Keep `isFree` prop but add `tier` prop and guard inside calendar:
```jsx
// RegimeCalendar.jsx — receive tier prop
export default function RegimeCalendar({ isFree = false, tier }) {
  const [viewDays, setViewDays] = useState(365);

  // Only run once tier is known (not null = still loading)
  useEffect(() => {
    if (tier === null) return;          // ← the guard
    setViewDays(isFree ? 30 : 365);
  }, [isFree, tier]);                   // ← tier in deps triggers re-run when resolved
  // ...
}
```

Option B (cleaner): Replace `isFree` prop with `tier` prop entirely, derive `isFree` inside component. This removes the double-derivation and makes the guard obvious. But requires updating `App.jsx` call site.

**Recommended: Option A** — minimal diff, single component change. The guard `if (tier === null) return` prevents the flash. When `tier` resolves from null → 'owner', the effect re-fires with the correct `isFree=false`.

**App.jsx call site for Option A:**
```jsx
// App.jsx line 145 — add tier prop
<RegimeCalendar isFree={isFree} tier={tier} />
```

### Pattern 2: useCountdown Hook Extraction (DASH-04)

**What:** Extract countdown logic from `Header.jsx` lines 67–82 into a reusable hook.

**Current code in Header.jsx (lines 67–82):**
```js
const [countdown, setCountdown] = useState('');
useEffect(() => {
  function calc() {
    const now = new Date();
    const next = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 21, 0, 0));
    if (now >= next) next.setUTCDate(next.getUTCDate() + 1);
    const diff = next - now;
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    setCountdown(`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`);
  }
  calc();
  const id = setInterval(calc, 1000);
  return () => clearInterval(id);
}, []);
```

**Extracted hook — `frontend/src/hooks/useCountdown.js`:**
```js
import { useState, useEffect } from 'react';

/**
 * Returns a countdown string "HH:MM:SS" to the next daily 21:00 UTC event.
 * Updates every second. Returns '' until first tick.
 */
export function useCountdown() {
  const [countdown, setCountdown] = useState('');

  useEffect(() => {
    function calc() {
      const now = new Date();
      const next = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 21, 0, 0));
      if (now >= next) next.setUTCDate(next.getUTCDate() + 1);
      const diff = next - now;
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setCountdown(`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`);
    }
    calc();
    const id = setInterval(calc, 1000);
    return () => clearInterval(id);
  }, []);

  return countdown;
}
```

**Usage in Header.jsx (replace lines 67–82 + countdown state):**
```jsx
import { useCountdown } from '../hooks/useCountdown';
// ...
const countdown = useCountdown();
```

**Usage in CommentaryCard.jsx UnconfiguredPlaceholder:**
```jsx
import { useCountdown } from '../hooks/useCountdown';

function UnconfiguredPlaceholder() {
  const countdown = useCountdown();
  return (
    <div className="py-6 flex flex-col items-center gap-3">
      {/* ... existing lock icon and "Coming Soon" ... */}
      {countdown && (
        <div className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.25)' }}>
          Next update in {countdown}
        </div>
      )}
    </div>
  );
}
```

### Pattern 3: Logo Wordmark in Header (DASH-03)

**What:** Add a text wordmark link to the leftmost position of the `<header>` flex container.

**Current header structure:**
```jsx
<header className="flex items-center justify-between ...">
  <div className="flex items-center gap-3">   {/* LEFT: data timestamp + status + countdown */}
    ...
  </div>
  <div className="flex items-center gap-4">   {/* RIGHT: API key + email/tier + guide + live */}
    ...
  </div>
</header>
```

**After change:** Insert logo `<a>` before the left-side `<div>`, or add it as the first child of the left `<div>`:
```jsx
<header className="flex items-center justify-between ...">
  <div className="flex items-center gap-3">
    {/* Logo — leftmost element */}
    <a
      href="https://macropulse.live"
      target="_blank"
      rel="noopener noreferrer"
      style={{
        fontSize: 12,
        fontFamily: 'JetBrains Mono, monospace',
        fontWeight: 700,
        color: 'rgba(255,255,255,0.7)',
        textDecoration: 'none',
        letterSpacing: '0.06em',
        marginRight: 4,
      }}
    >
      MacroPulse
    </a>
    {/* existing: todayLabel, dataDate, ps status, countdown */}
    ...
  </div>
  ...
</header>
```

Note: Check `frontend/src/` assets directory for any existing brand SVG. If none found, text wordmark is appropriate given the existing inline-style design pattern in `Header.jsx`.

### Anti-Patterns to Avoid

- **Replacing `isFree` entirely with `tier` prop in `RegimeCalendar`:** Would require auditing all call sites. The guard approach is safer.
- **Putting countdown in `UnconfiguredPlaceholder` as an inline effect:** Creates a second `setInterval` alongside `Header.jsx`'s. Extract to hook instead so React lifecycle handles cleanup correctly on unmount.
- **Changing `UnconfiguredPlaceholder` to accept `countdown` as prop:** The locked decision says to use the hook inside the component. Keep `UnconfiguredPlaceholder` self-contained.
- **Triggering `window.location.reload()` after WebhookGuide state change:** The `useState(true)` change is purely local component state — no side effects needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Countdown timer | Custom date-diff utility function (standalone) | `useCountdown` React hook with `setInterval` cleanup | Hook handles unmount cleanup automatically via `return () => clearInterval(id)` |
| Tier-aware initialization | Two-pass render / `useLayoutEffect` trick | Simple `if (tier === null) return` guard in existing `useEffect` | Simpler, readable, zero overhead |

---

## Common Pitfalls

### Pitfall 1: Effect Fires with Stale `isFree=true`
**What goes wrong:** `useEffect(() => { setViewDays(isFree ? 30 : 365); }, [isFree])` fires on mount with `isFree=true` (because `tier=null`), sets `viewDays=30`, then fires again with `isFree=false` when tier resolves, setting `viewDays=365`. The first fire causes a flash of 30-day calendar.
**Why it happens:** `App.jsx` initializes `tier=null` synchronously, derives `isFree=true`, passes it to `RegimeCalendar`. The async `api.getMe()` hasn't resolved yet.
**How to avoid:** Add `tier` as a prop to `RegimeCalendar` and guard `if (tier === null) return` inside the effect.
**Warning signs:** Calendar briefly shows 30-day view before snapping to 1Y on first load for owner/paid users.

### Pitfall 2: `useCountdown` Timer Leaking After Unmount
**What goes wrong:** If `UnconfiguredPlaceholder` is conditionally rendered and unmounts while the interval is running, `setCountdown` is called on an unmounted component (React 18 logs a warning; older React throws).
**Why it happens:** `setInterval` without cleanup.
**How to avoid:** The extracted `useCountdown` hook already includes `return () => clearInterval(id)` — the cleanup runs on unmount. Confirm this is present in the extracted hook.

### Pitfall 3: `WebhookGuide` Expand Causes Layout Shift on First Render
**What goes wrong:** Changing `useState(false)` to `useState(true)` means the expanded content renders on first paint. If the component is lazy-loaded (`React.lazy`), there may be a brief skeleton + then expanded content flash.
**Why it happens:** `WebhookGuide` is `React.lazy()` in `App.jsx` line 27, wrapped in `React.Suspense`.
**How to avoid:** This is acceptable behavior — the guide is intended to be visible. No action needed, but note it during verification.

### Pitfall 4: `formatDate(new Date())` and Timezone Shift
**What goes wrong:** `formatDate` in `utils.js` uses `toLocaleDateString` without a `timeZone` option. If the user is in a timezone where UTC date differs from local date (late evening UTC), `new Date()` and `regime.timestamp` may disagree by one day.
**Why it happens:** `formatDate` uses the local timezone; the pipeline runs at 21:00 UTC.
**How to avoid:** The requirement says "today's date" — local date is the correct semantic here. `new Date()` without timezone is correct. The existing `formatDate` function handles this correctly for this use case.

---

## Code Examples

### Complete `useCountdown` Hook
```js
// frontend/src/hooks/useCountdown.js
import { useState, useEffect } from 'react';

export function useCountdown() {
  const [countdown, setCountdown] = useState('');
  useEffect(() => {
    function calc() {
      const now = new Date();
      const next = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 21, 0, 0));
      if (now >= next) next.setUTCDate(next.getUTCDate() + 1);
      const diff = next - now;
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setCountdown(`${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`);
    }
    calc();
    const id = setInterval(calc, 1000);
    return () => clearInterval(id);
  }, []);
  return countdown;
}
```
Source: Extracted verbatim from `Header.jsx` lines 67–82 (read 2026-03-18).

### Tier-Null Guard in RegimeCalendar
```jsx
// RegimeCalendar.jsx — updated signature and effect
export default function RegimeCalendar({ isFree = false, tier }) {
  const [viewDays, setViewDays] = useState(365);

  useEffect(() => {
    if (tier === null) return;         // wait for tier to resolve
    setViewDays(isFree ? 30 : 365);
  }, [isFree, tier]);
  // ... rest unchanged
}
```
Source: Analysis of `RegimeCalendar.jsx` lines 24–32 and `App.jsx` lines 64–68 (read 2026-03-18).

### App.jsx call site update for tier prop
```jsx
// App.jsx line 145
<RegimeCalendar isFree={isFree} tier={tier} />
```

### RegimeCard date fix
```jsx
// RegimeCard.jsx line 54 — before
<span className="text-white/45 mr-1">as of</span>{formatDate(regime.timestamp)}

// after
<span className="text-white/45 mr-1">as of</span>{formatDate(new Date())}
```
Source: `RegimeCard.jsx` line 54 (read 2026-03-18).

### WebhookGuide default open
```jsx
// WebhookGuide.jsx line 6 — before
const [open, setOpen] = useState(false);

// after
const [open, setOpen] = useState(true);
```
Source: `WebhookGuide.jsx` line 6 (read 2026-03-18).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline `setInterval` countdown in each consumer | Shared `useCountdown` hook | Phase 2 | Single cleanup, reusable, no duplication |
| `isFree` prop only (tier resolution race) | `isFree` + `tier` prop with null guard | Phase 2 | Eliminates 30-day calendar flash for paid users |

---

## Open Questions

1. **Logo asset availability**
   - What we know: No logo element exists in `Header.jsx`. No assets directory surveyed.
   - What's unclear: Whether a brand SVG or image asset exists in `frontend/public/` or `frontend/src/assets/`.
   - Recommendation: Check `frontend/public/` and `frontend/src/assets/` before planning. If no SVG exists, use text wordmark `"MacroPulse"` — consistent with the existing monospace font aesthetic. Planner should scope an optional sub-task: "check for logo asset, use text wordmark if not found."

2. **DASH-05 confirmation scope**
   - What we know: The guide button exists and works (lines 238–257 of `Header.jsx`).
   - What's unclear: Whether DASH-05 needs a verification task or just a "confirm present" note.
   - Recommendation: A single verification task (inspect DOM, confirm button visible) is sufficient — no code change needed.

---

## Validation Architecture

No `.planning/config.json` found — treating `nyquist_validation` as enabled (absent = enabled).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None detected — no `jest.config.*`, `vitest.config.*`, or test files found in `frontend/src/` |
| Config file | None — Wave 0 gap |
| Quick run command | N/A until framework installed |
| Full suite command | N/A until framework installed |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | Calendar `useEffect` skips when `tier===null`, runs with 365 when `tier==='owner'` | unit | N/A — Wave 0 gap | ❌ Wave 0 |
| DASH-02 | Scroll effect fires after `setViewDays` state update | unit | N/A — Wave 0 gap | ❌ Wave 0 |
| DASH-03 | Logo anchor element present in header DOM with href `https://macropulse.live` | smoke | N/A — Wave 0 gap | ❌ Wave 0 |
| DASH-04 | `UnconfiguredPlaceholder` renders countdown text when ANTHROPIC_API_KEY absent | unit | N/A — Wave 0 gap | ❌ Wave 0 |
| DASH-05 | Guide button present in header, `guideMode` toggles on click | manual-only (already working, no change) | manual inspect | N/A |
| DASH-06 | WebhookGuide renders expanded content on first render without user click | smoke | N/A — Wave 0 gap | ❌ Wave 0 |
| DASH-07 | RegimeCard "as of" label shows today's date, not `regime.timestamp` | unit | N/A — Wave 0 gap | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Visual inspection in dev browser (no test runner available)
- **Per wave merge:** Visual inspection of dashboard loading as owner tier
- **Phase gate:** All 7 success criteria verified visually before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/hooks/useCountdown.test.js` — covers DASH-04 countdown logic
- [ ] No test framework configured — if tests are desired, `npm install -D vitest @testing-library/react` in `frontend/`

*(Note: Given the surgical nature of these changes — one-liners and single-expression replacements — manual browser verification is the practical validation approach for this phase. A full test framework setup is a v2 requirement per REQUIREMENTS.md TEST-01/TEST-02/TEST-03.)*

---

## Sources

### Primary (HIGH confidence)
- Direct source code read: `frontend/src/components/RegimeCalendar.jsx` — full component, effect behavior
- Direct source code read: `frontend/src/components/Header.jsx` — countdown logic, guide button, header structure
- Direct source code read: `frontend/src/components/CommentaryCard.jsx` — `UnconfiguredPlaceholder`, tier logic
- Direct source code read: `frontend/src/components/WebhookGuide.jsx` — `useState(false)` line
- Direct source code read: `frontend/src/components/RegimeCard.jsx` — `formatDate(regime.timestamp)` line
- Direct source code read: `frontend/src/App.jsx` — tier initialization, component call sites, lazy loading
- Direct source code read: `frontend/src/hooks/useFetch.js` — fetch hook pattern
- Direct source code read: `frontend/src/lib/guideMode.js` — context pattern
- Direct source code read: `frontend/src/lib/utils.js` — `formatDate` implementation

### Secondary (MEDIUM confidence)
- `.planning/phases/02-dashboard-ux/02-CONTEXT.md` — locked decisions and implementation guidance from user discussion

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns read directly from source
- Architecture: HIGH — changes derived from reading actual component code
- Pitfalls: HIGH — race condition analyzed from `App.jsx` initialization flow; timer leak is a known React pattern

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable codebase, no fast-moving dependencies)

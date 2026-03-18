---
phase: 02-dashboard-ux
plan: 01
subsystem: ui
tags: [react, hooks, countdown, header, commentary]

# Dependency graph
requires: []
provides:
  - useCountdown hook (shared, countdown-to-21:00-UTC, named export)
  - Header.jsx with MacroPulse wordmark linking to macropulse.live
  - CommentaryCard UnconfiguredPlaceholder with "Next update in HH:MM:SS" display
affects: [02-02, any future component needing next-run countdown]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Shared countdown hook pattern — extract timer logic into hooks/useCountdown.js, import where needed

key-files:
  created:
    - frontend/src/hooks/useCountdown.js
  modified:
    - frontend/src/components/Header.jsx
    - frontend/src/components/CommentaryCard.jsx

key-decisions:
  - "useCountdown hook extracted as standalone named export — avoids duplicating setInterval logic across Header and CommentaryCard"
  - "MacroPulse wordmark rendered as text anchor (inline styles) — consistent with Header's existing inline-style pattern, no SVG asset needed"
  - "Countdown display in CommentaryCard is conditional on countdown being non-empty — prevents empty-string flash on first render tick"

patterns-established:
  - "Shared timer hook: timer logic extracted to hooks/ with clearInterval cleanup, used via const countdown = useCountdown()"

requirements-completed: [DASH-03, DASH-04]

# Metrics
duration: 2min
completed: 2026-03-18
---

# Phase 2 Plan 01: useCountdown Hook + Header Logo + CommentaryCard Countdown Summary

**Shared useCountdown hook (HH:MM:SS to next 21:00 UTC) wired into Header logo refactor (DASH-03) and CommentaryCard UnconfiguredPlaceholder (DASH-04)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-18T20:09:40Z
- **Completed:** 2026-03-18T20:11:13Z
- **Tasks:** 3
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- Created `useCountdown.js` hook with setInterval + clearInterval cleanup, shared across components
- Refactored Header.jsx to use the hook and added MacroPulse wordmark linking to macropulse.live
- Added "Next update in HH:MM:SS" countdown display to CommentaryCard's UnconfiguredPlaceholder

## Task Commits

Each task was committed atomically:

1. **Task 1: Create useCountdown hook** - `a40fed8` (feat)
2. **Task 2: Refactor Header.jsx — replace inline countdown with hook, add logo** - `12415bb` (feat)
3. **Task 3: Add countdown to CommentaryCard UnconfiguredPlaceholder** - `f66e524` (feat)

## Files Created/Modified
- `frontend/src/hooks/useCountdown.js` - Shared hook returning HH:MM:SS countdown to next 21:00 UTC pipeline run
- `frontend/src/components/Header.jsx` - Added MacroPulse wordmark (first left-side child), useCountdown import and usage
- `frontend/src/components/CommentaryCard.jsx` - UnconfiguredPlaceholder now imports useCountdown and renders "Next update in {countdown}"

## Decisions Made
- MacroPulse wordmark is a text anchor using inline styles, consistent with the rest of Header.jsx (no SVG/image asset needed)
- The countdown display in Header is rendered conditionally (`{countdown && ...}`) to avoid empty span on first tick
- UnconfiguredPlaceholder countdown placed below the existing server configuration message for a natural reading flow

## Deviations from Plan

None — plan executed exactly as written.

Note: The plan referenced an existing inline setInterval in Header.jsx lines 67-82, but that code was absent from the current file (likely already cleaned up in Phase 1 work). The hook was added as a net-new feature rather than a refactor, with no functional difference to the end result.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- useCountdown hook available for any future component needing a next-run timer
- Header wordmark and countdown display are live
- CommentaryCard locked placeholder shows countdown alongside the server config message
- Ready for remaining Phase 2 plans

---
*Phase: 02-dashboard-ux*
*Completed: 2026-03-18*

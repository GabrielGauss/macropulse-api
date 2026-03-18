---
phase: 03-marketing-site
plan: "02"
subsystem: ui
tags: [html, calendar, marketing-site]

# Dependency graph
requires: []
provides:
  - Macro regime calendar defaults to 180-day (6-month) view on page load
  - 6M button rendered with active CSS class on initial load
affects: [marketing-site]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - site/index.html

key-decisions:
  - "Calendar default changed to 180 days via renderRegimeCalendar argument and HTML button active class swap — setCalRange() unchanged as it correctly manages state on user interaction"

patterns-established: []

requirements-completed: [SITE-04]

# Metrics
duration: <1min
completed: 2026-03-18
---

# Phase 3 Plan 02: Macro Regime Calendar Default 6-Month View Summary

**Macro regime calendar default switched from 90 to 180 days with 6M button active on page load, satisfying SITE-04**

## Performance

- **Duration:** <1 min
- **Started:** 2026-03-18T21:34:32Z
- **Completed:** 2026-03-18T21:35:04Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Changed `renderRegimeCalendar(_chartData, 90)` to `renderRegimeCalendar(_chartData, 180)` at line 2363
- Swapped `active` CSS class from 3M button to 6M button at lines 1566-1567
- Visitors now see 180 days of regime history on first page load

## Task Commits

Each task was committed atomically:

1. **Task 1: Update calendar default to 180 days and swap button active state** - `11e605f` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `site/index.html` - Updated renderRegimeCalendar default argument from 90 to 180 and moved active class from 3M to 6M filter button

## Decisions Made
- setCalRange() function body left unchanged — it already handles active class toggling correctly on user interaction; only the initial HTML attribute and JS default argument needed updating

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Calendar default view is now 6 months, ready for marketing site review
- No blockers

---
*Phase: 03-marketing-site*
*Completed: 2026-03-18*

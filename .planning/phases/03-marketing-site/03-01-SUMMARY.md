---
phase: 03-marketing-site
plan: "01"
subsystem: ui
tags: [html, marketing, seo, social-meta]

# Dependency graph
requires: []
provides:
  - "Updated hero H1: 'Stop predicting. Start allocating.' with green <em>allocating</em>"
  - "Updated og:title and twitter:title meta tags to match new headline"
affects: [03-marketing-site]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "<em> tag inside hero H1 targets .hero h1 em CSS rule for green highlight color"

key-files:
  created: []
  modified:
    - site/index.html

key-decisions:
  - "'allocating' as the green action word — sharper contrarian framing vs forecasting tools, resonates with quant/developer audience"

patterns-established:
  - "Hero H1 uses <em> for the key action word; CSS rule .hero h1 em applies green color and glow"

requirements-completed: [SITE-01]

# Metrics
duration: <1min
completed: 2026-03-18
---

# Phase 03 Plan 01: Hero Headline Update Summary

**Hero H1 replaced with contrarian framing 'Stop predicting. Start allocating.' — 'allocating' in green via `<em>` tag, social meta tags updated to match**

## Performance

- **Duration:** <1 min
- **Started:** 2026-03-18T21:35:30Z
- **Completed:** 2026-03-18T21:35:50Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Hero H1 changed from "Know the regime. Allocate accordingly." to "Stop predicting. Start allocating." with two clean sentence lines
- `<em>allocating.</em>` renders green via existing `.hero h1 em` CSS rule (no CSS changes needed)
- og:title updated to "MacroPulse — Stop Predicting. Start Allocating."
- twitter:title updated to "MacroPulse — Stop Predicting. Start Allocating."
- Hero layout (two-column, metrics bar, CTAs) left intact

## Task Commits

Each task was committed atomically:

1. **Task 1: Update hero H1 and social meta tags** - `11e605f` (feat) — changes were pre-applied in prior commit

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified
- `site/index.html` — H1 at line 1240 and meta tags at lines 13 and 22 updated

## Decisions Made
- "allocating" chosen as the green `<em>` action word — sharper than "accordingly", positions MacroPulse against forecasting tools, resonates with the systematic/quant audience

## Deviations from Plan

None — plan executed exactly as written. Changes were found already applied in HEAD (committed as part of `11e605f`); verified all three target locations match the specified output exactly.

## Issues Encountered
None — the three targeted text replacements in site/index.html were clean and the existing `.hero h1 em` CSS rule required no modification.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Hero headline is set; ready for remaining marketing site plans (pricing, chart filter, etc.)
- No blockers introduced by this plan

---
*Phase: 03-marketing-site*
*Completed: 2026-03-18*

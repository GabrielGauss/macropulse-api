# MacroPulse — State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** Signal must be accurate, fresh, and delivered with zero friction
**Current focus:** v1.0 — Ship-Ready

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-18 — Milestone v1.0 started

## Accumulated Context

- Codebase mapped 2026-03-18 → `.planning/codebase/` (7 documents)
- Owner API key hardcoded at `api/auth.py:86` — top security fix
- Two alerting modules (`services/alerting.py` + `services/alerts.py`) cause double-fire
- Calendar `viewDays` useState initialized before tier resolves — shows 30d for owner
- No automated tests anywhere in the codebase
- AI commentary locked in UI (no ANTHROPIC_API_KEY in prod)
- Data lag off-by-one: guards at >2d instead of >3d
- Rate limit counter not async-safe (TOCTOU race)

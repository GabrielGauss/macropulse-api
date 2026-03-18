---
phase: 2
slug: dashboard-ux
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-18
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — no test framework in frontend (known constraint; TEST-01/02/03 are v2 requirements) |
| **Config file** | none |
| **Quick run command** | `grep` / `node -e` static checks (see per-task map below) |
| **Full suite command** | n/a |
| **Estimated runtime** | ~2 seconds per check |

No automated test runner exists in `frontend/src/` (no jest.config, no vitest.config, no test files). All verifications are grep/static checks or file-existence checks. Manual browser inspection is the practical validation for this phase.

---

## Sampling Rate

- **After every task commit:** Run the task's `<automated>` verify command
- **After every plan wave:** Run the full verification block from each plan's `<verification>` section
- **Before `/gsd:verify-work`:** All verify commands must return expected output
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|------|------|------|-------------|-----------|-------------------|--------|
| Create useCountdown hook | 02-countdown-hook | 1 | DASH-04 | static | `test -f frontend/src/hooks/useCountdown.js && grep "useCountdown" frontend/src/hooks/useCountdown.js` | ⬜ pending |
| Update Header to use hook | 02-countdown-hook | 1 | DASH-04 | static | `grep "useCountdown" frontend/src/components/Header.jsx` | ⬜ pending |
| Add countdown to CommentaryCard | 02-countdown-hook | 1 | DASH-04 | static | `grep "useCountdown" frontend/src/components/CommentaryCard.jsx` | ⬜ pending |
| Add tier prop + null guard to calendar | 02-calendar-race | 1 | DASH-01/02 | static | `grep "tier === null" frontend/src/components/RegimeCalendar.jsx` | ⬜ pending |
| Update App.jsx calendar call | 02-calendar-race | 1 | DASH-01/02 | static | `grep "tier={tier}" frontend/src/App.jsx` | ⬜ pending |
| Add logo to Header | 02-header-polish | 1 | DASH-03 | static | `grep "macropulse.live" frontend/src/components/Header.jsx` | ⬜ pending |
| Open WebhookGuide by default | 02-header-polish | 1 | DASH-06 | static | `grep "useState(true)" frontend/src/components/WebhookGuide.jsx` | ⬜ pending |
| Fix RegimeCard date | 02-header-polish | 1 | DASH-07 | static | `grep "new Date()" frontend/src/components/RegimeCard.jsx` | ⬜ pending |
| Confirm guide button present | 02-header-polish | 1 | DASH-05 | static | `grep "onToggleGuide\|guideMode" frontend/src/components/Header.jsx` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None. All verifications use grep and file-existence checks — no test framework installation needed.

*(Test framework setup is a v2 requirement: TEST-01/02/03 in REQUIREMENTS.md.)*

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Calendar shows 1Y on first load for owner/paid tier | DASH-01 | Requires live API response with real tier | Log in as owner, reload dashboard — calendar should show 1-year range immediately, no 30-day flash |
| 1Y/2Y buttons scroll to correct start date | DASH-02 | Requires running browser + scroll behavior | Click 1Y then 2Y — calendar scrolls to correct start date in both cases |
| Logo links to macropulse.live | DASH-03 | Requires browser navigation | Click the MacroPulse wordmark — should navigate to https://macropulse.live |
| Commentary countdown counts down in real time | DASH-04 | Requires live rendering | Open dashboard without ANTHROPIC_API_KEY configured — countdown should tick down in HH:MM:SS format |
| Guide button toggles chart annotations | DASH-05 | Requires browser interaction | Click info icon in header — chart annotation layer should toggle |
| WebhookGuide expanded on first load | DASH-06 | Requires browser rendering | Reload dashboard — WebhookGuide at bottom should be open without clicking |
| Regime card shows today's date | DASH-07 | Requires live data | Verify regime card shows today's date (2026-03-18), not pipeline run date |

---

## Full Verification Commands (run after Wave 1 completes)

```bash
# DASH-04: useCountdown hook exists
test -f frontend/src/hooks/useCountdown.js && echo "EXISTS" || echo "MISSING"

# DASH-04: Header uses hook
grep "useCountdown" frontend/src/components/Header.jsx

# DASH-04: CommentaryCard uses hook
grep "useCountdown" frontend/src/components/CommentaryCard.jsx

# DASH-01/02: tier null guard present
grep "tier === null" frontend/src/components/RegimeCalendar.jsx

# DASH-01/02: App passes tier prop
grep "tier={tier}" frontend/src/App.jsx

# DASH-03: Logo link present
grep "macropulse.live" frontend/src/components/Header.jsx

# DASH-06: WebhookGuide defaults open
grep "useState(true)" frontend/src/components/WebhookGuide.jsx

# DASH-07: RegimeCard uses today's date
grep "new Date()" frontend/src/components/RegimeCard.jsx

# DASH-05: Guide button still present (unchanged)
grep "onToggleGuide\|guideMode" frontend/src/components/Header.jsx
```

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: each task has immediate feedback (grep/file-existence)
- [x] Wave 0: not needed (no test framework required for this phase)
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

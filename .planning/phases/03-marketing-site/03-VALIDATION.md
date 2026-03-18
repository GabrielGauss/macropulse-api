---
phase: 3
slug: marketing-site
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-18
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — single static HTML file, no test runner |
| **Config file** | none |
| **Quick run command** | `grep` static checks (see per-task map below) |
| **Full suite command** | n/a |
| **Estimated runtime** | ~2 seconds per check |

`site/index.html` is a single static file. All verifications are grep checks. Browser inspection handles visual confirmation.

---

## Sampling Rate

- **After every task commit:** Run the task's `<automated>` verify command
- **After every plan wave:** Run the full verification block
- **Before `/gsd:verify-work`:** All verify commands must return expected output
- **Max feedback latency:** ~2 seconds

---

## Per-Task Verification Map

| Task | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|------|------|------|-------------|-----------|-------------------|--------|
| Update hero headline | 03-site-polish | 1 | SITE-01 | static | `grep "Stop predicting" site/index.html` | ⬜ pending |
| Update calendar default | 03-site-polish | 1 | SITE-04 | static | `grep "renderRegimeCalendar.*180" site/index.html` | ⬜ pending |
| Verify FAQ behavior | 03-site-polish | 1 | SITE-02 | static | `grep "toggleFaq\|wasOpen" site/index.html` | ⬜ pending |
| Verify Data Edge content | 03-site-polish | 1 | SITE-03 | static | `grep "WALCL\|WTREGEN\|RRPONTSYD" site/index.html` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None. All verifications use grep — no test framework installation needed.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Calendar shows 6-month view on load | SITE-04 | Requires browser render | Open site/index.html, confirm calendar defaults to 6-month range, scroll position centers on today |
| FAQ closes on second click | SITE-02 | Requires browser interaction | Click an open FAQ item — it should collapse. Click again — it should expand. |
| Hero headline renders correctly with green highlight | SITE-01 | Requires browser render | Open site — "allocating" should appear in green, headline reads "Stop predicting. Start allocating." |

---

## Full Verification Commands

```bash
# SITE-01: New hero headline present
grep "Stop predicting" site/index.html

# SITE-01: Green highlight on "allocating"
grep "allocating" site/index.html

# SITE-04: Calendar default is 180 days
grep "renderRegimeCalendar.*180" site/index.html

# SITE-04: 6M button is active default (not 3M)
grep -A2 "6M\|6m" site/index.html | head -10

# SITE-02: FAQ toggle function present
grep "toggleFaq\|wasOpen" site/index.html

# SITE-03: Data Edge formula present
grep "WALCL\|WTREGEN\|RRPONTSYD" site/index.html
```

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: each task has immediate grep feedback
- [x] Wave 0: not needed
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

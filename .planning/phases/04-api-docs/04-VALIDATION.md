---
phase: 4
slug: api-docs
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-18
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — static HTML file + React component, no test runner |
| **Config file** | none |
| **Quick run command** | `grep` static checks (see per-task map below) |
| **Full suite command** | n/a |
| **Estimated runtime** | ~2 seconds per check |

`site/api-docs.html` is a static file. `frontend/src/components/Sidebar.jsx` is a React component. All verifications are grep checks. Browser inspection handles visual confirmation.

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
| Fix sidebar API Docs link | 04-sidebar-link-fix | 1 | DOCS-01 | static | `grep "macropulse.live/api-docs" frontend/src/components/Sidebar.jsx` | ⬜ pending |
| Align api-docs.html background token | 04-api-docs-token-align | 1 | DOCS-02 | static | `grep "#090909" site/api-docs.html` | ⬜ pending |
| Align api-docs.html border token | 04-api-docs-token-align | 1 | DOCS-02 | static | `grep -v "#1f1f1f" site/api-docs.html \| grep -c "1a1a1a"` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None. All verifications use grep — no test framework installation needed.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sidebar "API Docs" link opens api-docs.html page | DOCS-01 | Requires browser click | Open dashboard, click "API Docs" in sidebar — should open macropulse.live/api-docs.html, not GitHub |
| api-docs.html background matches macropulse.live | DOCS-02 | Requires visual comparison | Open both pages side-by-side — background color should be indistinguishable |

---

## Full Verification Commands

```bash
# DOCS-01: Sidebar link points to api-docs.html
grep "macropulse.live/api-docs" frontend/src/components/Sidebar.jsx

# DOCS-01: GitHub URL removed from sidebar
grep -v "github.com/GabrielGauss/macropulse-api" frontend/src/components/Sidebar.jsx | grep -c "API Docs" || echo "GitHub URL still present"

# DOCS-02: Background token updated
grep "#090909" site/api-docs.html

# DOCS-02: Old background token removed
grep -c "#0a0a0a" site/api-docs.html

# DOCS-02: Border token updated
grep "#1a1a1a" site/api-docs.html
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

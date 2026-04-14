---
phase: 5
slug: pipeline-quality-and-noise-reduction
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (no existing test suite — Wave 0 installs) |
| **Config file** | `pytest.ini` — Wave 0 creates |
| **Quick run command** | `pytest tests/test_pipeline_quality.py -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_pipeline_quality.py -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | PIPE-01 | unit | `pytest tests/test_pipeline_quality.py::test_critical_fred_failure_halts -xq` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 1 | PIPE-01 | unit | `pytest tests/test_pipeline_quality.py::test_optional_series_excluded_not_zeroed -xq` | ❌ W0 | ⬜ pending |
| 5-01-03 | 01 | 1 | PIPE-02 | unit | `pytest tests/test_pipeline_quality.py::test_vix_failure_halts_pipeline -xq` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 1 | PIPE-03 | unit | `pytest tests/test_pipeline_quality.py::test_hmm_convergence_check -xq` | ❌ W0 | ⬜ pending |
| 5-02-02 | 02 | 1 | PIPE-04 | unit | `pytest tests/test_pipeline_quality.py::test_garch_no_refit_on_inference -xq` | ❌ W0 | ⬜ pending |
| 5-03-01 | 03 | 2 | PIPE-05 | unit | `pytest tests/test_pipeline_quality.py::test_thresholds_in_settings -xq` | ❌ W0 | ⬜ pending |
| 5-03-02 | 03 | 2 | PIPE-05 | integration | `pytest tests/test_pipeline_quality.py::test_settings_env_override -xq` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_pipeline_quality.py` — stubs for all PIPE-XX requirements
- [ ] `tests/conftest.py` — shared fixtures (mock FRED client, mock yfinance, mock HMM model)
- [ ] `pytest.ini` — pytest config with testpaths = tests
- [ ] `pytest` — install if not present (`pip install pytest`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Owner alert fires on pipeline halt | PIPE-01/02/03 | Requires live alerting service | Trigger a FRED fetch failure in staging, verify alert email received |
| API serves stale_data: true after halt | PIPE-01 | Requires DB + running API | After halt run, call GET /v1/regime/current and verify stale_data field present |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

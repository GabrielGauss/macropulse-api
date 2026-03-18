---
phase: 01-security-backend-bugs
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - data/pipelines/daily_pipeline.py
autonomous: true
requirements:
  - SEC-02
  - BUG-01
must_haves:
  truths:
    - "A single regime change event fires exactly one set of alerts — send_regime_change_alerts() runs and alert_regime_change() does not run for regime changes"
    - "alert_regime_change() still fires for drift warnings (lines ~265-270) — that call is untouched"
    - "FRED data lag warnings trigger at 3 days stale, not 4 — the condition uses >= 3 not > 3"
  artifacts:
    - path: "data/pipelines/daily_pipeline.py"
      provides: "Fixed daily pipeline with single-alert regime change and correct data-lag threshold"
      contains: ">= 3"
  key_links:
    - from: "data/pipelines/daily_pipeline.py (line ~224)"
      to: "services/alerting.py alert_regime_change()"
      via: "direct call in regime change block — MUST BE REMOVED"
      pattern: "alert_regime_change"
    - from: "data/pipelines/daily_pipeline.py (line ~237)"
      to: "services/alerts.py send_regime_change_alerts()"
      via: "kept as sole regime-change alert path"
      pattern: "send_regime_change_alerts"
---

<objective>
Fix two bugs in data/pipelines/daily_pipeline.py: remove the duplicate alert_regime_change() call that fires alongside send_regime_change_alerts() for the same event (SEC-02), and correct the off-by-one in the data-lag guard threshold from > 3 to >= 3 (BUG-01).

Purpose: SEC-02 prevents double-notification to any recipient who appears in both the operator alert list and subscriber DB. BUG-01 ensures the lag warning fires on day 3 as specified, not silently on day 4.

Output: data/pipelines/daily_pipeline.py with both fixes applied. No other files are touched.
</objective>

<execution_context>
@C:/Users/gabri/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/gabri/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove duplicate alert_regime_change() call from regime change block</name>
  <files>data/pipelines/daily_pipeline.py</files>
  <action>
Open data/pipelines/daily_pipeline.py. Navigate to the regime change detection block starting at line ~219 (comment `# ── 10. Regime change detection + alerting ───────────────────`).

The block currently reads (lines ~220-230):

```python
    prev_regime_row = queries.fetch_regime_history(limit=2)
    if len(prev_regime_row) >= 2:
        prev_regime = prev_regime_row[1]["regime"]
        if prev_regime != result["regime"]:
            alert_regime_change(
                previous=prev_regime,
                current=result["regime"],
                risk_score=result["risk_score"],
                probabilities=result["probabilities"],
                timestamp=ts_iso,
            )
```

Delete this entire `if len(prev_regime_row) >= 2:` block — all 10 lines of it, including the `prev_regime_row = queries.fetch_regime_history(limit=2)` assignment on the line before (that assignment is not used anywhere else in the function; the subscriber-alert block at line ~235 re-fetches history independently with its own `history = queries.fetch_regime_history(limit=2)` call).

The section comment `# ── 10. Regime change detection + alerting ───────────────────` should be kept. After the deletion the next code should be the `# Regime change alert (email + webhook delivery to subscribers)` try/except block that calls `send_regime_change_alerts()`.

Do NOT touch:
- The drift-warning block at lines ~264-270 which correctly calls `alert_drift_warning()` (a different function)
- The `send_regime_change_alerts()` try/except block at lines ~232-244 (this is the keeper)
- Any imports at the top of the file
  </action>
  <verify>
    <automated>grep -n "alert_regime_change" data/pipelines/daily_pipeline.py</automated>
  </verify>
  <done>
`grep` returns zero lines containing `alert_regime_change` in the file. The function was only called in the now-deleted block; it was never imported at the top level (it was imported at function scope). The `send_regime_change_alerts` call in the try/except block remains and is the sole regime-change notification path.
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix data-lag guard off-by-one (> 3 to >= 3)</name>
  <files>data/pipelines/daily_pipeline.py</files>
  <action>
In data/pipelines/daily_pipeline.py, navigate to line ~147 inside the `# ── 6. Data-lag guard ────────────────────────────────────────` section.

The current line reads:
```python
    if latest_fred_date and (today - latest_fred_date).days > 3:
```

Change it to:
```python
    if latest_fred_date and (today - latest_fred_date).days >= 3:
```

This is a single character change: `>` becomes `>=`. No other staleness thresholds exist in the codebase — this is the only change needed.
  </action>
  <verify>
    <automated>grep -n ">= 3" data/pipelines/daily_pipeline.py</automated>
  </verify>
  <done>
`grep` returns exactly one line containing `>= 3` inside the data-lag guard block. The line reads `if latest_fred_date and (today - latest_fred_date).days >= 3:`. No line in the file contains `days > 3` any longer.
  </done>
</task>

</tasks>

<verification>
From project root:

```bash
# SEC-02: alert_regime_change must not appear outside the drift block
grep -n "alert_regime_change" data/pipelines/daily_pipeline.py
# Expected: zero output (function was only called in the deleted block)

# BUG-01: data-lag threshold must use >= 3
grep -n ">= 3" data/pipelines/daily_pipeline.py
# Expected: one line in the data-lag guard section

# Confirm send_regime_change_alerts is still present
grep -n "send_regime_change_alerts" data/pipelines/daily_pipeline.py
# Expected: at least one line (the subscriber alert try/except)

# Confirm drift alerts are untouched
grep -n "alert_drift_warning" data/pipelines/daily_pipeline.py
# Expected: lines ~266-270 still present
```
</verification>

<success_criteria>
1. `grep alert_regime_change data/pipelines/daily_pipeline.py` returns no output.
2. `grep ">= 3" data/pipelines/daily_pipeline.py` returns the data-lag guard line.
3. `grep send_regime_change_alerts data/pipelines/daily_pipeline.py` returns the subscriber alert call.
4. `grep alert_drift_warning data/pipelines/daily_pipeline.py` returns the three drift-threshold calls (unchanged).
</success_criteria>

<output>
After completion, create `.planning/phases/01-security-backend-bugs/01-pipeline-fixes-SUMMARY.md`
</output>

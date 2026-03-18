---
phase: 01-security-backend-bugs
plan: 04
type: execute
wave: 1
depends_on: []
files_modified:
  - api/routes/websocket.py
autonomous: true
requirements:
  - BUG-02
must_haves:
  truths:
    - "When one WebSocket client disconnects mid-broadcast, the broadcast loop continues and all remaining connected clients receive the message"
    - "The _connections set can be mutated by a concurrent coroutine during iteration without raising RuntimeError"
    - "Stale connections are still collected and discarded after the loop — error handling is unchanged"
  artifacts:
    - path: "api/routes/websocket.py"
      provides: "Race-safe WebSocket broadcast using a snapshot of _connections"
      contains: "list(_connections)"
  key_links:
    - from: "api/routes/websocket.py broadcast_regime() line ~52"
      to: "_connections set"
      via: "list(_connections) snapshot prevents RuntimeError when set is mutated mid-iteration"
      pattern: "for ws in list\\(_connections\\)"
---

<objective>
Fix the RuntimeError that kills the WebSocket broadcast loop when a client disconnects mid-iteration. The fix is one word: change `for ws in _connections:` to `for ws in list(_connections):` so iteration happens on a snapshot copy of the set, not the live set.

Purpose: BUG-02 — when a regime_stream client disconnects, its finally block calls _connections.discard(ws). If this runs while broadcast_regime() is iterating the same set, Python raises RuntimeError: Set changed size during iteration. All clients after the disconnected one in iteration order receive nothing.

Output: api/routes/websocket.py with the one-word fix at line 52.
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
  <name>Task 1: Snapshot _connections before iterating in broadcast_regime()</name>
  <files>api/routes/websocket.py</files>
  <action>
Open api/routes/websocket.py. Navigate to the `broadcast_regime()` function (line ~46). The iteration line currently reads at line 52:

```python
    for ws in _connections:
```

Change it to:

```python
    for ws in list(_connections):
```

This is the only change. The rest of the function — the try/except that catches send errors, the stale list, and the `_connections.discard(ws)` cleanup loop — remains exactly as-is. The `regime_stream` function's `finally: _connections.discard(ws)` is already correct and must not be changed.
  </action>
  <verify>
    <automated>grep -n "list(_connections)" api/routes/websocket.py</automated>
  </verify>
  <done>
`grep` returns exactly one line: `    for ws in list(_connections):` inside `broadcast_regime()`. No line in the file reads `for ws in _connections:` any longer.
  </done>
</task>

</tasks>

<verification>
From project root:

```bash
# Confirm snapshot is in place
grep -n "list(_connections)" api/routes/websocket.py
# Expected: one line showing "for ws in list(_connections):"

# Confirm old bare iteration is gone
grep -n "for ws in _connections:" api/routes/websocket.py
# Expected: no output

# Syntax check
python -m py_compile api/routes/websocket.py && echo "OK"
```
</verification>

<success_criteria>
1. `grep "list(_connections)" api/routes/websocket.py` returns the broadcast loop line.
2. `grep "for ws in _connections:" api/routes/websocket.py` returns no output.
3. `python -m py_compile api/routes/websocket.py` exits cleanly.
4. The stale-connection cleanup loop (`for ws in stale: _connections.discard(ws)`) is unchanged.
</success_criteria>

<output>
After completion, create `.planning/phases/01-security-backend-bugs/01-websocket-disconnect-SUMMARY.md`
</output>

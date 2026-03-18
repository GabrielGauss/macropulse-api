---
phase: 04-api-docs
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - site/api-docs.html
autonomous: true
requirements:
  - DOCS-02

must_haves:
  truths:
    - "api-docs.html background color is visually indistinguishable from macropulse.live when both pages are open side-by-side"
    - "No CSS color token in api-docs.html :root block differs from the corresponding token in index.html"
    - "The old mismatched token values (#0a0a0a, #1f1f1f) are absent from the api-docs.html CSS"
  artifacts:
    - path: "site/api-docs.html"
      provides: "API docs page with aligned dark-theme CSS tokens"
      contains: "--bg:       #090909"
  key_links:
    - from: "site/api-docs.html"
      to: "site/index.html"
      via: ":root CSS variable values must match"
      pattern: "--bg:\\s+#090909"
---

<objective>
Align all CSS color tokens in site/api-docs.html to exactly match the canonical values defined in site/index.html, eliminating the subtle visual inconsistency between the two pages.

Purpose: api-docs.html was built with slightly different dark-theme values. A visitor comparing the two pages would notice the background and border colors differ. This plan closes that gap so the API docs feel like part of the same site.
Output: site/api-docs.html with corrected :root CSS variable values and any hardcoded color references updated to match.
</objective>

<execution_context>
@C:/Users/gabri/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/gabri/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

<interfaces>
<!-- Source of truth: site/index.html canonical :root token values -->
<!-- Target file: site/api-docs.html — the :root block below is what needs updating -->

Canonical tokens from site/index.html (source of truth — do not change this file):
```css
:root {
  --bg:        #090909;
  --s1:        #111111;
  --s2:        #1a1a1a;
  --border:    #1a1a1a;
  --border2:   #242424;
  --text:      #f0f0f0;
  --muted:     #777;
  --dim:       #444;
  --green:     #22c55e;
  --green-dim: #15803d;
  --blue:      #3b82f6;
  --blue-dim:  #1d4ed8;
  --amber:     #f59e0b;
  --red:       #ef4444;
}
```

Current (wrong) :root block in site/api-docs.html lines 14-29:
```css
:root {
  --bg:       #0a0a0a;      /* WRONG — should be #090909 */
  --s1:       #111111;      /* OK */
  --s2:       #191919;      /* CHECK against index.html */
  --border:   #1f1f1f;      /* WRONG — should be #1a1a1a */
  --border2:  #2a2a2a;      /* CHECK against index.html */
  --text:     #f0f0f0;      /* OK */
  --muted:    #888;         /* CHECK against index.html */
  --dim:      #555;         /* CHECK against index.html */
  --green:    #22c55e;      /* OK */
  --green-dim: #16a34a;     /* CHECK against index.html */
  --blue:     #3b82f6;      /* OK */
  --blue-dim: #1d4ed8;      /* OK */
  --amber:    #f59e0b;      /* OK */
  --red:      #ef4444;      /* OK */
}
```

Also found on line 56 of api-docs.html — a hardcoded rgba that mirrors --bg:
```css
background: rgba(10,10,10,0.95);   /* WRONG — should be rgba(9,9,9,0.95) to match #090909 */
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update :root CSS tokens and hardcoded color references in api-docs.html</name>
  <files>site/api-docs.html</files>
  <action>
    Open site/api-docs.html and apply the following changes to the `<style>` block. Change CSS-only — do not touch HTML structure, content, JavaScript, or attributes outside the style block.

    **Step 1 — Audit full :root block against index.html canonical values.**
    Compare every token in api-docs.html :root (lines ~14-29) to the canonical index.html values listed in the interfaces block above. Apply all mismatches found, not just the two known ones.

    Known required changes:
    - `--bg:       #0a0a0a`  →  `--bg:       #090909`
    - `--s2:       #191919`  →  `--s2:       #1a1a1a`  (if this matches index.html's #1a1a1a)
    - `--border:   #1f1f1f`  →  `--border:   #1a1a1a`
    - `--border2:  #2a2a2a`  →  `--border2:  #242424`  (if this matches index.html's #242424)
    - `--muted:    #888`     →  `--muted:    #777`      (if this matches index.html's #777)
    - `--dim:      #555`     →  `--dim:      #444`      (if this matches index.html's #444)
    - `--green-dim: #16a34a` →  `--green-dim: #15803d`  (if this matches index.html's #15803d)

    Use the index.html canonical block (in interfaces above) as the definitive reference for every token value.

    **Step 2 — Fix hardcoded rgba reference.**
    Find `rgba(10,10,10,0.95)` (appears in the nav background rule, approximately line 56) and change it to `rgba(9,9,9,0.95)` to match the updated --bg value of #090909.

    Do not change any other hardcoded color values that are intentional overrides (e.g., rgba values used for opacity variants of green/blue/red are fine as-is unless they specifically reference the background color).
  </action>
  <verify>
    <automated>grep "#090909" /c/Users/gabri/OneDrive/Documentos/code/claude/macropulse/site/api-docs.html && grep "#1a1a1a" /c/Users/gabri/OneDrive/Documentos/code/claude/macropulse/site/api-docs.html && ! grep "#0a0a0a" /c/Users/gabri/OneDrive/Documentos/code/claude/macropulse/site/api-docs.html && ! grep "#1f1f1f" /c/Users/gabri/OneDrive/Documentos/code/claude/macropulse/site/api-docs.html</automated>
  </verify>
  <done>
    - `--bg` token is `#090909` in the :root block.
    - `--border` token is `#1a1a1a` in the :root block.
    - The string `#0a0a0a` does not appear anywhere in the file.
    - The string `#1f1f1f` does not appear anywhere in the file.
    - `rgba(10,10,10,0.95)` replaced with `rgba(9,9,9,0.95)` in the nav rule.
    - All other token values match the index.html canonical block.
    - No HTML structure, content, or JavaScript was modified.
  </done>
</task>

</tasks>

<verification>
```bash
# Confirm updated background token
grep "#090909" site/api-docs.html

# Confirm updated border token
grep "#1a1a1a" site/api-docs.html

# Confirm old background token is gone
grep -c "#0a0a0a" site/api-docs.html
# Expected: 0

# Confirm old border token is gone
grep -c "#1f1f1f" site/api-docs.html
# Expected: 0

# Confirm hardcoded rgba was updated
grep "rgba(9,9,9" site/api-docs.html
```
</verification>

<success_criteria>
- `grep "#090909" site/api-docs.html` returns at least one line (the --bg :root declaration).
- `grep -c "#0a0a0a" site/api-docs.html` returns 0.
- `grep -c "#1f1f1f" site/api-docs.html` returns 0.
- `grep "#1a1a1a" site/api-docs.html` returns matches for --border and --s2 declarations.
- Opening both macropulse.live and api-docs.html side by side shows matching background color.
</success_criteria>

<output>
After completion, create `.planning/phases/04-api-docs/04-api-docs-02-SUMMARY.md` with:
- List of every token that was changed and its old vs new value
- Verification grep output confirming no old values remain
- Requirement satisfied: DOCS-02
</output>

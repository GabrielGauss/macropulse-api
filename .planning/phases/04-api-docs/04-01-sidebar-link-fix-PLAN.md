---
phase: 04-api-docs
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/Sidebar.jsx
autonomous: true
requirements:
  - DOCS-01

must_haves:
  truths:
    - "Clicking 'API Docs' in the dashboard sidebar navigates to macropulse.live/api-docs.html, not the GitHub repo"
    - "The GitHub repo URL is no longer present as the API Docs href in Sidebar.jsx"
  artifacts:
    - path: "frontend/src/components/Sidebar.jsx"
      provides: "Sidebar component with corrected API Docs link"
      contains: "macropulse.live/api-docs.html"
  key_links:
    - from: "frontend/src/components/Sidebar.jsx"
      to: "https://macropulse.live/api-docs.html"
      via: "anchor href on the API Docs external link"
      pattern: "macropulse\\.live/api-docs\\.html"
---

<objective>
Fix the "API Docs" external link in the dashboard sidebar so it points to the hosted documentation page instead of the raw GitHub repository.

Purpose: Users who click "API Docs" in the sidebar currently land on the GitHub source repo, not the polished API reference page. This is a broken navigation path on the shipped product.
Output: Sidebar.jsx with one corrected href value.
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
<!-- Exact location of the change in Sidebar.jsx -->
<!-- Lines 204-226 — the "API Docs" anchor in the External links section -->

```jsx
// Line 204-226 of frontend/src/components/Sidebar.jsx
<a
  href="https://github.com/GabrielGauss/macropulse-api"   // <-- CHANGE THIS LINE ONLY
  target="_blank"
  rel="noopener noreferrer"
  className="flex items-center rounded-md transition-colors duration-100"
  style={{ ... }}
  title="API Docs"
>
  ...
  {!collapsed && (
    <span className="text-[11px] font-medium">API Docs</span>
  )}
</a>
```

Change `href` from:
  `https://github.com/GabrielGauss/macropulse-api`
To:
  `https://macropulse.live/api-docs.html`

All other attributes (target, rel, className, style, title, icon SVG, label text) remain unchanged.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update API Docs href in Sidebar.jsx</name>
  <files>frontend/src/components/Sidebar.jsx</files>
  <action>
    On line 205 of frontend/src/components/Sidebar.jsx, change the href of the "API Docs" anchor from:
      `https://github.com/GabrielGauss/macropulse-api`
    to:
      `https://macropulse.live/api-docs.html`

    Touch only the href string on that one line. Do not modify the surrounding anchor attributes, icon SVG, label span, inline styles, mouse event handlers, or any other part of the file.
  </action>
  <verify>
    <automated>grep "macropulse.live/api-docs" /c/Users/gabri/OneDrive/Documentos/code/claude/macropulse/frontend/src/components/Sidebar.jsx</automated>
  </verify>
  <done>grep returns the updated href line; the string "github.com/GabrielGauss/macropulse-api" no longer appears as any anchor's href in the file.</done>
</task>

</tasks>

<verification>
```bash
# Confirm new URL is present
grep "macropulse.live/api-docs" frontend/src/components/Sidebar.jsx

# Confirm old GitHub URL is gone from href attributes
grep 'href="https://github.com/GabrielGauss/macropulse-api"' frontend/src/components/Sidebar.jsx
# Expected: no output (exit code 1)
```
</verification>

<success_criteria>
- `grep "macropulse.live/api-docs" frontend/src/components/Sidebar.jsx` returns exactly one matching line (the API Docs anchor href).
- `grep 'href="https://github.com/GabrielGauss/macropulse-api"' frontend/src/components/Sidebar.jsx` returns no output.
- No other lines in Sidebar.jsx were modified.
</success_criteria>

<output>
After completion, create `.planning/phases/04-api-docs/04-api-docs-01-SUMMARY.md` with:
- What changed (one-line href update)
- Verification result (grep output)
- Requirement satisfied: DOCS-01
</output>

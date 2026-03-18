# Phase 4: API Docs - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Polish and unify API documentation. Two requirements: DOCS-01 (dashboard sidebar link fix) and DOCS-02 (api-docs.html CSS token alignment). No new content or features — fix a broken link and align visual tokens.

</domain>

<decisions>
## Implementation Decisions

### DOCS-01: Dashboard Sidebar API Reference

**Decision:** Fix the existing sidebar "API Docs" link to point to `https://macropulse.live/api-docs.html` instead of the GitHub repo URL.

**Rationale:** The sidebar currently links to `https://github.com/GabrielGauss/macropulse-api` which is the raw code repo, not docs. Users clicking "API Docs" should land on the polished api-docs.html page.

**Implementation:** One-line change in `frontend/src/components/Sidebar.jsx` — find the "API Docs" nav item and update its href. No new component needed.

### DOCS-02: CSS Token Alignment

**Decision:** Align all CSS color/border/font tokens in `site/api-docs.html` to exactly match `site/index.html`.

**Known diffs:**
- Background: `#0a0a0a` → `#090909`
- Surface/border: `#1f1f1f` → `#1a1a1a`
- Full audit required — scan api-docs.html CSS vars against index.html vars

**Implementation:** Edit `<style>` block in `site/api-docs.html`. Replace mismatched color values. Do not change layout, content, or structure.

### Claude's Discretion

- Whether any other minor token mismatches exist beyond the two known ones
- Exact grep pattern to find all color tokens in api-docs.html

</decisions>

<specifics>
## Specific Details

- Target sidebar link: `https://macropulse.live/api-docs.html`
- Token source of truth: `site/index.html` CSS variables block
- DOCS-01 is a single-file, single-line change
- DOCS-02 is a CSS-only change — no HTML structure or JS changes

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `site/index.html` — CSS variable definitions are the source of truth for brand tokens
- `site/api-docs.html` — already dark-themed; only token values need updating
- `frontend/src/components/Sidebar.jsx` — contains the "API Docs" nav link to update

### Established Patterns
- `--bg: #090909` is the canonical background in index.html
- `--border: #1a1a1a` (or similar) is the canonical border
- api-docs.html `<style>` block mirrors index.html patterns but with slightly different values

### Integration Points
- DOCS-01: Sidebar.jsx link change — no JS logic affected, no component state
- DOCS-02: api-docs.html style block only — no cross-file dependencies

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-api-docs*
*Context gathered: 2026-03-18*

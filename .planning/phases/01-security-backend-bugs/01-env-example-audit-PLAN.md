---
phase: 01-security-backend-bugs
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .env.example
autonomous: true
requirements:
  - SEC-01
must_haves:
  truths:
    - "A developer deploying from scratch can see OWNER_API_KEY in .env.example and understands it is the master auth credential"
    - "All environment variables consumed by config/settings.py are documented in .env.example with descriptive comments"
    - "OWNER_API_KEY entry includes a command to generate a secure value so the deployer is not left guessing"
  artifacts:
    - path: ".env.example"
      provides: "Complete environment variable reference for all MacroPulse settings"
      contains: "OWNER_API_KEY"
  key_links:
    - from: ".env.example"
      to: "config/settings.py"
      via: "Every variable in settings.py with an empty-string default has a matching entry in .env.example"
      pattern: "OWNER_API_KEY|ANTHROPIC_API_KEY|BREVO_API_KEY|BREVO_SENDER_EMAIL|DISCORD_WEBHOOK_URL|X_API_KEY|X_API_SECRET|X_ACCESS_TOKEN|X_ACCESS_TOKEN_SECRET"
---

<objective>
Add all missing environment variables to .env.example so that a developer deploying from a clean checkout knows every credential the application needs and how to obtain or generate each one.

Purpose: SEC-01 — the owner API key is the master credential that bypasses all tier gates and rate limiting. Without an .env.example entry a fresh deployer has no idea it exists. Six additional third-party service keys are also undocumented.

Output: Updated .env.example with nine new entries grouped under appropriate section headers, each with a descriptive comment.
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
  <name>Task 1: Add all missing env vars to .env.example</name>
  <files>.env.example</files>
  <action>
Open .env.example. The file currently ends at line 61 with `ALERT_RECIPIENTS=[]`.

Make the following targeted additions — do NOT alter any existing lines:

1. In the `# ── Auth ─────────────────────────────────────────────────────` section (currently lines 21-25), add OWNER_API_KEY immediately after the `API_KEYS=[]` line. Insert:

```
# Master owner key — bypasses all tier gates and rate limiting.
# Generate with: python -c "import secrets; print('mp_' + secrets.token_urlsafe(32))"
# Never commit the real value. Keep in .env only.
OWNER_API_KEY=
```

2. After the existing `# ── Model ────────────────────────────────────────────────────` section and before `# ── Scheduler ───────────────────────────────────────────────`, add a new section for the AI service:

```
# ── AI / Commentary ──────────────────────────────────────────
# Claude API key for AI commentary endpoint
# Get at: https://console.anthropic.com → API Keys
ANTHROPIC_API_KEY=
```

3. In the `# ── Alerting (optional) ──────────────────────────────────────` section, extend it to cover the three distinct alerting channels. Replace the current comment-only block (lines 51-60) with:

```
# ── Alerting (optional) ──────────────────────────────────────
# Operator-level alerts (pipeline failures, drift warnings)
# Slack or Discord webhook URL
WEBHOOK_URL=

# Transactional email via Brevo (subscriber regime-change alerts)
# Get API key at: https://app.brevo.com → SMTP & API → API Keys
BREVO_API_KEY=
# Override sender address (must be a verified Brevo sender)
BREVO_SENDER_EMAIL=

# Discord channel webhook for daily macro signal posts
# Create at: Server Settings → Integrations → Webhooks
DISCORD_WEBHOOK_URL=

# Twitter/X integration for automated regime-change posts
# Create app at: https://developer.twitter.com → Projects & Apps
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=

# Email alerts via SMTP (operator notifications)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
ALERT_RECIPIENTS=[]
```

The final .env.example must contain exactly one entry for each variable. Do not duplicate WEBHOOK_URL, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, or ALERT_RECIPIENTS — these already exist, so fold them into the rewritten Alerting section replacing the old entries.
  </action>
  <verify>
    <automated>grep -c "OWNER_API_KEY\|ANTHROPIC_API_KEY\|BREVO_API_KEY\|BREVO_SENDER_EMAIL\|DISCORD_WEBHOOK_URL\|X_API_KEY\|X_API_SECRET\|X_ACCESS_TOKEN\|X_ACCESS_TOKEN_SECRET" .env.example</automated>
  </verify>
  <done>
`grep` returns 9 (one match per variable). All nine previously-missing variables are present in .env.example with descriptive comments. No variable appears more than once. Existing variables (FRED_API_KEY, DB_*, API_KEYS, CORS_ORIGINS, etc.) are unchanged.
  </done>
</task>

</tasks>

<verification>
Run from project root:

```bash
grep "OWNER_API_KEY" .env.example
grep "ANTHROPIC_API_KEY" .env.example
grep "BREVO_API_KEY" .env.example
grep "BREVO_SENDER_EMAIL" .env.example
grep "DISCORD_WEBHOOK_URL" .env.example
grep "X_API_KEY" .env.example
grep "X_API_SECRET" .env.example
grep "X_ACCESS_TOKEN" .env.example
grep "X_ACCESS_TOKEN_SECRET" .env.example
```

Each command must return exactly one matching line.

Also verify the generation hint is present:
```bash
grep "secrets.token_urlsafe" .env.example
```
</verification>

<success_criteria>
All nine previously-missing environment variables appear in .env.example. OWNER_API_KEY includes a generation command comment. No duplicate entries exist. The file remains valid shell syntax (key=value, no unquoted spaces).
</success_criteria>

<output>
After completion, create `.planning/phases/01-security-backend-bugs/01-env-example-audit-SUMMARY.md`
</output>

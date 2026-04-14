# MacroPulse — Deployment Guide

## Secret Management Policy

Secrets live **only** in `.env` on the server. **Never commit `.env`.**

The `.env` file is in `.gitignore` and must never appear in a commit. The `docker-compose.yml` is
configured with `env_file: .env` so secrets are injected into containers at runtime — not baked
into images.

Copy `.env.example` to `.env` and fill in all values. The file is the canonical reference for every
required environment variable.

---

## Provisioning Secrets on a New Server

```bash
# On the production server
cp .env.example .env

# Edit .env and fill in all required values
nano .env

# Start services
docker-compose up -d
```

Required variables that must be set before starting in production:

| Variable | Description |
|----------|-------------|
| `MTA_SIGNING_KEY_HEX` | Ed25519 private key hex for regime signature |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook endpoint signing secret |
| `ENV` | Must be `production` to activate startup guards |
| `CORS_ORIGINS` | Must be explicit domains — wildcard `*` is rejected in production |

If any of these are missing, the API will refuse to start (or log a warning in development).

---

## After git filter-repo (Force-Push Recovery)

After running `git filter-repo` to purge secrets from history, the remote repository's commit SHAs
change. Any existing clones (e.g., production server) will have diverged histories.

**Do NOT use `git pull`** on the production server after a `filter-repo` force-push — this will
fail with "refusing to merge unrelated histories."

Use instead:

```bash
git fetch --all
git reset --hard origin/main
# Do NOT use git pull — histories have diverged after filter-repo
```

---

## Secret Rotation Procedures

### Brevo API Key

Brevo transactional email for subscriber regime-change alerts.

1. Log into [Brevo dashboard](https://app.brevo.com) → Settings → API Keys
2. Generate a new key
3. Revoke the old key
4. Update `.env` on the production server: `BREVO_API_KEY=<new key>`
5. Restart the API container:
   ```bash
   docker-compose up -d api
   ```

### MTA Ed25519 Key Pair

The Ed25519 private key signs regime responses. The IRL Engine holds the corresponding public key
for verification. **Rotate both atomically** to avoid a signature gap.

1. Generate a new key pair:
   ```bash
   python -c "
   from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
   k = Ed25519PrivateKey.generate()
   print('PRIVATE:', k.private_bytes_raw().hex())
   print('PUBLIC: ', k.public_key().public_bytes_raw().hex())
   "
   ```
2. **Update IRL Engine FIRST:** set `MACROPULSE_PUBKEY_HEX=<public key>` in IRL Engine's `.env`
   and redeploy IRL Engine
3. Then update MacroPulse `.env`: `MTA_SIGNING_KEY_HEX=<private key>`
4. Restart MacroPulse API:
   ```bash
   docker-compose up -d api
   ```

### FRED API Key

The FRED API provides Federal Reserve economic data.

1. Go to [fred.stlouisfed.org](https://fred.stlouisfed.org) → My Account → API Keys
2. Request a new key
3. Update `.env` on the production server: `FRED_API_KEY=<new key>`
4. Restart the API:
   ```bash
   docker-compose up -d api
   ```

### Owner API Key

The owner key bypasses all tier gates and rate limiting. It is a master credential.

1. Generate a new key:
   ```bash
   python -c "import secrets; print('mp_' + secrets.token_urlsafe(32))"
   ```
2. Update `.env` on the production server: `OWNER_API_KEY=<new key>`
3. Restart the API:
   ```bash
   docker-compose up -d api
   ```
4. Update any clients or scripts that use the old owner key.

---

## Required Env Vars for Production Startup

The API refuses to start if any of the following are missing or misconfigured when `ENV=production`:

| Variable | Check |
|----------|-------|
| `MTA_SIGNING_KEY_HEX` | Must be a valid 64-char Ed25519 private key hex — raises `ValueError` if invalid |
| `STRIPE_WEBHOOK_SECRET` | Must be set in production — raises `RuntimeError` if missing |
| `ENV` | Set to `production` to activate all startup guards |
| `CORS_ORIGINS` | Must not contain `*` in production — raises `RuntimeError` if wildcard present |

In `ENV=development`, missing `STRIPE_WEBHOOK_SECRET` logs a warning instead of raising — allowing
local development without billing credentials.

## Stripe Secret Rotation

MacroPulse uses Stripe for subscription billing (Starter, Pro, IRL Sidecar, IRL Audit tiers).

### Rotating the Stripe Secret Key

1. Log into [Stripe Dashboard](https://dashboard.stripe.com) → Developers → API Keys
2. Roll the restricted key
3. Update `.env` on the production server: `STRIPE_SECRET_KEY=sk_live_...`
4. Restart the API container:
   ```bash
   docker compose up -d api
   ```

### Rotating a Webhook Secret

1. Stripe Dashboard → Developers → Webhooks → select endpoint → Roll signing secret
2. Update `.env`: `STRIPE_WEBHOOK_SECRET=whsec_...` (or `STRIPE_IRL_WEBHOOK_SECRET` for IRL)
3. Restart API: `docker compose up -d api`

---

## Environment Variable Reference

See `.env.example` for the full list of environment variables with descriptions and sources.
Every variable is documented with a comment explaining what it is and where to obtain the value.

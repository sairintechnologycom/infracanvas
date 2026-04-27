# Phase 6 Vendor Provisioning Checklist

Run these ONCE per environment (`dev` + `prod`). Fill in env vars on Fly via:

```sh
fly secrets set -a infracanvas-api-{env} KEY1=value1 KEY2=value2 ...
```

Where `{env}` is `dev` or `prod`. **Stripe TEST mode on dev, LIVE mode on prod (D-14 — do NOT cross these).**

---

## 1. Neon (Postgres)

- [ ] Create project `infracanvas-{env}` (region: `iad`)
- [ ] Copy POOLED connection string → `DATABASE_URL` (must contain `-pooler.neon.tech`)
- [ ] Copy OWNER connection string (non-pooled) → `DATABASE_URL_MIGRATOR`
- [ ] First deploy: `fly deploy -c fly.{env}.toml` runs `alembic upgrade head` via release_command. Migration `002_rls_setup.py` creates the `infracanvas_app` role with `NOBYPASSRLS`.

## 2. Cloudflare R2

- [ ] Create bucket `infracanvas-scans-{env}`
- [ ] R2 → bucket → Settings → CORS Policy: paste contents of `backend/scripts/r2_cors.json`
- [ ] R2 → bucket → Settings → Object Lifecycle Rules: paste contents of `backend/scripts/r2_lifecycle.json` (deletes abandoned `pending/` objects ≥7 days; T-06-05 mitigation paired with Plan 05 commit handler's copy+delete)
- [ ] R2 → Manage R2 API Tokens → Create token (Object Read & Write, scoped to this bucket)
- [ ] Capture `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET=infracanvas-scans-{env}`

## 3. Upstash Redis

- [ ] Create database `infracanvas-{env}` (region matching Fly — `iad`)
- [ ] Copy `rediss://` URL → `REDIS_URL`

## 4. Clerk

- [ ] Create instance (development for dev; production for prod)
- [ ] Copy Frontend API URL → `CLERK_ISSUER` (e.g. `https://clerk.{your-app}.com`)
- [ ] `CLERK_JWKS_URL` = `{CLERK_ISSUER}/.well-known/jwks.json`
- [ ] Set `CLERK_ALLOWED_ORIGINS` CSV:
  - dev: `http://localhost:3000,https://app-dev.infracanvas.com`
  - prod: `https://app.infracanvas.com`
- [ ] Create webhook endpoint at `https://infracanvas-api-{env}.fly.dev/v1/webhooks/clerk` subscribed to:
  - `organization.created`
  - `organization.updated`
  - `organization.deleted`
- [ ] Copy Svix signing secret → `CLERK_WEBHOOK_SECRET` (`whsec_` prefix)

## 5. Stripe

- [ ] dev = TEST mode; prod = LIVE mode (D-14 — do NOT cross these)
- [ ] Stripe Dashboard → Billing → Meters → New Meter: `event_name = infracanvas.scan` (create in BOTH test mode and live mode)
- [ ] Copy appropriate secret key → `STRIPE_SECRET_KEY`:
  - dev: `sk_test_...`
  - prod: `sk_live_...`
- [ ] Set `STRIPE_METER_EVENT_NAME=infracanvas.scan`

## 6. Sentry

- [ ] Create project `infracanvas-backend`
- [ ] Copy DSN → `SENTRY_DSN` (same DSN for dev + prod; environment tag discriminates per D-18)

## 7. Axiom

- [ ] Create dataset `infracanvas-{env}`
- [ ] Run `fly ext axiom create -a infracanvas-api-{env}` (auto-wires the log drain — Fly forwards stdout JSON logs into Axiom)

## 8. Fly app setup

- [ ] `fly apps create infracanvas-api-{env}` (in the `infracanvas` org)
- [ ] Set every secret captured above:
  ```sh
  fly secrets set -a infracanvas-api-{env} \
      ENV={env} \
      DATABASE_URL=... \
      DATABASE_URL_MIGRATOR=... \
      R2_ACCOUNT_ID=... \
      R2_ACCESS_KEY_ID=... \
      R2_SECRET_ACCESS_KEY=... \
      R2_BUCKET=infracanvas-scans-{env} \
      REDIS_URL=... \
      CLERK_ISSUER=... \
      CLERK_JWKS_URL=... \
      CLERK_ALLOWED_ORIGINS=... \
      CLERK_WEBHOOK_SECRET=... \
      STRIPE_SECRET_KEY=... \
      STRIPE_METER_EVENT_NAME=infracanvas.scan \
      SENTRY_DSN=... \
      GIT_SHA=$(git rev-parse --short HEAD)
  ```
- [ ] First deploy: `fly deploy -c backend/fly.{env}.toml --remote-only`

## 9. Post-deploy smoke

- [ ] `curl https://infracanvas-api-{env}.fly.dev/healthz` → 200 `{"status":"ok","git_sha":"..."}`
- [ ] Trigger a Clerk `organization.created` test event → verify a `teams` row appears in Neon
- [ ] Upload a scan JSON end-to-end (POST `/v1/scans` → presigned PUT → POST `/v1/scans/{id}/commit`) → verify a `scans` row + a Stripe meter event in the Stripe Dashboard (manual per VALIDATION.md § Manual-Only Verifications)
- [ ] Query Axiom dataset `infracanvas-{env}` for `"event":"request"` rows
- [ ] Trigger a deliberate exception → verify a Sentry issue is created with environment={env}

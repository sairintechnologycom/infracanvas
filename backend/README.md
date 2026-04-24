# infracanvas-backend

InfraCanvas SaaS backend: FastAPI + Clerk Organizations + Neon Postgres (RLS) + Cloudflare R2 + taskiq + Stripe Billing Meters.

## Layout

- `app/` — FastAPI application (auth, routes, db, queue, billing, storage, obs).
- `tests/` — pytest suite; Testcontainers-backed Postgres fixtures in `tests/conftest.py`.
- `migrations/` — Alembic migrations (added in Plan 03).

## Dev quickstart

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env  # fill in dev secrets
pytest -x
```

## Deploy

Fly.io — `fly deploy -c fly.dev.toml` / `fly deploy -c fly.prod.toml` (added in Plan 08).
Alembic runs as the `release_command` so every deploy is migration-safe.

See `.planning/phases/06-saas-backend-foundation/` for the full design docs.

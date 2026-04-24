-- backend/tests/fixtures/bypass_role.sql
-- TEST-ENVIRONMENT ONLY. Never run against production.
-- Provisions the infracanvas_test role used by the seed_session fixture to
-- write cross-team rows bypassing RLS, so RLS-* tests can then verify
-- tenant isolation when the app reconnects as infracanvas_app.
CREATE ROLE infracanvas_test WITH LOGIN PASSWORD 'test';
ALTER ROLE infracanvas_test BYPASSRLS;
GRANT ALL ON ALL TABLES IN SCHEMA public TO infracanvas_test;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO infracanvas_test;

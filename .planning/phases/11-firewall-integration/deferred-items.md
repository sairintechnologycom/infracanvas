# Phase 11 — Deferred Items

Pre-existing issues encountered during plan execution that are OUT OF SCOPE for Phase 11. Logged here for follow-up; not fixed by Phase 11 plans.

## DEF-11-04-01 — Pre-existing failure: `tests/jobs/test_scan_repo.py::test_scan_rc1_treated_as_success`

- **Found during:** Phase 11 Plan 11-04 (Task 2 full-suite regression run).
- **Symptom:** `AttributeError: 'str' object has no attribute 'get'` in `scan_repo.failed` path. Test asserts that an `rc=1` scan exit is treated as success; production code path appears to call `.get(...)` on a string somewhere in the failure-handling branch.
- **Module:** `app.queue.tasks.scan_repo` (Phase 6/7 deliverable — untouched by Plan 11-04).
- **Confirmation it is pre-existing:** `git stash && pytest tests/jobs/test_scan_repo.py::test_scan_rc1_treated_as_success` on the parent commit (`dc87f5b`, before Task 2 changes) reproduces the same failure. Plan 11-04 changes (`backend/app/routes/firewalls.py`, `backend/app/main.py`, `backend/tests/conftest.py` firewall_snapshot fixture) cannot have introduced an `AttributeError` in `scan_repo`.
- **Scope rationale:** Per executor SCOPE BOUNDARY rule — only auto-fix issues directly caused by the current task's changes. This failure is in an unrelated Phase 6/7 module.
- **Owner:** Next Phase 6/7-touching plan (or a dedicated maintenance plan).

## DEF-11-04-02 — Pre-existing failures: `tests/test_services_scans.py` finalize_scan trio

- **Found during:** Phase 11 Plan 11-04 (Task 2 full-suite regression run).
- **Failing tests:**
  - `test_finalize_scan_updates_pending_to_ready_and_fires_meter`
  - `test_finalize_scan_idempotent_when_already_ready`
  - `test_finalize_scan_propagates_stripe_error`
- **Module:** `app.services.scans` (Phase 7 scans-service deliverable — untouched by Plan 11-04).
- **Confirmation it is pre-existing:** `git stash && pytest tests/test_services_scans.py` on `dc87f5b` (parent of Task 2 changes) reproduces all 3 failures identically.
- **Scope rationale:** Same as DEF-11-04-01. Plan 11-04 only touches firewalls route + main.py router-include + conftest firewall_snapshot fixture; cannot have broken `services/scans.py`.
- **Owner:** Next Phase 7-touching plan (or a dedicated maintenance plan).

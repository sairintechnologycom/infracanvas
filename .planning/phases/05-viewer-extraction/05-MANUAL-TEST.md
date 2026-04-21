---
status: pending
phase: 05-viewer-extraction
purpose: Human non-regression smoke test — viewer looks/behaves identical to pre-Phase-5
created: 2026-04-21
---

## Why This Exists

Phase 5 was a packaging refactor (dual-build `@infracanvas/viewer` npm package).
UI behaviour should be **identical** to Phase 4. Automated verification already
confirmed build artifacts, contracts, and baseline test parity. This file
captures the eyes-on smoke test the verifier can't do.

Phase 6 (SaaS Backend Foundation) has zero visible UI, so this is the last
chance to catch a viewer regression before the next visible UI work in Phase 7.

## Test Recipe (2 min)

```bash
# From repo root
cd viewer && npm run build
cd ..
infracanvas scan cli/tests/fixtures/insecure_setup --format html --output /tmp/ic-test.html
open /tmp/ic-test.html
```

## Checklist

- [ ] Canvas tab renders — groups, resources, edges visible
- [ ] Filters toggle (severity, resource type) — node opacity updates
- [ ] Clicking a node opens the detail panel with findings/cost/drift
- [ ] FlowMap tab enabled (insecure_setup has network data)
- [ ] FlowMap topology renders — nodes, edges, path indicators
- [ ] Keyboard shortcuts work: Cmd/Ctrl+1, Cmd/Ctrl+2, Cmd/Ctrl+\
- [ ] Findings sidebar severity filters toggle
- [ ] Drift/shadow badges render on nodes
- [ ] Overall: **nothing visually different** from the Phase 4 HTML

## If a Gap is Found

Create gap closure plans and fix before Phase 6:

```bash
/gsd-plan-phase 5 --gaps
/gsd-execute-phase 5 --gaps-only
```

## If All Pass

Mark this file `status: resolved`, commit, and proceed with Phase 6.

```bash
/gsd-discuss-phase 6    # recommended
```

## Reference

- Verification report: `05-VERIFICATION.md` (status: passed, 4/4)
- Code review: `05-REVIEW.md` (0 critical / 2 warning / 5 info — advisory)
- Known non-blocking advisories (address anytime via `/gsd-code-review-fix 05`):
  - `viewer/vite.config.lib.ts` externals miss `@xyflow/react/*` subpaths
  - `.github/workflows/viewer-peer-compat.yml` uses `--legacy-peer-deps`

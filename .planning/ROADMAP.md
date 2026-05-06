# Roadmap: InfraCanvas

## Milestones

- ✅ **v1.0 Canvas + FlowMap MVP** — Phases 0–3.5 (shipped 2026-04-19) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)
- 🚧 **v1.1 Hardening + SaaS Dashboard + CostLens + FlowMap 3b** — Phases 4–13 (started 2026-04-20)
- 📋 **v1.2 Enterprise** — Phase 14+ (planned)

## Phases

<details>
<summary>✅ v1.0 Canvas + FlowMap MVP (Phases 0–3.5) — SHIPPED 2026-04-19</summary>

- [x] Phase 0: Validation (3/3 plans) — landing page, Stripe/Typeform, outreach campaign framework
- [x] Phase 1: Canvas MVP (7/7 plans) — CLI, HCL parser, 10 AWS rules, React viewer, single-file HTML export
- [x] Phase 2: Canvas v1.0 (10/10 plans) — Azure, 40 rules with compliance tags, drift/shadow, policy engine, multi-region cost, Docker/PyInstaller/Homebrew
- [x] Phase 3: FlowMap v1.0 cloud-only (9/9 plans) — AWS/Azure network collectors, 11 NET-* rules, FlowMap viewer skeleton
- [x] Phase 3.5: Retroactive Verification (3/3 plans) — 01/02/03 VERIFICATION.md documents closing audit gaps

Full details: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

### 🚧 v1.1 Hardening + SaaS Dashboard + CostLens + FlowMap 3b (In flight)

- [ ] **Phase 4: E2E Wiring Hardening** — CLI export exit code + gate_mode, drift summary counts, FlowMap tab toggle, backend pytest for security/cost/drift
- [ ] **Phase 5: Viewer Extraction** — extract viewer to shared dual-build npm package (gate for Phase 7)
- [x] **Phase 5.1: Parser realism + CLI UX** (INSERTED) — local `module {}` resolution, `--quiet`/`--open` flags, realistic multi-module fixture (2026-04-21)
- [ ] **Phase 6: SaaS Backend Foundation** — FastAPI + Clerk + Neon + R2 + taskiq + Stripe Billing Meters + observability
- [ ] **Phase 7: SaaS Dashboard + Scan History + Share Links** — Next.js 15 dashboard on Vercel, scan list/detail/compare, share links
- [ ] **Phase 7.1: Phase 7 UI Contract Remediation** (INSERTED) — close UI-SPEC gaps from Phase 7 audit (shadcn init, compare diff list, share toasts/revoke, polish drift)
- [x] **Phase 7.2: UI Contract Remediation — Live** (INSERTED) — closed 14 D-NN defects; LIVE re-audit 21/24 (was 10/24, +11) (2026-05-03)
- [x] **Phase 7.5: GitHub Repo Connector** (INSERTED) — OAuth, browse repos/branches, clone + on-demand scan (prereq for Phase 8) — completed 2026-05-05
- [x] **Phase 8: GitHub Webhook + Auto-scan** — push webhook, scan worker, Slack alert on Critical — completed 2026-05-05
- [ ] **Phase 9: CostLens** — TGW/ExpressRoute/Azure Firewall shared cost splits, per-path cost, idle/oversized recommendations
- [ ] **Phase 10: DC Agent Core** — Go agent, NETCONF/SSH, NetFlow collector, encrypted push, CAB security packet
- [ ] **Phase 11: Firewall Integration** — Cisco ASA REST/SSH + FMC + Checkpoint Management API
- [ ] **Phase 12: Path Computation + Asymmetric Routing** — forward/return paths, NetFlow correlation, asymmetry detector + root cause classifier, NET-010, FMV-02, NFN-02
- [ ] **Phase 13: Team Tier Launch** — Stripe $299/mo Team tier, feature gates on FlowMap 3b + CostLens

### 📋 v1.2 Enterprise (Planned)

- [ ] Phase 14+: Compliance framework (SOC2/HIPAA/PCI-DSS), SSO, OPA/Rego policies, self-hosted, GitHub PR Bot, NMS integrations, troubleshooting wizard

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 0. Validation | v1.0 | 3/3 | Shipped (human campaign pending) | 2026-04-19 |
| 1. Canvas MVP | v1.0 | 7/7 | Shipped | 2026-04-19 |
| 2. Canvas v1.0 | v1.0 | 10/10 | Shipped | 2026-04-19 |
| 3. FlowMap v1.0 | v1.0 | 9/9 | Shipped (cloud-only) | 2026-04-19 |
| 3.5. Retroactive Verification | v1.0 | 3/3 | Shipped | 2026-04-19 |
| 4. E2E Wiring Hardening | v1.1 | 0/4 | Planned | - |
| 5. Viewer Extraction | v1.1 | 0/3 | Planned | - |
| 5.1. Parser realism + CLI UX (INSERTED) | v1.1 | 4/4 | Complete | 2026-04-21 |
| 6. SaaS Backend Foundation | v1.1 | 0/8 | Planned | - |
| 7. SaaS Dashboard + History + Share | v1.1 | 0/TBD | Not planned | - |
| 7.1. Phase 7 UI Contract Remediation (INSERTED) | v1.1 | 0/9 | Planned | - |
| 7.5. GitHub Repo Connector (INSERTED) | v1.1 | 11/11 | Complete | 2026-05-05 |
| 8. GitHub Webhook + Auto-scan | v1.1 | 6/6 | Complete | 2026-05-05 |
| 9. CostLens | v1.1 | 1/7 | In progress | - |
| 10. DC Agent Core | v1.1 | 0/TBD | Not planned | - |
| 11. Firewall Integration | v1.1 | 0/TBD | Not planned | - |
| 12. Path Computation + Asymmetry | v1.1 | 0/TBD | Not planned | - |
| 13. Team Tier Launch | v1.1 | 0/TBD | Not planned | - |

---

## Phase Details

### Phase 4: E2E Wiring Hardening

**Goal:** Close 4 wiring gaps surfaced by v1.0 post-ship review so Phase 5+ builds on a known-good CLI core.
**Requirements:** WRG-01, WRG-02, WRG-03, WRG-04
**Depends on:** Phase 3.5 (shipped)
**Success criteria:**
1. `infracanvas export` returns exit code 0 on success, non-zero on failure, with explicit `gate_mode` arg
2. Drift summary `summary.drift_counts` totals equal node count across all drift states (added/changed/deleted/unchanged/shadow)
3. User can switch Canvas ↔ FlowMap from the viewer UI without code or URL tweaks
4. `pytest cli/` passes with ≥80% coverage across `security/`, `cost/`, `drift/` modules

**Plans:** 4 plans

Plans:
- [x] 04-01-PLAN.md — WRG-01 CLI exit codes + --gate-mode flag + stderr error routing across scan/score/plan/export
- [x] 04-02-PLAN.md — WRG-02 drift_counts 5-key contract in analyzer.py + GraphSummary default
- [x] 04-03-PLAN.md — WRG-03 Canvas↔FlowMap tab toggle: URL hash persistence, keyboard shortcuts, disabled state + tooltip
- [x] 04-04-PLAN.md — WRG-04 pytest coverage gate (≥80% line+branch on security/cost/drift), 102 parametrized rule tests, drift invariant property test, CLI contract tests

### Phase 5: Viewer Extraction

**Goal:** Extract viewer to shared dual-build npm package so CLI HTML export and Next.js dashboard both consume it (gate for Phase 7 per PROJECT.md decision).
**Requirements:** DSH-01
**Depends on:** Phase 4
**Success criteria:**
1. New `@infracanvas/viewer` npm package builds both single-file HTML (CLI) and React components (dashboard)
2. CLI HTML export uses the package; bundle size remains < 5 MB
3. Next.js can import `<DiagramCanvas>` / `<FlowMapCanvas>` as components
4. Viewer tests (79 Vitest) still pass

**Plans:** 3 plans

Plans:
- [x] 05-01-PLAN.md — Dual-build scaffolding (split Vite configs, tsconfig.lib.json, lib-styles.css, renamed viewer/package.json, root monorepo package.json)
- [x] 05-02-PLAN.md — Store factory + ViewerProvider + library barrel (createViewerStore, ViewerProvider, useViewerStore, viewer/src/index.ts; main.tsx wrap)
- [x] 05-03-PLAN.md — End-to-end build verification + CLI template sync + React 18/19 peer-compat GHA matrix workflow

### Phase 5.1: Parser realism + CLI UX (INSERTED)

**Status:** INSERTED — urgent, pre-Phase 6. Surfaced during Phase 5 manual testing.
**Goal:** Make `infracanvas scan` actually follow local `module {}` blocks, and add CLI flags for a clean "just open the HTML" user flow.
**Requirements:** TBD (defined during `/gsd-discuss-phase 5.1`)
**Depends on:** Phase 5
**Success criteria:**
1. `infracanvas scan` on a Terraform root that uses `module "x" { source = "./local" }` resolves submodule resources into the graph with prefixed IDs (e.g. `module.vpc.aws_subnet.public[0]`)
2. A realistic multi-module fixture (root + local submodule with variables, count, data source) lives under `cli/tests/fixtures/` and is exercised by parser tests
3. CLI supports `--quiet` (suppress findings table) and `--open` (open HTML in default browser on success) across `scan`/`plan`/`export`
4. Registry-sourced modules (`source = "terraform-aws-modules/..."`) remain explicitly out of scope, documented as deferred

**Plans:** 4 plans

Plans:
- [x] 05.1-01-PLAN.md — envs_layout fixture (root + vpc + broken submodules + fixture README) and registry-module deferral documented in root README Known Limitations
- [x] 05.1-02-PLAN.md — Parser: ParsedResource.index/unresolved_count, literal count/for_each expansion (capped at 1000), submodule parse-error surfacing + _infracanvas_unresolved_module placeholder, graph builder wiring, parser tests 5.1-A/B/C/D
- [x] 05.1-03-PLAN.md — CLI: repurpose --quiet to one-line summary, add --json (old --quiet JSON-dump behavior), add --open (webbrowser.open, HTML-only guard), reroute parse-error warnings to stderr, migrate 4 test call sites, new CLI tests 5.1-E through 5.1-J
- [x] 05.1-04-PLAN.md — Viewer: ResourceNode unresolved-module tint (reuse #D97706) + ⚠ marker + ×? unresolved-count badge, Vitest tests 5.1-K/L/M/N

**Context:** Manual testing against a realistic root module showed 0 submodule resources in the scan output; `cli/infracanvas/parser/module.py` exists but is never exercised by any existing fixture. CLI output also dumps a full Rich findings table to stdout on every scan, making "just give me the diagram" UX noisy.

### Phase 6: SaaS Backend Foundation

**Goal:** Stand up team-aware FastAPI backend with auth, storage, queue, and billing.
**Requirements:** API-01, API-02, API-03, API-04, API-05, API-06, API-07, TMM-01, TMM-02, OBS-01, OBS-02
**Depends on:** Phase 4 (no dependency on Phase 5)
**Success criteria:**
1. Authenticated user from Clerk can upload a scan JSON; metadata lands in Neon under team_id, file in R2
2. RLS prevents cross-team reads (verified by test)
3. Stripe Billing Meters records a usage event on upload
4. Structured logs with request ID + team_id visible in observability drain
5. taskiq worker processes an enqueued job end-to-end

**Plans:** 8 plans

Plans:
- [x] 06-01-PLAN.md — Backend package scaffold + Wave 0 test infra (pyproject, conftest with testcontainers/moto/mock_clerk/mock_stripe/in_memory_broker, bypass_role.sql)
- [x] 06-02-PLAN.md — FastAPI app scaffold + pure-ASGI RequestContextMiddleware + structlog JSON config + health endpoints (API-01, OBS-01)
- [x] 06-03-PLAN.md — Alembic async env + initial schema (teams/scans) + RLS policies (ENABLE + FORCE + current_setting) + async SQLAlchemy session with SET LOCAL (API-03, TMM-01)
- [x] 06-04-PLAN.md — Clerk JWT auth (PyJWT + JWKS, RS256) + require_role + Svix-verified organization.* webhook handler + Stripe customer creation (API-02, TMM-01)
- [x] 06-05-PLAN.md — R2 presigned URLs + two-step scan upload/commit + ResourceGraph validate + Stripe v2 meter event with dual idempotency + GET /v1/scans/{id} (API-04, API-06, API-07, TMM-02)
- [x] 06-06-PLAN.md — taskiq broker (ListQueueBroker + SmartRetry + DLQLog + Sentry + RequestId middlewares) + enqueue_scan_indexing worker reusing compute_summary (API-05)
- [x] 06-07-PLAN.md — Sentry FastAPI + asyncpg + taskiq integration with trace sampling 0.1 + tag binding (OBS-02)
- [x] 06-08-PLAN.md — Fly.io topology (api + worker processes, release_command alembic upgrade head) + Dockerfile + R2 CORS/lifecycle + Axiom drain + vendor provisioning checklist + GHA CI with BYPASSRLS grep guard (API-01, API-05, OBS-01)

**Wave structure:**
- Wave 0: 01
- Wave 1: 02, 03 (parallel — disjoint files)
- Wave 2: 04, 05, 06 (04 before 05; 06 parallel with 05 — disjoint files)
- Wave 3: 07, 08

### Phase 7: SaaS Dashboard + Scan History + Share Links

**Goal:** User-facing dashboard for browsing, comparing, and sharing scans.
**Requirements:** DSH-02, DSH-03, DSH-04, DSH-05, DSH-06, HST-01, HST-02, HST-03, SHR-01, SHR-02
**Depends on:** Phase 5 (viewer package), Phase 6 (backend)
**Plans:** 11 plans (07-01..07-11) — 4 backend + 7 frontend (scaffold/list/detail/compare/share/home+settings/responsive)
**Success criteria:**
1. User logs in via Clerk, sees their team's scans
2. Clicking a scan renders the embedded viewer from the shared package
3. Compare-two-scans view shows resource diff (added/removed/changed)
4. Share link with token + optional password renders scan without auth
5. Dashboard responsive at 1440p and 1080p

Plans:
- [x] 07-01-PLAN.md — Scan metadata columns migration (branch/commit_sha/source + bcrypt dep)
- [x] 07-02-PLAN.md — Backend GET /v1/scans list endpoint with filters + cursor pagination
- [x] 07-03-PLAN.md — Backend GET /v1/scans/{a}/compare/{b} diff endpoint
- [x] 07-04-PLAN.md — Backend share-link endpoints + migration 006 + bcrypt service

- [x] 07-05-PLAN.md — Dashboard scaffold (Next.js 15 workspace, Clerk middleware, app shell, backendFetch, types)
- [x] 07-06-PLAN.md — Scans list page (history filters, cursor pagination, Sparkline, SeverityBadge, Vitest suite)
- [x] 07-07-PLAN.md — Scan detail page (MetadataHeader, ScanViewerClient, R2 retry, ShareButton stub)

- [x] 07-08-PLAN.md — Compare page (CompareLayout, DiffSummary, DiffNodeList, CompareViewerPair, ScanPickerModal)
- [x] 07-09-PLAN.md — Share subsystem frontend (ShareModal, PasswordGate zero-metadata, ShareViewer, public landing)
- [x] 07-10-PLAN.md — Responsive breakpoints + Lighthouse perf budget config (DSH-06)
- [x] 07-11-PLAN.md — Home dashboard + Settings sub-routes (members/billing/integrations) (DSH-05, D-04)

### Phase 7.1: Phase 7 UI Contract Remediation (INSERTED)

**Status:** INSERTED — closes UI-SPEC gaps surfaced by the Phase 7 UI audit (`07-UI-REVIEW.md`, score 16/24).
**Goal:** Bring the Phase 7 dashboard in line with the approved `07-UI-SPEC.md` design contract — install the design system, replace the rejected compare visualization, complete the share-link management surface, and close the polish drift on color/typography/spacing/copy.
**Requirements:** RMD-01, RMD-02, RMD-03, RMD-04, RMD-05, RMD-06
**Depends on:** Phase 7 (dashboard shell shipped)
**Plans:** 9 plans

Plans:
- [x] 07.1-01-PLAN.md — RMD-01 Wave 0: shadcn init + 17 blocks + globals.css preserve (1 human checkpoint) — completed 2026-04-30 (commits 0610970, a40d2fe, d7614b5, b4ae95b)
- [ ] 07.1-02-PLAN.md — RMD-01, RMD-03 Toaster mount + ShareModal/ScanPickerModal Dialog migration
- [ ] 07.1-03-PLAN.md — RMD-01, RMD-06 ScanFilters Select+Calendar + SettingsLayout Tabs migration
- [ ] 07.1-04-PLAN.md — RMD-04 Backend GET /v1/scans/{id}/share-links endpoint + dashboard proxy
- [ ] 07.1-05-PLAN.md — RMD-02 Compare 4-section card rewrite + Sheet drill-down + delete CompareViewerPair
- [ ] 07.1-06-PLAN.md — RMD-03, RMD-04 Active share-links list + AlertDialog revoke flow + toasts
- [ ] 07.1-07-PLAN.md — RMD-05, RMD-06 Top-bar action slot + ScanDetailActions + breadcrumb fix
- [ ] 07.1-08-PLAN.md — RMD-06 Polish drift sweep (typography/color/focus-ring grep gates)
- [ ] 07.1-09-PLAN.md — RMD-06 Sparkline hover tooltip + relative-date copy ("2 hours ago"/"Yesterday"/"Apr 26")
**Success criteria:**
1. shadcn/ui initialized in `dashboard/` with the 17 declared blocks; 4 hand-rolled/Radix-direct components migrated to shadcn primitives (`ScanPickerModal`, `ShareModal`, `SettingsLayout`, `ScanFilters`)
2. Compare page replaces dual-canvas viewer pair with the spec'd 4-section diff card layout (Added/Removed/Changed/Findings) + `<Sheet/>` drill-down + attribute-level expanders on Changed rows
3. `<Toaster/>` mounted at app root; share-link copied/revoked/failed toasts firing on the three success/failure paths
4. Active share-links list rendered per UI-SPEC format with `[Revoke]` opening an `<AlertDialog/>` destructive-confirm flow (backed by existing `DELETE /v1/scans/{id}/share-links/{share_id}` endpoint)
5. Top-bar action slot pattern implemented; `[Compare] [Share]` move from `MetadataHeader` to top bar on `/scans/{id}` route
6. Polish drift closed: amber accent constrained to spec'd reserved-for list, off-scale `text-xl`/`text-lg` headings normalized to the 4-size scale, home page gutters fixed to `px-8 py-12 gap-12`, focus rings normalized to `ring-slate-400`, breadcrumb + relative-date copy aligned to spec, custom-range filter + sparkline hover tooltip implemented

**Context:** Phase 7 shipped functional but the implementation diverged from `07-UI-SPEC.md` on three blockers (shadcn never initialized, compare ships the explicitly-rejected dual canvas, share-management surface incomplete) and several warnings (color/typography/spacing/copy drift). The audit (`07-UI-REVIEW.md`, 2026-04-29) scored 16/24 (B). Inserting this phase before 7.5 keeps the GitHub-connector work building on a contract-aligned dashboard rather than amplifying the divergence. No new features — pure remediation pass.

### Phase 7.2: UI Contract Remediation — Live (INSERTED)

**Status:** INSERTED — second remediation pass after live testing surfaced defects the pre-shipping code-only audit missed.
**Goal:** Close the 14 P0/P1/P2/P3 defects catalogued in `07.1-LIVE-UI-REVIEW.md` (10/24 live score) so the dashboard is shippable for Phase 7.5 GitHub Connector work.
**Requirements:** D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-12, D-13, D-14, D-15
**Depends on:** Phase 7, Phase 7.1 (this remediates 7.1's shipped state)
**Success criteria:**
1. Canvas tab on `/scans/[id]` renders the diagram in the dashboard shell (not overflowing viewport, not pushed off-screen)
2. FilterPanel / DetailPanel / SummaryBar / SearchBar render and react to per-scan state when embedded in dashboard
3. `/settings` resolves to a real page (redirect to `/settings/members`)
4. Sparkline data points render as circles, not stretched ovals; container height matches spec (≥80px)
5. Grade letter shown for any given score is identical across ScoreCard, ScansTable, MetadataHeader, and ShareViewer
6. Sidebar has no `w-12` icon-only dead zone at 768–1279px viewports
7. ShareModal uses shadcn `<Select/>` (not native), warning text uses `text-amber-600`, label reads "Link expires in"
8. Live re-audit scores ≥20/24 across all 6 pillars

**Plans:** 10 plans

Plans:
- [x] 07.2-01-PLAN.md — D-01 viewer App.tsx h-screen → h-full (Wave 1)
- [x] 07.2-02-PLAN.md — D-02 useViewerStoreOrSingleton migration for FilterPanel/DetailPanel/SummaryBar/SearchBar + FlowMap variants (Wave 1)
- [x] 07.2-03-PLAN.md — D-03 /settings redirect + D-04 sparkline preserveAspectRatio + ScoreSparkline h-[80px] (Wave 1)
- [x] 07.2-04-PLAN.md — D-05 gradeInfo() shared util + adoption across ScoreCard/ScansTable/MetadataHeader/ShareViewer (Wave 2)
- [x] 07.2-05-PLAN.md — D-06 Sidebar xl-breakpoint collapse removal (Wave 2)
- [x] 07.2-06-PLAN.md — D-07 /api/top-findings route handler + TopFindings card rewrite (Wave 2)
- [x] 07.2-07-PLAN.md — D-08 ShareModal shadcn Select + "Link expires in" + text-amber-600 warning (Wave 2)
- [x] 07.2-08-PLAN.md — D-09 + D-11 + D-12 + D-13 + D-14 dashboard sweep (Wave 3)
- [x] 07.2-09-PLAN.md — D-10 viewer FilterPanel typography sweep (Wave 3)
- [x] 07.2-10-PLAN.md — D-15 LIVE re-audit ≥20/24 (Wave 4 — verify)

**Context:** Live testing on the dev/local-no-auth branch (2026-05-02) exposed defects that the pre-shipping audit graded as 17/24 missed. Driver: viewer's `App.tsx` was designed for standalone HTML mode; embedding it inside the dashboard shell broke layout assumptions (`h-screen w-screen`) and surfaced a deferred-but-unfinished store migration (`useStore` singleton vs `useViewerStoreOrSingleton` factory). This phase closes both — plus copy, color, spacing, and typography drift left behind by 7.1's plan-08 sweep. Suggested wave structure in `07.1-LIVE-UI-REVIEW.md`: 3 waves, 9–12 plans.


### Phase 7.5: GitHub Repo Connector (PLANNED)

**Status:** COMPLETE (2026-05-05) — 11/11 plans shipped across 6 waves; PHASE-VERIFICATION.md status=passed + signed_off=2026-05-05; manual GitHub smoke approved by operator against a real InfraCanvas DEV App installation + sandbox Terraform fixture. Phase 8 (GitHub Webhook + Auto-scan) unblocked.
**Goal:** Let authenticated users connect a GitHub repo, browse repos/branches, and trigger a scan against a specific branch + path — without needing a CLI or a pre-uploaded scan JSON.
**Requirements:** GH-01, GH-02, GH-03, GH-04, GH-05
**Plans:** 11 plans
**Depends on:** Phase 6 (backend auth/storage/queue), Phase 7 (dashboard shell)
**Success criteria:**
1. User installs the InfraCanvas GitHub App and sees their accessible repos in the dashboard
2. User picks a repo + branch + optional subdirectory path, clicks "Scan"
3. Backend performs a read-only shallow clone, runs `infracanvas scan`, stores result in Neon + R2 under the team
4. The resulting scan appears in Phase 7 history/detail views (status pending → ready, polled every 2s)
5. GitLab, Bitbucket, and Azure DevOps are explicitly out of scope — deferred to v1.2 Enterprise

Plans:
- [x] 07.5-01-PLAN.md — Wave 0 foundation: deps + Dockerfile + settings + shadcn command primitive
- [x] 07.5-02-PLAN.md — Wave 0 schema: github_installations table + scans columns + ORM + test fixtures + alembic upgrade
- [x] 07.5-03-PLAN.md — Wave 1: GitHub App auth + httpx client + Pydantic schemas
- [x] 07.5-04-PLAN.md — Wave 2: /v1/github/installations + repos + branches + install-callback (4 endpoints, 21 tests, RLS-isolated, App-JWT install reverify, 60s repo cache, rate-limit→503, idempotent ON CONFLICT upsert, 302 dashboard redirects)
- [x] 07.5-05-PLAN.md — Wave 2: _finalize_scan helper extraction + POST /v1/scans/from-github + extended GET /v1/scans/{id}
- [x] 07.5-06-PLAN.md — Wave 3: scan_repo taskiq job (clone + scan + R2 + finalize) + put_bytes (2026-05-04 — full pipeline lands; r2.put_bytes async helper via run_in_threadpool; scan_repo @broker.task ships 7-kwarg signature with mint→clone→traversal-guard→scan→put_bytes→finalize_scan; 3 token-redaction layers + WHERE pending guard + tmpdir cleanup; rc 0/1 success rc=2 fail; 16 tests; backend pipeline now end-to-end executable)
- [x] 07.5-07-PLAN.md — Wave 3: dashboard proxy routes + lib/types.ts extensions (2026-05-04 — 4 Next.js Route Handlers under dashboard/app/api/github/{installations,repos,branches}/route.ts + dashboard/app/api/scans/from-github/route.ts proxy via backendFetch+Clerk JWT; repos+branches preserve 503+Retry-After:60 for rate-limit toasts; POST preserves 422/503/404 with generic 'request_failed' body for 500 to avoid info-leak; lib/types.ts gains InstallationResp/RepoResp/BranchResp + 6 optional ScanGetResp Phase 7.5 fields; presigned_get_url relaxed to nullable; tsc clean; 183/183 tests pass; 2 commits)
- [x] 07.5-08-PLAN.md — Wave 4: InstallButton + RepoCombobox + BranchPicker components (2026-05-04 — 3 reusable client components under dashboard/components/integrations/: InstallButton (window.open install URL state==clerkOrgId + noopener,noreferrer; T-07.5-08-01 mitigation), RepoCombobox (shadcn Popover+Command with shouldFilter={false} + 250ms useRef debounce + cancellable fetch + private lock icon + inline 503 alert), BranchPicker (shadcn Select + lazy-load on selectedRepo + URL-encoded repo path + default-to-default_branch fallback when value empty + cancellable fetch + same 503 inline alert); 17 vitest tests added 4+7+6 — full dashboard suite 200/200 pass; 6 commits via 3 TDD RED→GREEN cycles)
- [x] 07.5-09-PLAN.md — Wave 5: ScanTriggerForm + live /settings/integrations page (2026-05-04 — ScanTriggerForm composes Plan 08 RepoCombobox+BranchPicker+path Input+Scan Button → POST /api/scans/from-github → router.push(/scans/{id}); /settings/integrations rewritten as 3-state machine (loading/preinstall/postinstall) with bounded post-install hydration poll capped at 5×3s ≈ 15s when ?install=success AND empty list (T-07.5-09-01); Slack stub preserved; Rule 1 refresh of 2 settings-routes.test.tsx invariants for the removed disabled placeholder; 14 new vitest tests 7+7 — full dashboard suite 214/214 pass (was 200, +14 net); 4 commits via 2 TDD RED→GREEN cycles; tsc clean across in-scope files)
- [x] 07.5-10-PLAN.md — Wave 5: ScanPendingClient polling + /api/scan-status proxy + scan-detail gating (2026-05-05 — /api/scan-status proxy via backendFetch+Clerk JWT mirroring scan-presigned route; ScanPendingClient implements CC-14 useEffect+setInterval(2000)+cancelled-flag teardown polling /api/scan-status while pending → router.refresh on ready, render error_message + Retry CTA on failed; Retry POSTs /api/scans/from-github with payload sourced exclusively from server-fetched scan github_* columns (T-07.5-10-03); scan-detail page status gate (renderScanByStatus helper extracted to its own module per Next.js 15 page-export restriction Rule-1 fix) routes pending/failed → ScanPendingClient, ready+URL → unchanged ScanViewerClient path; Rule-1 fix #2 dropped vitest 4 invalid 3-arg vi.mock form; 11 new vitest tests added 7+4 — full dashboard suite 225/225 pass (was 214, +11 net); 5 commits via 2 TDD RED→GREEN cycles plus 1 standalone proxy commit; tsc clean across in-scope files)
- [x] 07.5-11-PLAN.md — Wave 6: phase verification + manual GitHub smoke checkpoint (2026-05-05 — Task 1 commit bbfa0c7 wrote 07.5-PHASE-VERIFICATION.md (Sections 1 per-VALIDATION.md row + 2 GH-01..GH-05 traceability with file:line + 3 T1–T9 cross-cutting greps all green) and 07.5-MANUAL-SMOKE.md (263-line operator checklist: P1–P5 pre-flight + S1–S16 smoke); Task 2 was the checkpoint:human-verify gate (gate=blocking) — operator walked the 16-step checklist against a real InfraCanvas DEV App installation + sandbox Terraform fixture and resumed with "approved"; Task 3 flipped Section 4 sign-off to all-checked + status=passed + signed_off=2026-05-05, wrote 07.5-11-SUMMARY.md, advanced STATE.md + this ROADMAP.md. Phase 7.5 CLOSED.)

**Context:** Roadmap gap identified before Phase 8 planning: Phase 8 assumes a repo is already connected and jumps to push-webhook handling, but no phase actually delivers the "connect a repo" UX. This phase closes that gap with GitHub-only for MVP; multi-provider (Azure DevOps / GitLab / Bitbucket) deferred per solo-founder scope discipline. Architecture decisions locked in 07.5-CONTEXT.md (D-01..D-17): GitHub App auth (mint-per-scan), taskiq scan_repo job reused by Phase 8 webhook flow, /settings/integrations as live state machine, scans.status='pending' polled every 2s.

### Phase 8: GitHub Webhook + Auto-scan

**Goal:** Auto-scan on push, alert on Critical findings.
**Requirements:** WBH-01, WBH-02, WBH-03
**Depends on:** Phase 6, Phase 7.5 (repo must be connected before push events matter)
**Success criteria:**
1. Push to a connected GitHub repo triggers a scan job inside 30 s
2. Scan result lands in Neon + R2 with commit SHA tied to team
3. Slack webhook fires when scan produces ≥ 1 Critical finding

### Phase 9: CostLens

**Goal:** Shared-infrastructure cost allocation + per-path cross-cloud data transfer cost.
**Requirements:** CLA-01, CLA-02, CLA-03, CLA-04, CLA-05, CLA-06, CPC-01, CPC-02 (deferred Phase 12), CPC-03
**Depends on:** Phase 7 (dashboard panel)
**Success criteria:**
1. TGW, ExpressRoute, Azure Firewall, NAT GW, VPC Endpoint costs split by workload tag
2. Per-path cross-cloud data transfer cost visible in FlowMap PathDetailPanel
3. Idle/oversized recommendations listed in viewer and dashboard
4. Allocation percentages sum to 100% per shared resource
5. CostLens tab active in viewer HTML report (not coming-soon)
6. Dashboard scan detail page shows 'Cost' tab with WorkloadTable

**Plans:** 7 plans

Plans:
- [ ] 09-01-PLAN.md — Wave 0: Test stubs + shadcn badge/tooltip install
- [ ] 09-02-PLAN.md — Wave 1: Pydantic models + config + FLAT_MONTHLY + SharedCostAllocator (CLA-01..04)
- [ ] 09-03-PLAN.md — Wave 1: IdleDetector + main.py wiring (CLA-05, CLA-06 data)
- [ ] 09-04-PLAN.md — Wave 1: EgressEstimator + main.py wiring (CPC-01)
- [ ] 09-05-PLAN.md — Wave 2: Viewer CostLensPanel + tab activation + TabBar test fixes (CLA-05, CLA-06 viewer)
- [ ] 09-06-PLAN.md — Wave 2: Dashboard Cost tab + WorkloadTable + ScanDetailTabs (CLA-06 dashboard)
- [ ] 09-07-PLAN.md — Wave 2: FlowMap PathDetailPanel cost annotation (CPC-03)

### Phase 10: DC Agent Core

**Goal:** Go DC Agent scaffolded, NETCONF/SSH + NetFlow + encrypted push working, CAB packet ready.
**Requirements:** DCA-01, DCA-02, DCA-03, DCA-04, DCA-05, DCA-06, DCA-07, DCA-08, DCA-09
**Depends on:** Phase 6 (backend receives agent pushes). Cisco NETCONF compatibility research (D-A3b) completed before DCA-02.
**Success criteria:**
1. `infracanvas-agent` single binary runs on Linux amd64 + macOS arm64
2. Agent collects routes from a Cisco IOS-XE device via NETCONF (SSH fallback verified)
3. NetFlow collector on UDP 2055 persists flow records
4. Encrypted push to cloud backend authenticates and stores readings
5. Daemon timing: routes 5 min, BGP 1 min, NetFlow 30 s (all observed)
6. CAB security-review packet complete (architecture diagram, data flow, threat model, SBOM)

### Phase 11: Firewall Integration

**Goal:** Cisco ASA + Checkpoint rule-base + policy data flow into cloud.
**Requirements:** ASA-01, ASA-02, ASA-03, CKP-01, CKP-02
**Depends on:** Phase 10
**Success criteria:**
1. ASA REST API pulls rule base + NAT table; SSH fallback works
2. FMC REST pulls policy
3. Checkpoint Management API pulls rule base + objects
4. All rule sets visible in cloud backend, tied to team + site

### Phase 12: Path Computation + Asymmetric Routing

**Goal:** Detect asymmetric routing end-to-end with root cause + impact, NET-010 active.
**Requirements:** PTH-01, PTH-02, PTH-03, ASY-01, ASY-02, ASY-03, NET-010, FMV-02, NFN-02
**Depends on:** Phase 10 (DC agent data), Phase 11 (firewall rules)
**Success criteria:**
1. Forward + return paths computed from route + policy data
2. NetFlow correlation flags paths where observed flow ≠ computed path
3. Asymmetric routing detector flags all asymmetric flow pairs
4. Root cause classifier assigns BGP_LOCAL_PREF / ROUTE_LEAK / NAT_ASYMMETRY
5. FlowMap viewer shows divergence marker (FMV-02); route-change alert (NFN-02) fires on DC agent churn

### Phase 13: Team Tier Launch

**Goal:** Team tier billable at $299/mo with FlowMap 3b + CostLens gated to it.
**Requirements:** TIR-01, TIR-02
**Depends on:** Phase 9, Phase 12
**Success criteria:**
1. Stripe Team product live at $299/mo
2. Free/Pro users blocked from FlowMap 3b + CostLens features with clear upgrade CTA
3. Team subscribers can access all gated features

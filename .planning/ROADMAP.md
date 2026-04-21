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
- [ ] **Phase 6: SaaS Backend Foundation** — FastAPI + Clerk + Neon + R2 + taskiq + Stripe Billing Meters + observability
- [ ] **Phase 7: SaaS Dashboard + Scan History + Share Links** — Next.js 15 dashboard on Vercel, scan list/detail/compare, share links
- [ ] **Phase 8: GitHub Webhook + Auto-scan** — push webhook, scan worker, Slack alert on Critical
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
| 6. SaaS Backend Foundation | v1.1 | 0/TBD | Not planned | - |
| 7. SaaS Dashboard + History + Share | v1.1 | 0/TBD | Not planned | - |
| 8. GitHub Webhook + Auto-scan | v1.1 | 0/TBD | Not planned | - |
| 9. CostLens | v1.1 | 0/TBD | Not planned | - |
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

### Phase 7: SaaS Dashboard + Scan History + Share Links

**Goal:** User-facing dashboard for browsing, comparing, and sharing scans.
**Requirements:** DSH-02, DSH-03, DSH-04, DSH-05, DSH-06, HST-01, HST-02, HST-03, SHR-01, SHR-02
**Depends on:** Phase 5 (viewer package), Phase 6 (backend)
**Success criteria:**
1. User logs in via Clerk, sees their team's scans
2. Clicking a scan renders the embedded viewer from the shared package
3. Compare-two-scans view shows resource diff (added/removed/changed)
4. Share link with token + optional password renders scan without auth
5. Dashboard responsive at 1440p and 1080p

### Phase 8: GitHub Webhook + Auto-scan

**Goal:** Auto-scan on push, alert on Critical findings.
**Requirements:** WBH-01, WBH-02, WBH-03
**Depends on:** Phase 6
**Success criteria:**
1. Push to a connected GitHub repo triggers a scan job inside 30 s
2. Scan result lands in Neon + R2 with commit SHA tied to team
3. Slack webhook fires when scan produces ≥ 1 Critical finding

### Phase 9: CostLens

**Goal:** Shared-infrastructure cost allocation + per-path cross-cloud data transfer cost.
**Requirements:** CLA-01, CLA-02, CLA-03, CLA-04, CLA-05, CLA-06, CPC-01, CPC-02, CPC-03
**Depends on:** Phase 7 (dashboard panel)
**Success criteria:**
1. TGW, ExpressRoute, Azure Firewall, NAT GW, VPC Endpoint costs split by workload tag
2. Per-path cross-cloud data transfer cost visible in FlowMap
3. Idle/oversized recommendations listed in dashboard
4. Allocation percentages sum to 100% per shared resource

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

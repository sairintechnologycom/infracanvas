# InfraCanvas Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Canvas + FlowMap v1.0 (Hybrid Cloud Intelligence MVP)

**Shipped:** 2026-04-19
**Phases:** 5 (00, 01, 02, 03, 03.5) | **Plans:** 32 | **Commits:** 223 | **Timeline:** 6 days

### What Was Built

- **Canvas pipeline (Phases 1–2):** HCL parser → NetworkX graph → 40 security rules (30 AWS + 10 Azure) with CIS/NIST/SOC2/PCI-DSS compliance tags → drift overlay + shadow detection + policy engine → multi-region cost estimator → React viewer → single-file HTML export. Full CLI with `scan`/`score`/`plan`/`export`/`serve` and CI flags (`--ci --fail-on --quiet --ignore --severity --watch`).
- **FlowMap cloud-only (Phase 3):** AWS + Azure network topology collectors (TGW, VPC, Direct Connect, vWAN, vNet, ExpressRoute, NSG flow logs) + 11 NET-* rules + React FlowMap viewer (TabBar + Canvas + Filter + PathDetail + EmptyState). Python↔TypeScript schema parity for 5 model types.
- **Validation landing (Phase 0):** Next.js static site at infracanvas.dev with Stripe founding-member CTA, Typeform lead capture, 7-section layout. Campaign framework (Reddit warm-up, 20-conversation tracker, Go/No-Go decision) ready for human execution.
- **Retroactive verification (Phase 3.5):** 3 VERIFICATION.md documents authored — 01 (29 REQ-IDs, 293 lines), 02 (21 REQ-IDs + UAT cross-refs, 410 lines), 03 (14 satisfied + 24 deferred, 377 lines). Closed all audit blockers without touching code.
- **Multi-platform distribution:** Dockerfile (multi-stage, non-root), PyInstaller spec, 3-platform GHA release workflow, Homebrew formula. Configured but first-release execution pending.

### What Worked

- **Deferring FlowMap 3b inside Phase 3 planning (cloud-only in v1.0)** — clean scope cut with 24 requirements explicitly enumerated in a Deferred Scope Note table. No orphans, no "half-built" FlowMap. Let v1.0 ship in 6 days instead of 10–16 weeks waiting on DC Agent CAB approval.
- **Retroactive verification (Phase 3.5)** — authoring VERIFICATION.md from existing SUMMARY/UAT/SECURITY artifacts was ~3 hours per phase vs. re-running verification from scratch. Proved that if SUMMARYs carry enough evidence at plan close, verification docs can be generated deterministically later.
- **`framework_ids` as a first-class field on every rule (Phase 2, not Phase 5)** — baking compliance tags into the rule schema during Phase 2 was cheaper than retrofitting in Enterprise (Phase 5). The FindingCard UI consumed them without schema churn.
- **Python↔TypeScript schema parity via shared Pydantic model → types.ts mirror** — caught via integration checker; zero drift across 5 FlowMap model types. The parity gate in the integration check is cheap and high-signal.
- **HCL parser silent-failure hardening as a Phase 2 prerequisite** — the "fix parse_errors collection BEFORE Azure parser" decision prevented weeks of debugging Azure issues that would have been masked by upstream silent failures.
- **Parallel plan execution within phases via wave-based `/gsd-execute-phase`** — Phase 3.5 ran 3 independent VERIFICATION.md authoring plans in parallel; wall-clock time matched the slowest plan, not the sum.

### What Was Inefficient

- **Missing VERIFICATION.md files for Phases 01/02/03 at initial milestone audit** — the audit surfaced 3 critical blockers that required spinning up an entire phase (3.5) to close. If verification had been a mandatory gate per plan (not just per phase) it would have been authored incrementally during execution at zero marginal cost.
- **`milestone complete` CLI extracted malformed accomplishments** — the summary-extract tool pulled raw "One-liner:" labels and unrelated text from SUMMARY.md files, requiring manual MILESTONES.md rewrite. The accomplishment extraction pipeline needs a cleaner grammar contract with SUMMARY templates.
- **`roadmap analyze` tool only detected 3 of 5 phases** — missed Phases 3 and 3.5 because of how phase headings were parsed. Milestone-close workflow had to fall back to Glob + manual counting.
- **ROADMAP.md drift between "Phase 2: Canvas v1.0" (goal label) and the actual v1.0 milestone (which spans Phases 0–3.5)** — `milestone_name` in STATE.md inherited Phase 2's goal text, which misrepresented the milestone scope in every tool output that surfaced it. Future milestones should use a dedicated milestone title rather than copying a phase goal.
- **REL-01..04 deferred validation** — the PyPI/Homebrew/GHA release workflow could not be tested end-to-end without a first semver tag (chicken-and-egg with Homebrew source-build). Milestone shipped with 4 PARTIAL requirements that could only have been closed by actually publishing.

### Patterns Established

- **`framework_ids: list[str]` on every security rule** — compliance-first rule schema. Applies to every new rule directory (aws/, azure/, network/, future gcp/).
- **`run_*_collection` orchestrator pattern with credential-safe warn-and-continue** — Phase 3-02's orchestrator handled missing AWS creds + missing Azure creds + partial results gracefully. Future cloud collectors (GCP in v4, Oracle, IBM) should follow this template.
- **Single-file HTML export with `window.__INFRACANVAS_DATA__` placeholder injection** — zero runtime dependencies, distributable via email. The postbuild hook (`viewer/package.json`) keeps `viewer/dist/index.html` byte-identical to `cli/infracanvas/export/viewer_template.html`.
- **Pydantic model in `graph/models.py` + TypeScript mirror in `viewer/src/types.ts`** — every new data model gets both sides. Integration checker enforces parity.
- **Plan SUMMARY frontmatter as the authoritative source for retroactive verification** — if SUMMARY.md records commit hashes, test counts, and file paths, VERIFICATION.md can be authored post-hoc without re-running code.
- **Deferred Scope Note tables with target phase + rationale per deferred REQ-ID** — explicit scope cuts beat "TBD" or silent omission. No orphans in the v1.0 audit.
- **Retroactive phase (3.5) for documentation gap closure** — when milestone audit finds missing artifacts, spin up a doc-only phase rather than re-executing feature phases.

### Key Lessons

1. **Make VERIFICATION.md a per-phase gate, not just a milestone gate.** Phase 3.5 existed only because Phases 01/02/03 had skipped verification at plan time. Cost: one extra phase. Fix: `/gsd-execute-phase` should enforce VERIFICATION.md before marking the phase complete.
2. **Explicit scope cuts with enumerated deferrals beat silent omission every time.** Phase 3's "24 REQ-IDs deferred to 3b/4 with target phase and rationale" produced zero orphans in the audit. Silent deferrals would have required archaeology.
3. **Pre-requisite hardening (HCL parse_errors) before a dependent feature (Azure parser) saves weeks of debugging.** Bake this into the planning discipline: if feature B depends on feature A working reliably, fix A's silent-failure modes first.
4. **Compliance-first rule schema (framework_ids in Phase 2, not Phase 5) is cheaper than retrofit.** A new schema field affects every rule file but is mechanical; retrofitting means per-rule review + regression testing.
5. **Retroactive doc-only phases are cheap (~3 hrs per VERIFICATION.md) when SUMMARYs carry evidence.** If SUMMARY template enforces commit hashes + test counts + file paths at plan close, later verification can be authored deterministically without re-running code.
6. **Chicken-and-egg distribution validation (PyPI → Homebrew source-build) leaves unavoidable PARTIAL requirements at milestone close.** Accept this as a known shipping footgun; close via a tiny post-milestone "first release" phase rather than blocking the milestone.

### Cost Observations

- Model mix: ~80% opus (planning, research, complex code), ~20% sonnet (sub-agents: verifier, integration-checker, ui-reviewer)
- Parallel execution within Phase 3.5 cut doc-authoring wall time ~3×
- Primary cost drivers were Phase 2 (broadest scope: Azure + 20 new rules + drift + shadow + policy + cost + staleness + distribution) and Phase 3 (9 plans, 5 new model types, 2 cloud collectors, FlowMap viewer)

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 5 | 32 | Baseline — GSD v1 workflow with wave-based parallel execution, retroactive verification phase (3.5) to close audit gaps |

### Cumulative Quality

| Milestone | Python Tests | TS Tests | Security Rules | LOC |
|-----------|--------------|----------|----------------|-----|
| v1.0 | 268+ | 79 | 51 (30 AWS + 10 Azure + 11 NET) | ~14,065 |

### Top Lessons (Verified Across Milestones)

*Will populate as more milestones ship.*

1. (v1.0) Explicit scope cuts with enumerated deferrals prevent orphaned requirements.
2. (v1.0) Pre-requisite hardening before dependent features beats parallel development when silent failures are possible.

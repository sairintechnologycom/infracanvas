# Milestones

## v1.0 — Canvas + FlowMap v1.0 (Hybrid Cloud Intelligence MVP) (Shipped: 2026-04-19)

**Phases completed:** 5 (00, 01, 02, 03, 03.5)
**Plans completed:** 32
**Commits:** 223 (4013690 → 1d14a26)
**Timeline:** 2026-04-14 → 2026-04-19 (6 days)
**LOC:** ~14,065 (Python + TypeScript/TSX)

**Delivered:** A CLI-first hybrid cloud intelligence tool. `infracanvas scan ./terraform` parses HCL, builds a NetworkX resource graph, evaluates 51 security rules (30 AWS + 10 Azure + 11 Network) with CIS/NIST/SOC2/PCI-DSS compliance tags, detects drift and shadow infrastructure, runs custom YAML policies, estimates multi-region cost, and exports a single-file interactive HTML viewer with Canvas + FlowMap tabs. Multi-platform distribution (Docker, PyInstaller, Homebrew) is wired but pending first release execution.

**Key accomplishments:**

- **Phase 0 — Validation:** Next.js landing page at infracanvas.dev with Stripe founding-member CTA + Typeform lead capture + demo video slot; 4-8 week Reddit/LinkedIn/Discord outreach campaign plan + 20-customer conversation tracker + Go/No-Go decision framework (VAL-01..05, campaign execution pending human).
- **Phase 1 — Canvas MVP:** Typer CLI (scan, score, plan, export, serve commands), HCL parser for 15 AWS resource types, NetworkX graph with VPC/subnet grouping, 10 AWS security rules (SEC-001..010), 0–100 health score with letter grades across 5 dimensions, React 18 + @xyflow viewer with Dagre layout and free-tier gate, single-file HTML export < 5MB, PyPI + Homebrew distribution configured.
- **Phase 2 — Canvas v1.0:** Azure provider (10 resource types, `normalize_azure_attrs`), 30 AWS security rules total + 10 Azure rules, all 40 rules carry CIS/NIST/SOC2/PCI-DSS `framework_ids`, Terraform plan reader (colour-coded drift overlay + before/after diffs), shadow detector (boto3 optional, 6 AWS resource types), custom policy engine (`.infracanvas.yml`, `--policy` flag), multi-region cost estimator (15 region multipliers + group aggregation), staleness checks (Lambda EOL, EKS/AKS version, resource locks), CI/watch flag set (`--ci --fail-on --quiet --ignore --severity --watch`), Docker + PyInstaller + GHA release workflow.
- **Phase 3 — FlowMap v1.0 (cloud-only):** NetworkPath/PathHop/DCCollectorReading/DCSite Pydantic models + TypeScript mirrors, `--flowmap` CLI flag + credential-safe collector orchestrator, AWS network collector (TGW + VPC + Direct Connect + CloudWatch flow log metadata), Azure network collector (vWAN + vNet peering + ExpressRoute + NSG flow log metadata), 11 NET-* rules (NET-010 reserved for 3b), React FlowMap viewer (TabBar + Canvas + FilterPanel + PathDetailPanel + EmptyState). 24 requirements correctly deferred to 3b (DC Agent, ASA/Checkpoint, path computation, asymmetry) or Phase 4 (tiering/Stripe).
- **Phase 3.5 — Retroactive Verification:** 3 VERIFICATION.md documents authored (01/02/03) closing all critical blockers from the initial v1.0 milestone audit; 91 milestone REQ-IDs traced across 3 independent sources (REQUIREMENTS traceability + SUMMARY frontmatter + VERIFICATION evidence); Nyquist compliance flipped from 0/4 → 3/4 (Phase 00 remains human-gated).

**Known Gaps / Deferred:**

- **REL-01..04 PARTIAL** — PyPI publish, Homebrew tap, GHA release workflow, Show HN all configured; first semver-tag execution pending.
- **VAL-01..05 human-gated** — 4–8 week Stripe/Typeform/Reddit campaign + 20 customer conversations + Go/No-Go decision awaits human execution per D-05 stagger.
- **24 FlowMap reqs deferred by design** to Phase 3b (DC Agent, ASA/Checkpoint, path computation, asymmetry) or Phase 4 (Team-tier gating). Fully enumerated with target phase and rationale in `milestones/v1.0-MILESTONE-AUDIT.md` and `03-VERIFICATION.md`.
- **CST-01 Infracost API** deferred to Phase 4 SaaS backend (static pricing ships in v1.0).
- **Azure shadow detection** deferred to Phase 3b/4 (AWS-only in v1.0 per 02-SECURITY.md T-02-09).

**Audit status at close:** `tech_debt` — 0 critical blockers, 0 orphaned requirements, 0 broken E2E flows, Python↔TS schema parity confirmed, 51 security rules with zero duplicate IDs, viewer bundle byte-identical to viewer/dist. See `milestones/v1.0-MILESTONE-AUDIT.md`.

**Archived artifacts:**
- `milestones/v1.0-ROADMAP.md` — full phase details
- `milestones/v1.0-REQUIREMENTS.md` — 91 requirements with outcomes
- `milestones/v1.0-MILESTONE-AUDIT.md` — final audit report

---

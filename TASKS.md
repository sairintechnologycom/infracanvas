# InfraCanvas — Build Roadmap (TASKS.md)

## Sprint Structure
- **Sprint length**: 1 week
- **Total MVP timeline**: 6 weeks (Weeks 1-6)
- **SaaS launch**: Weeks 7-10
- **Goal**: CLI with interactive diagrams + security findings by Week 6

---

## Week 1: Core Parser & Graph Foundation

### T-001: Project scaffolding (2h)
- [ ] Initialize Python project with `pyproject.toml`
- [ ] Set up `typer` CLI skeleton with `scan`, `plan`, `export` commands
- [ ] Configure `pytest`, `ruff`, `mypy`
- [ ] Initialize git repo, .gitignore, LICENSE (MIT for CLI core)
- [ ] Create Pydantic models: `Resource`, `Edge`, `ResourceGraph`, `Finding`

### T-002: HCL Parser — basic resources (6h)
- [ ] Parse `.tf` files using `python-hcl2`
- [ ] Extract resource blocks: type, name, provider
- [ ] Extract key attributes per resource type (start with 15 AWS types)
- [ ] Handle `variable`, `local`, `output` blocks
- [ ] Handle multiple files in a directory
- [ ] Unit tests: parse 3 sample Terraform projects

### T-003: HCL Parser — dependencies & modules (4h)
- [ ] Detect explicit dependencies (`depends_on`)
- [ ] Detect implicit dependencies (resource references like `aws_vpc.main.id`)
- [ ] Parse `module` blocks, resolve source paths
- [ ] Build dependency edges in graph
- [ ] Unit tests: verify correct edges for complex configs

### T-004: Terraform state reader (3h)
- [ ] Parse `.tfstate` JSON format
- [ ] Extract resources with full attributes
- [ ] Map state resources to HCL-declared resources
- [ ] Handle remote state (read from local file only for v1)
- [ ] Unit tests: parse sample tfstate files

### T-005: Resource graph builder (3h)
- [ ] Construct `networkx` directed graph from parsed resources
- [ ] Add resource metadata as node attributes
- [ ] Auto-group by VPC/subnet, module, region
- [ ] Export graph as JSON (matching schema in ARCHITECTURE.md)
- [ ] Unit tests: verify graph structure

**Week 1 deliverable**: `infracanvas scan ./terraform` outputs a JSON resource graph

---

## Week 2: Security Rules Engine

### T-006: Rule engine framework (4h)
- [ ] YAML rule definition schema
- [ ] Rule loader (discover and parse all rules in `rules/` directory)
- [ ] Evaluation engine: match resource type → evaluate condition → emit finding
- [ ] Support operators: `equals`, `not_equals`, `in`, `not_in`, `exists`, `not_exists`, `matches`
- [ ] Unit tests: engine with 5 test rules

### T-007: AWS security rules — Critical/High (6h)
- [ ] SEC-001: S3 bucket public ACL
- [ ] SEC-002: S3 bucket no encryption
- [ ] SEC-003: S3 bucket no versioning
- [ ] SEC-004: Security group 0.0.0.0/0 ingress on sensitive ports
- [ ] SEC-005: RDS publicly accessible
- [ ] SEC-006: RDS no encryption
- [ ] SEC-007: IAM policy with Action: "*"
- [ ] SEC-008: IAM policy with Resource: "*"
- [ ] SEC-009: EBS volume unencrypted
- [ ] SEC-010: CloudTrail not enabled
- [ ] Unit tests per rule with positive and negative cases

### T-008: AWS security rules — Medium/Info (4h)
- [ ] SEC-011: VPC flow logs disabled
- [ ] SEC-012: ALB no WAF
- [ ] SEC-013: Lambda not in VPC
- [ ] SEC-014: EC2 instance no IMDSv2
- [ ] SEC-015: KMS key rotation disabled
- [ ] SEC-016: SNS topic not encrypted
- [ ] SEC-017: SQS queue not encrypted
- [ ] SEC-018: Untagged resources (missing Name, Environment, Owner)
- [ ] SEC-019: RDS no multi-AZ
- [ ] SEC-020: No backup plan for RDS/DynamoDB
- [ ] Unit tests per rule

### T-009: Annotate graph with findings (2h)
- [ ] Run rule engine against all resources in graph
- [ ] Attach findings to respective resource nodes
- [ ] Calculate infrastructure score (100 - weighted penalty per finding)
- [ ] Generate finding summary counts
- [ ] Unit tests: end-to-end scan → annotated graph

**Week 2 deliverable**: `infracanvas scan` outputs JSON graph with security findings and score

---

## Week 3: Interactive Diagram Viewer (React)

### T-010: React viewer scaffolding (3h)
- [ ] Initialize Vite + React + TypeScript project in `viewer/`
- [ ] Install React Flow, Tailwind, Zustand
- [ ] Configure `vite-plugin-singlefile` for single HTML output
- [ ] Create data loading: read embedded JSON from `<script>` tag
- [ ] Set up store for filters, selections, panel state

### T-011: Resource node components (6h)
- [ ] Custom React Flow node: cloud provider icon + resource name + type
- [ ] Finding badge overlay (colored dot: red/orange/yellow/blue)
- [ ] Finding count tooltip on hover
- [ ] Cost label (if available)
- [ ] Drift indicator (green/red/amber border)
- [ ] Selected state with highlight ring
- [ ] Node sizing based on resource importance

### T-012: Diagram layout & grouping (4h)
- [ ] Auto-layout algorithm: hierarchical with group nesting
- [ ] Group nodes by VPC → subnet → resource
- [ ] Group background rectangles with labels
- [ ] Module boundary indicators
- [ ] Region labels
- [ ] Edge rendering: smooth bezier curves, arrow direction

### T-013: Interaction & panels (4h)
- [ ] Summary bar (top): total resources, findings by severity, cost, score
- [ ] Filter panel (left): filter by resource type, severity, module, region
- [ ] Detail panel (right): click resource → show attributes, findings, cost
- [ ] Finding detail: description, evidence, remediation code snippet
- [ ] Search: find resource by name/type
- [ ] Zoom controls, minimap, fit-to-screen

### T-014: Build pipeline (2h)
- [ ] Vite build → single HTML file with all JS/CSS inlined
- [ ] Python CLI embeds built HTML, injects graph JSON at build time
- [ ] `infracanvas scan ./terraform` → opens browser with diagram
- [ ] `infracanvas scan ./terraform -o report.html` → saves HTML file
- [ ] Test: end-to-end with 3 sample Terraform projects

**Week 3 deliverable**: Beautiful interactive diagram in a single HTML file

---

## Week 4: Drift Detection & Cost Estimation

### T-015: Terraform plan reader (4h)
- [ ] Parse `terraform show -json planfile` output
- [ ] Extract: resource changes (create, update, delete, no-op)
- [ ] Map changes to resource graph nodes
- [ ] Detect attribute-level changes (before/after values)
- [ ] Unit tests with sample plan JSON

### T-016: Drift visualization (3h)
- [ ] Color-code nodes: green (added), red (deleted), amber (changed)
- [ ] "Changes" panel listing all drifted resources
- [ ] Click changed resource → show before/after diff
- [ ] Summary: "3 added, 1 changed, 0 deleted"
- [ ] CLI: `infracanvas plan ./terraform --planfile=plan.json`

### T-017: Cost estimator (4h)
- [ ] Build pricing lookup table for top 20 AWS resource types
- [ ] Source: Infracost pricing API (free tier) or static pricing JSON
- [ ] Estimate based on resource type + key attributes (instance type, storage size)
- [ ] Cost per resource, per group, total
- [ ] Cost delta on plan changes
- [ ] Display on resource nodes and summary bar

### T-018: Score card generator (3h)
- [ ] `infracanvas score ./terraform` → terminal output with scores
- [ ] Scores: Security (0-100), Cost Efficiency, Compliance Readiness
- [ ] Letter grades: A/B/C/D/F per category
- [ ] Overall infrastructure health score
- [ ] `--format=json|markdown|html` for sharing
- [ ] Shareable HTML card for social media / Slack

**Week 4 deliverable**: Full scan with drift, cost, and a shareable score card

---

## Week 5: CLI Polish & Distribution

### T-019: CLI UX polish (4h)
- [ ] `rich` terminal output: progress bars, colored findings table
- [ ] `--watch` mode: re-scan on file changes
- [ ] `--ci` mode: JSON output, exit code based on finding severity threshold
- [ ] `--ignore` flag: skip specific rules
- [ ] Config file: `.infracanvas.yml` for project-level settings
- [ ] Error handling: helpful messages for common issues (no .tf files, parse errors)

### T-020: Packaging & distribution (4h)
- [ ] PyPI package: `pip install infracanvas`
- [ ] GitHub Actions: auto-publish to PyPI on tag
- [ ] Homebrew formula for macOS
- [ ] Docker image: `docker run infracanvas scan ./terraform`
- [ ] GitHub Releases: pre-built binaries (Linux amd64, macOS arm64)
- [ ] Install script: `curl -sSL https://get.infracanvas.dev | sh`

### T-021: Documentation (4h)
- [ ] README.md: quick start, features, screenshots, comparison table
- [ ] docs/: installation, CLI reference, rule reference, configuration
- [ ] CONTRIBUTING.md: how to add custom rules
- [ ] Record terminal demo GIF with `asciinema`
- [ ] Screenshot gallery of diagram outputs

### T-022: Sample projects & testing (3h)
- [ ] 5 sample Terraform projects of varying complexity
- [ ] Integration tests: scan each sample, verify output
- [ ] Performance test: 500-resource project in < 10 seconds
- [ ] Cross-platform testing: macOS, Linux, Windows (WSL)

**Week 5 deliverable**: Publishable CLI package with documentation

---

## Week 6: Landing Page & Launch Prep

### T-023: Landing page (4h)
- [ ] Hero: animated diagram generation demo
- [ ] Problem → solution narrative
- [ ] Feature showcase with screenshots
- [ ] Pricing table
- [ ] CLI install command with copy button
- [ ] Email waitlist for SaaS dashboard
- [ ] Deploy to Vercel

### T-024: Launch assets (3h)
- [ ] "Show HN" post draft
- [ ] Twitter/X launch thread (8 tweets)
- [ ] dev.to article: "I built an open-source Terraform architecture visualizer"
- [ ] Reddit posts: r/terraform, r/devops, r/aws
- [ ] Product Hunt listing prep

### T-025: Analytics & telemetry (2h)
- [ ] PostHog: track CLI usage (opt-in, anonymous)
- [ ] Track: command used, resource count, provider, finding counts
- [ ] Plausible: landing page analytics
- [ ] Sentry: CLI error tracking (opt-in)

### T-026: Launch execution (1h)
- [ ] Publish to PyPI, Homebrew
- [ ] Create GitHub repo (public)
- [ ] Post on HN, Reddit, Twitter, dev.to
- [ ] Monitor feedback, respond to issues

**Week 6 deliverable**: Public launch of CLI + landing page

---

## Weeks 7-10: SaaS Dashboard (Post-CLI-Launch)

### T-027: FastAPI backend (Week 7)
- [ ] Project CRUD, scan upload/retrieval
- [ ] Clerk auth integration
- [ ] Neon PostgreSQL + Alembic migrations
- [ ] R2 artifact storage
- [ ] API key management

### T-028: Next.js dashboard (Week 8-9)
- [ ] Dashboard layout with project list
- [ ] Scan history timeline per project
- [ ] Embedded diagram viewer (shared React component)
- [ ] Share link generation
- [ ] Team management (invite, roles)

### T-029: Billing & pro features (Week 9)
- [ ] Stripe/Dodo Payments integration
- [ ] Feature gating (free vs pro vs team)
- [ ] Usage metering (scan count, project count)
- [ ] Upgrade prompts in CLI

### T-030: CI/CD integration (Week 10)
- [ ] Webhook endpoint for GitHub/GitLab
- [ ] Auto-scan on push to main
- [ ] GitHub Action: `infracanvas-action`
- [ ] Scan status badge for README

---

## Priority Matrix

| Task | Impact | Effort | Priority |
|------|--------|--------|----------|
| HCL Parser | Critical | Medium | P0 |
| Security Rules | Critical | Medium | P0 |
| Diagram Viewer | Critical | High | P0 |
| Drift Detection | High | Medium | P1 |
| Cost Estimation | Medium | Medium | P1 |
| Score Card | High | Low | P1 |
| CLI Polish | Medium | Medium | P2 |
| Landing Page | High | Low | P1 |
| SaaS Backend | High | High | P2 |
| Dashboard | Medium | High | P3 |

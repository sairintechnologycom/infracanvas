# InfraCanvas — Tech Stack

## CLI & Core Engine

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Language** | Python 3.12+ | Fast prototyping, rich HCL/JSON parsing libraries, Bhushan's proficiency, easy to package |
| **HCL Parser** | `python-hcl2` | Pure Python HCL2 parser, handles most Terraform syntax |
| **Graph Library** | `networkx` | Resource dependency graph construction, traversal, layout algorithms |
| **CLI Framework** | `typer` + `rich` | Modern CLI with beautiful terminal output, auto-generated help |
| **Diagram Renderer** | Embedded React SPA (bundled HTML) | Single-file HTML output with interactive D3/React diagram |
| **JSON Schema** | `pydantic` | Type-safe resource graph model, JSON serialization |
| **Packaging** | `pyinstaller` + `pip` | Distribute as pip package and standalone binary |
| **Testing** | `pytest` | Unit + integration tests for parser and rules engine |

### Why Python over Rust/Go for MVP
- **Speed of iteration** > execution speed for a bootstrapped MVP
- HCL parsing libraries exist and are battle-tested
- If performance becomes an issue with large codebases (500+ resources), rewrite the parser in Rust later
- The bottleneck will be rendering, not parsing

## Security Rules Engine

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Rule format** | YAML definitions | Easy to write, community-contributable |
| **Evaluation** | Custom Python engine | Simple pattern matching against resource attributes |
| **Output** | Pydantic models → JSON | Type-safe, serializable findings |

```yaml
# Example rule definition
- id: SEC-001
  title: "S3 Bucket Publicly Accessible"
  severity: critical
  resource_types: ["aws_s3_bucket"]
  condition:
    attribute: "acl"
    operator: "in"
    values: ["public-read", "public-read-write"]
  remediation: "Set acl to 'private' and use bucket policies for access control"
```

## Frontend (Diagram Viewer — embedded in CLI output)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Framework** | React 18 | Component-based, hooks for interactivity |
| **Diagram Library** | `@xyflow/react` (React Flow) | Purpose-built for node-edge diagrams, zoom/pan/minimap built-in |
| **Icons** | Custom SVG cloud resource icons | AWS/Azure/GCP service icons (open-source icon sets) |
| **Styling** | Tailwind CSS | Rapid styling, small bundle |
| **Bundler** | Vite | Fast builds, single-file HTML output via `vite-plugin-singlefile` |
| **State** | Zustand | Lightweight state management for filters/selections |

### Why React Flow over D3 directly
- Built-in zoom, pan, minimap, node selection
- Custom node components (perfect for cloud resource cards with badges)
- Edge routing that avoids overlaps
- Active maintenance and community

## SaaS Backend

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Framework** | FastAPI (Python) | Same language as CLI, async, auto-generated OpenAPI docs |
| **ORM** | SQLAlchemy 2.0 + Alembic | Mature, async support, migration management |
| **Database** | PostgreSQL (Neon) | Serverless, scales to zero, built-in connection pooling |
| **Auth** | Clerk | Managed auth, social login, SSO for enterprise, generous free tier |
| **Object Storage** | Cloudflare R2 | S3-compatible, zero egress fees |
| **Cache** | Upstash Redis | Serverless Redis, session store, rate limiting |
| **Background Jobs** | `arq` (Redis-based) | Lightweight async task queue for scan processing |
| **Payments** | Stripe (or Dodo Payments) | Subscription billing, usage metering |

## SaaS Frontend (Dashboard)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Framework** | Next.js 14 (App Router) | SSR for public share pages, RSC for dashboard |
| **UI Library** | shadcn/ui + Tailwind | Polished components, consistent design |
| **Charts** | Recharts | Scan history trends, cost charts |
| **Diagram** | Same React Flow component (shared) | Consistent diagram experience CLI ↔ dashboard |
| **State** | TanStack Query | Server state management, caching |
| **Deployment** | Vercel | Zero-config Next.js hosting |

## DevOps & Tooling

| Tool | Purpose |
|------|---------|
| GitHub Actions | CI/CD for CLI releases + SaaS deployment |
| GitHub Releases | CLI binary distribution (multi-platform) |
| PyPI | Python package distribution |
| Homebrew | macOS CLI installation |
| Docker | Local development, optional self-hosted deployment |
| Sentry | Error tracking (CLI + SaaS) |
| PostHog | Product analytics (dashboard usage, feature adoption) |
| Plausible | Website analytics (landing page) |

## Monorepo Structure

```
infracanvas/
├── cli/                          # Python CLI + Core Engine
│   ├── infracanvas/
│   │   ├── __init__.py
│   │   ├── main.py               # Typer CLI entrypoint
│   │   ├── parser/
│   │   │   ├── hcl.py            # HCL file parser
│   │   │   ├── state.py          # tfstate reader
│   │   │   └── plan.py           # terraform plan JSON reader
│   │   ├── graph/
│   │   │   ├── builder.py        # Resource graph construction
│   │   │   ├── models.py         # Pydantic models
│   │   │   └── layout.py         # Auto-layout algorithms
│   │   ├── security/
│   │   │   ├── engine.py         # Rule evaluation engine
│   │   │   ├── rules/            # YAML rule definitions
│   │   │   │   ├── aws/
│   │   │   │   ├── azure/
│   │   │   │   └── gcp/
│   │   │   └── models.py
│   │   ├── cost/
│   │   │   ├── estimator.py
│   │   │   └── pricing.py
│   │   ├── drift/
│   │   │   └── analyzer.py
│   │   ├── export/
│   │   │   ├── html.py           # Embed React SPA with graph data
│   │   │   ├── json.py
│   │   │   ├── svg.py
│   │   │   └── png.py
│   │   └── config.py
│   ├── tests/
│   ├── pyproject.toml
│   └── README.md
│
├── viewer/                        # React diagram viewer (embedded in CLI HTML output)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── DiagramCanvas.tsx
│   │   │   ├── ResourceNode.tsx
│   │   │   ├── FindingBadge.tsx
│   │   │   ├── FilterPanel.tsx
│   │   │   ├── DetailPanel.tsx
│   │   │   └── SummaryBar.tsx
│   │   ├── icons/                # Cloud provider resource icons
│   │   ├── hooks/
│   │   └── store/
│   ├── vite.config.ts
│   └── package.json
│
├── api/                           # FastAPI SaaS backend
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── models/
│   │   ├── services/
│   │   └── middleware/
│   ├── alembic/
│   ├── tests/
│   └── pyproject.toml
│
├── dashboard/                     # Next.js SaaS frontend
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
│
├── docs/                          # Product & architecture docs
│   ├── PLAN.md
│   ├── ARCHITECTURE.md
│   ├── TECH_STACK.md
│   └── TASKS.md
│
├── .github/workflows/
│   ├── cli-release.yml
│   ├── api-deploy.yml
│   └── dashboard-deploy.yml
│
└── README.md
```

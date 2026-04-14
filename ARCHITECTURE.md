# InfraCanvas — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI (infracanvas)                         │
│  scan │ plan │ score │ export │ serve │ login │ push             │
└───────────┬─────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Engine (Rust/Python)                   │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ HCL Parser   │  │ State Reader │  │ Plan Reader           │  │
│  │ (.tf files)  │  │ (.tfstate)   │  │ (terraform show -json)│  │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘  │
│         │                 │                       │              │
│         ▼                 ▼                       ▼              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Resource Graph Builder                       │   │
│  │  Nodes: resources, data sources, modules                  │   │
│  │  Edges: dependencies, references, implicit relationships  │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │                                        │
│         ┌───────────────┼───────────────┐                       │
│         ▼               ▼               ▼                       │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐              │
│  │ Security    │ │ Cost        │ │ Drift        │              │
│  │ Engine      │ │ Estimator   │ │ Analyzer     │              │
│  │ (30 rules)  │ │ (pricing DB)│ │ (plan diff)  │              │
│  └──────┬──────┘ └──────┬──────┘ └──────┬───────┘              │
│         │               │               │                       │
│         ▼               ▼               ▼                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Annotated Graph (unified model)              │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │                                        │
│         ┌───────────────┼───────────────┐                       │
│         ▼               ▼               ▼                       │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐              │
│  │ HTML        │ │ JSON        │ │ SVG/PNG      │              │
│  │ Renderer    │ │ Exporter    │ │ Exporter     │              │
│  │ (React SPA) │ │ (CI/CD)     │ │ (reports)    │              │
│  └─────────────┘ └─────────────┘ └──────────────┘              │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼ (optional: push to cloud)
┌─────────────────────────────────────────────────────────────────┐
│                     SaaS Backend (FastAPI)                        │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Auth     │  │ Projects │  │ Scans    │  │ Sharing        │  │
│  │ (Clerk)  │  │ API      │  │ History  │  │ & Permissions  │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PostgreSQL (projects, scans, users, teams)               │   │
│  │  S3/R2 (scan artifacts: JSON, HTML, images)               │   │
│  │  Redis (session cache, rate limiting)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SaaS Frontend (Next.js)                         │
│                                                                  │
│  Dashboard │ Project View │ Scan History │ Diagram Viewer        │
│  Team Mgmt │ Settings     │ Billing      │ Public Share View     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### Core Entities

```
Project
├── id: uuid
├── name: string
├── description: string
├── repo_url: string (optional)
├── provider: enum (aws, azure, gcp)
├── team_id: uuid (FK)
├── created_at: timestamp
└── updated_at: timestamp

Scan
├── id: uuid
├── project_id: uuid (FK)
├── trigger: enum (cli, webhook, manual)
├── status: enum (pending, running, completed, failed)
├── source_type: enum (terraform_dir, tfstate, plan_json)
├── resource_count: integer
├── finding_counts: jsonb {critical, high, medium, info}
├── estimated_monthly_cost: decimal
├── drift_summary: jsonb {added, changed, deleted}
├── score: integer (0-100)
├── artifact_url: string (S3/R2 path)
├── created_at: timestamp
└── duration_ms: integer

Resource (stored in scan artifact JSON)
├── id: string (terraform resource address)
├── type: string (aws_instance, aws_s3_bucket, etc.)
├── name: string
├── provider: string
├── module: string (optional)
├── region: string
├── attributes: jsonb (parsed from HCL/state)
├── dependencies: string[] (resource addresses)
├── findings: Finding[]
├── cost_estimate: CostEstimate
└── drift_status: enum (unchanged, added, changed, deleted)

Finding
├── rule_id: string (SEC-001, SEC-002, etc.)
├── severity: enum (critical, high, medium, info)
├── title: string
├── description: string
├── remediation: string
├── resource_address: string
└── evidence: jsonb (specific attribute that triggered)

Team
├── id: uuid
├── name: string
├── plan: enum (free, pro, team, enterprise)
├── stripe_customer_id: string
└── created_at: timestamp

User
├── id: uuid
├── clerk_id: string
├── email: string
├── team_id: uuid (FK)
├── role: enum (owner, admin, member, viewer)
└── created_at: timestamp
```

### Resource Graph Schema (JSON)

```json
{
  "version": "1.0",
  "metadata": {
    "scan_id": "uuid",
    "project": "my-infra",
    "provider": "aws",
    "scanned_at": "2026-04-14T10:00:00Z",
    "terraform_version": "1.8.0"
  },
  "nodes": [
    {
      "id": "aws_vpc.main",
      "type": "aws_vpc",
      "name": "main",
      "module": "",
      "region": "us-east-1",
      "group": "vpc-12345",
      "attributes": { "cidr_block": "10.0.0.0/16" },
      "position": { "x": 0, "y": 0 },
      "findings": [],
      "cost": { "monthly": 0, "currency": "USD" },
      "drift": "unchanged"
    }
  ],
  "edges": [
    {
      "source": "aws_subnet.public",
      "target": "aws_vpc.main",
      "type": "dependency"
    }
  ],
  "summary": {
    "total_resources": 47,
    "findings": { "critical": 2, "high": 5, "medium": 12, "info": 8 },
    "estimated_monthly_cost": 2847.50,
    "score": 68,
    "drift": { "added": 3, "changed": 1, "deleted": 0 }
  }
}
```

---

## API Contracts

### CLI → SaaS API

```
POST   /api/v1/scans              Upload scan result
GET    /api/v1/scans/:id          Get scan details
GET    /api/v1/projects            List projects
POST   /api/v1/projects            Create project
GET    /api/v1/projects/:id/scans  List scans for project
POST   /api/v1/shares              Create share link
GET    /api/v1/shares/:token       Get shared scan (public)

Headers:
  Authorization: Bearer <api-key>
  Content-Type: application/json
```

### Webhook Endpoint

```
POST /api/v1/webhooks/scan
Body: {
  "project_id": "uuid",
  "source": "github|gitlab|bitbucket",
  "ref": "main",
  "commit_sha": "abc123",
  "terraform_dir": "./infra"
}
```

---

## Security Architecture

- **Auth**: Clerk (managed auth, SSO for Enterprise)
- **API keys**: Scoped per project, rotatable, stored hashed
- **Data isolation**: Row-level security in PostgreSQL per team
- **Scan artifacts**: Encrypted at rest in S3/R2, signed URLs for access
- **No secrets stored**: InfraCanvas never sees cloud credentials — it reads local files only
- **CLI scans are local**: Nothing leaves the machine unless `infracanvas push` is explicitly run
- **Share links**: UUID + random token, optional password, expiry

---

## Infrastructure (SaaS)

### Hosting (cost-optimized for solo founder)

| Component | Choice | Monthly Cost |
|-----------|--------|-------------|
| Backend | Railway or Fly.io (FastAPI) | $10-25 |
| Frontend | Vercel (Next.js) | $0-20 |
| Database | Neon PostgreSQL (serverless) | $0-19 |
| Object Storage | Cloudflare R2 | $0-5 |
| Cache | Upstash Redis | $0-10 |
| Auth | Clerk (free tier) | $0 |
| CDN | Cloudflare | $0 |
| **Total** | | **$10-79/mo** |

### CI/CD
- GitHub Actions for CLI releases (multi-platform binaries)
- GitHub Actions for SaaS deployment (Railway/Vercel auto-deploy)
- Release channels: stable, beta

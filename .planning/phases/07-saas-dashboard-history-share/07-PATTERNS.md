# Phase 7: SaaS Dashboard + Scan History + Share Links — Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 34 new/modified files
**Analogs found:** 28 / 34 (6 net-new, no codebase analog)

---

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `dashboard/package.json` | config | — | `landing/package.json` | exact |
| `dashboard/next.config.ts` | config | — | `landing/next.config.ts` | exact |
| `dashboard/tsconfig.json` | config | — | `landing/tsconfig.json` | role-match |
| `dashboard/app/layout.tsx` | config | request-response | `landing/app/layout.tsx` | role-match |
| `dashboard/app/globals.css` | config | — | `landing/app/globals.css` | exact |
| `dashboard/middleware.ts` | middleware | request-response | none (Clerk — net-new pattern) | no analog |
| `dashboard/app/(dashboard)/layout.tsx` | component | request-response | `landing/app/layout.tsx` | role-match |
| `dashboard/app/(dashboard)/page.tsx` | component | request-response | `landing/app/page.tsx` | role-match |
| `dashboard/app/(dashboard)/scans/page.tsx` | component | request-response | `landing/app/page.tsx` | role-match |
| `dashboard/app/(dashboard)/scans/[id]/page.tsx` | component | request-response | `landing/app/page.tsx` | role-match |
| `dashboard/app/(dashboard)/compare/[from]/[to]/page.tsx` | component | request-response | `landing/app/page.tsx` | role-match |
| `dashboard/app/(dashboard)/settings/[[...slug]]/page.tsx` | component | request-response | `landing/app/page.tsx` | role-match |
| `dashboard/app/(public)/share/[token]/page.tsx` | component | request-response | `landing/app/page.tsx` | role-match |
| `dashboard/components/layout/Sidebar.tsx` | component | event-driven | none (net-new) | no analog |
| `dashboard/components/layout/TopBar.tsx` | component | event-driven | none (net-new) | no analog |
| `dashboard/components/scans/ScanTable.tsx` | component | CRUD | `viewer/src/components/FilterPanel.tsx` | role-match |
| `dashboard/components/scans/ScanFilters.tsx` | component | event-driven | `viewer/src/components/FilterPanel.tsx` | role-match |
| `dashboard/components/scans/ScanDetailHeader.tsx` | component | request-response | `viewer/src/components/SummaryBar.tsx` | role-match |
| `dashboard/components/scans/ComparePickerModal.tsx` | component | event-driven | none (net-new) | no analog |
| `dashboard/components/compare/DiffSummaryStrip.tsx` | component | request-response | `viewer/src/components/SummaryBar.tsx` | role-match |
| `dashboard/components/compare/DiffSection.tsx` | component | event-driven | `viewer/src/components/FindingCard.tsx` | role-match |
| `dashboard/components/compare/DrillDownDrawer.tsx` | component | event-driven | `viewer/src/components/DetailPanel.tsx` | role-match |
| `dashboard/components/share/ShareModal.tsx` | component | event-driven | none (net-new) | no analog |
| `dashboard/components/share/ShareLanding.tsx` | component | request-response | `viewer/src/main.tsx` | role-match |
| `dashboard/components/share/PasswordGate.tsx` | component | request-response | none (net-new) | no analog |
| `dashboard/components/home/LatestScanCard.tsx` | component | request-response | `viewer/src/components/SummaryBar.tsx` | role-match |
| `dashboard/components/home/Sparkline.tsx` | component | transform | none (net-new handrolled SVG) | no analog |
| `dashboard/components/home/TopCriticalFindings.tsx` | component | request-response | `viewer/src/components/FindingCard.tsx` | role-match |
| `dashboard/lib/api.ts` | utility | request-response | `backend/app/auth/deps.py` (fetch pattern) | partial-match |
| `dashboard/lib/types.ts` | utility | transform | `viewer/src/types.ts` | role-match |
| `dashboard/lib/utils.ts` | utility | transform | `viewer/src/lib/colors.ts` | role-match |
| `backend/app/routes/compare.py` | route | request-response | `backend/app/routes/scans.py` | exact |
| `backend/app/routes/share_links.py` | route | request-response | `backend/app/routes/scans.py` | exact |
| `backend/app/schemas/scan.py` *(extend)* | model | transform | `backend/app/schemas/scan.py` | self |
| `backend/app/db/models.py` *(extend: ShareLink)* | model | CRUD | `backend/app/db/models.py` (Scan model) | self |
| `backend/migrations/versions/005_scan_metadata_columns.py` | migration | CRUD | `backend/migrations/versions/20260424_001_initial_schema.py` | exact |
| `backend/migrations/versions/006_share_links.py` | migration | CRUD | `backend/migrations/versions/20260424_003_teams_lookup_policy.py` | exact |
| `backend/pyproject.toml` *(extend: add bcrypt)* | config | — | self | self |
| `package.json` *(root: add dashboard workspace)* | config | — | self (`workspaces: ["viewer"]`) | self |

---

## Pattern Assignments

### `dashboard/package.json` + `dashboard/next.config.ts` + `dashboard/tsconfig.json`

**Analog:** `landing/package.json` + `landing/next.config.ts` + `landing/tsconfig.json`

**Package.json pattern** (`landing/package.json`, lines 1–24):
```json
{
  "name": "infracanvas-landing",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4.1.0",
    "@types/node": "25.6.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "tailwindcss": "^4.1.0",
    "typescript": "^5.8.0"
  }
}
```

**Dashboard diverges from landing in three ways:**
1. `name` → `"infracanvas-dashboard"`
2. Add deps: `@clerk/nextjs`, `lucide-react`, `@infracanvas/viewer`, `react-day-picker`, plus all shadcn/ui radix primitives
3. Add devDep: `@types/bcryptjs` is not needed (bcrypt is backend-only)

**Root workspace extension** (`package.json`, full file — 4 lines):
```json
{
  "name": "infracanvas-monorepo",
  "private": true,
  "workspaces": ["viewer"]
}
```
Change `"workspaces"` to `["viewer", "dashboard"]`.

---

### `dashboard/app/layout.tsx` (root layout — html/body only)

**Analog:** `landing/app/layout.tsx` (lines 1–43)

**Import pattern** (lines 1–6):
```typescript
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import './globals.css'
```

**Font loading pattern** (lines 7–10):
```typescript
const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
})
```
Dashboard adds a second font: `import { JetBrains_Mono } from 'next/font/google'` for `--font-mono` (commit SHAs, scan IDs).

**Root layout shell** (lines 25–43):
```typescript
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`dark ${inter.className}`}>
      <body className="bg-slate-950 text-slate-50 antialiased">
        <header><Nav /></header>
        <main>{children}</main>
        <footer><Footer /></footer>
      </body>
    </html>
  )
}
```
Dashboard changes: remove `dark`, remove `bg-slate-950 text-slate-50`, use `bg-white text-slate-900`. Remove Nav/Footer. **No `<ClerkProvider>` here** — ClerkProvider lives in `(dashboard)/layout.tsx` only (Pitfall 3 from RESEARCH.md).

**globals.css pattern** (`landing/app/globals.css`, line 1):
```css
@import "tailwindcss";
```
Dashboard `globals.css` adds `@import "@infracanvas/viewer/styles.css"` **before** `@import "tailwindcss"` so viewer's `--color-sev-*` tokens are available as utility classes (Pitfall 5).

---

### `dashboard/middleware.ts` (middleware, request-response)

**Analog:** None in codebase. Pattern from RESEARCH.md Pattern 2.

**Full pattern** (RESEARCH.md lines 317–339):
```typescript
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isPublicRoute = createRouteMatcher([
  '/share(.*)',
  '/sign-in(.*)',
  '/sign-up(.*)',
])

export default clerkMiddleware(async (auth, req) => {
  if (!isPublicRoute(req)) {
    await auth.protect()
  }
})

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
}
```

---

### `dashboard/app/(dashboard)/layout.tsx` (app shell — sidebar + top bar)

**Analog:** `landing/app/layout.tsx` (structure only)

**Pattern:** This layout wraps all authenticated routes. It provides `<ClerkProvider>`, the 220px fixed sidebar, and the 48px top bar. Children render in the remaining space.

```typescript
import { ClerkProvider } from '@clerk/nextjs'
import { Inter, JetBrains_Mono } from 'next/font/google'
import { Sidebar } from '@/components/layout/Sidebar'
import { TopBar } from '@/components/layout/TopBar'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <div className="flex h-screen bg-white">
        <Sidebar />
        <div className="flex flex-col flex-1 min-w-0">
          <TopBar />
          <main className="flex-1 overflow-auto">{children}</main>
        </div>
      </div>
    </ClerkProvider>
  )
}
```

---

### `dashboard/app/(dashboard)/page.tsx` + `dashboard/app/(dashboard)/scans/page.tsx` + `dashboard/app/(dashboard)/scans/[id]/page.tsx` + `dashboard/app/(dashboard)/compare/[from]/[to]/page.tsx` (RSC pages)

**Analog:** `landing/app/page.tsx` (RSC default export pattern, lines 1–19) + RESEARCH.md Patterns 1 + 4

**RSC data-fetch pattern** (RESEARCH.md lines 285–311 — `dashboard/lib/api.ts`):
```typescript
import { auth } from '@clerk/nextjs/server'

export async function backendFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const { getToken } = await auth()
  const token = await getToken()
  const res = await fetch(`${process.env.BACKEND_URL}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    cache: 'no-store',   // Per-user data — never cache on Vercel
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json() as Promise<T>
}
```

**Next.js 15 async params pattern** (RESEARCH.md lines 479–492 — Pitfall 1):
```typescript
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>
  searchParams: Promise<{ branch?: string }>
}) {
  const { id } = await params          // MUST await — Next.js 15 breaking change
  const { branch } = await searchParams
  // ...
}
```

**URL searchParams → backend filters pattern** (RESEARCH.md lines 374–397):
```typescript
// dashboard/app/(dashboard)/scans/page.tsx (RSC)
export default async function ScansPage({
  searchParams,
}: {
  searchParams: Promise<{ branch?: string; source?: string; from?: string; to?: string; score_lt?: string; page?: string; sort?: string; order?: string }>
}) {
  const sp = await searchParams
  const qs = new URLSearchParams()
  if (sp.branch) qs.set('branch', sp.branch)
  if (sp.source) qs.set('source', sp.source)
  if (sp.from) qs.set('created_after', sp.from)
  if (sp.to) qs.set('created_before', sp.to)
  if (sp.score_lt) qs.set('score_lt', sp.score_lt)
  if (sp.page) qs.set('cursor', sp.page)
  if (sp.sort) qs.set('sort', sp.sort)
  if (sp.order) qs.set('order', sp.order)
  qs.set('limit', '25')
  const data = await backendFetch<ScanListResp>(`/v1/scans?${qs}`)
  return <ScanTable data={data} />
}
```

**Viewer client wrapper pattern** (RESEARCH.md lines 343–368):
```typescript
// dashboard/components/scans/ScanViewer.tsx
'use client'
import { ViewerProvider, DiagramCanvas } from '@infracanvas/viewer'
import '@infracanvas/viewer/styles.css'
import type { ResourceGraph } from '@infracanvas/viewer'

interface Props { scan: ResourceGraph }

export function ScanViewer({ scan }: Props) {
  return (
    <ViewerProvider scan={scan}>
      <DiagramCanvas />
    </ViewerProvider>
  )
}
// In RSC page: pass only scan_id → client component fetches fresh presigned URL on mount
// (Pitfall 2: never embed presigned URL in RSC HTML — it may expire before JS hydrates)
```

---

### `dashboard/components/scans/ScanTable.tsx` + `ScanFilters.tsx` (component, CRUD / event-driven)

**Analog:** `viewer/src/components/FilterPanel.tsx`

**'use client' + Zustand-free local state pattern** — viewer's FilterPanel uses `useStore` (Zustand), but the dashboard scan table manages filter state via URL searchParams + `router.push`. Use `'use client'` with `useRouter` + `useSearchParams` from `next/navigation`:

```typescript
'use client'
import { useRouter, useSearchParams } from 'next/navigation'
import { useCallback } from 'react'

export function ScanFilters() {
  const router = useRouter()
  const sp = useSearchParams()

  const updateFilter = useCallback((key: string, value: string) => {
    const next = new URLSearchParams(sp.toString())
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('page')   // reset pagination on filter change
    router.push(`/scans?${next}`)
  }, [router, sp])
  // ...
}
```

**tabular-nums for score/count columns** (UI-SPEC typography contract):
```typescript
// Table cells with numbers use tabular-nums for column alignment
<td className="tabular-nums text-sm">{scan.summary_json?.findings?.critical ?? 0}</td>
```

---

### `dashboard/components/compare/DiffSection.tsx` + `DrillDownDrawer.tsx` (component, event-driven)

**Analog:** `viewer/src/components/FindingCard.tsx` (expandable row pattern) + `viewer/src/components/DetailPanel.tsx` (drawer/panel pattern)

**'use client' expandable row pattern** — copy the accordion expand/collapse from FindingCard:
```typescript
'use client'
import { useState } from 'react'
import { ChevronRight } from 'lucide-react'

export function DiffSection({ title, items, color }: DiffSectionProps) {
  const [open, setOpen] = useState(true)
  return (
    <div>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 w-full text-left py-2"
      >
        <ChevronRight className={`h-4 w-4 transition-transform ${open ? 'rotate-90' : ''}`} />
        <span className="text-sm font-semibold">{title}</span>
      </button>
      {open && items.map(item => <DiffRow key={item.id} item={item} />)}
    </div>
  )
}
```

**DrillDownDrawer uses shadcn `<Sheet>`** — no analog in codebase; use shadcn Sheet primitive with `<ViewerProvider>` inside.

---

### `dashboard/components/home/Sparkline.tsx` (component, transform)

**Analog:** None in codebase. UI-SPEC mandates handrolled SVG (~20 LOC), no Recharts.

**Pattern** (UI-SPEC locked: 10-point polyline, min/max dots, no axes, no tooltips):
```typescript
// 'use client' — SVG refs need browser
'use client'
interface Props { scores: number[] }  // up to 10 data points

export function Sparkline({ scores }: Props) {
  const W = 120, H = 32, PAD = 4
  const min = Math.min(...scores), max = Math.max(...scores)
  const range = max - min || 1
  const pts = scores.map((s, i) => {
    const x = PAD + (i / (scores.length - 1)) * (W - PAD * 2)
    const y = H - PAD - ((s - min) / range) * (H - PAD * 2)
    return `${x},${y}`
  })
  return (
    <svg width={W} height={H} className="overflow-visible">
      <polyline fill="none" stroke="currentColor" strokeWidth={2} points={pts.join(' ')} />
    </svg>
  )
}
```

---

### `dashboard/lib/types.ts` (utility, transform)

**Analog:** `viewer/src/types.ts`

**Import pattern** — re-export viewer types rather than duplicating:
```typescript
// dashboard/lib/types.ts
export type {
  ResourceGraph,
  GraphSummary,
  Finding,
  Severity,
  DriftStatus,
} from '@infracanvas/viewer'

// Dashboard-specific API response types (not in viewer):
export interface ScanListItem {
  id: string
  team_id: string
  status: 'pending' | 'ready' | 'failed'
  created_at: string
  size_bytes: number | null
  summary_json: {
    score: number
    findings: { critical: number; high: number; medium: number; info: number }
    drift: Record<string, number>
    total_resources: number
  } | null
  branch: string | null
  commit_sha: string | null
  source: 'cli' | 'manual' | 'github_webhook' | null
}

export interface ScanListResp {
  items: ScanListItem[]
  next_cursor: string | null
}

export interface ScanGetResp {
  id: string
  team_id: string
  status: string
  presigned_get_url: string
  size_bytes: number | null
  created_at: string
  summary_json: ScanListItem['summary_json']
  branch: string | null
  commit_sha: string | null
  source: string | null
}

export interface ResourceDiff {
  added: Array<{ id: string; type: string; attributes: Record<string, unknown> }>
  removed: Array<{ id: string; type: string; attributes: Record<string, unknown> }>
  changed: Array<{
    id: string
    type: string
    attribute_deltas: Array<{ key: string; before: unknown; after: unknown }>
  }>
  findings_delta: { critical: number; high: number; medium: number; info: number }
}

export interface ShareLink {
  id: string
  expires_at: string | null
  created_by: string
  has_password: boolean
  created_at: string
}

export interface ShareLinkCreateResp {
  id: string
  token: string   // raw token — returned ONCE, never stored raw
  url: string
  expires_at: string | null
}
```

---

### `backend/app/routes/compare.py` (route, request-response)

**Analog:** `backend/app/routes/scans.py` — exact match on role and data flow

**Import pattern** (scans.py lines 35–62):
```python
from __future__ import annotations

import asyncio
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from infracanvas.graph.models import ResourceGraph

from app.auth.clerk import ClerkPrincipal, require_role
from app.auth.deps import resolve_team_from_clerk_org
from app.db.models import Scan, Team
from app.db.session import get_sessionmaker
from app.schemas.compare import ResourceDiffResp   # new schema
from app.storage import r2
```

**Auth + team-scoped session pattern** (scans.py lines 276–319):
```python
@router.get("/{scan_a_id}/compare/{scan_b_id}", response_model=ResourceDiffResp)
async def compare_scans(
    scan_a_id: UUID,
    scan_b_id: UUID,
    principal: ClerkPrincipal = Depends(  # noqa: B008
        require_role("owner", "admin", "member", "basic_member")
    ),
    team: Team = Depends(resolve_team_from_clerk_org),
) -> ResourceDiffResp:
    sm = get_sessionmaker()
    async with sm() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team.id)},
            )
            row_a = (
                await session.execute(select(Scan).where(Scan.id == scan_a_id))
            ).scalar_one_or_none()
            row_b = (
                await session.execute(select(Scan).where(Scan.id == scan_b_id))
            ).scalar_one_or_none()
            if row_a is None or row_b is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "scan_not_found")
    # Concurrent R2 fetch (Pitfall 7: never sequential for two large blobs)
    blob_a, blob_b = await asyncio.gather(
        run_in_threadpool(r2.get_bytes, row_a.r2_key),
        run_in_threadpool(r2.get_bytes, row_b.r2_key),
    )
    graph_a = ResourceGraph.model_validate_json(blob_a)
    graph_b = ResourceGraph.model_validate_json(blob_b)
    return _compute_diff(graph_a, graph_b)
```

**404 pattern** — cross-team scan returns 404, not 403 (D-18 locked). Copy exactly from `get_scan`: `raise HTTPException(status.HTTP_404_NOT_FOUND, "scan_not_found")`.

**Error handling pattern** (scans.py lines 147–174):
```python
try:
    blob = await run_in_threadpool(r2.get_bytes, pending)
except ClientError as e:
    code = e.response.get("Error", {}).get("Code", "")
    if code in ("404", "NoSuchKey", "NotFound"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "object_not_found") from e
    raise
```

---

### `backend/app/routes/share_links.py` (route, request-response)

**Analog:** `backend/app/routes/scans.py` — exact match

**Import pattern** — same as compare.py plus:
```python
import secrets
import bcrypt   # NEW dep — must be in pyproject.toml before this file is written
from app.db.models import ShareLink   # new model
from app.schemas.share_links import (
    ShareLinkCreateReq, ShareLinkCreateResp,
    ShareLinkPublicResp, ShareLinkUnlockReq,
)
```

**Auth'd create endpoint pattern** (mirrors scans.py commit pattern, lines 177–216):
```python
@router.post("/{scan_id}/share-links", response_model=ShareLinkCreateResp, status_code=201)
async def create_share_link(
    scan_id: UUID,
    body: ShareLinkCreateReq,
    principal: ClerkPrincipal = Depends(require_role("owner", "admin", "member", "basic_member")),
    team: Team = Depends(resolve_team_from_clerk_org),
) -> ShareLinkCreateResp:
    raw_token = secrets.token_urlsafe(32)
    token_hash = await run_in_threadpool(bcrypt.hashpw, raw_token.encode(), bcrypt.gensalt())
    password_hash = None
    if body.password:
        password_hash = await run_in_threadpool(bcrypt.hashpw, body.password.encode(), bcrypt.gensalt())
    sm = get_sessionmaker()
    async with sm() as session:
        async with session.begin():
            await session.execute(
                text("SELECT set_config('app.current_team_id', :t, true)"),
                {"t": str(team.id)},
            )
            # ... verify scan belongs to team (404 if not), INSERT ShareLink row
```

**Public endpoint pattern** (no auth dep — note absence of `require_role` and `resolve_team_from_clerk_org`):
```python
@router.get("/{token}", response_model=ShareLinkPublicResp)
async def get_share_link(token: str) -> ShareLinkPublicResp:
    """Public endpoint — no Clerk JWT required.

    Uses share_link_by_token() SECURITY DEFINER function (migration 006)
    to look up by token_hash without opening a permissive SELECT policy
    on share_links (Pitfall 6 from RESEARCH.md).
    """
    sm = get_sessionmaker()
    async with sm() as session:
        async with session.begin():
            row = await _lookup_share_link_by_token(session, token)
            if row is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
            if row.revoked_at is not None:
                raise HTTPException(status.HTTP_410_GONE, "revoked")
            if row.expires_at and row.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status.HTTP_410_GONE, "expired")
            if row.password_hash is not None:
                return ShareLinkPublicResp(password_required=True)
            # No password — return presigned URL
            get_url = await run_in_threadpool(r2.presigned_get, row.scan.r2_key, _GET_TTL_SECONDS)
            return ShareLinkPublicResp(password_required=False, presigned_get_url=get_url, ...)
```

---

### `backend/app/db/models.py` — extend with `ShareLink` model

**Analog:** `backend/app/db/models.py` `Scan` model (lines 47–68)

**New model pattern** — copy `Scan` structure exactly, adding FK to `scans`:
```python
class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)   # clerk_user_id
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

**Import additions needed** (models.py lines 13–16):
```python
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
# Already present — no new imports needed for ShareLink except confirm String is imported
```

---

### `backend/app/schemas/scan.py` — extend with new fields + list types

**Analog:** `backend/app/schemas/scan.py` (full file — 68 lines)

**Strict request config pattern** (lines 22–23):
```python
_STRICT = ConfigDict(strict=True, extra="forbid")
```
All new request models (`ScanCommitReq` extension, `ShareLinkCreateReq`, `ShareLinkUnlockReq`) use `_STRICT`.

**Response model pattern** (lines 52–68 — `ScanGetResp`):
```python
class ScanGetResp(BaseModel):
    id: UUID
    team_id: UUID
    status: ScanStatus
    presigned_get_url: str
    size_bytes: int | None
    created_at: datetime
    summary_json: dict[str, Any] | None = None
```
Add new nullable fields to `ScanGetResp` (and new `ScanListItemResp`):
```python
    branch: str | None = None
    commit_sha: str | None = None
    source: str | None = None
```
Extend `ScanCommitReq` to accept these at commit time:
```python
class ScanCommitReq(BaseModel):
    model_config = _STRICT
    sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    branch: str | None = None
    commit_sha: str | None = Field(default=None, max_length=40)
    source: str | None = None
```

---

### `backend/migrations/versions/005_scan_metadata_columns.py` (migration, CRUD)

**Analog:** `backend/migrations/versions/20260424_001_initial_schema.py` — `op.create_table` / `op.add_column` pattern

**Import + header pattern** (001 lines 1–19):
```python
"""scan metadata columns: branch, commit_sha, source

Revision ID: 005_scan_metadata_columns
Revises: 004_scan_team_id_helper
Create Date: 2026-04-28
"""
from __future__ import annotations
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "005_scan_metadata_columns"
down_revision: Union[str, None] = "004_scan_team_id_helper"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**Add column pattern** (001 lines 22–73 — `op.create_table` structure):
```python
def upgrade() -> None:
    op.add_column("scans", sa.Column("branch", sa.String(255), nullable=True))
    op.add_column("scans", sa.Column("commit_sha", sa.String(40), nullable=True))
    op.add_column("scans", sa.Column("source", sa.String(32), nullable=True))
    op.create_index("ix_scans_branch", "scans", ["branch"])
    op.create_index("ix_scans_source", "scans", ["source"])

def downgrade() -> None:
    op.drop_index("ix_scans_source", "scans")
    op.drop_index("ix_scans_branch", "scans")
    op.drop_column("scans", "source")
    op.drop_column("scans", "commit_sha")
    op.drop_column("scans", "branch")
```

---

### `backend/migrations/versions/006_share_links.py` (migration, CRUD + RLS)

**Analog:** `backend/migrations/versions/20260424_003_teams_lookup_policy.py` — SECURITY DEFINER pattern (lines 71–91)

**Header pattern** (003 lines 1–29):
```python
"""share_links table, RLS policies, share_link_by_token() SECURITY DEFINER helper

Revision ID: 006_share_links
Revises: 005_scan_metadata_columns
Create Date: 2026-04-28
"""
```

**Table + RLS pattern** (based on 002_rls_setup.py lines 54–74):
```python
def upgrade() -> None:
    op.create_table("share_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("share_links_token_hash_key", "share_links", ["token_hash"])
    op.create_index("ix_share_links_team_id", "share_links", ["team_id"])
    op.create_index("ix_share_links_expires_at", "share_links", ["expires_at"])

    # GRANT to app role (same as 002_rls_setup.py lines 42–48)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON share_links TO infracanvas_app;")

    # Enable + FORCE RLS (same as 002_rls_setup.py lines 54–57)
    op.execute("ALTER TABLE share_links ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE share_links FORCE ROW LEVEL SECURITY;")

    # Authenticated team-member policies (same pattern as scans_team_isolation in 002)
    op.execute("""
        CREATE POLICY share_links_team_isolation ON share_links
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
    """)
```

**SECURITY DEFINER for public token lookup** (mirrors 003 lines 75–91 exactly):
```python
    # share_link_by_token() — public lookup without opening a permissive SELECT
    # policy. Mirrors team_by_clerk_org() pattern from migration 003.
    # Pitfall 6: returning ONLY the columns needed prevents cross-team metadata leak.
    op.execute("""
        CREATE OR REPLACE FUNCTION share_link_by_token(p_token_hash text)
        RETURNS share_links
        LANGUAGE sql
        SECURITY DEFINER
        STABLE
        SET search_path = public
        AS $$
          SELECT * FROM share_links
          WHERE token_hash = p_token_hash
            AND revoked_at IS NULL
          LIMIT 1;
        $$;
    """)
    op.execute("REVOKE ALL ON FUNCTION share_link_by_token(text) FROM PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION share_link_by_token(text) TO infracanvas_app;")
```

---

## Shared Patterns

### Team-Scoped Session (all authenticated backend routes)

**Source:** `backend/app/routes/scans.py` lines 294–319 (`get_scan` handler)
**Apply to:** `compare.py`, `share_links.py` (all auth'd endpoints)

```python
sm = get_sessionmaker()
async with sm() as session:
    async with session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        # ... queries run here under RLS
        row = (await session.execute(select(Model).where(...))).scalar_one_or_none()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
```

### Auth Dependencies (all authenticated backend routes)

**Source:** `backend/app/routes/scans.py` lines 99–104 + `backend/app/auth/deps.py`
**Apply to:** All `@router.post/get/delete` handlers in `compare.py` and `share_links.py` (auth'd endpoints)

```python
principal: ClerkPrincipal = Depends(  # noqa: B008
    require_role("owner", "admin", "member", "basic_member")
),
team: Team = Depends(resolve_team_from_clerk_org),
```
Note: public share-link endpoints (`GET /v1/share-links/{token}`, `POST /v1/share-links/{token}/unlock`) have **no auth deps** — they call `share_link_by_token()` SECURITY DEFINER directly.

### 404 Not Leaking Cross-Team Existence (all backend routes)

**Source:** `backend/app/routes/scans.py` lines 303–307
**Apply to:** All `get_scan`-style handlers in `compare.py` and `share_links.py`

```python
if row is None:
    raise HTTPException(status.HTTP_404_NOT_FOUND, "scan_not_found")
# NOT 403 — 404 is intentional: don't confirm cross-team scan existence (D-18)
```

### Pydantic Schema Config (all new request bodies)

**Source:** `backend/app/schemas/scan.py` lines 22–23
**Apply to:** `ScanCommitReq` extension, `ShareLinkCreateReq`, `ShareLinkUnlockReq`, `ResourceDiffResp`

```python
_STRICT = ConfigDict(strict=True, extra="forbid")   # request models
# Response models: no ConfigDict (forward-compat, allow extra fields)
```

### R2 Presigned GET Pattern (compare + share routes)

**Source:** `backend/app/routes/scans.py` lines 262–269
**Apply to:** `compare.py` (after diff), `share_links.py` (after token verify)

```python
_GET_TTL_SECONDS = 300
get_url = await run_in_threadpool(r2.presigned_get, row.r2_key, _GET_TTL_SECONDS)
```

### Alembic Migration Header (all new migrations)

**Source:** `backend/migrations/versions/20260424_001_initial_schema.py` lines 1–19
**Apply to:** `005_scan_metadata_columns.py`, `006_share_links.py`

```python
from __future__ import annotations
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "00N_name"
down_revision: Union[str, None] = "00N-1_previous"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

### SECURITY DEFINER Function Pattern (migration 006)

**Source:** `backend/migrations/versions/20260424_003_teams_lookup_policy.py` lines 75–91
**Apply to:** `006_share_links.py` `share_link_by_token()` function

```python
op.execute("""
    CREATE OR REPLACE FUNCTION <name>(<args>)
    RETURNS <type>
    LANGUAGE sql
    SECURITY DEFINER
    STABLE
    SET search_path = public
    AS $$ SELECT ... $$;
""")
op.execute("REVOKE ALL ON FUNCTION <name>(<args>) FROM PUBLIC;")
op.execute("GRANT EXECUTE ON FUNCTION <name>(<args>) TO infracanvas_app;")
```

### 'use client' + Lucide Icon Pattern (dashboard components)

**Source:** `viewer/src/components/FindingCard.tsx` (existing viewer component)
**Apply to:** `ScanTable.tsx`, `ScanFilters.tsx`, `DiffSection.tsx`, `DrillDownDrawer.tsx`, `ShareModal.tsx`, `PasswordGate.tsx`, `ComparePickerModal.tsx`

```typescript
'use client'
import { ChevronRight, Copy, ExternalLink, X } from 'lucide-react'
// icons: 16px (h-4 w-4) for inline, 20px (h-5 w-5) for standalone buttons
```

### Tailwind v4 — No Config File

**Source:** `landing/app/globals.css` (line 1), `viewer/src/lib-styles.css`
**Apply to:** `dashboard/app/globals.css`

```css
/* FIRST: viewer severity tokens */
@import "@infracanvas/viewer/styles.css";
/* SECOND: Tailwind v4 — single import, no tailwind.config.js */
@import "tailwindcss";
/* THIRD: shadcn CSS vars (generated by shadcn init) */
@layer base { :root { --background: 0 0% 100%; /* ... */ } }
```
No `tailwind.config.js` is created. All custom tokens go in `@theme {}` blocks inside this file.

### Score Grade Pill (reused across multiple dashboard pages)

**Source:** UI-SPEC Color section — grade pill spec
**Apply to:** `LatestScanCard.tsx`, `ScanTable.tsx`, `ScanDetailHeader.tsx`, `ShareLanding.tsx`

```typescript
const GRADE_STYLES: Record<string, string> = {
  'A+': 'bg-green-100 text-green-700',
  'A':  'bg-green-100 text-green-700',
  'B+': 'bg-sky-100 text-sky-700',
  'B':  'bg-sky-100 text-sky-700',
  'C':  'bg-amber-100 text-amber-700',
  'D':  'bg-orange-100 text-orange-700',
  'F':  'bg-red-100 text-red-700',
}
function scoreToGrade(score: number): string {
  if (score >= 90) return score >= 95 ? 'A+' : 'A'
  if (score >= 80) return score >= 85 ? 'B+' : 'B'
  if (score >= 70) return 'C'
  if (score >= 60) return 'D'
  return 'F'
}
```

---

## No Analog Found

Files with no close match in the codebase — planner should use RESEARCH.md patterns and vendor docs:

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `dashboard/middleware.ts` | middleware | request-response | No Clerk middleware exists in codebase. Use RESEARCH.md Pattern 2 verbatim. |
| `dashboard/components/layout/Sidebar.tsx` | component | event-driven | No sidebar component exists. Use shadcn + Clerk `<OrganizationSwitcher/>` + `<UserButton/>`. |
| `dashboard/components/layout/TopBar.tsx` | component | event-driven | No top bar component. Use `next/navigation` `usePathname` for breadcrumbs. |
| `dashboard/components/scans/ComparePickerModal.tsx` | component | event-driven | No picker modal exists. Use shadcn `<Dialog>` + `<Command>` (search). |
| `dashboard/components/share/ShareModal.tsx` | component | event-driven | No share-link UI exists. Use shadcn `<Dialog>` + `<Select>` + `<Input>`. |
| `dashboard/components/share/PasswordGate.tsx` | component | request-response | No password gate page exists. Use shadcn `<Form>` + `<Input type="password">`. |
| `dashboard/components/home/Sparkline.tsx` | component | transform | No chart component exists. Handrolled SVG per UI-SPEC (20 LOC polyline). |

---

## New Dependencies (not yet in codebase)

These must be installed before implementing the files that use them:

| Dependency | Location | Why New | Install |
|------------|----------|---------|---------|
| `bcrypt>=4.0,<5` | `backend/pyproject.toml` | Share-link token + password hashing (D-16). No bcrypt in backend venv [VERIFIED: RESEARCH.md]. | `uv add bcrypt` in `backend/` |
| `@clerk/nextjs` | `dashboard/package.json` | Clerk Next.js integration. Not in `landing/` (landing is anonymous). | `npm install @clerk/nextjs` in `dashboard/` |
| `react-day-picker@9.14.0` | `dashboard/package.json` | shadcn `<Calendar/>` dep for date-range filter on `/scans`. | `npm install react-day-picker` in `dashboard/` |
| `@infracanvas/viewer` | `dashboard/package.json` | Workspace link to viewer package. Requires `viewer/` to be built first. | `npm install @infracanvas/viewer` after adding to workspaces |
| shadcn/ui components | `dashboard/components/ui/` | Generated by `npx shadcn@latest add button dialog alert-dialog select input table tabs sheet skeleton sonner pagination calendar popover form label card dropdown-menu` | Run after `npx shadcn@latest init` |

---

## Metadata

**Analog search scope:** `backend/app/routes/`, `backend/app/db/`, `backend/app/auth/`, `backend/app/schemas/`, `backend/migrations/versions/`, `landing/app/`, `viewer/src/`
**Files scanned:** 12 source files read directly; 4 via grep outline
**Pattern extraction date:** 2026-04-28

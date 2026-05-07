# Phase 10: DC Agent Core - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 12 new/modified files
**Analogs found:** 8 / 12 (4 Go files have no codebase analog — greenfield Go module)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `agent/go.mod` | config | — | none (no Go in repo) | no analog |
| `agent/cmd/infracanvas-agent/main.go` | controller | event-driven | `.github/workflows/ci.yml` job structure + RESEARCH Pattern 1 | partial |
| `agent/internal/config/config.go` | utility | request-response | `cli/infracanvas/config.py` (YAML walk-up) | role-match |
| `agent/internal/netconf/collector.go` | service | request-response | none (no NETCONF in repo) | no analog |
| `agent/internal/ssh/collector.go` | service | request-response | none (no SSH client in repo) | no analog |
| `agent/internal/netflow/listener.go` | service | event-driven | none (no UDP listener in repo) | no analog |
| `agent/internal/netflow/buffer.go` | utility | batch | none (no ring buffer in repo) | no analog |
| `agent/internal/push/client.go` | service | request-response | `backend/app/storage/r2.py` (HTTP client + retry) | partial |
| `backend/app/routes/agent.py` | controller | request-response | `backend/app/routes/integrations.py` + `webhooks.py` | exact |
| `backend/migrations/versions/20260507_010_dc_sites.py` | migration | CRUD | `backend/migrations/versions/20260428_006_share_links.py` | exact |
| `.github/workflows/release.yml` | config | batch | existing `.github/workflows/release.yml` | exact (extend) |
| `agent/docs/cab/` | documentation | — | none | no analog |

---

## Pattern Assignments

### `backend/app/routes/agent.py` (controller, request-response)

**Analog:** `backend/app/routes/integrations.py` (POST with Pydantic body + per-route Depends) and `backend/app/routes/webhooks.py` (Bearer token extraction without Clerk JWT)

**Imports pattern** (`integrations.py` lines 1–18, `webhooks.py` lines 33–51):
```python
from __future__ import annotations

import hashlib
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_sessionmaker
# NEW: site-token auth dep (parallel path to require_principal)
from app.auth.site_token import DCSitePrincipal, require_site_token

router = APIRouter(prefix="/v1", tags=["agent"])
_log = structlog.get_logger("app.agent")
```

**Bearer token extraction pattern** (`webhooks.py` lines 61–66 — `_bearer` private helper in `clerk.py`):
```python
# From backend/app/auth/clerk.py lines 61-66
def _bearer(request: Request) -> str:
    """Extract Bearer token from Authorization header. 401 if missing/malformed."""
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_bearer")
    return h.split(" ", 1)[1].strip()
```

**Site-token dependency function** (new `backend/app/auth/site_token.py` — mirrors `clerk.py` `require_principal` shape, lines 69–100):
```python
# Pattern source: backend/app/auth/clerk.py require_principal (lines 69-100)
# + share_links SHA-256 lookup hash (migration 006, lines 8-14)
import hashlib
from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import raw_session

class DCSitePrincipal(BaseModel):
    team_id: str
    site_id: str

async def require_site_token(
    request: Request,
    session: AsyncSession = Depends(raw_session),
) -> DCSitePrincipal:
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_bearer")
    raw_token = h.split(" ", 1)[1].strip()
    lookup_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    # SELECT dc_sites WHERE token_lookup_hash = lookup_hash
    # (same indexed lookup as share_links.token_lookup_hash)
    ...
    if site is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_site_token")
    return DCSitePrincipal(team_id=str(site.team_id), site_id=str(site.id))
```

**POST endpoint pattern with Pydantic body + per-route Depends** (`integrations.py` lines 25–60):
```python
# From backend/app/routes/integrations.py lines 25-60
class SlackWebhookBody(BaseModel):
    webhook_url: str

@router.patch("/slack", status_code=200)
async def save_slack_webhook(
    body: SlackWebhookBody,
    principal: ClerkPrincipal = Depends(require_role(*_WRITE_ROLES)),  # noqa: B008
    team: Team = Depends(resolve_team_from_clerk_org),  # noqa: B008
) -> dict[str, str]:
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        ...
    _log.info("slack_webhook_saved", team_id=str(team.id))
    return {"message": "..."}
```

**Agent route shape** — `POST /v1/sites`, `POST /v1/agent/routes`, `POST /v1/agent/flows`:
```python
# POST /v1/sites — uses require_role("owner") (Clerk auth, same as github.py)
# POST /v1/agent/routes — uses require_site_token (site-token auth, NOT Clerk)
# POST /v1/agent/flows  — uses require_site_token (site-token auth, NOT Clerk)

class RoutesPushBody(BaseModel):
    site_id: str
    collected_at: str
    device_host: str
    routes: list[RouteRecord]

@router.post("/agent/routes", status_code=202)
async def push_routes(
    body: RoutesPushBody,
    principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
) -> dict[str, bool]:
    _log.info("agent_routes_received", site_id=principal.site_id, count=len(body.routes))
    return {"ok": True}
```

**Router registration in `main.py`** (`main.py` lines 37–48):
```python
# From backend/app/main.py lines 41-48 — follow same include_router pattern
from app.routes import agent as agent_routes
app.include_router(agent_routes.router)
```

**Error response pattern** (`webhooks.py` lines 86–98):
```python
# Consistent error string codes (not sentences) — e.g. "missing_bearer", "invalid_site_token"
raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_bearer")
raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_site_token")
raise HTTPException(status.HTTP_404_NOT_FOUND, "site_not_found")
```

---

### `backend/migrations/versions/20260507_010_dc_sites.py` (migration, CRUD)

**Analog:** `backend/migrations/versions/20260428_006_share_links.py` (exact match — new table with SHA-256 lookup hash + RLS team_isolation policy)

**File header + revision chain** (`006_share_links.py` lines 16–27):
```python
"""dc_sites table + site-token hashed storage (Phase 10 DCA-05).

Revision ID: 010_dc_sites
Revises: 009_slack_webhook_url
Create Date: 2026-05-07
"""
from __future__ import annotations
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_dc_sites"
down_revision: Union[str, None] = "009_slack_webhook_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**Table creation with UUID PK + team FK + token_lookup_hash** (`006_share_links.py` lines 30–67):
```python
# From backend/migrations/versions/20260428_006_share_links.py lines 30-67
def upgrade() -> None:
    op.create_table(
        "dc_sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        # SHA-256 hex of raw site token — deterministic, used for indexed SELECT
        # (same pattern as share_links.token_lookup_hash, migration 006 lines 53-54)
        sa.Column("token_lookup_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
```

**Unique index on token_lookup_hash** (`006_share_links.py` lines 69–78):
```python
    # From backend/migrations/versions/20260428_006_share_links.py lines 70-78
    op.create_unique_constraint(
        "dc_sites_token_lookup_hash_key", "dc_sites", ["token_lookup_hash"]
    )
    op.create_index("ix_dc_sites_team_id", "dc_sites", ["team_id"])
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON dc_sites TO infracanvas_app;")
```

**RLS team_isolation policy** (`006_share_links.py` lines 85–96):
```python
    # From backend/migrations/versions/20260428_006_share_links.py lines 85-96
    op.execute("ALTER TABLE dc_sites ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE dc_sites FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY dc_sites_team_isolation ON dc_sites
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
        """
    )
```

**downgrade pattern** (`006_share_links.py` lines 130–142):
```python
def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS dc_sites_team_isolation ON dc_sites;")
    op.drop_index("ix_dc_sites_team_id", table_name="dc_sites")
    op.drop_constraint("dc_sites_token_lookup_hash_key", "dc_sites", type_="unique")
    op.drop_table("dc_sites")
```

---

### `.github/workflows/release.yml` (config, batch — extend existing)

**Analog:** `.github/workflows/release.yml` (exact — add `build-agent` job alongside `build-binaries`)

**Existing trigger + permissions** (`release.yml` lines 1–11):
```yaml
# From .github/workflows/release.yml lines 1-11
name: Release
on:
  push:
    tags:
      - 'v*'
permissions:
  contents: write
  packages: write
```

**Existing job structure to mirror** (`release.yml` lines 13–61 `build-binaries` job):
```yaml
# Pattern: matrix job with os-specific artifact names + upload-artifact@v4
# New build-agent job follows same structure but uses setup-go@v6 instead of setup-python@v5
build-agent:
  name: Build agent ${{ matrix.goos }}-${{ matrix.goarch }}
  runs-on: ubuntu-latest          # single runner — CGO_ENABLED=0 cross-compile
  strategy:
    matrix:
      include:
        - goos: linux
          goarch: amd64
          artifact: infracanvas-agent-linux-amd64
        - goos: darwin
          goarch: arm64
          artifact: infracanvas-agent-macos-arm64
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-go@v6   # v6 is current (RESEARCH State of the Art)
      with:
        go-version: '1.25'
        cache-dependency-path: agent/go.sum
    - name: Build agent
      env:
        GOOS: ${{ matrix.goos }}
        GOARCH: ${{ matrix.goarch }}
        CGO_ENABLED: 0            # CRITICAL: pure-Go cross-compile (RESEARCH Pitfall 4)
      run: |
        cd agent
        go build -ldflags="-s -w -X main.version=${{ github.ref_name }}" \
          -o ../dist/${{ matrix.artifact }} \
          ./cmd/infracanvas-agent
    - uses: actions/upload-artifact@v4
      with:
        name: ${{ matrix.artifact }}
        path: dist/${{ matrix.artifact }}
```

**`create-release` job needs extension** (`release.yml` lines 133–150):
```yaml
# From .github/workflows/release.yml lines 133-150
# Add build-agent to needs[] and add agent artifact paths to files:
create-release:
  needs: [build-binaries, build-docker, publish-pypi, build-agent]  # add build-agent
  steps:
    - uses: softprops/action-gh-release@v2
      with:
        files: |
          artifacts/infracanvas-linux-amd64/infracanvas-linux-amd64
          artifacts/infracanvas-macos-arm64/infracanvas-macos-arm64
          artifacts/infracanvas-windows-x64/infracanvas-windows-x64.exe
          artifacts/infracanvas-agent-linux-amd64/infracanvas-agent-linux-amd64
          artifacts/infracanvas-agent-macos-arm64/infracanvas-agent-macos-arm64
```

**`ci.yml` agent test job** (mirror `test-cli` job at `.github/workflows/ci.yml` lines 9–28):
```yaml
# From .github/workflows/ci.yml lines 9-28 — test-cli pattern to mirror
test-agent:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-go@v6
      with:
        go-version: '1.25'
        cache-dependency-path: agent/go.sum
    - name: Run tests
      run: |
        cd agent
        go test ./... -race -count=1 -timeout 120s
```

---

### `agent/cmd/infracanvas-agent/main.go` (controller, event-driven)

**Analog:** No Go code in repo. Use RESEARCH Pattern 1 (cobra + tickers + graceful shutdown). Nearest structural analog is the Python CLI entrypoint `cli/infracanvas/main.py` (Typer app with subcommands).

**Python CLI entrypoint pattern for reference** (`cli/infracanvas/main.py`):
```python
# Structural analog: cli/infracanvas/main.py — Typer app with subcommands
# maps to: cobra root command + subcommands in Go
app = typer.Typer(name="infracanvas", no_args_is_help=True)
# → cobra.Command{Use: "infracanvas-agent", SilenceErrors: true}

@app.command()
def scan(planfile: Path = typer.Argument(...)):  # subcommand
# → runCmd = &cobra.Command{Use: "run", RunE: runDaemon}
```

**Go daemon pattern** (RESEARCH Pattern 1 — no codebase analog):
```go
// RESEARCH.md Pattern 1 (lines 181-218) — use verbatim
func runDaemon(cmd *cobra.Command, args []string) error {
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()

    routeTicker := time.NewTicker(5 * time.Minute)
    bgpTicker   := time.NewTicker(1 * time.Minute)
    flowFlusher := time.NewTicker(30 * time.Second)
    defer routeTicker.Stop()
    defer bgpTicker.Stop()
    defer flowFlusher.Stop()

    for {
        select {
        case <-ctx.Done():
            wg.Wait()
            return nil
        case <-routeTicker.C:
            go collectAndPushRoutes(ctx)
        case <-bgpTicker.C:
            go collectAndPushBGP(ctx)
        case <-flowFlusher.C:
            go flushFlowBuffer(ctx)
        }
    }
}
```

---

### `agent/internal/config/config.go` (utility, request-response)

**Analog:** `cli/infracanvas/config.py` (YAML config file with walk-up discovery — same concept, different language)

**Python config walk-up pattern for reference** (`cli/infracanvas/config.py`):
```python
# Structural concept: walk up filesystem for config file, fall back to defaults
# Go equivalent: check ./agent.yaml, then /etc/infracanvas/agent.yaml
```

**Go config struct** (RESEARCH Code Examples lines 539–556 — no codebase analog):
```go
// RESEARCH.md Code Examples — Go Config Struct
type Config struct {
    SiteToken  string   `yaml:"site_token"`
    BackendURL string   `yaml:"backend_url"`
    Devices    []Device `yaml:"devices"`
}

type Device struct {
    Host       string `yaml:"host"`
    Port       int    `yaml:"port"`
    Protocol   string `yaml:"protocol"`    // "netconf" | "ssh" | "config-import"
    Username   string `yaml:"username"`
    Password   string `yaml:"password"`
    ConfigFile string `yaml:"config_file"` // protocol=config-import only
    SiteID     string `yaml:"site_id"`     // optional override
}

func Load(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("config: read %s: %w", path, err)
    }
    var cfg Config
    if err := yaml.Unmarshal(data, &cfg); err != nil {
        return nil, fmt.Errorf("config: parse: %w", err)
    }
    return &cfg, nil
}
```

---

### `agent/internal/netconf/collector.go` (service, request-response)

**Analog:** None in codebase. Use RESEARCH Pattern 2 exclusively.

**NETCONF session + RPC pattern** (RESEARCH Pattern 2 lines 222–258):
```go
// RESEARCH.md Pattern 2 — nemith.io/netconf SSH transport
import (
    "nemith.io/netconf"
    ncssh "nemith.io/netconf/transport/ssh"
    "golang.org/x/crypto/ssh"
)

func dialDevice(ctx context.Context, host, user, pass string) (*netconf.Session, error) {
    cfg := &ssh.ClientConfig{
        User:            user,
        Auth:            []ssh.AuthMethod{ssh.Password(pass)},
        HostKeyCallback: ssh.InsecureIgnoreHostKey(), // NOTE: document in CAB as known risk
        Timeout:         10 * time.Second,
    }
    transport, err := ncssh.Dial(ctx, "tcp", host+":830", cfg)
    if err != nil {
        return nil, fmt.Errorf("netconf dial %s: %w", host, err)
    }
    return netconf.NewSession(transport)
}
// Use subtree filter as primary (avoids XPath namespace pitfalls — RESEARCH Pitfall 1)
// rpc.Filter{Type: "subtree", ...} rather than Type: "xpath"
```

---

### `agent/internal/ssh/collector.go` (service, request-response)

**Analog:** None in codebase. Use RESEARCH Pattern 3 exclusively.

**SSH CLI fallback pattern** (RESEARCH Pattern 3 lines 263–292):
```go
// RESEARCH.md Pattern 3 — golang.org/x/crypto/ssh + PTY
// CRITICAL: IOS-XE requires PTY + "terminal length 0" (RESEARCH Pitfall 2)
func execSSHCommand(ctx context.Context, host, user, pass, command string) (string, error) {
    cfg := &ssh.ClientConfig{
        User:            user,
        Auth:            []ssh.AuthMethod{ssh.Password(pass)},
        HostKeyCallback: ssh.InsecureIgnoreHostKey(),
    }
    client, err := ssh.Dial("tcp", host+":22", cfg)
    // ... PTY allocation required — sess.RequestPty("xterm", 200, 200, modes)
    // Use interactive shell (not sess.Output) to send "terminal length 0\n" first
}
```

---

### `agent/internal/netflow/listener.go` (service, event-driven)

**Analog:** None in codebase. Use RESEARCH Pattern 4 exclusively.

**NetFlow UDP listener pattern** (RESEARCH Pattern 4 lines 295–328):
```go
// RESEARCH.md Pattern 4 — goflow2/v2 decoder library (NOT standalone binary)
import (
    "github.com/netsampler/goflow2/v2/decoders/netflow"
    "github.com/netsampler/goflow2/v2/utils/templates"
)
// Per-sampler template cache must persist between UDP packets (RESEARCH Pitfall 3)
// Use templates.DefaultTemplateGenerator keyed by sampler addr string
```

---

### `agent/internal/netflow/buffer.go` (utility, batch)

**Analog:** None in codebase. Use RESEARCH Pattern 5 exclusively.

**Mutex ring buffer pattern** (RESEARCH Pattern 5 lines 333–367):
```go
// RESEARCH.md Pattern 5 — mutex + circular slice (no external dep needed)
type RingBuffer struct {
    mu   sync.Mutex
    data []FlowRecord
    head int
    size int
}
// Drain() resets head=0 after extracting records
// Append() uses head%size for circular overwrite
```

---

### `agent/internal/push/client.go` (service, request-response)

**Analog:** `backend/app/storage/r2.py` (HTTP client with error handling) — partial match. Use RESEARCH retry pattern.

**Retry-twice push pattern** (RESEARCH Code Examples lines 602–619):
```go
// RESEARCH.md retry pattern — retry 3 attempts (attempt 0,1,2), backoff 2s/4s
func pushWithRetry(ctx context.Context, url, token string, payload []byte, log *zap.Logger) error {
    var lastErr error
    for attempt := 0; attempt < 3; attempt++ {
        if attempt > 0 {
            time.Sleep(time.Duration(attempt*2) * time.Second)
        }
        if err := doPost(ctx, url, token, payload); err == nil {
            return nil
        } else {
            lastErr = err
        }
    }
    log.Warn("push failed after retries, dropping batch", zap.Error(lastErr))
    return nil  // drop-on-retry-exhaustion (D-07)
}

func doPost(ctx context.Context, url, token string, payload []byte) error {
    req, _ := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(payload))
    req.Header.Set("Authorization", "Bearer "+token)
    req.Header.Set("Content-Type", "application/json")
    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    if resp.StatusCode >= 500 {
        return fmt.Errorf("server error %d", resp.StatusCode)
    }
    return nil
}
```

---

### `agent/go.mod` (config)

**Analog:** None in repo. Standard Go module file.

```
module github.com/infracanvas/infracanvas/agent

go 1.25

require (
    nemith.io/netconf v0.0.4
    golang.org/x/crypto v0.50.0
    github.com/netsampler/goflow2/v2 v2.2.6
    github.com/spf13/cobra v1.10.2
    gopkg.in/yaml.v3 v3.0.1
    go.uber.org/zap v1.28.0
    github.com/stretchr/testify v1.11.1
)
```

Note: `agent/` is a self-contained module — no `go.work` file (RESEARCH Pitfall 5: go.work is local-only; CI builds via `cd agent && go build`).

---

## Shared Patterns

### Bearer Token Extraction
**Source:** `backend/app/auth/clerk.py` lines 61–66 (`_bearer` helper)
**Apply to:** `backend/app/auth/site_token.py` (new parallel auth module)
```python
# Exact pattern to copy into require_site_token:
h = request.headers.get("authorization", "")
if not h.lower().startswith("bearer "):
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_bearer")
raw_token = h.split(" ", 1)[1].strip()
```

### SHA-256 Token Lookup Hash
**Source:** `backend/migrations/versions/20260428_006_share_links.py` lines 8–14 (design notes) and `token_lookup_hash` column (lines 53–54)
**Apply to:** `backend/migrations/versions/20260507_010_dc_sites.py` + `backend/app/auth/site_token.py`
```python
# From share_links migration design notes (lines 8-14):
# token_lookup_hash (SHA-256 of raw token) enables O(1) indexed lookup
# bcrypt verification happens in Python after fetching the row by token_lookup_hash
import hashlib
lookup_hash = hashlib.sha256(raw_token.encode()).hexdigest()
# Store as sa.String(64) — exact column type from share_links
```

### RLS team_isolation Policy
**Source:** `backend/migrations/versions/20260428_006_share_links.py` lines 85–96
**Apply to:** `backend/migrations/versions/20260507_010_dc_sites.py`
```python
op.execute("ALTER TABLE dc_sites ENABLE ROW LEVEL SECURITY;")
op.execute("ALTER TABLE dc_sites FORCE ROW LEVEL SECURITY;")
op.execute("""
    CREATE POLICY dc_sites_team_isolation ON dc_sites
      USING (team_id = current_setting('app.current_team_id', true)::uuid)
      WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
""")
```

### Structlog Logging
**Source:** All existing route files (`github.py` line 51, `integrations.py` line 21, `webhooks.py` line 51)
**Apply to:** `backend/app/routes/agent.py`
```python
import structlog
_log = structlog.get_logger("app.agent")
# Usage: _log.info("agent_routes_received", site_id=principal.site_id, count=len(body.routes))
# Usage: _log.warning("agent_push_rejected", reason="invalid_token")
```

### Error String Code Convention
**Source:** `backend/app/routes/webhooks.py` lines 68–98, `backend/app/auth/clerk.py` lines 65–66
**Apply to:** `backend/app/routes/agent.py`, `backend/app/auth/site_token.py`
```python
# Error detail is a snake_case string code, not a sentence:
raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_bearer")
raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_site_token")
raise HTTPException(status.HTTP_404_NOT_FOUND, "site_not_found")
# NOT: raise HTTPException(400, "The token is invalid")
```

### FastAPI TestClient Test Pattern
**Source:** `backend/tests/test_health.py` lines 1–49
**Apply to:** `backend/tests/test_agent.py` (new)
```python
from __future__ import annotations
from fastapi.testclient import TestClient
from app.main import create_app

def test_push_routes_rejects_missing_bearer() -> None:
    """DCA-05: POST /v1/agent/routes returns 401 missing_bearer with no auth header."""
    with TestClient(create_app()) as client:
        r = client.post("/v1/agent/routes", json={...})
        assert r.status_code == 401
        assert r.json()["detail"] == "missing_bearer"
```

### conftest.py env stubs
**Source:** `backend/tests/conftest.py` lines 33–54
**Apply to:** `backend/tests/test_agent.py` — add any new env vars for agent tests as `os.environ.setdefault(...)` in conftest, not in individual tests.

### GHA Actions Version Convention
**Source:** `.github/workflows/release.yml` and `ci.yml`
**Apply to:** New jobs in both files
```yaml
# Pinned action versions in use — match these:
actions/checkout@v4
actions/setup-python@v5
actions/setup-node@v4
actions/upload-artifact@v4
actions/download-artifact@v4
softprops/action-gh-release@v2
# New for agent:
actions/setup-go@v6   # v6 is current (RESEARCH State of the Art)
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `agent/go.mod` | config | — | No Go code exists in repo; greenfield |
| `agent/internal/netconf/collector.go` | service | request-response | No NETCONF/XML RPC client in repo |
| `agent/internal/ssh/collector.go` | service | request-response | No SSH client (only SSH server auth patterns in crypto deps) |
| `agent/internal/netflow/listener.go` | service | event-driven | No UDP listener or streaming collector in repo |
| `agent/internal/netflow/buffer.go` | utility | batch | No ring buffer or in-memory queue in repo |
| `agent/docs/cab/` | documentation | — | No CAB security packet precedent in repo; use RESEARCH DCA-09 + STRIDE template |

For these files, the planner must use RESEARCH.md Patterns 1–5 and Code Examples as the primary reference.

---

## Metadata

**Analog search scope:** `backend/app/routes/`, `backend/app/auth/`, `backend/migrations/versions/`, `.github/workflows/`, `cli/infracanvas/`
**Files scanned:** 12 source files read in full or targeted sections
**Pattern extraction date:** 2026-05-07

**Key architectural constraint confirmed:** `require_site_token` MUST be a per-route `Depends(...)` — NOT global middleware. `require_principal` (Clerk) is also per-route in this codebase (`main.py` lines 37–51 confirms no global auth middleware). Agent routes use `require_site_token` exclusively; they must NOT also receive `require_principal`.

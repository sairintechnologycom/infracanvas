# Phase 10: DC Agent Core - Research

**Researched:** 2026-05-07
**Domain:** Go agent (NETCONF/SSH/NetFlow collector), FastAPI site-token auth, GHA cross-compile, enterprise CAB packet
**Confidence:** HIGH (core stack), MEDIUM (NETCONF XPath specifics), LOW (CAB packet format)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Go agent in `agent/` subfolder. Module path: `github.com/infracanvas/infracanvas/agent`. Standard Go layout: `agent/cmd/infracanvas-agent/main.go` (cobra entry) + `agent/internal/` (netconf, ssh, netflow, push, config packages).
- **D-02:** Shared semver tag — one `v0.X.Y` git tag triggers GHA to build both Python CLI wheel and Go agent binaries in the same release job. No separate `agent/vX.Y.Z` tags.
- **D-03:** Dashboard-generated site token model. `POST /v1/sites` endpoint creates dc_sites row and returns one-time plaintext token. Agent reads token from `agent.yaml`. No dashboard UI in Phase 10.
- **D-04:** Agent sends `Authorization: Bearer <site_token>` header. Backend validates via hashed-token DB lookup resolving `team_id` + `site_id`. Same header convention as Clerk JWT; parallel validation path.
- **D-05:** Credentials in `agent.yaml` (chmod 600). Not transmitted. Read-only NETCONF service accounts expected.
- **D-06:** `devices[]` array in `agent.yaml`. Per-device: `host`, `port`, `protocol` (netconf|ssh|config-import), `username`, `password`, optional `site_id` override.
- **D-07:** In-memory ring buffer, ~5 min capacity, 30-second flush, retry-twice-then-drop-with-WARN-log.
- **D-08:** JSON-over-HTTPS push to `POST /v1/agent/routes` and `POST /v1/agent/flows`.

### Claude's Discretion
- Go standard library choices (logging, HTTP client, yaml parser) where not specified
- Ring buffer implementation strategy (mutex-based vs channel-based)
- NETCONF XPath filter strings for routing tables and BGP neighbor state
- SSH output parsing approach (regex vs line-scan)
- CAB packet document format (Markdown + Mermaid vs PDF)
- Test mocking strategy for NETCONF/SSH (interface injection vs test server)
- Backend: exact column layout for `dc_sites` table beyond `site_token_hash` + `team_id`

### Deferred Ideas (OUT OF SCOPE)
- Dashboard UI for site token management — Phase 11+
- mTLS per-site certificates — enterprise v1.2+
- Disk-backed NetFlow queue — Phase 10 in-memory only
- Protobuf push encoding — deferred until demand validated
- CPC-02 (flow-log-driven data transfer attribution) — Phase 12
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DCA-01 | Go DC Agent scaffold — cobra CLI, daemon mode, single binary Linux amd64 + macOS arm64 | Cobra v1.10.2 docs verified; standard Go layout; cross-compile via `GOOS`/`GOARCH` |
| DCA-02 | Cisco NETCONF/RESTCONF client for IOS-XE | `nemith.io/netconf` v0.0.4 (maintained); IOS-XE supports RFC 6241/6242 NETCONF on port 830; YANG XPath patterns for routing |
| DCA-03 | SSH CLI fallback for NETCONF-unsupported devices | `golang.org/x/crypto` v0.50.0 SSH client; PTY allocation for IOS-XE interactive commands; output parsing patterns |
| DCA-04 | NetFlow v9/IPFIX UDP collector via netsampler/goflow2/v2 | `github.com/netsampler/goflow2/v2` v2.2.6 verified; UDP on port 2055; template system API confirmed |
| DCA-05 | Encrypted API push to cloud backend | TLS via standard `net/http` HTTPS; `Authorization: Bearer` header; JSON body; retry-twice pattern |
| DCA-06 | Daemon timing — routes 5 min, BGP 1 min, NetFlow 30 s | `time.NewTicker` + goroutine per collector; graceful shutdown via `os.Signal` + `context.WithCancel` |
| DCA-07 | Config file import fallback mode (no network access) | `agent.yaml` `protocol: config-import` + static YAML/JSON file reference; same push path |
| DCA-08 | Cross-compiled binaries + GHA release workflow | `actions/setup-go@v6`; `GOOS`/`GOARCH` matrix; attach to existing `release.yml` `create-release` job |
| DCA-09 | Enterprise CAB security-review packet (architecture, data flow, threat model) | STRIDE template; SBOM via `cyclonedx-gomod`; Mermaid diagrams in Markdown |
</phase_requirements>

---

## Summary

Phase 10 introduces a standalone Go binary (`infracanvas-agent`) into a monorepo that currently contains only Python and TypeScript. The primary research questions are: (1) which Go NETCONF library to use for Cisco IOS-XE, (2) how to embed goflow2/v2's decoder as a library rather than running the goflow2 binary standalone, (3) how to add site-token auth to the FastAPI backend in parallel with existing Clerk JWT auth without touching existing routes, and (4) how to add a Go cross-compile step to the existing release workflow.

The standard approach for a Go binary added to a mixed-language monorepo is a self-contained `go.mod` at `agent/` — no Go workspaces needed because there is no shared Go code between the agent and other monorepo components. The Go 1.25.2 toolchain is already installed locally. `nemith.io/netconf` (v0.0.4, Jan 2026) is the maintained successor to the deprecated `Juniper/go-netconf` and implements RFC 6241/6242 with a clean SSH transport API. `netsampler/goflow2/v2` (v2.2.6, Dec 2025) provides a decoder library — the agent uses its `decoders/netflow` and `decoders/sflow` packages directly with a UDP listener, rather than running the standalone binary. The in-memory ring buffer is most naturally implemented with a `sync.Mutex`-protected circular slice (a third-party library is unnecessary overhead for this fixed-capacity pattern). On the backend, the site-token validation is a new FastAPI dependency function — a parallel path to `require_principal` — consuming the same `Authorization: Bearer` header but doing a SHA-256 lookup against a new `dc_sites` table (migration 010, following the existing numbering of 009).

**Primary recommendation:** Use `nemith.io/netconf` for NETCONF (not `Juniper/go-netconf` which is archived), use goflow2/v2 decoder packages (not the standalone binary), implement ring buffer with mutex + circular slice, add a dedicated `agent-ci` GHA job to `ci.yml` and a `build-agent` matrix job to `release.yml`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| NETCONF/SSH device collection | Go Agent (agent/) | — | Network device protocol speaks only to local agent; credentials never leave agent host |
| NetFlow UDP reception | Go Agent (agent/) | — | UDP packets arrive at agent's network interface |
| Data push (routes + flows) | Go Agent → API Backend | — | Agent is push-only client; backend is the authoritative store |
| Site-token generation | API Backend (POST /v1/sites) | — | Token generation requires DB + random secret; agent only reads tokens |
| Site-token validation | API Backend (auth middleware) | — | Validates on every push request; agent has no access to DB |
| Route/flow storage | API Backend (Neon DB + R2) | — | SaaS persistence layer; agents are stateless by design |
| Config-import fallback | Go Agent (agent/) | — | File read is local to agent; same push path after parsing |
| CAB security packet | Documentation artifact | — | Consumed by enterprise procurement reviewers, not by runtime |

---

## Standard Stack

### Core (Go Agent)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `nemith.io/netconf` | v0.0.4 | NETCONF RFC 6241/6242 client | Maintained successor to archived Juniper/go-netconf; SSH transport built-in; clean RPC API |
| `golang.org/x/crypto` | v0.50.0 | SSH CLI transport + crypto primitives | Official Go extended crypto; only option for Go SSH client |
| `github.com/netsampler/goflow2/v2` | v2.2.6 | NetFlow v9/IPFIX decoder | Locked decision in STATE.md; production-grade decoder with template management |
| `github.com/spf13/cobra` | v1.10.2 | CLI framework | Standard Go CLI; daemon subcommand + persistent flags |
| `gopkg.in/yaml.v3` | v3.0.1 | `agent.yaml` config parsing | De-facto standard Go YAML; compatible with YAML 1.1/1.2 |
| `go.uber.org/zap` | v1.28.0 | Structured logging | Industry standard for production Go; JSON output; level gates |
| `github.com/stretchr/testify` | v1.11.1 | Test assertions + mocking | Standard Go test library; `require` + `assert` + `mock` packages |

### Supporting (Go Agent)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Standard `net/http` | stdlib | HTTPS push to backend | No third-party needed for simple JSON POST with retry |
| Standard `sync` | stdlib | Ring buffer mutex | `sync.Mutex` + `sync.WaitGroup` for buffer and goroutine lifecycle |
| Standard `os/signal` | stdlib | Graceful shutdown | `signal.NotifyContext` for SIGINT/SIGTERM |
| Standard `time` | stdlib | Collection tickers | `time.NewTicker` for 5 min / 1 min / 30 s intervals |

### Supporting (Backend — Python)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `secrets` (stdlib) | — | One-time site-token generation | `secrets.token_urlsafe(32)` for 32-byte entropy token |
| `hashlib` (stdlib) | — | SHA-256 token hash for DB lookup | Same pattern as `share_links.token_lookup_hash` (migration 006) |
| `bcrypt` | >=4.0,<5 | Token hash for stored verification | Already in backend deps; same pattern as share link bcrypt |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `nemith.io/netconf` | `netascode/go-netconf` | netascode is simpler/more fluent but smaller community; nemith.io is more RFC-complete |
| `nemith.io/netconf` | `Juniper/go-netconf` | Juniper/go-netconf is archived — do not use |
| Mutex ring buffer | `smallnest/ringbuffer` | External dep not worth it for a fixed-capacity ~5 min buffer; stdlib is sufficient |
| `go.uber.org/zap` | `log/slog` (stdlib Go 1.21+) | `slog` is viable but `zap` has better production field binding ergonomics; either works |
| `cyclonedx-gomod` | `syft` | syft is more flexible but requires Docker/external binary in CI; cyclonedx-gomod is a single Go binary |

**Installation (agent):**
```bash
cd agent
go mod init github.com/infracanvas/infracanvas/agent
go get nemith.io/netconf@v0.0.4
go get golang.org/x/crypto@v0.50.0
go get github.com/netsampler/goflow2/v2@v2.2.6
go get github.com/spf13/cobra@v1.10.2
go get gopkg.in/yaml.v3@v3.0.1
go get go.uber.org/zap@v1.28.0
go get github.com/stretchr/testify@v1.11.1
```

**Version verification:** All versions above confirmed against `proxy.golang.org` on 2026-05-07.

---

## Architecture Patterns

### System Architecture Diagram

```
[Cisco IOS-XE device] ──NETCONF:830──► [internal/netconf] ──► [RouteRecord]──►┐
[Legacy device]       ──SSH:22────────► [internal/ssh]     ──► [RouteRecord]──►│
[Static YAML file]    ──file read──────► [internal/config]  ──► [RouteRecord]──►├──► [internal/push] ──HTTPS/TLS──► [POST /v1/agent/routes]
                                                                                 │                  Bearer token    [POST /v1/agent/flows]
[Network switch]      ──UDP:2055──────► [internal/netflow]  ──► [FlowRecord] ──►│                                         │
                                              │                                  │                                   [FastAPI backend]
                                          ring buffer                           └──────────────────────────────────► [dc_sites auth dep]
                                         (5 min cap)                                                                        │
                                              │ 30s flush                                                            [Neon DB + R2]
                                              ▼
                                       retry x2 → drop+WARN

[os.Signal SIGINT/SIGTERM] ──────────► [context.WithCancel] ──► all goroutines drain + exit
```

### Recommended Project Structure
```
agent/
├── cmd/
│   └── infracanvas-agent/
│       └── main.go           # cobra root + subcommands (run, version)
├── internal/
│   ├── config/
│   │   └── config.go         # agent.yaml loader (gopkg.in/yaml.v3)
│   ├── netconf/
│   │   └── collector.go      # nemith.io/netconf SSH session + RPC
│   ├── ssh/
│   │   └── collector.go      # golang.org/x/crypto/ssh exec + output parser
│   ├── netflow/
│   │   ├── listener.go       # UDP:2055 + goflow2/v2 decode
│   │   └── buffer.go         # mutex ring buffer
│   └── push/
│       └── client.go         # net/http JSON POST + retry-twice
├── go.mod                    # module github.com/infracanvas/infracanvas/agent
├── go.sum
└── agent.yaml.example        # documented example config (chmod 600 instruction)
```

### Pattern 1: Daemon Run with Cobra + Tickers + Graceful Shutdown

```go
// Source: Cobra user guide https://github.com/spf13/cobra/blob/main/site/content/user_guide.md
// + Go stdlib os/signal docs
var runCmd = &cobra.Command{
    Use:   "run",
    Short: "Start the agent daemon",
    RunE:  runDaemon,
}

func runDaemon(cmd *cobra.Command, args []string) error {
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()

    routeTicker  := time.NewTicker(5 * time.Minute)
    bgpTicker    := time.NewTicker(1 * time.Minute)
    flowFlusher  := time.NewTicker(30 * time.Second)
    defer routeTicker.Stop()
    defer bgpTicker.Stop()
    defer flowFlusher.Stop()

    var wg sync.WaitGroup
    // start NetFlow UDP listener goroutine...

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

### Pattern 2: NETCONF Session + Get-Config RPC (IOS-XE)

```go
// Source: nemith.io/netconf README https://github.com/nemith/netconf
// IOS-XE NETCONF port: 830; enable with: netconf-yang on IOS-XE
import (
    "nemith.io/netconf"
    ncssh "nemith.io/netconf/transport/ssh"
    "nemith.io/netconf/rpc"
    "golang.org/x/crypto/ssh"
)

func dialDevice(ctx context.Context, host, user, pass string) (*netconf.Session, error) {
    cfg := &ssh.ClientConfig{
        User:            user,
        Auth:            []ssh.AuthMethod{ssh.Password(pass)},
        HostKeyCallback: ssh.InsecureIgnoreHostKey(), // [ASSUMED] replace with known_hosts in prod
        Timeout:         10 * time.Second,
    }
    transport, err := ncssh.Dial(ctx, "tcp", host+":830", cfg)
    if err != nil {
        return nil, fmt.Errorf("netconf dial %s: %w", host, err)
    }
    return netconf.NewSession(transport)
}

// XPath filter for IOS-XE routing table (ietf-routing YANG)
// [ASSUMED] exact namespace prefix may vary across IOS-XE versions
const routingXPath = `/rt:routing-state/routing-instance[name="default"]/ribs/rib[name="ipv4-default"]/routes/route`

func getRoutes(ctx context.Context, sess *netconf.Session) ([]byte, error) {
    reply, err := rpc.Get{
        Filter: rpc.Filter{Type: "xpath", Select: routingXPath},
    }.Exec(ctx, sess)
    if err != nil {
        return nil, err
    }
    return reply, nil
}
```

### Pattern 3: SSH CLI Fallback (IOS-XE)

```go
// Source: golang.org/x/crypto/ssh pkg docs https://pkg.go.dev/golang.org/x/crypto/ssh
// IOS-XE requires PTY allocation for multi-command sessions
func execSSHCommand(ctx context.Context, host, user, pass, command string) (string, error) {
    cfg := &ssh.ClientConfig{
        User: user,
        Auth: []ssh.AuthMethod{ssh.Password(pass)},
        HostKeyCallback: ssh.InsecureIgnoreHostKey(),
    }
    client, err := ssh.Dial("tcp", host+":22", cfg)
    if err != nil {
        return "", err
    }
    defer client.Close()

    sess, err := client.NewSession()
    if err != nil {
        return "", err
    }
    defer sess.Close()

    // IOS-XE requires PTY for terminal pagination; use "terminal length 0" pattern
    modes := ssh.TerminalModes{ssh.ECHO: 0, ssh.TTY_OP_ISPEED: 9600}
    if err := sess.RequestPty("xterm", 200, 200, modes); err != nil {
        return "", err
    }
    out, err := sess.Output(command)
    return string(out), err
}
```

### Pattern 4: NetFlow v9/IPFIX UDP Listener with goflow2/v2

```go
// Source: Context7 goflow2/v2 docs https://context7.com/netsampler/goflow2/llms.txt
import (
    "github.com/netsampler/goflow2/v2/decoders/netflow"
    "github.com/netsampler/goflow2/v2/utils/templates"
)

func runNetFlowListener(ctx context.Context, buf *RingBuffer) error {
    conn, err := net.ListenUDP("udp", &net.UDPAddr{Port: 2055})
    if err != nil {
        return err
    }
    go func() {
        <-ctx.Done()
        conn.Close()
    }()

    raw := make([]byte, 9000) // max UDP NetFlow packet
    templateCache := make(map[string]templates.Template) // keyed by sampler IP:port
    for {
        n, addr, err := conn.ReadFromUDP(raw)
        if err != nil {
            if ctx.Err() != nil { return } // shutdown
            continue
        }
        samplerKey := addr.String()
        tmpl := getOrCreateTemplate(templateCache, samplerKey)
        pkt, err := netflow.DecodeMessageNetFlow(bytes.NewBuffer(raw[:n]), tmpl, nil)
        if err != nil { continue }
        buf.Append(extractFlowRecords(pkt))
    }
}
```

### Pattern 5: Mutex Ring Buffer

```go
// Source: [ASSUMED] standard mutex+slice pattern; confirmed viable by smallnest/ringbuffer analysis
type RingBuffer struct {
    mu   sync.Mutex
    data []FlowRecord
    head int
    size int
}

func NewRingBuffer(capacity int) *RingBuffer {
    return &RingBuffer{data: make([]FlowRecord, capacity), size: capacity}
}

func (r *RingBuffer) Append(records []FlowRecord) {
    r.mu.Lock()
    defer r.mu.Unlock()
    for _, rec := range records {
        r.data[r.head%r.size] = rec
        r.head++
    }
}

func (r *RingBuffer) Drain() []FlowRecord {
    r.mu.Lock()
    defer r.mu.Unlock()
    start := 0
    if r.head > r.size { start = r.head % r.size }
    n := min(r.head, r.size)
    out := make([]FlowRecord, n)
    for i := 0; i < n; i++ {
        out[i] = r.data[(start+i)%r.size]
    }
    r.head = 0 // reset after drain
    return out
}
```

### Pattern 6: Backend Site-Token Auth Dependency (FastAPI)

```python
# Source: [ASSUMED] parallel to require_principal in backend/app/auth/clerk.py
# Same Authorization: Bearer header; different token type resolution
import hashlib, secrets
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

async def require_site_token(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> DCSitePrincipal:
    """Validate site token from Authorization: Bearer header.
    
    Mirrors require_principal shape but resolves team_id + site_id from dc_sites
    table using SHA-256 lookup hash (same pattern as share_links.token_lookup_hash).
    """
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_bearer")
    raw_token = h.split(" ", 1)[1].strip()
    lookup_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    row = await session.execute(
        select(DCSite).where(DCSite.token_lookup_hash == lookup_hash)
    )
    site = row.scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_site_token")
    return DCSitePrincipal(team_id=site.team_id, site_id=site.id)
```

### Pattern 7: GHA Go Cross-Compile Matrix

```yaml
# Source: [VERIFIED: GHA docs + existing release.yml pattern in repo]
build-agent:
  name: Build agent ${{ matrix.goos }}-${{ matrix.goarch }}
  runs-on: ubuntu-latest
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
    - uses: actions/setup-go@v6
      with:
        go-version: '1.25'
        cache-dependency-path: agent/go.sum
    - name: Build agent
      env:
        GOOS: ${{ matrix.goos }}
        GOARCH: ${{ matrix.goarch }}
        CGO_ENABLED: 0          # critical: CGO disabled for pure-Go cross-compile
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

### Anti-Patterns to Avoid
- **Using `Juniper/go-netconf`:** This repo is archived as of 2024; `nemith.io/netconf` is the maintained successor. The nemith README explicitly notes the transition.
- **Running goflow2 as a standalone subprocess:** goflow2/v2 is designed to be used as a library via its `decoders/netflow` package. Subprocess wrapping adds process management overhead and JSON parsing latency.
- **CGO enabled for cross-compile:** `CGO_ENABLED=1` requires a C cross-compiler for `linux/amd64` when building on `darwin/arm64`. The agent has no C dependencies; always set `CGO_ENABLED=0`.
- **Storing raw site token in DB:** Store only SHA-256 lookup hash for O(1) indexed lookup, same as `share_links.token_lookup_hash` pattern established in migration 006. The raw token is only returned once at creation time.
- **Missing PTY allocation for SSH CLI on IOS-XE:** IOS-XE's SSH server enables terminal pagination by default. Without a PTY + `terminal length 0` pre-command, `show ip route` output is truncated at 24 lines.
- **Forgetting `terminal length 0` IOS-XE pre-command:** Even with PTY, IOS-XE paginates output unless `terminal length 0` is sent first in the session.
- **Ignoring NetFlow template records:** NetFlow v9 requires receiving a template flowset before data flowsets can be decoded. `goflow2/v2`'s `templates.DefaultTemplateGenerator` handles this per-sampler-address; per-process template state must be retained between UDP packets.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NETCONF SSH framing + base 1.0 chunked encoding | Custom SSH+XML state machine | `nemith.io/netconf` | RFC 6242 framing has multiple edge cases (hello capability exchange, error handling, chunked vs end-of-message mode) |
| NetFlow v9 template management | Custom template store | `goflow2/v2/utils/templates` + `decoders/netflow` | Template records can arrive out-of-order, per-exporter, with retransmission; goflow2 handles all of this |
| NetFlow v9/IPFIX packet decode | Custom binary parser | `goflow2/v2/decoders/netflow` | Dozens of field types, variable-length encoding, IPFIX enterprise IEs |
| SSH client protocol | Raw TCP + custom SSH handshake | `golang.org/x/crypto/ssh` | SSH wire protocol is complex; crypto primitives are security-critical |
| SBOM generation | Manually listing deps | `cyclonedx-gomod` CLI | `go.sum` is the ground truth; cyclonedx-gomod reads it natively |

**Key insight:** The NETCONF domain has significant protocol complexity at the framing layer (base 1.0 vs 1.1 chunked encoding, hello capability negotiation, RPC error XML parsing). The template-dependency problem in NetFlow v9 is a well-known source of data-loss bugs if hand-rolled. Both are solved by existing, tested libraries.

---

## Runtime State Inventory

> This is a greenfield Go agent directory — `agent/` does not yet exist. No rename/refactor involved.

**Step 2.5: SKIPPED** — Phase 10 creates new files and a new DB table. No existing runtime state needs migration. The `dc_sites` table is new (migration 010); no existing records to migrate.

---

## Common Pitfalls

### Pitfall 1: IOS-XE NETCONF — Wrong YANG Namespace Prefix
**What goes wrong:** `<get>` with XPath filter returns empty data set; no error is raised.
**Why it happens:** IOS-XE NETCONF requires the correct YANG module namespace prefix in XPath selectors. The prefix `rt:` maps to `urn:ietf:params:xml:ns:yang:ietf-routing` but the prefix registration must appear in the RPC request. Some IOS-XE versions support native YANG (`Cisco-IOS-XE-native`) rather than standard `ietf-routing`.
**How to avoid:** Test against a real IOS-XE device or CSR1000v VM before finalising XPath strings. Fallback: use subtree filters (simpler XML, no namespace prefix issue) rather than XPath for initial implementation. The `rpc.Get{Filter: rpc.Filter{Type: "subtree", ...}}` API supports both. [ASSUMED] final XPath strings need device validation.
**Warning signs:** Empty XML reply body with no `<rpc-error>` element.

### Pitfall 2: SSH "More" Prompt Truncation
**What goes wrong:** `show ip route` returns only 24 lines of output (one terminal page) because IOS-XE's SSH server paginates.
**Why it happens:** Even with PTY, IOS-XE defaults to 24-line terminal length. Without sending `terminal length 0` first, commands that produce many routes are silently truncated.
**How to avoid:** Open an interactive shell session (not `sess.Output(command)` which is one-shot exec). Send `terminal length 0\n`, wait for prompt, then send the target command, read until next prompt.
**Warning signs:** Route count in parsed output is exactly 24; output ends mid-table.

### Pitfall 3: NetFlow Template Records Received After Data Records
**What goes wrong:** First batch of flows is decoded as empty or returns errors; data appears only on second flush cycle.
**Why it happens:** NetFlow v9 exporters send template records at startup and then periodically. If the agent starts mid-stream, the first data records arrive before the first template retransmission.
**How to avoid:** Use `templates.DefaultTemplateGenerator` from goflow2/v2, which caches templates per sampler address across packets. Start the listener before beginning to flush the ring buffer (allow one flush cycle of startup grace before alerting on zero flows).
**Warning signs:** All flow decode calls return errors on first few batches after startup.

### Pitfall 4: CGO Cross-Compile Failure
**What goes wrong:** GHA `build-agent` job fails with "exec format error" or linker errors when building `linux/amd64` on `ubuntu-latest`.
**Why it happens:** Even on a Linux runner, if any transitive dependency imports `C` or uses build tags enabling CGO, cross-compilation to a different architecture requires the appropriate C cross-compiler toolchain.
**How to avoid:** Set `CGO_ENABLED=0` explicitly in the build step. Verify no transitive dep uses CGO by running `go build -v ./...` locally and checking for any `cgo` log lines.
**Warning signs:** Build fails with `cgo: C compiler "gcc" not found` or runtime crash on target device with "ELF class mismatch".

### Pitfall 5: Shared Semver Tag — Go Module Proxy Confusion
**What goes wrong:** `go get github.com/infracanvas/infracanvas/agent@v0.2.0` fails because the Go module proxy looks for a `v0.2.0` tag at the repo root but `go.mod` is in `agent/`, not the root.
**Why it happens:** Go's module proxy expects the `go.mod` at the path matching the module path. For a nested module `github.com/infracanvas/infracanvas/agent`, the tag `agent/v0.2.0` is required by Go conventions — but D-02 locks shared semver tags (plain `v0.X.Y`).
**How to avoid:** The agent is NOT intended to be imported as a library by external consumers (it is a binary, not a library module). The plain `v0.X.Y` tag is safe because no one will `go get` the agent module. GHA builds with an explicit checkout + `cd agent && go build` path, bypassing the module proxy entirely. Document in `agent/README.md` that this module is not published to pkg.go.dev.
**Warning signs:** N/A unless someone attempts `go get` of the agent module externally.

### Pitfall 6: Bearer Token Collision Between Clerk JWT and Site Token
**What goes wrong:** A push request to `/v1/agent/routes` is mistakenly validated by `require_principal` (Clerk JWT dependency) which the route does not use, but a middleware or wrong dependency order causes a 401.
**Why it happens:** If `require_principal` is applied as a global middleware (rather than a per-route dependency), all routes receive Clerk JWT validation regardless of intent.
**How to avoid:** `require_site_token` is a per-route `Depends(...)` dependency on the `/v1/agent/*` routes only. `require_principal` is NOT applied globally in this codebase (confirmed: it is a per-route dependency in existing routes). New agent routes use `require_site_token` exclusively.
**Warning signs:** `/v1/agent/routes` returns 401 `invalid_token` (Clerk error code) instead of the expected site-token error.

---

## Code Examples

### Agent Config YAML Structure
```yaml
# agent.yaml — chmod 600 (D-05)
# Source: CONTEXT.md §Specific Ideas
site_token: "ic_site_xxxxxxxxxxxxx"
backend_url: "https://api.infracanvas.dev"

devices:
  - host: "192.168.1.1"
    port: 830
    protocol: netconf
    username: "infracanvas-ro"
    password: "secret"
  - host: "192.168.1.2"
    port: 22
    protocol: ssh
    username: "infracanvas-ro"
    password: "secret"
  - host: "sw-core-01"
    protocol: config-import
    config_file: "/etc/infracanvas/sw-core-01-routes.yaml"
```

### Go Config Struct
```go
// Source: [ASSUMED] standard gopkg.in/yaml.v3 pattern
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
```

### Backend: dc_sites Alembic Migration (migration 010)
```python
# Source: [VERIFIED: existing pattern from migration 006_share_links.py]
# Follows revision ID pattern: "010_dc_sites"
# down_revision: "009_slack_webhook_url"
op.create_table(
    "dc_sites",
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("team_id", postgresql.UUID(as_uuid=True),
              sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
    sa.Column("name", sa.Text, nullable=False),               # human-readable label
    sa.Column("token_lookup_hash", sa.Text, nullable=False),  # SHA-256(raw_token), unique indexed
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)
op.create_index("ix_dc_sites_token_lookup_hash", "dc_sites", ["token_lookup_hash"], unique=True)
# RLS: team_isolation policy (same pattern as scans/share_links)
op.execute("ALTER TABLE dc_sites ENABLE ROW LEVEL SECURITY")
op.execute("ALTER TABLE dc_sites FORCE ROW LEVEL SECURITY")
op.execute("""
    CREATE POLICY team_isolation ON dc_sites
    USING (team_id = current_setting('app.current_team_id')::uuid)
    WITH CHECK (team_id = current_setting('app.current_team_id')::uuid)
""")
```

### Push Route Payload Shape (JSON)
```json
{
  "site_id": "uuid",
  "collected_at": "2026-05-07T10:30:00Z",
  "device_host": "192.168.1.1",
  "routes": [
    {
      "prefix": "10.0.0.0/8",
      "next_hop": "192.168.1.254",
      "protocol": "bgp",
      "metric": 100,
      "as_path": "65001 65002"
    }
  ]
}
```

### Retry-Twice Push Pattern
```go
// Source: [ASSUMED] standard retry pattern
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
    return nil // drop-on-retry-exhaustion (D-07)
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Juniper/go-netconf` | `nemith.io/netconf` | 2024 (Juniper archived) | Must use nemith.io; Juniper repo will not receive fixes |
| `goflow2/v1` (netsampler/goflow2) | `goflow2/v2` (same repo, v2 tag) | 2023 | v2 has breaking API changes; STATE.md locks `goflow2/v2` — do not use v1 |
| Shared `go.work` workspace for monorepo | Per-module `go.mod` (no go.work in CI) | Go 1.18+ | go.work is local-only; CI builds each module via its own `go.mod` |
| `actions/setup-go@v4` | `actions/setup-go@v6` | 2024 | v6 is current; v4 still works but use v6 for new workflows |

**Deprecated/outdated:**
- `Juniper/go-netconf`: Archived. README says use `nemith/netconf`. Do not use.
- `netsampler/goflow2` (v1 imports, no `/v2`): API incompatible with v2; STATE.md locks v2.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | IOS-XE NETCONF XPath prefix `rt:` maps to `urn:ietf:params:xml:ns:yang:ietf-routing` | Code Examples (Pattern 2) | Wrong XPath returns empty reply; must fall back to subtree filter or use native IOS-XE YANG |
| A2 | PTY + `terminal length 0` is sufficient to get full `show ip route` output on IOS-XE without hitting pager | Pitfalls #2 | May still need to detect `--More--` prompts and send spaces on older IOS-XE versions |
| A3 | `nemith.io/netconf` v0.0.4 is compatible with Go 1.25.2 | Standard Stack | Library states "latest two Go versions"; Go 1.25 is newer than stated; likely fine but unverified |
| A4 | `require_site_token` FastAPI dep uses per-route `Depends()` not global middleware | Code Examples (Pattern 6) | If Clerk middleware is global, both deps fire on agent routes causing double-auth failure |
| A5 | `dc_sites` table belongs to the same Neon DB as other tables (teams/scans) | Architecture | If a separate DB is needed for agent data, migration strategy changes |
| A6 | The CAB packet format (Markdown + Mermaid) is acceptable to enterprise buyers | CAB section | Some enterprises require PDF or specific Word template; format may need adjustment |

---

## Open Questions

1. **IOS-XE NETCONF XPath vs Subtree filter**
   - What we know: IOS-XE supports both XPath and subtree filters per RFC 6241; `nemith.io/netconf` `rpc.Filter` supports both via `Type: "xpath"` or `Type: "subtree"`.
   - What's unclear: Exact YANG model path for routing table varies between `ietf-routing` (RFC 8349) and Cisco native `Cisco-IOS-XE-route-oper` YANG model depending on IOS-XE release.
   - Recommendation: Implement subtree filter as the primary path (simpler, no namespace issues); add XPath as an optional config flag. Validate against a CSR1000v or DevNet sandbox before marking DCA-02 complete.

2. **BGP neighbor state YANG path**
   - What we know: IOS-XE supports `Cisco-IOS-XE-bgp-oper` YANG model for BGP operational state.
   - What's unclear: Whether `ietf-bgp` or the Cisco-native YANG model is more reliable across IOS-XE versions in the field.
   - Recommendation: Use `Cisco-IOS-XE-bgp-oper` (native); it is more complete and avoids version gaps in `ietf-bgp` support.

3. **`POST /v1/sites` — admin-only or team-owner-only?**
   - What we know: CONTEXT.md D-03 says "admin endpoint or CLI seed command". Phase 10 ships backend endpoint only, no dashboard UI.
   - What's unclear: Should this endpoint use `require_role("owner")` (restricting to team owners only) or be further protected by a separate `INFRACANVAS_ADMIN_KEY` header for ops-only access?
   - Recommendation: Use `require_role("owner")` consistent with other team-management routes. The ops-only flag can be added in Phase 11 if needed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Go toolchain | agent/ build, tests | ✓ | go1.25.2 darwin/arm64 | — |
| `actions/setup-go@v6` | GHA CI + release | ✓ (GHA-provided) | v6.4.0 | — |
| CGO_ENABLED=0 cross-compile | `linux/amd64` agent binary from macOS runner | ✓ | — | — |
| `cyclonedx-gomod` CLI | DCA-09 SBOM generation | ✗ (not installed locally) | — | Install via `go install github.com/CycloneDX/cyclonedx-gomod/cmd/cyclonedx-gomod@latest` in Wave 0 |
| Docker (testcontainers) | Backend dc_sites migration tests | ✓ (confirmed in STATE.md Plan 07.5-06) | ryuk 0.8.1 | — |
| Cisco IOS-XE device | DCA-02 live NETCONF validation | ✗ | — | Cisco DevNet always-on sandbox (devnetsandbox.cisco.com) or CSR1000v locally; mock interface in tests |

**Missing dependencies with no fallback:** None — all blocking items have documented fallbacks.

**Missing dependencies with fallback:**
- `cyclonedx-gomod`: Install in Wave 0 / DCA-09 plan as a Wave N task step.
- Real IOS-XE device: Use Cisco DevNet sandbox for manual validation of DCA-02. Agent tests use mock interface injection.

---

## Validation Architecture

### Test Framework

#### Go Agent
| Property | Value |
|----------|-------|
| Framework | Go standard `testing` + `github.com/stretchr/testify` v1.11.1 |
| Config file | none — `go test ./...` from `agent/` |
| Quick run command | `cd agent && go test ./... -count=1 -timeout 30s` |
| Full suite command | `cd agent && go test ./... -race -count=1 -timeout 120s` |

#### Backend (Python)
| Property | Value |
|----------|-------|
| Framework | pytest ~8.3.0 (existing) |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd backend && pytest tests/test_agent.py -x -q` |
| Full suite command | `cd backend && pytest --cov=app --cov-report=term-missing -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DCA-01 | `infracanvas-agent run --config agent.yaml` starts daemon, exits on SIGINT | unit + smoke | `cd agent && go test ./cmd/... -run TestDaemonStartStop -timeout 10s` | ❌ Wave 0 |
| DCA-02 | NETCONF session opens, get-config RPC returns XML, routes parsed | unit (mock) | `cd agent && go test ./internal/netconf/... -run TestNetconfCollector` | ❌ Wave 0 |
| DCA-03 | SSH session opens, `show ip route` parsed to RouteRecord slice | unit (mock) | `cd agent && go test ./internal/ssh/... -run TestSSHCollector` | ❌ Wave 0 |
| DCA-04 | UDP packet on :2055 decoded to FlowRecord; template reuse across packets | unit | `cd agent && go test ./internal/netflow/... -run TestNetFlowListener` | ❌ Wave 0 |
| DCA-04 | Ring buffer Append + Drain are concurrent-safe | unit + race | `cd agent && go test ./internal/netflow/... -race -run TestRingBuffer` | ❌ Wave 0 |
| DCA-05 | Push client sends POST with Bearer header; retries twice on 5xx; drops after 3 failures | unit (httptest) | `cd agent && go test ./internal/push/... -run TestPushClient` | ❌ Wave 0 |
| DCA-05 | Backend `POST /v1/agent/routes` validates site token; returns 401 on bad token | integration | `cd backend && pytest tests/test_agent.py::test_agent_routes_auth -x` | ❌ Wave 0 |
| DCA-06 | Ticker fires at correct intervals; all three tickers coexist | unit | `cd agent && go test ./cmd/... -run TestTickerIntervals` | ❌ Wave 0 |
| DCA-07 | `protocol: config-import` reads YAML file and produces RouteRecord (no network) | unit | `cd agent && go test ./internal/config/... -run TestConfigImport` | ❌ Wave 0 |
| DCA-08 | `linux/amd64` binary built from release.yml; artifact attached to GH release | GHA check | Manual GHA run on test tag | N/A |
| DCA-09 | CAB packet files exist: architecture diagram, data flow, threat model, SBOM | manual | `ls agent/docs/cab/` | ❌ Wave N (last plan) |

### Sampling Rate
- **Per task commit:** `cd agent && go test ./... -count=1 -timeout 30s`
- **Per wave merge:** `cd agent && go test ./... -race -count=1` + `cd backend && pytest tests/test_agent.py -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `agent/internal/netconf/collector_test.go` — mock NETCONF server or interface injection — covers DCA-02
- [ ] `agent/internal/ssh/collector_test.go` — mock SSH server — covers DCA-03
- [ ] `agent/internal/netflow/listener_test.go` + `buffer_test.go` — UDP test sender + ring buffer race — covers DCA-04
- [ ] `agent/internal/push/client_test.go` — `httptest.Server` stubs — covers DCA-05
- [ ] `backend/tests/test_agent.py` — pytest for `/v1/sites` + `/v1/agent/routes` + `/v1/agent/flows` — covers DCA-05 backend
- [ ] `agent/cmd/infracanvas-agent/main_test.go` — daemon start/stop + ticker interval — covers DCA-01, DCA-06
- [ ] `agent/internal/config/config_test.go` — YAML parse + config-import mode — covers DCA-07

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Site-token: `secrets.token_urlsafe(32)` + SHA-256 lookup hash; Clerk JWT unchanged |
| V3 Session Management | no | Agent is stateless; no user sessions |
| V4 Access Control | yes | `require_site_token` dep; RLS on `dc_sites` table scoped to `team_id` |
| V5 Input Validation | yes | Pydantic models on `POST /v1/agent/routes` and `POST /v1/agent/flows` payloads |
| V6 Cryptography | yes | TLS 1.2+ for HTTPS push (Go stdlib `net/http` default); SHA-256 for token lookup hash; never hand-roll crypto |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Forged site token | Spoofing | SHA-256 lookup + timing-safe compare (`hmac.compare_digest` or SHA-256 is safe for equality) |
| Credential exfiltration from agent.yaml | Information Disclosure | File permissions chmod 600; credentials never in push payload; documented in CAB packet |
| Replay attack on push endpoint | Tampering | TLS prevents replay; token is long-lived (revocable per-site via DB delete) |
| Malicious NetFlow packet crashing agent | Denial of Service | goflow2/v2 returns errors gracefully; listener loop continues on decode error |
| NETCONF/SSH MITM | Spoofing + Tampering | [ASSUMED] `ssh.InsecureIgnoreHostKey()` in code examples is placeholder; production should use `ssh.FixedHostKey` or `knownhosts` verification — document in CAB packet as a known limitation |
| Agent pushing to wrong backend (DNS spoofing) | Spoofing | Backend URL pinned in `agent.yaml`; TLS certificate validation enforced by Go's default `net/http` client |

**CAB packet required disclosures (DCA-09):**
1. Device credentials (username/password) are stored in plaintext in `agent.yaml` on the agent host, protected only by OS file permissions (chmod 600). Ops teams must use read-only NETCONF service accounts.
2. SSH host key verification uses `InsecureIgnoreHostKey()` in initial implementation — document this as a known risk and remediation path (use known_hosts file).
3. Site token is long-lived; revocation requires manual DB delete (no expiry). Phase 10 has no token rotation mechanism.
4. Only topology and routing data is transmitted — no configuration data, no credentials.

---

## Sources

### Primary (HIGH confidence)
- `nemith.io/netconf` README — https://github.com/nemith/netconf — API patterns, SSH transport, IOS-XE compatibility
- Context7 `/netsampler/goflow2` — UDP listener, NFv9 decode, template management API
- Context7 `/spf13/cobra` — CLI flags, command structure
- `proxy.golang.org` — verified versions: cobra v1.10.2, goflow2/v2 v2.2.6, nemith.io/netconf v0.0.4, golang.org/x/crypto v0.50.0, testify v1.11.1, zap v1.28.0
- Existing repo: `backend/migrations/versions/20260428_006_share_links.py` — SHA-256 lookup hash pattern
- Existing repo: `backend/app/routes/webhooks.py` — Bearer token extraction pattern
- Existing repo: `.github/workflows/release.yml` — existing release workflow structure to extend
- Existing repo: `.github/workflows/ci.yml` — existing CI structure for adding `test-agent` job
- Go 1.25.2 confirmed available locally via `go version`

### Secondary (MEDIUM confidence)
- CycloneDX/cyclonedx-gomod README — https://github.com/CycloneDX/cyclonedx-gomod — SBOM generation for Go
- Cisco NETCONF/YANG IOS-XE guide — https://www.cisco.com/c/en/us/support/docs/storage-networking/management/200933-YANG-NETCONF-Configuration-Validation.html
- NETCONF XPath filter patterns — https://rayka-co.com/lesson/netconf-xpath-filter-example-for-get-command/
- OWASP STRIDE threat model — https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html

### Tertiary (LOW confidence)
- IOS-XE NETCONF XPath routing paths — community forum + Cisco docs; not validated against a live device
- Go monorepo patterns — community blogs; Go workspaces local-only recommendation is well-established

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against proxy.golang.org on 2026-05-07
- Architecture: HIGH — based on verified library APIs and existing codebase patterns
- NETCONF XPath specifics: MEDIUM — library API confirmed; exact XPath strings flagged as ASSUMED (A1)
- SSH CLI fallback: MEDIUM — PTY pattern confirmed from official docs; `terminal length 0` is well-known IOS-XE pattern
- Pitfalls: HIGH — library-specific pitfalls verified via nemith README and goflow2 source; IOS-XE pitfalls are MEDIUM (community knowledge)
- CAB packet format: LOW — no single authoritative "enterprise CAB packet" standard exists; STRIDE + SBOM + architecture diagram is the common pattern

**Research date:** 2026-05-07
**Valid until:** 2026-06-07 (30 days — nemith.io/netconf is pre-1.0, check for API changes before planning execution)

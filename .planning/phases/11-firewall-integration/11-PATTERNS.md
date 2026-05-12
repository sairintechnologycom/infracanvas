# Phase 11: Firewall Integration — Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 24 (NEW: 17, MODIFIED: 7)
**Analogs found:** 24 / 24 (Phase 10 codebase is a tight, direct analog for every file)

---

## File Classification

### NEW files (17)

| File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `agent/internal/asa/rest.go` | collector | request-response (HTTPS REST + token cache) | `agent/internal/netconf/collector.go` | role-match (REST not NETCONF, but same Dialer/Collector shape) |
| `agent/internal/asa/rest_test.go` | test (collector) | httptest-driven | `agent/internal/netconf/collector_test.go` | exact |
| `agent/internal/asa/ssh.go` | collector | request-response (SSH show running-config) | `agent/internal/ssh/collector.go` | exact |
| `agent/internal/asa/ssh_test.go` | test (collector) | fixture-driven | `agent/internal/ssh/collector_test.go` + `parser_test.go` | exact |
| `agent/internal/asa/types.go` | types | (struct shapes shared between rest/ssh) | `agent/internal/netconf/types.go` | exact |
| `agent/internal/fmc/client.go` | collector | request-response (REST + token+refresh) | `agent/internal/netconf/collector.go` | role-match |
| `agent/internal/fmc/client_test.go` | test (collector) | httptest-driven | `agent/internal/netconf/collector_test.go` | exact |
| `agent/internal/fmc/types.go` | types | wire shapes | `agent/internal/netconf/types.go` | exact |
| `agent/internal/checkpoint/live.go` | collector | request-response (login → fetch → logout) | `agent/internal/netconf/collector.go` | role-match |
| `agent/internal/checkpoint/live_test.go` | test (collector) | httptest-driven | `agent/internal/netconf/collector_test.go` | exact |
| `agent/internal/checkpoint/parser.go` | utility (pure parser) | transform | `agent/internal/ssh/parser.go` | role-match (regex parser → JSON unmarshal) |
| `agent/internal/checkpoint/parser_test.go` | test (parser) | fixture-driven | `agent/internal/ssh/parser_test.go` | exact |
| `agent/internal/checkpoint/import.go` | loader (file-read) | file-I/O | `agent/internal/config/import.go` | exact (CKP-02 mirrors config-import) |
| `agent/internal/checkpoint/import_test.go` | test (loader) | fixture-driven | `agent/internal/config/import_test.go` (sibling of import.go) | exact |
| `agent/internal/checkpoint/types.go` | types | shared between live/import | `agent/internal/netconf/types.go` | exact |
| `backend/app/routes/firewalls.py` | read-handler (Clerk JWT) | request-response | `backend/app/routes/github.py` (`list_installations_endpoint`) | exact |
| `backend/app/schemas/firewall.py` | pydantic-schema | (push body + read response) | `backend/app/schemas/agent.py` | exact |
| `backend/migrations/versions/20260510_011_firewall_tables.py` | migration | DDL + RLS | `backend/migrations/versions/20260507_010_dc_sites.py` | exact |
| `backend/app/tasks/firewall_prune.py` | task (taskiq periodic) | batch | (Phase 6 taskiq workers) | role-match — see "No Analog" |

### MODIFIED files (7)

| File | Role | Data Flow | Closest Analog (in-file) | Match |
|---|---|---|---|---|
| `agent/cmd/infracanvas-agent/main.go` | ticker-wiring | event-driven (4th ticker + dispatch) | self — extends `Intervals` + `runDaemonWithIntervals` + `collectorFor` | exact |
| `agent/internal/config/config.go` | config-validation | file-I/O | self — extends protocol switch | exact |
| `agent/internal/push/client.go` | push-method | request-response | self — `PushRoutes` / `PushFlows` extended with 3 firewall methods | exact |
| `agent/internal/push/types.go` | push-payload | wire contract | self — `RoutesPayload` / `FlowsPayload` shape mirrored × 3 | exact |
| `backend/app/routes/agent.py` | push-handler (site-token) | request-response | self — `push_routes` / `push_flows` shape mirrored × 3 | exact |
| `backend/app/db/models.py` | ORM model | (mapping) | self — `DCSite` ORM class lines 169-193 | exact |
| `backend/app/main.py` | router-include | wiring | self — `app.include_router(...)` line 49 | exact |
| `agent/docs/cab/{threat-model,architecture,dataflow,known-limitations,operator-runbook}.md` | cab-doc | docs (EXTEND) | self — Phase 10 DCA-09 packet (do NOT replace) | exact |

---

## Pattern Assignments

### `agent/cmd/infracanvas-agent/main.go` (ticker-wiring) — MODIFY

**Analog:** self (Phase 10 final state)

**Intervals struct extension** (current lines 42-57 → extend with 4th field):

```go
// CURRENT (lines 44-57)
type Intervals struct {
    Routes time.Duration
    BGP    time.Duration
    Flow   time.Duration
}
func defaultIntervals() Intervals {
    return Intervals{
        Routes: 5 * time.Minute,
        BGP:    1 * time.Minute,
        Flow:   30 * time.Second,
    }
}

// PHASE 11 EXTENSION — append Firewall field per CONTEXT.md D-02
//   Firewall: 1 * time.Hour,
```

**Pusher interface extension** (current lines 59-64 — Phase 11 adds 3 methods):

```go
type Pusher interface {
    PushRoutes(ctx context.Context, p push.RoutesPayload) error
    PushFlows(ctx context.Context, p push.FlowsPayload) error
    // PHASE 11 — append:
    // PushFirewallRules(ctx context.Context, p push.FirewallRulesPayload) error
    // PushFirewallNAT(ctx context.Context, p push.FirewallNATPayload) error
    // PushFirewallObjects(ctx context.Context, p push.FirewallObjectsPayload) error
}
```

**`collectorFor` dispatch pattern** (lines 75-93 — extend with new protocol cases):

```go
func collectorFor(dev config.Device) RouteCollectorFn {
    switch dev.Protocol {
    case config.ProtocolNetconf:
        c := netconf.NewCollector(netconf.DefaultDialer())
        return func(ctx context.Context, d config.Device) ([]netconf.RouteRecord, error) {
            return c.GetRoutes(ctx, d.Host, d.Port, d.Username, d.Password)
        }
    case config.ProtocolSSH: ...
    case config.ProtocolConfigImport: ...
    }
    return nil
}
```
**Phase 11 keeps:** the type-switch-on-protocol shape, the closure-over-Collector pattern, the nil-return-for-unsupported branch.
**Phase 11 changes:** add a parallel `firewallCollectorFor(dev)` (or add cases to a new `collectAndPushFirewall`) returning a `(rules, nat, objects, err)` tuple. Plan 11-11 wires this.

**Ticker select-loop pattern** (lines 250-268 — extend with 4th case):

```go
routeT := time.NewTicker(iv.Routes)
bgpT := time.NewTicker(iv.BGP)
flowT := time.NewTicker(iv.Flow)
defer routeT.Stop()
defer bgpT.Stop()
defer flowT.Stop()

var wg sync.WaitGroup
for {
    select {
    case <-ctx.Done():
        log.Info("agent_shutdown_signal", zap.String("reason", ctx.Err().Error()))
        wg.Wait()
        log.Info("agent_stopped")
        return nil
    case <-routeT.C:
        wg.Add(1)
        go func() { defer wg.Done(); collectAndPushRoutes(ctx, cfg, pusher, log) }()
    case <-bgpT.C: ...
    case <-flowT.C: ...
    // PHASE 11 — append 4th case mirroring exactly:
    // fwT := time.NewTicker(iv.Firewall); defer fwT.Stop()
    // case <-fwT.C:
    //     wg.Add(1)
    //     go func() { defer wg.Done(); collectAndPushFirewall(ctx, cfg, pusher, log) }()
    }
}
```

**`collectAndPushFirewall` shape** — model on `collectAndPushRoutes` (lines 98-127). For each device, dispatch by protocol, mint a snapshot_id (UUIDv4 — RESEARCH Pattern 2), push three payloads with the same snapshot_id, log on failure but never panic.

**Notes:**
- Keep the no-op stub commit pattern: Phase 10 plan 10-07 introduced `collectAndPushBGP` as a `_log.Debug("bgp_tick_noop_phase10")` stub before BGP collection landed. Plan 11-06 should land a `collectAndPushFirewall` stub first; Plan 11-11 fills it in.
- Hermetic-test seam: `checkpoint-import` protocol must be the only one used in the main-loop test (mirrors Phase 10 use of `config-import` — RESEARCH §"Hermetic test wiring").

---

### `agent/internal/config/config.go` (config-validation) — MODIFY

**Analog:** self (current lines 15-79)

**Protocol consts pattern** (lines 16-20):

```go
// CURRENT
const (
    ProtocolNetconf      = "netconf"
    ProtocolSSH          = "ssh"
    ProtocolConfigImport = "config-import"
)
// PHASE 11 — append five new consts, exactly mirroring naming style:
// ProtocolASARest         = "asa-rest"
// ProtocolASASSH          = "asa-ssh"
// ProtocolFMC             = "fmc"
// ProtocolCheckpoint      = "checkpoint"
// ProtocolCheckpointImport = "checkpoint-import"
```

**Device struct** (lines 30-38) — **NO new fields**. Reuse `Host`/`Port`/`Protocol`/`Username`/`Password`/`ConfigFile`/`SiteID`. CONTEXT D-16 explicitly forbids new fields.

**Validation switch** (lines 64-77 — extend the `switch d.Protocol` arm):

```go
for i, d := range c.Devices {
    switch d.Protocol {
    case ProtocolNetconf, ProtocolSSH, ProtocolConfigImport:
        // ok
    // PHASE 11 — extend with: ProtocolASARest, ProtocolASASSH, ProtocolFMC,
    //                          ProtocolCheckpoint, ProtocolCheckpointImport
    default:
        return fmt.Errorf("device[%d]: invalid protocol: %s", i, d.Protocol)
    }
    if d.Protocol == ProtocolConfigImport && d.ConfigFile == "" {
        return fmt.Errorf("device[%d]: config_file required when protocol=config-import", i)
    }
    // PHASE 11 — add same guard for ProtocolCheckpointImport:
    //   if d.Protocol == ProtocolCheckpointImport && d.ConfigFile == "" { ... }
    if d.Protocol != ProtocolConfigImport && d.Host == "" {
        return fmt.Errorf("device[%d]: host required when protocol=%s", i, d.Protocol)
    }
    // PHASE 11 — exempt ProtocolCheckpointImport from the host requirement:
    //   amend the condition to (... != Cci && ... != Cgi && d.Host == "")
}
```

**Notes:** keep the early-return error message format `device[%d]: <field> required when protocol=<p>` verbatim — tests grep for this string.

---

### `agent/internal/checkpoint/import.go` (loader, file-I/O) — NEW (mirrors `config/import.go`)

**Analog:** `agent/internal/config/import.go` (full file, 54 lines)

**Pattern to copy verbatim** (lines 19-54):

```go
type configImportRoute struct {
    Prefix   string `yaml:"prefix"`
    NextHop  string `yaml:"next_hop"`
    Protocol string `yaml:"protocol"`
    Metric   int    `yaml:"metric"`
    ASPath   string `yaml:"as_path"`
}

type configImportFile struct {
    Routes []configImportRoute `yaml:"routes"`
}

func LoadConfigImport(path string) ([]netconf.RouteRecord, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("config-import: read %s: %w", path, err)
    }
    var f configImportFile
    if err := yaml.Unmarshal(data, &f); err != nil {
        return nil, fmt.Errorf("config-import: parse %s: %w", path, err)
    }
    out := make([]netconf.RouteRecord, 0, len(f.Routes))
    for _, r := range f.Routes {
        out = append(out, netconf.RouteRecord{ Prefix: r.Prefix, ... })
    }
    return out, nil
}
```

**Phase 11 differences:**
- Three input files (`.rulebase.json`, `.nat.json`, `.objects.json`) instead of one YAML — RESEARCH Pattern 1 / Open Q3.
- `encoding/json` not `yaml.v3` (Checkpoint exports JSON).
- Returns `(Rules, NATs, Objects, error)` — calls into `parser.Parse()` for the actual unmarshaling so the file-I/O wrapper stays a thin shell (matches Pattern 1 separation of concerns).
- Error message prefix `"checkpoint-import: …"` (mirrors `"config-import: …"`).
- Empty-file guarantee: return empty slice not nil (mirrors `LoadConfigImport`'s "empty files return empty slice and nil error" promise — required so the agent pushes empty snapshots rather than silently skipping).

---

### `agent/internal/asa/ssh.go` (collector, SSH-driven) — NEW

**Analog:** `agent/internal/ssh/collector.go` (132 lines)

**Pattern: Dialer + Session interfaces + interactiveSession** (lines 18-74, 80-129):

```go
// Test seam: Session abstracts what the production interactiveSession does
type Session interface {
    Run(ctx context.Context, command string) (string, error)
    Close() error
}
type Dialer interface {
    Dial(ctx context.Context, host string, port int, user, pass string) (Session, error)
}

type Collector struct { dialer Dialer }
func NewCollector(d Dialer) *Collector { return &Collector{dialer: d} }

// GetRoutes runs `show ip route` over an interactive PTY-allocated session
// and returns the parsed route table. Caller passes primitives rather than
// a config.Device to avoid an internal/config ↔ internal/ssh import cycle
func (c *Collector) GetRoutes(ctx context.Context, host string, port int, user, pass string) ([]netconf.RouteRecord, error) {
    if port == 0 { port = 22 }
    sess, err := c.dialer.Dial(ctx, host, port, user, pass)
    if err != nil { return nil, fmt.Errorf("ssh: dial %s:%d: %w", host, port, err) }
    defer func() { _ = sess.Close() }()
    out, err := sess.Run(ctx, "show ip route")
    if err != nil { return nil, fmt.Errorf("ssh: run %s: %w", host, err) }
    return ParseShowIPRoute(out), nil
}

// Production dialer — InsecureIgnoreHostKey is CAB-documented (T-10-05-01)
func (defaultDialer) Dial(ctx context.Context, host string, port int, user, pass string) (Session, error) {
    cfg := &cryptossh.ClientConfig{
        User: user,
        Auth: []cryptossh.AuthMethod{cryptossh.Password(pass)},
        HostKeyCallback: cryptossh.InsecureIgnoreHostKey(),  // CAB-documented
        Timeout: 10 * time.Second,
    }
    ...
}

// PTY pattern: terminal length 0 + command + exit\n in a single shell payload
// Required for IOS-XE / ASA — without it `show running-config` truncates at 24 lines
modes := cryptossh.TerminalModes{
    cryptossh.ECHO:          0,                     // T-10-05-02 — no PTY echo
    cryptossh.TTY_OP_ISPEED: 14400,
    cryptossh.TTY_OP_OSPEED: 14400,
}
...
payload := "terminal length 0\n" + command + "\nexit\n"
```

**Phase 11 ASA SSH differences:**
- Command is `show running-config` (or `show running-config access-list ; show running-config nat`) — RESEARCH Pitfall 4. Same `terminal length 0` pager mitigation as Phase 10.
- Returns `([]asa.Rule, []asa.NATRule, []asa.Object, error)` — three slices, not one route slice.
- ACL parser: linear-time regex per CONTEXT D-12 / RESEARCH "Don't Hand-Roll" row 4 — copy the line-by-line scan structure from `agent/internal/ssh/parser.go` (skip non-matching lines, no backreferences, no unbounded quantifiers per T-10-05-03).

---

### `agent/internal/asa/rest.go` + `agent/internal/fmc/client.go` + `agent/internal/checkpoint/live.go` (collectors, HTTPS REST) — NEW

**Analog:** `agent/internal/netconf/collector.go` (Dialer/Collector/Session pattern lines 39-78) + RESEARCH Pattern 3 (token cache).

**Pattern to copy from netconf:**

```go
// Session is the minimal NETCONF session surface the Collector needs.
// Implemented by *netconf.Session in production and by mocks in tests.
type Session interface {
    GetSubtree(ctx context.Context, filter string) ([]byte, error)
    Close() error
}
type Dialer interface {
    Dial(ctx context.Context, host string, port int, user, pass string) (Session, error)
}

type Collector struct { dialer Dialer }
func NewCollector(d Dialer) *Collector { return &Collector{dialer: d} }

func (c *Collector) GetRoutes(ctx context.Context, host string, port int, user, pass string) ([]RouteRecord, error) {
    if port == 0 { port = 830 }
    sess, err := c.dialer.Dial(ctx, host, port, user, pass)
    if err != nil { return nil, fmt.Errorf("netconf: dial %s:%d: %w", host, port, err) }
    defer func() { _ = sess.Close() }()
    body, err := sess.GetSubtree(ctx, ietfRoutingSubtreeFilter)
    if err != nil { return nil, fmt.Errorf("netconf: rpc get %s: %w", host, err) }
    return parseRoutesXML(body)
}
```

**ASA REST token cache** (RESEARCH Pattern 3):
```go
type RESTCollector struct {
    http  *http.Client
    cache map[string]asaToken  // host -> token; cleared per-pull
}
func (c *RESTCollector) Pull(ctx context.Context, dev config.Device) (...) {
    tok, err := c.acquireToken(ctx, dev)        // POST /api/tokenservices
    if err != nil { return nil, nil, nil, err }
    defer c.deleteToken(ctx, dev, tok)          // DELETE /api/tokenservices/{tok} — best-effort
    // GET /api/objects/networkobjects, /api/access/in/.../rules, /api/nat with X-Auth-Token: tok
}
```

**Checkpoint login-per-pull** (RESEARCH Pattern 1, CONTEXT D-14):
```go
func (c *LiveCollector) Pull(ctx context.Context, dev config.Device) (Rules, NATs, Objects, error) {
    sid, err := c.login(ctx, dev)
    if err != nil { return nil, nil, nil, err }
    defer c.logout(ctx, sid)            // best-effort; WARN on failure (CONTEXT.md <specifics>)
    rb, err := c.showAccessRulebase(ctx, sid, dev)   // paginate via offset; max 500/page
    nb, err := c.showNATRulebase(ctx, sid, dev)
    objs, err := c.showObjects(ctx, sid, dev)
    return Parse(rb, nb, objs)          // shared parser (parser.go)
}
```

**Notes (apply to all three REST collectors):**
- Use `http.Client{Timeout: 10*time.Second}` (mirrors netconf SSH dial timeout).
- Caller passes primitives (`host, port, user, pass, siteID`) not a `config.Device` — avoids the `internal/config ↔ internal/<vendor>` import cycle established in Phase 10 (see comment at netconf collector.go line 61-62).
- Errors: `fmt.Errorf("<vendor>: <stage> %s: %w", host, err)` (mirrors `"netconf: dial %s:%d: %w"`).
- Logging: NEVER log username/password/SID/token. Phase 10 mitigations T-10-04-02 / T-10-05-02 / T-10-07-02 extend to firewall collectors. Log only `host` + `protocol` + pull-id (RESEARCH Anti-Patterns).
- NO retry/backoff inside collectors — `agent/internal/push/Client` owns retries (D-07). Collectors fail-and-return; the next ticker tick is the retry (RESEARCH Anti-Patterns).

---

### `agent/internal/checkpoint/parser.go` (utility, transform — pure function) — NEW

**Analog:** RESEARCH Pattern 1 + structure-mirror of `agent/internal/ssh/parser.go`.

**Signature contract:**
```go
// Parse takes a raw mgmt_cli show-access-rulebase / show-nat-rulebase / show-objects
// JSON byte slice and returns normalized slices. Pure function — no I/O.
func Parse(rulebaseJSON, natJSON, objectsJSON []byte) (Rules, NATs, Objects, error)
```

**Why this matters:** both `live.go` (HTTP) and `import.go` (file) call this single function. `parser_test.go` MUST cover BOTH live and import shapes with paired fixtures (RESEARCH §Risk Landmines #7 — `TestParser_LiveImportEquivalence`).

**Notes:** RESEARCH "Don't Hand-Roll" row 3 — use `encoding/json` into typed structs, NOT a recursive descent parser. Checkpoint JSON shape is regular and documented.

---

### `agent/internal/push/client.go` (push-method) — MODIFY

**Analog:** self (Phase 10 final state)

**Three methods to add — exact shape of `PushRoutes` lines 84-93:**

```go
// PushRoutes POSTs a routes batch with retry-twice-then-drop semantics (D-07).
// Returns nil after 3 retried-failures: the batch is silently dropped.
// Returns a non-nil error ONLY for non-retryable failures (4xx — 401/403/422)
// so the caller can surface auth/validation problems explicitly to operators.
func (c *Client) PushRoutes(ctx context.Context, p RoutesPayload) error {
    body, err := json.Marshal(p)
    if err != nil {
        return fmt.Errorf("push: marshal routes: %w", err)
    }
    return c.postWithRetry(ctx, routesPath, body, "routes",
        zap.String("site_id", p.SiteID),
        zap.String("device_host", p.DeviceHost),
        zap.Int("count", len(p.Routes)))
}
```

**Phase 11 — three new methods + three new path consts:**
```go
const (
    firewallRulesPath   = "/v1/agent/firewall-rules"
    firewallNATPath     = "/v1/agent/firewall-nat"
    firewallObjectsPath = "/v1/agent/firewall-objects"
)
// PushFirewallRules / PushFirewallNAT / PushFirewallObjects — each calls
// postWithRetry with kind="firewall-rules"/"firewall-nat"/"firewall-objects"
// and zap fields: site_id, snapshot_id, firewall_id, count.
```

**postWithRetry MUST NOT be touched** (lines 108-144) — the D-07 retry contract is locked. Phase 11 reuses it verbatim (RESEARCH "Don't Hand-Roll" row 1).

**Notes:** the `T-10-07-02` token-redaction guarantee applies — log fields never contain the token; response body sample is capped at 512 bytes (line 166 `io.CopyN(&sample, resp.Body, 512)`).

---

### `agent/internal/push/types.go` (push-payload, wire contract) — MODIFY

**Analog:** self (full file, 26 lines)

**Pattern:**
```go
// RoutesPayload is the wire contract for POST /v1/agent/routes.
// Field names match backend Pydantic RoutesPushBody exactly (Plan 10-02 —
// backend/app/schemas/agent.py). Any drift on either side breaks the
// agent ↔ backend contract.
type RoutesPayload struct {
    SiteID      string                `json:"site_id"`
    CollectedAt string                `json:"collected_at"`
    DeviceHost  string                `json:"device_host"`
    Routes      []netconf.RouteRecord `json:"routes"`
}
```

**Phase 11 — three new structs:**
```go
type FirewallRulesPayload struct {
    SiteID      string `json:"site_id"`
    SnapshotID  string `json:"snapshot_id"`        // UUIDv4 minted by agent (RESEARCH Pattern 2)
    FirewallID  string `json:"firewall_id"`         // device serial / dev.Host
    Vendor      string `json:"vendor"`              // "cisco-asa" | "cisco-fmc" | "checkpoint"
    Source      string `json:"source"`              // "asa-rest"|"asa-ssh"|"fmc"|"checkpoint"|"checkpoint-import"
    SnapshotTS  string `json:"snapshot_ts"`         // RFC3339
    Rules       []Rule `json:"rules"`
}
// FirewallNATPayload — same envelope, NATRules slice
// FirewallObjectsPayload — same envelope, Objects slice
```

**Notes:** field names MUST match Pydantic `FirewallRulesPushBody` (in `backend/app/schemas/firewall.py`) verbatim — header comment in this file is load-bearing for that contract.

---

### `backend/app/routes/agent.py` (push-handler, site-token) — MODIFY (add 3 handlers)

**Analog:** self — `push_routes` lines 86-99 + `push_flows` lines 102-114

**Pattern to mirror exactly:**
```python
@router.post("/agent/routes", status_code=status.HTTP_202_ACCEPTED)
async def push_routes(
    body: RoutesPushBody,
    principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
) -> dict[str, bool]:
    """Receive a routing-table batch from a DC agent. Phase 10 logs only — Phase 11 persists."""
    _log.info(
        "agent_routes_received",
        site_id=principal.site_id,
        team_id=principal.team_id,
        device_host=body.device_host,
        count=len(body.routes),
    )
    return {"ok": True}
```

**Phase 11 — three new endpoints (`push_firewall_rules`, `push_firewall_nat`, `push_firewall_objects`).** Unlike Phase 10 these are NOT log-only; they persist. RESEARCH Pattern 2 shows the persistence shape:

```python
async def push_firewall_rules(
    body: FirewallRulesPushBody,
    principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
) -> dict[str, bool]:
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(principal.team_id)},
        )
        # Idempotent parent insert — first endpoint to arrive wins (Pattern 2)
        await session.execute(insert(FirewallRulesetSnapshot).values(
            snapshot_id=body.snapshot_id, site_id=principal.site_id,
            firewall_id=body.firewall_id, vendor=body.vendor, source=body.source,
            snapshot_ts=body.snapshot_ts,
        ).on_conflict_do_nothing(index_elements=["snapshot_id"]))
        # Then bulk-insert children
        await session.execute(insert(FirewallRule), [...])
    _log.info("agent_firewall_rules_received",
              site_id=principal.site_id, team_id=principal.team_id,
              snapshot_id=body.snapshot_id, firewall_id=body.firewall_id,
              count=len(body.rules))
    return {"ok": True}
```

**Notes:**
- `Depends(require_site_token)` — REUSE; do NOT re-implement (RESEARCH "Don't Hand-Roll" row 2). The dependency was added in Phase 10 plan 10-02.
- `# noqa: B008` on the `Depends(...)` default — required by project lint config; copy verbatim.
- `set_config('app.current_team_id', :t, true)` — REQUIRED inside every transaction touching team-scoped tables (this is what makes RLS work). Mirror exactly.
- `status.HTTP_202_ACCEPTED` — Phase 10 chose 202 for ingest; mirror.
- Module docstring header (lines 1-12) — extend with the three new endpoints in the bullet list.

---

### `backend/app/routes/firewalls.py` (read-handler, Clerk JWT) — NEW

**Analog:** `backend/app/routes/github.py` `list_installations_endpoint` (lines 80-114)

**Pattern to copy:**
```python
from app.auth.clerk import ClerkPrincipal, require_role
from app.auth.deps import resolve_team_from_clerk_org
from app.db.models import GithubInstallation, Team
from app.db.session import get_sessionmaker

router = APIRouter(prefix="/v1/github", tags=["github"])
_log = structlog.get_logger("app.github")
_READ_ROLES = ("owner", "admin", "member", "basic_member")

@router.get("/installations", response_model=list[InstallationResp])
async def list_installations_endpoint(
    principal: ClerkPrincipal = Depends(require_role(*_READ_ROLES)),  # noqa: B008
    team: Team = Depends(resolve_team_from_clerk_org),                # noqa: B008
) -> list[InstallationResp]:
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": str(team.id)},
        )
        result = await session.execute(
            select(GithubInstallation).order_by(GithubInstallation.installed_at.desc())
        )
        rows = list(result.scalars().all())
    return [InstallationResp(...) for r in rows]
```

**Phase 11 endpoint — `GET /v1/sites/{site_id}/firewall-rules`:**
- `router = APIRouter(prefix="/v1", tags=["firewalls"])` (the `{site_id}` path param means the prefix is just `/v1`).
- `_READ_ROLES = ("owner", "admin", "member", "basic_member")` — copy verbatim.
- Site-membership check FIRST (mirrors `list_repos_endpoint` lines 144-152): `select(DCSite.id).where(DCSite.id == site_id)` — RLS isolates the lookup to the caller's team; a cross-team probe returns 404 before any further work.
- Then `select(FirewallRulesetSnapshot)` joined to children, filtered to "latest snapshot per firewall_id" (e.g., DISTINCT ON `(firewall_id) ORDER BY firewall_id, snapshot_ts DESC` per CONTEXT D-11).
- Response model: list of per-device snapshot envelopes including rules + nat + objects.

---

### `backend/app/schemas/firewall.py` (pydantic-schema) — NEW

**Analog:** `backend/app/schemas/agent.py` (full file, 78 lines)

**Pattern to copy:**
```python
from pydantic import BaseModel, Field

class RouteRecord(BaseModel):
    prefix: str
    next_hop: str
    protocol: str
    metric: int = 0
    as_path: str = ""

class RoutesPushBody(BaseModel):
    """Request body for POST /v1/agent/routes.

    T-10-02-06: routes bounded at 10 000 to prevent DoS via unbounded
    payload allocation.
    """
    site_id: str
    collected_at: str  # ISO 8601
    device_host: str
    routes: list[RouteRecord] = Field(..., max_length=10000)
```

**Phase 11 — apply identical bound pattern:**
```python
class FirewallRule(BaseModel):
    position: int
    src_zone: str | None = None
    dst_zone: str | None = None
    src_cidr: str
    dst_cidr: str
    action: str
    protocol: str | None = None
    ports: str | None = None
    raw_blob: dict  # vendor-native (D-08 hybrid)

class FirewallRulesPushBody(BaseModel):
    """Request body for POST /v1/agent/firewall-rules.

    T-11-NN-MM (planner-assigned): rules bounded at 50 000 to prevent
    DoS via unbounded payload allocation. Higher than Phase 10's 10 000
    because enterprise rule bases can legitimately exceed 10 k.
    """
    site_id: str
    snapshot_id: str         # UUIDv4 from agent
    firewall_id: str
    vendor: str
    source: str              # "asa-rest"|"asa-ssh"|"fmc"|"checkpoint"|"checkpoint-import"
    snapshot_ts: str         # ISO 8601
    rules: list[FirewallRule] = Field(..., max_length=50000)

# FirewallNATPushBody / FirewallObjectsPushBody — same envelope shape
```

**Notes:**
- Module docstring (lines 1-9) — keep the exact "Locked contracts consumed by both backend routes and the Go push client" note pattern; this contract is load-bearing.
- `from __future__ import annotations` (line 10) — copy.
- Bound rationale (`# T-10-02-06`) — Phase 11 picks new threat IDs, planner numbers them.

---

### `backend/migrations/versions/20260510_011_firewall_tables.py` (migration) — NEW

**Analog:** `backend/migrations/versions/20260507_010_dc_sites.py` (full file, 95 lines) — **canonical template** for RLS-protected team-scoped tables in this codebase.

**Pattern to copy verbatim per table:**
```python
def upgrade() -> None:
    op.create_table("dc_sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("token_lookup_hash", sa.String(64), nullable=False),
        sa.Column("created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint("dc_sites_token_lookup_hash_key", "dc_sites", ["token_lookup_hash"])
    op.create_index("ix_dc_sites_team_id", "dc_sites", ["team_id"])
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON dc_sites TO infracanvas_app;")
    op.execute("ALTER TABLE dc_sites ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE dc_sites FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY dc_sites_team_isolation ON dc_sites
          USING (team_id = current_setting('app.current_team_id', true)::uuid)
          WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
    """)
```

**Phase 11 — apply this template to all four tables** (per CONTEXT D-08/09/10):
1. `firewall_ruleset_snapshots` — has `team_id` FK + RLS policy (parent table).
2. `firewall_rules` — child of `firewall_ruleset_snapshots` via `snapshot_id` FK with `ondelete="CASCADE"`. Per RESEARCH "Don't Hand-Roll" row 6: cascade FK + a single `DELETE WHERE snapshot_ts < ...` is enough; no per-row trigger.
3. `firewall_nat_rules` — same shape as `firewall_rules`.
4. `firewall_objects` — same shape as `firewall_rules`.

**Critical patterns to keep:**
- `FORCE ROW LEVEL SECURITY` — catches future BYPASSRLS regressions (RESEARCH "Don't Hand-Roll" row 3).
- `ENABLE` + `FORCE` + `CREATE POLICY <name>_team_isolation` triplet — naming is `<table>_team_isolation` per the migration 010 precedent.
- `GRANT SELECT, INSERT, UPDATE, DELETE ON <table> TO infracanvas_app;` — required for the RLS-bounded role.
- Indexes: `(site_id, firewall_id, snapshot_ts DESC)` on `firewall_ruleset_snapshots` for the "latest per firewall" read pattern (CONTEXT Discretion bullet 5).
- For child tables, RLS policy can either be (a) repeat the team-isolation policy with a join lookup or (b) inherit via `snapshot_id` FK to a team-scoped parent. Planner picks; (a) is simpler and matches the canonical template.

**SECURITY DEFINER function** (lines 67-87) — Phase 11 does NOT need a new SECURITY DEFINER lookup function (the read API uses Clerk JWT → resolved team_id, not a token-hash lookup). Skip this part of the template.

**Doc-comment** (RESEARCH Risk Landmine #6): add a doc-comment in the migration listing the columns Phase 12 path computation reads (`src_cidr`, `dst_cidr`, `action`, `protocol`, `ports`, `src_translation`, `dst_translation`, `interface_in`, `interface_out`) so future migrations think twice before renaming.

**Migration metadata pattern (lines 15-18):**
```python
revision: str = "011_firewall_tables"
down_revision: str | None = "010_dc_sites"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

---

### `backend/app/db/models.py` (ORM models) — MODIFY (extend with 4 classes)

**Analog:** self — `DCSite` class lines 169-193

**Pattern to mirror:**
```python
class DCSite(Base):
    """DC Agent site row (Phase 10 DCA-05).

    Stores the SHA-256 lookup hash of the site-token — the plaintext token
    is returned ONCE at creation time and never stored (same pattern as
    share_links.token_lookup_hash, migration 006). RLS team_isolation policy
    (migration 010) scopes all access to the owning team.
    """
    __tablename__ = "dc_sites"
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    token_lookup_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

**Phase 11 — add four classes (`FirewallRulesetSnapshot`, `FirewallRule`, `FirewallNATRule`, `FirewallObject`)** mirroring the docstring-naming-typed-Mapped pattern. `JSONB` columns use `from sqlalchemy.dialects.postgresql import JSONB`.

---

### `backend/app/main.py` (router-include) — MODIFY (one-line add)

**Analog:** self — line 49

**Pattern:**
```python
app.include_router(agent_routes.router)   # current Phase 10 line 49
# PHASE 11 — append:
# app.include_router(firewalls_routes.router)
```

(Import line near top: `from app.routes import firewalls as firewalls_routes`.)

---

### `agent/docs/cab/{threat-model,architecture,dataflow,known-limitations}.md` (cab-doc) — EXTEND

**Analog:** `agent/docs/cab/threat-model.md` Phase 10 final state (162 lines).

**EXTEND, do NOT replace** (CONTEXT explicit, RESEARCH Plan 11-13).

**Pattern: Threat Register row** (lines 50-68 — TB-1 table):

```markdown
| Threat ID | STRIDE | Component | Disposition | Mitigation |
|-----------|--------|-----------|-------------|-----------|
| T-10-04-01 | Spoofing | NETCONF / SSH MITM on management VLAN | accept | `ssh.InsecureIgnoreHostKey()` in initial implementation. ... |
| T-10-04-02 | Information Disclosure | password log leakage via NETCONF auth | mitigate | Password held only in `ssh.Password()` auth method; never logged via zap fields. Log lines emit `host` and `protocol` only. |
| ...
| T-10-05-03 | Denial of Service | adversarial `show ip route` output | mitigate | Linear-time regex parser; non-matching lines silently skipped. No backreferences or unbounded quantifiers. |
```

**Phase 11 — add Phase 11-numbered rows under each existing Trust Boundary section** (TB-1 / TB-2 / TB-3) using IDs of the form `T-11-NN-MM` where `NN` is the plan number (e.g., `T-11-07-01` for the ASA REST collector plan). Examples:
- TB-1: `T-11-07-01` ASA REST MITM (accept — same posture as T-10-04-01); `T-11-08-01` ASA SSH parser fragility (mitigate — same linear-regex posture as T-10-05-03); `T-11-10-01` Checkpoint SID lifecycle on long pulls (mitigate — `session-timeout: 3600`).
- TB-2: `T-11-04-01` firewall payload size DoS (mitigate — Pydantic `Field(..., max_length=50000)` on rules list).
- TB-3: `T-11-05-01` firewall mgmt credentials in `agent.yaml` (mitigate — same `chmod 600` posture as T-10-03-01).

**CONTEXT.md `<specifics>` extension checklist (must be in CAB extension):**
1. Firewall mgmt credentials never leave the agent host (same as device credentials, Phase 10 D-05)
2. Only rule-base + NAT + object metadata is transmitted to SaaS — never live traffic, never password material
3. Transmission is TLS-encrypted via the existing push client
4. Site token is revocable per-site, which kills firewall ingest along with route/flow ingest
5. Login-per-pull for Checkpoint means no SID at rest

**dataflow.md** (current 107 lines) — extend the "Data Inventory" table (lines 22-34) with new rows:
- Firewall rule-base (prefix, action, protocol, port, zone) — sourced from REST/SSH/file (TB-1) — operational — YES (POST /v1/agent/firewall-rules over HTTPS, TB-2).
- Firewall NAT table — same.
- Firewall objects (host/network/group/service definitions) — same.
- Checkpoint SID — login response (TB-2 inbound) — Secret — NO (in-memory only; logout-on-pull-end).

**known-limitations.md** — add an `L-N` row for ASA REST API EOL at 9.16 (RESEARCH Pitfall 1) and Checkpoint SID timeout on >50k rule layers (RESEARCH Risk Landmine #4).

**Plan flag:** Plan 11-13 must set `autonomous: false` with `checkpoint:human-verify` gate, mirroring Phase 10 plan 10-09 pattern (CONTEXT.md research §"Plans flagged for autonomous: false").

---

## Shared Patterns

### Pattern A — Site-token Bearer auth (`require_site_token`)
**Source:** `backend/app/auth/site_token.py` (Phase 10 plan 10-02 — REUSED VERBATIM)
**Apply to:** all 3 new push handlers in `backend/app/routes/agent.py` (rules / nat / objects)
**Excerpt** (usage from `routes/agent.py:89`):
```python
principal: DCSitePrincipal = Depends(require_site_token),  # noqa: B008
```
**Why:** Phase 10 already implements SHA-256 lookup hash via `dc_site_by_token_hash` SQL function (migration 010 lines 67-87). Re-implementing is forbidden (RESEARCH "Don't Hand-Roll" row 2).

### Pattern B — Clerk JWT + Team-RLS context-setting (read API)
**Source:** `backend/app/routes/github.py` `list_installations_endpoint` (lines 80-114) + `app/auth/clerk.py` (`require_role`) + `app/auth/deps.py` (`resolve_team_from_clerk_org`)
**Apply to:** `backend/app/routes/firewalls.py` (read endpoint)
**Excerpt:**
```python
async with sm() as session, session.begin():
    await session.execute(
        text("SELECT set_config('app.current_team_id', :t, true)"),
        {"t": str(team.id)},
    )
    # ... team-scoped queries here ...
```
**Why:** every read of an RLS-protected table MUST set `app.current_team_id` inside the same transaction. Forgetting this is the most common source of "empty list" bugs (the RLS policy returns 0 rows when the GUC is unset).

### Pattern C — Postgres RLS team_isolation policy
**Source:** `backend/migrations/versions/20260507_010_dc_sites.py` (lines 51-58)
**Apply to:** all four firewall tables (`firewall_ruleset_snapshots`, `firewall_rules`, `firewall_nat_rules`, `firewall_objects`)
**Excerpt:**
```python
op.execute("ALTER TABLE dc_sites ENABLE ROW LEVEL SECURITY;")
op.execute("ALTER TABLE dc_sites FORCE ROW LEVEL SECURITY;")
op.execute("""
    CREATE POLICY dc_sites_team_isolation ON dc_sites
      USING (team_id = current_setting('app.current_team_id', true)::uuid)
      WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);
""")
```
**Why:** `FORCE` catches future BYPASSRLS regressions; `WITH CHECK` blocks INSERTs that would violate the policy.

### Pattern D — Push payload bound (T-10-02-06 pattern)
**Source:** `backend/app/schemas/agent.py:53` `Field(..., max_length=10000)`
**Apply to:** `FirewallRulesPushBody.rules`, `FirewallNATPushBody.nat_rules`, `FirewallObjectsPushBody.objects` in `backend/app/schemas/firewall.py`
**Excerpt:**
```python
routes: list[RouteRecord] = Field(..., max_length=10000)
```
**Why:** unbounded list = trivial DoS via memory allocation. Phase 11 picks a higher bound (~50000) because enterprise rule bases can legitimately exceed 10k; planner documents the chosen number with rationale.

### Pattern E — Idempotent agent-minted snapshot_id (RESEARCH Pattern 2)
**Source:** RESEARCH §Pattern 2 + this PATTERNS.md ` agent/cmd/infracanvas-agent/main.go` section.
**Apply to:** all 3 new push handlers in `backend/app/routes/agent.py`
**Excerpt:**
```python
await session.execute(insert(FirewallRulesetSnapshot).values(
    snapshot_id=body.snapshot_id, ...
).on_conflict_do_nothing(index_elements=["snapshot_id"]))
```
**Why:** removes ordering coupling between the three endpoints — whichever arrives first creates the parent row, the others skip the parent insert via ON CONFLICT.

### Pattern F — Push retry-twice-then-drop (D-07)
**Source:** `agent/internal/push/client.go:108-144` (`postWithRetry`) — REUSED VERBATIM
**Apply to:** all 3 new push methods (`PushFirewallRules`, `PushFirewallNAT`, `PushFirewallObjects`)
**Excerpt:**
```go
return c.postWithRetry(ctx, routesPath, body, "routes",
    zap.String("site_id", p.SiteID),
    zap.String("device_host", p.DeviceHost),
    zap.Int("count", len(p.Routes)))
```
**Why:** D-07 retry contract is locked. The 3-attempt cap + linear backoff + 4xx-bail-out + drop-and-WARN behaviour is regression-tested. Per-collector retry logic is FORBIDDEN (RESEARCH Anti-Patterns).

### Pattern G — Token / credential redaction
**Source:** `agent/docs/cab/threat-model.md` mitigations T-10-04-02 / T-10-05-02 / T-10-07-02
**Apply to:** every new collector (asa, fmc, checkpoint) AND every new push method.
**Rules:**
1. Log only `host`, `protocol`, `pull_id`, `count`. NEVER log `username`, `password`, `sid`, `token`.
2. Response body samples capped at 512 bytes (`io.CopyN(&sample, resp.Body, 512)` in push client line 166).
3. PTY echo disabled for SSH (`cryptossh.TerminalModes{ECHO: 0}` — ssh/collector.go line 92).

### Pattern H — Caller passes primitives, not config.Device
**Source:** `agent/internal/netconf/collector.go:60-63` comment + `agent/internal/ssh/collector.go:36-38` comment
**Apply to:** every new collector signature (asa.RESTCollector, asa.SSHCollector, fmc.Collector, checkpoint.LiveCollector)
**Excerpt:**
```go
// Caller passes primitives rather than a config.Device to avoid an
// internal/config ↔ internal/netconf import cycle (config depends on
// netconf.RouteRecord; netconf would otherwise pull config in).
func (c *Collector) GetRoutes(ctx context.Context, host string, port int, user, pass string) ([]RouteRecord, error)
```
**Why:** prevents an import cycle. The `collectorFor` dispatcher in `main.go` is the only place that touches `config.Device` and unpacks it.

### Pattern I — Hermetic main-loop test via file-read protocol
**Source:** `agent/cmd/infracanvas-agent/main.go:13` + comment at lines 67-69 + `agent/internal/config/import.go`
**Apply to:** Phase 11 main-loop test for the firewall ticker — use `protocol: checkpoint-import` exclusively (file read; no network).
**Excerpt:**
```go
// case config.ProtocolConfigImport:
//     return func(_ context.Context, d config.Device) ([]netconf.RouteRecord, error) {
//         return config.LoadConfigImport(d.ConfigFile)
//     }
```

---

## No Analog Found

| File | Role | Reason |
|---|---|---|
| `backend/app/tasks/firewall_prune.py` | task (taskiq periodic) | Phase 6 introduced taskiq workers but there is no existing periodic-DELETE task in the codebase. RESEARCH "Don't Hand-Roll" row 6 recommends `taskiq_periodic` because backend already runs taskiq workers; planner inspects the Phase 6 plan 06-06 task scaffolding for the closest existing periodic-task shape. The DELETE itself is trivial: `DELETE FROM firewall_ruleset_snapshots WHERE snapshot_ts < NOW() - INTERVAL '<TTL>';` — child tables cascade. |

---

## Metadata

**Analog search scope:**
- `agent/cmd/`, `agent/internal/{config,push,netconf,ssh,netflow}/`
- `agent/docs/cab/`
- `backend/app/{routes,schemas,db,auth}/`
- `backend/migrations/versions/`

**Files scanned (read in this pass):**
- `agent/cmd/infracanvas-agent/main.go` (full)
- `agent/internal/config/config.go` (full)
- `agent/internal/config/import.go` (full)
- `agent/internal/push/client.go` (full)
- `agent/internal/push/types.go` (full)
- `agent/internal/netconf/collector.go` (full)
- `agent/internal/ssh/collector.go` (full)
- `backend/app/routes/agent.py` (full)
- `backend/app/routes/github.py` (full)
- `backend/app/schemas/agent.py` (full)
- `backend/migrations/versions/20260507_010_dc_sites.py` (full)
- `backend/app/db/models.py` (DCSite class only, lines 169-193)
- `agent/docs/cab/threat-model.md` (Threat Register lines 46-160)
- `agent/docs/cab/dataflow.md` (lines 1-60)
- `backend/app/main.py` (router-include block, line 42-49)

**Pattern extraction date:** 2026-05-10

---

## PATTERN MAPPING COMPLETE

**Phase:** 11 - Firewall Integration
**Files classified:** 24 (17 NEW, 7 MODIFIED)
**Analogs found:** 24 / 24

### Coverage
- Files with exact analog: 22
- Files with role-match analog: 1 (`backend/app/tasks/firewall_prune.py` — Phase 6 taskiq workers)
- Files with no analog: 0 (the prune task has a role-match; no file is unmoored)

### Key Patterns Identified
- **Phase 10 is the canonical analog source for the entire phase.** Every Go agent file modeled on `internal/{netconf,ssh,push,config}/`; every backend file modeled on `routes/agent.py` + `schemas/agent.py` + migration `010_dc_sites.py`.
- **Three orthogonal auth flows reused verbatim:** site-token Bearer (`require_site_token` for ingest) / Clerk JWT (`require_role` for read API) / RLS team_isolation (postgres). Phase 11 wires existing primitives, never re-implements.
- **Snapshot-per-pull replace + agent-minted snapshot_id (RESEARCH Pattern 2)** is the load-bearing architectural decision that lets the three push endpoints stay independent and idempotent. ON CONFLICT DO NOTHING on `snapshot_id` is the keystone.
- **Shared parser bridges live API + offline import** (RESEARCH Pattern 1) — `checkpoint/parser.go` is a pure function called by both `live.go` and `import.go`. Mirrors Phase 10's `config-import` precedent and keeps the air-gapped path on the same code as the live path.
- **No new push-client, no new auth dep, no new RLS template, no new CAB packet.** Phase 11 EXTENDS Phase 10 along well-marked seams.

### File Created
`/Users/bhushan/Documents/Projects/Infracanvas/.planning/phases/11-firewall-integration/11-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns and exact line numbers in PLAN.md files. Each of the 14 plans suggested by RESEARCH §"Plan Decomposition Recommendation" has a 1-1 mapping to the analog excerpts above.

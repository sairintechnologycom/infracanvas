---
phase: 11-firewall-integration
plan: 10
subsystem: agent/internal/fmc
tags: [agent, collector, fmc, rest-api, wave-3, asa-02, pattern-g, pattern-h, d-08, pitfall-3, pitfall-6]
requires:
  - phase-11-plan-01-summary  # Wave 0 RED scaffold (client_test.go + 4 JSON fixtures)
  - phase-11-plan-05-summary  # push.FirewallRule / FirewallNATRule / FirewallObject wire shapes
  - phase-11-plan-07-summary  # 4th ticker + Pusher interface (downstream consumer in Plan 11-12)
provides:
  - fmc-rest-client                 # fmc.NewClient(*http.Client) + (*Client).Pull returns 3 slices + error
  - fmc-token-refresh-lifecycle     # POST /generatetoken header-read + POST /refreshtoken 1-attempt-on-401 + refreshCount cap @ 3
  - fmc-auth-sentinel               # ErrFMCAuth (errors.Is-comparable) on initial 401, 2nd 401 post-refresh, or refresh-count exhausted
  - fmc-domain-uuid-enforcement     # Pitfall 6 — empty DOMAIN_UUID after auth bails before /fmc_config calls
  - fmc-vendor-shape-types          # fmcAccessRulesResp / fmcNATRulesResp / fmcNetworkObjectsResp / fmcPolicyListResp + item types (package-internal)
  - fmc-paginated-walker            # Links.Next-first + paging.pages offset/limit fallback + 1000-page cap (T-11-10-04)
  - fmc-action-mapper               # ALLOW/TRUST/FASTPATH/MONITOR → permit ; BLOCK/BLOCK_RESET/INTERACTIVE_BLOCK* → deny
affects:
  - plan-11-12  # collectAndPushFirewall dispatcher will instantiate fmc.NewClient for protocol=fmc devices
tech-stack:
  added: []  # zero new dependencies; reuses net/http, encoding/json, crypto/tls, net/url from stdlib + push.FirewallRule shapes
  patterns:
    - "Pattern G — credential redaction: SetBasicAuth + Header.Set for X-auth-access-token / X-auth-refresh-token; no zap.Logger field on Client; structural rather than allowlist enforcement"
    - "Pattern H — collector accepts primitives (host, port, user, pass); no config.Device dependency; avoids import cycle"
    - "RESEARCH Pitfall 3 — exactly-one-refresh-attempt-on-401: doGetRaw splits to errFMCAccessExpired internal sentinel + ErrFMCAuth public sentinel"
    - "RESEARCH Pitfall 6 — DOMAIN_UUID captured from auth response headers and validated non-empty before /fmc_config paths"
    - "D-07 retry semantics owned by push.Client — collector returns errors cleanly, no per-collector retry"
    - "D-08 hybrid raw_blob — single source-of-truth json.RawMessage threaded paginatedGet accumulator → normalize functions"
    - "16 MiB body cap (io.LimitReader) + 1000-page cap — T-11-10-04 adversary-controlled-FMC mitigation"
    - "Wave 0 test signature is the contract — NewClient(*http.Client) + Pull(ctx, host, port, user, pass) mirror sibling Plan 11-08 (no zap.Logger, no siteID)"
key-files:
  created:
    - agent/internal/fmc/types.go      # 219 lines, internal FMC vendor-shape types
    - agent/internal/fmc/client.go     # 738 lines, Client + token lifecycle + Pull + normalize
  modified:
    - agent/internal/fmc/client_test.go  # 2-block test-server change (HTTP → TLS server), Rule 1 deviation
decisions:
  - "NewClient signature is NewClient(client *http.Client) *Client — 1 arg, not the plan must_haves's NewClient(http, log) form. The Wave 0 RED test in client_test.go is the locked contract (lines 75 / 124: `c := NewClient(srv.Client())`). Plan 11-08 SUMMARY established the precedent for mirroring the test signature exactly: logging belongs in the Plan 11-12 dispatcher; the collector is a pure transport. Pattern G is enforced structurally (no logger field → no possible token leak from this package) rather than via a log-field allowlist."
  - "Pull signature is Pull(ctx, host, port, user, pass) — 5 args, not the plan must_haves's 6-arg form with siteID. Wave 0 test contract on lines 77 / 126: `c.Pull(ctx, host, port, \"ro\", \"secret\")`. SiteID belongs in the Plan 11-12 dispatcher which mints snapshot_id and wraps the three returned slices in push.FirewallRulesPayload + FirewallNATPayload + FirewallObjectsPayload. Mirrors ASA REST (Plan 11-08) precedent."
  - "client_test.go switched from httptest.NewServer to httptest.NewTLSServer (2-block change, Rule 1 deviation). Production FMC is HTTPS-only and the collector's TLS-validating http.Client (InsecureSkipVerify=false per T-11-10-03 baseline) refused plain HTTP. NewTLSServer's self-signed cert is trusted by srv.Client() via the test cert pool, so the test exercises real TLS validation. Sibling Plan 11-08 made the identical change for ASA REST tests."
  - "Pagination walker has TWO modes: (a) follow Links.Next URL when present (preferred — FMC bakes offset+limit into the next URL), (b) fall back to offset/limit walking driven by paging.pages when FMC omits links.next. The Wave 0 RED fixture exercises mode (b) explicitly (TestClient_PaginatedAccessRules rewrites paging.pages from 1 → 2 with no next link). Real-world FMC 7.x behavior matches the fixture — some endpoints omit links.next on the first page even when pages > 1. Both modes share a 1000-page hard cap as T-11-10-04 DoS guard against an adversarial FMC pointing next at itself or reporting unbounded pages."
  - "Pagination URL rewriting uses a withOffset helper that preserves the rest of the query string verbatim (notably expanded=true) and replaces only the offset= parameter. limit= is added if absent. Same approach scales to all three resource paths (accessrules + manualnatrules + object/networks) without per-endpoint pagination logic."
  - "doGetRaw splits into doGetRawOnce + doGetRaw to express the exactly-one-refresh-attempt semantic cleanly. Internal sentinel errFMCAccessExpired signals 'we saw a 401 on a content GET' (not on auth itself); doGetRaw owns the refresh+retry-once decision and converts a persistent 401 into the public ErrFMCAuth sentinel. The split avoids the more common nested-if-conditional approach that obscures Pitfall 3's strict semantics."
  - "buildURL re-roots absolute Links.Next URLs against the host+port the agent was configured to dial. FMC self/next URLs reference the FMC's own configured hostname (which may not match the inbound host — operators often expose FMC through a load-balancer with a different SAN). Re-rooting keeps every request going through the dial path the operator authorized; otherwise next-link following would silently bypass operator-configured routing."
  - "Action mapping covers FMC's full action vocabulary: ALLOW/TRUST/FASTPATH → 'permit', BLOCK and four BLOCK_* variants → 'deny', MONITOR → 'permit' (monitored traffic passes; the monitor side effect is FMC-internal and Phase 12 path computation ignores it). Unknown values lowercase-passthrough for graceful degradation if Cisco adds new action types in future FMC releases."
  - "normalizeAccessRule emits Position=0 on every rule because FMC orders by metadata.ruleIndex which the normalized push.FirewallRule.Position field doesn't accommodate directly; the original ruleIndex is preserved verbatim in raw_blob. Phase 12 path computation may read rule order from raw_blob via JSONB path lookup if/when ordering matters."
  - "normalizeNetworkObject defaults to kind='network' (not 'group') when the FMC Type is neither 'Host' nor 'Network' — Phase 11's testdata only exercises Host/Network so the fallback path is conservatism for future fixture additions. D-09's 'group' kind is reserved for explicit object-group references which /object/networks does not emit (groups live at /object/networkgroups, deferred)."
  - "First-policy-only access + NAT policy selection (Pull picks accessPolicies.Items[0].ID and natPolicies.Items[0].ID). CONTEXT Discretion explicitly authorized this; operator-driven selection deferred. If FMC has zero policies the rule list is legitimately empty — Pull returns nil-slice + nil-error so the dispatcher pushes an empty snapshot rather than failing."
  - "Pull pre-allocates rules / nats / objs as nil-slice and grows via append. Unlike ASA REST (Plan 11-08) which uses make([]T, 0, len(items)) per normalize loop, FMC paginates so the total count is not known upfront. append's growth-doubling is the idiomatic choice when count is unknown."
metrics:
  duration_minutes: 10
  tasks_completed: 2
  files_created: 2
  files_modified: 1
  total_files: 3
  completed_date: "2026-05-15"
---

# Phase 11 Plan 10: FMC REST Client with Token Refresh Summary

Cisco FMC REST API collector (REQ ASA-02) lands as the Wave-3 sibling to ASA REST (Plan 11-08) and ASA SSH (Plan 11-09). `fmc.NewClient(*http.Client) *Client` + `(*Client).Pull(ctx, host, port, user, pass) ([]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error)` acquires a per-pull token via `POST /api/fmc_platform/v1/auth/generatetoken` (reading X-auth-access-token + X-auth-refresh-token + DOMAIN_UUID from the response HEADERS, not the body — Pitfall 3), paginates the first access policy's access rules + the first NAT policy's manual NAT rules + the domain's network objects, and normalizes each item to the push wire shapes from Plan 11-05. The token lifecycle is the most complex of the four vendors: on a 401 mid-pull the client attempts exactly ONE refresh via `POST /refreshtoken`; a second 401 OR a refresh failure surfaces the new `ErrFMCAuth` sentinel (non-retryable, recognized by push.Client's D-07 retry logic). After 3 refreshes the refresh-token is considered exhausted (Pitfall 3) and the next ticker tick acquires a fresh token from scratch. Plan 11-01's Wave 0 RED tests (TestClient_TokenRefresh + TestClient_PaginatedAccessRules) now both GREEN.

## What Was Built

### Task 1 — Internal FMC vendor-shape types in `agent/internal/fmc/types.go` (commit `67ce13d`)

`agent/internal/fmc/types.go` (NEW, 219 lines) — 15 internal types arranged in four groups:

**Token state (1 type):**

| Type           | Purpose                                                                     |
| -------------- | --------------------------------------------------------------------------- |
| `fmcTokenInfo` | Per-pull token state: accessToken, refreshToken, domainUUID, refreshCount (cap @ 3 per Pitfall 3). Stack-local in `Pull`; never persisted between pulls. |

**Paginated response envelopes (4 types):**

| Type                    | Maps to                                                  |
| ----------------------- | -------------------------------------------------------- |
| `fmcAccessRulesResp`    | `/policy/accesspolicies/{pid}/accessrules` envelope     |
| `fmcNATRulesResp`       | `/policy/ftdnatpolicies/{pid}/manualnatrules` envelope  |
| `fmcNetworkObjectsResp` | `/object/networks` envelope                              |
| `fmcPolicyListResp`     | `/policy/accesspolicies` and `/policy/ftdnatpolicies` envelopes (Items=[]fmcPolicyRef) |

**Envelope helpers (3 types):**

| Type           | Purpose                                                       |
| -------------- | ------------------------------------------------------------- |
| `fmcLinks`     | self + optional next (next absent on last page)               |
| `fmcPaging`    | offset / limit / count / pages (pages > 1 enables walker fallback) |
| `fmcPolicyRef` | id + name + type (only id is read for rule pagination URL)    |

**Per-resource item types (7 types):**

| Type                | Maps to                                                                  |
| ------------------- | ------------------------------------------------------------------------ |
| `fmcAccessRule`     | one access rule (id, name, action, sourceZones, sourceNetworks, destinationPorts, …, `Raw json.RawMessage \`json:"-"\``) |
| `fmcNATRule`        | one manual NAT rule (originalSource, translatedSource, sourceInterface, …, Raw) |
| `fmcNetworkObject`  | one host/network object (id, name, type, value, Raw)                    |
| `fmcZoneList`       | security-zone reference list (Objects only)                              |
| `fmcNetworkRefList` | network/host reference list (Objects + Literals)                         |
| `fmcObjectRef`      | named reference (id + name + type)                                       |
| `fmcLiteral`        | inline literal (value + type)                                            |
| `fmcPortList`       | port reference list (Objects + Literals)                                 |
| `fmcPortLiteral`    | inline port literal (port + protocol-number + type)                      |

All package-internal. `Raw json.RawMessage \`json:"-"\`` on the three item types is populated manually during normalization in client.go (D-08 hybrid raw_blob — the bytes flow as a single source-of-truth from `paginatedGet`'s accumulator into the typed shape AND the push payload's raw_blob field, with no separate re-marshal).

### Task 2 — `Client` + token lifecycle + `Pull` in `agent/internal/fmc/client.go` (commit `fdaa691`)

`agent/internal/fmc/client.go` (NEW, 738 lines) — the production FMC collector. Structurally:

| Section                     | Lines | Purpose                                                                 |
| --------------------------- | ----- | ----------------------------------------------------------------------- |
| `ErrFMCAuth` sentinel       | 1     | `errors.Is`-comparable non-retryable auth failure                       |
| Constants                   | 4     | `defaultHTTPTimeout=10s`, `defaultPort=443`, `maxRefreshAttempts=3`, `maxResponseBytes=16MiB` |
| `Client` struct + `NewClient` | ~30 | `http *http.Client` + `token *fmcTokenInfo`; production default is TLS-validating |
| `Pull` orchestration        | ~95  | Token acquire → DOMAIN_UUID enforce → access policy + paginate rules → NAT policy + paginate NAT → paginate objects |
| Token lifecycle             | ~75  | `acquireToken` (read headers, not body) + `refreshToken` (1-attempt with cap @ 3) |
| Authenticated GET           | ~95  | `doGet` / `doGetRaw` / `doGetRawOnce` split exposing the exactly-one-refresh semantic |
| Pagination                  | ~80  | `paginatedGet` (Links.Next-first, paging.pages fallback) + `withOffset` query rewriter |
| Normalize                   | ~110 | `normalizeAccessRule`, `normalizeNATRule`, `normalizeNetworkObject` to push wire shapes |
| Helpers                     | ~50  | `mapFMCAction`, `firstZoneName`, `firstNetworkValue`, `firstPortValue`, `firstPortProtocol`, `baseURL`, `buildURL` |

**Token lifecycle deep dive (Pitfall 3 strict semantics):**

```
acquireToken:    POST /generatetoken
                 → read X-auth-access-token + X-auth-refresh-token + DOMAIN_UUID from HEADERS
                 → 401 returns ErrFMCAuth
                 → empty DOMAIN_UUID returns wrapped fmt.Errorf (Pitfall 6)

doGetRaw:        doGetRawOnce (first attempt)
                 → on 401 → refreshToken (1 attempt)
                          → on success → doGetRawOnce (second attempt, isRetry=true)
                                       → on 401 again → ErrFMCAuth
                                       → on 2xx → success
                          → on failure → ErrFMCAuth (refresh exhausted OR network error)

refreshToken:    if refreshCount >= 3 → ErrFMCAuth (Pitfall 3 cap)
                 POST /refreshtoken with X-auth-access-token + X-auth-refresh-token
                 → 401 returns ErrFMCAuth
                 → 2xx updates accessToken from response header; refreshCount++
```

**Pagination walker (T-11-10-04 hardening):**

```
paginatedGet(startPath, accumulator):
    path = startPath
    for page in 0..1000:
        body = doGetRaw(path)              # auto-handles refresh-on-401
        decode envelope (Links + Paging + raw Items)
        accumulator(each raw item)         # caller fills typed shape AND raw_blob
        if Links.Next:   path = Links.Next;          continue   # preferred mode
        if Paging.Pages > pagesSeen:
            path = withOffset(startPath, pagesSeen * limit, limit)
            continue                                            # fallback mode
        return nil
    return error "pagination exceeded 1000 pages"               # DoS guard
```

The fallback mode is what makes `TestClient_PaginatedAccessRules` GREEN — the Wave 0 fixture rewrites `paging.pages` from 1 to 2 without adding a `next` link, mirroring real-world FMC 7.x behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] client_test.go test-server scheme mismatch**
- **Found during:** Task 2 verification (`go test -race ./internal/fmc/...`)
- **Issue:** Wave 0 RED test used `httptest.NewServer` (plain HTTP) but the production FMC client builds `https://...` URLs and the default http.Client refuses plain-HTTP responses (`"http: server gave HTTP response to HTTPS client"`). Production FMC is HTTPS-only and `InsecureSkipVerify` is intentionally `false` per the T-11-10-03 acceptance posture, so weakening the client to fit the test would be the wrong direction.
- **Fix:** Switched both test bodies (TestClient_TokenRefresh + TestClient_PaginatedAccessRules) from `httptest.NewServer(mux)` to `httptest.NewTLSServer(mux)`. `srv.Client()` automatically carries the self-signed cert in its TLS pool, so the production TLS-validating http.Client trusts the test server without InsecureSkipVerify. Two added comments cite the Plan 11-08 SUMMARY precedent (sibling Rule 1 deviation made identical change for ASA REST tests).
- **Files modified:** `agent/internal/fmc/client_test.go`
- **Commit:** `fdaa691`

### Signature Deviations from Plan must_haves (documented, not auto-fixed)

The plan's `must_haves.truths` describes `fmc.NewClient(http, log) returns *Client with token state` and `Pull(ctx, host, port, user, pass, siteID) returns three slices + error`. The Wave 0 RED test fixed by Plan 11-01 locked a different contract:

| Method     | Plan must_haves      | Wave 0 test (locked contract)      | Decision                                                                                                                                                                                  |
| ---------- | -------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `NewClient` | `(*http.Client, *zap.Logger)` | `(*http.Client)` only          | Match test. Pattern G is enforced structurally (no logger field → no token leak from this package). Logging belongs in Plan 11-12 dispatcher. Sibling Plan 11-08 made the identical decision. |
| `Pull`     | 6 args incl. `siteID` | 5 args (no siteID)                | Match test. SiteID belongs in dispatcher which wraps the returned slices into push.FirewallRulesPayload. Sibling Plan 11-08 made the identical decision.                                |

Both deviations follow the Plan 11-08 SUMMARY's stated precedent that "the test is the contract" when must_haves and Wave 0 tests disagree. Pattern G is preserved (no log surface for tokens to leak from); Pattern H is preserved (primitives-only signature, no config.Device).

### Auth gates

None — no live FMC was contacted; all tests run hermetically against httptest.

## Verification

```
$ go vet ./internal/fmc/...
(clean)

$ go test -race ./internal/fmc/...
ok  	github.com/infracanvas/infracanvas/agent/internal/fmc	2.247s

$ go test -race -run TestClient_TokenRefresh ./internal/fmc/...
ok  	github.com/infracanvas/infracanvas/agent/internal/fmc	2.092s

$ go test -race -run TestClient_PaginatedAccessRules ./internal/fmc/...
ok  	github.com/infracanvas/infracanvas/agent/internal/fmc	1.349s
```

Wave 0 fmc RED tests GREEN. `go vet` clean. `-race` clean. ASA-02 satisfied.

### Acceptance Criteria Check

**Task 1 (types.go):**
- ✓ File exists
- ✓ `package fmc` count = 1
- ✓ 6 envelope types (fmcAccessRule, fmcNATRule, fmcNetworkObject, fmcAccessRulesResp, fmcNATRulesResp, fmcNetworkObjectsResp)
- ✓ 4 support types (fmcTokenInfo, fmcPolicyRef, fmcLinks, fmcPaging)
- ✓ 3 `json:"-"` tags (Raw on AccessRule + NATRule + NetworkObject)
- ✓ FMC camelCase tags (sourceNetworks, destinationNetworks, originalSource, translatedSource: 4 verified)
- ✓ Builds standalone

**Task 2 (client.go):**
- ✓ File exists
- ✓ `func NewClient` count = 1
- ✓ `func (c *Client) Pull` count = 1
- ✓ Lifecycle methods (acquireToken, refreshToken, doGet, paginatedGet + supporting doGetRaw + doGetRawOnce + buildURL + withOffset) = 6 matched + helpers
- ✓ Both /generatetoken + /refreshtoken paths present (2)
- ✓ X-auth-access-token / X-auth-refresh-token / DOMAIN_UUID header refs (21)
- ✓ `/api/fmc_config/v1/domain` references (3 lines mentioning fmc_config; 5 endpoint constructions when counting `domainBase + ` literal concatenations)
- ✓ ErrFMCAuth references (17 — declaration + decision points)
- ✓ refreshCount references (3 — cap check + increment + reset on acquire)
- ✓ Zero zap.String pattern-G violations (grep returns 0)
- ✓ TestClient_TokenRefresh exits 0
- ✓ TestClient_PaginatedAccessRules exits 0
- ✓ All FMC tests GREEN with -race

## Self-Check: PASSED

**Files claimed:**
- `agent/internal/fmc/types.go` — FOUND (219 lines)
- `agent/internal/fmc/client.go` — FOUND (738 lines)
- `agent/internal/fmc/client_test.go` — FOUND (modified — 2 NewTLSServer switches)

**Commits claimed:**
- `67ce13d` (Task 1: types.go) — FOUND in `git log --oneline | head -5`
- `fdaa691` (Task 2: client.go + test fix) — FOUND in `git log --oneline | head -5`

## Threat Model Compliance

All STRIDE threats from `<threat_model>` mitigated as planned:

| Threat ID    | Mitigation in code                                                                                                                                |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-11-10-01   | Pattern G structural: Client has no `*zap.Logger` field; tokens flow only through `req.Header.Set` / `resp.Header.Get`; verified via `grep -cE 'zap\.String\("(user\|pass\|password\|accessToken\|refreshToken)"' = 0` |
| T-11-10-02   | `maxRefreshAttempts = 3` constant + refreshCount check at top of `refreshToken`; ErrFMCAuth bails out and forces re-acquire on next tick         |
| T-11-10-03   | TLS-validating default http.Client with `InsecureSkipVerify: false`; same posture as ASA REST Plan 11-08                                          |
| T-11-10-04   | Defensive index checks in `firstZoneName` / `firstNetworkValue` / `firstPortValue` / `firstPortProtocol`; `io.LimitReader(maxResponseBytes)`; `maxPages = 1000` cap in paginatedGet; collector-level error wraps via `fmt.Errorf` |
| T-11-10-05   | `DOMAIN_UUID` populated only from auth response header; collector refuses to proceed if empty; no caller-overridable domain parameter on Pull    |

No new threat flags beyond the plan's `<threat_model>`.

## Forward Linkage

- **Plan 11-12** (dispatcher) will instantiate `fmc.NewClient(nil)` for `protocol: fmc` devices, call `Pull(ctx, dev.Host, dev.Port, dev.Username, dev.Password)`, mint snapshot_id, and push via `push.Client.PushFirewallRules` / `PushFirewallNAT` / `PushFirewallObjects` with `Vendor: "cisco-fmc"` and `Source: "fmc"`.
- **Plan 11-13** (CAB packet) lifts the FMC token-lifecycle + DOMAIN_UUID requirement into `agent/docs/cab/data-flow.md` and the credential-storage section of `agent/docs/cab/threat-model.md`.
- **Phase 12** (path computation) reads the FMC-emitted `push.FirewallRule.{Action, SrcCIDR, DstCIDR, Protocol, Ports}` columns for policy-mismatch detection; `push.FirewallNATRule.{InterfaceIn, InterfaceOut, SrcTranslation, DstTranslation}` for NAT_ASYMMETRY classification.

## Stays Inside the Worktree

This plan stays strictly inside `agent/internal/fmc/`. Sibling Wave 3 plans (11-09 ASA SSH at `agent/internal/asa/ssh.go` and 11-11 Checkpoint at `agent/internal/checkpoint/`) are untouched. No modifications to STATE.md, ROADMAP.md, or any non-fmc file — the orchestrator owns those writes after the wave completes.

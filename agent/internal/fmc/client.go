// client.go — Cisco FMC (Firepower Management Center) REST API collector
// (REQ ASA-02).
//
// Pulls access rules + manual-NAT rules + network objects from a Cisco FMC
// via the v1 REST API, normalizes the vendor-shape JSON into push.FirewallRule
// / push.FirewallNATRule / push.FirewallObject (D-08 hybrid: normalized
// columns + raw_blob), and returns three slices to the caller. The caller
// (collectAndPushFirewall in main.go, wired by Plan 11-12) is responsible
// for minting the snapshot_id and pushing the slices via push.Client.
//
// Token lifecycle (RESEARCH Pitfall 3 — the most complex of the four
// vendors): a single Pull invocation calls POST /generatetoken, reads the
// X-auth-access-token + X-auth-refresh-token + DOMAIN_UUID headers (not the
// body), caches them on the stack for the duration of the pull, and uses
// the access token as the X-auth-access-token header on subsequent GETs.
// On 401 mid-pull the collector attempts exactly ONE refresh via
// POST /refreshtoken; a second 401 OR a refresh failure surfaces as
// ErrFMCAuth (non-retryable). The refresh count is capped at 3 per FMC's
// documented refresh-token lifetime — after that the caller must re-acquire
// from scratch via /generatetoken; client.go returns ErrFMCAuth to force
// the dispatcher onto the next ticker tick rather than spinning.
//
// DOMAIN_UUID requirement (RESEARCH Pitfall 6): every /api/fmc_config path
// MUST include the DOMAIN_UUID returned from the auth call. The collector
// refuses to proceed if DOMAIN_UUID is missing in the auth response — a
// common misconfiguration symptom where the operator's credentials lack
// domain mapping.
//
// Pagination: FMC returns a `links.next` URL on paginated responses. The
// collector follows `Links.Next` until empty. Each `expanded=true&limit=100`
// pull bounds individual page size.
//
// Caller passes primitives (host, port, user, pass) rather than a
// config.Device — Pattern H, avoids the internal/config ↔ internal/fmc
// import cycle. Pattern H precedent: agent/internal/asa/rest.go (Plan 11-08).
//
// NO retry inside the collector — D-07 retry is owned by push.Client
// (Plan 11-05). Collector errors return cleanly; the next ticker tick is
// the retry.
//
// Pattern G credential redaction: this collector NEVER logs username,
// password, X-auth-access-token, or X-auth-refresh-token. Basic-auth is
// set via req.SetBasicAuth (which the net/http stack does not log); the
// access token is used only as an outbound header value. The collector
// carries no logger — logging belongs in the Plan 11-12 dispatcher which
// sees only host + slice lengths + errors. Pattern G is therefore enforced
// structurally rather than via a log-field allowlist.
package fmc

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/infracanvas/infracanvas/agent/internal/push"
)

// ErrFMCAuth is returned from Pull (and surfaced from refreshToken / doGet)
// when FMC rejects the caller's credentials. The error is sentinel-comparable
// via errors.Is so the dispatcher (Plan 11-12) and the push client can
// recognize it as non-retryable. T-11-10-01 / T-11-10-02.
var ErrFMCAuth = errors.New("fmc: authentication failed (non-retryable)")

// defaultHTTPTimeout matches the ASA REST collector (Plan 11-08) — 10 s is
// the Phase 10 management-plane dial ceiling. FMC pulls can span multiple
// paginated calls; the per-request timeout still bounds each one.
const defaultHTTPTimeout = 10 * time.Second

// defaultPort is the FMC HTTPS management port.
const defaultPort = 443

// maxRefreshAttempts caps refresh-token reuse (RESEARCH Pitfall 3 — FMC
// documents up to 3 refreshes per /generatetoken call; after that the
// refresh token is rejected and the caller must re-authenticate from
// scratch). Bailing with ErrFMCAuth lets the next ticker tick acquire a
// fresh token rather than spinning the collector.
const maxRefreshAttempts = 3

// maxResponseBytes caps the JSON body read on every GET. 16 MiB is large
// enough for the biggest plausible per-page rule envelope and small enough
// to bound memory if the FMC misbehaves. T-11-10-04 mitigation against an
// adversary-controlled FMC.
const maxResponseBytes = 16 * 1024 * 1024

// Client pulls firewall state from a Cisco FMC via the v1 REST API.
// The http.Client field is the test seam: tests inject an httptest.Server's
// client; production passes nil to NewClient to get a TLS-validating client
// with the default 10 s timeout.
//
// token is per-pull state; it is reset on every Pull invocation and never
// persists between pulls. Pull is not safe to call concurrently on a single
// Client instance — instantiate a fresh Client per goroutine if parallelism
// is needed (Plan 11-12 dispatcher creates one per device).
type Client struct {
	http  *http.Client
	token *fmcTokenInfo
}

// NewClient returns a Client. Pass nil to get a production http.Client with
// TLS validation enabled and a 10 s timeout. Pass a httptest.Server.Client()
// (or any other *http.Client) for tests.
//
// InsecureSkipVerify is intentionally false in the production default —
// operator-managed TLS certificates on the FMC management interface are
// the Phase 11 security baseline (T-11-10-03 acceptance posture). Plan
// 11-13 / CAB documents the future operator knob to flip this.
//
// Signature note: NewClient takes a single *http.Client argument matching
// the Wave 0 RED test contract (agent/internal/fmc/client_test.go line 75 /
// 124: `c := NewClient(srv.Client())`). The plan's must_haves spec lists a
// second *zap.Logger parameter, but the test is the locked contract — the
// Plan 11-08 sibling SUMMARY established the precedent of mirroring the
// test signature exactly. Logging belongs in the Plan 11-12 dispatcher;
// the collector is a pure transport that returns errors for the caller to
// log. Pattern G credential redaction is enforced structurally (no token
// is ever written anywhere observable from this package).
func NewClient(client *http.Client) *Client {
	if client == nil {
		client = &http.Client{
			Timeout: defaultHTTPTimeout,
			Transport: &http.Transport{
				TLSClientConfig: &tls.Config{
					MinVersion:         tls.VersionTLS12,
					InsecureSkipVerify: false,
				},
			},
		}
	}
	return &Client{http: client}
}

// Pull acquires a token, lists the first access policy and first NAT policy,
// paginates the access rules + manual NAT rules + network objects under
// them, normalizes each item to the push wire shape, and returns three
// slices. The caller mints the snapshot_id and pushes via push.Client.
//
// Signature note: Pull takes (ctx, host, port, user, pass) — 5 args, not
// the plan's 6-arg form with siteID. The Wave 0 RED test in client_test.go
// is the locked contract (lines 77 / 126: `c.Pull(ctx, host, port, "ro", "secret")`)
// and Plan 11-08's SUMMARY established the precedent — siteID belongs in
// the dispatcher (Plan 11-12), not the collector.
//
// First-policy-only is intentional: FMC operators typically maintain one
// access policy and one NAT policy per managed FTD (D-15). Operator-driven
// policy selection is deferred (CONTEXT.md Discretion).
//
// Errors are wrapped per the Phase 10 convention:
//
//	"fmc: <stage> %s: %w"
//
// On any auth failure (initial 401, second-401-after-refresh, refresh-count
// exhausted) Pull returns ErrFMCAuth so errors.Is(err, ErrFMCAuth) is true.
func (c *Client) Pull(
	ctx context.Context,
	host string,
	port int,
	user, pass string,
) ([]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error) {
	if port == 0 {
		port = defaultPort
	}

	if err := c.acquireToken(ctx, host, port, user, pass); err != nil {
		return nil, nil, nil, err
	}

	// RESEARCH Pitfall 6: collector MUST NOT proceed without DOMAIN_UUID.
	// Empty DOMAIN_UUID means the auth response omitted the header (a real
	// FMC misconfig) — bail rather than build invalid /fmc_config paths.
	if c.token == nil || c.token.domainUUID == "" {
		return nil, nil, nil, fmt.Errorf("fmc: missing DOMAIN_UUID in auth response from %s", host)
	}

	domainBase := "/api/fmc_config/v1/domain/" + c.token.domainUUID

	// ── Access rules ─────────────────────────────────────────────────────
	// Phase 11 picks the first access policy (CONTEXT Discretion). If the
	// FMC has zero policies the rule list is legitimately empty — return
	// empty slices without an error.
	var rules []push.FirewallRule
	var accessPolicies fmcPolicyListResp
	if err := c.doGet(ctx, host, port, domainBase+"/policy/accesspolicies", &accessPolicies); err != nil {
		return nil, nil, nil, fmt.Errorf("fmc: list accesspolicies %s: %w", host, err)
	}
	if len(accessPolicies.Items) > 0 {
		policyID := accessPolicies.Items[0].ID
		path := domainBase + "/policy/accesspolicies/" + policyID + "/accessrules?expanded=true&limit=100"
		err := c.paginatedGet(ctx, host, port, path, func(raw json.RawMessage) error {
			var item fmcAccessRule
			if err := json.Unmarshal(raw, &item); err != nil {
				return fmt.Errorf("decode access rule: %w", err)
			}
			item.Raw = raw
			rules = append(rules, normalizeAccessRule(item))
			return nil
		})
		if err != nil {
			return nil, nil, nil, fmt.Errorf("fmc: paginate accessrules %s: %w", host, err)
		}
	}

	// ── NAT rules ────────────────────────────────────────────────────────
	var nats []push.FirewallNATRule
	var natPolicies fmcPolicyListResp
	if err := c.doGet(ctx, host, port, domainBase+"/policy/ftdnatpolicies", &natPolicies); err != nil {
		return nil, nil, nil, fmt.Errorf("fmc: list ftdnatpolicies %s: %w", host, err)
	}
	if len(natPolicies.Items) > 0 {
		policyID := natPolicies.Items[0].ID
		path := domainBase + "/policy/ftdnatpolicies/" + policyID + "/manualnatrules?expanded=true&limit=100"
		err := c.paginatedGet(ctx, host, port, path, func(raw json.RawMessage) error {
			var item fmcNATRule
			if err := json.Unmarshal(raw, &item); err != nil {
				return fmt.Errorf("decode nat rule: %w", err)
			}
			item.Raw = raw
			nats = append(nats, normalizeNATRule(item))
			return nil
		})
		if err != nil {
			return nil, nil, nil, fmt.Errorf("fmc: paginate manualnatrules %s: %w", host, err)
		}
	}

	// ── Network objects ──────────────────────────────────────────────────
	var objs []push.FirewallObject
	objPath := domainBase + "/object/networks?expanded=true&limit=100"
	err := c.paginatedGet(ctx, host, port, objPath, func(raw json.RawMessage) error {
		var item fmcNetworkObject
		if err := json.Unmarshal(raw, &item); err != nil {
			return fmt.Errorf("decode network object: %w", err)
		}
		item.Raw = raw
		obj, err := normalizeNetworkObject(item)
		if err != nil {
			return err
		}
		objs = append(objs, obj)
		return nil
	})
	if err != nil {
		return nil, nil, nil, fmt.Errorf("fmc: paginate object/networks %s: %w", host, err)
	}

	return rules, nats, objs, nil
}

// ─── Token lifecycle ──────────────────────────────────────────────────────

// acquireToken POSTs basic-auth credentials to /generatetoken and reads
// X-auth-access-token, X-auth-refresh-token, and DOMAIN_UUID from the
// response HEADERS (not the body — RESEARCH Pitfall 3). 401 returns
// ErrFMCAuth (non-retryable); other non-2xx statuses return a wrapped
// error.
//
// Pattern G: user/pass are passed only via req.SetBasicAuth — they are
// never logged, never embedded in the URL, never stringified.
func (c *Client) acquireToken(ctx context.Context, host string, port int, user, pass string) error {
	req, err := http.NewRequestWithContext(
		ctx, http.MethodPost,
		baseURL(host, port)+"/api/fmc_platform/v1/auth/generatetoken",
		nil,
	)
	if err != nil {
		return fmt.Errorf("fmc: token build %s: %w", host, err)
	}
	req.SetBasicAuth(user, pass)
	req.Header.Set("Accept", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("fmc: token %s: %w", host, err)
	}
	defer func() { _ = resp.Body.Close() }()
	// Drain a bounded prefix so the connection can be reused. Bounded read
	// defends against a hostile server streaming gigabytes into a 401 body
	// (T-11-10-04 — adversary-controlled FMC hardening).
	_, _ = io.CopyN(io.Discard, resp.Body, 4096)

	if resp.StatusCode == http.StatusUnauthorized {
		return ErrFMCAuth
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("fmc: token %s: status %d", host, resp.StatusCode)
	}

	access := resp.Header.Get("X-auth-access-token")
	refresh := resp.Header.Get("X-auth-refresh-token")
	domain := resp.Header.Get("DOMAIN_UUID")
	if access == "" {
		return fmt.Errorf("fmc: token %s: missing X-auth-access-token header", host)
	}
	c.token = &fmcTokenInfo{
		accessToken:  access,
		refreshToken: refresh,
		domainUUID:   domain,
		refreshCount: 0,
	}
	return nil
}

// refreshToken POSTs the current refresh+access token pair to /refreshtoken
// and updates c.token.accessToken from the response X-auth-access-token
// header on success. After maxRefreshAttempts (3) the refresh token is
// considered exhausted per RESEARCH Pitfall 3 and ErrFMCAuth is returned —
// the dispatcher's next ticker tick acquires a fresh token from scratch.
//
// Pattern G: refresh/access token values flow ONLY through req.Header.Set
// outbound and resp.Header.Get inbound. They are never logged, never
// stringified, never embedded in the URL.
func (c *Client) refreshToken(ctx context.Context, host string, port int) error {
	if c.token == nil {
		return ErrFMCAuth
	}
	if c.token.refreshCount >= maxRefreshAttempts {
		return ErrFMCAuth
	}

	req, err := http.NewRequestWithContext(
		ctx, http.MethodPost,
		baseURL(host, port)+"/api/fmc_platform/v1/auth/refreshtoken",
		nil,
	)
	if err != nil {
		return fmt.Errorf("fmc: refresh build %s: %w", host, err)
	}
	req.Header.Set("X-auth-access-token", c.token.accessToken)
	req.Header.Set("X-auth-refresh-token", c.token.refreshToken)
	req.Header.Set("Accept", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("fmc: refresh %s: %w", host, err)
	}
	defer func() { _ = resp.Body.Close() }()
	_, _ = io.CopyN(io.Discard, resp.Body, 4096)

	if resp.StatusCode == http.StatusUnauthorized {
		return ErrFMCAuth
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("fmc: refresh %s: status %d", host, resp.StatusCode)
	}

	newAccess := resp.Header.Get("X-auth-access-token")
	if newAccess == "" {
		return fmt.Errorf("fmc: refresh %s: missing X-auth-access-token header", host)
	}
	c.token.accessToken = newAccess
	c.token.refreshCount++
	return nil
}

// ─── Authenticated GET ────────────────────────────────────────────────────

// doGet issues a GET with the X-auth-access-token header and unmarshals the
// JSON body into out. On 401 it calls refreshToken once and retries exactly
// ONCE; a second 401 OR a refresh failure returns ErrFMCAuth (RESEARCH
// Pitfall 3 strict semantics — T-11-10-02 DoS mitigation: no infinite refresh
// loop).
//
// The response body read is bounded to 16 MiB (T-11-10-04).
func (c *Client) doGet(ctx context.Context, host string, port int, path string, out interface{}) error {
	body, err := c.doGetRaw(ctx, host, port, path)
	if err != nil {
		return err
	}
	if err := json.Unmarshal(body, out); err != nil {
		return fmt.Errorf("unmarshal %s: %w", path, err)
	}
	return nil
}

// doGetRaw is the underlying GET that returns the unparsed body bytes. Split
// out so paginatedGet can extract the items array as []json.RawMessage
// without first having to know the per-resource Item type.
func (c *Client) doGetRaw(ctx context.Context, host string, port int, path string) ([]byte, error) {
	body, err := c.doGetRawOnce(ctx, host, port, path, false)
	if err == nil {
		return body, nil
	}
	if !errors.Is(err, errFMCAccessExpired) {
		return nil, err
	}
	// 401 — try exactly ONE refresh, then exactly ONE retry. Pitfall 3.
	if rerr := c.refreshToken(ctx, host, port); rerr != nil {
		return nil, rerr // ErrFMCAuth or wrapped network error
	}
	body, err = c.doGetRawOnce(ctx, host, port, path, true)
	if err == nil {
		return body, nil
	}
	if errors.Is(err, errFMCAccessExpired) {
		// Second 401 after refresh — non-retryable.
		return nil, ErrFMCAuth
	}
	return nil, err
}

// errFMCAccessExpired is an internal sentinel signaling a 401 on a content
// GET (as opposed to on the auth endpoint). It is NEVER returned from
// exported methods — doGetRaw converts a persistent 401-after-refresh into
// ErrFMCAuth so the public surface has exactly one auth-failure sentinel.
var errFMCAccessExpired = errors.New("fmc: access token expired (internal)")

// doGetRawOnce performs a single GET attempt with the current access token.
// 401 is signaled via errFMCAccessExpired; the caller (doGetRaw) is
// responsible for the refresh+retry decision.
func (c *Client) doGetRawOnce(ctx context.Context, host string, port int, path string, isRetry bool) ([]byte, error) {
	// path may be an absolute URL (Links.Next from a previous page) or a
	// path-only string. url.Parse handles both; we rebuild a clean URL
	// against the configured host:port either way (the FMC self/next URLs
	// reference the operator-visible hostname, which may not match the
	// inbound host the agent dials — same host, different cert SAN cases
	// would otherwise break here).
	target, err := buildURL(host, port, path)
	if err != nil {
		return nil, fmt.Errorf("build url %s: %w", path, err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, target, nil)
	if err != nil {
		return nil, fmt.Errorf("build request %s: %w", path, err)
	}
	if c.token != nil {
		req.Header.Set("X-auth-access-token", c.token.accessToken)
	}
	req.Header.Set("Accept", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, fmt.Errorf("get %s: %w", path, err)
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode == http.StatusUnauthorized {
		// Drain so the connection can be reused before the retry.
		_, _ = io.CopyN(io.Discard, resp.Body, 4096)
		if isRetry {
			// Caller will convert this into ErrFMCAuth.
			return nil, errFMCAccessExpired
		}
		return nil, errFMCAccessExpired
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		_, _ = io.CopyN(io.Discard, resp.Body, 4096)
		return nil, fmt.Errorf("get %s: status %d", path, resp.StatusCode)
	}

	body, err := io.ReadAll(io.LimitReader(resp.Body, maxResponseBytes))
	if err != nil {
		return nil, fmt.Errorf("read body %s: %w", path, err)
	}
	return body, nil
}

// ─── Pagination ───────────────────────────────────────────────────────────

// paginatedGet walks an FMC paginated collection, invoking accumulator once
// per item. Iteration follows the response `links.next` URL when present,
// and falls back to offset/limit walking (driven by `paging.pages`) when
// the FMC omits a next link but reports more than one page. A defensive
// max-pages cap (1000) prevents an adversarial FMC from indicating an
// infinite page count (T-11-10-04).
//
// The accumulator receives the raw item JSON so client.go can both decode
// it into the typed shape AND preserve it for the D-08 raw_blob field via
// a single source of truth.
func (c *Client) paginatedGet(
	ctx context.Context,
	host string,
	port int,
	startPath string,
	accumulator func(json.RawMessage) error,
) error {
	const maxPages = 1000
	path := startPath
	pagesSeen := 0
	for page := 0; page < maxPages; page++ {
		body, err := c.doGetRaw(ctx, host, port, path)
		if err != nil {
			return err
		}
		// Decode only the envelope shape we need — links + paging + raw items.
		var env struct {
			Links  fmcLinks          `json:"links"`
			Paging fmcPaging         `json:"paging"`
			Items  []json.RawMessage `json:"items"`
		}
		if err := json.Unmarshal(body, &env); err != nil {
			return fmt.Errorf("decode envelope %s: %w", path, err)
		}
		for _, raw := range env.Items {
			if err := accumulator(raw); err != nil {
				return err
			}
		}
		pagesSeen++
		// Prefer Links.Next when FMC provides it — it carries the offset+limit
		// pre-baked and survives any operator-specific paging quirks.
		if env.Links.Next != "" {
			path = env.Links.Next
			continue
		}
		// Fallback: paging.pages declares the total page count. If we have
		// not yet visited all of them, advance offset by limit and refetch.
		// Some FMC versions omit links.next on the first page even when
		// pages > 1 (observed against 7.x; the Wave 0 RED test exercises
		// this exact shape).
		if env.Paging.Pages > pagesSeen {
			limit := env.Paging.Limit
			if limit <= 0 {
				limit = len(env.Items)
			}
			if limit <= 0 {
				// Empty page with pages>seen — degenerate; bail rather than spin.
				return nil
			}
			nextOffset := pagesSeen * limit
			path = withOffset(startPath, nextOffset, limit)
			continue
		}
		return nil
	}
	return fmt.Errorf("fmc: pagination exceeded %d pages at %s (T-11-10-04)", maxPages, host)
}

// withOffset rewrites the `offset=` query parameter on a paginated path,
// preserving the rest of the query string verbatim. Used by paginatedGet
// when the FMC omits links.next but reports paging.pages > 1.
func withOffset(rawPath string, offset, limit int) string {
	q := ""
	base := rawPath
	if i := strings.IndexByte(rawPath, '?'); i >= 0 {
		base = rawPath[:i]
		q = rawPath[i+1:]
	}
	pairs := []string{}
	if q != "" {
		for _, kv := range strings.Split(q, "&") {
			if kv == "" {
				continue
			}
			if strings.HasPrefix(kv, "offset=") {
				continue
			}
			pairs = append(pairs, kv)
		}
	}
	pairs = append(pairs, "offset="+strconv.Itoa(offset))
	// Ensure limit is present even if the caller omitted it.
	hasLimit := false
	for _, kv := range pairs {
		if strings.HasPrefix(kv, "limit=") {
			hasLimit = true
			break
		}
	}
	if !hasLimit && limit > 0 {
		pairs = append(pairs, "limit="+strconv.Itoa(limit))
	}
	return base + "?" + strings.Join(pairs, "&")
}

// ─── Normalization to push wire shape ────────────────────────────────────

// normalizeAccessRule converts an fmcAccessRule into a push.FirewallRule.
// FMC action values ("ALLOW"/"BLOCK"/"TRUST"/"MONITOR") are mapped to the
// canonical permit/deny taxonomy on the push shape; the original value is
// preserved in raw_blob for forensic accuracy.
//
// SrcCIDR / DstCIDR are populated from the first inline literal value,
// falling back to the first named object's Name. Phase 12 path computation
// reads SrcCIDR/DstCIDR — if both are empty, the rule is treated as
// wildcard (intentional: matches FMC's implicit "any/any" semantics when
// neither sourceNetworks nor destinationNetworks is specified).
func normalizeAccessRule(r fmcAccessRule) push.FirewallRule {
	return push.FirewallRule{
		Position: 0, // FMC orders by metadata.ruleIndex; preserved in raw_blob
		SrcZone:  firstZoneName(r.SourceZones),
		DstZone:  firstZoneName(r.DestinationZones),
		SrcCIDR:  firstNetworkValue(r.SourceNetworks),
		DstCIDR:  firstNetworkValue(r.DestinationNetworks),
		Action:   mapFMCAction(r.Action),
		Protocol: firstPortProtocol(r.DestinationPorts),
		Ports:    firstPortValue(r.DestinationPorts),
		RawBlob:  r.Raw,
	}
}

// normalizeNATRule converts an fmcNATRule into a push.FirewallNATRule.
// SrcTranslation / DstTranslation prefer the named object reference
// (operator-readable) over an empty object, matching the FMC operator UI
// convention. Interface names flow through verbatim.
func normalizeNATRule(n fmcNATRule) push.FirewallNATRule {
	return push.FirewallNATRule{
		Position:       0, // FMC orders by metadata.index; preserved in raw_blob
		SrcTranslation: n.TranslatedSource.Name,
		DstTranslation: n.TranslatedDestination.Name,
		InterfaceIn:    n.SourceInterface.Name,
		InterfaceOut:   n.DestinationInterface.Name,
		RawBlob:        n.Raw,
	}
}

// normalizeNetworkObject converts an fmcNetworkObject into a push.FirewallObject.
// FMC's "Host" type maps to the canonical "host" kind, "Network" maps to
// "network"; anything else falls back to "network" as a safe default
// (downstream consumers treat unknown kinds as opaque per D-09).
//
// Value is marshalled into a JSON object {"cidr": <value>} — Phase 12
// queries this column with JSONB path lookups, and a stable single-key
// shape simplifies that work. The full vendor shape is preserved in
// raw_blob.
func normalizeNetworkObject(o fmcNetworkObject) (push.FirewallObject, error) {
	kind := "network"
	if o.Type == "Host" {
		kind = "host"
	}
	value, err := json.Marshal(struct {
		CIDR string `json:"cidr"`
	}{CIDR: o.Value})
	if err != nil {
		return push.FirewallObject{}, fmt.Errorf("marshal object value name=%s: %w", o.Name, err)
	}
	return push.FirewallObject{
		Kind:    kind,
		Name:    o.Name,
		Value:   value,
		RawBlob: o.Raw,
	}, nil
}

// mapFMCAction translates FMC's uppercase action vocabulary to the
// canonical permit/deny shape on push.FirewallRule. Unknown values pass
// through lowercased so future FMC additions degrade gracefully.
func mapFMCAction(a string) string {
	switch strings.ToUpper(a) {
	case "ALLOW", "TRUST", "FASTPATH":
		return "permit"
	case "BLOCK", "BLOCK_RESET", "INTERACTIVE_BLOCK", "INTERACTIVE_BLOCK_RESET":
		return "deny"
	case "MONITOR":
		return "permit" // monitored traffic passes; the monitor side effect is FMC-internal
	default:
		return strings.ToLower(a)
	}
}

// firstZoneName returns the first zone object's Name, or "" if the list is
// empty / has only literals. Defensive index check per T-11-10-04.
func firstZoneName(z fmcZoneList) string {
	if len(z.Objects) == 0 {
		return ""
	}
	return z.Objects[0].Name
}

// firstNetworkValue returns the first source/destination address as a CIDR
// or named ref. Literals take precedence over object refs (literals are
// already CIDRs; object refs would require a second lookup to resolve).
// Defensive index check per T-11-10-04.
func firstNetworkValue(n fmcNetworkRefList) string {
	if len(n.Literals) > 0 {
		return n.Literals[0].Value
	}
	if len(n.Objects) > 0 {
		return n.Objects[0].Name
	}
	return ""
}

// firstPortValue returns the first port literal's Port, or "" if the list
// is empty. Defensive index check per T-11-10-04.
func firstPortValue(p fmcPortList) string {
	if len(p.Literals) == 0 {
		return ""
	}
	return p.Literals[0].Port
}

// firstPortProtocol returns the first port literal's Protocol number
// translated to "tcp" / "udp" / "icmp" where recognized; otherwise returns
// the raw value (or empty). FMC encodes protocols as IANA numbers in
// PortLiteral.Protocol.
func firstPortProtocol(p fmcPortList) string {
	if len(p.Literals) == 0 {
		return ""
	}
	proto := p.Literals[0].Protocol
	switch proto {
	case "6":
		return "tcp"
	case "17":
		return "udp"
	case "1":
		return "icmp"
	default:
		return proto
	}
}

// ─── Helpers ─────────────────────────────────────────────────────────────

// baseURL builds the FMC management base URL from host + port.
func baseURL(host string, port int) string {
	return "https://" + host + ":" + strconv.Itoa(port)
}

// buildURL accepts either an absolute URL (Links.Next from FMC) or a path
// fragment, and returns a URL string rooted at the configured host+port.
// FMC self/next URLs reference the FMC's own configured hostname, which
// may not match the inbound host the agent dials (operator deployments
// often expose FMC through a load-balancer hostname with a different SAN
// in the certificate). Re-rooting against host+port keeps every request
// going through the dial path the operator authorized.
func buildURL(host string, port int, raw string) (string, error) {
	if strings.HasPrefix(raw, "http://") || strings.HasPrefix(raw, "https://") {
		u, err := url.Parse(raw)
		if err != nil {
			return "", err
		}
		// Re-root path+query against host:port.
		return baseURL(host, port) + u.RequestURI(), nil
	}
	if !strings.HasPrefix(raw, "/") {
		raw = "/" + raw
	}
	return baseURL(host, port) + raw, nil
}

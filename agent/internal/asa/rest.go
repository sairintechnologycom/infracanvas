// rest.go — Cisco ASA REST API collector (ASA-01).
//
// Pulls access rules + NAT table + network objects from a Cisco ASA via the
// legacy REST API, normalizes the vendor-shape JSON into push.FirewallRule /
// push.FirewallNATRule / push.FirewallObject (D-08 hybrid: normalized
// columns + raw_blob), and returns three slices to the caller. The caller
// (collectAndPushFirewall in main.go, wired by Plan 11-12) is responsible
// for minting the snapshot_id and pushing the slices via push.Client.
//
// Token lifecycle (RESEARCH Pattern 3): a single Pull invocation calls
// POST /api/tokenservices, caches the returned X-Auth-Token on the stack
// for the duration of the pull, issues three authenticated GETs, then
// best-effort DELETEs the token via defer. Nothing persists between pulls.
//
// 401 from /api/tokenservices is reported as ErrASAAuth (non-retryable):
// the push client's D-07 retry-twice-then-drop logic recognizes
// non-retryable errors and surfaces them to the operator rather than
// spinning on them. T-11-08-02.
//
// ASA REST API EOL: Cisco removed the legacy REST API at ASA 9.17+.
// Operators running 9.17 or newer must switch to protocol: asa-ssh in
// agent.yaml. RESEARCH Pitfall 1. Plan 11-13 lifts this language into
// agent/docs/cab/known-limitations.md as the operator-facing surface.
//
// Caller passes primitives (host, port, user, pass) rather than a
// config.Device — Pattern H, avoids the internal/config ↔ internal/asa
// import cycle.
//
// NO retry inside the collector — D-07 retry is owned by push.Client
// (Plan 11-05). Collector errors return cleanly; the next ticker tick is
// the retry.
//
// Pattern G credential redaction: this collector NEVER logs username,
// password, or the X-Auth-Token. Basic-auth is set via req.SetBasicAuth
// (which the net/http stack does not log); the token is used only as an
// outbound header value.
package asa

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

// ErrASAAuth is returned from Pull when the ASA REST endpoint rejects the
// caller's credentials (HTTP 401 from POST /api/tokenservices). The error
// is sentinel-comparable via errors.Is so the dispatcher (Plan 11-12) and
// the push client can surface it as non-retryable. T-11-08-02.
var ErrASAAuth = errors.New("asa-rest: 401 unauthorized (non-retryable)")

// aclInterface is the named ACL interface the REST collector pulls from.
// ASA REST exposes one ACL per interface; "outside_in" is the conventional
// inside→outside policy name on canonical fixtures and is also what the
// Plan 11-01 RED test stubs serve at /api/access/in/outside_in/rules.
// Future work (operator config knob) can make this per-device.
const aclInterface = "outside_in"

// defaultHTTPTimeout matches the netconf collector's SSH dial timeout —
// 10 seconds is the established Phase 10 ceiling for management-plane
// dials. The REST collector inherits that ceiling for the same operator
// expectations.
const defaultHTTPTimeout = 10 * time.Second

// defaultPort is the ASA HTTPS management port. Operators can override via
// agent.yaml.devices[].port; 0 means "use the default".
const defaultPort = 443

// RESTCollector pulls firewall state from a Cisco ASA via the REST API.
// The http.Client field is the test seam: tests inject an httptest.Server's
// client; production passes nil to NewRESTCollector to get a TLS-validating
// client with the default 10 s timeout.
type RESTCollector struct {
	http *http.Client
}

// NewRESTCollector returns a RESTCollector. Pass nil to get a production
// http.Client with TLS validation enabled and a 10 s timeout. Pass a
// httptest.Server.Client() (or any other *http.Client) for tests.
//
// InsecureSkipVerify is intentionally false in the production default —
// operator-managed TLS certificates on the ASA management interface are
// the Phase 10 / Phase 11 security baseline (T-11-08-01 acceptance posture).
// Plan 11-13 / CAB documents the future operator knob to flip this.
func NewRESTCollector(client *http.Client) *RESTCollector {
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
	return &RESTCollector{http: client}
}

// Pull acquires a token, fetches the three datasets, normalizes them to the
// push wire shapes, releases the token best-effort, and returns three
// slices. The caller mints the snapshot_id and pushes via push.Client.
//
// Errors are wrapped per the Phase 10 convention:
//
//	"asa-rest: <stage> %s: %w"
//
// On 401 from the token endpoint Pull returns (nil, nil, nil, ErrASAAuth)
// — errors.Is(err, ErrASAAuth) is true so the caller can branch on it.
func (c *RESTCollector) Pull(
	ctx context.Context,
	host string,
	port int,
	user, pass string,
) ([]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error) {
	if port == 0 {
		port = defaultPort
	}
	base := baseURL(host, port)

	tok, err := c.acquireToken(ctx, base, user, pass)
	if err != nil {
		return nil, nil, nil, err
	}
	defer c.deleteToken(ctx, base, tok)

	var aclResp asaACLResponse
	if err := c.doGet(ctx, base+"/api/access/in/"+aclInterface+"/rules", tok, &aclResp); err != nil {
		return nil, nil, nil, fmt.Errorf("asa-rest: acl %s: %w", host, err)
	}

	var natResp asaNATResponse
	if err := c.doGet(ctx, base+"/api/nat", tok, &natResp); err != nil {
		return nil, nil, nil, fmt.Errorf("asa-rest: nat %s: %w", host, err)
	}

	var objResp asaObjectsResponse
	if err := c.doGet(ctx, base+"/api/objects/networkobjects", tok, &objResp); err != nil {
		return nil, nil, nil, fmt.Errorf("asa-rest: objects %s: %w", host, err)
	}

	rules, err := normalizeRules(aclResp.Items)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("asa-rest: normalize rules %s: %w", host, err)
	}
	nats, err := normalizeNATs(natResp.Items)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("asa-rest: normalize nat %s: %w", host, err)
	}
	objs, err := normalizeObjects(objResp.Items)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("asa-rest: normalize objects %s: %w", host, err)
	}

	return rules, nats, objs, nil
}

// ─── Token lifecycle ──────────────────────────────────────────────────────

// acquireToken POSTs basic-auth credentials to /api/tokenservices and reads
// the X-Auth-Token response header. 401 returns ErrASAAuth (non-retryable);
// other non-2xx statuses return a wrapped error.
//
// Pattern G: user/pass are passed only via req.SetBasicAuth — they are
// never logged, never embedded in the URL, never stringified.
func (c *RESTCollector) acquireToken(ctx context.Context, base, user, pass string) (string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, base+"/api/tokenservices", nil)
	if err != nil {
		return "", fmt.Errorf("asa-rest: token build %s: %w", hostOf(base), err)
	}
	req.SetBasicAuth(user, pass)
	req.Header.Set("Accept", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return "", fmt.Errorf("asa-rest: token %s: %w", hostOf(base), err)
	}
	defer func() { _ = resp.Body.Close() }()
	// Drain body so the connection can be reused. Bounded read defends
	// against a hostile server streaming gigabytes into a 401 body
	// (T-11-08-04 — adversary-controlled ASA hardening).
	_, _ = io.CopyN(io.Discard, resp.Body, 4096)

	if resp.StatusCode == http.StatusUnauthorized {
		return "", ErrASAAuth
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", fmt.Errorf("asa-rest: token %s: status %d", hostOf(base), resp.StatusCode)
	}

	tok := resp.Header.Get("X-Auth-Token")
	if tok == "" {
		return "", fmt.Errorf("asa-rest: token %s: missing X-Auth-Token header", hostOf(base))
	}
	return tok, nil
}

// deleteToken issues DELETE /api/tokenservices/<token> on a best-effort basis.
// Failures are swallowed silently — the ASA times tokens out after 30 min
// anyway (T-11-08-05 acceptance). The token value itself is NEVER logged
// (Pattern G); only the host is mentioned on error.
func (c *RESTCollector) deleteToken(ctx context.Context, base, tok string) {
	if tok == "" {
		return
	}
	// Best-effort cleanup; use a derived context with a short timeout so a
	// cancelled parent ctx still gets the DELETE in flight.
	dctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	_ = ctx // parent ctx not used: deletion is fire-and-forget even on shutdown
	defer cancel()

	req, err := http.NewRequestWithContext(
		dctx, http.MethodDelete,
		base+"/api/tokenservices/"+url.PathEscape(tok),
		nil,
	)
	if err != nil {
		return
	}
	resp, err := c.http.Do(req)
	if err != nil {
		// Pattern G: tok is intentionally absent from any log surface; we
		// don't emit zap here because the collector doesn't carry a logger
		// (see Pattern H — caller wires logging). Silent failure is the
		// accepted posture for T-11-08-05.
		return
	}
	_, _ = io.CopyN(io.Discard, resp.Body, 4096)
	_ = resp.Body.Close()
}

// ─── Authenticated GET ────────────────────────────────────────────────────

// doGet issues a GET with the X-Auth-Token header and unmarshals the JSON
// body into out. The response body read is bounded to 16 MiB to cap
// adversary-controlled payload size (T-11-08-04).
func (c *RESTCollector) doGet(ctx context.Context, urlStr, tok string, out interface{}) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, urlStr, nil)
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("X-Auth-Token", tok)
	req.Header.Set("Accept", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode == http.StatusUnauthorized {
		return ErrASAAuth
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("status %d", resp.StatusCode)
	}

	// 16 MiB cap — large enough for any plausible rule base, small enough
	// to bound memory if the device misbehaves.
	body, err := io.ReadAll(io.LimitReader(resp.Body, 16*1024*1024))
	if err != nil {
		return fmt.Errorf("read body: %w", err)
	}
	if err := json.Unmarshal(body, out); err != nil {
		return fmt.Errorf("unmarshal: %w", err)
	}
	return nil
}

// ─── Normalization to push wire shape ────────────────────────────────────

// normalizeRules converts asaACLItem slices to push.FirewallRule slices.
// Each item's raw_blob captures the original vendor JSON via re-marshal
// (D-08 hybrid — normalized columns drive Phase 12 path computation, the
// raw blob preserves the vendor-native shape for future forensics).
func normalizeRules(items []asaACLItem) ([]push.FirewallRule, error) {
	out := make([]push.FirewallRule, 0, len(items))
	for _, it := range items {
		raw, err := json.Marshal(it)
		if err != nil {
			return nil, fmt.Errorf("rule pos=%d: %w", it.Position, err)
		}
		action := "deny"
		if it.Permit {
			action = "permit"
		}
		proto, ports := splitProtocolValue(it.DestinationService.Value)
		out = append(out, push.FirewallRule{
			Position: it.Position,
			SrcCIDR:  addrRefToCIDR(it.SourceAddress),
			DstCIDR:  addrRefToCIDR(it.DestinationAddress),
			Action:   action,
			Protocol: proto,
			Ports:    ports,
			RawBlob:  raw,
		})
	}
	return out, nil
}

// normalizeNATs converts asaNATItem slices to push.FirewallNATRule slices.
func normalizeNATs(items []asaNATItem) ([]push.FirewallNATRule, error) {
	out := make([]push.FirewallNATRule, 0, len(items))
	for _, it := range items {
		raw, err := json.Marshal(it)
		if err != nil {
			return nil, fmt.Errorf("nat pos=%d: %w", it.Position, err)
		}
		out = append(out, push.FirewallNATRule{
			Position:       it.Position,
			SrcTranslation: netObjRefToString(it.TranslatedSourceNetworkObject),
			DstTranslation: netObjRefToString(it.OriginalSourceNetworkObject),
			InterfaceIn:    it.OriginalSourceInterface.Name,
			InterfaceOut:   it.TranslatedSourceInterface.Name,
			RawBlob:        raw,
		})
	}
	return out, nil
}

// normalizeObjects converts asaObjectItem slices to push.FirewallObject
// slices. Kind is mapped from ASA's "object#NetworkObj" /
// "object#NetworkObjGroup" / inner Host/Network hints to the canonical
// {host, network, group} taxonomy from D-09.
func normalizeObjects(items []asaObjectItem) ([]push.FirewallObject, error) {
	out := make([]push.FirewallObject, 0, len(items))
	for _, it := range items {
		raw, err := json.Marshal(it)
		if err != nil {
			return nil, fmt.Errorf("object name=%s: %w", it.Name, err)
		}
		kind := classifyObjectKind(it)
		value, err := objectValueJSON(it)
		if err != nil {
			return nil, fmt.Errorf("object name=%s: %w", it.Name, err)
		}
		out = append(out, push.FirewallObject{
			Kind:    kind,
			Name:    it.Name,
			Value:   value,
			RawBlob: raw,
		})
	}
	return out, nil
}

// classifyObjectKind maps the ASA object shape to {host, network, group}.
// "object#NetworkObjGroup" → group; otherwise the inner Host/Network field
// decides between host (IPv4Address) and network (IPv4Network).
func classifyObjectKind(it asaObjectItem) string {
	if strings.Contains(it.Kind, "Group") || len(it.Members) > 0 {
		return "group"
	}
	if it.Host != nil {
		if it.Host.Kind == "IPv4Network" {
			return "network"
		}
		return "host"
	}
	if it.Network != nil {
		return "network"
	}
	// Fallback when the wire shape is ambiguous — D-09's "group" is the
	// safest catch-all since downstream consumers treat unknown kinds as
	// opaque.
	return "group"
}

// objectValueJSON marshals the meaningful sub-shape of an object into JSON
// for the push.FirewallObject.Value JSONB field. Hosts emit their value
// string, networks their CIDR, groups their member list. The full vendor
// shape is preserved separately in RawBlob.
func objectValueJSON(it asaObjectItem) (json.RawMessage, error) {
	switch {
	case it.Host != nil:
		return json.Marshal(it.Host)
	case it.Network != nil:
		return json.Marshal(it.Network)
	case len(it.Members) > 0:
		return json.Marshal(it.Members)
	default:
		return json.Marshal(struct{}{})
	}
}

// addrRefToCIDR collapses an asaAddressRef to a CIDR string for the
// normalized src_cidr / dst_cidr column. ASA emits "any" for AnyIPAddress
// and a literal CIDR or host IP for objectRef shapes; the value field is
// the source of truth.
func addrRefToCIDR(ref asaAddressRef) string {
	if ref.Value == "" {
		return ref.ObjRef
	}
	if ref.Value == "any" {
		return "0.0.0.0/0"
	}
	return ref.Value
}

// netObjRefToString collapses an asaNetObjRef to the string the push
// payload's src_translation / dst_translation expects. Name takes
// precedence (operator-readable) over Value (raw CIDR) for translated
// fields, matching the ASA-side naming convention.
func netObjRefToString(ref asaNetObjRef) string {
	if ref.Name != "" {
		return ref.Name
	}
	if ref.Value != "" {
		return ref.Value
	}
	return ref.ObjRef
}

// splitProtocolValue parses the ASA destinationService.value form
// ("tcp/80", "udp/53", "ip", "any") into (protocol, ports). Unknown shapes
// return (value, "") so the caller can decide how to surface them.
func splitProtocolValue(v string) (proto, ports string) {
	if v == "" {
		return "", ""
	}
	if i := strings.IndexByte(v, '/'); i >= 0 {
		return v[:i], v[i+1:]
	}
	return v, ""
}

// ─── Helpers ─────────────────────────────────────────────────────────────

// baseURL builds the ASA management base URL from host + port.
func baseURL(host string, port int) string {
	return "https://" + host + ":" + strconv.Itoa(port)
}

// hostOf strips the scheme + port off a baseURL for error messages.
// Used inside acquireToken/deleteToken where the original `host` parameter
// is not in scope and we want the error wrap to mention only the host.
func hostOf(base string) string {
	s := strings.TrimPrefix(base, "https://")
	s = strings.TrimPrefix(s, "http://")
	if i := strings.IndexByte(s, ':'); i >= 0 {
		s = s[:i]
	}
	return s
}

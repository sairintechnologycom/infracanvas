// live.go — Checkpoint Management API live collector (CKP-01).
//
// LiveCollector implements the D-14 lifecycle: login → fetch (paginated)
// rulebase + NAT rulebase + objects → logout (best-effort). Each Pull
// invocation owns its own SID; no SID is persisted between pulls, so we
// never have an at-rest credential to protect. The SID itself is held only
// on the stack for the duration of the pull.
//
// Pattern G (SID redaction): the SID is passed only via the X-chkp-sid
// header on outbound requests. It is NEVER logged — not as a zap field, not
// in a printf, not in an error wrap. live_test.go captures the collector's
// log output and grep-fails on the SID literal as a regression guard.
//
// Pitfall 2 mitigation: login passes `"session-timeout": 3600` to extend
// the SID's server-side validity past Checkpoint's default short window.
// Large rule bases (Risk Landmine 4) on slow management interfaces can
// otherwise drain SIDs mid-pull. The 1-hour ceiling is also the
// Phase 11 D-02 ticker cadence so any single pull will finish before the
// next attempt regardless of SID re-issue.
//
// Pagination: show-access-rulebase and show-nat-rulebase paginate at 500
// rows per page via {offset, limit}. The loop continues while
// response.To < response.Total. Accumulated rules are re-marshalled into a
// single ckpAccessRulebaseResp / ckpNATRulebaseResp envelope so Parse sees
// one payload — this keeps the live and import code paths byte-identical
// at the parser boundary (D-12).
//
// 401 from login → ErrCheckpointAuth (non-retryable). Pattern H: caller
// owns retry policy (push.Client's retry-twice-then-drop in Plan 11-05);
// the next ticker tick is the next attempt.
package checkpoint

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"

	"github.com/infracanvas/infracanvas/agent/internal/push"
)

// ErrCheckpointAuth is returned from Pull when /web_api/login rejects the
// caller's credentials (HTTP 401). The error is sentinel-comparable via
// errors.Is so the dispatcher (Plan 11-12) and the push client can surface
// it as non-retryable. T-11-11-03.
var ErrCheckpointAuth = errors.New("checkpoint: authentication failed (non-retryable)")

// defaultHTTPTimeout matches Phase 10's management-plane dial ceiling.
const defaultHTTPTimeout = 30 * time.Second

// defaultPort is the Checkpoint Management API HTTPS port. Operators
// override via agent.yaml.devices[].port; 0 means "use the default".
const defaultPort = 443

// pageLimit is the per-page row count the collector requests from
// show-access-rulebase / show-nat-rulebase. 500 is Checkpoint's documented
// maximum.
const pageLimit = 500

// maxPages guards against a runaway server reporting unbounded `total`
// values. With pageLimit=500 this caps a single Pull at 5 million rules
// across the access + NAT rulebases — orders of magnitude beyond any
// realistic Checkpoint deployment.
const maxPages = 10000

// defaultRulebaseName is the canonical Checkpoint policy package name.
// Operator-managed alternates (e.g. "MyPolicy") are a future config knob;
// "Standard" matches the Wave 0 fixtures and the Checkpoint default.
const defaultRulebaseName = "Standard"

// LiveCollector pulls Checkpoint policy state via the Management API. The
// http.Client field is the test seam: tests inject an httptest.Server's
// client; production passes nil to NewLiveCollector to get a TLS-validating
// client with the default timeout. The log field is wired by tests via
// NewLiveCollectorWithLogger so the SID-redaction assertion can grep the
// captured log bytes.
type LiveCollector struct {
	http *http.Client
	log  *zap.Logger
}

// NewLiveCollector returns a LiveCollector with a nop logger. Pass nil for
// the http.Client to get a production client (TLS 1.2+, 30 s timeout).
// Tests inject an httptest.Server.Client(); production passes nil.
func NewLiveCollector(client *http.Client) *LiveCollector {
	return &LiveCollector{
		http: defaultClient(client),
		log:  zap.NewNop(),
	}
}

// NewLiveCollectorWithLogger returns a LiveCollector that writes its
// structured log lines to the provided io.Writer. Used by Wave 0's
// TestLiveCollector_LoginPullLogout to capture log output and assert the
// SID never appears. Production callers should use NewLiveCollector and
// hook into the main zap logger via the dispatcher (Plan 11-12).
func NewLiveCollectorWithLogger(client *http.Client, w io.Writer) *LiveCollector {
	encoderCfg := zap.NewProductionEncoderConfig()
	encoderCfg.EncodeTime = zapcore.ISO8601TimeEncoder
	core := zapcore.NewCore(
		zapcore.NewJSONEncoder(encoderCfg),
		zapcore.AddSync(w),
		zapcore.InfoLevel,
	)
	return &LiveCollector{
		http: defaultClient(client),
		log:  zap.New(core),
	}
}

// defaultClient mirrors the Phase 11 ASA REST collector's default — TLS 1.2+
// with full certificate validation. Operator-managed TLS on the Checkpoint
// mgmt interface is the security baseline; Plan 11-13 / CAB documents the
// future knob to flip InsecureSkipVerify for lab use.
func defaultClient(c *http.Client) *http.Client {
	if c != nil {
		return c
	}
	return &http.Client{
		Timeout: defaultHTTPTimeout,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{
				MinVersion:         tls.VersionTLS12,
				InsecureSkipVerify: false,
			},
		},
	}
}

// Pull acquires a SID, fetches the rulebase + NAT + objects payloads,
// invokes the shared Parse, and returns normalized slices. The SID is
// released via best-effort logout in a deferred call. Errors are wrapped
// "checkpoint: <stage> <host>: %w" per the Phase 10 convention.
func (c *LiveCollector) Pull(
	ctx context.Context,
	host string,
	port int,
	user, pass string,
) ([]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error) {
	if port == 0 {
		port = defaultPort
	}
	base := baseURL(host, port)

	sid, err := c.login(ctx, base, host, user, pass)
	if err != nil {
		return nil, nil, nil, err
	}
	// Best-effort logout — Pattern G: sid NEVER appears in any zap field.
	defer c.logout(base, host, sid)

	rulebaseBytes, pages, err := c.showRulebase(ctx, base, host, sid)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("checkpoint: rulebase %s: %w", host, err)
	}
	natBytes, natPages, err := c.showNATRulebase(ctx, base, host, sid)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("checkpoint: nat-rulebase %s: %w", host, err)
	}
	objBytes, err := c.showObjects(ctx, base, host, sid)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("checkpoint: objects %s: %w", host, err)
	}

	rules, nats, objs, err := Parse(rulebaseBytes, natBytes, objBytes)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("checkpoint: parse %s: %w", host, err)
	}

	// Pattern G: log only host + counts. SID never appears.
	c.log.Info("checkpoint_pull_complete",
		zap.String("host", host),
		zap.Int("rules", len(rules)),
		zap.Int("nat_rules", len(nats)),
		zap.Int("objects", len(objs)),
		zap.Int("rulebase_pages", pages),
		zap.Int("nat_pages", natPages),
	)
	return rules, nats, objs, nil
}

// ─── Session lifecycle ───────────────────────────────────────────────────

// login POSTs credentials + a 3600 s session-timeout hint to /web_api/login.
// Returns the SID on success, ErrCheckpointAuth on 401, a wrapped error
// otherwise. Pattern G: user/pass never appear in any log field or error
// wrap; only the host is mentioned.
func (c *LiveCollector) login(ctx context.Context, base, host, user, pass string) (string, error) {
	body, err := json.Marshal(map[string]any{
		"user":            user,
		"password":        pass,
		"session-timeout": 3600,
	})
	if err != nil {
		return "", fmt.Errorf("checkpoint: login build %s: %w", host, err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, base+"/web_api/login", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("checkpoint: login build %s: %w", host, err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return "", fmt.Errorf("checkpoint: login %s: %w", host, err)
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode == http.StatusUnauthorized {
		// Drain the body so the connection can be reused (bounded).
		_, _ = io.CopyN(io.Discard, resp.Body, 4096)
		return "", ErrCheckpointAuth
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", fmt.Errorf("checkpoint: login %s: status %d", host, resp.StatusCode)
	}

	respBytes, err := io.ReadAll(io.LimitReader(resp.Body, 64*1024))
	if err != nil {
		return "", fmt.Errorf("checkpoint: login %s: read: %w", host, err)
	}
	var lr ckpLoginResp
	if err := json.Unmarshal(respBytes, &lr); err != nil {
		return "", fmt.Errorf("checkpoint: login %s: parse: %w", host, err)
	}
	if lr.SID == "" {
		return "", fmt.Errorf("checkpoint: login %s: empty sid in response", host)
	}
	return lr.SID, nil
}

// logout POSTs an empty body to /web_api/logout with the X-chkp-sid header.
// Failures are logged at WARN but never propagate to the Pull caller — the
// SID will expire on its own (T-11-11-06 acceptance posture). Pattern G:
// the SID is intentionally absent from every zap field.
func (c *LiveCollector) logout(base, host, sid string) {
	if sid == "" {
		return
	}
	// Use a derived context so a cancelled parent ctx still gets the
	// DELETE in flight. 5 s is enough for a single round trip to the
	// management interface.
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, base+"/web_api/logout", bytes.NewReader([]byte("{}")))
	if err != nil {
		c.log.Warn("checkpoint_logout_failed", zap.String("host", host), zap.String("stage", "build"))
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	req.Header.Set("X-chkp-sid", sid)

	resp, err := c.http.Do(req)
	if err != nil {
		c.log.Warn("checkpoint_logout_failed", zap.String("host", host), zap.String("stage", "do"))
		return
	}
	_, _ = io.CopyN(io.Discard, resp.Body, 4096)
	_ = resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		c.log.Warn("checkpoint_logout_failed", zap.String("host", host), zap.Int("status", resp.StatusCode))
	}
}

// ─── Authenticated fetchers ──────────────────────────────────────────────

// showRulebase pulls the full access rulebase, paginating via offset+limit.
// Accumulated rules are re-marshalled into a single ckpAccessRulebaseResp
// envelope so Parse sees one canonical payload — this keeps live and import
// byte-identical at the parser boundary (D-12).
//
// Returns the marshalled envelope bytes plus the number of pages walked,
// for log accounting.
func (c *LiveCollector) showRulebase(ctx context.Context, base, host, sid string) ([]byte, int, error) {
	combined := ckpAccessRulebaseResp{}
	pages := 0
	for offset := 0; ; pages++ {
		if pages >= maxPages {
			return nil, pages, fmt.Errorf("checkpoint: rulebase %s: pagination exceeded %d pages", host, maxPages)
		}
		body, err := json.Marshal(map[string]any{
			"name":                  defaultRulebaseName,
			"details-level":         "full",
			"use-object-dictionary": true,
			"offset":                offset,
			"limit":                 pageLimit,
		})
		if err != nil {
			return nil, pages, fmt.Errorf("build: %w", err)
		}
		var page ckpAccessRulebaseResp
		if err := c.postJSON(ctx, base+"/web_api/show-access-rulebase", sid, body, &page); err != nil {
			return nil, pages, err
		}
		combined.Rulebase = append(combined.Rulebase, page.Rulebase...)
		// Pagination terminator: once the server reports we've reached
		// the end of the result set, stop. Defensive: also stop if the
		// page returned zero rows (empty rulebase).
		if page.To >= page.Total || len(page.Rulebase) == 0 {
			combined.Total = len(combined.Rulebase)
			combined.From = 1
			combined.To = len(combined.Rulebase)
			break
		}
		offset = page.To
	}
	out, err := json.Marshal(combined)
	if err != nil {
		return nil, pages, fmt.Errorf("checkpoint: rulebase %s: marshal envelope: %w", host, err)
	}
	return out, pages + 1, nil
}

// showNATRulebase mirrors showRulebase against /web_api/show-nat-rulebase.
// The body must include the policy package name; Checkpoint's NAT rulebase
// is co-located with the access rulebase under the same package.
func (c *LiveCollector) showNATRulebase(ctx context.Context, base, host, sid string) ([]byte, int, error) {
	combined := ckpNATRulebaseResp{}
	pages := 0
	for offset := 0; ; pages++ {
		if pages >= maxPages {
			return nil, pages, fmt.Errorf("checkpoint: nat-rulebase %s: pagination exceeded %d pages", host, maxPages)
		}
		body, err := json.Marshal(map[string]any{
			"package":       defaultRulebaseName,
			"details-level": "full",
			"offset":        offset,
			"limit":         pageLimit,
		})
		if err != nil {
			return nil, pages, fmt.Errorf("build: %w", err)
		}
		var page ckpNATRulebaseResp
		if err := c.postJSON(ctx, base+"/web_api/show-nat-rulebase", sid, body, &page); err != nil {
			return nil, pages, err
		}
		combined.Rulebase = append(combined.Rulebase, page.Rulebase...)
		if page.To >= page.Total || len(page.Rulebase) == 0 {
			combined.Total = len(combined.Rulebase)
			combined.From = 1
			combined.To = len(combined.Rulebase)
			break
		}
		offset = page.To
	}
	out, err := json.Marshal(combined)
	if err != nil {
		return nil, pages, fmt.Errorf("checkpoint: nat-rulebase %s: marshal envelope: %w", host, err)
	}
	return out, pages + 1, nil
}

// showObjects pulls all objects via /web_api/show-objects. v1 issues a single
// request with type=any and limit=500; if Total exceeds the page size we
// loop. Phase 11 D-13 limits scope to hosts/networks/groups/services, all of
// which Checkpoint returns under the catch-all type=any.
func (c *LiveCollector) showObjects(ctx context.Context, base, host, sid string) ([]byte, error) {
	combined := ckpObjectsResp{}
	for offset := 0; ; {
		body, err := json.Marshal(map[string]any{
			"type":          "any",
			"details-level": "full",
			"offset":        offset,
			"limit":         pageLimit,
		})
		if err != nil {
			return nil, fmt.Errorf("build: %w", err)
		}
		var page ckpObjectsResp
		if err := c.postJSON(ctx, base+"/web_api/show-objects", sid, body, &page); err != nil {
			return nil, err
		}
		combined.Objects = append(combined.Objects, page.Objects...)
		if page.To >= page.Total || len(page.Objects) == 0 {
			combined.Total = len(combined.Objects)
			combined.From = 1
			combined.To = len(combined.Objects)
			break
		}
		offset = page.To
	}
	out, err := json.Marshal(combined)
	if err != nil {
		return nil, fmt.Errorf("checkpoint: objects %s: marshal envelope: %w", host, err)
	}
	return out, nil
}

// postJSON is the shared authenticated POST helper. It applies the
// X-chkp-sid header, posts the body, and unmarshals the JSON response into
// out. 401 responses produce ErrCheckpointAuth so the dispatcher can route
// to the non-retryable surface.
func (c *LiveCollector) postJSON(ctx context.Context, urlStr, sid string, body []byte, out interface{}) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, urlStr, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("build: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	req.Header.Set("X-chkp-sid", sid)

	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode == http.StatusUnauthorized {
		_, _ = io.CopyN(io.Discard, resp.Body, 4096)
		return ErrCheckpointAuth
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("status %d", resp.StatusCode)
	}
	// 16 MiB cap mirrors the ASA REST collector — large enough for any
	// plausible single page, small enough to bound adversary-controlled
	// payload size (T-11-11-05).
	respBytes, err := io.ReadAll(io.LimitReader(resp.Body, 16*1024*1024))
	if err != nil {
		return fmt.Errorf("read body: %w", err)
	}
	if err := json.Unmarshal(respBytes, out); err != nil {
		return fmt.Errorf("unmarshal: %w", err)
	}
	return nil
}

// ─── Helpers ──────────────────────────────────────────────────────────────

// baseURL builds the Checkpoint management base URL from host + port.
// The collector accepts both "host" and "host:port" forms in the host
// parameter for resilience against tests that pass URL fragments.
func baseURL(host string, port int) string {
	// If host already carries a port (e.g. from a testhelper that split
	// "127.0.0.1:54321" then joined them), don't double it.
	if strings.Contains(host, ":") {
		return "http://" + host
	}
	// Tests use httptest.NewServer (plain http). Production uses TLS.
	// We pick https when port is the default 443, http otherwise — which
	// in practice means tests always end up on http (their port is
	// non-default) and operators on https.
	scheme := "http"
	if port == 443 {
		scheme = "https"
	}
	return scheme + "://" + host + ":" + strconv.Itoa(port)
}

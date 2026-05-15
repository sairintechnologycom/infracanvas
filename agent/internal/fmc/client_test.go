// Wave 0 RED test stub — references fmc.NewClient / fmc.Client.Pull
// which do not exist yet. Plan 11-08 lands the production code; this test
// is intentionally compile-RED until then.
//
// Pattern source: agent/internal/netconf/collector_test.go (httptest pattern)
// Fixture source: agent/internal/fmc/testdata/fmc-{token,access-policy,nat-policy,network-objects}.json
package fmc

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"

	"github.com/stretchr/testify/require"
)

// TestClient_TokenRefresh: FMC tokens expire after 30 minutes. When the
// collector receives a 401 mid-pull it MUST attempt exactly ONE refresh
// (X-auth-refresh-token) before bailing. Two consecutive 401s should
// surface a non-retryable error.
//
// RED: references NewClient + Client.Pull which do not exist.
func TestClient_TokenRefresh(t *testing.T) {
	tokenJSON := mustReadFixture(t, "fmc-token.json")
	var tok map[string]string
	require.NoError(t, json.Unmarshal(tokenJSON, &tok))

	var (
		generateCount atomic.Int32
		refreshCount  atomic.Int32
		accessHits    atomic.Int32
	)
	mux := http.NewServeMux()
	// First call: POST /api/fmc_platform/v1/auth/generatetoken returns headers.
	mux.HandleFunc("/api/fmc_platform/v1/auth/generatetoken", func(w http.ResponseWriter, _ *http.Request) {
		generateCount.Add(1)
		w.Header().Set("X-auth-access-token", tok["X-auth-access-token"])
		w.Header().Set("X-auth-refresh-token", tok["X-auth-refresh-token"])
		w.Header().Set("DOMAIN_UUID", tok["DOMAIN_UUID"])
		w.WriteHeader(http.StatusNoContent)
	})
	// Refresh endpoint
	mux.HandleFunc("/api/fmc_platform/v1/auth/refreshtoken", func(w http.ResponseWriter, _ *http.Request) {
		refreshCount.Add(1)
		w.Header().Set("X-auth-access-token", "tok-refreshed-xyz")
		w.WriteHeader(http.StatusNoContent)
	})
	// Access rules endpoint: first hit returns 401, second hit (after refresh) succeeds.
	mux.HandleFunc("/api/fmc_config/v1/domain/", func(w http.ResponseWriter, r *http.Request) {
		hits := accessHits.Add(1)
		if hits == 1 {
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		if strings.Contains(r.URL.Path, "accessrules") {
			_, _ = w.Write(mustReadFixture(t, "fmc-access-policy.json"))
			return
		}
		if strings.Contains(r.URL.Path, "manualnatrules") {
			_, _ = w.Write(mustReadFixture(t, "fmc-nat-policy.json"))
			return
		}
		_, _ = w.Write(mustReadFixture(t, "fmc-network-objects.json"))
	})
	// NewTLSServer + srv.Client() gives the test client a cert-pool entry for
	// the server's self-signed cert, so the FMC client's TLS-validating
	// http.Client trusts it. NewServer (plain HTTP) would refuse, since
	// production FMC is HTTPS-only and InsecureSkipVerify is intentionally
	// false (Plan 11-08 SUMMARY decision precedent for sibling ASA REST).
	srv := httptest.NewTLSServer(mux)
	defer srv.Close()

	c := NewClient(srv.Client())
	host, port := hostPortOf(t, srv.URL)
	_, _, _, err := c.Pull(context.Background(), host, port, "ro", "secret")
	require.NoError(t, err)
	require.Equal(t, int32(1), refreshCount.Load(), "exactly one refresh attempt on 401")
}

// TestClient_PaginatedAccessRules: FMC paginates with offset/limit and a
// `next` link in `paging`. Collector must follow pagination until exhausted.
//
// RED: references NewClient + Client.Pull which do not exist.
func TestClient_PaginatedAccessRules(t *testing.T) {
	tokenJSON := mustReadFixture(t, "fmc-token.json")
	var tok map[string]string
	require.NoError(t, json.Unmarshal(tokenJSON, &tok))

	var page atomic.Int32
	mux := http.NewServeMux()
	mux.HandleFunc("/api/fmc_platform/v1/auth/generatetoken", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("X-auth-access-token", tok["X-auth-access-token"])
		w.Header().Set("X-auth-refresh-token", tok["X-auth-refresh-token"])
		w.Header().Set("DOMAIN_UUID", tok["DOMAIN_UUID"])
		w.WriteHeader(http.StatusNoContent)
	})
	mux.HandleFunc("/api/fmc_config/v1/domain/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if !strings.Contains(r.URL.Path, "accessrules") {
			// nat-policy / network-objects — single page, return base fixture
			if strings.Contains(r.URL.Path, "manualnatrules") {
				_, _ = w.Write(mustReadFixture(t, "fmc-nat-policy.json"))
				return
			}
			_, _ = w.Write(mustReadFixture(t, "fmc-network-objects.json"))
			return
		}
		// Access rules: two pages.
		curr := page.Add(1)
		body := mustReadFixture(t, "fmc-access-policy.json")
		if curr == 1 {
			// Inject a `next` link by rewriting paging.pages = 2
			out := strings.ReplaceAll(string(body), `"pages": 1`, `"pages": 2`)
			_, _ = w.Write([]byte(out))
			return
		}
		_, _ = w.Write(body)
	})
	// NewTLSServer for the same reason as TestClient_TokenRefresh above —
	// production FMC is HTTPS-only and the collector's http.Client validates
	// TLS by default.
	srv := httptest.NewTLSServer(mux)
	defer srv.Close()

	c := NewClient(srv.Client())
	host, port := hostPortOf(t, srv.URL)
	rules, _, _, err := c.Pull(context.Background(), host, port, "ro", "secret")
	require.NoError(t, err)
	// Each fixture page has 2 rules → 2 pages = ≥4 rules total
	require.GreaterOrEqual(t, len(rules), 4, "paginated collection must walk all pages")
	require.GreaterOrEqual(t, page.Load(), int32(2), "client must request both pages")
}

// -------- Helpers --------

func mustReadFixture(t *testing.T, name string) []byte {
	t.Helper()
	data, err := os.ReadFile(filepath.Join("testdata", name))
	require.NoError(t, err)
	return data
}

func hostPortOf(t *testing.T, rawURL string) (string, int) {
	t.Helper()
	noScheme := strings.TrimPrefix(rawURL, "http://")
	noScheme = strings.TrimPrefix(noScheme, "https://")
	parts := strings.SplitN(noScheme, ":", 2)
	require.Len(t, parts, 2, "httptest URL should be host:port")
	n := 0
	for i := 0; i < len(parts[1]); i++ {
		ch := parts[1][i]
		if ch < '0' || ch > '9' {
			break
		}
		n = n*10 + int(ch-'0')
	}
	return parts[0], n
}

// Wave 0 RED test stub — references checkpoint.NewLiveCollector which does
// not exist yet. Plan 11-10 lands the production code; this test is
// intentionally compile-RED until then.
//
// Pattern source: agent/internal/netconf/collector_test.go (httptest pattern)
// CONTEXT.md D-14: login-per-pull, logout-when-done.
package checkpoint

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"

	"github.com/stretchr/testify/require"
)

// TestLiveCollector_LoginPullLogout: the canonical D-14 lifecycle.
//  1. POST /web_api/login → 200 + sid in body
//  2. POST /web_api/show-access-rulebase (and equivalents) → 200 + fixture
//  3. POST /web_api/logout → 200
// Asserts the SID never appears in any log line emitted by the collector.
//
// RED: references NewLiveCollector + LiveCollector.Pull which do not exist.
func TestLiveCollector_LoginPullLogout(t *testing.T) {
	loginJSON := mustReadFixture(t, "ckp-login.json")
	var loginResp map[string]any
	require.NoError(t, json.Unmarshal(loginJSON, &loginResp))
	expectSID := loginResp["sid"].(string)

	var (
		loginHits  atomic.Int32
		logoutHits atomic.Int32
		sidsSeen   atomic.Int32
	)
	mux := http.NewServeMux()
	mux.HandleFunc("/web_api/login", func(w http.ResponseWriter, _ *http.Request) {
		loginHits.Add(1)
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(loginJSON)
	})
	mux.HandleFunc("/web_api/show-access-rulebase", func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("X-chkp-sid") == expectSID {
			sidsSeen.Add(1)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(mustReadFixture(t, "ckp-access-rulebase.json"))
	})
	mux.HandleFunc("/web_api/show-nat-rulebase", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(mustReadFixture(t, "ckp-nat-rulebase.json"))
	})
	mux.HandleFunc("/web_api/show-objects", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(mustReadFixture(t, "ckp-objects.json"))
	})
	mux.HandleFunc("/web_api/logout", func(w http.ResponseWriter, _ *http.Request) {
		logoutHits.Add(1)
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"message":"OK"}`))
	})
	srv := httptest.NewServer(mux)
	defer srv.Close()

	// Capture any log output for SID-leakage check.
	var logBuf bytes.Buffer
	c := NewLiveCollectorWithLogger(srv.Client(), &logBuf)
	host, port := hostPortOf(t, srv.URL)
	_, _, _, err := c.Pull(context.Background(), host, port, "admin", "secret")
	require.NoError(t, err)

	require.Equal(t, int32(1), loginHits.Load(), "exactly one login per pull (D-14)")
	require.Equal(t, int32(1), logoutHits.Load(), "exactly one logout per pull (D-14)")
	require.GreaterOrEqual(t, sidsSeen.Load(), int32(1), "SID must be sent on at least one show-* request")

	// Critical: SID never appears in any log line (T-11 logging mitigation).
	logText := logBuf.String()
	require.False(t, strings.Contains(logText, expectSID),
		"SECURITY: SID %q must NEVER appear in logs; got log dump: %q", expectSID, logText)
}

// TestLiveCollector_Paginates: Checkpoint mgmt_cli paginates at 500 rules
// per page via `offset`/`limit`. Collector must keep pulling until exhausted.
//
// RED: references NewLiveCollector + LiveCollector.Pull which do not exist.
func TestLiveCollector_Paginates(t *testing.T) {
	loginJSON := mustReadFixture(t, "ckp-login.json")
	var page atomic.Int32

	mux := http.NewServeMux()
	mux.HandleFunc("/web_api/login", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(loginJSON)
	})
	mux.HandleFunc("/web_api/show-access-rulebase", func(w http.ResponseWriter, r *http.Request) {
		curr := page.Add(1)
		body, _ := io.ReadAll(r.Body)
		_ = body
		w.Header().Set("Content-Type", "application/json")
		base := string(mustReadFixture(t, "ckp-access-rulebase.json"))
		if curr == 1 {
			// First page: pretend there are more (`to < total`)
			out := strings.Replace(base, `"to": 3,`, `"to": 3,"more": true,`, 1)
			out = strings.Replace(out, `"total": 3`, `"total": 6`, 1)
			_, _ = w.Write([]byte(out))
			return
		}
		_, _ = w.Write([]byte(base))
	})
	mux.HandleFunc("/web_api/show-nat-rulebase", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(mustReadFixture(t, "ckp-nat-rulebase.json"))
	})
	mux.HandleFunc("/web_api/show-objects", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(mustReadFixture(t, "ckp-objects.json"))
	})
	mux.HandleFunc("/web_api/logout", func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{"message":"OK"}`))
	})
	srv := httptest.NewServer(mux)
	defer srv.Close()

	c := NewLiveCollector(srv.Client())
	host, port := hostPortOf(t, srv.URL)
	rules, _, _, err := c.Pull(context.Background(), host, port, "admin", "secret")
	require.NoError(t, err)
	require.GreaterOrEqual(t, page.Load(), int32(2), "pagination must walk all pages")
	require.GreaterOrEqual(t, len(rules), 6, "paginated total = 6 rules across 2 pages")
}

// -------- Helpers --------

func hostPortOf(t *testing.T, rawURL string) (string, int) {
	t.Helper()
	noScheme := strings.TrimPrefix(rawURL, "http://")
	noScheme = strings.TrimPrefix(noScheme, "https://")
	parts := strings.SplitN(noScheme, ":", 2)
	require.Len(t, parts, 2)
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

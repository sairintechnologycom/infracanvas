// Wave 0 RED test stub — references asa.NewRESTCollector / asa.RESTCollector
// which do not exist yet. Plan 11-05 lands the production code; this test
// is intentionally compile-RED until then.
//
// Pattern source: agent/internal/netconf/collector_test.go (httptest pattern)
// Fixture source: agent/internal/asa/testdata/asa-rest-{acl,nat,objects}.json
package asa

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
)

// TestRESTCollector_Pull: happy path against an httptest server serving the
// three canned fixtures. Asserts the collector returns parsed Rules, NATs,
// and Objects slices with at least the documented counts.
//
// RED: references NewRESTCollector + RESTCollector.Pull which do not exist.
func TestRESTCollector_Pull(t *testing.T) {
	aclJSON := mustReadFixture(t, "asa-rest-acl.json")
	natJSON := mustReadFixture(t, "asa-rest-nat.json")
	objsJSON := mustReadFixture(t, "asa-rest-objects.json")

	mux := http.NewServeMux()
	// Token acquisition: ASA REST uses POST /api/tokenservices.
	mux.HandleFunc("/api/tokenservices", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Auth-Token", "test-token-abc")
		w.WriteHeader(http.StatusNoContent)
	})
	mux.HandleFunc("/api/access/in/outside_in/rules", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(aclJSON)
	})
	mux.HandleFunc("/api/nat", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(natJSON)
	})
	mux.HandleFunc("/api/objects/networkobjects", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(objsJSON)
	})
	srv := httptest.NewTLSServer(mux)
	defer srv.Close()

	// Use the TLS server's client — its cert pool trusts the self-signed
	// httptest cert, so the collector's production InsecureSkipVerify=false
	// posture still holds in the test (mirrors prod TLS-validating dial).
	c := NewRESTCollector(srv.Client())
	host, port := hostPortOf(t, srv.URL)
	rules, nats, objs, err := c.Pull(context.Background(), host, port, "ro", "secret")
	require.NoError(t, err)
	require.GreaterOrEqual(t, len(rules), 3, "fixture has 3 access rules")
	require.GreaterOrEqual(t, len(nats), 2, "fixture has 2 NAT rules")
	require.GreaterOrEqual(t, len(objs), 3, "fixture has 3 network objects")
}

// TestRESTCollector_DisabledAPI: the ASA REST endpoint returns 401 when the
// `http server enable` line is missing from running-config. Collector must
// surface this as a non-retryable error (do not loop forever).
//
// RED: references NewRESTCollector + RESTCollector.Pull which do not exist.
func TestRESTCollector_DisabledAPI(t *testing.T) {
	srv := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
		_, _ = w.Write([]byte(`{"messages":[{"code":"UNAUTHORIZED","details":"http server not enabled"}]}`))
	}))
	defer srv.Close()

	c := NewRESTCollector(srv.Client())
	host, port := hostPortOf(t, srv.URL)
	_, _, _, err := c.Pull(context.Background(), host, port, "ro", "secret")
	require.Error(t, err)
	// Error must indicate non-retryable to the caller; the surface here is the
	// string "401" or "unauthorized". Plan 11-05 picks the canonical wording;
	// this assertion locks the requirement that it surfaces clearly.
	msg := strings.ToLower(err.Error())
	require.True(t,
		strings.Contains(msg, "401") || strings.Contains(msg, "unauthorized"),
		"non-retryable 401 must be visible in error message, got: %q", err.Error(),
	)
}

// -------- Helpers --------

func mustReadFixture(t *testing.T, name string) []byte {
	t.Helper()
	data, err := os.ReadFile(filepath.Join("testdata", name))
	require.NoError(t, err)
	return data
}

// hostPortOf splits an httptest.Server URL into (host, port).
func hostPortOf(t *testing.T, rawURL string) (string, int) {
	t.Helper()
	// strip scheme
	noScheme := strings.TrimPrefix(rawURL, "http://")
	noScheme = strings.TrimPrefix(noScheme, "https://")
	parts := strings.SplitN(noScheme, ":", 2)
	require.Len(t, parts, 2, "httptest URL should be host:port")
	var p int
	_, err := fmtSscanf(parts[1], "%d", &p)
	require.NoError(t, err)
	return parts[0], p
}

// fmtSscanf is a tiny indirection so we don't pull fmt into the top-level
// imports (keeps the imports list aligned with the netconf analog).
func fmtSscanf(s, f string, v *int) (int, error) {
	return sscanInt(s, v)
}

func sscanInt(s string, v *int) (int, error) {
	n := 0
	for i := 0; i < len(s); i++ {
		if s[i] < '0' || s[i] > '9' {
			return i, nil
		}
		n = n*10 + int(s[i]-'0')
	}
	*v = n
	return len(s), nil
}

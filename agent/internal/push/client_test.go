package push

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
	"go.uber.org/zap/zaptest"

	"github.com/infracanvas/infracanvas/agent/internal/netconf"
	"github.com/infracanvas/infracanvas/agent/internal/netflow"
)

func fastBackoff(attempt int) time.Duration {
	return time.Duration(attempt*50) * time.Millisecond
}

func sampleRoutesPayload() RoutesPayload {
	return RoutesPayload{
		SiteID:      "00000000-0000-0000-0000-000000000001",
		CollectedAt: "2026-05-07T10:00:00Z",
		DeviceHost:  "192.0.2.1",
		Routes: []netconf.RouteRecord{
			{Prefix: "10.0.0.0/8", NextHop: "192.168.1.254", Protocol: "bgp", Metric: 100},
		},
	}
}

func sampleFlowsPayload() FlowsPayload {
	return FlowsPayload{
		SiteID:      "00000000-0000-0000-0000-000000000001",
		CollectedAt: "2026-05-07T10:00:00Z",
		Flows: []netflow.FlowRecord{
			{SrcIP: "10.0.0.1", DstIP: "10.0.0.2", SrcPort: 1024, DstPort: 80, Protocol: 6, Bytes: 1500, Packets: 1},
		},
	}
}

func TestPushRoutes_Happy(t *testing.T) {
	var calls int32
	var capturedAuth, capturedBody string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&calls, 1)
		require.Equal(t, "/v1/agent/routes", r.URL.Path)
		require.Equal(t, http.MethodPost, r.Method)
		capturedAuth = r.Header.Get("Authorization")
		buf := make([]byte, 4096)
		n, _ := r.Body.Read(buf)
		capturedBody = string(buf[:n])
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "ic_site_xxx", zaptest.NewLogger(t))
	c.SetBackoff(fastBackoff)
	err := c.PushRoutes(context.Background(), sampleRoutesPayload())
	require.NoError(t, err)
	require.Equal(t, int32(1), atomic.LoadInt32(&calls))
	require.Equal(t, "Bearer ic_site_xxx", capturedAuth)
	require.Contains(t, capturedBody, `"site_id":"00000000-0000-0000-0000-000000000001"`)
	require.Contains(t, capturedBody, `"device_host":"192.0.2.1"`)
	require.Contains(t, capturedBody, `"prefix":"10.0.0.0/8"`)
}

func TestPushFlows_Happy(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		require.Equal(t, "/v1/agent/flows", r.URL.Path)
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "tk", zaptest.NewLogger(t))
	c.SetBackoff(fastBackoff)
	require.NoError(t, c.PushFlows(context.Background(), sampleFlowsPayload()))
}

func TestPushRoutes_RetryOn5xx(t *testing.T) {
	var calls int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		n := atomic.AddInt32(&calls, 1)
		if n < 3 {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "tk", zaptest.NewLogger(t))
	c.SetBackoff(fastBackoff)
	require.NoError(t, c.PushRoutes(context.Background(), sampleRoutesPayload()))
	require.Equal(t, int32(3), atomic.LoadInt32(&calls))
}

func TestPushRoutes_DropsAfterRetries(t *testing.T) {
	var calls int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&calls, 1)
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "tk", zaptest.NewLogger(t))
	c.SetBackoff(fastBackoff)
	// D-07: drop-and-continue — returns nil error even though all 3 attempts failed.
	require.NoError(t, c.PushRoutes(context.Background(), sampleRoutesPayload()))
	require.Equal(t, int32(3), atomic.LoadInt32(&calls))
}

func TestPushRoutes_NoRetryOn401(t *testing.T) {
	var calls int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&calls, 1)
		w.WriteHeader(http.StatusUnauthorized)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "tk", zaptest.NewLogger(t))
	c.SetBackoff(fastBackoff)
	err := c.PushRoutes(context.Background(), sampleRoutesPayload())
	require.Error(t, err)
	require.Contains(t, err.Error(), "401")
	require.Equal(t, int32(1), atomic.LoadInt32(&calls), "401 must not retry")
}

func TestPushRoutes_NoRetryOn422(t *testing.T) {
	var calls int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&calls, 1)
		w.WriteHeader(http.StatusUnprocessableEntity)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "tk", zaptest.NewLogger(t))
	c.SetBackoff(fastBackoff)
	err := c.PushRoutes(context.Background(), sampleRoutesPayload())
	require.Error(t, err)
	require.Contains(t, err.Error(), "422")
	require.Equal(t, int32(1), atomic.LoadInt32(&calls), "422 must not retry")
}

// Slow test — uses production linearBackoff to regression-lock the 2s timing.
func TestPushRoutes_BackoffTiming(t *testing.T) {
	if testing.Short() {
		t.Skip("backoff timing test skipped in -short mode")
	}
	var calls int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		n := atomic.AddInt32(&calls, 1)
		if n == 1 {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "tk", zaptest.NewLogger(t))
	// Production backoff in this test ONLY.
	start := time.Now()
	require.NoError(t, c.PushRoutes(context.Background(), sampleRoutesPayload()))
	elapsed := time.Since(start)
	require.GreaterOrEqual(t, elapsed, 2*time.Second, "backoff must wait 2s before retry 1")
	require.Less(t, elapsed, 4*time.Second, "backoff must NOT wait 4s when retry 1 succeeds")
}

func TestPushRoutes_BearerHeaderShape(t *testing.T) {
	var seenAuth string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seenAuth = r.Header.Get("Authorization")
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "ic_site_token_xyz", zaptest.NewLogger(t))
	c.SetBackoff(fastBackoff)
	require.NoError(t, c.PushRoutes(context.Background(), sampleRoutesPayload()))
	require.True(t, strings.HasPrefix(seenAuth, "Bearer "), "header must start with 'Bearer '")
	require.Equal(t, "Bearer ic_site_token_xyz", seenAuth)
}

func TestPushRoutes_JSONShape(t *testing.T) {
	var captured RoutesPayload
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		require.NoError(t, json.NewDecoder(r.Body).Decode(&captured))
		w.WriteHeader(http.StatusAccepted)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "tk", zaptest.NewLogger(t))
	c.SetBackoff(fastBackoff)
	require.NoError(t, c.PushRoutes(context.Background(), sampleRoutesPayload()))
	require.Equal(t, "00000000-0000-0000-0000-000000000001", captured.SiteID)
	require.Equal(t, "192.0.2.1", captured.DeviceHost)
	require.Len(t, captured.Routes, 1)
	require.Equal(t, "10.0.0.0/8", captured.Routes[0].Prefix)
}

// TestPushClient alias matches 10-VALIDATION.md verify command.
func TestPushClient(t *testing.T) { TestPushRoutes_Happy(t) }

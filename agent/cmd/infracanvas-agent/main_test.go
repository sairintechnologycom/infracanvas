package main

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
	"go.uber.org/zap/zaptest"

	"github.com/infracanvas/infracanvas/agent/internal/config"
	"github.com/infracanvas/infracanvas/agent/internal/netflow"
	"github.com/infracanvas/infracanvas/agent/internal/push"
)

const minimalYAML = `
site_token: "ic_site_test"
backend_url: "https://example.invalid"
devices: []
`

func writeMinimalConfig(t *testing.T) string {
	t.Helper()
	f := filepath.Join(t.TempDir(), "agent.yaml")
	require.NoError(t, os.WriteFile(f, []byte(minimalYAML), 0o600))
	return f
}

// TestDaemonStartStop: runDaemonWithIntervals returns nil within 200ms when
// ctx is cancelled; verifies graceful shutdown contract.
func TestDaemonStartStop(t *testing.T) {
	cfg, err := config.Load(writeMinimalConfig(t))
	require.NoError(t, err)
	log := zaptest.NewLogger(t)

	ctx, cancel := context.WithCancel(context.Background())
	// Use very small intervals so tickers definitely fire at least once before cancel.
	// PHASE 11 — Firewall must be non-zero (time.NewTicker(0) panics).
	iv := Intervals{
		Routes:   50 * time.Millisecond,
		BGP:      50 * time.Millisecond,
		Flow:     50 * time.Millisecond,
		Firewall: 50 * time.Millisecond,
	}

	done := make(chan error, 1)
	go func() {
		done <- runDaemonWithIntervals(ctx, cfg, iv, log,
			netflow.NewRingBuffer(10), &fakePusher{})
	}()

	time.Sleep(120 * time.Millisecond) // allow at least 2 tick fires
	cancel()

	select {
	case err := <-done:
		require.NoError(t, err)
	case <-time.After(2 * time.Second):
		t.Fatal("runDaemonWithIntervals did not return within 2s after cancel")
	}
}

// TestDefaultIntervals locks the DCA-06 timing contract for routes/BGP/flow
// AND the Phase 11 D-02 extension that adds Firewall=1h as the 4th interval.
// EXTENDED — not replaced — per Plan 11-01 acceptance criteria (the 3-interval
// assertions stay; the 4th assertion is appended).
func TestDefaultIntervals(t *testing.T) {
	iv := defaultIntervals()
	require.Equal(t, 5*time.Minute, iv.Routes, "routes ticker must be 5min per DCA-06")
	require.Equal(t, 1*time.Minute, iv.BGP, "BGP ticker must be 1min per DCA-06")
	require.Equal(t, 30*time.Second, iv.Flow, "NetFlow flush must be 30s per DCA-06")
	require.Equal(t, 1*time.Hour, iv.Firewall, "Phase 11 D-02: 4th interval Firewall=1h")
}

// TestRunDaemon_FirewallTick (Phase 11 D-03): asserts the 4th ticker fires
// collectAndPushFirewall on tick and that ctx cancel drains the in-flight
// goroutine before runDaemonWithIntervals returns.
//
// Plan 11-07 lands collectAndPushFirewall as a STUB that only emits a
// log.Debug — it does NOT call the pusher yet. So the assertion here is
// "no panic, clean shutdown, run returns nil within 2s of cancel". Plan
// 11-12 (Wave 4) will fill in real per-protocol dispatch and tighten this
// test to assert pusher.firewallRulesCount > 0.
func TestRunDaemon_FirewallTick(t *testing.T) {
	cfg, err := config.Load(writeMinimalConfig(t))
	require.NoError(t, err)
	log := zaptest.NewLogger(t)

	iv := Intervals{
		Routes:   1 * time.Hour, // suppress in test
		BGP:      1 * time.Hour,
		Flow:     1 * time.Hour,
		Firewall: 10 * time.Millisecond, // fire fast
	}

	ctx, cancel := context.WithCancel(context.Background())
	pusher := &fakePusher{}

	done := make(chan error, 1)
	go func() {
		done <- runDaemonWithIntervals(ctx, cfg, iv, log,
			netflow.NewRingBuffer(10), pusher)
	}()

	// Allow at least a few firewall ticks to fire.
	time.Sleep(80 * time.Millisecond)
	cancel()

	select {
	case err := <-done:
		require.NoError(t, err, "daemon must return nil after ctx cancel")
	case <-time.After(2 * time.Second):
		t.Fatal("runDaemonWithIntervals did not return within 2s after cancel — firewall goroutine leak?")
	}

	// Plan 11-07 stub asserts shutdown drain only. Plan 11-12 will tighten:
	//   require.Greater(t, pusher.firewallRulesCount, 0)
	// Counter field exists today (fakePusher Plan 11-07) so the tightening
	// is a 1-line change once collectAndPushFirewall stops being a no-op.
}

// TestVersionCommand: invoking `version` prints the package-level version var.
func TestVersionCommand(t *testing.T) {
	cmd := newRootCmd()
	var out bytes.Buffer
	cmd.SetOut(&out)
	cmd.SetArgs([]string{"version"})
	require.NoError(t, cmd.Execute())
	require.Equal(t, "dev\n", out.String())
}

// TestRunRequiresConfig: `run --config /no/such/file` returns config-read error.
func TestRunRequiresConfig(t *testing.T) {
	cmd := newRootCmd()
	var stderr bytes.Buffer
	cmd.SetErr(&stderr)
	cmd.SetOut(&bytes.Buffer{})
	cmd.SetArgs([]string{"run", "--config", "/no/such/file/agent.yaml"})
	err := cmd.Execute()
	require.Error(t, err)
	require.Contains(t, err.Error(), "config: read")
}

// Avoid unused import warning if zap isn't otherwise referenced.
var _ = zap.NewNop

// -------- Test fakes for the wiring tests --------

type fakePusher struct {
	mu                   sync.Mutex
	routes               []push.RoutesPayload
	flows                []push.FlowsPayload
	firewallRules        []push.FirewallRulesPayload
	firewallNAT          []push.FirewallNATPayload
	firewallObjects      []push.FirewallObjectsPayload
	firewallRulesCount   int
	firewallNATCount     int
	firewallObjectsCount int
	err                  error
}

func (f *fakePusher) PushRoutes(_ context.Context, p push.RoutesPayload) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.routes = append(f.routes, p)
	return f.err
}
func (f *fakePusher) PushFlows(_ context.Context, p push.FlowsPayload) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.flows = append(f.flows, p)
	return f.err
}

// PHASE 11 — three firewall push methods. Plan 11-07 stub increments counters
// only; Plan 11-12 will fill in real per-protocol dispatch and tighten
// TestRunDaemon_FirewallTick to assert counters > 0.
func (f *fakePusher) PushFirewallRules(_ context.Context, p push.FirewallRulesPayload) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.firewallRules = append(f.firewallRules, p)
	f.firewallRulesCount++
	return f.err
}
func (f *fakePusher) PushFirewallNAT(_ context.Context, p push.FirewallNATPayload) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.firewallNAT = append(f.firewallNAT, p)
	f.firewallNATCount++
	return f.err
}
func (f *fakePusher) PushFirewallObjects(_ context.Context, p push.FirewallObjectsPayload) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.firewallObjects = append(f.firewallObjects, p)
	f.firewallObjectsCount++
	return f.err
}

func TestCollectAndPushRoutes_ConfigImport(t *testing.T) {
	dir := t.TempDir()
	rfile := filepath.Join(dir, "routes.yaml")
	require.NoError(t, os.WriteFile(rfile,
		[]byte("routes:\n  - {prefix: \"10.0.0.0/8\", next_hop: \"192.168.1.1\", protocol: static, metric: 1}\n"),
		0o600))

	cfg := &config.Config{
		SiteToken:  "tk",
		BackendURL: "http://x",
		Devices: []config.Device{
			{Host: "sw-core", Protocol: config.ProtocolConfigImport, ConfigFile: rfile, SiteID: "site-1"},
		},
	}
	pusher := &fakePusher{}
	collectAndPushRoutes(context.Background(), cfg, pusher, zaptest.NewLogger(t))

	require.Len(t, pusher.routes, 1)
	require.Equal(t, "site-1", pusher.routes[0].SiteID)
	require.Equal(t, "sw-core", pusher.routes[0].DeviceHost)
	require.Len(t, pusher.routes[0].Routes, 1)
	require.Equal(t, "10.0.0.0/8", pusher.routes[0].Routes[0].Prefix)
}

func TestFlushFlowBuffer_Drains(t *testing.T) {
	rb := netflow.NewRingBuffer(10)
	rb.Append([]netflow.FlowRecord{
		{SrcIP: "a", DstIP: "b", Protocol: 6, Bytes: 100, Packets: 1},
		{SrcIP: "c", DstIP: "d", Protocol: 17, Bytes: 200, Packets: 2},
		{SrcIP: "e", DstIP: "f", Protocol: 6, Bytes: 300, Packets: 3},
	})

	cfg := &config.Config{Devices: []config.Device{{SiteID: "site-9"}}}
	pusher := &fakePusher{}
	flushFlowBuffer(context.Background(), cfg, rb, pusher, zaptest.NewLogger(t))

	require.Len(t, pusher.flows, 1)
	require.Equal(t, "site-9", pusher.flows[0].SiteID)
	require.Len(t, pusher.flows[0].Flows, 3)
	require.Equal(t, 0, rb.Len(), "Drain must reset the buffer")
}

func TestFlushFlowBuffer_EmptyNoOp(t *testing.T) {
	rb := netflow.NewRingBuffer(10)
	cfg := &config.Config{Devices: []config.Device{{SiteID: "site-9"}}}
	pusher := &fakePusher{}
	flushFlowBuffer(context.Background(), cfg, rb, pusher, zaptest.NewLogger(t))
	require.Len(t, pusher.flows, 0, "empty buffer should not push")
}

func TestCollectorFor_UnsupportedProtocolReturnsNil(t *testing.T) {
	require.Nil(t, collectorFor(config.Device{Protocol: "unknown"}))
}

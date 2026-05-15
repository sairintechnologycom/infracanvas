package main

import (
	"bytes"
	"context"
	"fmt"
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

// Minimal Checkpoint mgmt_cli --format json exports — enough for the shared
// parser to emit at least one push.FirewallRule so TestRunDaemon_FirewallTick
// can observe the firewall ticker pushing into fakePusher counters.
const checkpointImportRulebaseJSON = `{"uid":"p","name":"P","rulebase":[{"uid":"r1","name":"Allow-Test","type":"access-rule","rule-number":1,"enabled":true,"source":[{"uid":"any","name":"Any"}],"destination":[{"uid":"any","name":"Any"}],"service":[{"uid":"any","name":"Any"}],"action":{"uid":"a","name":"Accept"},"track":{"type":{"name":"Log"}}}]}`
const checkpointImportNATJSON = `{"uid":"n","name":"N","rulebase":[]}`
const checkpointImportObjectsJSON = `{"objects":[]}`

// writeCheckpointImportConfig stages a temp dir containing the three offline
// Checkpoint export JSON files (base + .rulebase.json / .nat.json / .objects.json)
// and an agent.yaml with a single checkpoint-import device pointing at the
// base. The dispatcher's checkpointImportPaths helper resolves the three
// siblings via the base-prefix convention from Plan 11-12.
func writeCheckpointImportConfig(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	base := filepath.Join(dir, "ckp")
	require.NoError(t, os.WriteFile(base+".rulebase.json", []byte(checkpointImportRulebaseJSON), 0o600))
	require.NoError(t, os.WriteFile(base+".nat.json", []byte(checkpointImportNATJSON), 0o600))
	require.NoError(t, os.WriteFile(base+".objects.json", []byte(checkpointImportObjectsJSON), 0o600))

	cfgYAML := fmt.Sprintf(`
site_token: "ic_site_test"
backend_url: "https://example.invalid"
devices:
  - host: "ckp-mgmt-import"
    protocol: "checkpoint-import"
    config_file: %q
    site_id: "site-test"
`, base)
	cfgPath := filepath.Join(dir, "agent.yaml")
	require.NoError(t, os.WriteFile(cfgPath, []byte(cfgYAML), 0o600))
	return cfgPath
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
// collectAndPushFirewall on tick AND that the dispatcher actually pushes
// payloads via the pusher interface. The test uses a checkpoint-import
// device (no network, deterministic) so the dispatcher exercises the
// checkpoint.LoadImport branch + the three sequential PushFirewall* calls
// with a shared snapshot_id (Plan 11-12 Wave 4 contract).
//
// Plan 11-07 landed collectAndPushFirewall as a noop stub. Plan 11-12 fills
// the body; this test was tightened from "no panic" to require pusher
// counters > 0 to lock the dispatcher actually wires through.
func TestRunDaemon_FirewallTick(t *testing.T) {
	cfg, err := config.Load(writeCheckpointImportConfig(t))
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

	// Plan 11-12 dispatcher must wire LoadImport → 3 PushFirewall* calls
	// per tick with a shared snapshot_id. Assert all three counters fire.
	pusher.mu.Lock()
	defer pusher.mu.Unlock()
	require.Greater(t, pusher.firewallRulesCount, 0,
		"firewall dispatcher must push rules (Plan 11-12 GREEN)")
	require.Greater(t, pusher.firewallNATCount, 0,
		"firewall dispatcher must push NAT (Plan 11-12 GREEN)")
	require.Greater(t, pusher.firewallObjectsCount, 0,
		"firewall dispatcher must push objects (Plan 11-12 GREEN)")
	// Shared snapshot_id across the 3 payloads (RESEARCH Pattern 2, D-08).
	require.NotEmpty(t, pusher.firewallRules[0].SnapshotID,
		"snapshot_id must be minted per tick")
	require.Equal(t, pusher.firewallRules[0].SnapshotID, pusher.firewallNAT[0].SnapshotID,
		"rules + NAT must share the same per-device snapshot_id")
	require.Equal(t, pusher.firewallRules[0].SnapshotID, pusher.firewallObjects[0].SnapshotID,
		"rules + objects must share the same per-device snapshot_id")
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

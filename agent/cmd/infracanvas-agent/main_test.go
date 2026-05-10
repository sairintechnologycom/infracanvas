package main

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
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
	iv := Intervals{Routes: 50 * time.Millisecond, BGP: 50 * time.Millisecond, Flow: 50 * time.Millisecond}

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

// TestTickerIntervals locks the DCA-06 timing contract.
func TestTickerIntervals(t *testing.T) {
	iv := defaultIntervals()
	require.Equal(t, 5*time.Minute, iv.Routes, "routes ticker must be 5min per DCA-06")
	require.Equal(t, 1*time.Minute, iv.BGP, "BGP ticker must be 1min per DCA-06")
	require.Equal(t, 30*time.Second, iv.Flow, "NetFlow flush must be 30s per DCA-06")
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
	routes []push.RoutesPayload
	flows  []push.FlowsPayload
	err    error
}

func (f *fakePusher) PushRoutes(_ context.Context, p push.RoutesPayload) error {
	f.routes = append(f.routes, p)
	return f.err
}
func (f *fakePusher) PushFlows(_ context.Context, p push.FlowsPayload) error {
	f.flows = append(f.flows, p)
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

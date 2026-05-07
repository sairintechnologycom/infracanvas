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
	go func() { done <- runDaemonWithIntervals(ctx, cfg, iv, log) }()

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

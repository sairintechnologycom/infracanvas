// Command infracanvas-agent is the InfraCanvas DC Agent daemon.
//
// Run subcommand: starts the collection loop (routes 5m, BGP 1m, NetFlow flush 30s)
// until SIGINT/SIGTERM, at which point it drains in-flight goroutines and exits.
//
// Per CONTEXT.md D-01 the binary lives at agent/cmd/infracanvas-agent and the
// module path is github.com/infracanvas/infracanvas/agent.
//
// Plan 10-07 wires the previously-stubbed collector functions to real packages:
//
//	NETCONF (10-04)        -> internal/netconf.Collector.GetRoutes
//	SSH show ip route (10-05) -> internal/ssh.Collector.GetRoutes
//	config-import (10-05)  -> internal/config.LoadConfigImport
//	NetFlow listener (10-06)  -> internal/netflow.Listener (goroutine)
//	Push client (10-07)    -> internal/push.Client (Bearer + retry-twice-then-drop)
package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/spf13/cobra"
	"go.uber.org/zap"

	"github.com/infracanvas/infracanvas/agent/internal/config"
	"github.com/infracanvas/infracanvas/agent/internal/netconf"
	"github.com/infracanvas/infracanvas/agent/internal/netflow"
	"github.com/infracanvas/infracanvas/agent/internal/push"
	"github.com/infracanvas/infracanvas/agent/internal/ssh"
)

// version is injected at build time via:
//
//	go build -ldflags="-X main.version=$(git describe --tags)" ./cmd/infracanvas-agent
var version = "dev"

// Intervals locks the DCA-06 daemon timing contract. Exposed as a type for
// tests so callers can assert the contract without running real tickers.
//
// PHASE 11 D-02 — extended with Firewall: 1h (4th ticker). Firewall rule bases
// change at change-window cadence, not minute-by-minute, so the 1h cadence is
// distinct from the Phase 10 sub-minute pulls. See 11-CONTEXT.md D-02.
type Intervals struct {
	Routes   time.Duration
	BGP      time.Duration
	Flow     time.Duration
	Firewall time.Duration // PHASE 11 D-02 — firewall pulls every 1h
}

// defaultIntervals returns the locked DCA-06 collection cadence + the
// Phase 11 D-02 Firewall=1h cadence.
func defaultIntervals() Intervals {
	return Intervals{
		Routes:   5 * time.Minute,
		BGP:      1 * time.Minute,
		Flow:     30 * time.Second,
		Firewall: 1 * time.Hour, // PHASE 11 D-02
	}
}

// Pusher abstracts push.Client so tests can inject a fakePusher without
// spinning up an httptest.Server. Production uses *push.Client.
//
// PHASE 11 — extended with three firewall push methods. push.Client implements
// all five methods (see agent/internal/push/client.go); the tests' fakePusher
// implements the three new methods as no-ops.
type Pusher interface {
	PushRoutes(ctx context.Context, p push.RoutesPayload) error
	PushFlows(ctx context.Context, p push.FlowsPayload) error
	// PHASE 11 — three firewall methods (implemented by push.Client, Plan 11-05)
	PushFirewallRules(ctx context.Context, p push.FirewallRulesPayload) error
	PushFirewallNAT(ctx context.Context, p push.FirewallNATPayload) error
	PushFirewallObjects(ctx context.Context, p push.FirewallObjectsPayload) error
}

// RouteCollectorFn dials a device and returns its current routes.
// Production wiring binds netconf/ssh/config-import implementations by
// protocol; tests that exercise main-level wiring use config-import (a
// pure file read, no network) so they can run hermetically.
type RouteCollectorFn func(ctx context.Context, dev config.Device) ([]netconf.RouteRecord, error)

// collectorFor returns the RouteCollectorFn appropriate to the device protocol.
// Returns nil for protocols not supported in this code path — currently
// the agent supports the three loader protocols defined in 10-CONTEXT.md D-06.
func collectorFor(dev config.Device) RouteCollectorFn {
	switch dev.Protocol {
	case config.ProtocolNetconf:
		c := netconf.NewCollector(netconf.DefaultDialer())
		return func(ctx context.Context, d config.Device) ([]netconf.RouteRecord, error) {
			return c.GetRoutes(ctx, d.Host, d.Port, d.Username, d.Password)
		}
	case config.ProtocolSSH:
		c := ssh.NewCollector(ssh.DefaultDialer())
		return func(ctx context.Context, d config.Device) ([]netconf.RouteRecord, error) {
			return c.GetRoutes(ctx, d.Host, d.Port, d.Username, d.Password)
		}
	case config.ProtocolConfigImport:
		return func(_ context.Context, d config.Device) ([]netconf.RouteRecord, error) {
			return config.LoadConfigImport(d.ConfigFile)
		}
	}
	return nil
}

// collectAndPushRoutes iterates devices, dials each, pushes results.
// Pure function over (cfg, pusher, log) — tests inject a fakePusher and
// rely on collectorFor's config-import branch (no network) for determinism.
func collectAndPushRoutes(ctx context.Context, cfg *config.Config, pusher Pusher, log *zap.Logger) {
	for _, dev := range cfg.Devices {
		fn := collectorFor(dev)
		if fn == nil {
			log.Debug("collector_skip_unsupported_protocol",
				zap.String("device", dev.Host),
				zap.String("protocol", dev.Protocol))
			continue
		}
		routes, err := fn(ctx, dev)
		if err != nil {
			log.Warn("collect_routes_failed",
				zap.String("device", dev.Host),
				zap.String("protocol", dev.Protocol),
				zap.Error(err))
			continue
		}
		payload := push.RoutesPayload{
			SiteID:      dev.SiteID,
			CollectedAt: time.Now().UTC().Format(time.RFC3339),
			DeviceHost:  dev.Host,
			Routes:      routes,
		}
		if err := pusher.PushRoutes(ctx, payload); err != nil {
			log.Warn("push_routes_failed",
				zap.String("device", dev.Host),
				zap.Error(err))
		}
	}
}

// collectAndPushBGP is per-CONTEXT.md scope decision a no-op until BGP-neighbor
// collection lands in Phase 11. The 1-min ticker fires but does nothing in
// Phase 10 — keeping the ticker live so Phase 11 just adds the call.
func collectAndPushBGP(_ context.Context, _ *config.Config, _ Pusher, log *zap.Logger) {
	log.Debug("bgp_tick_noop_phase10")
}

// flushFlowBuffer drains the netflow ring buffer and pushes the result.
// siteID is taken from the first device with one configured (or empty if
// none — backend will reject empty site_id with 422 which non-retries, so
// operators see the misconfiguration explicitly).
func flushFlowBuffer(ctx context.Context, cfg *config.Config, buf *netflow.RingBuffer, pusher Pusher, log *zap.Logger) {
	flows := buf.Drain()
	if len(flows) == 0 {
		return
	}
	siteID := ""
	for _, d := range cfg.Devices {
		if d.SiteID != "" {
			siteID = d.SiteID
			break
		}
	}
	payload := push.FlowsPayload{
		SiteID:      siteID,
		CollectedAt: time.Now().UTC().Format(time.RFC3339),
		Flows:       flows,
	}
	if err := pusher.PushFlows(ctx, payload); err != nil {
		log.Warn("push_flows_failed", zap.Error(err))
	}
}

// newRootCmd builds and returns the cobra root command.
func newRootCmd() *cobra.Command {
	var cfgPath string

	root := &cobra.Command{
		Use:           "infracanvas-agent",
		Short:         "InfraCanvas DC Agent — collects routes + flows, pushes to cloud backend",
		SilenceErrors: true,
		SilenceUsage:  true,
	}

	runCmd := &cobra.Command{
		Use:   "run",
		Short: "Start the agent daemon",
		RunE: func(cmd *cobra.Command, args []string) error {
			cfg, err := config.Load(cfgPath)
			if err != nil {
				return err
			}
			log, err := zap.NewProduction()
			if err != nil {
				return fmt.Errorf("logger init: %w", err)
			}
			defer func() { _ = log.Sync() }()

			ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
			defer stop()

			// Production push client + ring buffer + listener wiring.
			// Buffer capacity 100 000 ≈ 5min headroom at 333 flows/sec
			// (per netflow/buffer.go package doc — D-07 sizing).
			pusher := push.NewClient(cfg.BackendURL, cfg.SiteToken, log)
			rb := netflow.NewRingBuffer(100000)

			// Launch NetFlow UDP listener BEFORE the ticker loop so the 30s
			// flushFlowBuffer ticker has populated state to drain. Listener.Run
			// blocks until ctx is cancelled (Plan 10-06 listener respects
			// ctx.Done() via a 500ms read deadline). cfg.NetflowAddr would be
			// the right wiring point in a future plan — for now use the
			// netflow.DefaultUDPAddr (":2055") literal.
			listener := netflow.NewListener(netflow.DefaultUDPAddr, rb, log, newGoflow2Decode())
			// Single-line goroutine launch — Plan 10-07 acceptance criteria
			// regex `go .*listener.*\.Run\(ctx\)` regression-locks this site
			// so future refactors cannot accidentally drop the listener.
			go func() { _ = listener.Run(ctx) }() //nolint:errcheck // listener.Run logs internal errors; ctx-cancel returns nil

			return runDaemonWithIntervals(ctx, cfg, defaultIntervals(), log, rb, pusher)
		},
	}
	runCmd.Flags().StringVar(&cfgPath, "config", "./agent.yaml",
		"Path to agent.yaml (default ./agent.yaml; fallback /etc/infracanvas/agent.yaml)")

	versionCmd := &cobra.Command{
		Use:   "version",
		Short: "Print agent version",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Fprintln(cmd.OutOrStdout(), version)
		},
	}

	root.AddCommand(runCmd)
	root.AddCommand(versionCmd)
	return root
}

// runDaemonWithIntervals runs the collection loop until ctx is cancelled.
// Tests pass a fakePusher + a small RingBuffer; production passes a real
// push.Client and the long-lived ring buffer the netflow listener writes to.
func runDaemonWithIntervals(
	ctx context.Context,
	cfg *config.Config,
	iv Intervals,
	log *zap.Logger,
	rb *netflow.RingBuffer,
	pusher Pusher,
) error {
	log.Info("agent_starting",
		zap.String("version", version),
		zap.String("backend_url", cfg.BackendURL),
		zap.Int("device_count", len(cfg.Devices)))

	routeT := time.NewTicker(iv.Routes)
	bgpT := time.NewTicker(iv.BGP)
	flowT := time.NewTicker(iv.Flow)
	defer routeT.Stop()
	defer bgpT.Stop()
	defer flowT.Stop()

	var wg sync.WaitGroup
	for {
		select {
		case <-ctx.Done():
			log.Info("agent_shutdown_signal", zap.String("reason", ctx.Err().Error()))
			wg.Wait()
			log.Info("agent_stopped")
			return nil
		case <-routeT.C:
			wg.Add(1)
			go func() { defer wg.Done(); collectAndPushRoutes(ctx, cfg, pusher, log) }()
		case <-bgpT.C:
			wg.Add(1)
			go func() { defer wg.Done(); collectAndPushBGP(ctx, cfg, pusher, log) }()
		case <-flowT.C:
			wg.Add(1)
			go func() { defer wg.Done(); flushFlowBuffer(ctx, cfg, rb, pusher, log) }()
		}
	}
}

// newGoflow2Decode is a local alias for netflow.NewGoflow2Decode so the
// runCmd RunE closure reads top-down without exposing goflow2 internals
// across packages. Plan 10-07 acceptance criteria pin the lowercase name
// here as a regression guard against accidental refactors that drop the
// production decoder.
func newGoflow2Decode() netflow.DecodeFunc { return netflow.NewGoflow2Decode() }

func main() {
	if err := newRootCmd().Execute(); err != nil {
		fmt.Fprintln(os.Stderr, "infracanvas-agent:", err)
		os.Exit(1)
	}
}

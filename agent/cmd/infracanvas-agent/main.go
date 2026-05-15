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
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/google/uuid"
	"github.com/spf13/cobra"
	"go.uber.org/zap"

	"github.com/infracanvas/infracanvas/agent/internal/asa"
	"github.com/infracanvas/infracanvas/agent/internal/checkpoint"
	"github.com/infracanvas/infracanvas/agent/internal/config"
	"github.com/infracanvas/infracanvas/agent/internal/fmc"
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

// firewallPuller pulls one snapshot of rules + NAT + objects for one device.
// Returned by firewallCollectorFor; nil for non-firewall protocols. Pattern H:
// the closure passes primitives (host/port/user/pass) to the vendor Pull
// method — never the config.Device, which would import-cycle into the
// vendor packages.
type firewallPuller func(ctx context.Context, dev config.Device) (
	[]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error,
)

// firewallHTTPClient returns the http.Client used by the Wave 3 REST
// collectors. Single stdlib client with TLS validation against the system
// trust store and a 60s overall timeout. Per-call clients are fine here —
// the firewall ticker fires once per hour in production, so no connection
// pooling benefit to share across devices.
func firewallHTTPClient() *http.Client {
	return &http.Client{Timeout: 60 * time.Second}
}

// checkpointImportPaths resolves the three sibling JSON files (rulebase, NAT,
// objects) from dev.ConfigFile. Two operator conventions are accepted:
//
//   - dev.ConfigFile ends in ".rulebase.json" → treat as the rulebase path
//     and derive .nat.json / .objects.json siblings by trimming the suffix.
//   - else → treat dev.ConfigFile as a base prefix; append the three
//     extensions verbatim (e.g. base "/etc/infracanvas/ckp" →
//     /etc/infracanvas/ckp.rulebase.json + .nat.json + .objects.json).
//
// Plan 11-13 operator runbook surfaces this convention.
func checkpointImportPaths(base string) (rulebase, nat, objects string) {
	const rbSuffix = ".rulebase.json"
	if strings.HasSuffix(base, rbSuffix) {
		trimmed := strings.TrimSuffix(base, rbSuffix)
		return base, trimmed + ".nat.json", trimmed + ".objects.json"
	}
	return base + rbSuffix, base + ".nat.json", base + ".objects.json"
}

// firewallVendorSource maps dev.Protocol to the (vendor, source) pair carried
// on every FirewallRules/NAT/Objects payload (push/types.go field contract).
// Vendor is the device family; source is the agent-side collection path so
// the backend can distinguish e.g. ASA via REST vs via SSH for the same
// device family.
func firewallVendorSource(protocol string) (vendor, source string) {
	switch protocol {
	case config.ProtocolASARest:
		return "cisco-asa", "asa-rest"
	case config.ProtocolASASSH:
		return "cisco-asa", "asa-ssh"
	case config.ProtocolFMC:
		return "cisco-fmc", "fmc"
	case config.ProtocolCheckpoint:
		return "checkpoint", "checkpoint"
	case config.ProtocolCheckpointImport:
		return "checkpoint", "checkpoint-import"
	}
	return "", ""
}

// firewallCollectorFor returns the firewallPuller closure appropriate to the
// device protocol. Non-firewall protocols (netconf, ssh, config-import) return
// nil — those are handled by collectAndPushRoutes on the routes ticker.
//
// One vendor client per call: production cadence is 1h so connection-pool
// sharing across devices would only save a few TLS handshakes per hour while
// adding mutable shared state. Single stdlib *http.Client per pull keeps the
// dispatcher stateless and trivially safe to call from the ticker goroutine.
func firewallCollectorFor(dev config.Device) firewallPuller {
	switch dev.Protocol {
	case config.ProtocolASARest:
		c := asa.NewRESTCollector(firewallHTTPClient())
		return func(ctx context.Context, d config.Device) (
			[]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error,
		) {
			return c.Pull(ctx, d.Host, d.Port, d.Username, d.Password)
		}
	case config.ProtocolASASSH:
		c := asa.NewSSHCollector(asa.DefaultSSHDialer())
		return func(ctx context.Context, d config.Device) (
			[]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error,
		) {
			return c.Pull(ctx, d.Host, d.Port, d.Username, d.Password)
		}
	case config.ProtocolFMC:
		c := fmc.NewClient(firewallHTTPClient())
		return func(ctx context.Context, d config.Device) (
			[]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error,
		) {
			return c.Pull(ctx, d.Host, d.Port, d.Username, d.Password)
		}
	case config.ProtocolCheckpoint:
		c := checkpoint.NewLiveCollector(firewallHTTPClient())
		return func(ctx context.Context, d config.Device) (
			[]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error,
		) {
			return c.Pull(ctx, d.Host, d.Port, d.Username, d.Password)
		}
	case config.ProtocolCheckpointImport:
		return func(_ context.Context, d config.Device) (
			[]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error,
		) {
			rb, nat, objs := checkpointImportPaths(d.ConfigFile)
			return checkpoint.LoadImport(rb, nat, objs)
		}
	}
	return nil
}

// collectAndPushFirewall is the 4th-ticker entry point. PHASE 11 plan 11-12
// (Wave 4) fills the body. For each device with a firewall protocol, dispatch
// to the matching Wave-3 vendor collector, mint a single UUIDv4 snapshot_id
// per device per tick (RESEARCH Pattern 2 + D-08 — shared across the 3 push
// endpoints so the backend INSERT ... ON CONFLICT DO NOTHING parent insert
// is idempotent regardless of arrival order), then push the three payloads
// sequentially. Non-firewall protocols are silently skipped (no error, no
// log) — they're handled by collectAndPushRoutes on the routes ticker.
//
// Pattern G — log fields restricted to host / protocol / snapshot_id /
// counts; never user/pass/token. The vendor collectors are responsible for
// keeping credentials out of their own error returns.
func collectAndPushFirewall(ctx context.Context, cfg *config.Config, pusher Pusher, log *zap.Logger) {
	for _, dev := range cfg.Devices {
		fn := firewallCollectorFor(dev)
		if fn == nil {
			continue // non-firewall protocol — silently skip per plan 11-12 must_have
		}
		rules, nats, objs, err := fn(ctx, dev)
		if err != nil {
			log.Warn("firewall_pull_failed",
				zap.String("device", dev.Host),
				zap.String("protocol", dev.Protocol),
				zap.Error(err))
			continue
		}

		snapshotID := uuid.NewString() // RESEARCH Pattern 2 + D-08 — shared across 3 push calls
		snapshotTS := time.Now().UTC().Format(time.RFC3339)
		vendor, source := firewallVendorSource(dev.Protocol)
		firewallID := dev.Host // FirewallID per push/types.go: "device serial / dev.Host"

		log.Info("firewall_pull_ok",
			zap.String("device", dev.Host),
			zap.String("protocol", dev.Protocol),
			zap.String("snapshot_id", snapshotID),
			zap.Int("rules", len(rules)),
			zap.Int("nat", len(nats)),
			zap.Int("objects", len(objs)))

		rulesPayload := push.FirewallRulesPayload{
			SiteID:     dev.SiteID,
			SnapshotID: snapshotID,
			FirewallID: firewallID,
			Vendor:     vendor,
			Source:     source,
			SnapshotTS: snapshotTS,
			Rules:      rules,
		}
		if err := pusher.PushFirewallRules(ctx, rulesPayload); err != nil {
			log.Warn("push_firewall_rules_failed",
				zap.String("device", dev.Host),
				zap.String("snapshot_id", snapshotID),
				zap.Error(err))
		}

		natPayload := push.FirewallNATPayload{
			SiteID:     dev.SiteID,
			SnapshotID: snapshotID,
			FirewallID: firewallID,
			Vendor:     vendor,
			Source:     source,
			SnapshotTS: snapshotTS,
			NATRules:   nats,
		}
		if err := pusher.PushFirewallNAT(ctx, natPayload); err != nil {
			log.Warn("push_firewall_nat_failed",
				zap.String("device", dev.Host),
				zap.String("snapshot_id", snapshotID),
				zap.Error(err))
		}

		objectsPayload := push.FirewallObjectsPayload{
			SiteID:     dev.SiteID,
			SnapshotID: snapshotID,
			FirewallID: firewallID,
			Vendor:     vendor,
			Source:     source,
			SnapshotTS: snapshotTS,
			Objects:    objs,
		}
		if err := pusher.PushFirewallObjects(ctx, objectsPayload); err != nil {
			log.Warn("push_firewall_objects_failed",
				zap.String("device", dev.Host),
				zap.String("snapshot_id", snapshotID),
				zap.Error(err))
		}
	}
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
	fwT := time.NewTicker(iv.Firewall) // PHASE 11 D-03 — 4th ticker
	defer routeT.Stop()
	defer bgpT.Stop()
	defer flowT.Stop()
	defer fwT.Stop() // PHASE 11 D-03

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
		case <-fwT.C: // PHASE 11 D-03 — same wg.Add/wg.Done drain pattern
			wg.Add(1)
			go func() { defer wg.Done(); collectAndPushFirewall(ctx, cfg, pusher, log) }()
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

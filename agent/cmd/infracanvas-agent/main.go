// Command infracanvas-agent is the InfraCanvas DC Agent daemon.
//
// Run subcommand: starts the collection loop (routes 5m, BGP 1m, NetFlow flush 30s)
// until SIGINT/SIGTERM, at which point it drains in-flight goroutines and exits.
//
// Per CONTEXT.md D-01 the binary lives at agent/cmd/infracanvas-agent and the
// module path is github.com/infracanvas/infracanvas/agent.
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
)

// version is injected at build time via:
//
//	go build -ldflags="-X main.version=$(git describe --tags)" ./cmd/infracanvas-agent
var version = "dev"

// Intervals locks the DCA-06 daemon timing contract. Exposed as a type for
// tests so callers can assert the contract without running real tickers.
type Intervals struct {
	Routes time.Duration
	BGP    time.Duration
	Flow   time.Duration
}

// defaultIntervals returns the locked DCA-06 collection cadence.
func defaultIntervals() Intervals {
	return Intervals{
		Routes: 5 * time.Minute,
		BGP:    1 * time.Minute,
		Flow:   30 * time.Second,
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

			return runDaemonWithIntervals(ctx, cfg, defaultIntervals(), log)
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
// Collector hooks are stubbed in this plan; plans 10-04/05/06/07 wire the real
// implementations into collectAndPushRoutes / collectAndPushBGP / flushFlowBuffer.
func runDaemonWithIntervals(ctx context.Context, cfg *config.Config, iv Intervals, log *zap.Logger) error {
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
			go func() { defer wg.Done(); collectAndPushRoutes(ctx, cfg, log) }()
		case <-bgpT.C:
			wg.Add(1)
			go func() { defer wg.Done(); collectAndPushBGP(ctx, cfg, log) }()
		case <-flowT.C:
			wg.Add(1)
			go func() { defer wg.Done(); flushFlowBuffer(ctx, cfg, log) }()
		}
	}
}

// Stubs — plans 10-04/05/06/07 replace these with real collector implementations.

func collectAndPushRoutes(_ context.Context, _ *config.Config, log *zap.Logger) {
	log.Debug("collect_routes_tick (stub)")
}

func collectAndPushBGP(_ context.Context, _ *config.Config, log *zap.Logger) {
	log.Debug("collect_bgp_tick (stub)")
}

func flushFlowBuffer(_ context.Context, _ *config.Config, log *zap.Logger) {
	log.Debug("flush_flow_tick (stub)")
}

func main() {
	if err := newRootCmd().Execute(); err != nil {
		fmt.Fprintln(os.Stderr, "infracanvas-agent:", err)
		os.Exit(1)
	}
}

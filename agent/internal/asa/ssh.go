// Package asa — ssh.go: Cisco ASA SSH fallback collector (ASA-03).
//
// Opens a single SSH session, issues `terminal pager 0` then
// `show running-config`, and feeds the captured text to ParseRunningConfig
// (ssh_parser.go). Returns three normalized slices for direct push to
// /v1/agent/firewall-{rules,nat,objects}.
//
// The Dialer/Session test seam mirrors agent/internal/ssh/collector.go from
// Phase 10. The interfaces are declared local to this package (SSHSession,
// SSHDialer) so that Wave 0 (`ssh_test.go`) and the ASA SSH adapter can
// share a single mock surface. The production default dialer wraps
// agent/internal/ssh.DefaultDialer() so the cryptossh / PTY / ECHO-0 /
// InsecureIgnoreHostKey posture from Phase 10 is reused verbatim — there
// is exactly one place in the agent where SSH transport security is
// configured, and that place is the ssh package (T-10-05-01/02
// inheritance).
//
// Mitigations:
//   - T-11-09-01 (SSH MITM): InsecureIgnoreHostKey inherited from
//     ssh.DefaultDialer (CAB-documented Phase 10 posture).
//   - T-11-09-02 (password leak via PTY echo): ECHO=0 set by underlying
//     ssh.DefaultDialer. Pattern G — log only host + counts; never user
//     or password.
//   - T-11-09-03 (parser DoS): delegated to ParseRunningConfig's
//     bounded-quantifier regexes.
//
// Pattern H — caller passes primitives, not config.Device, to avoid an
// internal/config ↔ internal/asa import cycle. The main.go dispatcher
// owns the config.Device → primitives unpack.
package asa

import (
	"context"
	"fmt"

	"go.uber.org/zap"

	"github.com/infracanvas/infracanvas/agent/internal/push"
	xssh "github.com/infracanvas/infracanvas/agent/internal/ssh"
)

// SSHSession is the minimal SSH session surface the SSHCollector needs.
// Mirrors xssh.Session structurally so the production adapter is a
// thin pass-through. Declared in this package so Wave 0 ssh_test.go and
// the collector share a single mock surface.
type SSHSession interface {
	Run(ctx context.Context, command string) (string, error)
	Close() error
}

// SSHDialer opens an SSHSession to a device. Test seam (mirrors
// xssh.Dialer). The production implementation wraps xssh.DefaultDialer
// so InsecureIgnoreHostKey + ECHO=0 + the PTY pager-mitigation payload
// are inherited from Phase 10's single source of truth.
type SSHDialer interface {
	Dial(ctx context.Context, host string, port int, user, pass string) (SSHSession, error)
}

// SSHCollector is the Cisco ASA SSH fallback collector (ASA-03). It is a
// thin wrapper around a Dialer that issues the pager-disable + show
// running-config payload and delegates parsing to ParseRunningConfig.
type SSHCollector struct {
	dialer SSHDialer
	log    *zap.Logger
}

// NewSSHCollector returns an *SSHCollector wired to d. If d is nil, the
// production default dialer (wrapping xssh.DefaultDialer) is used.
// Logging defaults to zap.NewNop so unit tests can ignore it; callers
// that want operational logs should wire one via the SetLogger setter
// below.
//
// Plan 11-09 Wave 0 lock: NewSSHCollector(d SSHDialer) *SSHCollector —
// single argument (the dialer). A separate SetLogger setter keeps the
// constructor signature compatible with ssh_test.go without dragging the
// logger into the test mock surface.
func NewSSHCollector(d SSHDialer) *SSHCollector {
	if d == nil {
		d = defaultSSHDialer{}
	}
	return &SSHCollector{dialer: d, log: zap.NewNop()}
}

// DefaultSSHDialer returns the production SSH dialer that wraps
// agent/internal/ssh.DefaultDialer() (CAB-documented Phase 10 transport
// posture: InsecureIgnoreHostKey + ECHO=0 + PTY payload). Plan 11-12
// dispatcher uses this from the firewall ticker so callers don't
// construct the unexported defaultSSHDialer themselves.
func DefaultSSHDialer() SSHDialer { return defaultSSHDialer{} }

// SetLogger installs a *zap.Logger for INFO-level pull-complete logging.
// Returns the collector for chained construction. Safe to call before
// Pull; concurrent calls are not safe (caller is expected to wire once
// at startup).
func (c *SSHCollector) SetLogger(log *zap.Logger) *SSHCollector {
	if log != nil {
		c.log = log
	}
	return c
}

// Pull opens an SSH session, sends `terminal pager 0\nshow running-config`,
// and parses the output. Returns the three normalized slices.
//
// Caller passes primitives (host/port/user/pass) rather than a
// config.Device to avoid an internal/config ↔ internal/asa import cycle
// (Pattern H). Default port 22 if port == 0.
//
// Errors are returned wrapped as `asa-ssh: <stage> <host>: <inner>` so
// log aggregation can grep by stage (dial / run).
func (c *SSHCollector) Pull(
	ctx context.Context,
	host string,
	port int,
	user, pass string,
) ([]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error) {
	if port == 0 {
		port = 22
	}

	sess, err := c.dialer.Dial(ctx, host, port, user, pass)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("asa-ssh: dial %s:%d: %w", host, port, err)
	}
	defer func() { _ = sess.Close() }()

	// `terminal pager 0` is the ASA-specific pager-disable command (RESEARCH
	// Pitfall 4). The Phase 10 default dialer also prepends
	// `terminal length 0` internally — ASA accepts both and the redundant
	// prefix is harmless. By naming `terminal pager 0` explicitly here we
	// (a) make the intent self-evident at the call site and (b) match
	// Wave 0 test expectations (TestSSHCollector_DisablesPager).
	out, err := sess.Run(ctx, "terminal pager 0\nshow running-config")
	if err != nil {
		return nil, nil, nil, fmt.Errorf("asa-ssh: run %s: %w", host, err)
	}

	rules, nats, objs, perr := ParseRunningConfig(out)
	if perr != nil {
		return rules, nats, objs, fmt.Errorf("asa-ssh: parse %s: %w", host, perr)
	}

	// Pattern G — log only non-sensitive fields. Never user/pass.
	c.log.Info("asa_ssh_pull_complete",
		zap.String("host", host),
		zap.Int("rules", len(rules)),
		zap.Int("nats", len(nats)),
		zap.Int("objects", len(objs)),
	)
	return rules, nats, objs, nil
}

// ─── Production default dialer ────────────────────────────────────────────
//
// defaultSSHDialer adapts xssh.DefaultDialer to the local SSHDialer
// interface so the asa package can share Phase 10's
// InsecureIgnoreHostKey + ECHO=0 + PTY-payload code path without
// duplicating any cryptossh setup.

type defaultSSHDialer struct{}

func (defaultSSHDialer) Dial(ctx context.Context, host string, port int, user, pass string) (SSHSession, error) {
	sess, err := xssh.DefaultDialer().Dial(ctx, host, port, user, pass)
	if err != nil {
		return nil, err
	}
	return xsshSessionAdapter{inner: sess}, nil
}

// xsshSessionAdapter wraps an xssh.Session as an SSHSession. The two
// interfaces are structurally identical; the adapter exists purely so
// Go's nominal type system accepts the cross-package handoff without an
// awkward type assertion at every call site.
type xsshSessionAdapter struct {
	inner xssh.Session
}

func (a xsshSessionAdapter) Run(ctx context.Context, command string) (string, error) {
	return a.inner.Run(ctx, command)
}

func (a xsshSessionAdapter) Close() error { return a.inner.Close() }

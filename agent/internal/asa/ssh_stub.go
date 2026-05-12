// ssh_stub.go — TEMPORARY compile shim for Plan 11-09's SSH collector tests.
//
// Plan 11-01 (Wave 0 RED) landed agent/internal/asa/ssh_test.go which
// references SSHSession, SSHDialer, NewSSHCollector, and ParseRunningConfig.
// Plan 11-08 (this file's owner) implements the REST collector — but Go's
// package model means ssh_test.go MUST compile for the REST tests to run.
//
// This shim provides the minimal symbols the SSH tests reference so the
// asa package compiles. The function bodies are intentionally empty — the
// SSH tests will fail at the assertion level (expected RED) until Plan
// 11-09 replaces this file with the real ssh.go implementation.
//
// Plan 11-09 MUST delete this file when landing the real SSHCollector.
// Grep for "ssh_stub.go" in the repo to verify it's gone.
package asa

import (
	"context"

	"github.com/infracanvas/infracanvas/agent/internal/push"
)

// SSHSession is the minimal SSH session surface the SSHCollector needs.
// Mirrors the netconf/ssh package's Session interface. Plan 11-09 wires
// real cryptossh under it.
type SSHSession interface {
	Run(ctx context.Context, command string) (string, error)
	Close() error
}

// SSHDialer opens an SSHSession to a device. Test seam.
type SSHDialer interface {
	Dial(ctx context.Context, host string, port int, user, pass string) (SSHSession, error)
}

// SSHCollector is the Plan 11-09 SSH-driven ASA collector stub. The real
// implementation parses `show running-config` via terminal-pager-disable
// over an interactive shell. Plan 11-08 ships this empty shell so the
// asa package compiles; Plan 11-09 fills in the body.
type SSHCollector struct {
	dialer SSHDialer
}

// NewSSHCollector returns a stub *SSHCollector. Plan 11-09 lands the real
// constructor body.
func NewSSHCollector(d SSHDialer) *SSHCollector {
	return &SSHCollector{dialer: d}
}

// Pull is a stub — returns empty slices, no commands issued. Plan 11-09's
// TestSSHCollector_DisablesPager will then fail at the
// `require.NotEmpty(sess.commands)` assertion, which is the intended RED
// state until the real implementation lands.
func (c *SSHCollector) Pull(
	_ context.Context,
	_ string,
	_ int,
	_, _ string,
) ([]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error) {
	return nil, nil, nil, nil
}

// ParseRunningConfig is a stub — returns empty slices. Plan 11-09's
// TestSSHParser_RealConfig will fail at the
// `require.GreaterOrEqual(len(rules), 5)` assertion, which is the
// intended RED state until the real parser lands.
func ParseRunningConfig(_ string) (
	[]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error,
) {
	return nil, nil, nil, nil
}

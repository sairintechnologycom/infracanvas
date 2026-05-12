// Wave 0 RED test stub — references asa.NewSSHCollector / asa.ParseRunningConfig
// which do not exist yet. Plan 11-06 lands the production code; this test
// is intentionally compile-RED until then.
//
// Pattern source: agent/internal/ssh/collector_test.go (mock Session/Dialer)
// Fixture source: agent/internal/asa/testdata/show-running-config.txt
package asa

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
)

// -------- Fake Session / Dialer (mirrors ssh package test pattern) --------

type fakeSession struct {
	out      string
	runErr   error
	closed   bool
	commands []string
}

func (f *fakeSession) Run(_ context.Context, command string) (string, error) {
	f.commands = append(f.commands, command)
	return f.out, f.runErr
}

func (f *fakeSession) Close() error { f.closed = true; return nil }

type fakeDialer struct {
	sess SSHSession
}

func (f *fakeDialer) Dial(_ context.Context, _ string, _ int, _, _ string) (SSHSession, error) {
	return f.sess, nil
}

// TestSSHCollector_DisablesPager: ASA `show running-config` truncates at 24
// lines unless `terminal pager 0` (or `terminal length 0`) is issued first.
// The collector MUST send the pager-disable command before any show command.
//
// RED: references NewSSHCollector + SSHSession + SSHDialer which do not exist.
func TestSSHCollector_DisablesPager(t *testing.T) {
	sess := &fakeSession{out: "asa# show running-config\n!\n: end\n"}
	c := NewSSHCollector(&fakeDialer{sess: sess})

	_, _, _, _ = c.Pull(context.Background(), "asa-host", 22, "ro", "secret")

	require.NotEmpty(t, sess.commands, "collector must issue at least one command")
	first := sess.commands[0]
	require.True(t,
		strings.Contains(first, "terminal pager 0") || strings.Contains(first, "terminal length 0"),
		"first command must disable pager (T-10-05 / RESEARCH Pitfall 4), got: %q", first,
	)
}

// TestSSHParser_RealConfig: parse a real-ish ASA `show running-config` fixture
// and assert the parser surfaces at least 5 access-list rules, 3 NAT rules,
// and 3 objects. Locks the D-12 normalization shape.
//
// RED: references ParseRunningConfig which does not exist.
func TestSSHParser_RealConfig(t *testing.T) {
	raw, err := os.ReadFile(filepath.Join("testdata", "show-running-config.txt"))
	require.NoError(t, err)

	rules, nats, objs, err := ParseRunningConfig(string(raw))
	require.NoError(t, err)
	require.GreaterOrEqual(t, len(rules), 5, "fixture contains ≥5 access-list lines")
	require.GreaterOrEqual(t, len(nats), 3, "fixture contains ≥3 nat lines")
	require.GreaterOrEqual(t, len(objs), 3, "fixture contains ≥3 object/object-group declarations")
}

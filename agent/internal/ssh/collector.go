package ssh

import (
	"bytes"
	"context"
	"fmt"
	"net"
	"strconv"
	"time"

	cryptossh "golang.org/x/crypto/ssh"

	"github.com/infracanvas/infracanvas/agent/internal/config"
	"github.com/infracanvas/infracanvas/agent/internal/netconf"
)

// Session executes commands on a remote device via an interactive PTY shell.
// The contract is: terminal length 0 has already been sent before Run is called.
type Session interface {
	Run(ctx context.Context, command string) (string, error)
	Close() error
}

// Dialer opens a Session to a device. Test seam (mirrors netconf.Dialer).
type Dialer interface {
	Dial(ctx context.Context, host string, port int, user, pass string) (Session, error)
}

type Collector struct {
	dialer Dialer
}

func NewCollector(d Dialer) *Collector { return &Collector{dialer: d} }

// GetRoutes runs `show ip route` over an interactive PTY-allocated session
// and returns the parsed route table.
func (c *Collector) GetRoutes(ctx context.Context, dev config.Device) ([]netconf.RouteRecord, error) {
	port := dev.Port
	if port == 0 {
		port = 22
	}
	sess, err := c.dialer.Dial(ctx, dev.Host, port, dev.Username, dev.Password)
	if err != nil {
		return nil, fmt.Errorf("ssh: dial %s:%d: %w", dev.Host, port, err)
	}
	defer func() { _ = sess.Close() }()

	out, err := sess.Run(ctx, "show ip route")
	if err != nil {
		return nil, fmt.Errorf("ssh: run %s: %w", dev.Host, err)
	}
	return ParseShowIPRoute(out), nil
}

// -------- Production Dialer --------

func DefaultDialer() Dialer { return &defaultDialer{} }

type defaultDialer struct{}

func (defaultDialer) Dial(ctx context.Context, host string, port int, user, pass string) (Session, error) {
	cfg := &cryptossh.ClientConfig{
		User:            user,
		Auth:            []cryptossh.AuthMethod{cryptossh.Password(pass)},
		HostKeyCallback: cryptossh.InsecureIgnoreHostKey(), // CAB-documented (Plan 10-09)
		Timeout:         10 * time.Second,
	}
	addr := net.JoinHostPort(host, strconv.Itoa(port))
	client, err := cryptossh.Dial("tcp", addr, cfg)
	if err != nil {
		return nil, err
	}
	return &interactiveSession{client: client}, nil
}

// interactiveSession allocates a PTY, sends "terminal length 0" to disable
// pagination (RESEARCH Pitfall 2), then runs commands via separate exec
// sessions on the same client connection. PTY+stdin pattern is required for
// IOS-XE: without it, `show ip route` is truncated at 24 lines.
type interactiveSession struct {
	client *cryptossh.Client
}

func (s *interactiveSession) Run(ctx context.Context, command string) (string, error) {
	sess, err := s.client.NewSession()
	if err != nil {
		return "", fmt.Errorf("new session: %w", err)
	}
	defer func() { _ = sess.Close() }()

	modes := cryptossh.TerminalModes{
		cryptossh.ECHO:          0,
		cryptossh.TTY_OP_ISPEED: 14400,
		cryptossh.TTY_OP_OSPEED: 14400,
	}
	if err := sess.RequestPty("xterm", 200, 200, modes); err != nil {
		return "", fmt.Errorf("request pty: %w", err)
	}

	var stdout bytes.Buffer
	sess.Stdout = &stdout

	// Send terminal length 0 + the actual command in a single shell payload.
	// Ending with `exit\n` so the shell terminates and CombinedOutput-equivalent
	// returns once the SSH server closes the channel.
	if err := sess.Shell(); err != nil {
		return "", fmt.Errorf("shell: %w", err)
	}
	stdin, err := sess.StdinPipe()
	if err != nil {
		return "", fmt.Errorf("stdin pipe: %w", err)
	}
	payload := "terminal length 0\n" + command + "\nexit\n"
	if _, err := stdin.Write([]byte(payload)); err != nil {
		_ = stdin.Close()
		return "", fmt.Errorf("write payload: %w", err)
	}
	_ = stdin.Close()

	// Wait blocks until the shell exits (we sent `exit`).
	if err := sess.Wait(); err != nil {
		// Non-zero shell exit (some IOS-XE versions return -1 after `exit`)
		// is acceptable IFF stdout has content.
		if stdout.Len() == 0 {
			return "", fmt.Errorf("wait: %w", err)
		}
	}
	return stdout.String(), nil
}

func (s *interactiveSession) Close() error { return s.client.Close() }

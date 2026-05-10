package ssh

import (
	"context"
	"errors"
	"testing"

	"github.com/stretchr/testify/require"
)

type fakeSession struct {
	out    string
	runErr error
	closed bool
}

func (f *fakeSession) Run(ctx context.Context, command string) (string, error) {
	return f.out, f.runErr
}
func (f *fakeSession) Close() error { f.closed = true; return nil }

type fakeDialer struct {
	sess    Session
	dialErr error
	capPort int
}

func (f *fakeDialer) Dial(ctx context.Context, host string, port int, user, pass string) (Session, error) {
	f.capPort = port
	if f.dialErr != nil {
		return nil, f.dialErr
	}
	return f.sess, nil
}

const sampleSSHOutput = `Codes: L - local, C - connected, S - static
Gateway of last resort is 192.168.1.1 to network 0.0.0.0

S*   0.0.0.0/0 [1/0] via 192.168.1.1
S    10.0.0.0/8 [1/0] via 192.168.1.254
B    172.16.0.0/12 [200/0] via 192.168.1.253, 00:01:23
C    192.168.1.0/24 is directly connected, GigabitEthernet0/0
`

var (
	sampleHost = "192.0.2.1"
	samplePort = 22
	sampleUser = "ro"
	samplePass = "secret"
)

func TestSSHCollector_Happy(t *testing.T) {
	sess := &fakeSession{out: sampleSSHOutput}
	c := NewCollector(&fakeDialer{sess: sess})
	routes, err := c.GetRoutes(context.Background(), sampleHost, samplePort, sampleUser, samplePass)
	require.NoError(t, err)
	require.Len(t, routes, 4)
	require.True(t, sess.closed, "Session.Close must be invoked")
}

func TestSSHCollector_DialError(t *testing.T) {
	c := NewCollector(&fakeDialer{dialErr: errors.New("connection refused")})
	_, err := c.GetRoutes(context.Background(), sampleHost, samplePort, sampleUser, samplePass)
	require.Error(t, err)
	require.Contains(t, err.Error(), "ssh: dial")
}

func TestSSHCollector_RunError(t *testing.T) {
	sess := &fakeSession{runErr: errors.New("session closed")}
	c := NewCollector(&fakeDialer{sess: sess})
	_, err := c.GetRoutes(context.Background(), sampleHost, samplePort, sampleUser, samplePass)
	require.Error(t, err)
	require.Contains(t, err.Error(), "ssh: run")
	require.True(t, sess.closed, "Session.Close still called on Run error")
}

func TestSSHCollector_DefaultPort(t *testing.T) {
	d := &fakeDialer{sess: &fakeSession{out: ""}}
	c := NewCollector(d)
	_, _ = c.GetRoutes(context.Background(), "x", 0, "", "") // port=0 → default 22
	require.Equal(t, 22, d.capPort, "default port for SSH must be 22")
}

// TestSSHCollector wraps the verify-command name from 10-VALIDATION.md.
func TestSSHCollector(t *testing.T) { TestSSHCollector_Happy(t) }

package netconf

import (
	"context"
	"encoding/json"
	"errors"
	"testing"

	"github.com/stretchr/testify/require"

	"github.com/infracanvas/infracanvas/agent/internal/config"
)

// -------- Fake Dialer / Session --------

type fakeSession struct {
	body   []byte
	rpcErr error
	closed bool
}

func (f *fakeSession) GetSubtree(_ context.Context, _ string) ([]byte, error) {
	return f.body, f.rpcErr
}

func (f *fakeSession) Close() error { f.closed = true; return nil }

type fakeDialer struct {
	sess    Session
	dialErr error
}

func (f *fakeDialer) Dial(_ context.Context, _ string, _ int, _, _ string) (Session, error) {
	if f.dialErr != nil {
		return nil, f.dialErr
	}
	return f.sess, nil
}

const cannedXML = `<?xml version="1.0"?>
<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <data>
    <routing-state xmlns="urn:ietf:params:xml:ns:yang:ietf-routing">
      <routing-instance>
        <name>default</name>
        <ribs>
          <rib>
            <routes>
              <route>
                <destination-prefix>10.0.0.0/8</destination-prefix>
                <next-hop><next-hop-address>192.168.1.254</next-hop-address></next-hop>
                <source-protocol>bgp</source-protocol>
                <metric>100</metric>
                <as-path>65001 65002</as-path>
              </route>
              <route>
                <destination-prefix>172.16.0.0/12</destination-prefix>
                <next-hop><next-hop-address>192.168.1.253</next-hop-address></next-hop>
                <source-protocol>ospf</source-protocol>
                <metric>20</metric>
              </route>
            </routes>
          </rib>
        </ribs>
      </routing-instance>
    </routing-state>
  </data>
</rpc-reply>`

var sampleDevice = config.Device{
	Host: "192.0.2.1", Port: 830, Protocol: "netconf",
	Username: "ro", Password: "secret",
}

func TestNetconfCollector_Happy(t *testing.T) {
	sess := &fakeSession{body: []byte(cannedXML)}
	c := NewCollector(&fakeDialer{sess: sess})
	routes, err := c.GetRoutes(context.Background(), sampleDevice)
	require.NoError(t, err)
	require.Len(t, routes, 2)
	require.Equal(t, "10.0.0.0/8", routes[0].Prefix)
	require.Equal(t, "192.168.1.254", routes[0].NextHop)
	require.Equal(t, "bgp", routes[0].Protocol)
	require.Equal(t, 100, routes[0].Metric)
	require.Equal(t, "65001 65002", routes[0].ASPath)
	require.Equal(t, "172.16.0.0/12", routes[1].Prefix)
	require.Equal(t, "ospf", routes[1].Protocol)
	require.True(t, sess.closed, "Session.Close must be invoked")
}

func TestNetconfCollector_DialError(t *testing.T) {
	c := NewCollector(&fakeDialer{dialErr: errors.New("i/o timeout")})
	_, err := c.GetRoutes(context.Background(), sampleDevice)
	require.Error(t, err)
	require.Contains(t, err.Error(), "netconf: dial")
}

func TestNetconfCollector_RPCError(t *testing.T) {
	sess := &fakeSession{rpcErr: errors.New("rpc closed")}
	c := NewCollector(&fakeDialer{sess: sess})
	_, err := c.GetRoutes(context.Background(), sampleDevice)
	require.Error(t, err)
	require.Contains(t, err.Error(), "netconf: rpc")
}

func TestNetconfCollector_EmptyReply(t *testing.T) {
	c := NewCollector(&fakeDialer{sess: &fakeSession{body: []byte("")}})
	routes, err := c.GetRoutes(context.Background(), sampleDevice)
	require.NoError(t, err)
	require.Len(t, routes, 0)
}

func TestNetconfCollector_MalformedXML(t *testing.T) {
	c := NewCollector(&fakeDialer{sess: &fakeSession{body: []byte("<not xml")}})
	_, err := c.GetRoutes(context.Background(), sampleDevice)
	require.Error(t, err)
	require.Contains(t, err.Error(), "netconf: parse")
}

// TestNetconfCollector wraps the suite name from 10-VALIDATION.md so the
// -run TestNetconfCollector filter still exercises a representative case.
func TestNetconfCollector(t *testing.T) {
	TestNetconfCollector_Happy(t)
}

func TestRouteRecordJSONShape(t *testing.T) {
	r := RouteRecord{
		Prefix: "10.0.0.0/8", NextHop: "192.168.1.254", Protocol: "bgp",
		Metric: 100, ASPath: "65001",
	}
	b, err := json.Marshal(r)
	require.NoError(t, err)
	s := string(b)
	require.Contains(t, s, `"prefix":"10.0.0.0/8"`)
	require.Contains(t, s, `"next_hop":"192.168.1.254"`)
	require.Contains(t, s, `"protocol":"bgp"`)
	require.Contains(t, s, `"metric":100`)
	require.Contains(t, s, `"as_path":"65001"`)
}

// Package netconf implements the IOS-XE NETCONF route collector (DCA-02).
//
// Subtree filter is used in preference to XPath (RESEARCH Pitfall 1) to
// avoid namespace-prefix issues across IOS-XE versions. The Dialer
// interface is the test seam: production code uses defaultDialer which
// wraps nemith.io/netconf + golang.org/x/crypto/ssh.
package netconf

import (
	"context"
	"encoding/xml"
	"fmt"
	"net"
	"strconv"
	"time"

	"golang.org/x/crypto/ssh"
	"nemith.io/netconf"
	ncssh "nemith.io/netconf/transport/ssh"

	"nemith.io/netconf/rpc"

	"github.com/infracanvas/infracanvas/agent/internal/config"
)

// ietfRoutingSubtreeFilter is the routing-state subtree filter for IOS-XE.
// Subtree filters avoid the XPath-namespace-prefix pitfall (RESEARCH Pitfall 1).
const ietfRoutingSubtreeFilter = `<routing-state xmlns="urn:ietf:params:xml:ns:yang:ietf-routing">
  <routing-instance>
    <name>default</name>
    <ribs>
      <rib>
        <routes><route/></routes>
      </rib>
    </ribs>
  </routing-instance>
</routing-state>`

// Session is the minimal NETCONF session surface the Collector needs.
// Implemented by *netconf.Session in production and by mocks in tests.
type Session interface {
	GetSubtree(ctx context.Context, filter string) ([]byte, error)
	Close() error
}

// Dialer opens a NETCONF Session to a device. Test seam.
type Dialer interface {
	Dial(ctx context.Context, host string, port int, user, pass string) (Session, error)
}

// Collector orchestrates dial + RPC + parse for one or many devices.
type Collector struct {
	dialer Dialer
}

// NewCollector creates a Collector with the given Dialer.
func NewCollector(d Dialer) *Collector {
	return &Collector{dialer: d}
}

// GetRoutes dials the device, issues the routing-state subtree get, and
// returns parsed RouteRecord entries. Empty replies return an empty slice,
// not an error (RESEARCH Pitfall 1).
func (c *Collector) GetRoutes(ctx context.Context, dev config.Device) ([]RouteRecord, error) {
	port := dev.Port
	if port == 0 {
		port = 830 // RFC 6242 default NETCONF-over-SSH
	}
	sess, err := c.dialer.Dial(ctx, dev.Host, port, dev.Username, dev.Password)
	if err != nil {
		return nil, fmt.Errorf("netconf: dial %s:%d: %w", dev.Host, port, err)
	}
	defer func() { _ = sess.Close() }()

	body, err := sess.GetSubtree(ctx, ietfRoutingSubtreeFilter)
	if err != nil {
		return nil, fmt.Errorf("netconf: rpc get %s: %w", dev.Host, err)
	}
	return parseRoutesXML(body)
}

// Internal XML shape — matches the routing-state subtree reply structure.
// The outer rpc-reply wrapper is present when using the test fakeSession (canned XML),
// and is also constructed by the production nemithSessionAdapter for consistency.
type rpcReply struct {
	XMLName xml.Name `xml:"rpc-reply"`
	Routes  []struct {
		Prefix      string `xml:"destination-prefix"`
		NextHop     string `xml:"next-hop>next-hop-address"`
		SourceProto string `xml:"source-protocol"`
		Metric      int    `xml:"metric"`
		ASPath      string `xml:"as-path"`
	} `xml:"data>routing-state>routing-instance>ribs>rib>routes>route"`
}

func parseRoutesXML(body []byte) ([]RouteRecord, error) {
	if len(body) == 0 {
		return []RouteRecord{}, nil
	}
	var r rpcReply
	if err := xml.Unmarshal(body, &r); err != nil {
		return nil, fmt.Errorf("netconf: parse: %w", err)
	}
	out := make([]RouteRecord, 0, len(r.Routes))
	for _, e := range r.Routes {
		out = append(out, RouteRecord{
			Prefix:   e.Prefix,
			NextHop:  e.NextHop,
			Protocol: e.SourceProto,
			Metric:   e.Metric,
			ASPath:   e.ASPath,
		})
	}
	return out, nil
}

// -------- Production Dialer (defaultDialer) --------

// DefaultDialer returns a production Dialer wiring nemith.io/netconf via SSH.
// HostKeyCallback uses InsecureIgnoreHostKey — documented in CAB packet
// (DCA-09 plan 10-09) as a known limitation; tightening to known_hosts
// verification is enterprise-tier work.
func DefaultDialer() Dialer { return &defaultDialer{} }

type defaultDialer struct{}

func (defaultDialer) Dial(ctx context.Context, host string, port int, user, pass string) (Session, error) {
	cfg := &ssh.ClientConfig{
		User:            user,
		Auth:            []ssh.AuthMethod{ssh.Password(pass)},
		HostKeyCallback: ssh.InsecureIgnoreHostKey(), // CAB-documented limitation
		Timeout:         10 * time.Second,
	}
	addr := net.JoinHostPort(host, strconv.Itoa(port))
	transport, err := ncssh.Dial(ctx, "tcp", addr, cfg)
	if err != nil {
		return nil, err
	}
	sess, err := netconf.NewSession(transport)
	if err != nil {
		_ = transport.Close()
		return nil, err
	}
	return &nemithSessionAdapter{sess: sess}, nil
}

// nemithSessionAdapter narrows *netconf.Session to the Session interface.
// GetSubtree wraps the inner data XML back into an rpc-reply envelope so
// parseRoutesXML sees a consistent structure regardless of caller.
type nemithSessionAdapter struct {
	sess *netconf.Session
}

// GetSubtree issues a NETCONF <get> with a "subtree" filter (not XPath).
// Using SubtreeFilter avoids YANG namespace-prefix issues on IOS-XE (RESEARCH Pitfall 1).
func (a *nemithSessionAdapter) GetSubtree(ctx context.Context, filter string) ([]byte, error) {
	getReq := &rpc.Get{
		Filter: rpc.SubtreeFilter(filter), // type="subtree" per RFC 6241 §6.4.2
	}
	innerXML, err := getReq.Exec(ctx, a.sess)
	if err != nil {
		return nil, err
	}
	// Wrap the inner data XML in an rpc-reply envelope so parseRoutesXML
	// uses a consistent structure (rpc-reply > data > ...).
	wrapped := []byte(`<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"><data>`)
	wrapped = append(wrapped, innerXML...)
	wrapped = append(wrapped, []byte(`</data></rpc-reply>`)...)
	return wrapped, nil
}

func (a *nemithSessionAdapter) Close() error {
	return a.sess.Close(context.Background())
}

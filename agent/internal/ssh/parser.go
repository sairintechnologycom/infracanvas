// Package ssh implements the IOS-XE SSH CLI fallback collector (DCA-03).
//
// ParseShowIPRoute is the pure-function table parser, separable from the
// network-bound Collector for deterministic testing. Format reference:
// RESEARCH §Pattern 3 + §Pitfalls 2 + IOS-XE `show ip route` documented
// line forms.
package ssh

import (
	"regexp"
	"strconv"
	"strings"

	"github.com/infracanvas/infracanvas/agent/internal/netconf"
)

// protocolCodeMap normalizes IOS-XE single-char route codes to lowercase
// protocol strings. Unmapped codes pass through unchanged.
var protocolCodeMap = map[string]string{
	"S":  "static",
	"S*": "static",
	"B":  "bgp",
	"R":  "rip",
	"O":  "ospf",
	"C":  "connected",
	"L":  "local",
	"D":  "eigrp",
	"i":  "isis",
}

// viaRouteRE matches lines of the form:
//
//	<code(s)>  <prefix>/<mask> [<admin>/<metric>] via <next-hop>[, <iface>][, <age>]
//
// Captures: code, prefix, admin, next_hop
var viaRouteRE = regexp.MustCompile(
	`^(?P<code>\S+(?:\s+\S+)?)\s+(?P<prefix>\d+\.\d+\.\d+\.\d+/\d+)\s+\[(?P<admin>\d+)/\d+\]\s+via\s+(?P<nh>\d+\.\d+\.\d+\.\d+)`,
)

// connectedRouteRE matches:
//
//	C    192.168.1.0/24 is directly connected, GigabitEthernet0/0
//	L    192.168.1.10/32 is directly connected, GigabitEthernet0/0
var connectedRouteRE = regexp.MustCompile(
	`^(?P<code>[CL])\s+(?P<prefix>\d+\.\d+\.\d+\.\d+/\d+)\s+is\s+directly\s+connected`,
)

// ParseShowIPRoute parses IOS-XE `show ip route` text output into RouteRecords.
// Lines that don't match either pattern are silently skipped (legend, banners,
// gateway-of-last-resort lines, blank lines).
func ParseShowIPRoute(out string) []netconf.RouteRecord {
	var routes []netconf.RouteRecord
	for _, raw := range strings.Split(out, "\n") {
		line := strings.TrimRight(raw, "\r")
		if line == "" {
			continue
		}
		if m := viaRouteRE.FindStringSubmatch(line); m != nil {
			code := strings.TrimSpace(m[1])
			proto := protocolCodeMap[code]
			if proto == "" {
				// Try first token if compound code (e.g. "O*N1")
				head := strings.SplitN(code, " ", 2)[0]
				if p, ok := protocolCodeMap[strings.TrimRight(head, "*")]; ok {
					proto = p
				} else {
					proto = strings.ToLower(strings.TrimRight(head, "*"))
				}
			}
			metric, _ := strconv.Atoi(m[3])
			routes = append(routes, netconf.RouteRecord{
				Prefix:   m[2],
				NextHop:  m[4],
				Protocol: proto,
				Metric:   metric,
			})
			continue
		}
		if m := connectedRouteRE.FindStringSubmatch(line); m != nil {
			proto := protocolCodeMap[m[1]]
			routes = append(routes, netconf.RouteRecord{
				Prefix:   m[2],
				NextHop:  "",
				Protocol: proto,
			})
			continue
		}
	}
	return routes
}

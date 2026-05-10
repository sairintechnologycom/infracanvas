package ssh

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestParseShowIPRoute_BasicStatic(t *testing.T) {
	out := "S    10.0.0.0/8 [1/0] via 192.168.1.254\n"
	routes := ParseShowIPRoute(out)
	require.Len(t, routes, 1)
	require.Equal(t, "10.0.0.0/8", routes[0].Prefix)
	require.Equal(t, "192.168.1.254", routes[0].NextHop)
	require.Equal(t, "static", routes[0].Protocol)
	require.Equal(t, 1, routes[0].Metric)
}

func TestParseShowIPRoute_DefaultMarker(t *testing.T) {
	out := "S*   0.0.0.0/0 [1/0] via 192.168.1.1\n"
	routes := ParseShowIPRoute(out)
	require.Len(t, routes, 1)
	require.Equal(t, "0.0.0.0/0", routes[0].Prefix)
	require.Equal(t, "static", routes[0].Protocol)
}

func TestParseShowIPRoute_BGP(t *testing.T) {
	out := "B    172.16.0.0/12 [200/0] via 192.168.1.253, 00:01:23\n"
	routes := ParseShowIPRoute(out)
	require.Len(t, routes, 1)
	require.Equal(t, "172.16.0.0/12", routes[0].Prefix)
	require.Equal(t, "bgp", routes[0].Protocol)
	require.Equal(t, 200, routes[0].Metric)
}

func TestParseShowIPRoute_OSPF(t *testing.T) {
	out := "O    10.1.1.0/24 [110/2] via 10.0.0.1, 00:00:30, GigabitEthernet0/0\n"
	routes := ParseShowIPRoute(out)
	require.Len(t, routes, 1)
	require.Equal(t, "ospf", routes[0].Protocol)
	require.Equal(t, 110, routes[0].Metric)
}

func TestParseShowIPRoute_Connected(t *testing.T) {
	out := "C    192.168.1.0/24 is directly connected, GigabitEthernet0/0\n" +
		"L    192.168.1.10/32 is directly connected, GigabitEthernet0/0\n"
	routes := ParseShowIPRoute(out)
	require.Len(t, routes, 2)
	require.Equal(t, "connected", routes[0].Protocol)
	require.Equal(t, "local", routes[1].Protocol)
	require.Equal(t, "", routes[0].NextHop)
}

func TestParseShowIPRoute_SkipLegendAndBlank(t *testing.T) {
	out := "Codes: L - local, C - connected\n\nGateway of last resort is 192.168.1.1\n\n"
	routes := ParseShowIPRoute(out)
	require.Empty(t, routes)
}

func TestParseShowIPRoute_MultiRouteTable(t *testing.T) {
	out := `Codes: L - local, C - connected, S - static
Gateway of last resort is 192.168.1.1 to network 0.0.0.0

S*   0.0.0.0/0 [1/0] via 192.168.1.1
S    10.0.0.0/8 [1/0] via 192.168.1.254
B    172.16.0.0/12 [200/0] via 192.168.1.253, 00:01:23
C    192.168.1.0/24 is directly connected, GigabitEthernet0/0
`
	routes := ParseShowIPRoute(out)
	require.Len(t, routes, 4)
	require.Equal(t, "0.0.0.0/0", routes[0].Prefix)
	require.Equal(t, "10.0.0.0/8", routes[1].Prefix)
	require.Equal(t, "172.16.0.0/12", routes[2].Prefix)
	require.Equal(t, "192.168.1.0/24", routes[3].Prefix)
}

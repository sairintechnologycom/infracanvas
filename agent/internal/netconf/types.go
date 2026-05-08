package netconf

// RouteRecord is the agent-internal representation of a single route entry,
// shared with the push package and serialized over the wire to
// POST /v1/agent/routes. JSON field names MUST match backend Pydantic
// RouteRecord in backend/app/schemas/agent.py (Plan 10-02).
type RouteRecord struct {
	Prefix   string `json:"prefix"`
	NextHop  string `json:"next_hop"`
	Protocol string `json:"protocol"`
	Metric   int    `json:"metric"`
	ASPath   string `json:"as_path"`
}

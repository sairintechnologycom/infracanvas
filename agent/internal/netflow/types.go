package netflow

// FlowRecord is the agent-internal representation of a single NetFlow record,
// shared with the push package and serialized over the wire to
// POST /v1/agent/flows. JSON field names MUST match the backend Pydantic
// FlowRecord in backend/app/schemas/agent.py (Plan 10-02).
type FlowRecord struct {
	SrcIP    string `json:"src_ip"`
	DstIP    string `json:"dst_ip"`
	SrcPort  int    `json:"src_port"`
	DstPort  int    `json:"dst_port"`
	Protocol int    `json:"protocol"`
	Bytes    int    `json:"bytes"`
	Packets  int    `json:"packets"`
}

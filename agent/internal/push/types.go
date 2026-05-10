package push

import (
	"github.com/infracanvas/infracanvas/agent/internal/netconf"
	"github.com/infracanvas/infracanvas/agent/internal/netflow"
)

// RoutesPayload is the wire contract for POST /v1/agent/routes.
// Field names match backend Pydantic RoutesPushBody exactly (Plan 10-02 —
// backend/app/schemas/agent.py). Any drift on either side breaks the
// agent ↔ backend contract.
type RoutesPayload struct {
	SiteID      string                `json:"site_id"`
	CollectedAt string                `json:"collected_at"`
	DeviceHost  string                `json:"device_host"`
	Routes      []netconf.RouteRecord `json:"routes"`
}

// FlowsPayload is the wire contract for POST /v1/agent/flows.
// Field names match backend Pydantic FlowsPushBody exactly.
type FlowsPayload struct {
	SiteID      string               `json:"site_id"`
	CollectedAt string               `json:"collected_at"`
	Flows       []netflow.FlowRecord `json:"flows"`
}

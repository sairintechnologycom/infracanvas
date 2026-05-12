package push

import (
	"encoding/json"

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

// ─── PHASE 11 ─── Firewall payloads.
//
// FirewallRulesPayload / FirewallNATPayload / FirewallObjectsPayload are the
// wire contracts for POST /v1/agent/firewall-rules, /firewall-nat, /firewall-objects.
// Field names match backend Pydantic FirewallRulesPushBody / FirewallNATPushBody /
// FirewallObjectsPushBody (backend/app/schemas/firewall.py) exactly. Any drift on
// either side breaks the agent ↔ backend contract.
//
// snapshot_id is minted by the agent (UUIDv4) per RESEARCH Pattern 2 — three
// endpoints share the same snapshot_id so the backend INSERT ... ON CONFLICT
// DO NOTHING parent insert is idempotent regardless of arrival order.

// FirewallRule is a single access rule (D-08 hybrid: normalized columns drive
// Phase 12 path computation; raw_blob preserves the vendor-native shape).
type FirewallRule struct {
	Position int             `json:"position"`
	SrcZone  string          `json:"src_zone,omitempty"`
	DstZone  string          `json:"dst_zone,omitempty"`
	SrcCIDR  string          `json:"src_cidr"`
	DstCIDR  string          `json:"dst_cidr"`
	Action   string          `json:"action"` // 'permit'|'deny'|'accept'|'drop'
	Protocol string          `json:"protocol,omitempty"`
	Ports    string          `json:"ports,omitempty"`
	RawBlob  json.RawMessage `json:"raw_blob"` // vendor-native (D-08 hybrid)
}

// FirewallNATRule is a single NAT rule (D-15 forward-feed for Phase 12
// NAT_ASYMMETRY).
type FirewallNATRule struct {
	Position       int             `json:"position"`
	SrcTranslation string          `json:"src_translation,omitempty"`
	DstTranslation string          `json:"dst_translation,omitempty"`
	InterfaceIn    string          `json:"interface_in,omitempty"`
	InterfaceOut   string          `json:"interface_out,omitempty"`
	RawBlob        json.RawMessage `json:"raw_blob"`
}

// FirewallObject is a host/network/group/service object (D-09).
// kind is one of: 'host' | 'network' | 'group' | 'service'.
type FirewallObject struct {
	Kind    string          `json:"kind"`
	Name    string          `json:"name"`
	Value   json.RawMessage `json:"value"` // JSONB
	RawBlob json.RawMessage `json:"raw_blob"`
}

// FirewallRulesPayload is the wire contract for POST /v1/agent/firewall-rules.
type FirewallRulesPayload struct {
	SiteID     string         `json:"site_id"`
	SnapshotID string         `json:"snapshot_id"` // UUIDv4 minted by agent
	FirewallID string         `json:"firewall_id"` // device serial / dev.Host
	Vendor     string         `json:"vendor"`      // 'cisco-asa'|'cisco-fmc'|'checkpoint'
	Source     string         `json:"source"`      // 'asa-rest'|'asa-ssh'|'fmc'|'checkpoint'|'checkpoint-import'
	SnapshotTS string         `json:"snapshot_ts"` // RFC3339
	Rules      []FirewallRule `json:"rules"`
}

// FirewallNATPayload is the wire contract for POST /v1/agent/firewall-nat.
type FirewallNATPayload struct {
	SiteID     string            `json:"site_id"`
	SnapshotID string            `json:"snapshot_id"`
	FirewallID string            `json:"firewall_id"`
	Vendor     string            `json:"vendor"`
	Source     string            `json:"source"`
	SnapshotTS string            `json:"snapshot_ts"`
	NATRules   []FirewallNATRule `json:"nat_rules"`
}

// FirewallObjectsPayload is the wire contract for POST /v1/agent/firewall-objects.
type FirewallObjectsPayload struct {
	SiteID     string           `json:"site_id"`
	SnapshotID string           `json:"snapshot_id"`
	FirewallID string           `json:"firewall_id"`
	Vendor     string           `json:"vendor"`
	Source     string           `json:"source"`
	SnapshotTS string           `json:"snapshot_ts"`
	Objects    []FirewallObject `json:"objects"`
}

// Package asa implements the Cisco ASA firewall collectors (ASA-01 + ASA-03).
//
// Two collectors live in this package and share the internal vendor-shape
// types defined here:
//
//   - RESTCollector — pulls access rules + NAT + network objects via the ASA
//     REST API (POST /api/tokenservices + X-Auth-Token-authenticated GETs).
//     Implemented in rest.go (this plan, 11-08). Covers ASA-01.
//   - SSHCollector — pulls `show running-config` over SSH and parses the
//     ACL / NAT / object lines with a linear-time regex. Implemented in
//     ssh.go (Plan 11-09). Covers ASA-03.
//
// Callers see the normalized push wire-shape (push.FirewallRule,
// push.FirewallNATRule, push.FirewallObject — defined in
// agent/internal/push/types.go). The vendor-shape types in this file stay
// package-internal: they're an intermediate decode target between raw ASA
// JSON and the push payload structs.
//
// ASA REST API EOL: Cisco removed the legacy REST API at ASA 9.17+. Devices
// running 9.17 or newer must use protocol: asa-ssh in agent.yaml. See
// agent/docs/cab/known-limitations.md (Plan 11-13) for the operator-facing
// surface. RESEARCH Pitfall 1.
package asa

import (
	"encoding/json"
	"time"
)

// ─── Token cache entry ────────────────────────────────────────────────────
//
// asaToken holds an X-Auth-Token returned by POST /api/tokenservices for the
// lifetime of a single Pull invocation. The token is acquired at the start
// of Pull and best-effort DELETEd via defer; nothing persists between pulls.
// Per RESEARCH Pattern 3 — token cache is per-pull, never at-rest.
type asaToken struct {
	value      string
	acquiredAt time.Time
}

// ─── /api/access/in/{iface}/rules response shape ──────────────────────────

// asaACLResponse mirrors the top-level body of GET /api/access/in/<iface>/rules.
type asaACLResponse struct {
	Items     []asaACLItem `json:"items"`
	RangeInfo asaRangeInfo `json:"rangeInfo"`
}

// asaACLItem is one access-list entry. Raw is populated manually during the
// normalize step in rest.go to capture the unmodified vendor JSON for the
// raw_blob field (D-08 hybrid).
type asaACLItem struct {
	Position           int             `json:"position"`
	RuleID             int64           `json:"ruleId"`
	Permit             bool            `json:"permit"`
	SourceAddress      asaAddressRef   `json:"sourceAddress"`
	DestinationAddress asaAddressRef   `json:"destinationAddress"`
	SourceService      asaProtocolRef  `json:"sourceService"`
	DestinationService asaProtocolRef  `json:"destinationService"`
	Active             bool            `json:"active"`
	Remarks            []string        `json:"remarks,omitempty"`
	Raw                json.RawMessage `json:"-"`
}

// asaAddressRef is the source/destination address shape on an ACL item.
// Kind discriminates literal CIDRs ("AnyIPAddress" / "IPv4Address") from
// object references ("objectRef#NetworkObj").
type asaAddressRef struct {
	Kind   string `json:"kind"`
	Value  string `json:"value,omitempty"`
	ObjRef string `json:"objectRef,omitempty"`
}

// asaProtocolRef is the protocol/service shape on an ACL item. Value is the
// canonical "tcp/80" / "udp/53" / "ip" / "any" string ASA emits.
type asaProtocolRef struct {
	Kind  string `json:"kind"`
	Value string `json:"value"`
}

// asaRangeInfo is the paging envelope ASA returns on collection endpoints.
// Plan 11-08 reads but does not yet act on it (single-page pulls only).
type asaRangeInfo struct {
	Offset int `json:"offset"`
	Limit  int `json:"limit"`
	Total  int `json:"total"`
}

// ─── /api/nat response shape ──────────────────────────────────────────────

// asaNATResponse mirrors the top-level body of GET /api/nat.
type asaNATResponse struct {
	Items     []asaNATItem `json:"items"`
	RangeInfo asaRangeInfo `json:"rangeInfo"`
}

// asaNATItem is one NAT rule. Raw is populated manually during normalize.
type asaNATItem struct {
	Position                      int             `json:"position"`
	Mode                          string          `json:"mode,omitempty"`
	Type                          string          `json:"type,omitempty"`
	OriginalSourceNetworkObject   asaNetObjRef    `json:"originalSourceNetworkObject,omitempty"`
	TranslatedSourceNetworkObject asaNetObjRef    `json:"translatedSourceNetworkObject,omitempty"`
	OriginalSourceInterface       asaInterfaceRef `json:"originalSourceInterface,omitempty"`
	TranslatedSourceInterface     asaInterfaceRef `json:"translatedSourceInterface,omitempty"`
	Raw                           json.RawMessage `json:"-"`
}

// asaNetObjRef is the network-object reference shape on a NAT rule's
// original/translated source field. Kind discriminates literal addresses,
// object references, and interface references.
type asaNetObjRef struct {
	Kind   string `json:"kind"`
	Name   string `json:"name,omitempty"`
	ObjRef string `json:"objectRef,omitempty"`
	Value  string `json:"value,omitempty"`
}

// asaInterfaceRef is the interface-reference shape on a NAT rule's
// original/translated interface field.
type asaInterfaceRef struct {
	Kind string `json:"kind,omitempty"`
	Name string `json:"name,omitempty"`
}

// ─── /api/objects/networkobjects response shape ───────────────────────────

// asaObjectsResponse mirrors the top-level body of GET /api/objects/networkobjects.
type asaObjectsResponse struct {
	Items     []asaObjectItem `json:"items"`
	RangeInfo asaRangeInfo    `json:"rangeInfo"`
}

// asaObjectItem is one network/host/group object. Kind values seen in the
// wild: "object#NetworkObj" (host or network), "object#NetworkObjGroup"
// (group). Host/Network are mutually exclusive — one is populated based on
// the object's underlying type. Raw is populated manually during normalize.
type asaObjectItem struct {
	ObjectID string            `json:"objectId,omitempty"`
	Name     string            `json:"name"`
	Kind     string            `json:"kind"`
	Host     *asaHostValue     `json:"host,omitempty"`
	Network  *asaHostValue     `json:"network,omitempty"`
	Members  []asaObjectMember `json:"members,omitempty"`
	Raw      json.RawMessage   `json:"-"`
}

// asaHostValue is the host/network inner value shape on an object. Kind is
// "IPv4Address" for a single host, "IPv4Network" for a CIDR.
type asaHostValue struct {
	Kind  string `json:"kind"`
	Value string `json:"value"`
}

// asaObjectMember is one member of an object-group. Same shape as a
// network-object reference inside an ACL.
type asaObjectMember struct {
	Kind   string `json:"kind"`
	Name   string `json:"name,omitempty"`
	ObjRef string `json:"objectRef,omitempty"`
	Value  string `json:"value,omitempty"`
}

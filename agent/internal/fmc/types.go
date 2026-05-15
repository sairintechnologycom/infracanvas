// Package fmc implements the Cisco Firepower Management Center (FMC) REST
// API collector (REQ ASA-02 — FMC is a Cisco firewall management plane that
// supervises FTD / ASA-with-FirePOWER devices and exposes a unified REST API
// for access policy, NAT policy, and network-object inventory).
//
// One collector lives in this package:
//
//   - Client — pulls access rules + manual-NAT rules + network objects via
//     the FMC v1 REST API (POST /api/fmc_platform/v1/auth/generatetoken +
//     X-auth-access-token-authenticated GETs). Implemented in client.go.
//
// Callers see the normalized push wire-shape (push.FirewallRule,
// push.FirewallNATRule, push.FirewallObject — defined in
// agent/internal/push/types.go). The vendor-shape types in this file stay
// package-internal: they're an intermediate decode target between raw FMC
// JSON and the push payload structs.
//
// FMC token lifecycle (RESEARCH Pitfall 3): the access token is valid for
// 30 minutes; the refresh token gives up to 3 refreshes for an effective
// 120-minute window. On 401 the collector attempts exactly ONE refresh via
// /api/fmc_platform/v1/auth/refreshtoken before bailing with ErrFMCAuth
// (non-retryable). After 3 successful refreshes, the next refresh attempt
// returns ErrFMCAuth — the next ticker tick acquires a fresh token.
//
// DOMAIN_UUID requirement (RESEARCH Pitfall 6): FMC is multi-domain by
// default. The DOMAIN_UUID header on the auth response identifies which
// domain the credentials authenticated against; every /api/fmc_config path
// MUST include that UUID. Phase 11 scopes pulls to the first DOMAIN_UUID
// returned; operator-driven multi-domain selection is deferred.
package fmc

import (
	"encoding/json"
)

// ─── Token state ──────────────────────────────────────────────────────────
//
// fmcTokenInfo holds the three values returned from POST /generatetoken plus
// a counter tracking how many refreshes have been performed against the
// current access-token (capped at 3 per RESEARCH Pitfall 3 — after that the
// caller must re-acquire from scratch via /generatetoken).
//
// The token is created at the start of Pull and lives only for the duration
// of that Pull. Nothing persists between pulls.
type fmcTokenInfo struct {
	accessToken  string // X-auth-access-token response header
	refreshToken string // X-auth-refresh-token response header
	domainUUID   string // DOMAIN_UUID response header (mandatory for /fmc_config paths)
	refreshCount int    // 0..3; after 3, refreshToken returns ErrFMCAuth
}

// ─── Paginated response envelopes ─────────────────────────────────────────
//
// FMC returns a uniform envelope shape across collection endpoints: a links
// object (self + optional next), an items array, and a paging block with
// offset/limit/count/pages. Go generics complicate JSON unmarshalling here
// (the items array shape varies per endpoint), so we define one envelope
// per resource type.

// fmcAccessRulesResp envelopes
// GET /api/fmc_config/v1/domain/{uuid}/policy/accesspolicies/{pid}/accessrules
type fmcAccessRulesResp struct {
	Links  fmcLinks        `json:"links"`
	Items  []fmcAccessRule `json:"items"`
	Paging fmcPaging       `json:"paging"`
}

// fmcNATRulesResp envelopes
// GET /api/fmc_config/v1/domain/{uuid}/policy/ftdnatpolicies/{pid}/manualnatrules
type fmcNATRulesResp struct {
	Links  fmcLinks     `json:"links"`
	Items  []fmcNATRule `json:"items"`
	Paging fmcPaging    `json:"paging"`
}

// fmcNetworkObjectsResp envelopes
// GET /api/fmc_config/v1/domain/{uuid}/object/networks
type fmcNetworkObjectsResp struct {
	Links  fmcLinks           `json:"links"`
	Items  []fmcNetworkObject `json:"items"`
	Paging fmcPaging          `json:"paging"`
}

// fmcPolicyListResp envelopes
// GET /api/fmc_config/v1/domain/{uuid}/policy/accesspolicies
// GET /api/fmc_config/v1/domain/{uuid}/policy/ftdnatpolicies
// Phase 11 picks the first policy (D-15 + CONTEXT Discretion — operator-
// driven policy selection deferred).
type fmcPolicyListResp struct {
	Links  fmcLinks        `json:"links"`
	Items  []fmcPolicyRef  `json:"items"`
	Paging fmcPaging       `json:"paging"`
}

// fmcLinks is the links envelope on a paginated response. Self is the
// canonical URL for the current page; Next is the URL for the next page
// (absent on the last page).
type fmcLinks struct {
	Self   string `json:"self"`
	Next   string `json:"next,omitempty"`
	Parent string `json:"parent,omitempty"`
}

// fmcPaging is the paging block on a paginated response. Pages > 1 with a
// missing Links.Next indicates the server expects offset-walking; client.go
// follows Links.Next when present and falls back to offset/limit otherwise.
type fmcPaging struct {
	Offset int `json:"offset"`
	Limit  int `json:"limit"`
	Count  int `json:"count"`
	Pages  int `json:"pages"`
}

// fmcPolicyRef is one entry from /policy/accesspolicies or /policy/ftdnatpolicies.
// Phase 11 reads only the ID to drive the rule-pagination URL.
type fmcPolicyRef struct {
	ID   string `json:"id"`
	Name string `json:"name"`
	Type string `json:"type"`
}

// ─── Access rule shape ────────────────────────────────────────────────────

// fmcAccessRule is one access rule inside an FMC access policy. FMC uses
// camelCase JSON tags and uppercase action values ("ALLOW" / "BLOCK") which
// client.go normalizes to the canonical permit/deny taxonomy on the push
// wire shape.
//
// Raw is populated manually during normalization (D-08 hybrid raw_blob).
type fmcAccessRule struct {
	ID                  string             `json:"id"`
	Name                string             `json:"name"`
	Type                string             `json:"type"`
	Action              string             `json:"action"` // ALLOW / BLOCK / TRUST / MONITOR
	Enabled             bool               `json:"enabled"`
	SourceZones         fmcZoneList        `json:"sourceZones,omitempty"`
	DestinationZones    fmcZoneList        `json:"destinationZones,omitempty"`
	SourceNetworks      fmcNetworkRefList  `json:"sourceNetworks,omitempty"`
	DestinationNetworks fmcNetworkRefList  `json:"destinationNetworks,omitempty"`
	SourcePorts         fmcPortList        `json:"sourcePorts,omitempty"`
	DestinationPorts    fmcPortList        `json:"destinationPorts,omitempty"`
	IPSPolicy           interface{}        `json:"ipsPolicy,omitempty"` // ignored — not on path-asymmetry path
	Raw                 json.RawMessage    `json:"-"`
}

// fmcZoneList is the security-zone reference list on an access rule.
// Phase 12 path computation may use zone names; Phase 11 emits them as
// src_zone / dst_zone on the push.FirewallRule.
type fmcZoneList struct {
	Objects []fmcObjectRef `json:"objects,omitempty"`
}

// fmcNetworkRefList is the network/host reference list. FMC can express a
// rule's source/destination either as object references (named hosts /
// networks / groups defined elsewhere) or as inline literals (raw CIDRs).
type fmcNetworkRefList struct {
	Objects  []fmcObjectRef `json:"objects,omitempty"`
	Literals []fmcLiteral   `json:"literals,omitempty"`
}

// fmcObjectRef is a named reference into the network-objects inventory.
type fmcObjectRef struct {
	ID   string `json:"id,omitempty"`
	Name string `json:"name"`
	Type string `json:"type,omitempty"` // Host / Network / NetworkGroup / SecurityZone
}

// fmcLiteral is an inline source/destination address — raw CIDR or host IP.
type fmcLiteral struct {
	Value string `json:"value"`
	Type  string `json:"type"` // Host / Network
}

// fmcPortList is the source/destination port reference list. FMC mirrors the
// network-ref shape — named PortObjects OR inline PortLiterals.
type fmcPortList struct {
	Objects  []fmcObjectRef    `json:"objects,omitempty"`
	Literals []fmcPortLiteral  `json:"literals,omitempty"`
}

// fmcPortLiteral is an inline port literal — protocol number ("6" = TCP,
// "17" = UDP) + port string ("80", "443", "53").
type fmcPortLiteral struct {
	Port     string `json:"port"`
	Protocol string `json:"protocol"`
	Type     string `json:"type,omitempty"` // PortLiteral
}

// ─── NAT rule shape ───────────────────────────────────────────────────────

// fmcNATRule is one manual NAT rule under an FTD NAT policy. The shape uses
// camelCase originalSource / translatedSource / originalDestination /
// translatedDestination + sourceInterface / destinationInterface object
// refs. Raw is populated manually during normalization.
type fmcNATRule struct {
	ID                    string          `json:"id"`
	Type                  string          `json:"type"` // FTDManualNatRule
	Enabled               bool            `json:"enabled"`
	OriginalSource        fmcObjectRef    `json:"originalSource,omitempty"`
	TranslatedSource      fmcObjectRef    `json:"translatedSource,omitempty"`
	OriginalDestination   fmcObjectRef    `json:"originalDestination,omitempty"`
	TranslatedDestination fmcObjectRef    `json:"translatedDestination,omitempty"`
	SourceInterface       fmcObjectRef    `json:"sourceInterface,omitempty"`
	DestinationInterface  fmcObjectRef    `json:"destinationInterface,omitempty"`
	Raw                   json.RawMessage `json:"-"`
}

// ─── Network object shape ────────────────────────────────────────────────

// fmcNetworkObject is one entry from /object/networks. Type discriminates
// host (single address) vs Network (CIDR). Raw is populated manually during
// normalization (D-08 hybrid).
type fmcNetworkObject struct {
	ID    string          `json:"id"`
	Name  string          `json:"name"`
	Type  string          `json:"type"` // Host / Network
	Value string          `json:"value"`
	Raw   json.RawMessage `json:"-"`
}

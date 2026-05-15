// parser.go — D-12 shared Checkpoint policy parser.
//
// Parse is a pure function over three JSON byte slices (rulebase, NAT
// rulebase, objects). It is called by BOTH live.go (CKP-01 web_api responses)
// and import.go (CKP-02 mgmt_cli --format json offline export). The Wave 0
// test TestParser_LiveImportEquivalence locks this: paired live/import
// fixtures MUST decode to byte-identical normalized output.
//
// Normalization shape follows D-08 hybrid: each push.FirewallRule /
// FirewallNATRule / FirewallObject carries normalized columns for Phase 12
// path computation plus a raw_blob preserving the original vendor JSON. Raw
// blobs are produced by re-marshalling the decoded internal struct (NOT by
// slicing the input bytes) so that paired fixtures with cosmetic JSON
// differences (whitespace, key order) still produce byte-equal raw_blob —
// which is what reflect.DeepEqual in the equivalence test needs.
//
// Errors propagate only from json.Unmarshal failures. Missing optional
// fields, unresolved object UIDs, unknown action names, and unknown service
// types are tolerated and degrade gracefully — Checkpoint's `Any` sentinel
// and operator-renamed catch-alls would otherwise turn into hard parse
// failures every time a customer renames an object.
package checkpoint

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"

	"github.com/infracanvas/infracanvas/agent/internal/push"
)

// Parse normalizes a Checkpoint rulebase + NAT rulebase + objects payload
// triple into push.FirewallRule / push.FirewallNATRule / push.FirewallObject
// slices. Empty input slices return empty output slices and a nil error so
// callers (live.go, import.go) can pass through partial datasets without a
// special case.
//
// D-12 contract: identical input bytes MUST produce identical output bytes.
// The internal types (types.go) and this function are the single shared
// surface that backs both the live API and the offline import paths.
func Parse(rulebaseJSON, natJSON, objectsJSON []byte) ([]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error) {
	// ─── Objects first ────────────────────────────────────────────────
	// Decode the objects payload (if any), then build a UID→ckpObject
	// lookup table used to resolve refs on access rules and NAT rules.
	var objResp ckpObjectsResp
	if len(objectsJSON) > 0 {
		if err := json.Unmarshal(objectsJSON, &objResp); err != nil {
			return nil, nil, nil, fmt.Errorf("checkpoint: parse objects: %w", err)
		}
	}
	objectsByUID := make(map[string]ckpObject, len(objResp.Objects))
	for _, o := range objResp.Objects {
		objectsByUID[o.UID] = o
	}

	// Build the push.FirewallObject slice in source order — order matters
	// for reflect.DeepEqual on the equivalence test.
	objects := make([]push.FirewallObject, 0, len(objResp.Objects))
	for _, o := range objResp.Objects {
		raw, err := json.Marshal(o)
		if err != nil {
			return nil, nil, nil, fmt.Errorf("checkpoint: marshal object %s: %w", o.UID, err)
		}
		valueJSON, err := objectValueJSON(o)
		if err != nil {
			return nil, nil, nil, fmt.Errorf("checkpoint: marshal object value %s: %w", o.UID, err)
		}
		objects = append(objects, push.FirewallObject{
			Kind:    mapType(o.Type),
			Name:    o.Name,
			Value:   valueJSON,
			RawBlob: raw,
		})
	}

	// ─── Access rulebase ──────────────────────────────────────────────
	var rbResp ckpAccessRulebaseResp
	if len(rulebaseJSON) > 0 {
		if err := json.Unmarshal(rulebaseJSON, &rbResp); err != nil {
			return nil, nil, nil, fmt.Errorf("checkpoint: parse rulebase: %w", err)
		}
	}
	rules := make([]push.FirewallRule, 0, len(rbResp.Rulebase))
	for _, r := range rbResp.Rulebase {
		raw, err := json.Marshal(r)
		if err != nil {
			return nil, nil, nil, fmt.Errorf("checkpoint: marshal rule %s: %w", r.UID, err)
		}
		proto, ports := resolveServiceRefs(r.Service, objectsByUID)
		rules = append(rules, push.FirewallRule{
			Position: r.RuleNumber,
			SrcCIDR:  resolveAddrRefs(r.Source, objectsByUID),
			DstCIDR:  resolveAddrRefs(r.Destination, objectsByUID),
			Action:   mapAction(r.Action.Name),
			Protocol: proto,
			Ports:    ports,
			RawBlob:  raw,
		})
	}

	// ─── NAT rulebase ─────────────────────────────────────────────────
	var natResp ckpNATRulebaseResp
	if len(natJSON) > 0 {
		if err := json.Unmarshal(natJSON, &natResp); err != nil {
			return nil, nil, nil, fmt.Errorf("checkpoint: parse nat rulebase: %w", err)
		}
	}
	nats := make([]push.FirewallNATRule, 0, len(natResp.Rulebase))
	for _, n := range natResp.Rulebase {
		raw, err := json.Marshal(n)
		if err != nil {
			return nil, nil, nil, fmt.Errorf("checkpoint: marshal nat rule %s: %w", n.UID, err)
		}
		nats = append(nats, push.FirewallNATRule{
			Position:       n.RuleNumber,
			SrcTranslation: resolveSingleRef(n.TranslatedSource, objectsByUID),
			DstTranslation: resolveSingleRef(n.TranslatedDestination, objectsByUID),
			// Checkpoint uses install-on (gateway list) rather than
			// interface-in/out. Leave the interface fields empty per
			// CONTEXT D-07; Phase 12 NAT_ASYMMETRY consumes src/dst
			// translation as the primary signal.
			InterfaceIn:  "",
			InterfaceOut: "",
			RawBlob:      raw,
		})
	}

	return rules, nats, objects, nil
}

// ─── Helpers ──────────────────────────────────────────────────────────────

// mapType maps a Checkpoint object type string to the D-09 taxonomy
// {host, network, group, service}. Unknown types fall through to "group" —
// the safest catch-all because downstream consumers treat unknown kinds as
// opaque buckets rather than executable network primitives.
func mapType(ckpType string) string {
	switch {
	case ckpType == "host":
		return "host"
	case ckpType == "network":
		return "network"
	case ckpType == "group" || ckpType == "service-group" || ckpType == "network-group":
		return "group"
	case strings.HasPrefix(ckpType, "service-"):
		return "service"
	default:
		return "group"
	}
}

// mapAction maps the Checkpoint action name to the canonical
// {permit, deny} action vocabulary the push wire shape expects.
// "Accept" → "permit"; "Drop"/"Reject" → "deny"; any other shape falls
// through to the lowercased name (best-effort) so operator-customized action
// names degrade gracefully rather than dropping rules wholesale.
func mapAction(name string) string {
	switch name {
	case "Accept":
		return "permit"
	case "Drop", "Reject":
		return "deny"
	case "":
		// Defensive: an empty action name in the rulebase is an operator
		// or upstream bug. We surface it as "permit" so the rule is still
		// counted in path computation; the raw_blob preserves the truth
		// for forensics.
		return "permit"
	default:
		return strings.ToLower(name)
	}
}

// resolveAddrRefs collapses a slice of ckpRef into a comma-joined CIDR
// string for the normalized src_cidr / dst_cidr columns. Each ref is
// resolved via the objectsByUID map; unresolved refs fall back to the ref
// Name (Checkpoint emits "Any" verbatim for the universal sentinel). An
// empty ref slice → "any" → downstream maps to 0.0.0.0/0.
func resolveAddrRefs(refs []ckpRef, byUID map[string]ckpObject) string {
	if len(refs) == 0 {
		return "any"
	}
	parts := make([]string, 0, len(refs))
	for _, r := range refs {
		parts = append(parts, resolveAddrRef(r, byUID))
	}
	return strings.Join(parts, ",")
}

// resolveAddrRef resolves a single address ref. Host objects → "ip/32";
// network objects → "subnet/mask"; group objects → "group:<name>" placeholder
// (Phase 12 expands groups via the firewall_objects table). Unresolved →
// the ref's Name as-is.
func resolveAddrRef(r ckpRef, byUID map[string]ckpObject) string {
	if obj, ok := byUID[r.UID]; ok {
		switch {
		case obj.IPv4Address != "":
			return obj.IPv4Address + "/32"
		case obj.Subnet4 != "" && obj.MaskLength4 > 0:
			return obj.Subnet4 + "/" + strconv.Itoa(obj.MaskLength4)
		case len(obj.Members) > 0:
			return "group:" + obj.Name
		}
	}
	// Fall back to the ref's Name (covers the "Any" sentinel and any
	// dictionary-expanded refs whose object body wasn't included in the
	// objects payload).
	if r.Name == "Any" {
		return "any"
	}
	if r.Name != "" {
		return r.Name
	}
	return r.UID
}

// resolveSingleRef resolves a single (non-slice) ckpRef for the NAT
// src_translation / dst_translation fields. Empty refs collapse to "".
func resolveSingleRef(r ckpRef, byUID map[string]ckpObject) string {
	if r.UID == "" && r.Name == "" {
		return ""
	}
	if obj, ok := byUID[r.UID]; ok {
		if obj.IPv4Address != "" {
			return obj.IPv4Address
		}
		if obj.Subnet4 != "" && obj.MaskLength4 > 0 {
			return obj.Subnet4 + "/" + strconv.Itoa(obj.MaskLength4)
		}
		if obj.Name != "" {
			return obj.Name
		}
	}
	if r.Name != "" {
		return r.Name
	}
	return r.UID
}

// resolveServiceRefs picks the first service ref and resolves its protocol
// + ports from the objects dictionary. Subsequent refs are dropped at the
// normalized layer (Phase 12 consumes one service per rule); the raw_blob
// preserves the full list for vendor-native UI / forensics.
//
// Unknown service types degrade to an empty (proto, ports) pair so the rule
// is still emitted; the raw_blob captures the truth.
func resolveServiceRefs(refs []ckpRef, byUID map[string]ckpObject) (proto, ports string) {
	if len(refs) == 0 {
		return "", ""
	}
	r := refs[0]
	// The "Any" sentinel collapses to protocol="any", ports="".
	if r.Name == "Any" {
		return "any", ""
	}
	obj, ok := byUID[r.UID]
	if !ok {
		return "", ""
	}
	switch {
	case strings.HasPrefix(obj.Type, "service-tcp"):
		return "tcp", obj.Port
	case strings.HasPrefix(obj.Type, "service-udp"):
		return "udp", obj.Port
	case strings.HasPrefix(obj.Type, "service-icmp"):
		return "icmp", ""
	case strings.HasPrefix(obj.Type, "service-"):
		// service-other / service-dce-rpc / etc. — surface the trailing
		// discriminator so Phase 12 can decide whether to special-case.
		return strings.TrimPrefix(obj.Type, "service-"), obj.Port
	}
	return "", ""
}

// objectValueJSON marshals the meaningful sub-shape of an object into JSON
// for the push.FirewallObject.Value JSONB column. Hosts emit
// {"ipv4-address": ...}; networks emit {"subnet4": ..., "mask-length4": ...};
// groups emit {"members": [...]}; services emit {"port": ...}. The full
// vendor shape is preserved separately in RawBlob.
func objectValueJSON(o ckpObject) (json.RawMessage, error) {
	switch {
	case o.IPv4Address != "":
		return json.Marshal(map[string]string{"ipv4-address": o.IPv4Address})
	case o.Subnet4 != "" && o.MaskLength4 > 0:
		return json.Marshal(map[string]any{
			"subnet4":      o.Subnet4,
			"mask-length4": o.MaskLength4,
		})
	case len(o.Members) > 0:
		return json.Marshal(map[string]any{"members": o.Members})
	case o.Port != "":
		return json.Marshal(map[string]string{"port": o.Port})
	default:
		return json.Marshal(struct{}{})
	}
}

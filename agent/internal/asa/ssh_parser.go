// Package asa — ssh_parser.go: pure-function parser for Cisco ASA
// `show running-config` output. Linear-time line-by-line scan with a small
// state machine for multi-line object / object-group blocks. Non-matching
// lines are silently skipped (T-10-05-03 inheritance from Phase 10 ssh
// parser pattern). Never returns an error from the parsing itself; the
// returned error is reserved for catastrophic scanner failures (bufio buffer
// exhaustion on pathological input) so callers don't have to special-case
// huge configs going forward.
//
// Pattern source: agent/internal/ssh/parser.go (ParseShowIPRoute). The
// linear-regex strategy is documented in Phase 10 PATTERNS + RESEARCH and
// re-applied here per 11-PATTERNS.md Pattern G/H.
//
// Mitigations:
//   - T-11-09-03 (DoS via crafted output): all regexes have bounded
//     quantifiers and no backreferences; non-matching lines are dropped.
//   - T-11-09-05 (very large running-config): bufio.Scanner buffer is sized
//     to 1 MiB so single-line configs up to ~1 MB don't trip the default
//     64 KiB cap.
package asa

import (
	"bufio"
	"encoding/json"
	"net"
	"regexp"
	"strconv"
	"strings"

	"github.com/infracanvas/infracanvas/agent/internal/push"
)

// ─── Compiled regexes (MustCompile at package init) ───────────────────────
//
// Each pattern is anchored, uses bounded quantifiers (\S+, \s+, [a-z]+),
// and contains no backreferences. Submatch indices are documented inline.

// aclLineRE — extended ACL form. Captures:
//
//	1=name, 2=action(permit|deny), 3=protocol,
//	4=source spec, 5=destination spec, 6=optional port (after `eq`)
//
// The address-spec alternative `host \S+ | any4? | any6? | \S+\s+\S+ |
// object(-group)? \S+` is greedy left-to-right; `host`/`any[46]`/`object`
// are tried before the bare `\S+\s+\S+` (IP+mask) fallback.
var aclLineRE = regexp.MustCompile(
	`^access-list\s+(\S+)\s+extended\s+(permit|deny)\s+(\S+)\s+` +
		`(host\s+\S+|any4|any6|any|object-group\s+\S+|object\s+\S+|\S+\s+\S+)\s+` +
		`(host\s+\S+|any4|any6|any|object-group\s+\S+|object\s+\S+|\S+\s+\S+)` +
		`(?:\s+eq\s+(\S+))?`,
)

// natLineRE — single-line NAT form. Captures:
//
//	1=iface_in, 2=iface_out, 3=mode(dynamic|static),
//	4=original src, 5=translated src,
//	6=optional original dst (after `destination static`),
//	7=optional translated dst
var natLineRE = regexp.MustCompile(
	`^nat\s+\((\S+),(\S+)\)\s+source\s+(dynamic|static)\s+(\S+)\s+(\S+)` +
		`(?:\s+destination\s+static\s+(\S+)\s+(\S+))?`,
)

// objectStartRE — opens an `object network NAME` or `object service NAME`
// block. Captures: 1=kind(network|service), 2=name.
var objectStartRE = regexp.MustCompile(`^object\s+(network|service)\s+(\S+)`)

// objectGroupStartRE — opens an `object-group network NAME` or
// `object-group service NAME [proto]` block. Captures: 1=kind, 2=name.
var objectGroupStartRE = regexp.MustCompile(`^object-group\s+(network|service)\s+(\S+)`)

// objectHostRE — continuation line ` host <IP>` inside an `object network`.
// Leading whitespace is what marks it as a continuation. Captures: 1=IP.
var objectHostRE = regexp.MustCompile(`^\s+host\s+(\S+)`)

// objectSubnetRE — continuation line ` subnet <IP> <MASK>` inside an
// `object network`. Captures: 1=IP, 2=mask.
var objectSubnetRE = regexp.MustCompile(`^\s+subnet\s+(\S+)\s+(\S+)`)

// networkObjectRE — continuation line ` network-object <spec>` inside an
// `object-group network`. Captures: 1=spec (the rest of the line after the
// `network-object` keyword, raw — caller normalizes).
var networkObjectRE = regexp.MustCompile(`^\s+network-object\s+(.+)$`)

// ─── Pure-function entry point ────────────────────────────────────────────

// ParseRunningConfig scans an ASA `show running-config` text dump and
// returns three normalized slices: access-list rules, NAT rules, and
// host/network/group objects. The fourth return value is reserved for
// scanner errors (oversized lines exceeding the 1 MiB buffer); parser
// non-matches never surface as errors — those lines are silently dropped.
//
// Pure function: no I/O, no logging, deterministic in input. Safe to call
// concurrently.
func ParseRunningConfig(text string) (
	[]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error,
) {
	var (
		rules []push.FirewallRule
		nats  []push.FirewallNATRule
		objs  []push.FirewallObject

		ruleCount, natCount int

		// Active object/object-group block state. When non-empty,
		// continuation lines are accumulated; on any non-continuation
		// boundary the accumulated block is flushed to objs.
		curName    string
		curKind    string // "host" | "network" | "group" | "service"
		curBlock   string // "object" | "object-group"
		curValues  []string
		curRawLine string
	)

	flushObject := func() {
		if curName == "" {
			return
		}
		// Encode the accumulated value(s) as a JSON array of strings.
		// Single-value blocks (host/subnet) still emit a one-element array;
		// downstream consumers can pull element 0 if they expect a scalar.
		valueJSON, _ := json.Marshal(curValues)
		rawJSON, _ := json.Marshal(map[string]any{
			"line":   curRawLine,
			"name":   curName,
			"block":  curBlock,
			"values": curValues,
		})
		objs = append(objs, push.FirewallObject{
			Kind:    curKind,
			Name:    curName,
			Value:   valueJSON,
			RawBlob: rawJSON,
		})
		curName, curKind, curBlock, curRawLine = "", "", "", ""
		curValues = nil
	}

	scanner := bufio.NewScanner(strings.NewReader(text))
	// Mitigation T-11-09-05: bump max line length from default 64 KiB to
	// 1 MiB so abnormally long single-line config items don't trip Scan.
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)

	for scanner.Scan() {
		raw := strings.TrimRight(scanner.Text(), "\r")
		// Detect block continuation vs. a fresh top-level statement.
		// Continuation = line starts with whitespace AND we're inside a block.
		isContinuation := curName != "" && len(raw) > 0 &&
			(raw[0] == ' ' || raw[0] == '\t')

		// 1. Try ACL.
		if m := aclLineRE.FindStringSubmatch(raw); m != nil {
			flushObject()
			ruleCount++
			rules = append(rules, push.FirewallRule{
				Position: ruleCount,
				SrcCIDR:  normalizeAddressSpec(m[4]),
				DstCIDR:  normalizeAddressSpec(m[5]),
				Action:   m[2],
				Protocol: m[3],
				Ports:    m[6],
				RawBlob:  rawLineBlob(raw),
			})
			continue
		}

		// 2. Try NAT.
		if m := natLineRE.FindStringSubmatch(raw); m != nil {
			flushObject()
			natCount++
			n := push.FirewallNATRule{
				Position:       natCount,
				InterfaceIn:    m[1],
				InterfaceOut:   m[2],
				SrcTranslation: m[5],
				RawBlob:        rawLineBlob(raw),
			}
			if m[7] != "" {
				n.DstTranslation = m[7]
			}
			nats = append(nats, n)
			continue
		}

		// 3. Try `object network|service NAME`.
		if m := objectStartRE.FindStringSubmatch(raw); m != nil {
			flushObject()
			curName = m[2]
			curBlock = "object"
			// kind is provisionally set from the keyword; the continuation
			// line (host/subnet) refines it for the network case.
			if m[1] == "service" {
				curKind = "service"
			} else {
				curKind = "network"
			}
			curRawLine = raw
			continue
		}

		// 4. Try `object-group network|service NAME`.
		if m := objectGroupStartRE.FindStringSubmatch(raw); m != nil {
			flushObject()
			curName = m[2]
			curBlock = "object-group"
			curKind = "group"
			curRawLine = raw
			continue
		}

		// 5. Continuation lines inside an active object block.
		if isContinuation {
			if m := objectHostRE.FindStringSubmatch(raw); m != nil {
				curKind = "host"
				curValues = append(curValues, m[1]+"/32")
				continue
			}
			if m := objectSubnetRE.FindStringSubmatch(raw); m != nil {
				curKind = "network"
				curValues = append(curValues, ipMaskToCIDR(m[1], m[2]))
				continue
			}
			if m := networkObjectRE.FindStringSubmatch(raw); m != nil {
				curValues = append(curValues, normalizeAddressSpec(m[1]))
				continue
			}
			// Other continuation forms (port-object, service-object, etc.)
			// are silently captured into curValues as raw text so downstream
			// can still see them via raw_blob.
			curValues = append(curValues, strings.TrimSpace(raw))
			continue
		}

		// 6. Non-continuation, non-matching top-level line — close any open
		// block and drop the line. T-10-05-03: silent skip.
		if curName != "" {
			flushObject()
		}
	}
	// Flush trailing block on EOF.
	flushObject()

	if err := scanner.Err(); err != nil {
		return rules, nats, objs, err
	}
	return rules, nats, objs, nil
}

// ─── Helpers (pure) ───────────────────────────────────────────────────────

// rawLineBlob wraps the original config line as `{"line": "<line>"}` JSON
// so each push struct's raw_blob field preserves the vendor-native text
// for D-08 hybrid storage.
func rawLineBlob(line string) json.RawMessage {
	b, _ := json.Marshal(map[string]string{"line": line})
	return b
}

// normalizeAddressSpec converts an ASA address specification into a
// CIDR-shaped string where possible. Recognized forms:
//
//	"host 1.2.3.4"     → "1.2.3.4/32"
//	"any" / "any4"     → "0.0.0.0/0"
//	"any6"             → "::/0"
//	"1.2.3.4 255.0.0.0"→ "1.2.3.0/8"
//	"object NAME"      → "object:NAME"
//	"object-group N"   → "object-group:N"
//	"host NAME"        → "object:NAME"  (ASA accepts a named-object after
//	                     `host`; we surface it as an object ref so the
//	                     downstream resolver can join it back)
//
// Unrecognized inputs pass through verbatim so the raw_blob trail
// preserves the original text.
func normalizeAddressSpec(s string) string {
	s = strings.TrimSpace(s)
	switch s {
	case "any", "any4":
		return "0.0.0.0/0"
	case "any6":
		return "::/0"
	}
	tokens := strings.Fields(s)
	if len(tokens) == 0 {
		return s
	}
	switch tokens[0] {
	case "host":
		if len(tokens) < 2 {
			return s
		}
		if ip := net.ParseIP(tokens[1]); ip != nil {
			if ip.To4() != nil {
				return tokens[1] + "/32"
			}
			return tokens[1] + "/128"
		}
		// `host NAME` where NAME is an object reference.
		return "object:" + tokens[1]
	case "object":
		if len(tokens) < 2 {
			return s
		}
		return "object:" + tokens[1]
	case "object-group":
		if len(tokens) < 2 {
			return s
		}
		return "object-group:" + tokens[1]
	}
	// Two-token IP + mask form.
	if len(tokens) == 2 {
		return ipMaskToCIDR(tokens[0], tokens[1])
	}
	return s
}

// ipMaskToCIDR converts an IPv4 dotted-quad address + dotted-quad mask
// pair into prefix-length notation. Returns the original "ip mask" string
// joined by a space if either token fails to parse — the raw text still
// flows through raw_blob.
func ipMaskToCIDR(ipStr, maskStr string) string {
	ip := net.ParseIP(ipStr)
	if ip == nil {
		return ipStr + " " + maskStr
	}
	ip4 := ip.To4()
	if ip4 == nil {
		return ipStr + " " + maskStr
	}
	maskIP := net.ParseIP(maskStr)
	if maskIP == nil {
		return ipStr + " " + maskStr
	}
	mask4 := maskIP.To4()
	if mask4 == nil {
		return ipStr + " " + maskStr
	}
	bits, _ := net.IPv4Mask(mask4[0], mask4[1], mask4[2], mask4[3]).Size()
	return ip4.String() + "/" + strconv.Itoa(bits)
}

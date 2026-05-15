// types.go — internal wire-shape types for the Checkpoint Management API.
//
// These types decode the on-the-wire JSON emitted by both the live web_api
// endpoints (CKP-01: POST /web_api/show-access-rulebase etc.) and the offline
// mgmt_cli export (CKP-02: `mgmt_cli show access-rulebase --format json` redirected
// to a file). The D-12 architectural decision is that BOTH paths share the same
// parser, which in turn assumes a single shared internal type set. The paired
// Wave 0 fixtures (ckp-access-rulebase.json + ckp-access-rulebase-import.json)
// must decode equivalently here; if they diverge, TestParser_LiveImportEquivalence
// surfaces the regression before Wave 4.
//
// Field names follow Checkpoint's kebab-case JSON convention. Each top-level
// rule/object struct carries a `Raw json.RawMessage \`json:"-"\`` field that
// `parser.go` populates with the original vendor JSON via re-marshal, feeding
// the D-08 hybrid schema (normalized columns + raw_blob).
//
// Scope is locked to access rulebase + NAT rulebase + objects (host/network/
// group/service-*) per D-13. Threat-prevention layers, app control, identity
// awareness, URL filtering are intentionally absent — they are not on the
// path-asymmetry path.
package checkpoint

import "encoding/json"

// ─── Login ────────────────────────────────────────────────────────────────

// ckpLoginResp is the response to POST /web_api/login. The SID is the
// session identifier used in subsequent X-chkp-sid headers (D-14: live only,
// never persisted across pulls).
type ckpLoginResp struct {
	SID            string `json:"sid"`
	UID            string `json:"uid"`
	SessionTimeout int    `json:"session-timeout"`
}

// ─── Access rulebase ──────────────────────────────────────────────────────

// ckpAccessRulebaseResp is the envelope returned by POST /web_api/show-access-rulebase
// (also emitted by `mgmt_cli show access-rulebase --format json`). The
// pagination cursor is (From, To, Total); the loop in live.go pages until
// To >= Total.
type ckpAccessRulebaseResp struct {
	UID               string            `json:"uid,omitempty"`
	Name              string            `json:"name,omitempty"`
	Rulebase          []ckpAccessRule   `json:"rulebase"`
	From              int               `json:"from"`
	To                int               `json:"to"`
	Total             int               `json:"total"`
	ObjectsDictionary []json.RawMessage `json:"objects-dictionary,omitempty"`
}

// ckpAccessRule is a single access-rulebase row.
type ckpAccessRule struct {
	UID         string          `json:"uid"`
	Name        string          `json:"name,omitempty"`
	Type        string          `json:"type"`
	RuleNumber  int             `json:"rule-number"`
	Enabled     bool            `json:"enabled"`
	Source      []ckpRef        `json:"source,omitempty"`
	Destination []ckpRef        `json:"destination,omitempty"`
	Service     []ckpRef        `json:"service,omitempty"`
	Action      ckpActionRef    `json:"action"`
	Raw         json.RawMessage `json:"-"`
}

// ckpRef is a reference to an object dictionary entry. When
// `use-object-dictionary: true` is passed at request time the response
// expands references with Name + Type; otherwise only UID is populated.
type ckpRef struct {
	UID  string `json:"uid"`
	Name string `json:"name,omitempty"`
	Type string `json:"type,omitempty"`
}

// ckpActionRef is the action discriminator on an access rule. Name is one of
// "Accept", "Drop", "Reject", "Inline Layer" (the last is out of scope per
// D-13 and is mapped to a safe default).
type ckpActionRef struct {
	UID  string `json:"uid"`
	Name string `json:"name"`
}

// ─── NAT rulebase ─────────────────────────────────────────────────────────

// ckpNATRulebaseResp is the envelope returned by POST /web_api/show-nat-rulebase.
type ckpNATRulebaseResp struct {
	UID      string       `json:"uid,omitempty"`
	Name     string       `json:"name,omitempty"`
	Rulebase []ckpNATRule `json:"rulebase"`
	From     int          `json:"from"`
	To       int          `json:"to"`
	Total    int          `json:"total"`
}

// ckpNATRule is a single NAT-rulebase row. Checkpoint NAT is direction-based
// (original-* vs translated-*) — there are no explicit interface-in/out fields
// like ASA; install-on identifies which gateway enforces the rule.
type ckpNATRule struct {
	UID                    string          `json:"uid"`
	Type                   string          `json:"type"`
	RuleNumber             int             `json:"rule-number"`
	Enabled                bool            `json:"enabled"`
	Method                 string          `json:"method,omitempty"`
	OriginalSource         ckpRef          `json:"original-source,omitempty"`
	OriginalDestination    ckpRef          `json:"original-destination,omitempty"`
	OriginalService        ckpRef          `json:"original-service,omitempty"`
	TranslatedSource       ckpRef          `json:"translated-source,omitempty"`
	TranslatedDestination  ckpRef          `json:"translated-destination,omitempty"`
	TranslatedService      ckpRef          `json:"translated-service,omitempty"`
	InstallOn              []ckpRef        `json:"install-on,omitempty"`
	Raw                    json.RawMessage `json:"-"`
}

// ─── Objects ──────────────────────────────────────────────────────────────

// ckpObjectsResp is the envelope returned by POST /web_api/show-objects.
type ckpObjectsResp struct {
	Objects []ckpObject `json:"objects"`
	From    int         `json:"from"`
	To      int         `json:"to"`
	Total   int         `json:"total"`
}

// ckpObject is a host / network / group / service-* object. Only the
// type-relevant fields are populated; the rest are zero.
type ckpObject struct {
	UID         string          `json:"uid"`
	Name        string          `json:"name"`
	Type        string          `json:"type"`
	IPv4Address string          `json:"ipv4-address,omitempty"`
	Subnet4     string          `json:"subnet4,omitempty"`
	MaskLength4 int             `json:"mask-length4,omitempty"`
	Members     []ckpRef        `json:"members,omitempty"`
	Port        string          `json:"port,omitempty"`
	Raw         json.RawMessage `json:"-"`
}

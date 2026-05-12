// Wave 0 RED test stub — references checkpoint.Parse which does not exist yet.
// Plan 11-09 lands the production parser; this test is intentionally
// compile-RED until then.
//
// THIS IS THE LOAD-BEARING D-12 LOCK: paired live + import fixtures MUST
// produce equivalent parsed output, otherwise the "shared parser bridges
// CKP-01 + CKP-02" decision collapses.
//
// Pattern source: agent/internal/ssh/parser_test.go (fixture-from-disk)
package checkpoint

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/stretchr/testify/require"
)

// TestParser_LiveImportEquivalence locks the D-12 shared-parser premise:
// the live API response shape (ckp-access-rulebase.json) and the
// `mgmt_cli show ... --format json` offline export shape
// (ckp-access-rulebase-import.json) MUST yield identical parser output.
//
// If a future divergence emerges, the planner must either:
//   1. Reshape one fixture to match the other (preferred), or
//   2. Split into two parsers (kills D-12 — requires CONTEXT.md revisit).
//
// RED: references Parse which does not exist.
func TestParser_LiveImportEquivalence(t *testing.T) {
	liveRulebase := mustReadFixture(t, "ckp-access-rulebase.json")
	importRulebase := mustReadFixture(t, "ckp-access-rulebase-import.json")
	natRulebase := mustReadFixture(t, "ckp-nat-rulebase.json")
	objs := mustReadFixture(t, "ckp-objects.json")

	liveRules, liveNATs, liveObjs, err := Parse(liveRulebase, natRulebase, objs)
	require.NoError(t, err)

	importRules, importNATs, importObjs, err := Parse(importRulebase, natRulebase, objs)
	require.NoError(t, err)

	require.True(t,
		reflect.DeepEqual(liveRules, importRules),
		"D-12 lock: live and import fixtures must yield equivalent Rules (got live=%d import=%d)",
		len(liveRules), len(importRules),
	)
	require.True(t,
		reflect.DeepEqual(liveNATs, importNATs),
		"D-12 lock: NAT rulebase parsing equivalence",
	)
	require.True(t,
		reflect.DeepEqual(liveObjs, importObjs),
		"D-12 lock: objects parsing equivalence",
	)
}

// TestParser_RulebaseCounts: surface a minimum-counts contract on the
// canonical live fixture. Locks D-13 scope (access rules + NAT + objects).
//
// RED: references Parse which does not exist.
func TestParser_RulebaseCounts(t *testing.T) {
	liveRulebase := mustReadFixture(t, "ckp-access-rulebase.json")
	natRulebase := mustReadFixture(t, "ckp-nat-rulebase.json")
	objs := mustReadFixture(t, "ckp-objects.json")

	rules, nats, parsedObjs, err := Parse(liveRulebase, natRulebase, objs)
	require.NoError(t, err)
	require.GreaterOrEqual(t, len(rules), 3, "fixture has 3 access rules")
	require.GreaterOrEqual(t, len(nats), 2, "fixture has 2 NAT rules")
	require.GreaterOrEqual(t, len(parsedObjs), 5, "fixture has 8 objects (hosts + nets + groups + services)")
}

// -------- Helpers --------

func mustReadFixture(t *testing.T, name string) []byte {
	t.Helper()
	data, err := os.ReadFile(filepath.Join("testdata", name))
	require.NoError(t, err)
	return data
}

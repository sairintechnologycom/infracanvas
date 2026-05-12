// Wave 0 RED test stub — references checkpoint.LoadImport which does not
// exist yet. Plan 11-11 lands the production code; this test is
// intentionally compile-RED until then.
//
// Pattern source: agent/internal/config/import.go (mirror for `checkpoint-import`)
// D-12 lock: the import path MUST go through the same shared parser as the
// live API path, so TestImport_MatchesLiveShape is the parser-equivalence
// regression test from the LOADER side.
package checkpoint

import (
	"path/filepath"
	"reflect"
	"testing"

	"github.com/stretchr/testify/require"
)

// TestImport_MatchesLiveShape: loading the three offline export files
// through LoadImport must produce identical output to calling Parse on
// the equivalent live API fixtures. Proves D-12 import path goes through
// the shared parser.
//
// RED: references LoadImport which does not exist.
func TestImport_MatchesLiveShape(t *testing.T) {
	// Live path: read fixtures and parse directly.
	live := mustReadFixture(t, "ckp-access-rulebase.json")
	natFixture := mustReadFixture(t, "ckp-nat-rulebase.json")
	objsFixture := mustReadFixture(t, "ckp-objects.json")
	liveRules, liveNATs, liveObjs, err := Parse(live, natFixture, objsFixture)
	require.NoError(t, err)

	// Import path: load three on-disk files.
	rulebasePath := filepath.Join("testdata", "ckp-access-rulebase-import.json")
	natPath := filepath.Join("testdata", "ckp-nat-rulebase.json")
	objsPath := filepath.Join("testdata", "ckp-objects.json")
	importRules, importNATs, importObjs, err := LoadImport(rulebasePath, natPath, objsPath)
	require.NoError(t, err)

	require.True(t, reflect.DeepEqual(liveRules, importRules),
		"D-12 lock: LoadImport must produce parser-equivalent Rules")
	require.True(t, reflect.DeepEqual(liveNATs, importNATs),
		"D-12 lock: LoadImport must produce parser-equivalent NATs")
	require.True(t, reflect.DeepEqual(liveObjs, importObjs),
		"D-12 lock: LoadImport must produce parser-equivalent Objects")
}

// TestImport_MissingFile: LoadImport must surface a clear error when a
// referenced file is missing. Mirrors LoadConfigImport error prefix style.
//
// RED: references LoadImport which does not exist.
func TestImport_MissingFile(t *testing.T) {
	_, _, _, err := LoadImport(
		filepath.Join("testdata", "does-not-exist.json"),
		filepath.Join("testdata", "ckp-nat-rulebase.json"),
		filepath.Join("testdata", "ckp-objects.json"),
	)
	require.Error(t, err)
	// Error prefix MUST be "checkpoint-import:" to mirror "config-import:" precedent.
	require.Contains(t, err.Error(), "checkpoint-import:",
		"error prefix must mirror config-import: precedent, got: %q", err.Error())
}

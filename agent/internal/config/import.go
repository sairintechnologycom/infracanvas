// LoadConfigImport reads a static route file and returns []netconf.RouteRecord.
//
// Used when devices[].protocol == "config-import" — the air-gapped fallback
// (DCA-07) where an operator dumps `show ip route` output into a YAML file
// the agent reads in lieu of dialing a device. The on-disk shape is decoupled
// from the wire shape via configImportRoute → netconf.RouteRecord mapping so
// netconf/types.go stays JSON-tag-only.
package config

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"

	"github.com/infracanvas/infracanvas/agent/internal/netconf"
)

type configImportRoute struct {
	Prefix   string `yaml:"prefix"`
	NextHop  string `yaml:"next_hop"`
	Protocol string `yaml:"protocol"`
	Metric   int    `yaml:"metric"`
	ASPath   string `yaml:"as_path"`
}

type configImportFile struct {
	Routes []configImportRoute `yaml:"routes"`
}

// LoadConfigImport reads a static route YAML file and returns the contained
// RouteRecord slice. Empty files (routes: []) return an empty slice and nil
// error so the agent pushes empty batches rather than silently skipping.
func LoadConfigImport(path string) ([]netconf.RouteRecord, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("config-import: read %s: %w", path, err)
	}
	var f configImportFile
	if err := yaml.Unmarshal(data, &f); err != nil {
		return nil, fmt.Errorf("config-import: parse %s: %w", path, err)
	}
	out := make([]netconf.RouteRecord, 0, len(f.Routes))
	for _, r := range f.Routes {
		out = append(out, netconf.RouteRecord{
			Prefix:   r.Prefix,
			NextHop:  r.NextHop,
			Protocol: r.Protocol,
			Metric:   r.Metric,
			ASPath:   r.ASPath,
		})
	}
	return out, nil
}

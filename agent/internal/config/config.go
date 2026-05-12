// Package config loads agent.yaml and validates the device list.
//
// Schema is locked in 10-CONTEXT.md D-06. The loader rejects unknown protocols
// and missing required fields up-front so the daemon fails fast rather than
// discovering misconfiguration mid-collection.
package config

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

// Protocol values accepted in agent.yaml devices[].protocol.
const (
	ProtocolNetconf      = "netconf"
	ProtocolSSH          = "ssh"
	ProtocolConfigImport = "config-import"
	// Phase 11 — firewall protocols (D-16, D-04, D-05, D-12).
	// ProtocolCheckpointImport mirrors ProtocolConfigImport: file-based,
	// host-exempt, requires config_file.
	ProtocolASARest          = "asa-rest"
	ProtocolASASSH           = "asa-ssh"
	ProtocolFMC              = "fmc"
	ProtocolCheckpoint       = "checkpoint"
	ProtocolCheckpointImport = "checkpoint-import"
)

// Config is the top-level agent configuration loaded from agent.yaml.
type Config struct {
	SiteToken  string   `yaml:"site_token"`
	BackendURL string   `yaml:"backend_url"`
	Devices    []Device `yaml:"devices"`
}

// Device represents a single network device entry in the agent.yaml devices[] array.
type Device struct {
	Host       string `yaml:"host"`
	Port       int    `yaml:"port"`
	Protocol   string `yaml:"protocol"`
	Username   string `yaml:"username"`
	Password   string `yaml:"password"`
	ConfigFile string `yaml:"config_file"`
	SiteID     string `yaml:"site_id"`
}

// Load reads and validates agent.yaml from path.
// Returns an error if the file is missing, malformed, or fails validation.
func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("config: read %s: %w", path, err)
	}
	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("config: parse %s: %w", path, err)
	}
	if err := cfg.validate(); err != nil {
		return nil, fmt.Errorf("config: validate %s: %w", path, err)
	}
	return &cfg, nil
}

func (c *Config) validate() error {
	if c.SiteToken == "" {
		return fmt.Errorf("site_token required")
	}
	if c.BackendURL == "" {
		return fmt.Errorf("backend_url required")
	}
	for i, d := range c.Devices {
		switch d.Protocol {
		case ProtocolNetconf, ProtocolSSH, ProtocolConfigImport,
			ProtocolASARest, ProtocolASASSH, ProtocolFMC,
			ProtocolCheckpoint, ProtocolCheckpointImport:
			// ok
		default:
			return fmt.Errorf("device[%d]: invalid protocol: %s", i, d.Protocol)
		}
		if d.Protocol == ProtocolConfigImport && d.ConfigFile == "" {
			return fmt.Errorf("device[%d]: config_file required when protocol=config-import", i)
		}
		if d.Protocol == ProtocolCheckpointImport && d.ConfigFile == "" {
			return fmt.Errorf("device[%d]: config_file required when protocol=checkpoint-import", i)
		}
		if d.Protocol != ProtocolConfigImport && d.Protocol != ProtocolCheckpointImport && d.Host == "" {
			return fmt.Errorf("device[%d]: host required when protocol=%s", i, d.Protocol)
		}
	}
	return nil
}

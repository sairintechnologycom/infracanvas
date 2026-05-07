package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
)

const fullYAML = `
site_token: "ic_site_xxxxxxxx"
backend_url: "https://api.infracanvas.dev"
devices:
  - host: "192.168.1.1"
    port: 830
    protocol: netconf
    username: "ro"
    password: "secret"
  - host: "192.168.1.2"
    port: 22
    protocol: ssh
    username: "ro"
    password: "secret"
  - host: "sw-core"
    protocol: config-import
    config_file: "/etc/infracanvas/sw-core.yaml"
`

func writeTmp(t *testing.T, body string) string {
	t.Helper()
	f := filepath.Join(t.TempDir(), "agent.yaml")
	require.NoError(t, os.WriteFile(f, []byte(body), 0o600))
	return f
}

func TestConfigLoad(t *testing.T) {
	path := writeTmp(t, fullYAML)
	cfg, err := Load(path)
	require.NoError(t, err)
	require.Equal(t, "ic_site_xxxxxxxx", cfg.SiteToken)
	require.Equal(t, "https://api.infracanvas.dev", cfg.BackendURL)
	require.Len(t, cfg.Devices, 3)
	require.Equal(t, ProtocolNetconf, cfg.Devices[0].Protocol)
	require.Equal(t, ProtocolSSH, cfg.Devices[1].Protocol)
	require.Equal(t, ProtocolConfigImport, cfg.Devices[2].Protocol)
}

func TestConfigLoadMissingSiteToken(t *testing.T) {
	path := writeTmp(t, "backend_url: https://x\ndevices: []\n")
	_, err := Load(path)
	require.Error(t, err)
	require.True(t, strings.Contains(err.Error(), "site_token required"), err.Error())
}

func TestConfigLoadMissingBackendURL(t *testing.T) {
	path := writeTmp(t, "site_token: x\ndevices: []\n")
	_, err := Load(path)
	require.Error(t, err)
	require.Contains(t, err.Error(), "backend_url required")
}

func TestConfigLoadInvalidProtocol(t *testing.T) {
	body := "site_token: x\nbackend_url: https://x\ndevices:\n  - host: a\n    protocol: ftp\n"
	path := writeTmp(t, body)
	_, err := Load(path)
	require.Error(t, err)
	require.Contains(t, err.Error(), "invalid protocol: ftp")
}

func TestConfigLoadConfigImportRequiresFile(t *testing.T) {
	body := "site_token: x\nbackend_url: https://x\ndevices:\n  - host: a\n    protocol: config-import\n"
	path := writeTmp(t, body)
	_, err := Load(path)
	require.Error(t, err)
	require.Contains(t, err.Error(), "config_file required")
}

func TestConfigLoadNonexistentFile(t *testing.T) {
	_, err := Load("/no/such/path/agent.yaml")
	require.Error(t, err)
	require.Contains(t, err.Error(), "config: read")
}

// TestConfigImport: filter devices by protocol=config-import.
// Full RED implementation lives in plan 10-05; this test locks the loader's protocol enum.
func TestConfigImport(t *testing.T) {
	path := writeTmp(t, fullYAML)
	cfg, err := Load(path)
	require.NoError(t, err)
	var imported []Device
	for _, d := range cfg.Devices {
		if d.Protocol == ProtocolConfigImport {
			imported = append(imported, d)
		}
	}
	require.Len(t, imported, 1)
	require.Equal(t, "/etc/infracanvas/sw-core.yaml", imported[0].ConfigFile)
}

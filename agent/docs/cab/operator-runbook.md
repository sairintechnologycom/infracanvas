# Operator Runbook — DC Agent Deployment

**Audience:** A site operator deploying the InfraCanvas DC Agent at a
customer's data centre.
**Goal:** A minimum-viable end-to-end deployment for Phase 10.
**Estimated time:** ≈ 20 minutes for a single-host install with one
NETCONF target and one NetFlow exporter.

This runbook is written so a junior SRE can follow it without prior
exposure to the InfraCanvas internals. If a step assumes knowledge that
your team does not have, please flag it back to InfraCanvas — that is a
runbook gap.

## Prerequisites

- A Linux amd64 or macOS arm64 host on the management VLAN.
- Outbound HTTPS reachability from the agent host to
  `api.infracanvas.dev` on port 443/tcp.
- Inbound UDP reachability on port 2055 from NetFlow exporters (only
  required if you intend to collect flow data).
- SSH (port 22) or NETCONF (port 830) reachability from the agent host
  to each target device.
- A team-owner account on the InfraCanvas SaaS dashboard.
- `curl`, `chmod`, and a text editor (`nano`, `vim`, …) on the agent
  host.

## Step 1 — Provision a site token

On a workstation with `curl`:

```bash
# Replace TEAM_OWNER_JWT with a Clerk session JWT for a team owner.
curl -X POST https://api.infracanvas.dev/v1/sites \
  -H "Authorization: Bearer TEAM_OWNER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"name": "dc-east-1"}'
```

Response (the `site_token` is shown ONCE — store it now in your
secrets manager):

```json
{
  "site_id": "uuid",
  "name": "dc-east-1",
  "site_token": "ic_site_abcdef..."
}
```

Treat `site_token` like a long-lived bearer secret. If it leaks, delete
the corresponding `dc_sites` row to revoke and reissue (see
[known-limitations.md](./known-limitations.md) L-3).

## Step 2 — Place agent.yaml

On the agent host:

```bash
sudo mkdir -p /etc/infracanvas
sudo $EDITOR /etc/infracanvas/agent.yaml
```

Paste a config based on the example shipped with the agent at
`agent/agent.yaml.example`, substituting the `site_token` from Step 1
and your device credentials.

Then lock down permissions:

```bash
sudo chmod 600 /etc/infracanvas/agent.yaml
sudo chown root:root /etc/infracanvas/agent.yaml
```

> **Important:** the `chmod 600` is the *only* protection on plaintext
> credentials in Phase 10 (see [known-limitations.md](./known-limitations.md)
> L-2). Do not skip it. Step 5 (systemd) explains how to widen ownership
> to the dedicated service account while keeping the file mode.

## Step 3 — Install the agent binary

Download the appropriate release binary:

```bash
# Linux amd64:
sudo curl -fsSL \
  https://github.com/infracanvas/infracanvas/releases/latest/download/infracanvas-agent-linux-amd64 \
  -o /usr/local/bin/infracanvas-agent
sudo chmod 755 /usr/local/bin/infracanvas-agent

# macOS arm64:
curl -fsSL \
  https://github.com/infracanvas/infracanvas/releases/latest/download/infracanvas-agent-macos-arm64 \
  -o /usr/local/bin/infracanvas-agent
chmod 755 /usr/local/bin/infracanvas-agent
```

Verify the binary version:

```bash
/usr/local/bin/infracanvas-agent version
```

Expected output: a semver string matching the release tag (for example
`v0.1.0`).

> **Hardening:** for sensitive sites, verify the SHA-256 of the
> downloaded binary against the hash recorded in this packet's
> [sbom.cyclonedx.json](./sbom.cyclonedx.json) metadata before
> proceeding. See [known-limitations.md](./known-limitations.md) L-7.

## Step 4 — Verify connectivity (one-shot)

Run a one-shot test (Ctrl-C to exit after the first push cycle):

```bash
sudo /usr/local/bin/infracanvas-agent run --config /etc/infracanvas/agent.yaml
```

Within five minutes you should see structured JSON logs that include:

- `agent_starting` (with version + device count)
- `netflow_listener_started` (if NetFlow is configured)
- `route_collected` and `push_routes_ok` (one per device per cycle)

On the SaaS side, the dashboard's `dc_sites` row for this site should
show recent activity. (Phase 11+ will add a UI; until then, ask
InfraCanvas support to confirm receipt against the structured-log
drain.)

## Step 5 — Install as a systemd service (Linux)

Create `/etc/systemd/system/infracanvas-agent.service`:

```ini
[Unit]
Description=InfraCanvas DC Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=infracanvas
Group=infracanvas
ExecStart=/usr/local/bin/infracanvas-agent run --config /etc/infracanvas/agent.yaml
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadOnlyPaths=/etc/infracanvas
RestrictAddressFamilies=AF_INET AF_INET6
LockPersonality=true

[Install]
WantedBy=multi-user.target
```

Create the unprivileged service account, hand it ownership of the
config (so it can read it), and re-lock the file mode:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin infracanvas
sudo chown infracanvas:infracanvas /etc/infracanvas/agent.yaml
sudo chmod 600 /etc/infracanvas/agent.yaml

sudo systemctl daemon-reload
sudo systemctl enable --now infracanvas-agent
```

Verify:

```bash
sudo systemctl status infracanvas-agent
sudo journalctl -u infracanvas-agent -f
```

> **macOS hosts:** there is no `systemd` on macOS; deploy the agent via
> `launchd` plist (template available on request from InfraCanvas
> support) or under a process supervisor of the operator's choice.

## Step 6 — Firewall rules

| Direction | Port/Proto | Peer | Required for |
|-----------|-----------|------|--------------|
| Outbound  | 443/tcp   | `api.infracanvas.dev` | Push (always required) |
| Outbound  | 830/tcp   | NETCONF devices | If using `protocol: netconf` |
| Outbound  | 22/tcp    | SSH-only devices | If using `protocol: ssh` |
| Inbound   | 2055/udp  | NetFlow exporters | If collecting NetFlow |

Iptables example (Linux), restricting NetFlow ingress to a known
exporter CIDR:

```bash
sudo iptables -A INPUT -p udp --dport 2055 -s <netflow-exporter-cidr> -j ACCEPT
sudo iptables -A INPUT -p udp --dport 2055 -j DROP
```

`firewalld` example:

```bash
sudo firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=<exporter-cidr> port port=2055 protocol=udp accept'
sudo firewall-cmd --reload
```

## Step 7 — Healthchecks (optional but recommended)

Add a cron task that alerts if the systemd service is not active:

```bash
*/15 * * * * systemctl is-active --quiet infracanvas-agent || \
  mail -s "InfraCanvas agent down" ops@example.com < /dev/null
```

Alternatively, scrape `journalctl -u infracanvas-agent` into your
existing log-aggregation tool and alert on the absence of
`push_routes_ok` events for more than two ticker cadences (10 min).

## Troubleshooting

| Symptom | Likely cause | Remedy |
|---------|-------------|--------|
| `config: read /etc/infracanvas/agent.yaml: permission denied` | systemd `User=` cannot read a 600-mode file owned by root | `sudo chown infracanvas /etc/infracanvas/agent.yaml` (Step 5 covers this) |
| All pushes fail 401 `invalid_site_token` | Token revoked or wrong | Re-issue via `POST /v1/sites`; update `agent.yaml`; restart |
| NetFlow buffer always empty | Exporters not configured to send to agent IP/port 2055 | Configure exporters with the agent's IP as collector destination |
| `netflow_decode_error` repeatedly | Exporter sending NetFlow v5 (unsupported) | v5 deferred to Phase 11+; reconfigure exporters to use v9 or IPFIX |
| Routes only contain 24 entries | IOS-XE pager truncation | Phase 10 sends `terminal length 0` automatically; legacy IOS may need it set per-account |
| TLS handshake error to `api.infracanvas.dev` | Corporate proxy without trust-store update | Ensure system trust store includes the public CA chain; consider adding `HTTPS_PROXY` |

## Decommissioning

To stop collecting from this site:

```bash
sudo systemctl disable --now infracanvas-agent
sudo rm /etc/infracanvas/agent.yaml
sudo userdel infracanvas
sudo rm /usr/local/bin/infracanvas-agent /etc/systemd/system/infracanvas-agent.service
sudo systemctl daemon-reload
```

Then revoke the site token on the SaaS side. In Phase 10 this requires
contacting InfraCanvas support to delete the `dc_sites` row; Phase 11+
will add a self-service revoke button in the dashboard UI.

## Operational notes

- The agent does not write to disk during normal operation. The
  `systemd` `ProtectSystem=strict` and `ReadOnlyPaths=/etc/infracanvas`
  hardening lines reflect this and are safe to enable.
- The agent does not require root once installed. `User=infracanvas`
  with the file ownership change in Step 5 is the recommended posture.
- The agent is a single binary with no shared-library dependencies
  (`CGO_ENABLED=0`). It does not write `/var/run` PID files or
  `/var/log` logs — all state is journald-managed.

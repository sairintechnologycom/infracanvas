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

---

## Firewall Devices (Phase 11)

Phase 11 adds four firewall vendors (Cisco ASA, Cisco FMC,
Checkpoint live, Checkpoint offline import) via **five new
`protocol:` values** on the existing `devices[]` array. No new
top-level `agent.yaml` field is required. Firewall pulls run on a
**4th ticker at 1h cadence** alongside the Phase 10 Routes / BGP /
Flow tickers.

### Step F1 — Extend `agent.yaml` with firewall devices

```yaml
# Phase 10 fields stay unchanged:
site_token: "ic_site_..."
backend_url: "https://api.infracanvas.dev"

devices:
  # ----- Phase 10 (routes/flows) — unchanged -----
  - host: "rtr-edge-01.dc1"
    port: 830
    protocol: netconf
    username: "infracanvas-ro"
    password: "REPLACE_ME"

  # ----- Phase 11: Cisco ASA REST -----
  # Works on ASA 9.3(2) through 9.16 ONLY. ASA 9.17+ removed the REST API
  # (see L-11-01); use 'asa-ssh' for those devices.
  - host: "asa-edge-01.dc1"
    port: 443
    protocol: asa-rest
    username: "infracanvas-ro"
    password: "REPLACE_ME"

  # ----- Phase 11: Cisco ASA SSH (universal — works on all ASA versions) -----
  # Required for ASA 9.17+; equally valid on older ASA if SSH is preferred.
  - host: "asa-edge-02.dc1"
    port: 22
    protocol: asa-ssh
    username: "infracanvas-ro"
    password: "REPLACE_ME"

  # ----- Phase 11: Cisco FMC -----
  # The agent uses the first DOMAIN_UUID + first access policy + first NAT
  # policy returned by the FMC auth and list endpoints (see L-11-04).
  - host: "fmc.corp.example"
    port: 443
    protocol: fmc
    username: "infracanvas-ro"
    password: "REPLACE_ME"

  # ----- Phase 11: Checkpoint Management API (live) -----
  # Login-per-pull lifecycle. SID is held in memory for the pull duration
  # only and is logged out at the end of each tick (D-14). No SID at rest.
  - host: "cp-mgmt.corp.example"
    port: 443
    protocol: checkpoint
    username: "infracanvas-ro"
    password: "REPLACE_ME"

  # ----- Phase 11: Checkpoint offline import (air-gapped) -----
  # See Step F3 for how to produce the three sibling files.
  - host: "cp-mgmt-airgap"
    protocol: checkpoint-import
    config_file: "/etc/infracanvas/cp-airgap.rulebase.json"
    # The agent will look for ALL THREE of:
    #   /etc/infracanvas/cp-airgap.rulebase.json
    #   /etc/infracanvas/cp-airgap.nat.json
    #   /etc/infracanvas/cp-airgap.objects.json
    # The `config_file` may alternatively be the base prefix
    # `/etc/infracanvas/cp-airgap` (no extension) — the agent appends
    # the three suffixes itself.
```

Re-lock the permissions after editing:

```bash
sudo chmod 600 /etc/infracanvas/agent.yaml
sudo chown infracanvas:infracanvas /etc/infracanvas/agent.yaml
```

> **Important:** the same `chmod 600` trust-boundary that protects
> Phase 10 device credentials (see [known-limitations.md](./known-limitations.md)
> L-2) is the only protection on the new firewall mgmt credentials in
> Phase 11. The agent does **not** write any of these credentials to
> disk beyond the `agent.yaml` you just edited.

### Step F2 — Use read-only firewall mgmt accounts

Create dedicated read-only service accounts on each firewall vendor's
management plane. The agent only issues `show` / GET / `show-*`
commands; a write-capable account is over-privileged and a credential
leak yields more authority than necessary.

| Vendor | Recommended role | Reviewer-verifiable grep |
|---|---|---|
| Cisco ASA (REST) | Read-only `aaa authorization` group | `grep -E '"POST"\|"PATCH"\|"PUT"' agent/internal/asa/rest.go` returns only the `/api/tokenservices` auth call and the cleanup `DELETE`. |
| Cisco ASA (SSH) | Privilege level 1 (read-only) account | `grep -E 'configure terminal\|write memory' agent/internal/asa/ssh.go` returns empty. |
| Cisco FMC | "Security Analyst (Read Only)" predefined role | `grep -E '"POST"\|"PATCH"\|"PUT"' agent/internal/fmc/client.go` returns only the `generatetoken` / `refreshtoken` auth calls. |
| Checkpoint | Read-only API administrator | `grep -E 'add-\|set-\|delete-\|publish' agent/internal/checkpoint/live.go` returns empty. |

The structural read-only posture is documented in the
[threat-model.md](./threat-model.md) "Phase 11 — Firewall Management
Credential Storage" section.

### Step F3 — Generate `checkpoint-import` files (air-gapped Checkpoint only)

If you have a Checkpoint mgmt server that cannot be reached from the
agent host (or you prefer to dump the rule-base manually on a
change-control cadence rather than allowing live API access), use the
`checkpoint-import` protocol.

On the Checkpoint mgmt host (or any host with `mgmt_cli` and reachability
to the mgmt server):

```bash
mgmt_cli login user "$U" password "$P" > session.txt

# Replace "Standard" with your actual layer/package name.
mgmt_cli show access-rulebase name "Standard" details-level "full" \
    --format json -s session.txt > cp-airgap.rulebase.json

mgmt_cli show nat-rulebase package "Standard" --format json \
    -s session.txt > cp-airgap.nat.json

mgmt_cli show objects type any details-level "full" \
    --format json -s session.txt > cp-airgap.objects.json

mgmt_cli logout -s session.txt
```

Copy the three files to the agent host:

```bash
sudo cp cp-airgap.rulebase.json /etc/infracanvas/
sudo cp cp-airgap.nat.json      /etc/infracanvas/
sudo cp cp-airgap.objects.json  /etc/infracanvas/
sudo chown infracanvas:infracanvas /etc/infracanvas/cp-airgap.*.json
sudo chmod 600 /etc/infracanvas/cp-airgap.*.json
```

Re-run on whatever cadence your change-control window dictates. The
agent re-reads the files on every 1h firewall tick, so an updated set
of files lands in the SaaS backend within an hour of being placed on
the agent host (no agent restart required).

### Step F4 — Verify firewall pulls

After restarting the agent (or waiting up to 1h for the next firewall
tick), watch the agent and backend logs.

**On the agent host:**

```bash
sudo journalctl -u infracanvas-agent -f | grep firewall
```

Expected log lines per device per tick (zap structured JSON):

- `firewall_pull_start` with `device` and `protocol` fields
- `firewall_pull_ok` with `device`, `protocol`, `rules_count`,
  `nat_count`, `objects_count`, and a single shared `snapshot_id`
- `push_firewall_rules_ok` / `push_firewall_nat_ok` /
  `push_firewall_objects_ok` — three pushes per device, all carrying
  the SAME `snapshot_id` (this is the RESEARCH Pattern 2 lock)

**On the backend side** (if you have InfraCanvas support visibility,
or run a local backend per the smoke-test instructions):

```
agent_firewall_rules_received   ... site_id=... snapshot_id=... count=N
agent_firewall_nat_received     ... site_id=... snapshot_id=... count=N
agent_firewall_objects_received ... site_id=... snapshot_id=... count=N
```

All three should share the same `snapshot_id` per device per pull.

**Read API verification** (Clerk-JWT-authenticated; replace placeholders):

```bash
curl -H "Authorization: Bearer $CLERK_JWT" \
  "https://api.infracanvas.dev/v1/sites/$SITE_ID/firewall-rules" \
  | jq '.[] | {firewall_id, vendor, source, snapshot_ts, rule_count: (.rules | length)}'
```

Expect one entry per configured firewall device on this site, showing
the latest snapshot.

### Step F5 — Firewall mgmt credential rotation

The procedure mirrors the Phase 10 site-token rotation in spirit but
applies to vendor mgmt credentials.

1. **Rotate the password on the firewall mgmt plane:**
   - ASA: `aaa authentication` workflow, or the local-user `password` command, or via your AAA back-end (TACACS+ / RADIUS).
   - FMC: System → Users → edit the `infracanvas-ro` user.
   - Checkpoint: SmartConsole → Users / API → update the API user's password.
2. **Update `agent.yaml`** with the new password for the affected
   `devices[]` entry. Preserve `chmod 600` afterwards:
   ```bash
   sudo $EDITOR /etc/infracanvas/agent.yaml
   sudo chmod 600 /etc/infracanvas/agent.yaml
   sudo chown infracanvas:infracanvas /etc/infracanvas/agent.yaml
   ```
3. **Reload the agent.** Currently this is a process restart:
   ```bash
   sudo systemctl reload infracanvas-agent || sudo systemctl restart infracanvas-agent
   # If you manage the agent outside systemd, send SIGHUP if your supervisor maps it;
   # otherwise a clean stop + start is equivalent.
   ```
4. **Watch the next firewall tick** (within the next hour) for a
   successful `firewall_pull_ok` on the rotated device. If you see
   401 persisting after the next tick, the password update did not
   take effect — re-verify Step 1 and Step 2.

> The agent does not buffer the old credentials anywhere — they are
> read from `agent.yaml` once at startup and on each reload. There is
> no on-disk credential cache to clean up.

### Step F6 — Firewall troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| 404 or 401 "REST API disabled" from `asa-rest` device | ASA 9.17+ removed the REST API (L-11-01) | Switch the device's `protocol:` to `asa-ssh` in `agent.yaml`; reload the agent. |
| 401 from FMC mid-pull after several successful pulls | FMC access-token TTL (30 min) exceeded; refresh failed (3 refresh attempts already used) | Agent will auto-re-acquire on the next firewall tick. If 401s persist beyond one full tick, check that the FMC `infracanvas-ro` user is not locked or password-expired. |
| 401 mid-pull from Checkpoint, especially on `show-objects` after several successful pages | Checkpoint SID timeout on a very large rule layer (L-11-02) | Agent already passes the max `session-timeout: 3600` at login. For layers that legitimately exceed an hour to pull, switch to `checkpoint-import` and generate the files out-of-band (Step F3). |
| `checkpoint-import: read <path>: no such file or directory` | Sibling file naming mismatch (L-11-03) | Confirm all three files exist with the exact suffixes `.rulebase.json` / `.nat.json` / `.objects.json` in the same directory as the path in `agent.yaml`. The dispatcher derives sibling paths from the base; misnamed siblings surface as missing-file errors. |
| `asa-ssh` parser returns suspiciously few rules | ASA pager truncation (Phase 11 Pitfall 4) | The agent sends `terminal pager 0` automatically before `show running-config`; if you still see truncation, check the `infracanvas-ro` user's AAA-bound default `terminal pager` setting on the device. Submit a sample anonymized config to InfraCanvas support if rules are present in the running-config but missing from the agent's parse output. |
| Backend logs no `agent_firewall_*_received` lines after 1h | Firewall ticker not firing or all devices using non-firewall protocols | Verify at least one device in `agent.yaml` has a firewall `protocol:` value; the ticker fires regardless of device count but the dispatcher's `firewallCollectorFor` returns `nil` for non-firewall protocols and silently skips them. |
| `device[N]: invalid protocol: <typo>` at agent start-up | Phase 11 validation switch rejects unknown protocol values (T-11-06-01) | Fix the typo in `agent.yaml`. Valid values are exactly: `netconf`, `ssh`, `config-import`, `asa-rest`, `asa-ssh`, `fmc`, `checkpoint`, `checkpoint-import`. |
| `device[N]: config_file required when protocol=checkpoint-import` at start-up | `protocol: checkpoint-import` declared without `config_file:` | Add `config_file: /etc/infracanvas/<base>.rulebase.json` (or the base-prefix form) to the device entry. |

### Step F7 — Firewall pull cadence notes

- Firewall pulls fire **every 1 hour**, fixed (Phase 11 D-02). This
  is deliberately distinct from the Phase 10 cadences (routes 5m /
  BGP 1m / flows 30s). Firewall rule bases change at change-control
  cadence, not minute-by-minute.
- Per-device pull duration is typically under one minute for small
  rule bases (≤ 1000 rules) and can stretch to several minutes for
  Checkpoint mgmt servers with very large policies. The 1h cadence
  provides comfortable headroom in all realistic deployments
  (T-11-07-01 acceptance).
- The agent waits for all pulls to drain on shutdown (`sync.WaitGroup`,
  T-11-07-02 mitigation). A graceful stop may take up to the longest-
  running pull's wall time, capped by per-request HTTP/SSH timeouts.

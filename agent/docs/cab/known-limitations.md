# Known Limitations

The InfraCanvas DC Agent is shipped with the following acknowledged
limitations. Each has a documented remediation path; the enterprise
tier (v1.2+) addresses the most security-significant ones.

This document covers two phases:

- **Phase 10** (DC Agent Core — route + flow collection) — limitations
  L-1 through L-7 below.
- **Phase 11** (firewall integration — ASA + FMC + Checkpoint) —
  limitations L-11-01 through L-11-05 in the "Phase 11 Firewall
  Integration" section at the end of this document.

The list is exhaustive for the current baseline. If a reviewer
identifies a residual not listed here, it is a packet gap — please flag
it back to InfraCanvas so this document can be updated.

## L-1: SSH host-key verification disabled

**What:** The agent uses `ssh.InsecureIgnoreHostKey()` for both NETCONF
(port 830/tcp) and SSH-CLI fallback (port 22/tcp) connections to network
devices.

**Risk:** A network adversary capable of TCP MITM on the management VLAN
could impersonate a device and either (a) capture device credentials
sent during SSH authentication, or (b) feed crafted route data to the
agent.

**Why this posture in Phase 10:** Operators commonly run agents on the
same management VLAN as devices, where the trust assumption is "no
untrusted hosts on this VLAN". A `known_hosts` workflow requires a
one-time human-trusted bootstrap, increasing deployment friction during
the initial pilot phase.

**Operator mitigations available today:**

- Deploy the agent on the same management VLAN as the devices so MITM
  requires VLAN-level compromise.
- Use ACLs to ensure only the management VLAN can reach 22/tcp and
  830/tcp on the devices.
- Use dedicated read-only NETCONF / SSH service accounts so MITM yields
  no escalation beyond read-only telemetry that the SaaS already
  receives.

**Future remediation:** The enterprise tier will add `known_hosts` /
`FixedHostKey` verification, with a one-shot bootstrap subcommand
(`infracanvas-agent learn-hosts`) for operators who want
certificate-equivalent identity on the SSH / NETCONF channel.

## L-2: Device credentials stored plaintext on agent host

**What:** `agent.yaml` contains plaintext SSH / NETCONF passwords for
each device the agent collects from. The file is protected only by
Unix file permissions (`chmod 600`).

**Risk:** Anyone with root access on the agent host can read device
credentials. A compromised agent host yields all configured device
credentials.

**Why this posture in Phase 10:** OS-keyring integration is platform-
specific (gnome-keyring on Linux, Keychain on macOS, no equivalent on
bare-metal Linux servers without a desktop session). Phase 10 ships
with the operator-managed-secrets posture for compatibility breadth.

**Operator mitigations available today:**

- `chmod 600` the `agent.yaml` (operator-runbook Step 2).
- Use read-only NETCONF / SSH service accounts so a credential leak
  yields read-only telemetry, not config-write capability.
- Run the agent process as a non-root user via `systemd User=` (see
  operator-runbook Step 5).
- Use full-disk encryption on the agent host so an offline disk
  acquisition does not yield credentials.

**Future remediation:** Enterprise tier will support SSH-key-based auth
for SSH / NETCONF (no passwords in `agent.yaml`) and HashiCorp Vault /
AWS SSM Parameter Store / GCP Secret Manager integration for credential
retrieval at runtime.

## L-3: Site token has no automatic rotation

**What:** The site token issued by `POST /v1/sites` is long-lived and
has no expiry. The operator must manually rotate by:

1. Issuing a new token via `POST /v1/sites` (creates a new site row).
2. Updating `agent.yaml` with the new token.
3. Restarting the agent.
4. Deleting the old `dc_sites` row to revoke the old token.

**Risk:** A token leak (e.g. via `agent.yaml` exfiltration or a backup
restore mishap) is exploitable indefinitely until manual operator
action revokes the row.

**Operator mitigations available today:**

- Audit the `dc_sites` table monthly; delete unused or stale tokens.
- Use a token-naming convention (e.g. `dc-east-2026-q2`) so operators
  can identify which site is at risk.
- Monitor the structured-log drain (Axiom) for unexpected `site_id`
  activity in `agent_routes_received` and `agent_flows_received` events.

**Future remediation:** Enterprise tier will add a token-rotation API
(`POST /v1/sites/{id}/rotate-token`), automatic expiry (90-day
default), and a refresh-token model.

## L-4: NetFlow data not encrypted in transit

**What:** NetFlow v9 / IPFIX is a UDP-only legacy protocol that does
**not** encrypt the wire payload.

**Risk:** Anyone on the network path between exporters and the agent
can passively observe flow records. Flow records are 5-tuple metadata
(source IP, dest IP, ports, protocol, byte / packet counts) — not
packet contents, not user data — but they are operational telemetry
that some compliance regimes treat as sensitive.

**Why this posture in Phase 10:** NetFlow is the de-facto standard for
network telemetry, and exporters in widespread field deployment do not
support encrypted variants (IPFIX-over-DTLS / IPFIX-over-TLS exists but
field deployment is rare).

**Operator mitigations available today:**

- Deploy the agent on the same management VLAN as the exporters
  (defense in depth — same advice as L-1).
- Use IPSec or VLAN-level isolation if NetFlow traverses untrusted
  segments.
- Bind the agent's NetFlow listener to a specific interface on the
  management VLAN rather than `0.0.0.0`.

**Future remediation:** Encrypted-NetFlow ingest (IPFIX-over-DTLS) is
not currently on the roadmap because exporter support is sparse.
Customer requests will reprioritize.

## L-5: No persistent NetFlow storage

**What:** The NetFlow ring buffer is in-memory only. If the agent
crashes or restarts, the un-flushed buffer (up to 30 seconds' worth) is
lost.

**Risk:** Operational data loss only — no security impact. Flows in
that 30-second window do not appear in the SaaS dashboard.

**Why this posture in Phase 10:** A disk-backed queue adds dependency
surface (SQLite + corruption recovery + lifecycle management) for a
30-second loss window, which trades poorly during the pilot phase.

**Future remediation:** Disk-backed queue is on the Phase 10+
deferred-items list.

## L-6: No mTLS to backend

**What:** Backend authentication is bearer-token only (`Authorization:
Bearer site_token`), not mTLS.

**Risk:** A bearer-token leak yields full push capability for the
affected site until manual revocation. mTLS would require the attacker
to also possess the per-site client certificate **and** its private key.

**Why this posture in Phase 10:** mTLS adds PKI infrastructure that
smaller teams cannot operationally maintain (cert issuance, rotation,
revocation lists).

**Future remediation:** mTLS is deferred to the enterprise tier (v1.2+).
For customers who require it before then, contact InfraCanvas support
to discuss a private-PKI bootstrap.

## L-7: No release-binary signing

**What:** Agent binaries attached to GitHub releases are not signed
(no Sigstore cosign, no GPG, no Apple notarization).

**Risk:** TLS to github.com prevents in-transit modification, but does
not provide cryptographic post-download attestation. An adversary who
compromised GitHub Releases would not be detected.

**Operator mitigations available today:**

- Verify the SHA-256 hash of the downloaded binary against the value
  recorded in this CAB packet's [sbom.cyclonedx.json](./sbom.cyclonedx.json)
  metadata after each release.
- Pin a known-good binary on internal artifact repositories rather than
  re-downloading from github.com for every install.
- For especially sensitive sites, build the agent from source against
  the published commit SHA — `go.sum` verification ensures the
  dependency closure matches.

**Future remediation:** Sigstore cosign signing (with optional Apple
notarization for macOS targets) is on the enterprise-tier roadmap.

---

## Risk-Acceptance Summary

| L | Severity (CISO view) | Operator action available? | Future remediation tier |
|---|---------------------|---------------------------|------------------------|
| L-1 | Medium-High | Yes (VLAN + read-only accounts) | Enterprise (v1.2+) |
| L-2 | Medium | Yes (chmod 600, non-root user, FDE) | Enterprise (v1.2+) |
| L-3 | Medium | Yes (manual audit + revoke) | Enterprise (v1.2+) |
| L-4 | Low-Medium | Yes (VLAN isolation) | Roadmap (demand-gated) |
| L-5 | Low (no security impact) | N/A | Phase 10+ deferred-items |
| L-6 | Medium | Partial (token rotation) | Enterprise (v1.2+) |
| L-7 | Medium | Yes (SHA-256 verify) | Enterprise (v1.2+) |

If a customer's policy makes any of L-1, L-2, L-3, L-6, or L-7 a
hard blocker, contact InfraCanvas support to discuss the enterprise-
tier early-access path.

---

## Phase 11 Firewall Integration

The Phase 11 firewall integration introduces five new collectors (ASA
REST, ASA SSH, FMC, Checkpoint live, Checkpoint offline import) and
three new backend ingest endpoints. The Phase 11 limitations below are
all vendor-imposed or product-design residuals; none of them are
security holes. Each has an operator-side workaround.

| Limitation ID | Limitation | Impact | Mitigation / Workaround |
|---|---|---|---|
| L-11-01 | Cisco ASA REST API removed at ASA 9.17+ (EOL boundary 9.16) | `protocol: asa-rest` fails with 404 from `/api/tokenservices` or 401 with "REST API disabled" on devices running ASA 9.17 or later | Operator switches the affected device to `protocol: asa-ssh` (`show running-config` over SSH works on all ASA versions). RESEARCH Pitfall 1; surfaced in [operator-runbook.md](./operator-runbook.md) troubleshooting. |
| L-11-02 | Checkpoint Management API SID timeout on very large rule layers (>50k rules per layer) | Pull may receive 401 mid-pagination if a single layer exceeds the `session-timeout: 3600` second window the agent passes at login | Agent already passes the max-allowed 3600s timeout at login (Pitfall 2 mitigation). For layers that legitimately exceed 1 hour to pull, operator falls back to `protocol: checkpoint-import` and produces the `mgmt_cli` exports out-of-band. RESEARCH Pitfall 2 / Risk Landmine 4. |
| L-11-03 | `checkpoint-import` requires a fixed sibling-file naming convention | Operator must produce three files from `mgmt_cli` at predictable suffixes — `<base>.rulebase.json`, `<base>.nat.json`, `<base>.objects.json` — and place them all in the same directory as the path declared in `agent.yaml`'s `config_file` field | The agent dispatcher accepts either the base-prefix form (`/etc/infracanvas/cp-airgap`) or the `.rulebase.json`-suffixed form (`/etc/infracanvas/cp-airgap.rulebase.json`); the other two siblings are derived by suffix substitution. Documented in [operator-runbook.md](./operator-runbook.md) Phase 11 section with copy-paste-ready `mgmt_cli` commands. RESOLVED Open Question 3 (RESEARCH 11-RESEARCH.md). |
| L-11-04 | FMC integration uses the first `DOMAIN_UUID` + first access policy + first NAT policy returned by the auth and list endpoints | Multi-tenant FMC deployments or environments with multiple parallel access policies only get the first domain / first policy on the hourly pull | Operator-driven domain / policy selection is deferred to a future phase. T-11-10-05 (in [threat-model.md](./threat-model.md)) mitigates the worst case structurally (the agent never hardcodes a `DOMAIN_UUID`; it always uses the auth-response header). RESEARCH Pitfall 6 simplification — revisit in v1.2 if customers report multi-domain coverage gaps. |
| L-11-05 | Snapshot retention is 14 days by default | Older firewall rule-base history (e.g. "what did this rule base look like 6 months ago?") is not queryable via the read API once pruned | Adjustable per-deployment via the `FIREWALL_SNAPSHOT_TTL_DAYS` env var on the backend (zero schema change — the env var is read by the taskiq prune task at run time). RESEARCH Risk Landmine 2 + Pitfall 7. Operators requiring longer retention bump the env var; pilot deployments commonly run 14d to keep Neon storage cost predictable. |

### Phase 11 risk-acceptance summary

| L | Severity (CISO view) | Operator action available? | Future remediation tier |
|---|---|---|---|
| L-11-01 | Low (vendor EOL — operator already needs to know ASA versions in their fleet) | Yes (switch device to `asa-ssh`) | Already-shipped (ASA SSH is the official Cisco-recommended path for 9.17+) |
| L-11-02 | Low-Medium (operator-visible failure mode at very large scale only) | Yes (fall back to `checkpoint-import`) | Larger session-timeout / refresh-token model deferred to v1.2 |
| L-11-03 | Low (operational convention, not security) | Yes (follow runbook naming convention) | Stable v1.1 contract — multi-file or alternate naming deferred unless customers ask |
| L-11-04 | Low-Medium (impacts visibility, not security) | Yes (operator can run a second agent host per FMC domain — wide rather than deep) | Multi-domain enumeration is on the v1.2 roadmap |
| L-11-05 | Low (operational / storage) | Yes (env var bump) | Configurable per-team retention is on the v1.2 roadmap |

None of L-11-01 through L-11-05 are security blockers. All are
documented for operator transparency and to prevent silent surprises
during deployment.

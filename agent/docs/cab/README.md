# InfraCanvas DC Agent — Change Advisory Board (CAB) Security Review Packet

**Audience:** Enterprise procurement, IT security review boards, change advisory boards.
**Phase:** 10 (DC Agent Core).
**Version:** Generated against the InfraCanvas DC Agent at the tag listed in [`sbom.cyclonedx.json`](./sbom.cyclonedx.json) (see `metadata.component.version`).
**Last updated:** 2026-05-10.
**Status:** DRAFT — pending internal review before first external circulation.

This packet contains the documents an enterprise reviewer needs to approve
deployment of the InfraCanvas DC Agent (`infracanvas-agent`) in a regulated
environment. It is intentionally self-contained — no external references are
required to complete a review.

## Contents

| Document | Purpose |
|----------|---------|
| [architecture.md](./architecture.md) | System architecture, component map, network footprint, dependency footprint |
| [dataflow.md](./dataflow.md) | Data inventory and classification (operational/secret/PII), trust boundaries crossed, encryption posture |
| [threat-model.md](./threat-model.md) | STRIDE threat register with mitigations, accepted risks, and cross-cutting controls |
| [sbom.cyclonedx.json](./sbom.cyclonedx.json) | CycloneDX 1.6 SBOM — every dependency with version, hash, and license evidence |
| [known-limitations.md](./known-limitations.md) | Phase 10 known limitations with operator mitigations and remediation roadmap |
| [operator-runbook.md](./operator-runbook.md) | Step-by-step deployment guide for site operators |

## What the agent does (one paragraph)

The InfraCanvas DC Agent is a single-binary Go process that runs inside a
customer's data centre, collects routing-table state from network devices
(via NETCONF, SSH, or static config-file import) and NetFlow v9 / IPFIX
records from network exporters, and pushes the collected data over HTTPS
to the InfraCanvas SaaS backend. It does **not** receive or execute any
inbound commands; it does **not** modify device state; it does **not**
transmit device credentials.

## What the agent does NOT do (Phase 10 scope)

- Modify any device configuration (read-only collection only).
- Transmit device username/password (read-only NETCONF/SSH service-account
  credentials live entirely on the agent host).
- Maintain persistent state on disk (NetFlow buffer is in-memory only).
- Accept inbound network traffic, except UDP/2055 for NetFlow records.
- Provide a remote-control plane (no inbound HTTP, no SSH server, no API).

## Outbound-only network posture

With the single exception of the optional NetFlow UDP listener on port
2055/udp (which receives one-way packets from operator-owned exporters
inside the same management VLAN), the agent **never accepts inbound
network connections**. There is no inbound HTTP endpoint, no remote shell,
no remote-execution channel. All cloud connectivity is initiated by the
agent over outbound HTTPS to a single, configured backend URL.

## How to review this packet

1. Read [architecture.md](./architecture.md) for the system shape and
   network footprint.
2. Read [dataflow.md](./dataflow.md) to confirm what data leaves the agent
   host and what stays local.
3. Read [threat-model.md](./threat-model.md) for the STRIDE register and
   the trust-boundary analysis.
4. Read [known-limitations.md](./known-limitations.md) for the residual-risk
   inventory and remediation roadmap.
5. Read [operator-runbook.md](./operator-runbook.md) for the deployment
   steps your site team will follow.
6. Inspect [sbom.cyclonedx.json](./sbom.cyclonedx.json) for transitive
   dependencies, versions, and hashes.

If a question is not answered by these documents, it is a gap in the
packet — please flag it back to InfraCanvas so this README can be
updated.

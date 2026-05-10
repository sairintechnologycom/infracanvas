# Phase 11: Firewall Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 11-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-10
**Phase:** 11-Firewall Integration
**Areas discussed:** Collection topology, Backend rule data model, CKP-02 interpretation, agent.yaml shape

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Collection topology | Agent-extension vs cloud-side puller vs mixed | ✓ |
| Backend rule data model | Normalized vs vendor-native vs hybrid | ✓ |
| CKP-02 interpretation | Offline-import path vs API-response parser | ✓ |
| agent.yaml shape | Extend devices[] vs separate firewalls[] array | ✓ |

**User's choice:** All four areas selected for discussion.

---

## Collection topology

### Where should the firewall collectors run?

| Option | Description | Selected |
|--------|-------------|----------|
| Extend the Go DC agent | New internal/{asa,fmc,checkpoint} packages; inherits Phase 10 site-token + LAN-only credential storage | ✓ |
| Cloud-side puller | Backend reaches firewall mgmt APIs over public internet | |
| Mixed — agent default, cloud opt-in | Two code paths, two threat models | |

**User's choice:** Extend the Go DC agent.

### Polling cadence for firewall rule collection?

| Option | Description | Selected |
|--------|-------------|----------|
| Hourly | 4th channel alongside DCA-06 timing (Routes 5m, BGP 1m, NetFlow 30s) | ✓ |
| On agent restart only | Rule-base drift invisible until restart | |
| Configurable per-site (default 1h) | More knobs to support | |

**User's choice:** Hourly.

### When ASA REST is unavailable, what triggers SSH fallback (ASA-03)?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-device protocol selection | Operator declares asa-rest or asa-ssh; deterministic; matches Phase 10 protocol-field model | ✓ |
| Auto-fallback at runtime | Try REST first; SSH on persistent failure | |
| Both — declared default + auto-fallback override | Most code, hardest to test | |

**User's choice:** Per-device protocol selection.

### Site mapping — per-device site_id or inherit from agent?

| Option | Description | Selected |
|--------|-------------|----------|
| Inherit agent site by default; override per-device | Reuses Phase 10 Device.SiteID field; zero new schema | ✓ |
| Always require per-device site_id | More verbose config | |
| Auto-discover from device location/hostname | Brittle | |

**User's choice:** Inherit agent site by default; override per-device.

### NAT data shape (ASA-01 success criterion 1)?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate firewall_nat_rules table/endpoint | NAT structurally different from access rules; Phase 12 NAT_ASYMMETRY classifier consumes separately | ✓ |
| Unified rules table with rule_kind discriminator | Schema rot from nullable kind-specific columns | |
| Defer NAT to Phase 12 | Conflicts with ROADMAP success criterion 1 | |

**User's choice:** Separate firewall_nat_rules table/endpoint.

**Notes:** All five sub-questions converged cleanly. Operator-declared protocol (D-04) chosen explicitly to keep the CAB threat model auditable — operators can answer "which channel produced this rule" without runtime ambiguity.

---

## Backend rule data model

### How should firewall rules be stored?

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid — normalized + raw_blob | Normalized columns for Phase 12 path computation + raw_blob JSONB for vendor-specific UI/audit | ✓ |
| Normalized only | Loses vendor-specific fields (Checkpoint inline-layers, ASA object-groups, FMC pre-filter rules) | |
| Vendor-native tables | Three migrations; Phase 12 has to special-case every vendor | |

**User's choice:** Hybrid — normalized + raw_blob.

### Address objects, service objects, object-groups — store separately or denormalize?

| Option | Description | Selected |
|--------|-------------|----------|
| Store separately + reference | Mirrors how ASA/FMC/Checkpoint actually model rules; CKP-01 success criterion explicitly says "rule base + objects" | ✓ |
| Denormalize into rules — expand at ingest | Audit trail of "which group" is lost | |
| Both — denormalize for query, keep objects for display | Two writes per ingest | |

**User's choice:** Store separately + reference.

### Rule-base versions / deployment history?

| Option | Description | Selected |
|--------|-------------|----------|
| Snapshot per pull (full replace) | Atomic deploy semantics match how vendors actually push rules | ✓ |
| Diff-based — only write changes | Storage-efficient but reconstruction queries are complex | |
| No history — always latest | "When did this rule appear?" is unanswerable | |

**User's choice:** Snapshot per pull (full replace).

### Phase 11 ships ingest only or also backend read API?

| Option | Description | Selected |
|--------|-------------|----------|
| Ingest + minimal read API | GET /v1/sites/{site_id}/firewall-rules; satisfies ROADMAP success criterion 4 | ✓ |
| Ingest only — read API in Phase 12 | Cleaner phase boundary but conflicts with ROADMAP success criterion 4 | |
| Full UI — dashboard rule browser | Scope creep | |

**User's choice:** Ingest + minimal read API.

---

## CKP-02 interpretation

### What does "Checkpoint rule-base export parser" cover?

| Option | Description | Selected |
|--------|-------------|----------|
| Both — offline-export path + API parser share one parser | Pure function over Checkpoint policy JSON; CKP-01 feeds live, CKP-02 adds offline import via checkpoint-import protocol mirroring Phase 10 config-import | ✓ |
| Offline-export only | Two code paths for the same data shape; duplicate parsing logic | |
| API-response parser only | No story for air-gapped Checkpoint installs | |

**User's choice:** Both — shared parser for live API + offline import.

### Which Checkpoint API objects must Phase 11 cover?

| Option | Description | Selected |
|--------|-------------|----------|
| Access rulebase + NAT rulebase + objects (host/network/group/service) | Minimum for Phase 12; aligns with ROADMAP success criterion 3 | ✓ |
| Access rulebase + objects only (no NAT) | Phase 12 NAT_ASYMMETRY needs Checkpoint NAT too | |
| Everything CKP-01 exposes | Massive scope creep | |

**User's choice:** Access rulebase + NAT rulebase + objects.

### Checkpoint Mgmt API session lifecycle?

| Option | Description | Selected |
|--------|-------------|----------|
| Login per pull, logout when done | Stateless between pulls; no on-disk SID; matches mgmt_cli script idiom | ✓ |
| Long-lived session with refresh | SID lifecycle errors become a debugging surface | |
| Customer-supplied long-lived token | May not be available in all environments | |

**User's choice:** Login per pull, logout when done.

### FMC vs direct ASA REST — precedence when both configured?

| Option | Description | Selected |
|--------|-------------|----------|
| Independent — pull both, dedupe in backend by device serial | Snapshot-per-pull "most recent wins"; drift between FMC and ASA stays visible in snapshot history | ✓ |
| FMC takes precedence — skip direct ASA pull when managed | Cleaner but rule-base drift becomes invisible | |
| Defer — Phase 11 only documents the question | Pull what's configured, no special handling | |

**User's choice:** Independent — pull both, dedupe in backend by device serial.

---

## agent.yaml shape

### How should firewalls be expressed in agent.yaml?

| Option | Description | Selected |
|--------|-------------|----------|
| Extend devices[] with new protocol values | Reuses existing Device struct; adds asa-rest/asa-ssh/fmc/checkpoint/checkpoint-import; zero new schema | ✓ |
| Separate firewalls[] array with its own schema | Cleaner conceptual separation; doubles config surface | |
| Hybrid — devices[] for transport-uniform, firewalls[] only when extra fields needed | Most flexible, also most surface area | |

**User's choice:** Extend devices[] with new protocol values.

### How should agent loop scheduling for firewall pulls compose with DCA-06?

| Option | Description | Selected |
|--------|-------------|----------|
| Add Firewall ticker as a 4th interval in defaultIntervals() | DCA-06 contract evolves to 4 intervals; tests assert all four | ✓ |
| Run firewall pulls inside the Routes ticker (every 12th tick) | Tangles two concerns | |
| Separate goroutine with internal hourly sleep, no ticker | Doesn't fit the existing ticker idiom | |

**User's choice:** Add Firewall ticker as a 4th interval.

### Push endpoint shape for firewall data?

| Option | Description | Selected |
|--------|-------------|----------|
| Three endpoints — POST /v1/agent/firewall-rules + /firewall-nat + /firewall-objects | Mirrors Phase 10 D-08 per-data-type pattern | ✓ |
| POST /v1/agent/firewall-snapshot — single endpoint with rules+nat+objects | Atomic but large payloads for big rule bases | |
| POST /v1/agent/firewalls — vendor discriminator in payload | Looser contract; worse type-checking | |

**User's choice:** Three endpoints.

### Credential storage for firewall mgmt accounts?

| Option | Description | Selected |
|--------|-------------|----------|
| Same model as Phase 10 — plaintext in agent.yaml (chmod 600), CAB documents | Consistency with Phase 10 D-05 over extra mechanism | ✓ |
| OS keychain integration | Headless servers often lack keychain daemons | |
| Encrypted with site_token-derived key | Marginal gain; key-rotation complexity | |

**User's choice:** Same model — plaintext in agent.yaml, CAB packet documents.

---

## Claude's Discretion

- Snapshot retention TTL specifics (default ~30 days suggested) — planner picks exact value with rationale.
- Internal package layout within `agent/internal/asa/` (separate `rest.go` + `ssh.go` files vs sub-packages) — planner picks idiomatic Go.
- ASA REST API version targeting and FMC API version pinning — planner researches current stable versions.
- Specific FastAPI route handler structure — follow `backend/app/routes/github.py` precedent.
- Pydantic model shapes for the three push payloads — planner derives from D-08/09 schema.
- Alembic migration naming, indexes, JSONB index strategy — planner decides per existing conventions.
- Whether each protocol gets its own collector type vs single vendor collector with internal protocol switch (Phase 10 precedent leans toward separate types per transport).

## Deferred Ideas

- Dashboard UI for firewall rule browsing — dedicated dashboard hardening phase
- Long-lived Checkpoint SID with refresh — revisit if rate limits or login latency become a bottleneck
- OS keychain credential storage — Phase 10 plaintext-with-chmod-600 precedent applies
- Encrypted credentials with site_token-derived key — marginal gain, skip
- Per-site configurable firewall poll interval — default 1h is sufficient for v1.1
- FMC takes precedence over direct ASA — keeps drift visible; revisit if duplicate-ingest cost matters
- Checkpoint threat-prevention layers, application control, identity awareness, URL filtering — Compliance phase v1.2
- Palo Alto, Fortinet, Juniper SRX firewall integrations — out of v1.1
- Rule simulation / what-if analysis / compliance scoring — v1.2 Compliance phase
- Diff-based snapshot storage — skip until storage cost is a real concern
- Auto-fallback ASA REST → SSH at runtime — keeps threat model auditable; skip
- Dashboard UI for site token management (carried forward from Phase 10) — still deferred
- mTLS per-site certificates (carried forward from Phase 10) — v1.2 enterprise
- Disk-backed firewall pull queue — snapshot-per-pull on 1h cadence tolerates single missed pulls
- Protobuf push encoding (carried forward) — revisit if bandwidth becomes a measurable concern

---
phase: 03-flowmap-v1-0
plan: 04
subsystem: cli
tags: [azure, mgmt-network, vwan, expressroute, flowmap, collector, credentials]

requires:
  - phase: 03-flowmap-v1-0/01
    provides: ResourceGraph v2.1 (ResourceNode, CostEstimate, DriftStatus)
  - phase: 03-flowmap-v1-0/02
    provides: flowmap.collector orchestrator seam — lazy-imports collect_azure_network
provides:
  - "`cli/infracanvas/flowmap/azure.py` — `collect_azure_network(graph: ResourceGraph) -> ResourceGraph`"
  - "Lazy-imported azure-identity + azure-mgmt-network SDK calls (Reader-role only)"
  - "Credential guard raising RuntimeError listing ONLY missing ARM_* env var names"
  - "Per-API defensive wrappers — one HttpResponseError never aborts the other collectors"
  - "Eight azurerm_* node types (verbatim for Plan 03-05 rule YAML + Plan 03-07 viewer handlers)"
  - "Sanitized Azure fixtures at cli/tests/fixtures/flowmap/azure/{vwan,vnet,expressroute}.json"
affects: [03-05, 03-07]

tech-stack:
  added: []  # deps already declared by Plan 03-01
  patterns:
    - "Lazy SDK import + ImportError -> RuntimeError with credential-free message"
    - "ARM_* env-var-only auth (CONTEXT D-05, Phase 2 D-07) — no fallback credential sources, no cached credentials"
    - "MISSING-var-names-only exception surface (T-03-04-02) — env-var VALUES never interpolated"
    - "Per-API try/except with noqa: BLE001 (Azure SDK raises diverse HttpResponseError subclasses)"
    - ".as_dict()-based unwrapping of azure-mgmt Model objects — mockable via MagicMock()"
    - "resource_id path-parser helper (_parse_rg_and_name) — resolves rg + resource name from the standard Azure ARM path"

key-files:
  created:
    - cli/infracanvas/flowmap/azure.py
    - cli/tests/test_flowmap_azure.py
    - cli/tests/fixtures/flowmap/azure/vwan.json
    - cli/tests/fixtures/flowmap/azure/vnet.json
    - cli/tests/fixtures/flowmap/azure/expressroute.json
  modified: []

key-decisions:
  - "Use azurerm_* type prefix matching Phase 2 parser convention (not mgmt-network internal names) — Plan 03-05 NET rules + Plan 03-07 viewer can match on a single identifier scheme across both parsed-from-HCL and cloud-collected resources"
  - "Flow-log metadata attaches to the NSG node's attributes['flow_log'] rather than becoming a standalone node — preserves NSG as the primary finding surface for AZN-03 rules in Plan 03-05"
  - "Per-API try/except at the outer _collect_* level AND the inner nested list (hub_connections, peerings) so partial collection is preserved even when only one child API denies"
  - "os.environ[...] (not os.environ.get(...)) on the four ARM_* reads AFTER the missing-var check — the check runs first, so a KeyError here is impossible; this makes mypy strict happy and keeps the read obvious to reviewers"
  - "Mock sys.modules with MagicMock() rather than pytest.importorskip — tests must cover the guard paths themselves, which requires running in environments where the SDK is NOT installed; importorskip would hide those paths"

patterns-established:
  - "Azure FlowMap collector template: lazy SDK import -> creds guard -> inferred location -> dispatch to per-resource _collect_* helpers -> each with defensive try/except"
  - "Credential leak test pattern: set the sensitive env var to a distinctive fingerprint (super-secret-v4lue-xyz), trigger the error path, assert that fingerprint does NOT appear in str(exc) or exc.args — reusable for any future env-var-driven integration"

requirements-completed: [AZN-01, AZN-02, AZN-03]

duration: ~45min
completed: 2026-04-19
---

# Phase 03-flowmap-v1-0 / Plan 04: Azure cloud-network collector

**`collect_azure_network(graph)` reads ARM_* env vars, calls azure-mgmt-network list() APIs under a Reader-scoped ClientSecretCredential, and appends eight azurerm_* node types — vWAN, virtual hubs + connections, vNets + peerings, NSGs (with securityRules + flow-log metadata), and ExpressRoute circuits + peerings — to the ResourceGraph that Plan 03-02's orchestrator passes in. Zero real Azure calls in CI; 16 tests mock the SDK via `patch.dict('sys.modules', ...)`.**

## Azure Node Type Reference (for Plans 03-05 and 03-07)

The collector emits these exact `ResourceNode.type` strings. Downstream rule-YAML authors and viewer node-type handlers MUST use these verbatim:

| Type string                             | Source API                                                         | Attribute highlights                                           |
| --------------------------------------- | ------------------------------------------------------------------ | -------------------------------------------------------------- |
| `azurerm_virtual_wan`                   | `virtual_wans.list()`                                              | `provisioning_state`, `allow_branch_to_branch_traffic`, `sku`  |
| `azurerm_virtual_hub`                   | `virtual_hubs.list()`                                              | `address_prefix`, `virtual_wan_id`, `provisioning_state`       |
| `azurerm_virtual_hub_connection`        | `hub_virtual_network_connections.list(rg, hub)`                    | `virtual_hub_id`, `remote_virtual_network_id`, `enable_internet_security` |
| `azurerm_virtual_network`               | `virtual_networks.list_all()`                                      | `address_space` (list), `subnets` (list of {name, address_prefix}) |
| `azurerm_virtual_network_peering`       | `virtual_network_peerings.list(rg, vnet)`                          | `virtual_network_id`, `remote_virtual_network_id`, `peering_state` |
| `azurerm_network_security_group`        | `network_security_groups.list_all()`                               | `security_rules`, `default_security_rules`, `flow_log` (from AZN-03) |
| `azurerm_express_route_circuit`         | `express_route_circuits.list_all()`                                | `bandwidth_mbps`, `service_provider`, `peering_location`       |
| `azurerm_express_route_circuit_peering` | `express_route_circuit_peerings.list(rg, circuit)`                 | `peering_type`, `peer_asn`, `primary_peer_address_prefix`, `vlan_id` |

For NSG nodes, `attributes["flow_log"]` contains the AZN-03 metadata: `{flow_log_id, enabled, retention_days, format_type, storage_id}`.

## Performance

- **Duration:** ~45 min
- **Started:** 2026-04-19 (Wave 3, parallel executor)
- **Completed:** 2026-04-19
- **Tasks:** 3 (all committed atomically)
- **Files created:** 5 (1 source + 1 test + 3 fixtures)

## Task Commits

1. **Task 1: Azure fixtures** — `755930f` — `test(03-04): add sanitized Azure fixtures (vWAN, vNet, ExpressRoute)`
2. **Task 2: Implement azure.py** — `3447a7f` — `feat(03-04): implement collect_azure_network — vWAN, vNet, NSG, ExpressRoute`
3. **Task 3: Pytest coverage** — `ed19638` — `test(03-04): 16 tests for collect_azure_network — guards, happy paths, defensive wrappers`

All commits use `git commit --no-verify` per Wave-3 parallel-executor worktree protocol.

## Files Created

- **`cli/infracanvas/flowmap/azure.py`** (405 lines) — `collect_azure_network` + 6 per-API helpers (`_collect_virtual_wans`, `_collect_virtual_hubs`, `_collect_virtual_networks`, `_collect_network_security_groups`, `_collect_express_route_circuits`, `_collect_flow_log_metadata`) + 3 utilities (`_infer_location`, `_add_node`, `_as_dict`, `_parse_rg_and_name`)
- **`cli/tests/test_flowmap_azure.py`** (274 lines) — 16 tests across 4 test classes
- **`cli/tests/fixtures/flowmap/azure/vwan.json`** — 1 vWAN + 1 hub + 1 hub connection
- **`cli/tests/fixtures/flowmap/azure/vnet.json`** — 1 vNet (2 subnets) + 1 peering + 1 NSG (allow-https rule)
- **`cli/tests/fixtures/flowmap/azure/expressroute.json`** — 1 ER circuit (10Gbps Equinix) + 1 AzurePrivatePeering (ASN 64521) + 1 flow-log metadata entry

## Verification

**Tests:**
```
cli/tests/test_flowmap_azure.py: 16 passed in 0.15s
cli/tests/: 256 passed in 9.83s (240 pre-existing baseline + 16 new; ZERO regressions)
```

**Lint:**
```
ruff check cli/infracanvas/flowmap/azure.py -> All checks passed!
ruff check cli/tests/test_flowmap_azure.py -> All checks passed!
```

**mypy --strict:** Clean on code-under-test; the only errors reported are `import-not-found` for `azure.identity` and `azure.mgmt.network`, which is expected in CI where `[flowmap]` extras are not installed (same posture as `hcl2.*` already in `pyproject.toml [[tool.mypy.overrides]]`). With extras installed (`pip install -e '.[flowmap]'`), mypy --strict passes clean.

**Security audit (plan verification step 4-5):**
- `grep -n 'os.environ' cli/infracanvas/flowmap/azure.py` returns only the 5 ARM_* reads. Zero raw `os.environ` dict logging.
- RuntimeError message strings manually reviewed: the missing-var branch interpolates only `', '.join(missing)` (the MISSING-var NAMES list) — never any env-var VALUES. The ImportError branch emits a static string with no runtime data at all.

## Threat Model Compliance

| Threat ID | Mitigation Applied |
|-----------|-------------------|
| T-03-04-01 Elevation of Privilege — Reader-scope only | Code only calls `*.list()` / `*.list_all()` / nested `*.list(rg, parent)`; zero mutating SDK methods. User_setup documents Reader role only. |
| T-03-04-02 Info Disclosure — credential leakage in RuntimeError | `test_credential_values_not_leaked_in_exception` sets ARM_CLIENT_SECRET="super-secret-v4lue-xyz", triggers the missing-cred path, and asserts that distinctive value is NOT present in `str(exc_info.value)` OR `str(exc_info.value.args)`. Collector code only interpolates `', '.join(missing)` — the NAMES of missing vars, never VALUES. |
| T-03-04-03 Info Disclosure — subscription/tenant IDs in HTML | Accepted (same posture as Phase 2 parser + Plan 03-03 AWS collector). Customer-owned offline artifact. |
| T-03-04-04 Denial of Service — unbounded list_all() | Subscription-scoped per D-05. Defensive per-API wrappers catch transient failures. No pagination in 3a (customer subscription size < 1000 resources assumed — aligns with shadow/ precedent). |
| T-03-04-05 Spoofing — compromised SP secret | Accepted — credential lifecycle is customer-managed. |
| T-03-04-06 Info Disclosure — flow-log ingestion | Only metadata collected (enabled, retention, format, storage_id). Zero log-content ingestion. `test_flow_log_metadata_attached_to_nsg` verifies metadata shape, not log-event presence. |
| T-03-04-07 Tampering — fixture injection | Accepted — check-in artifacts reviewed at PR time. Not a runtime threat. |

## Decisions Made

- **No `pytest.importorskip('azure.mgmt.network')`** — the whole point of this test file is to cover the credential-guard and missing-SDK paths, which only fire when the SDK is NOT installed. `importorskip` would silently skip those assertions in the common CI case where extras aren't installed and give us false green. Instead, `patch.dict('sys.modules', ...)` with MagicMock-backed SDKs covers the happy path and `patch.dict('sys.modules', {'azure.identity': None, 'azure.mgmt.network': None})` covers the missing-SDK path — both work regardless of whether the real SDK is installed.
- **Per-API defensive wrappers at TWO levels**: (a) outer collector (`_collect_virtual_hubs`) wraps the top-level list() call; (b) inner nested call (`hub_virtual_network_connections.list(rg, hub_name)`) is separately wrapped. This means that if ONE hub denies its connections-list but another succeeds, partial collection is preserved. Matches `test_api_failure_swallowed` expectation that vWAN still collects after vNet denial.
- **Flow-log metadata merged into the NSG node** (not a standalone node) — Plan 03-05's NFN-01 rule "NSG without flow log" needs `attributes["flow_log"]` on the NSG to fire cleanly; a separate node would require cross-node rule logic that the current rule engine doesn't support.
- **`_as_dict` helper** accepts both Azure SDK Model objects (via `.as_dict()`) and raw dicts — tests can inject dicts directly, real SDK responses unwrap transparently.

## Deviations from Plan

**[Rule 2 — Missing critical functionality] Added `test_malformed` and `test_empty_subscription_returns_empty_graph` and `test_node_types_use_azurerm_prefix` tests beyond the plan's explicit list.** These cover three correctness-critical cases the plan's must-haves imply but didn't name:
- `_parse_rg_and_name` robustness on malformed IDs (negative-path safety — without this, a malformed resource ID could bubble an IndexError into `_collect_virtual_hubs` and skip its whole API)
- Empty-subscription path (happy-path-zero — first-time customer with no vWAN/vNet/ER must not crash)
- Node-type prefix assertion (cross-plan contract — Plan 03-05 and 03-07 depend on these exact strings; a single typo in my implementation would break them silently without this assertion)

**[Refinement] `_as_dict` has a defensive `isinstance(result, dict)` check** around `obj.as_dict()`'s return value because mypy --strict complained about `Any` flowing through — the plan's snippet returned the bare `.as_dict()` result. This is a mypy-correctness refinement, not a behavior change: real Azure SDK `.as_dict()` always returns `dict`.

Every other detail matches the plan verbatim — signatures, error messages, node types, attribute keys, fixture shapes.

## Issues Encountered

- **`cli/.venv` had no `pytest` installed initially** — ran `.venv/bin/python -m pip install pytest` as a one-off to execute the suite. No project-file change.
- **mypy --strict flags `azure.identity` and `azure.mgmt.network` as `import-not-found`** in environments without the `[flowmap]` extras — expected per Plan 03-01's optional-dependency posture. If this becomes noisy for future contributors, adding `module = ["azure.*"]` / `ignore_missing_imports = true` to `pyproject.toml [[tool.mypy.overrides]]` (mirroring the existing `hcl2.*` override) is a clean follow-up. Not done here because it's out of plan scope and STATE.md is owned by the orchestrator.

## User Setup Required

Documented in plan frontmatter `user_setup`:

1. Create an Azure AD service principal (App Registration) with **Reader role** on the subscription(s) containing the vWAN / vNet / ExpressRoute resources
2. Export four env vars before running `infracanvas scan --flowmap`:
   - `ARM_CLIENT_ID` — Application (client) ID
   - `ARM_CLIENT_SECRET` — Client secret from Certificates & Secrets
   - `ARM_TENANT_ID` — Azure AD tenant ID
   - `ARM_SUBSCRIPTION_ID` — Target subscription ID
3. Install extras: `pip install -e '.[flowmap]'`

Only **Reader** / `Microsoft.Network/*/read` permissions are required. No write permissions ever requested by the collector.

## Next Plan Readiness

- **Plan 03-05 (NET security rules)** — YAML rule authors use the 8 `azurerm_*` type strings verbatim (table above). For `NFN-01 NSG without flow log`, match `type == "azurerm_network_security_group"` and `attributes.flow_log.enabled != true`. For `NFN-02 vNet peering with allow_forwarded_traffic`, match `type == "azurerm_virtual_network_peering"` and `attributes.allow_forwarded_traffic == true`.
- **Plan 03-07 (viewer FlowMap UI)** — Azure node-type handlers in `viewer/src/` key off the same 8 strings. Provide icons + tooltip layouts per the table above.
- **Plan 03-02 orchestrator** — No further changes needed. The `from infracanvas.flowmap.azure import collect_azure_network` lazy import inside `run_flowmap_collection` now resolves; `except ImportError` becomes a dead path (still harmless); `except RuntimeError` surfaces our creds-missing warning as the user-visible `[yellow]Warning:[/yellow]`.

## Self-Check: PASSED

**File existence:**
- FOUND: `cli/infracanvas/flowmap/azure.py` (405 lines)
- FOUND: `cli/tests/test_flowmap_azure.py` (274 lines)
- FOUND: `cli/tests/fixtures/flowmap/azure/vwan.json`
- FOUND: `cli/tests/fixtures/flowmap/azure/vnet.json`
- FOUND: `cli/tests/fixtures/flowmap/azure/expressroute.json`
- FOUND: `.planning/phases/03-flowmap-v1-0/03-04-SUMMARY.md`

**Commits verified in git log:**
- FOUND: `755930f` (Task 1 fixtures)
- FOUND: `3447a7f` (Task 2 azure.py)
- FOUND: `ed19638` (Task 3 pytest suite)

**Plan must_haves.truths verification:**
- ✓ `collect_azure_network(graph)` populates graph.nodes with all 8 resource categories (verified by `test_node_types_use_azurerm_prefix`)
- ✓ Missing azure SDK raises RuntimeError containing "azure-mgmt-network not installed" (verified by `test_missing_sdk_raises`)
- ✓ Missing ARM_* env vars raises RuntimeError listing missing var names (verified by `test_missing_all_creds_lists_all` + `test_missing_single_cred_lists_only_missing`)
- ✓ Individual Azure SDK call failure caught, other APIs continue (verified by `test_api_failure_swallowed`)
- ✓ Collected nodes use `azurerm_*` type prefix (verified by `test_node_types_use_azurerm_prefix`)
- ✓ Error messages never embed ARM_CLIENT_SECRET (verified by `test_credential_values_not_leaked_in_exception`)

**Sibling plan file isolation (Wave 3 parallel-executor constraint):**
- ✓ No modification to `cli/infracanvas/flowmap/aws.py` (Plan 03-03's file — confirmed: this session did not touch it; sibling agent's commit `49a2b86` is a separate, earlier commit)
- ✓ No modification to `cli/tests/test_flowmap_aws.py`
- ✓ No modification to `cli/tests/fixtures/flowmap/aws/**`
- ✓ No modification to `cli/infracanvas/flowmap/collector.py` (Plan 03-02's seam)
- ✓ No modification to `.planning/STATE.md` or `.planning/ROADMAP.md`

---
*Phase: 03-flowmap-v1-0*
*Completed: 2026-04-19*

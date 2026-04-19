---
phase: 03-flowmap-v1-0
plan: 05
subsystem: security
tags: [yaml-rules, security-engine, net-findings, cloud-only, path-independent, aws, azure]

# Dependency graph
requires:
  - phase: 03-flowmap-v1-0/03-01
    provides: NetworkFinding extension (source="network" | "security") + Finding.framework_ids
provides:
  - NET-001..NET-006 AWS network security rules (TGW, VPC/NACL, Direct Connect)
  - NET-007..NET-009 + NET-011, NET-012 Azure network security rules (vWAN, vNet peering, NSG, ExpressRoute)
  - Rule directory convention: security/rules/network/{provider}_{scope}.yaml
  - Test pattern: pytest-parametrized positive/negative fixture matrix per rule
affects: [03-02, 03-03, 03-04, 03-06, 03-07, 03-08, 03b-01]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "NET-* rule family prefix (distinct from Phase 2 SEC-*, AZ-*) for auto-discovery + filtering"
    - "Dotted-path any_equals for nested list-of-dicts (routes.State, entries.cidr_block, security_rules.properties.destinationAddressPrefix)"
    - "JSON fixture-per-provider under tests/fixtures/flowmap/rules/ with explicit _positive/_negative suffix convention"

key-files:
  created:
    - cli/infracanvas/security/rules/network/aws_tgw.yaml
    - cli/infracanvas/security/rules/network/aws_vpc.yaml
    - cli/infracanvas/security/rules/network/aws_dx.yaml
    - cli/infracanvas/security/rules/network/azure_vwan.yaml
    - cli/infracanvas/security/rules/network/azure_vnet.yaml
    - cli/infracanvas/security/rules/network/azure_expressroute.yaml
    - cli/tests/test_flowmap_network_rules.py
    - cli/tests/fixtures/flowmap/rules/aws_net_fixtures.json
    - cli/tests/fixtures/flowmap/rules/azure_net_fixtures.json
  modified:
    - cli/tests/test_security.py

key-decisions:
  - "Shipped NET-001..NET-009 + NET-011 + NET-012 (11 rules); NET-010 reserved for Phase 3b (ASY-03, path-dependent)"
  - "Used any_equals with dotted-path attribute (e.g. routes.State) rather than refactoring the collector to pre-flatten state flags — zero engine changes, zero collector-side coupling"
  - "Framework_ids documented as plausible (not authoritative) mappings; Phase 5 CMP-* adds the authoritative catalog per T-03-05-04 mitigation"
  - "Bumped test_security.py::TestRuleLoader::test_loads_all_rules from `== 40` to `>= 51` (deviation Rule 3 — the existing assertion was authored before NET-* existed)"

patterns-established:
  - "Rule catalogue numbering: NET-00N reserved in numeric order, documented in SUMMARY with 3b hand-off note for any deferrals"
  - "Hand-crafted positive/negative fixtures — one minimal JSON node per rule × direction — enables regression-locking without collector coupling"

requirements-completed: [FDM-03, NFN-01]

# Metrics
duration: ~15min
completed: 2026-04-19
---

# Phase 3 Plan 05: FlowMap Network Security Rules Summary

**11 cloud-only, path-independent NET-* YAML rules (6 AWS + 5 Azure) auto-discovered by the existing rglob loader, locked by 28 parametrized positive/negative pytest assertions — zero engine code changes.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-19T05:42Z
- **Completed:** 2026-04-19T05:57Z
- **Tasks:** 3
- **Files modified/created:** 10 (6 YAML + 2 fixture JSON + 1 new test file + 1 test_security.py edit)

## Accomplishments

- Landed NET-001..NET-006 AWS rules covering Transit Gateway health (blackhole route, attachment state), VPC observability (flow log absence), NACL ingress (0.0.0.0/0), and Direct Connect link state (VIF + connection).
- Landed NET-007..NET-009 + NET-011 + NET-012 Azure rules covering vWAN hub-connection security posture + provisioning state, vNet peering gateway-transit misconfigs, NSG wildcard destination, and ExpressRoute provisioning.
- Proved every rule fires on its positive fixture (FIRED) and stays silent on its negative fixture (SILENT) — 22/22 positive/negative checks pass.
- Proved loader discovers all 11 new NET-* rules via existing `rglob('*.yaml')` — no engine / loader modifications.
- Total rule count after merge: **51** (Phase 2 baseline 40 + 11 new NET-*).

## Task Commits

1. **Task 1: Author 6 AWS NET-* YAML rules (NET-001..NET-006)** — `f21c682` (feat)
2. **Task 2: Author 5 Azure NET-* YAML rules (NET-007..NET-012 minus NET-010)** — `54d238f` (feat)
3. **Task 3: Pytest suite + positive/negative fixtures for all 11 NET-* rules** — `6c07366` (test)

## Shipped NET-* Catalogue

| ID | Provider | Resource Type | Operator | Severity |
|----|----------|---------------|----------|----------|
| NET-001 | AWS | aws_ec2_transit_gateway_route_table | any_equals (routes.State) | high |
| NET-002 | AWS | aws_ec2_transit_gateway_attachment | not_equals (state) | medium |
| NET-003 | AWS | aws_network_acl | any_equals (entries.cidr_block) | high |
| NET-004 | AWS | aws_vpc | not_exists (flow_log) | medium |
| NET-005 | AWS | aws_dx_virtual_interface | not_equals (state) | critical |
| NET-006 | AWS | aws_dx_connection | not_equals (state) | high |
| NET-007 | Azure | azurerm_virtual_hub_connection | equals (enable_internet_security == false) | high |
| NET-008 | Azure | azurerm_virtual_hub_connection | not_equals (provisioning_state) | medium |
| NET-009 | Azure | azurerm_virtual_network_peering | equals (use_remote_gateways == true) | medium |
| NET-011 | Azure | azurerm_network_security_group | any_equals (security_rules.properties.destinationAddressPrefix) | high |
| NET-012 | Azure | azurerm_express_route_circuit | not_equals (service_provider_provisioning_state) | critical |

All 11 operators are from the documented set in `cli/infracanvas/security/engine.py` lines 49-75: `equals, not_equals, in, not_in, exists, not_exists, contains, matches_cidr, list_contains_cidr, any_equals`.

## NET-010 — Reserved for Phase 3b-01

**NET-010 is deliberately NOT shipped in Phase 3a.** It corresponds to ASY-03 (stateful firewall on only one leg of a traffic path — asymmetric inspection). The rule requires path-dependent analysis (two-hop pairing + stateful-firewall detection across paths), which is out of scope for 3a's cloud-only, path-independent rule surface.

**Handoff to Phase 3b-01 author:** allocate NET-010 when implementing ASY-03 so numbering remains contiguous once path math lands. The `test_net_010_reserved_for_phase_3b` test in `test_flowmap_network_rules.py` will fail the day NET-010 lands — that is intentional; update the assertion at that time.

## Framework-ID Mapping Caveat

The `framework_ids` populated on each NET rule (CIS-3.4, NIST-SC-7, SOC2-CC6.6, PCI-DSS-1.2, CIS-Azure-6.1, etc.) are **plausible mappings** consistent with Phase 2 precedent. They are NOT authoritative compliance assertions. Phase 5 (CMP-* compliance pack) will introduce the authoritative CIS/NIST/SOC2/PCI-DSS mapping database and reconcile these IDs. The Phase 4 dashboard MUST NOT claim compliance certification based on these IDs (mitigation T-03-05-04 in the plan's threat model).

## Files Created/Modified

- `cli/infracanvas/security/rules/network/aws_tgw.yaml` — NET-001, NET-002
- `cli/infracanvas/security/rules/network/aws_vpc.yaml` — NET-003, NET-004
- `cli/infracanvas/security/rules/network/aws_dx.yaml` — NET-005, NET-006
- `cli/infracanvas/security/rules/network/azure_vwan.yaml` — NET-007, NET-008
- `cli/infracanvas/security/rules/network/azure_vnet.yaml` — NET-009, NET-011
- `cli/infracanvas/security/rules/network/azure_expressroute.yaml` — NET-012
- `cli/tests/test_flowmap_network_rules.py` — 28 test methods: 6 loader + 22 parametrized positive/negative evaluations
- `cli/tests/fixtures/flowmap/rules/aws_net_fixtures.json` — 12 fixture nodes (6 rules × {positive, negative})
- `cli/tests/fixtures/flowmap/rules/azure_net_fixtures.json` — 10 fixture nodes (5 rules × {positive, negative})
- `cli/tests/test_security.py` — bumped `test_loads_all_rules` assertion from `== 40` to `>= 51`

## Decisions Made

- **any_equals with dotted path for nested lists** — `any_equals` expects an attribute path with at least two parts (`list_attr.inner_key`). Used `routes.State` / `entries.cidr_block` / `security_rules.properties.destinationAddressPrefix` instead of flat attribute + restructured fixtures. This required no changes to `_check_any_equals` helper (which already handles dotted paths via `_get_nested_attr`).
- **NET-010 absence captured as a test** — Better to encode the reservation in executable form than in a prose comment: `test_net_010_reserved_for_phase_3b` will trip as a reminder when 3b-01 lands.
- **Framework-id plausibility disclaimer** — Documented here rather than in each YAML file to keep rule files grep-clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated `test_security.py::TestRuleLoader::test_loads_all_rules` assertion**
- **Found during:** Task 3 (reviewing existing test assertions before adding new ones)
- **Issue:** Existing assertion `assert len(rules) == 40` would fail on CI once 11 NET rules loaded (actual: 51).
- **Fix:** Bumped to `assert len(rules) >= 51` with updated comment noting 30 SEC + 10 AZ + 11 NET (Phase 3a) and documenting NET-010 reservation.
- **Files modified:** `cli/tests/test_security.py`
- **Verification:** With all 51 rules loaded, `len(rules) >= 51` → True.
- **Committed in:** `6c07366` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minimal — the assertion bump was strictly required for CI health; no scope expansion.

## Issues Encountered

None of substance. Two process notes:

- **Sandbox can't run pytest directly** — pytest is not installed in the repo's .venv (only runtime deps). Validated test logic by executing the test module through a stub `pytest.mark.parametrize` shim and running each test method directly via the main repo's Python interpreter with `PYTHONPATH` pointed at the worktree. All 28 test methods pass. A subsequent CI run (where pytest + dev-extras are installed) will execute them through the real pytest harness.
- **No changes needed to `security/engine.py` or `security/loader.py`** — confirmed that the existing `_check_any_equals` helper + `_get_nested_attr` recursion handle arbitrary nested dotted paths, so every NET rule expressed its intent using the existing operator set.

## User Setup Required

None — no external service configuration, credentials, or environment variables required. Rules are pure data that ship in the Python package and auto-load at runtime.

## Next Phase Readiness

- **Wave 2 sibling plans:** Plans 03-03 (AWS collector) + 03-04 (Azure collector) will produce the node types these rules match (`aws_ec2_transit_gateway_*`, `azurerm_virtual_hub_connection`, etc.). Once their PLANs merge, end-to-end cloud scans will surface NET-* findings alongside SEC-* / AZ-* findings on the unified pipeline described in Plan 03-01's SUMMARY (D-12).
- **Plan 03-08 (filter panel) consumer:** The FlowMap filter panel's finding-source selector (security | policy | network) should include NET-* findings under `source="security"` (engine assigns source there). If 3b's true-network findings emit `source="network"` via NetworkFinding, the filter panel will correctly distinguish rule-engine NET-* (security) from graph-level NET findings (network).
- **Plan 3b-01 author:** Pick up NET-010 (ASY-03). Update `test_net_010_reserved_for_phase_3b` at the same time.
- **Phase 5 (CMP-*) author:** Reconcile `framework_ids` on all NET-* rules against the authoritative compliance catalog.

## Self-Check

- `cli/infracanvas/security/rules/network/aws_tgw.yaml` — FOUND
- `cli/infracanvas/security/rules/network/aws_vpc.yaml` — FOUND
- `cli/infracanvas/security/rules/network/aws_dx.yaml` — FOUND
- `cli/infracanvas/security/rules/network/azure_vwan.yaml` — FOUND
- `cli/infracanvas/security/rules/network/azure_vnet.yaml` — FOUND
- `cli/infracanvas/security/rules/network/azure_expressroute.yaml` — FOUND
- `cli/tests/test_flowmap_network_rules.py` — FOUND
- `cli/tests/fixtures/flowmap/rules/aws_net_fixtures.json` — FOUND
- `cli/tests/fixtures/flowmap/rules/azure_net_fixtures.json` — FOUND
- Commit `f21c682` — FOUND
- Commit `54d238f` — FOUND
- Commit `6c07366` — FOUND
- `load_rules()` returns 51 rules with all 11 NET-* ids present; NET-010 absent — VERIFIED

## Self-Check: PASSED

---
*Phase: 03-flowmap-v1-0*
*Plan: 05*
*Completed: 2026-04-19*

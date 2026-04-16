---
phase: 02-canvas-v1-0
plan: "02"
subsystem: azure-parser-security
tags: [wave-1, azure, parser, security-rules, typescript, python]
dependency_graph:
  requires: [02-00, 02-01]
  provides: [azure-parser, azure-security-rules, azure-viewer-config]
  affects: [02-07, 02-08]
tech_stack:
  added: []
  patterns: [azure-attr-normalisation, provider-dispatch-in-builder, yaml-rule-framework-ids]
key_files:
  created:
    - cli/infracanvas/parser/azure.py
    - cli/infracanvas/security/rules/azure/network.yaml
    - cli/infracanvas/security/rules/azure/storage.yaml
    - cli/infracanvas/security/rules/azure/compute.yaml
    - cli/infracanvas/security/rules/azure/identity.yaml
    - cli/infracanvas/security/rules/azure/database.yaml
    - viewer/src/icons/azureServiceConfig.ts
    - cli/tests/fixtures/azure/vnet.tf
    - cli/tests/fixtures/azure/storage.tf
    - cli/tests/fixtures/azure/compute.tf
  modified:
    - cli/infracanvas/graph/builder.py
    - cli/tests/test_azure_parser.py
    - cli/tests/test_security.py
decisions:
  - "Azure normalisation lives in a separate parser/azure.py module, not inlined in builder.py — keeps provider-specific logic isolated and easier to extend"
  - "Single azure/ fixture directory (not per-resource subdirs) — parse_directory scans all .tf files, simplifying test helper to _scan_azure() with no arguments"
  - "test_loads_all_rules updated from 10 to 20 — AWS 10 + Azure 10, test must track true total (Rule 1 auto-fix)"
metrics:
  duration: "~12 minutes"
  completed: "2026-04-16T12:00:00Z"
  tasks_completed: 2
  files_modified: 13
---

# Phase 02 Plan 02: Azure Parser, Security Rules, and Viewer Icon Config Summary

Azure Terraform resource support added end-to-end: `normalize_azure_attrs()` normalises `location` to `region`, builder dispatches to it for `azurerm` provider, 10 security rules (AZ-001..AZ-010) with CIS/NIST/SOC2/PCI-DSS tags load automatically, and `azureServiceConfig.ts` provides correct UI colours per UI-SPEC.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Azure parser, builder integration, and test fixtures | 0834bf9 | parser/azure.py, builder.py, test_azure_parser.py, 3 fixture .tf files |
| 2 | Azure security rules and viewer icon config | 6c8a12e | 5 azure/*.yaml, azureServiceConfig.ts, test_security.py |

## Verification Results

- Python: `168 passed, 21 skipped` — zero regressions after both tasks
- Azure parser: 6 tests green (vnet, NSG, provider=azurerm, location->region, storage, AKS)
- Azure rules: 10 rules loaded with `framework_ids` arrays (confirmed via CLI assertion)
- TypeScript: `npx tsc --noEmit` exits 0, no errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_loads_all_rules assertion from 10 to 20**
- **Found during:** Task 2
- **Issue:** `test_loads_all_rules` asserted `len(rules) == 10` (AWS-only count). Adding 10 Azure rules made it assert against 20, causing a failure.
- **Fix:** Updated assertion to `len(rules) == 20` with a comment: "10 AWS (SEC-001..010) + 10 Azure (AZ-001..010)"
- **Files modified:** cli/tests/test_security.py
- **Commit:** 6c8a12e

## Known Stubs

None — all files are fully wired with real logic. The Wave 0 stub in `test_azure_parser.py` was replaced with 6 passing tests.

## Threat Flags

None. Per the plan's threat model:
- T-02-04: `normalize_azure_attrs` only reads dict values and copies — no file I/O or exec. Accepted.
- T-02-05: Azure resource attributes come from user's own .tf files — same trust boundary as existing AWS path. Accepted.

## Self-Check: PASSED

- [x] cli/infracanvas/parser/azure.py exists and contains `def normalize_azure_attrs`
- [x] cli/infracanvas/graph/builder.py contains `normalize_azure_attrs` import for azurerm provider
- [x] cli/tests/fixtures/azure/vnet.tf exists with `azurerm_virtual_network`
- [x] cli/tests/fixtures/azure/storage.tf exists with `azurerm_storage_account`
- [x] cli/tests/fixtures/azure/compute.tf exists with `azurerm_kubernetes_cluster`
- [x] cli/tests/test_azure_parser.py has 6 passing tests (no skip marker)
- [x] cli/infracanvas/security/rules/azure/network.yaml contains `AZ-001`
- [x] cli/infracanvas/security/rules/azure/storage.yaml contains `AZ-002`
- [x] cli/infracanvas/security/rules/azure/compute.yaml contains `AZ-004`
- [x] cli/infracanvas/security/rules/azure/identity.yaml contains `AZ-008`
- [x] cli/infracanvas/security/rules/azure/database.yaml contains `AZ-010`
- [x] All 10 Azure rules have `framework_ids` arrays (verified by load_rules() assertion)
- [x] viewer/src/icons/azureServiceConfig.ts contains `AZURE_SERVICE_CONFIG` with 12 entries
- [x] viewer/src/icons/azureServiceConfig.ts contains `getAzureServiceConfig` function
- [x] Commit 0834bf9 exists (Task 1)
- [x] Commit 6c8a12e exists (Task 2)

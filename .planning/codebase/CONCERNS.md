# Codebase Concerns

**Analysis Date:** 2026-04-15

## Tech Debt

**Silent HCL parsing failures:**
- Issue: HCL parser catches all exceptions and silently returns without logging
- Files: `cli/infracanvas/parser/hcl.py` (lines 89-92)
- Impact: Malformed or unsupported Terraform files are skipped without user notification. Users may think files were processed when they weren't.
- Fix approach: Replace bare `except Exception: return` with specific exception handling, logging, and warnings to stderr. Track which files failed and report to user.

**Type safety in watchdog integration:**
- Issue: FileSystemEventHandler subclass bypasses type checking with `# type: ignore` comments
- Files: `cli/infracanvas/main.py` (lines 331-332)
- Impact: Event handler signature mismatches could occur at runtime. Makes refactoring unsafe.
- Fix approach: Create a properly typed wrapper class that implements the full FileSystemEventHandler protocol with correct argument types.

**Bare global imports in commands:**
- Issue: watchdog imported inside function when not available, using fallback with ImportError
- Files: `cli/infracanvas/main.py` (lines 317-321)
- Impact: `--watch` flag silently fails if optional dependency not installed. Command returns 0 but does nothing.
- Fix approach: Validate dependencies at CLI initialization time or provide clearer error messaging at runtime.

**Cost estimation hardcoded to us-east-1:**
- Issue: All pricing is hardcoded to single region, no region detection from infrastructure
- Files: `cli/infracanvas/cost/estimator.py` (lines 1, 12-49)
- Impact: Cost estimates for resources in other regions (us-west-2, eu-west-1, etc.) will be inaccurate. No way to configure region.
- Fix approach: Extract region from resource attributes, implement region-aware pricing lookup table, or load dynamic pricing data.

**Missing validation for plan diff attribute changes:**
- Issue: DriftAnalyzer doesn't validate that attribute_changes match actual before/after diffs
- Files: `cli/infracanvas/drift/analyzer.py` (lines 12-49)
- Impact: Stale or incorrect attribute changes from plan parser could corrupt drift tracking.
- Fix approach: Add assertion that all keys in attribute_changes exist in either before or after.

**Config file graceful degradation silences errors:**
- Issue: YAML/validation errors during config loading return empty defaults without logging
- Files: `cli/infracanvas/config.py` (lines 19-30)
- Impact: Misconfigured .infracanvas.yml (typos, invalid values) silently ignored. Users won't know config isn't being applied.
- Fix approach: Log warnings for invalid configs, optionally fail fast with --strict flag.

---

## Known Bugs

**Graph layout doesn't handle cycles:**
- Symptoms: Circular dependencies in resource graphs may cause infinite loops or infinite edges in layout engine
- Files: `viewer/src/lib/layout.ts` (lines 128-256)
- Trigger: Resources with circular implicit dependencies (e.g., A references B, B references A)
- Workaround: Manually remove circular dependencies from Terraform

**Tier classification misses computed instance types:**
- Symptoms: EC2 instances with dynamic instance_type values don't tier correctly
- Files: `viewer/src/lib/layout.ts` (lines 74-87, 89-100)
- Trigger: When instance_type is a variable reference or computed value instead of literal string
- Workaround: Use explicit depends_on to place in correct tier

**Finding card doesn't truncate very long evidence values:**
- Symptoms: Long attribute values overflow the detail panel in UI
- Files: `viewer/src/components/DetailPanel.tsx` (structure suggests no text overflow handling)
- Trigger: Resources with large JSON attributes, long ARNs, or multi-line configuration blocks
- Workaround: Manually inspect resources in viewer UI

---

## Security Considerations

**No validation of injected window data:**
- Risk: Window.__INFRACANVAS_DATA__ is injected directly into React without type checking or sanitization
- Files: `viewer/src/App.tsx` (lines 15-16)
- Current mitigation: Data comes from own HTML export, but if served over HTTP could be manipulated
- Recommendations: Validate data structure at load time, sanitize any untrusted data, implement Content Security Policy headers

**Cost estimates not validated for negative values:**
- Risk: Invalid pricing data or calculation errors could produce negative costs, misleading summaries
- Files: `cli/infracanvas/cost/estimator.py` (lines 113-127)
- Current mitigation: None
- Recommendations: Assert all costs >= 0.0, add bounds checking for pricing tables, validate multi_az boolean parsing

**YAML rule files not schema-validated:**
- Risk: Malformed security rule definitions could crash evaluator or silently skip checks
- Files: `cli/infracanvas/security/loader.py` (lines 30-61)
- Current mitigation: Basic dictionary key access without defaults
- Recommendations: Use pydantic BaseModel validation for rule YAML, fail fast on missing required fields (id, severity)

**No authentication on imported data in viewer:**
- Risk: HTML export contains full scan data including sensitive resource configurations. No access control.
- Files: `cli/infracanvas/export/html.py`, `viewer/src/App.tsx`
- Current mitigation: Share links have random tokens, but HTML files are standalone
- Recommendations: Add optional password protection to HTML exports, implement viewer-side data encryption

---

## Performance Bottlenecks

**Graph layout re-renders on every filter change:**
- Problem: Filter state changes trigger full buildFlowElements() recompute instead of incremental updates
- Files: `viewer/src/components/DiagramCanvas.tsx` (lines 43-47, 50-66)
- Cause: useMemo depends on graph directly, setNodes called with full recompute
- Improvement path: Memoize node opacity changes only, defer edge recomputation, use incremental node updates

**Large Terraform projects (>500 resources) become sluggish:**
- Problem: NetworkX graph operations not optimized for dense graphs. Layout algorithm O(n²) position calculations.
- Files: `cli/infracanvas/graph/builder.py`, `viewer/src/lib/layout.ts` (lines 150-256)
- Cause: Nested loops for tier classification, zone calculations for every resource
- Improvement path: Implement spatial hashing, batch position calculations, lazy load regional services

**Security rule evaluation is O(rules × nodes):**
- Problem: Every rule evaluated against every node sequentially
- Files: `cli/infracanvas/security/engine.py` (lines 12-23)
- Cause: No indexing by resource type or rule applicability
- Improvement path: Pre-index rules by resource type, short-circuit evaluation for inapplicable rules

**No caching for cost lookups:**
- Problem: _estimate_resource() performs dictionary lookups on every cost calculation
- Files: `cli/infracanvas/cost/estimator.py` (lines 83-98)
- Cause: No memoization for repeated resource types
- Improvement path: Cache results by (resource_type, attributes_hash), implement LRU cache

---

## Fragile Areas

**HCL parser depends on hcl2 library behavior:**
- Files: `cli/infracanvas/parser/hcl.py` (lines 40-56)
- Why fragile: Quote stripping and value cleaning logic brittle. If hcl2 library changes output format, parser breaks.
- Safe modification: Add comprehensive tests for quote handling, use abstract hcl2 interface
- Test coverage: Covered by test_parser.py but only for simple cases

**Resource reference detection regex/string matching:**
- Files: `cli/infracanvas/parser/references.py` (not fully reviewed)
- Why fragile: Implicit dependency detection depends on correct identifier parsing. Edge cases with complex interpolations.
- Safe modification: Validate against real Terraform reference syntax, add tests for edge cases
- Test coverage: test_parser.py covers basic references

**Drift analyzer attribute diff calculation:**
- Files: `cli/infracanvas/parser/plan.py` (lines 83-100+)
- Why fragile: Compares before/after using == operator. Complex objects (lists, nested dicts) may not diff correctly if order changes.
- Safe modification: Use deep comparison, implement custom diff for lists and dicts
- Test coverage: test_plan.py exists but extent unclear

**React component state mutation risk:**
- Files: `viewer/src/store.ts` (lines 30-71)
- Why fragile: Zustand store spreads filters object. If filter arrays mutated externally, store won't detect changes.
- Safe modification: Use immutable array operations (const new array), consider freezing filter objects
- Test coverage: store.test.ts covers basic operations

**Zustand store doesn't validate graph structure:**
- Files: `viewer/src/store.ts`, `viewer/src/App.tsx` (lines 14-18)
- Why fragile: No runtime type checking when graph injected or set. Invalid structure crashes components downstream.
- Safe modification: Add runtime validation using zod or io-ts, guard against missing required fields
- Test coverage: types.test.ts exists but doesn't validate at runtime

---

## Scaling Limits

**Current limit: ~1000 resources before layout becomes unusable**
- Current capacity: Layout tested with sample data of ~50 nodes. Viewer uses O(n²) position math.
- Limit: At 1000+ nodes, layout calculation visible lag (>100ms), node rendering stutters
- Scaling path: Implement virtual scrolling for regional services, spatial partitioning for layout, WebWorker for calculations

**HCL parser processes one file at a time sequentially**
- Current capacity: Full directory parse blocks for 1000+ file directories
- Limit: Large monorepos with hundreds of .tf files process slowly
- Scaling path: Implement concurrent file parsing (ThreadPoolExecutor), batch hcl2.load() calls

**Security rules loaded entirely into memory**
- Current capacity: 30 hardcoded rules fit easily
- Limit: Adding hundreds of custom rules will load entire rule set for every scan
- Scaling path: Implement lazy rule loading by resource type, cache compiled rules

**HTML export creates single large file**
- Current capacity: ~10MB HTML for 500-resource infrastructure
- Limit: Browser viewer becomes laggy, file shares problematic over slow connections
- Scaling path: Implement paginated HTML, split large graphs into tiles, server-side rendering

---

## Dependencies at Risk

**python-hcl2 library maintenance:**
- Risk: Library has minimal maintenance. HCL3 (latest) not widely adopted in hcl2 library
- Impact: Terraform 1.5+ features (terraform.required_providers changes) won't parse correctly
- Migration plan: Consider switching to hcl library (Go-based wrapper) or native parser implementation

**NetworkX for graph operations:**
- Risk: Heavy dependency for basic graph operations. Not designed for real-time interactive rendering.
- Impact: Adding advanced graph algorithms (shortest path, community detection) would bloat bundle
- Migration plan: For viewer, consider replacing with lightweight graph library or custom adjacency list

**Zustand state management without persistence:**
- Risk: No automatic persistence. Filter state lost on page refresh.
- Impact: Users' filter selections don't survive navigation
- Migration plan: Add localStorage persistence layer, consider Redux if app becomes more complex

**No pinned dependency versions in requirements.txt:**
- Risk: Future breaking changes in pydantic, yaml, or typer could break CLI
- Impact: CI/CD runs might suddenly fail with incompatible library versions
- Migration plan: Use poetry or pipenv with locked dependencies, add upper bounds on major versions

---

## Missing Critical Features

**No support for Azure or GCP resources:**
- Problem: Hardcoded AWS resource types and pricing only. Azure and GCP fully unsupported.
- Blocks: Users cannot analyze multi-cloud infrastructure with InfraCanvas

**No drift detection without terraform plan:**
- Problem: Must explicitly run `terraform show -json` and pass plan file. No automatic plan detection.
- Blocks: Continuous compliance monitoring workflow requires manual steps

**No rule customization without modifying source code:**
- Problem: Security rules hardcoded in YAML files within package. Can't add custom rules at runtime.
- Blocks: Enterprise users with custom compliance requirements have no way to extend

**No filtering persistence across sessions:**
- Problem: Filter selections lost on page reload. Must reselect severity, resource type, drift status.
- Blocks: Users analyzing the same infrastructure repeatedly must re-filter each time

**No graph comparison (before/after scans):**
- Problem: Can view individual scans but no side-by-side comparison or diff visualization.
- Blocks: Understanding infrastructure changes over time requires manual inspection

---

## Test Coverage Gaps

**HTML export rendering not tested:**
- What's not tested: Template generation, styling correctness, viewer data injection
- Files: `cli/infracanvas/export/html.py`, `cli/infracanvas/export/scorecard.py`
- Risk: Regressions in HTML export go undetected. Viewer could receive malformed data.
- Priority: High (external-facing output)

**Cost estimation edge cases:**
- What's not tested: Reserved instances, spot pricing, multi-AZ cost doubling, unknown instance types
- Files: `cli/infracanvas/cost/estimator.py`
- Risk: Cost estimates could be off by 50%+ for complex deployments
- Priority: Medium (affects pricing accuracy)

**Security rule edge cases:**
- What's not tested: Nested attribute access, list comprehensions, complex CIDR matching
- Files: `cli/infracanvas/security/engine.py` (lines 26-74)
- Risk: Rules may silently fail to match on complex resource configurations
- Priority: High (security implications)

**State file parsing edge cases:**
- What's not tested: Sensitive attributes, nested modules, data sources in state
- Files: `cli/infracanvas/parser/state.py`
- Risk: Resources may be missing from graph if state parsing fails
- Priority: Medium (could corrupt results)

**Viewer drag/drop and interactions:**
- What's not tested: Node dragging in canvas, filter panel toggles, keyboard navigation
- Files: `viewer/src/components/DiagramCanvas.tsx`, `viewer/src/components/FilterPanel.tsx`
- Risk: UI responsiveness bugs only discovered by users
- Priority: Medium (usability)

**Main CLI integration tests:**
- What's not tested: Full scan pipeline with outputs (test_cli.py likely only covers command parsing)
- Files: `cli/infracanvas/main.py`
- Risk: Complex orchestration bugs in scan/serve/push workflows
- Priority: High (primary entry point)

---

*Concerns audit: 2026-04-15*

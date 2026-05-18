"""Phase 12 D-11 — Python network detectors (path-aware rules).

Distinct from ``cli/infracanvas/security/rules/`` (YAML attribute rules).
Path-aware logic (compare-two-path-objects) is materially harder to
express in the YAML operator set; one rule (NET-010) does not justify
expanding the engine. This subpackage holds path-aware detectors that
emit ``NetworkFinding`` through the existing aggregation pipeline (Phase 2
D-09 / Phase 3 D-12) via ``rule_id="NET-010"`` + ``source="network"``.

The YAML catalog (``cli/infracanvas/security/rules/``) intentionally does
NOT carry NET-010. Catalog count stays 51; the active-detector count
rises to 52.
"""

"""Phase 12 pure-compute modules (D-01).

NO I/O. NO DB. Pure functions over Pydantic + ORM-row-shaped inputs.
The taskiq job in app.queue.tasks.path_compute orchestrates fetches +
calls these functions + persists results.

Public surface:
- lpm.build_trie / lpm.lookup
- forward.compute_forward
- pair.compute_pair
- correlate.matches / correlate.emit_divergence  (v1.1 endpoint-only)
- asymmetry.is_asymmetric / asymmetry.asymmetric_nodes
- classify.score_nat / classify.score_leak / classify.score_local_pref / classify.classify
- impact.impact_bytes_per_sec / impact.impact_firewall_count
"""
from __future__ import annotations

"""Regression guard: the shipped viewer_template.html must contain Phase 3 FlowMap UI.

This test exists because Phase 3 UAT (2026-04-19) found the CLI was shipping a
stale Phase-2 viewer bundle even though all Phase 3 viewer source had landed.
Root cause: no automated sync from viewer/dist/index.html into
cli/infracanvas/export/viewer_template.html.

Companion mitigations:
  - viewer/package.json `postbuild` hook (automatic sync on every npm run build)
  - this test (fails CI if a future change still drifts)

If this test fails, run `cd viewer && npm run build` — the postbuild hook
will resync the template. If the hook is broken, fix viewer/package.json
before re-running.
"""

from __future__ import annotations

from pathlib import Path

import pytest

TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "infracanvas"
    / "export"
    / "viewer_template.html"
)

# Tokens that MUST appear in a correctly built Phase 3 viewer bundle.
# Derived from viewer/src Phase 3 components:
#   - FlowMap        : TabBar label (viewer/src/components/TabBar.tsx)
#   - BETA           : Beta pill on FlowMap tab + empty state
#   - activeTab      : Zustand store field (viewer/src/store/useStore.ts)
#   - No network topology collected yet : FlowMapEmptyState headline
REQUIRED_TOKENS = (
    "FlowMap",
    "BETA",
    "activeTab",
    "No network topology collected yet",
)

# The placeholder that cli/infracanvas/export/html.py replaces with graph JSON.
# If this disappears, `infracanvas scan` will silently produce HTML with no data.
DATA_PLACEHOLDER = "window.__INFRACANVAS_DATA__ = null;"

# A legitimate Phase 3 bundle is ~3.5 MB; a broken/empty copy would be KB-scale.
MIN_TEMPLATE_BYTES = 1_000_000


@pytest.fixture(scope="module")
def template_text() -> str:
    assert TEMPLATE_PATH.exists(), (
        f"Viewer template not found at {TEMPLATE_PATH}. "
        "Run `cd viewer && npm run build` — the postbuild hook copies "
        "dist/index.html into the CLI package."
    )
    return TEMPLATE_PATH.read_text()


def test_viewer_template_contains_flowmap_tokens(template_text: str) -> None:
    """Bundled template must contain Phase 3 FlowMap UI markers."""
    missing = [tok for tok in REQUIRED_TOKENS if tok not in template_text]
    assert not missing, (
        f"viewer_template.html is missing Phase 3 FlowMap tokens: {missing}. "
        "The bundled CLI template is stale. Run `cd viewer && npm run build` "
        "to trigger the postbuild sync hook."
    )


def test_viewer_template_placeholder_intact(template_text: str) -> None:
    """html.py replaces this placeholder at export time — if it's gone, scans produce blank viewers."""
    assert DATA_PLACEHOLDER in template_text, (
        f"Placeholder '{DATA_PLACEHOLDER}' missing from viewer_template.html. "
        "cli/infracanvas/export/html.py will not be able to inject graph data."
    )


def test_viewer_template_not_trivially_small() -> None:
    """Catch a sync step that accidentally copied an empty or error page."""
    size = TEMPLATE_PATH.stat().st_size
    assert size >= MIN_TEMPLATE_BYTES, (
        f"viewer_template.html is only {size} bytes — expected >= "
        f"{MIN_TEMPLATE_BYTES}. The bundle may be broken or truncated."
    )

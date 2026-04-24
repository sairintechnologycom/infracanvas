"""Observability tests — JSON log shape and secret scrubbing (OBS-001..OBS-003)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import create_app


def test_request_log_is_json_with_required_fields(capsys) -> None:
    """OBS-001: every request produces one JSON log line with request_id + method + path + status + duration_ms."""
    with TestClient(create_app()) as client:
        rid = "test-obs-01"
        client.get("/healthz", headers={"X-Request-ID": rid})
    out = capsys.readouterr().out.strip().splitlines()
    request_lines = []
    for line in out:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("event") == "request":
            request_lines.append(payload)
    assert len(request_lines) >= 1, f"no 'request' log lines found in {out!r}"
    entry = request_lines[-1]
    assert entry["request_id"] == rid
    assert entry["method"] == "GET"
    assert entry["path"] == "/healthz"
    assert entry["status"] == 200
    assert isinstance(entry["duration_ms"], int | float)


def test_scrub_redacts_authorization_header() -> None:
    """OBS-002: scrub_sensitive processor redacts known secret keys."""
    from app.obs.logging import scrub_sensitive

    out = scrub_sensitive(
        None,
        None,
        {
            "event": "foo",
            "authorization": "Bearer secret",
            "stripe-signature": "t=1,v1=abc",
            "other": "keep",
        },
    )
    assert out["authorization"] == "<redacted>"
    assert out["stripe-signature"] == "<redacted>"
    assert out["other"] == "keep"


def test_scrub_redacts_r2_url_query() -> None:
    """OBS-003: R2 presigned URL query strings are stripped in logs."""
    from app.obs.logging import scrub_sensitive

    url = (
        "https://abc.r2.cloudflarestorage.com/bucket/key.json"
        "?X-Amz-Signature=secret&X-Amz-Expires=300"
    )
    out = scrub_sensitive(None, None, {"url": url})
    assert "X-Amz-Signature" not in out["url"]
    assert out["url"].endswith("?<redacted>")

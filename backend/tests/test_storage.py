"""moto-backed R2 client tests (STO-001..004).

These exercise the boto3 helpers in :mod:`app.storage.r2` against a
moto-mocked S3 bucket (R2 is S3-compatible at the protocol level so moto
is faithful enough for the contract assertions we care about: presigned
URL shape, HEAD round-trip, copy + delete semantics).

We replace the cached R2 client with a plain moto-mocked S3 client (no
custom endpoint_url) for the duration of each test. moto intercepts
botocore at the HTTP layer when no endpoint_url is set; with an
endpoint_url moto's interception is unreliable across versions, so the
simpler path is to use a stock S3 client. The presigned-URL test
reinstates a real R2-style client just to assert URL shape.
"""
from __future__ import annotations

import os

import boto3
import pytest
from botocore.config import Config


@pytest.fixture(autouse=True)
def _reset_r2_client_cache() -> None:
    """Clear the lru_cache on get_r2_client between tests so each test
    starts from a clean client built against the current settings/env."""
    from app.storage.r2 import get_r2_client

    get_r2_client.cache_clear()
    yield
    get_r2_client.cache_clear()


def _swap_r2_client_for_moto(monkeypatch: pytest.MonkeyPatch, bucket: str) -> None:
    """Replace ``get_r2_client`` with a function returning a moto-friendly
    S3 client (no custom endpoint_url) AND override ``settings.r2_bucket``
    to the moto bucket. This is the most reliable way to drive moto across
    boto3/moto version combos without depending on endpoint_url matching.
    """
    from app.settings import settings
    from app.storage import r2 as r2_mod

    monkeypatch.setattr(settings, "r2_bucket", bucket)

    moto_client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
    )

    def _client_override():  # type: ignore[no-untyped-def]
        return moto_client

    monkeypatch.setattr(r2_mod, "get_r2_client", _client_override)


def test_presigned_put_contains_no_content_length_range(
    mock_r2, monkeypatch
) -> None:
    """STO-001: presigned PUT URL must NOT encode Content-Length-Range.

    Research callout #2: R2 doesn't honour that condition on presigned PUT
    even when the bound length matches. Size enforcement is at commit-time
    HEAD, not URL sign time.

    This test asserts URL *shape* — it does NOT need a working bucket; the
    real R2 client (with its custom endpoint_url) is fine here because
    boto3 generates the URL locally without making a network call.
    """
    from app.storage.r2 import presigned_put

    # Use the real (un-mocked) get_r2_client; presigned URL generation is
    # local-only.
    url = presigned_put("pending/01HX0000000000000000000001.json")
    # The condition would surface as content-length-range in either the
    # query string (older signing) or the X-Amz-SignedHeaders list.
    assert "content-length-range" not in url.lower()
    # Sanity: it IS a presigned SigV4 URL.
    assert "X-Amz-Signature=" in url


def test_head_roundtrip(mock_r2, monkeypatch) -> None:
    """STO-002: HEAD returns the ContentLength of a freshly uploaded object."""
    _swap_r2_client_for_moto(monkeypatch, mock_r2.bucket)
    from app.storage.r2 import get_r2_client, head

    key = "pending/01HX0000000000000000000002.json"
    body = b'{"x":1}'
    get_r2_client().put_object(
        Bucket=mock_r2.bucket, Key=key, Body=body, ContentType="application/json"
    )
    h = head(key)
    assert h["ContentLength"] == len(body)


def test_get_returns_bytes(mock_r2, monkeypatch) -> None:
    """STO-003: get_bytes round-trips the object body verbatim."""
    _swap_r2_client_for_moto(monkeypatch, mock_r2.bucket)
    from app.storage.r2 import get_bytes, get_r2_client

    key = "pending/01HX0000000000000000000003.json"
    body = b'{"hello":"world"}'
    get_r2_client().put_object(Bucket=mock_r2.bucket, Key=key, Body=body)
    assert get_bytes(key) == body


async def test_put_bytes_uploads_to_r2(mock_r2, monkeypatch) -> None:
    """STO-005: ``put_bytes`` writes the object to the configured bucket
    with the given key/body/content-type via boto3 ``put_object``.

    Worker-side helper (Phase 7.5 Plan 06): the ``scan_repo`` taskiq job
    uploads the scan JSON blob directly under
    ``teams/{team_id}/scans/{scan_id}.json`` — no presigned-PUT round
    trip because the worker IS the trusted writer.
    """
    _swap_r2_client_for_moto(monkeypatch, mock_r2.bucket)
    from app.storage.r2 import get_bytes, head, put_bytes

    key = "teams/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/scans/sc_005.json"
    body = b'{"hello":"put_bytes"}'

    await put_bytes(key, body, "application/json")

    assert get_bytes(key) == body
    h = head(key)
    assert h["ContentLength"] == len(body)
    assert h["ContentType"] == "application/json"


async def test_put_bytes_runs_in_threadpool(mock_r2, monkeypatch) -> None:
    """STO-006: ``put_bytes`` offloads the blocking boto3 call via
    ``fastapi.concurrency.run_in_threadpool`` so it does not block the
    worker asyncio event loop.

    boto3 is sync; calling it directly inside an async coroutine would
    pin the event loop for the duration of the upload. We assert the
    helper invokes ``run_in_threadpool`` exactly once per call.
    """
    _swap_r2_client_for_moto(monkeypatch, mock_r2.bucket)
    from app.storage import r2 as r2_mod

    call_log: list[str] = []
    real_run_in_threadpool = r2_mod.run_in_threadpool

    async def _spy(fn, *args, **kwargs):  # type: ignore[no-untyped-def]
        call_log.append("invoked")
        return await real_run_in_threadpool(fn, *args, **kwargs)

    monkeypatch.setattr(r2_mod, "run_in_threadpool", _spy)

    key = "teams/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/scans/sc_006.json"
    await r2_mod.put_bytes(key, b"x", "application/json")
    assert call_log == ["invoked"], (
        f"expected exactly one threadpool offload, saw {call_log!r}"
    )


async def test_put_bytes_propagates_boto_error(mock_r2, monkeypatch) -> None:
    """STO-007: a boto3 ``ClientError`` from ``put_object`` re-raises out
    of ``put_bytes`` so the worker can flip the scan to ``failed``.

    The helper does not swallow R2 transport errors — the worker's
    outer try/except is the single failure-handling site, which keeps
    the failure-path UPDATE invariant in one place.
    """
    from botocore.exceptions import ClientError

    from app.storage import r2 as r2_mod

    class _BoomClient:
        def put_object(self, **kwargs):  # type: ignore[no-untyped-def]
            raise ClientError(
                error_response={"Error": {"Code": "InternalError", "Message": "boom"}},
                operation_name="PutObject",
            )

    monkeypatch.setattr(r2_mod, "get_r2_client", lambda: _BoomClient())

    with pytest.raises(ClientError):
        await r2_mod.put_bytes("teams/x/scans/sc.json", b"x", "application/json")


def test_copy_then_delete_moves_pending_to_final(mock_r2, monkeypatch) -> None:
    """STO-004 (D-11): commit flow copies pending/ → teams/{team_id}/scans/
    then deletes the pending/ source. After the move, only the final key
    exists; the lifecycle rule will GC any pending/ objects we leave
    behind on copy failure (Plan 08).
    """
    _swap_r2_client_for_moto(monkeypatch, mock_r2.bucket)
    from botocore.exceptions import ClientError

    from app.storage.r2 import copy, delete, get_bytes, get_r2_client, head

    src = "pending/01HX0000000000000000000004.json"
    dst = (
        "teams/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/"
        "scans/01HX0000000000000000000004.json"
    )
    body = b'{"resource_graph":true}'
    client = get_r2_client()
    client.put_object(Bucket=mock_r2.bucket, Key=src, Body=body)

    copy(src_key=src, dst_key=dst)
    delete(src)

    # Final exists with the expected bytes.
    assert get_bytes(dst) == body
    # Pending source is gone — HEAD raises ClientError 404.
    with pytest.raises(ClientError):
        head(src)

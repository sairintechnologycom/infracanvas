"""Cloudflare R2 client + presigned URL helpers.

R2 is S3-compatible but REQUIRES SigV4 (``signature_version="s3v4"``) — older
SigV2 signatures are rejected. The boto3 client is constructed with that
config and pointed at the per-account R2 endpoint.

Two-step upload layout (D-11):

    pending/{scan_id}.json          <-- presigned PUT target; 7-day GC lifecycle
    teams/{team_id}/scans/{scan_id}.json   <-- final committed key

The presigned PUT URL DOES NOT carry a Content-Length-Range condition —
research callout #2: R2 does not support that condition on presigned PUT
(it returns ``SignatureDoesNotMatch`` even when the bound length matches).
Size enforcement happens at commit time via :func:`head` (RESEARCH § F5).

All boto3 calls are blocking; route layer wraps them in
``run_in_threadpool`` to avoid blocking the asyncio event loop.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from app.settings import settings


@lru_cache(maxsize=1)
def get_r2_client() -> BaseClient:
    """Return a singleton boto3 S3 client configured for Cloudflare R2.

    Cached because ``boto3.client`` is non-trivial to construct (loads
    botocore models from disk) and the configuration never changes for
    the lifetime of the process.
    """
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),  # REQUIRED for R2 (RESEARCH F5)
    )


def presigned_put(
    key: str,
    content_type: str = "application/json",
    expires_in: int = 600,
) -> str:
    """Generate a presigned PUT URL for ``key``.

    NOTE (research callout #2): we DO NOT add a Content-Length-Range entry
    to ``Params``. R2 rejects that condition on presigned PUT. Size cap is
    enforced at commit-time via :func:`head` against the resulting object.
    """
    return get_r2_client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.r2_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
        HttpMethod="PUT",
    )


def presigned_get(key: str, expires_in: int = 300) -> str:
    """Generate a presigned GET URL with default 5-minute TTL.

    Short TTL (≤300s) bounds the leak window if the URL is logged or shared
    inadvertently. The team_id is baked into ``key`` server-side from the
    authenticated principal — clients cannot influence it.
    """
    return get_r2_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def head(key: str) -> dict[str, Any]:
    """HEAD an object — returns ``{"ContentLength": int, "ETag": str, ...}``.

    Used at commit time to enforce the 25-MB size cap. Raises
    ``botocore.exceptions.ClientError`` with code 404/NotFound/NoSuchKey
    when the object doesn't exist (the route translates that to HTTP 404).
    """
    return get_r2_client().head_object(Bucket=settings.r2_bucket, Key=key)


def get_bytes(key: str) -> bytes:
    """Read an object's body fully into memory.

    Acceptable here because the size cap (25 MB enforced upstream by
    :func:`head`) bounds memory use to a known constant per request.
    """
    obj = get_r2_client().get_object(Bucket=settings.r2_bucket, Key=key)
    return obj["Body"].read()


def copy(src_key: str, dst_key: str) -> None:
    """Server-side copy inside the same bucket: ``src_key`` → ``dst_key``.

    Commit flow uses this to move ``pending/{scan_id}.json`` to
    ``teams/{team_id}/scans/{scan_id}.json`` after the DB+Stripe tx
    succeeds (D-11). Server-side copy avoids streaming bytes through the
    backend.
    """
    get_r2_client().copy_object(
        Bucket=settings.r2_bucket,
        Key=dst_key,
        CopySource={"Bucket": settings.r2_bucket, "Key": src_key},
    )


def delete(key: str) -> None:
    """Delete a single object."""
    get_r2_client().delete_object(Bucket=settings.r2_bucket, Key=key)

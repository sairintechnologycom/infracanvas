"""structlog JSON logging configuration + secret-scrubbing processor.

Processor pipeline (order matters):

    merge_contextvars -> add_log_level -> TimeStamper(iso) ->
    scrub_sensitive -> StackInfoRenderer -> dict_tracebacks ->
    JSONRenderer(orjson.dumps)

``scrub_sensitive`` mitigates threat T-06-08 (information disclosure via
stdout log drain) by redacting known-sensitive keys and stripping R2
presigned-URL query strings.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import orjson
import structlog

_SCRUB_KEYS = {
    "authorization",
    "x-signature",
    "cookie",
    "stripe-signature",
    "svix-signature",
    "svix-id",
    "clerk-webhook-secret",
    "stripe_secret_key",
    "r2_secret_access_key",
    "clerk_webhook_secret",
}

# Matches Cloudflare R2 presigned URLs; captures the path up to (but not
# including) the ``?`` so we can preserve the URL shape while stripping the
# signature query string.
_R2_URL_RE = re.compile(
    r"(https://[^.]+\.r2\.cloudflarestorage\.com/[^?\s]+)\?[^\s\"]+"
)


def scrub_sensitive(
    _logger: Any, _method: Any, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """structlog processor — redact known-sensitive keys and R2 query strings."""
    for k in list(event_dict.keys()):
        if k.lower() in _SCRUB_KEYS:
            event_dict[k] = "<redacted>"
    for k, v in event_dict.items():
        if isinstance(v, str):
            event_dict[k] = _R2_URL_RE.sub(r"\1?<redacted>", v)
    return event_dict


def configure_logging(*, level: int = logging.INFO) -> None:
    """Configure structlog once at import; idempotent (cache_logger_on_first_use)."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            scrub_sensitive,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(serializer=orjson.dumps),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

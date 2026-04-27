"""Clerk JWT validation + role gate.

`require_principal` validates the Bearer token against Clerk's JWKS using
``algorithms=["RS256"]`` (T-06-06: algorithm confusion prevention — never
let `none` or HS256 pass), then extracts the v2 session claims into a typed
:class:`ClerkPrincipal`.

`require_role(*allowed)` is a FastAPI dep factory that gates downstream
routes on the principal's organization role (Clerk membership ``rol`` slug).

Audience handling: Clerk session tokens carry ``azp`` (authorized party)
rather than ``aud`` (RESEARCH § P8). We pass ``audience=None`` to
``jwt.decode`` and check ``azp`` against ``settings.clerk_allowed_origins``
in a separate explicit step to avoid PyJWT's audience-mismatch path silently
masking azp validation.
"""

from __future__ import annotations

from typing import Any

import jwt
import sentry_sdk
import structlog
from fastapi import Depends, HTTPException, Request, status
from jwt import InvalidTokenError, PyJWKClient
from pydantic import BaseModel

from app.settings import settings

# Single module-level JWKS client; cached keys with 1h lifespan to avoid
# hammering Clerk's JWKS endpoint per request. PyJWKClient handles its own
# rate-limited refresh on cache miss.
_jwks_client = PyJWKClient(
    settings.clerk_jwks_url,
    cache_keys=True,
    lifespan=3600,
)


class ClerkPrincipal(BaseModel):
    """Validated Clerk session principal.

    Fields:
        user_id: ``sub`` claim (Clerk user id, ``user_xxx``).
        session_id: ``sid`` claim (Clerk session id, ``sess_xxx``).
        clerk_org_id: ``o.id`` claim (Clerk organization id, ``org_xxx``).
        role: ``o.rol`` claim (organization-membership role slug; e.g.
            ``"admin"``, ``"basic_member"``, ``"owner"``, custom).
        request_id: Request-scoped log id, copied from the structlog
            contextvar set by :class:`RequestContextMiddleware`.
    """

    user_id: str
    session_id: str
    clerk_org_id: str
    role: str
    request_id: str = ""


def _bearer(request: Request) -> str:
    """Extract Bearer token from Authorization header. 401 if missing/malformed."""
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_bearer")
    return h.split(" ", 1)[1].strip()


async def require_principal(request: Request) -> ClerkPrincipal:
    """Validate Clerk session JWT and return :class:`ClerkPrincipal`.

    Validation order (each raises an explicit error code on failure):

    1. ``missing_bearer`` (401) — no/wrong Authorization header.
    2. ``invalid_token`` (401) — JWT signature/expiry/required-claim failures.
       PyJWT enforces ``algorithms=["RS256"]`` (T-06-06).
    3. ``azp_mismatch`` (401) — ``azp`` claim not in
       ``settings.clerk_allowed_origins``.
    4. ``no_active_organization`` (403) — ``o`` claim missing or no
       ``o.id``. Clerk emits no ``o`` when the user has no active org.

    On success: binds ``user_id`` and ``clerk_org_id`` to the structlog
    contextvar, sets matching Sentry user/tags. ``team_id`` is NOT bound
    here — that happens in :func:`resolve_team_from_clerk_org` after the
    DB lookup.
    """
    token = _bearer(request)
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token).key
        claims: dict[str, Any] = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],  # algorithm confusion protection (T-06-06)
            issuer=settings.clerk_issuer,
            audience=None,  # Clerk uses azp, not aud (RESEARCH § P8)
            options={"require": ["exp", "iat", "sub", "sid"]},
            leeway=10,
        )
    except InvalidTokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token") from e

    if claims.get("azp") not in settings.clerk_allowed_origins:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "azp_mismatch")

    o = claims.get("o")
    if not o or not o.get("id"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "no_active_organization")

    rid = structlog.contextvars.get_contextvars().get("request_id", "")
    principal = ClerkPrincipal(
        user_id=claims["sub"],
        session_id=claims["sid"],
        clerk_org_id=o["id"],
        role=o.get("rol", ""),
        request_id=rid,
    )

    structlog.contextvars.bind_contextvars(
        user_id=principal.user_id,
        clerk_org_id=principal.clerk_org_id,
    )
    sentry_sdk.set_user({"id": principal.user_id})
    sentry_sdk.set_tag("clerk_org_id", principal.clerk_org_id)
    sentry_sdk.set_tag("request_id", rid)
    return principal


def require_role(*allowed: str):
    """FastAPI dep factory that requires the principal's role be in ``allowed``.

    Returns 403 ``forbidden_role`` if the role does not match. Composes on
    top of :func:`require_principal` (one JWT validation per request).
    """

    async def _dep(p: ClerkPrincipal = Depends(require_principal)) -> ClerkPrincipal:
        if p.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden_role")
        return p

    return _dep

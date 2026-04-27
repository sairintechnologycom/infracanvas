"""Clerk webhook endpoint.

`POST /v1/webhooks/clerk` reads the raw request body bytes (NEVER
deserializes via the parsed-JSON helper — Svix HMAC must verify the
byte-exact payload before any deserialisation, RESEARCH § F2 critical
pitfall) and forwards to :func:`app.auth.webhooks.verify_and_dispatch`.

Bad signature → 401 ``bad_signature``. Successful dispatch → 200
``{"ok": true}``. Unknown event types are also 200 (handler swallows them).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.webhooks import verify_and_dispatch
from app.db.session import raw_session

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@router.post("/clerk", status_code=200)
async def clerk_webhook(
    request: Request,
    session: AsyncSession = Depends(raw_session),
) -> dict[str, bool]:
    body = await request.body()  # RAW BYTES — never .json() (RESEARCH § F2)
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }
    try:
        await verify_and_dispatch(body, headers, session)
    except PermissionError as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "bad_signature"
        ) from e
    return {"ok": True}

"""Stripe v2 meter-event posting for the per-scan billing meter.

Uses ``stripe.v2.billing.meter_events.create`` (the v2 API per RESEARCH §
F8). Research callout #3: the legacy ``stripe.billing.MeterEvent.create``
namespace and ``create_usage_record`` are explicitly NOT used — the v2
endpoint is the supported path for usage-based meters.

Dual idempotency layer (D-09 / TMM-02):

* ``identifier`` — Stripe-side 24h dedup window keyed on this string.
  Two events with the same ``(event_name, identifier)`` collapse into one
  on Stripe's side — protects against client retries that succeed
  server-side but lose the response.
* ``idempotency_key`` — HTTP-level Stripe-Idempotency-Key header (also a
  24h window). Protects against transport-layer retries (network blip
  between us and Stripe; both sides ack but we don't see the response).

Both keys are set to ``scan_id`` so the entire (event_name, scan_id)
domain is duplicated-protected end-to-end.

Failure semantics: this function raises ``stripe.error.StripeError`` on
any non-2xx response. Caller MUST be inside its DB transaction so the
exception aborts the tx — preserving the invariant "every committed scan
row has a meter event" (D-09).
"""
from __future__ import annotations

import stripe

from app.settings import settings


def _client() -> stripe.StripeClient:
    """Construct a fresh ``StripeClient`` bound to the configured secret.

    Cheap to build (no network); tests can override
    ``settings.stripe_secret_key`` and the next call picks it up. v15+
    of stripe-python exposes the v2 namespace only via ``StripeClient``
    (the legacy module-level ``stripe.v2.billing.meter_events.create``
    no longer exists at runtime, despite older docs).
    """
    return stripe.StripeClient(settings.stripe_secret_key)


async def record_scan_meter_event(
    *, scan_id: str, stripe_customer_id: str
) -> None:
    """Post one Stripe v2 meter event for a successful scan commit.

    Args:
        scan_id: UUIDv7 of the committed scan; used as both ``identifier``
            and ``idempotency_key`` (dual idempotency, see module
            docstring).
        stripe_customer_id: Pre-existing Stripe customer id from
            ``Team.stripe_customer_id`` (provisioned by the
            organization.created webhook in Plan 06-04).

    Raises:
        stripe.error.StripeError: any non-2xx response. Caller must be
            inside a DB transaction so the exception triggers rollback.
    """
    # Resource path: stripe.v2.billing.meter_events.create — confirmed via
    # `dir(StripeClient().v2.billing.meter_events)` on stripe-python 15.1.
    _client().v2.billing.meter_events.create(
        params={
            "event_name": settings.stripe_meter_event_name,  # "infracanvas.scan"
            "payload": {
                "stripe_customer_id": stripe_customer_id,
                "value": "1",
            },
            "identifier": scan_id,
        },
        options={"idempotency_key": scan_id},
    )

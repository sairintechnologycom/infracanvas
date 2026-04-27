"""SDK-boundary Stripe v2 meter-event tests (MET-001..003).

We mock at the SDK boundary (``stripe_meter._client``) rather than at
the HTTP layer. Rationale: stripe-python v15 routes V2 calls through a
``StripeClient``-internal request stack that uses ``requests`` (not
``httpx``), so respx-based interception (which only hooks httpx) does
not catch them. Patching the SDK call site is more robust across SDK
versions and tests the same observable contract — that the recorder
calls the right resource path with the right params + idempotency key.

The ``mock_stripe`` fixture from ``tests/conftest.py`` is intentionally
NOT used here for that reason. (It is still used by ``test_scans.py``
for scenarios that exercise both SDK + DB rollback together.)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class _MeterCall:
    """One captured ``meter_events.create(params=..., options=...)`` call."""

    params: dict[str, Any]
    options: dict[str, Any] | None


@dataclass
class _Capturing:
    """Stand-in for ``StripeClient`` that records calls and returns a dummy.

    Mimics the shape ``client.v2.billing.meter_events.create(params=...,
    options=...)`` that ``record_scan_meter_event`` invokes.
    """

    calls: list[_MeterCall] = field(default_factory=list)

    def install(self, monkeypatch: Any) -> None:
        from app.billing import stripe_meter

        outer = self

        class _MeterEvents:
            def create(self, *, params: Any, options: Any = None) -> Any:
                outer.calls.append(_MeterCall(params=dict(params), options=options))
                # Return None — caller doesn't use the response.
                return None

        class _Billing:
            meter_events = _MeterEvents()

        class _V2:
            billing = _Billing()

        class _Client:
            v2 = _V2()

        monkeypatch.setattr(stripe_meter, "_client", lambda: _Client())


@pytest.mark.asyncio
async def test_meter_event_sends_v2_endpoint(monkeypatch: Any) -> None:
    """MET-001: record_scan_meter_event invokes
    ``client.v2.billing.meter_events.create`` with the configured
    event_name + identifier + customer/value payload."""
    from app.billing.stripe_meter import record_scan_meter_event

    cap = _Capturing()
    cap.install(monkeypatch)

    await record_scan_meter_event(scan_id="sc_1", stripe_customer_id="cus_1")

    assert len(cap.calls) == 1
    params = cap.calls[0].params
    assert params["event_name"] == "infracanvas.scan"
    assert params["identifier"] == "sc_1"
    assert params["payload"]["stripe_customer_id"] == "cus_1"
    assert str(params["payload"]["value"]) == "1"


@pytest.mark.asyncio
async def test_meter_event_uses_idempotency_key(monkeypatch: Any) -> None:
    """MET-002: idempotency_key option == scan_id.

    The Stripe SDK forwards this as the HTTP ``Idempotency-Key`` header
    on the underlying request — Stripe applies a 24h dedup window keyed on
    that string. Combined with the in-body ``identifier`` (also = scan_id,
    a 24h server-side dedup window on its own), this is the dual
    idempotency layer described in the module docstring.
    """
    from app.billing.stripe_meter import record_scan_meter_event

    cap = _Capturing()
    cap.install(monkeypatch)

    await record_scan_meter_event(scan_id="sc_2", stripe_customer_id="cus_1")

    assert len(cap.calls) == 1
    options = cap.calls[0].options or {}
    assert options.get("idempotency_key") == "sc_2"


@pytest.mark.asyncio
async def test_meter_event_raises_on_stripe_error(monkeypatch: Any) -> None:
    """MET-003: any Stripe error raised by the SDK propagates to the caller.

    The commit handler depends on this property for DB rollback: if
    Stripe rejects the event, the exception aborts the enclosing tx so
    no scan row is committed without a matching meter event (D-09).
    """
    import stripe

    from app.billing import stripe_meter

    class _MeterEvents:
        def create(self, *, params: Any, options: Any = None) -> Any:
            raise stripe.error.APIError("boom")

    class _Billing:
        meter_events = _MeterEvents()

    class _V2:
        billing = _Billing()

    class _Client:
        v2 = _V2()

    monkeypatch.setattr(stripe_meter, "_client", lambda: _Client())

    with pytest.raises(stripe.error.StripeError):
        await stripe_meter.record_scan_meter_event(
            scan_id="sc_3", stripe_customer_id="cus_1"
        )

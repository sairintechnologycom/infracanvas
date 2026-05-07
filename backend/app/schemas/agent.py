"""DC Agent request/response Pydantic schemas (Phase 10 DCA-05).

Locked contracts consumed by both backend routes and the Go push client
(Plan 10-07). Changes here MUST be mirrored in the Go RoutesPushBody /
FlowsPushBody structs.

T-10-02-06 mitigation: RoutesPushBody.routes and FlowsPushBody.flows are
bounded at 10 000 records per batch to prevent unbounded payload allocation.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSiteBody(BaseModel):
    """Request body for POST /v1/sites."""

    name: str = Field(..., min_length=1, max_length=200)


class CreateSiteResp(BaseModel):
    """Response for POST /v1/sites — site_token returned ONCE; never again.

    Per CONTEXT.md D-03: only the SHA-256 hash is persisted in dc_sites.
    The plaintext token must be copied by the operator immediately.
    """

    site_id: str
    name: str
    site_token: str  # plaintext, one-time


class RouteRecord(BaseModel):
    """A single routing-table entry collected from a DC device."""

    prefix: str
    next_hop: str
    protocol: str
    metric: int = 0
    as_path: str = ""


class RoutesPushBody(BaseModel):
    """Request body for POST /v1/agent/routes.

    T-10-02-06: routes bounded at 10 000 to prevent DoS via unbounded
    payload allocation.
    """

    site_id: str
    collected_at: str  # ISO 8601
    device_host: str
    routes: list[RouteRecord] = Field(..., max_length=10000)


class FlowRecord(BaseModel):
    """A single NetFlow v9/IPFIX record collected by the UDP listener."""

    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: int
    bytes: int
    packets: int


class FlowsPushBody(BaseModel):
    """Request body for POST /v1/agent/flows.

    T-10-02-06: flows bounded at 10 000 to prevent DoS via unbounded
    payload allocation.
    """

    site_id: str
    collected_at: str  # ISO 8601
    flows: list[FlowRecord] = Field(..., max_length=10000)

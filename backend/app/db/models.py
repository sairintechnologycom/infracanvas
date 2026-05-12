"""SQLAlchemy 2.0 ORM models for the SaaS backend.

Per RESEARCH § F4: Team + Scan tables with team-scoped RLS applied in
migration 002_rls_setup. Every team-scoped table carries `team_id` as the
isolation discriminant used by `current_setting('app.current_team_id', true)`.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScanStatus(StrEnum):
    pending = "pending"
    ready = "ready"
    failed = "failed"


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    clerk_org_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    r2_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus, name="scan_status", native_enum=True),
        nullable=False,
        default=ScanStatus.pending,
    )
    summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Phase 7.5 D-12 / D-13 — GitHub repo connector provenance + debug fields.
    source_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_installation_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    github_repo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ShareLink(Base):
    """Share-link row.

    Security model (D-13..D-16):
    - ``token_hash``: bcrypt hash of the raw URL-safe token (cost 12). Verified in
      Python with ``bcrypt.checkpw`` after the row is fetched.
    - ``token_lookup_hash``: SHA-256 hex of the raw token. Deterministic, indexed,
      enables O(1) lookup without iterating all rows for bcrypt verification.
    - ``password_hash``: bcrypt hash of the optional viewer password (nullable —
      ``None`` means no password). When set, scan metadata is withheld until
      ``/unlock`` succeeds (D-15).
    - RLS ``share_links_team_isolation`` policy enforces team scope on all
      authenticated paths. The unauthenticated public path uses the
      ``share_link_by_token()`` SECURITY DEFINER function (migration 006).
    """

    __tablename__ = "share_links"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    token_lookup_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GithubInstallation(Base):
    """GitHub App installation per team (Phase 7.5 D-11).

    Stores the long-lived ``github_installation_id`` (opaque integer, NOT a
    secret) plus account metadata so the dashboard can render
    "Installed on @owner" without an extra GitHub API call. Token material
    is never persisted — workers mint fresh installation tokens via App JWT
    on every scan (D-06).

    RLS posture (mirrors ``ShareLink``): ENABLE + FORCE Row-Level Security
    with a single FOR ALL policy ``team_id = current_setting('app.current_team_id', true)::uuid``.
    Migration 007 owns the policy + grants; this ORM class is the typed
    handle the API + worker use to read/write rows.
    """

    __tablename__ = "github_installations"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    github_installation_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    github_account_login: Mapped[str] = mapped_column(String(255), nullable=False)
    github_account_type: Mapped[str] = mapped_column(String(32), nullable=False)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    installed_by_user_id: Mapped[str] = mapped_column(String(64), nullable=False)


class DCSite(Base):
    """DC Agent site row (Phase 10 DCA-05).

    Stores the SHA-256 lookup hash of the site-token — the plaintext token
    is returned ONCE at creation time and never stored (same pattern as
    share_links.token_lookup_hash, migration 006). RLS team_isolation policy
    (migration 010) scopes all access to the owning team.
    """

    __tablename__ = "dc_sites"

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    token_lookup_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FirewallRulesetSnapshot(Base):
    """Phase 11 D-08/D-10 — parent of every firewall snapshot.

    Snapshot ID is agent-minted (RESEARCH Pattern 2) — backend uses
    ON CONFLICT DO NOTHING on ``snapshot_id`` in the three push route
    handlers (Plan 11-03) so the endpoints are independent and idempotent.

    RLS posture (migration 011): ENABLE + FORCE Row-Level Security with a
    single ``team_id = current_setting('app.current_team_id', true)::uuid``
    policy. Children (``firewall_rules`` / ``firewall_nat_rules`` /
    ``firewall_objects``) enforce team-scope via parent JOIN in their own
    policy — they carry no ``team_id`` column.

    Retention (T-11-02-05): pruned by ``app.tasks.firewall_prune`` at
    ``FIREWALL_SNAPSHOT_TTL_DAYS`` (default 14). FK ``ondelete=CASCADE``
    sweeps children when the parent goes.
    """

    __tablename__ = "firewall_ruleset_snapshots"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("dc_sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    firewall_id: Mapped[str] = mapped_column(Text, nullable=False)
    vendor: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FirewallRuleORM(Base):
    """Phase 11 D-08 hybrid — normalized columns + raw_blob JSONB.

    The ``ORM`` suffix avoids the symbol collision with the un-suffixed
    Pydantic ``FirewallRule`` (``app.schemas.firewall``). Phase 12's
    path-computation reads the normalized columns; UI/audit reads
    ``raw_blob``.
    """

    __tablename__ = "firewall_rules"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("firewall_ruleset_snapshots.snapshot_id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    src_zone: Mapped[str | None] = mapped_column(Text, nullable=True)
    dst_zone: Mapped[str | None] = mapped_column(Text, nullable=True)
    src_cidr: Mapped[str] = mapped_column(Text, nullable=False)
    dst_cidr: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    protocol: Mapped[str | None] = mapped_column(Text, nullable=True)
    ports: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_blob: Mapped[dict] = mapped_column(JSONB, nullable=False)


class FirewallNATRuleORM(Base):
    """Phase 11 D-08 — NAT rule with normalized translation columns.

    Phase 12's NAT_ASYMMETRY classifier (REQ §ASY-02) reads
    ``src_translation`` / ``dst_translation`` / ``interface_in`` /
    ``interface_out`` — locked column names.
    """

    __tablename__ = "firewall_nat_rules"

    nat_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("firewall_ruleset_snapshots.snapshot_id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    src_translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    dst_translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    interface_in: Mapped[str | None] = mapped_column(Text, nullable=True)
    interface_out: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_blob: Mapped[dict] = mapped_column(JSONB, nullable=False)


class FirewallObjectORM(Base):
    """Phase 11 D-09 — host/network/group/service object definitions.

    ``kind`` is application-validated to ``{host, network, group, service}``
    via the Pydantic side (``FirewallObject``). The column is plain Text
    here to avoid an Alembic enum migration; the Pydantic boundary is the
    enforcement point.
    """

    __tablename__ = "firewall_objects"

    object_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("firewall_ruleset_snapshots.snapshot_id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_blob: Mapped[dict] = mapped_column(JSONB, nullable=False)

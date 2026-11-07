"""Current-state domain records. Mutations must follow the documented lock protocol.

Relationships are deliberately read-only: ORM cascades must not silently change
memberships or bypass the explicit future transaction service.
"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint,
    Index, Integer, LargeBinary, String, UniqueConstraint, Uuid, and_, func, select, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("length(btrim(display_name)) > 0", name="ck_users_name"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    display_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    memberships: Mapped[list["Membership"]] = relationship(viewonly=True, foreign_keys="Membership.user_id")


class Hackathon(Base):
    __tablename__ = "hackathons"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="ck_hackathons_name"),
        CheckConstraint("min_team_size >= 1 AND max_team_size >= min_team_size", name="ck_hackathons_sizes"),
        UniqueConstraint("id", "min_team_size", "max_team_size", name="uq_hackathons_sizes"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    min_team_size: Mapped[int] = mapped_column(Integer)
    max_team_size: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    teams: Mapped[list["Team"]] = relationship(viewonly=True)


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("id", "hackathon_id", name="uq_teams_hackathon"),
        ForeignKeyConstraint(
            ["hackathon_id", "min_team_size", "max_team_size"],
            ["hackathons.id", "hackathons.min_team_size", "hackathons.max_team_size"],
            name="fk_teams_hackathon_sizes", onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["id", "leader_user_id"], ["memberships.team_id", "memberships.user_id"],
            name="fk_teams_leader_member", deferrable=True, initially="DEFERRED", use_alter=True,
            ondelete="NO ACTION", onupdate="NO ACTION", match="SIMPLE",
        ),
        CheckConstraint("length(btrim(name)) > 0", name="ck_teams_name"),
        CheckConstraint("min_team_size >= 1 AND max_team_size >= min_team_size", name="ck_teams_sizes"),
        CheckConstraint("version >= 1", name="ck_teams_version"),
        CheckConstraint(
            "(deleted_at IS NULL AND leader_user_id IS NOT NULL) OR "
            "(deleted_at IS NOT NULL AND leader_user_id IS NULL)", name="ck_teams_leader_state",
        ),
        Index("ix_teams_board", "hackathon_id", text("created_at DESC"), text("id DESC"), postgresql_where=text("deleted_at IS NULL")),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    hackathon_id: Mapped[UUID] = mapped_column(Uuid)
    name: Mapped[str] = mapped_column(String(120))
    min_team_size: Mapped[int] = mapped_column(Integer)
    max_team_size: Mapped[int] = mapped_column(Integer)
    leader_user_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", name="fk_teams_creator"))
    version: Mapped[int] = mapped_column(BigInteger, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    memberships: Mapped[list["Membership"]] = relationship(
        viewonly=True, foreign_keys="[Membership.team_id, Membership.hackathon_id]"
    )
    leader: Mapped["Membership | None"] = relationship(
        viewonly=True, primaryjoin=lambda: and_(Team.id == Membership.team_id, Team.leader_user_id == Membership.user_id),
        foreign_keys=lambda: [Team.id, Team.leader_user_id], uselist=False,
    )

    @property
    def readiness(self) -> str:
        if self.deleted_at is not None:
            return "deleted"
        return "ready" if self.member_count >= self.min_team_size else "forming"


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_memberships_team_user"),
        ForeignKeyConstraint(["team_id", "hackathon_id"], ["teams.id", "teams.hackathon_id"], name="fk_memberships_team_hackathon"),
        Index("ix_memberships_roster", "team_id", "joined_at", "user_id"),
        Index("ix_memberships_user", "user_id"),
    )
    hackathon_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", name="fk_memberships_user"), primary_key=True)
    team_id: Mapped[UUID] = mapped_column(Uuid)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    team: Mapped[Team] = relationship(viewonly=True, foreign_keys=[team_id, hackathon_id])
    user: Mapped[User] = relationship(viewonly=True, foreign_keys=[user_id])


# A correlated SQL expression, not a persisted/generated column or Python cache.
Team.member_count = column_property(
    select(func.count(Membership.user_id)).where(Membership.team_id == Team.id).correlate_except(Membership).scalar_subquery()
)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("actor_id", "operation", "key", name="uq_idempotency_scope"),
        CheckConstraint("length(operation) > 0 AND length(key) BETWEEN 1 AND 128 AND key !~ '[^ -~]'", name="ck_idempotency_key"),
        CheckConstraint("octet_length(request_hash) = 32", name="ck_idempotency_hash"),
        CheckConstraint(
            "(state = 'pending' AND http_status IS NULL AND response_body IS NULL AND response_headers IS NULL AND completed_at IS NULL) OR "
            "(state = 'completed' AND http_status IS NOT NULL AND http_status BETWEEN 100 AND 599 AND response_body IS NOT NULL AND response_headers IS NOT NULL AND completed_at IS NOT NULL)",
            name="ck_idempotency_state",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", name="fk_idempotency_actor"))
    hackathon_id: Mapped[UUID] = mapped_column(ForeignKey("hackathons.id", name="fk_idempotency_hackathon"))
    operation: Mapped[str] = mapped_column(String(64))
    key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[bytes] = mapped_column(LargeBinary)
    state: Mapped[str] = mapped_column(String(16), server_default=text("'pending'"))
    http_status: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    response_headers: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actor: Mapped[User] = relationship(viewonly=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        UniqueConstraint("idempotency_record_id", name="uq_audit_operation"),
        UniqueConstraint("team_id", "team_version", name="uq_audit_team_version"),
        ForeignKeyConstraint(["team_id", "hackathon_id"], ["teams.id", "teams.hackathon_id"], name="fk_audit_team_hackathon"),
        CheckConstraint("team_version >= 1 AND length(action) > 0", name="ck_audit_action"),
        Index("ix_audit_team_history", "team_id", "occurred_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    idempotency_record_id: Mapped[UUID] = mapped_column(ForeignKey("idempotency_records.id", name="fk_audit_operation"))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", name="fk_audit_actor"))
    hackathon_id: Mapped[UUID] = mapped_column(Uuid)
    team_id: Mapped[UUID] = mapped_column(Uuid)
    team_version: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(64))
    old_state: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    new_state: Mapped[dict] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    operation_record: Mapped[IdempotencyRecord] = relationship(viewonly=True)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        UniqueConstraint("audit_event_id", name="uq_outbox_audit"),
        CheckConstraint("schema_version >= 1 AND attempt_count >= 0 AND length(event_type) > 0", name="ck_outbox_values"),
        Index("ix_outbox_pending", "occurred_at", "id", postgresql_where=text("published_at IS NULL")),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    audit_event_id: Mapped[UUID] = mapped_column(ForeignKey("audit_events.id", name="fk_outbox_audit"))
    event_type: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    payload: Mapped[dict] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    audit_event: Mapped[AuditEvent] = relationship(viewonly=True)

"""Retained team-scoped join requests; only explicit services mutate them."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class JoinRequest(Base):
    __tablename__ = 'join_requests'
    __table_args__ = (
        ForeignKeyConstraint(['team_id', 'hackathon_id'], ['teams.id', 'teams.hackathon_id'], name='fk_requests_team_hackathon'),
        UniqueConstraint('team_id', 'requester_id', name='uq_requests_team_user'),
        CheckConstraint("(status='pending' AND resolved_at IS NULL AND resolved_by IS NULL) OR "
                        "(status IN ('approved','rejected') AND resolved_at IS NOT NULL AND resolved_by IS NOT NULL)", name='ck_requests_state'),
        CheckConstraint('isfinite(created_at) AND (resolved_at IS NULL OR (isfinite(resolved_at) AND resolved_at>=created_at))', name='ck_requests_time'),
        Index('ix_requests_pending', 'team_id', 'id', postgresql_where=text("status='pending'")),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    hackathon_id: Mapped[UUID] = mapped_column(Uuid)
    team_id: Mapped[UUID] = mapped_column(Uuid)
    requester_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', name='fk_requests_user'))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'pending'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('clock_timestamp()'))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', name='fk_requests_decider'))

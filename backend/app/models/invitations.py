"""Recipient-bound grants; immutable scope and retained terminal history."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Invitation(Base):
    __tablename__ = 'invitations'
    __table_args__ = (
        ForeignKeyConstraint(['team_id','hackathon_id'],['teams.id','teams.hackathon_id'],name='fk_invitations_team_hackathon'),
        CheckConstraint("(status='pending' AND redeemed_at IS NULL) OR (status='redeemed' AND redeemed_at IS NOT NULL)",name='ck_invitations_state'),
        CheckConstraint("isfinite(created_at) AND isfinite(expires_at) AND expires_at>created_at AND expires_at<=created_at+INTERVAL '24 hours' AND (redeemed_at IS NULL OR (isfinite(redeemed_at) AND redeemed_at>=created_at AND redeemed_at<expires_at))",name='ck_invitations_time'),
        Index('ix_invitations_inbox','hackathon_id','recipient_id','id'),
    )
    id: Mapped[UUID] = mapped_column(Uuid,primary_key=True,default=uuid4)
    hackathon_id: Mapped[UUID] = mapped_column(Uuid)
    team_id: Mapped[UUID] = mapped_column(Uuid)
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey('users.id',name='fk_invitations_recipient'))
    issued_by: Mapped[UUID] = mapped_column(ForeignKey('users.id',name='fk_invitations_issuer'))
    status: Mapped[str] = mapped_column(String(16),server_default=text("'pending'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

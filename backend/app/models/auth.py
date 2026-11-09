"""Authentication storage only; no credential/session verification or issuance."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, String, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.domain import User


class AccountCredential(Base):
    __tablename__ = 'account_credentials'
    __table_args__ = (
        UniqueConstraint('username', name='uq_credentials_username'),
        CheckConstraint('length(username) BETWEEN 3 AND 32 AND username COLLATE "C" !~ \'[^a-z0-9_]\'', name='ck_credentials_username'),
        CheckConstraint("length(password_hash) BETWEEN 11 AND 1024 AND password_hash LIKE '$argon2id$%'", name='ck_credentials_hash_format'),
        CheckConstraint('isfinite(created_at) AND isfinite(updated_at) AND updated_at >= created_at', name='ck_credentials_timestamps'),
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('users.id', name='fk_credentials_user'), primary_key=True)
    username: Mapped[str] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship(viewonly=True)
    sessions: Mapped[list['AuthSession']] = relationship(viewonly=True, foreign_keys='AuthSession.user_id')


class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    __table_args__ = (
        CheckConstraint('octet_length(token_hash) = 32', name='ck_sessions_digest'),
        CheckConstraint('octet_length(csrf_token) = 32', name='ck_sessions_csrf'),
        CheckConstraint("expires_at = created_at + interval '8 hours'", name='ck_sessions_expiration'),
        CheckConstraint('isfinite(created_at) AND isfinite(expires_at) AND (revoked_at IS NULL OR isfinite(revoked_at))', name='ck_sessions_finite'),
        CheckConstraint('revoked_at IS NULL OR revoked_at >= created_at', name='ck_sessions_revocation'),
        Index('ix_sessions_user', 'user_id'),
        Index('ix_sessions_expiry', 'expires_at'),
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid,
        ForeignKey('users.id', name='fk_sessions_user'),
        ForeignKey('account_credentials.user_id', name='fk_sessions_credentials'))
    csrf_token: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now() + interval '8 hours'"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship(viewonly=True, foreign_keys=[user_id])
    credential: Mapped[AccountCredential] = relationship(viewonly=True, foreign_keys=[user_id])


class AuthThrottleBucket(Base):
    __tablename__ = 'auth_throttle_buckets'
    __table_args__ = (
        CheckConstraint('length(btrim(scope)) > 0', name='ck_throttle_scope'),
        CheckConstraint('octet_length(key_hash) = 32', name='ck_throttle_key'),
        CheckConstraint('attempts >= 0', name='ck_throttle_attempts'),
        CheckConstraint('isfinite(window_start) AND isfinite(expires_at) AND expires_at > window_start', name='ck_throttle_expiration'),
        Index('ix_throttle_expiry', 'expires_at'),
    )
    scope: Mapped[str] = mapped_column(String(64), primary_key=True)
    key_hash: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    attempts: Mapped[int] = mapped_column(BigInteger, server_default=text('0'))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

"""Opt-in discovery data, independent of membership/authentication state."""
from uuid import UUID
from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, String, Uuid, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ParticipantProfile(Base):
    __tablename__ = 'participant_profiles'
    __table_args__ = (
        CheckConstraint("cardinality(skills) <= 20 AND array_ndims(skills) IS NOT DISTINCT FROM CASE WHEN cardinality(skills)=0 THEN NULL ELSE 1 END AND array_position(skills,NULL) IS NULL AND array_to_string(skills,'') !~ '[^a-z0-9+#.-]' AND array_to_string(skills,',') ~ '^([a-z0-9][a-z0-9+#.-]{0,31}(,[a-z0-9][a-z0-9+#.-]{0,31})*)?$'", name='ck_profiles_skills'),
        CheckConstraint("timezone IS NULL OR (length(timezone) BETWEEN 1 AND 64 AND timezone !~ '[^A-Za-z0-9_+./-]')", name='ck_profiles_timezone'),
        CheckConstraint('NOT discoverable OR timezone IS NOT NULL', name='ck_profiles_discovery'),
        CheckConstraint('version >= 1', name='ck_profiles_version'),
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey('users.id', name='fk_profiles_user'), primary_key=True)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String(32)), server_default=text("'{}'::varchar[]"))
    timezone: Mapped[str | None] = mapped_column(String(64))
    discoverable: Mapped[bool] = mapped_column(Boolean, server_default=text('false'))
    version: Mapped[int] = mapped_column(BigInteger, server_default=text('1'))

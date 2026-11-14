"""Add optional discovery profiles; do not modify existing rows or grants."""
from alembic import op

revision = '0006_profiles'
down_revision = '0005_invitations'
branch_labels = None
depends_on = None


def upgrade():
    if not op.get_context().as_sql:
        from sqlalchemy import text
        if op.get_bind().execute(text("SELECT to_regclass('public.participant_profiles') IS NOT NULL OR to_regtype('public.participant_profiles') IS NOT NULL")).scalar_one():
            raise RuntimeError('Profile objects already exist; no adoption or replacement')
    op.execute('''CREATE TABLE public.participant_profiles (
        user_id UUID NOT NULL,
        skills VARCHAR(32)[] DEFAULT '{}'::varchar[] NOT NULL,
        timezone VARCHAR(64), discoverable BOOLEAN DEFAULT false NOT NULL,
        version BIGINT DEFAULT 1 NOT NULL,
        CONSTRAINT pk_participant_profiles PRIMARY KEY(user_id),
        CONSTRAINT fk_profiles_user FOREIGN KEY(user_id) REFERENCES public.users(id),
        CONSTRAINT ck_profiles_skills CHECK (
            cardinality(skills) <= 20
            AND array_ndims(skills) IS NOT DISTINCT FROM CASE WHEN cardinality(skills)=0 THEN NULL ELSE 1 END
            AND array_position(skills,NULL) IS NULL
            AND array_to_string(skills,'') !~ '[^a-z0-9+#.-]'
            AND array_to_string(skills,',') ~ '^([a-z0-9][a-z0-9+#.-]{0,31}(,[a-z0-9][a-z0-9+#.-]{0,31})*)?$'),
        CONSTRAINT ck_profiles_timezone CHECK (timezone IS NULL OR
            (length(timezone) BETWEEN 1 AND 64 AND timezone !~ '[^A-Za-z0-9_+./-]')),
        CONSTRAINT ck_profiles_discovery CHECK (NOT discoverable OR timezone IS NOT NULL),
        CONSTRAINT ck_profiles_version CHECK (version >= 1)
    )''')


def downgrade():
    raise RuntimeError('Profile removal requires a separate owner-reviewed data retention plan')

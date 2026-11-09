"""Add authentication storage, preserving all existing domain rows and DDL."""
from alembic import op
import sqlalchemy as sa

revision = '0003_auth'
down_revision = '0002_domain'
branch_labels = None
depends_on = None

TABLE_NAMES = ('account_credentials', 'auth_sessions', 'auth_throttle_buckets')

TABLE_DDL = (
    '''CREATE TABLE public.account_credentials (
        user_id UUID NOT NULL,
        username VARCHAR(32) NOT NULL,
        password_hash VARCHAR(1024) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        CONSTRAINT pk_account_credentials PRIMARY KEY (user_id),
        CONSTRAINT uq_credentials_username UNIQUE (username),
        CONSTRAINT fk_credentials_user FOREIGN KEY (user_id) REFERENCES public.users(id),
        CONSTRAINT ck_credentials_username CHECK (length(username) BETWEEN 3 AND 32 AND username COLLATE "C" !~ '[^a-z0-9_]'),
        CONSTRAINT ck_credentials_hash_format CHECK (length(password_hash) BETWEEN 11 AND 1024 AND password_hash LIKE '$argon2id$%'),
        CONSTRAINT ck_credentials_timestamps CHECK (isfinite(created_at) AND isfinite(updated_at) AND updated_at >= created_at)
    )''',
    '''CREATE TABLE public.auth_sessions (
        token_hash BYTEA NOT NULL,
        user_id UUID NOT NULL,
        csrf_token BYTEA NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        expires_at TIMESTAMPTZ DEFAULT (now() + interval '8 hours') NOT NULL,
        revoked_at TIMESTAMPTZ,
        CONSTRAINT pk_auth_sessions PRIMARY KEY (token_hash),
        CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES public.users(id),
        CONSTRAINT fk_sessions_credentials FOREIGN KEY (user_id) REFERENCES public.account_credentials(user_id),
        CONSTRAINT ck_sessions_digest CHECK (octet_length(token_hash) = 32),
        CONSTRAINT ck_sessions_csrf CHECK (octet_length(csrf_token) = 32),
        CONSTRAINT ck_sessions_expiration CHECK (expires_at = created_at + interval '8 hours'),
        CONSTRAINT ck_sessions_finite CHECK (isfinite(created_at) AND isfinite(expires_at) AND (revoked_at IS NULL OR isfinite(revoked_at))),
        CONSTRAINT ck_sessions_revocation CHECK (revoked_at IS NULL OR revoked_at >= created_at)
    )''',
    '''CREATE TABLE public.auth_throttle_buckets (
        scope VARCHAR(64) NOT NULL,
        key_hash BYTEA NOT NULL,
        window_start TIMESTAMPTZ NOT NULL,
        attempts BIGINT DEFAULT 0 NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL,
        CONSTRAINT pk_auth_throttle_buckets PRIMARY KEY (scope,key_hash,window_start),
        CONSTRAINT ck_throttle_scope CHECK (length(btrim(scope)) > 0),
        CONSTRAINT ck_throttle_key CHECK (octet_length(key_hash) = 32),
        CONSTRAINT ck_throttle_attempts CHECK (attempts >= 0),
        CONSTRAINT ck_throttle_expiration CHECK (isfinite(window_start) AND isfinite(expires_at) AND expires_at > window_start)
    )''',
    'CREATE INDEX ix_sessions_user ON public.auth_sessions(user_id)',
    'CREATE INDEX ix_sessions_expiry ON public.auth_sessions(expires_at)',
    'CREATE INDEX ix_throttle_expiry ON public.auth_throttle_buckets(expires_at)',
)

GUARD_DDL = '''CREATE FUNCTION public.merge_guard_auth_row() RETURNS trigger
LANGUAGE plpgsql VOLATILE SECURITY INVOKER
SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    IF TG_TABLE_NAME = 'account_credentials' THEN
        IF (NEW.user_id,NEW.created_at) IS DISTINCT FROM (OLD.user_id,OLD.created_at) THEN
            RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='guard_credentials_identity', MESSAGE='Credential identity is immutable';
        END IF;
    ELSIF TG_TABLE_NAME = 'auth_sessions' THEN
        IF (NEW.token_hash,NEW.user_id,NEW.csrf_token,NEW.created_at,NEW.expires_at)
           IS DISTINCT FROM (OLD.token_hash,OLD.user_id,OLD.csrf_token,OLD.created_at,OLD.expires_at) THEN
            RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='guard_sessions_identity', MESSAGE='Session identity and absolute lifetime are immutable';
        END IF;
        IF OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at THEN
            RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='guard_sessions_revoked', MESSAGE='Session revocation is terminal';
        END IF;
    END IF;
    RETURN NEW;
END;
$$'''


def upgrade():
    if not op.get_context().as_sql:
        conflicts = op.get_bind().execute(sa.text('''
            SELECT c.relname FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname=ANY(:names)
            UNION ALL SELECT t.typname FROM pg_catalog.pg_type t JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace
            WHERE n.nspname='public' AND t.typname=ANY(:names)
            UNION ALL SELECT p.proname FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='public' AND p.proname='merge_guard_auth_row'
        '''), {'names': list(TABLE_NAMES)}).all()
        if conflicts:
            raise RuntimeError('Unexpected authentication schema conflict; stop before changes')
    for statement in TABLE_DDL:
        op.execute(statement)
    op.execute(GUARD_DDL)
    for table in TABLE_NAMES:
        op.execute(f'CREATE TRIGGER tr_{table}_no_truncate BEFORE TRUNCATE ON public.{table} FOR EACH STATEMENT EXECUTE FUNCTION public.merge_deny_truncate()')
    for table in ('account_credentials', 'auth_sessions'):
        op.execute(f'CREATE TRIGGER tr_{table}_guard BEFORE UPDATE ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.merge_guard_auth_row()')


def downgrade():
    raise RuntimeError('Authentication downgrade requires a separate reviewed owner-approved data-retention procedure')

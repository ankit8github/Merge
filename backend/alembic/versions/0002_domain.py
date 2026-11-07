"""Approved domain schema; frozen DDL, independent of future model changes.

Revision ID: 0002_domain
Revises: 0001_baseline
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_domain"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

DOMAIN_TABLES = ("users", "hackathons", "teams", "memberships", "idempotency_records", "audit_events", "outbox_events")

FUNCTION_DDL = (
    """
CREATE FUNCTION public.merge_guard_row() RETURNS trigger
LANGUAGE plpgsql VOLATILE SECURITY INVOKER
SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    IF TG_TABLE_NAME = 'memberships' THEN
        RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'guard_membership_immutable',
            MESSAGE = 'Membership rows cannot be updated; use explicit leave/join transactions';
    ELSIF TG_TABLE_NAME = 'audit_events' THEN
        RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'guard_audit_append_only', MESSAGE = 'Audit records are append only';
    ELSIF TG_TABLE_NAME = 'teams' THEN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'guard_team_soft_delete', MESSAGE = 'Teams must be soft deleted';
        END IF;
        IF (NEW.id, NEW.hackathon_id, NEW.min_team_size, NEW.max_team_size, NEW.created_by, NEW.created_at)
           IS DISTINCT FROM (OLD.id, OLD.hackathon_id, OLD.min_team_size, OLD.max_team_size, OLD.created_by, OLD.created_at) THEN
            RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'guard_team_identity', MESSAGE = 'Team identity and size configuration are immutable';
        END IF;
        IF OLD.deleted_at IS NOT NULL AND NEW IS DISTINCT FROM OLD THEN
            RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'guard_team_tombstone', MESSAGE = 'Deleted teams cannot be changed';
        END IF;
    ELSIF TG_TABLE_NAME = 'idempotency_records' THEN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'guard_idempotency_retention', MESSAGE = 'Idempotency outcomes are retained';
        END IF;
        IF (NEW.id, NEW.actor_id, NEW.hackathon_id, NEW.operation, NEW.key, NEW.request_hash, NEW.created_at)
           IS DISTINCT FROM (OLD.id, OLD.actor_id, OLD.hackathon_id, OLD.operation, OLD.key, OLD.request_hash, OLD.created_at)
           OR (OLD.state = 'completed' AND NEW IS DISTINCT FROM OLD) THEN
            RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'guard_idempotency_immutable', MESSAGE = 'Idempotency scope and completed outcome are immutable';
        END IF;
    ELSIF TG_TABLE_NAME = 'outbox_events' THEN
        IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'guard_outbox_retention', MESSAGE = 'Outbox records are retained';
        END IF;
        IF (NEW.id, NEW.audit_event_id, NEW.event_type, NEW.schema_version, NEW.payload, NEW.occurred_at)
           IS DISTINCT FROM (OLD.id, OLD.audit_event_id, OLD.event_type, OLD.schema_version, OLD.payload, OLD.occurred_at) THEN
            RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'guard_outbox_identity', MESSAGE = 'Outbox event identity and payload are immutable';
        END IF;
    ELSIF NEW.id IS DISTINCT FROM OLD.id THEN
        RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'guard_primary_identity', MESSAGE = 'Primary identity is immutable';
    END IF;
    RETURN NEW;
END;
$$
""",
    """
CREATE FUNCTION public.merge_lock_membership_team() RETURNS trigger
LANGUAGE plpgsql VOLATILE SECURITY INVOKER
SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    target_id uuid;
    tombstone timestamptz;
BEGIN
    IF TG_OP = 'INSERT' THEN target_id := NEW.team_id; ELSE target_id := OLD.team_id; END IF;
    SELECT deleted_at INTO tombstone FROM public.teams WHERE id = target_id FOR NO KEY UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = '23503', CONSTRAINT = 'fk_memberships_team_hackathon', MESSAGE = 'Membership team does not exist';
    END IF;
    IF TG_OP = 'INSERT' AND tombstone IS NOT NULL THEN
        RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'guard_team_deleted', MESSAGE = 'Deleted team cannot accept memberships';
    END IF;
    IF TG_OP = 'INSERT' THEN RETURN NEW; ELSE RETURN OLD; END IF;
END;
$$
""",
    """
CREATE FUNCTION public.merge_validate_team() RETURNS trigger
LANGUAGE plpgsql VOLATILE SECURITY INVOKER
SET search_path = pg_catalog, pg_temp AS $$
DECLARE
    target_id uuid;
    final_team public.teams%ROWTYPE;
    actual_count bigint;
BEGIN
    IF TG_TABLE_NAME = 'teams' THEN target_id := NEW.id;
    ELSIF TG_OP = 'DELETE' THEN target_id := OLD.team_id;
    ELSE target_id := NEW.team_id;
    END IF;
    -- Separate SPI statements: count obtains a fresh snapshot after lock waits.
    -- Always re-read final rows, never validate stale queued NEW/OLD state.
    SELECT * INTO final_team FROM public.teams WHERE id = target_id FOR NO KEY UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = '23503', CONSTRAINT = 'ct_team_exists', MESSAGE = 'Team disappeared during integrity validation';
    END IF;
    SELECT count(*) INTO actual_count FROM public.memberships WHERE team_id = target_id;
    IF final_team.deleted_at IS NOT NULL THEN
        IF actual_count <> 0 OR final_team.leader_user_id IS NOT NULL THEN
            RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'ct_team_deleted_empty', MESSAGE = 'Deleted team must have no members or leader';
        END IF;
    ELSIF actual_count < 1 THEN
        RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'ct_team_nonempty', MESSAGE = 'Live team must have at least one member';
    ELSIF actual_count > final_team.max_team_size THEN
        RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'ct_team_capacity', MESSAGE = 'Team capacity exceeded';
    END IF;
    RETURN NULL;
END;
$$
""",
    """
CREATE FUNCTION public.merge_validate_idempotency() RETURNS trigger
LANGUAGE plpgsql VOLATILE SECURITY INVOKER
SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM public.idempotency_records WHERE id = NEW.id AND state <> 'completed') THEN
        RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'ct_idempotency_completed', MESSAGE = 'Pending idempotency record cannot commit';
    END IF;
    RETURN NULL;
END;
$$
""",
    """
CREATE FUNCTION public.merge_deny_truncate() RETURNS trigger
LANGUAGE plpgsql VOLATILE SECURITY INVOKER
SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    RAISE EXCEPTION USING ERRCODE = '23514', CONSTRAINT = 'guard_domain_truncate', MESSAGE = 'Protected domain tables cannot be truncated';
END;
$$
""",
)


def upgrade() -> None:
    # No IF NOT EXISTS or CREATE OR REPLACE: never absorb an unexpected object.
    if not op.get_context().as_sql:
        connection = op.get_bind()
        conflicts = connection.execute(sa.text("""
            SELECT c.relname FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relname = ANY(:names)
            UNION ALL
            SELECT p.proname FROM pg_catalog.pg_proc p
            JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public' AND p.proname LIKE 'merge\\_%' ESCAPE '\\'
        """), {"names": list(DOMAIN_TABLES)}).scalars().all()
        if conflicts:
            raise RuntimeError("Unexpected domain schema conflict; migration stopped before changes")
    for statement in TABLE_DDL:
        op.execute(statement)
    for statement in FUNCTION_DDL:
        op.execute(statement)
    for table in DOMAIN_TABLES:
        op.execute(f"CREATE TRIGGER tr_{table}_no_truncate BEFORE TRUNCATE ON public.{table} FOR EACH STATEMENT EXECUTE FUNCTION public.merge_deny_truncate()")
    for table in ("users", "hackathons", "teams", "memberships", "idempotency_records", "audit_events", "outbox_events"):
        events = "UPDATE OR DELETE" if table in ("teams", "idempotency_records", "audit_events", "outbox_events") else "UPDATE"
        op.execute(f"CREATE TRIGGER tr_{table}_guard BEFORE {events} ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.merge_guard_row()")
    op.execute("CREATE TRIGGER tr_memberships_lock BEFORE INSERT OR DELETE ON public.memberships FOR EACH ROW EXECUTE FUNCTION public.merge_lock_membership_team()")
    op.execute("CREATE CONSTRAINT TRIGGER ct_teams_final AFTER INSERT OR UPDATE ON public.teams DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.merge_validate_team()")
    op.execute("CREATE CONSTRAINT TRIGGER ct_memberships_final AFTER INSERT OR DELETE ON public.memberships DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.merge_validate_team()")
    op.execute("CREATE CONSTRAINT TRIGGER ct_idempotency_final AFTER INSERT OR UPDATE ON public.idempotency_records DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.merge_validate_idempotency()")


def downgrade() -> None:
    raise RuntimeError("Domain downgrade is destructive and requires a separately reviewed owner-approved procedure")

# Snapshot of reviewed SQLAlchemy DDL; never import current application metadata here.
TABLE_DDL = (
    """
CREATE TABLE public.hackathons (
	id UUID NOT NULL,
	name VARCHAR(120) NOT NULL,
	min_team_size INTEGER NOT NULL,
	max_team_size INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_hackathons PRIMARY KEY (id),
	CONSTRAINT ck_hackathons_name CHECK (length(btrim(name)) > 0),
	CONSTRAINT ck_hackathons_sizes CHECK (min_team_size >= 1 AND max_team_size >= min_team_size),
	CONSTRAINT uq_hackathons_sizes UNIQUE (id, min_team_size, max_team_size)
)
    """,
    """
CREATE TABLE public.users (
	id UUID NOT NULL,
	display_name VARCHAR(80) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_users PRIMARY KEY (id),
	CONSTRAINT ck_users_name CHECK (length(btrim(display_name)) > 0)
)
    """,
    """
CREATE TABLE public.idempotency_records (
	id UUID NOT NULL,
	actor_id UUID NOT NULL,
	hackathon_id UUID NOT NULL,
	operation VARCHAR(64) NOT NULL,
	key VARCHAR(128) NOT NULL,
	request_hash BYTEA NOT NULL,
	state VARCHAR(16) DEFAULT 'pending' NOT NULL,
	http_status INTEGER,
	response_body JSONB,
	response_headers JSONB,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	completed_at TIMESTAMP WITH TIME ZONE,
	CONSTRAINT pk_idempotency_records PRIMARY KEY (id),
	CONSTRAINT uq_idempotency_scope UNIQUE (actor_id, operation, key),
	CONSTRAINT ck_idempotency_key CHECK (length(operation) > 0 AND length(key) BETWEEN 1 AND 128 AND key !~ '[^ -~]'),
	CONSTRAINT ck_idempotency_hash CHECK (octet_length(request_hash) = 32),
	CONSTRAINT ck_idempotency_state CHECK ((state = 'pending' AND http_status IS NULL AND response_body IS NULL AND response_headers IS NULL AND completed_at IS NULL) OR (state = 'completed' AND http_status IS NOT NULL AND http_status BETWEEN 100 AND 599 AND response_body IS NOT NULL AND response_headers IS NOT NULL AND completed_at IS NOT NULL)),
	CONSTRAINT fk_idempotency_actor FOREIGN KEY(actor_id) REFERENCES public.users (id),
	CONSTRAINT fk_idempotency_hackathon FOREIGN KEY(hackathon_id) REFERENCES public.hackathons (id)
)
    """,
    """
CREATE TABLE public.teams (
	id UUID NOT NULL,
	hackathon_id UUID NOT NULL,
	name VARCHAR(120) NOT NULL,
	min_team_size INTEGER NOT NULL,
	max_team_size INTEGER NOT NULL,
	leader_user_id UUID,
	created_by UUID NOT NULL,
	version BIGINT DEFAULT 1 NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	deleted_at TIMESTAMP WITH TIME ZONE,
	CONSTRAINT pk_teams PRIMARY KEY (id),
	CONSTRAINT uq_teams_hackathon UNIQUE (id, hackathon_id),
	CONSTRAINT fk_teams_hackathon_sizes FOREIGN KEY(hackathon_id, min_team_size, max_team_size) REFERENCES public.hackathons (id, min_team_size, max_team_size) ON UPDATE RESTRICT,
	CONSTRAINT ck_teams_name CHECK (length(btrim(name)) > 0),
	CONSTRAINT ck_teams_sizes CHECK (min_team_size >= 1 AND max_team_size >= min_team_size),
	CONSTRAINT ck_teams_version CHECK (version >= 1),
	CONSTRAINT ck_teams_leader_state CHECK ((deleted_at IS NULL AND leader_user_id IS NOT NULL) OR (deleted_at IS NOT NULL AND leader_user_id IS NULL)),
	CONSTRAINT fk_teams_creator FOREIGN KEY(created_by) REFERENCES public.users (id)
)
    """,
    """
CREATE TABLE public.audit_events (
	id UUID NOT NULL,
	idempotency_record_id UUID NOT NULL,
	actor_id UUID NOT NULL,
	hackathon_id UUID NOT NULL,
	team_id UUID NOT NULL,
	team_version BIGINT NOT NULL,
	action VARCHAR(64) NOT NULL,
	old_state JSONB,
	new_state JSONB NOT NULL,
	occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_audit_events PRIMARY KEY (id),
	CONSTRAINT uq_audit_operation UNIQUE (idempotency_record_id),
	CONSTRAINT uq_audit_team_version UNIQUE (team_id, team_version),
	CONSTRAINT fk_audit_team_hackathon FOREIGN KEY(team_id, hackathon_id) REFERENCES public.teams (id, hackathon_id),
	CONSTRAINT ck_audit_action CHECK (team_version >= 1 AND length(action) > 0),
	CONSTRAINT fk_audit_operation FOREIGN KEY(idempotency_record_id) REFERENCES public.idempotency_records (id),
	CONSTRAINT fk_audit_actor FOREIGN KEY(actor_id) REFERENCES public.users (id)
)
    """,
    """
CREATE TABLE public.memberships (
	hackathon_id UUID NOT NULL,
	user_id UUID NOT NULL,
	team_id UUID NOT NULL,
	joined_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_memberships PRIMARY KEY (hackathon_id, user_id),
	CONSTRAINT uq_memberships_team_user UNIQUE (team_id, user_id),
	CONSTRAINT fk_memberships_team_hackathon FOREIGN KEY(team_id, hackathon_id) REFERENCES public.teams (id, hackathon_id),
	CONSTRAINT fk_memberships_user FOREIGN KEY(user_id) REFERENCES public.users (id)
)
    """,
    """
CREATE TABLE public.outbox_events (
	id UUID NOT NULL,
	audit_event_id UUID NOT NULL,
	event_type VARCHAR(64) NOT NULL,
	schema_version INTEGER DEFAULT 1 NOT NULL,
	payload JSONB NOT NULL,
	occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	published_at TIMESTAMP WITH TIME ZONE,
	attempt_count INTEGER DEFAULT 0 NOT NULL,
	CONSTRAINT pk_outbox_events PRIMARY KEY (id),
	CONSTRAINT uq_outbox_audit UNIQUE (audit_event_id),
	CONSTRAINT ck_outbox_values CHECK (schema_version >= 1 AND attempt_count >= 0 AND length(event_type) > 0),
	CONSTRAINT fk_outbox_audit FOREIGN KEY(audit_event_id) REFERENCES public.audit_events (id)
)
    """,
    """
CREATE INDEX ix_teams_board ON public.teams (hackathon_id, created_at DESC, id DESC) WHERE deleted_at IS NULL
    """,
    """
CREATE INDEX ix_audit_team_history ON public.audit_events (team_id, occurred_at, id)
    """,
    """
CREATE INDEX ix_memberships_roster ON public.memberships (team_id, joined_at, user_id)
    """,
    """
CREATE INDEX ix_memberships_user ON public.memberships (user_id)
    """,
    """
CREATE INDEX ix_outbox_pending ON public.outbox_events (occurred_at, id) WHERE published_at IS NULL
    """,
    """
ALTER TABLE public.teams ADD CONSTRAINT fk_teams_leader_member FOREIGN KEY(id, leader_user_id) REFERENCES public.memberships (team_id, user_id) MATCH SIMPLE ON DELETE NO ACTION ON UPDATE NO ACTION DEFERRABLE INITIALLY DEFERRED
    """,
)

"""Add retained join requests. No existing table, data or privilege changes."""
from alembic import op
import sqlalchemy as sa

revision = '0004_admission'
down_revision = '0003_auth'
branch_labels = None
depends_on = None

TABLE_DDL = '''CREATE TABLE public.join_requests (
    id UUID NOT NULL,
    hackathon_id UUID NOT NULL,
    team_id UUID NOT NULL,
    requester_id UUID NOT NULL,
    status VARCHAR(16) DEFAULT 'pending' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT clock_timestamp() NOT NULL,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID,
    CONSTRAINT pk_join_requests PRIMARY KEY (id),
    CONSTRAINT uq_requests_team_user UNIQUE (team_id,requester_id),
    CONSTRAINT fk_requests_team_hackathon FOREIGN KEY (team_id,hackathon_id) REFERENCES public.teams(id,hackathon_id),
    CONSTRAINT fk_requests_user FOREIGN KEY (requester_id) REFERENCES public.users(id),
    CONSTRAINT fk_requests_decider FOREIGN KEY (resolved_by) REFERENCES public.users(id),
    CONSTRAINT ck_requests_state CHECK (
        (status='pending' AND resolved_at IS NULL AND resolved_by IS NULL) OR
        (status IN ('approved','rejected') AND resolved_at IS NOT NULL AND resolved_by IS NOT NULL)),
    CONSTRAINT ck_requests_time CHECK (isfinite(created_at) AND
        (resolved_at IS NULL OR (isfinite(resolved_at) AND resolved_at>=created_at)))
)'''

GUARD_DDL = '''CREATE FUNCTION public.merge_guard_request() RETURNS trigger
LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    IF TG_OP IN ('DELETE','TRUNCATE') THEN
        RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='guard_request_retained', MESSAGE='Requests are retained';
    ELSIF TG_OP='INSERT' THEN
        IF NEW.status <> 'pending' THEN
            RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='guard_request_initial', MESSAGE='Requests start pending';
        END IF;
    ELSE
        IF (NEW.id,NEW.hackathon_id,NEW.team_id,NEW.requester_id,NEW.created_at)
            IS DISTINCT FROM (OLD.id,OLD.hackathon_id,OLD.team_id,OLD.requester_id,OLD.created_at) THEN
            RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='guard_request_identity', MESSAGE='Request identity is immutable';
        END IF;
        IF OLD.status <> 'pending' OR NEW.status NOT IN ('approved','rejected') THEN
            RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='guard_request_terminal', MESSAGE='Request resolution is terminal';
        END IF;
    END IF;
    RETURN NEW;
END;
$$'''

VALIDATE_DDL = '''CREATE FUNCTION public.merge_validate_request_admission() RETURNS trigger
LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    IF NEW.status='approved' AND NOT EXISTS (
        SELECT 1 FROM public.memberships m WHERE m.hackathon_id=NEW.hackathon_id
        AND m.team_id=NEW.team_id AND m.user_id=NEW.requester_id) THEN
        RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='ct_request_admitted', MESSAGE='Approved request requires admission';
    END IF;
    RETURN NULL;
END;
$$'''


def upgrade():
    if not op.get_context().as_sql:
        conflict = op.get_bind().execute(sa.text('''SELECT to_regclass('public.join_requests'),
            to_regtype('public.join_requests'), to_regprocedure('public.merge_guard_request()'),
            to_regprocedure('public.merge_validate_request_admission()')''')).one()
        if any(value is not None for value in conflict):
            raise RuntimeError('Admission objects already exist; no adoption or replacement')
    op.execute(TABLE_DDL)
    op.execute("CREATE INDEX ix_requests_pending ON public.join_requests(team_id,id) WHERE status='pending'")
    op.execute(GUARD_DDL)
    op.execute(VALIDATE_DDL)
    op.execute('''CREATE TRIGGER guard_request_row BEFORE INSERT OR UPDATE OR DELETE ON public.join_requests
        FOR EACH ROW EXECUTE FUNCTION public.merge_guard_request()''')
    op.execute('''CREATE TRIGGER guard_request_truncate BEFORE TRUNCATE ON public.join_requests
        FOR EACH STATEMENT EXECUTE FUNCTION public.merge_guard_request()''')
    op.execute('''CREATE CONSTRAINT TRIGGER ct_request_admitted AFTER INSERT OR UPDATE ON public.join_requests
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.merge_validate_request_admission()''')


def downgrade():
    raise RuntimeError('Retained requests require a separate owner-approved downgrade plan')

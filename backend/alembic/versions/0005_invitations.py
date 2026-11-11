"""Add recipient-bound retained invitations without altering prior data or grants."""
from alembic import op
import sqlalchemy as sa

revision = '0005_invitations'
down_revision = '0004_admission'
branch_labels = None
depends_on = None

TABLE_DDL = '''CREATE TABLE public.invitations (
    id UUID NOT NULL, hackathon_id UUID NOT NULL, team_id UUID NOT NULL,
    recipient_id UUID NOT NULL, issued_by UUID NOT NULL,
    status VARCHAR(16) DEFAULT 'pending' NOT NULL,
    created_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
    redeemed_at TIMESTAMPTZ,
    CONSTRAINT pk_invitations PRIMARY KEY (id),
    CONSTRAINT fk_invitations_team_hackathon FOREIGN KEY (team_id,hackathon_id) REFERENCES public.teams(id,hackathon_id),
    CONSTRAINT fk_invitations_recipient FOREIGN KEY (recipient_id) REFERENCES public.users(id),
    CONSTRAINT fk_invitations_issuer FOREIGN KEY (issued_by) REFERENCES public.users(id),
    CONSTRAINT ck_invitations_state CHECK ((status='pending' AND redeemed_at IS NULL) OR (status='redeemed' AND redeemed_at IS NOT NULL)),
    CONSTRAINT ck_invitations_time CHECK (isfinite(created_at) AND isfinite(expires_at)
        AND expires_at>created_at AND expires_at<=created_at+INTERVAL '24 hours'
        AND (redeemed_at IS NULL OR (isfinite(redeemed_at) AND redeemed_at>=created_at AND redeemed_at<expires_at)))
)'''

GUARD_DDL = '''CREATE FUNCTION public.merge_guard_invitation() RETURNS trigger
LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    IF TG_OP IN ('DELETE','TRUNCATE') THEN
        RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='guard_invitation_retained', MESSAGE='Invitations are retained';
    ELSIF TG_OP='INSERT' THEN
        IF NEW.status <> 'pending' THEN
            RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='guard_invitation_initial', MESSAGE='Invitations start pending';
        END IF;
    ELSE
        IF (NEW.id,NEW.hackathon_id,NEW.team_id,NEW.recipient_id,NEW.issued_by,NEW.created_at,NEW.expires_at)
            IS DISTINCT FROM (OLD.id,OLD.hackathon_id,OLD.team_id,OLD.recipient_id,OLD.issued_by,OLD.created_at,OLD.expires_at) THEN
            RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='guard_invitation_identity', MESSAGE='Invitation identity is immutable';
        END IF;
        IF OLD.status <> 'pending' OR NEW.status <> 'redeemed' THEN
            RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='guard_invitation_terminal', MESSAGE='Redemption is terminal';
        END IF;
    END IF;
    RETURN NEW;
END;
$$'''

VALIDATE_DDL = '''CREATE FUNCTION public.merge_validate_invitation_admission() RETURNS trigger
LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    IF NEW.status='redeemed' AND NOT EXISTS (SELECT 1 FROM public.memberships m
        WHERE m.hackathon_id=NEW.hackathon_id AND m.team_id=NEW.team_id AND m.user_id=NEW.recipient_id) THEN
        RAISE EXCEPTION USING ERRCODE='23514', CONSTRAINT='ct_invitation_admitted', MESSAGE='Redemption requires membership';
    END IF;
    RETURN NULL;
END;
$$'''


def upgrade():
    if not op.get_context().as_sql:
        conflicts = op.get_bind().execute(sa.text('''SELECT to_regclass('public.invitations'),
            to_regtype('public.invitations'),to_regprocedure('public.merge_guard_invitation()'),
            to_regprocedure('public.merge_validate_invitation_admission()')''')).one()
        if any(value is not None for value in conflicts):
            raise RuntimeError('Invitation objects already exist; no adoption or replacement')
    op.execute(TABLE_DDL)
    op.execute('CREATE INDEX ix_invitations_inbox ON public.invitations(hackathon_id,recipient_id,id)')
    op.execute(GUARD_DDL)
    op.execute(VALIDATE_DDL)
    op.execute('''CREATE TRIGGER guard_invitation_row BEFORE INSERT OR UPDATE OR DELETE ON public.invitations
        FOR EACH ROW EXECUTE FUNCTION public.merge_guard_invitation()''')
    op.execute('''CREATE TRIGGER guard_invitation_truncate BEFORE TRUNCATE ON public.invitations
        FOR EACH STATEMENT EXECUTE FUNCTION public.merge_guard_invitation()''')
    op.execute('''CREATE CONSTRAINT TRIGGER ct_invitation_admitted AFTER INSERT OR UPDATE ON public.invitations
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION public.merge_validate_invitation_admission()''')


def downgrade():
    raise RuntimeError('Retained invitations require a separate owner-approved downgrade plan')

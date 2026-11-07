"""Real PostgreSQL integrity tests; UUID fixtures never survive the outer rollback.

SET CONSTRAINTS ALL IMMEDIATE executes the same deferred checks used at commit.
Negative commit tests actually commit and rely on PostgreSQL's atomic rollback.
No TRUNCATE, privileged trigger disabling, object dropping or database reset is
used for cleanup. The TRUNCATE test expects rejection before any data removal.
"""
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, configure_mappers

import app.models
from app.core.config import Settings
from app.db.base import Base
from app.db.session import build_engine
from app.models import Team

pytestmark = pytest.mark.database


@pytest.fixture
def connection():
    engine = build_engine(Settings())
    with engine.connect() as connection:
        assert connection.get_isolation_level() == "READ COMMITTED"
        transaction = connection.begin()
        connection.execute(text("SET LOCAL lock_timeout = '5s'"))
        connection.execute(text("SET LOCAL statement_timeout = '15s'"))
        try:
            yield connection
        finally:
            if transaction.is_active:
                transaction.rollback()
            connection.rollback()
    engine.dispose()


def execute(c, statement, **values):
    return c.execute(text(statement), values)


def seed(c, maximum=3, minimum=2):
    hackathon = uuid4()
    users = [uuid4() for _ in range(4)]
    for user in users:
        execute(c, "INSERT INTO public.users(id,display_name) VALUES (:id,'schema-test')", id=user)
    execute(c, "INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:id,'schema-test',:minimum,:maximum)", id=hackathon, minimum=minimum, maximum=maximum)
    return hackathon, users


def create_team(c, hackathon, founder, maximum=3, minimum=2, membership=True):
    team = uuid4()
    execute(c, """INSERT INTO public.teams(id,hackathon_id,name,min_team_size,max_team_size,leader_user_id,created_by)
        VALUES (:id,:hackathon,'schema-test',:minimum,:maximum,:founder,:founder)""",
        id=team, hackathon=hackathon, minimum=minimum, maximum=maximum, founder=founder)
    if membership:
        join(c, hackathon, team, founder)
    return team


def join(c, hackathon, team, user):
    execute(c, "INSERT INTO public.memberships(hackathon_id,team_id,user_id) VALUES (:hackathon,:team,:user)", hackathon=hackathon, team=team, user=user)


def validate(c):
    execute(c, "SET CONSTRAINTS ALL IMMEDIATE")
    execute(c, "SET CONSTRAINTS ALL DEFERRED")


def rejected(action, state, constraint=None):
    with pytest.raises(IntegrityError) as error:
        action()
    assert error.value.orig.sqlstate == state
    if constraint:
        assert error.value.orig.diag.constraint_name == constraint


def test_founding_membership_and_derived_count(connection):
    c = connection
    h, u = seed(c)
    t = create_team(c, h, u[0])
    validate(c)
    configure_mappers()
    with Session(bind=c, join_transaction_mode="create_savepoint") as session:
        team = session.get(Team, t)
        assert team.member_count == 1 and team.readiness == "forming"
        assert team.leader.user_id == u[0]
        assert len(team.memberships) == 1
    assert "member_count" not in Team.__table__.columns
    assert "readiness" not in Team.__table__.columns


def test_founderless_team_actual_commit_fails(connection):
    h, u = seed(connection)
    create_team(connection, h, u[0], membership=False)
    # Both leader FK and nonempty validation are deferred; either may report first.
    with pytest.raises(IntegrityError) as error:
        connection.commit()
    assert error.value.orig.sqlstate in ("23503", "23514")


def test_cross_team_duplicate_membership(connection):
    h, u = seed(connection)
    first = create_team(connection, h, u[0])
    second = create_team(connection, h, u[1])
    join(connection, h, first, u[2])
    rejected(lambda: join(connection, h, second, u[2]), "23505", "pk_memberships")


def test_invalid_leader_assignment(connection):
    h, u = seed(connection)
    t = create_team(connection, h, u[0])
    execute(connection, "UPDATE public.teams SET leader_user_id=:user WHERE id=:team", user=u[1], team=t)
    rejected(lambda: validate(connection), "23503", "fk_teams_leader_member")


def test_direct_overcapacity_actual_commit_fails(connection):
    h, u = seed(connection, maximum=2)
    t = create_team(connection, h, u[0], maximum=2)
    join(connection, h, t, u[1])
    join(connection, h, t, u[2])
    rejected(connection.commit, "23514", "ct_team_capacity")


def test_membership_move_is_rejected(connection):
    h, u = seed(connection)
    first = create_team(connection, h, u[0])
    second = create_team(connection, h, u[1])
    rejected(lambda: execute(connection, "UPDATE public.memberships SET team_id=:other WHERE team_id=:team", other=second, team=first), "23514", "guard_membership_immutable")


def test_soft_delete_last_member_uses_final_state(connection):
    h, u = seed(connection)
    t = create_team(connection, h, u[0])
    execute(connection, "DELETE FROM public.memberships WHERE team_id=:team", team=t)
    execute(connection, "UPDATE public.teams SET leader_user_id=NULL,deleted_at=now() WHERE id=:team", team=t)
    validate(connection)
    assert execute(connection, "SELECT count(*) FROM public.memberships WHERE team_id=:team", team=t).scalar_one() == 0
    rejected(lambda: join(connection, h, t, u[1]), "23514", "guard_team_deleted")


def test_soft_deleted_team_cannot_retain_members(connection):
    h, u = seed(connection)
    t = create_team(connection, h, u[0])
    execute(connection, "UPDATE public.teams SET leader_user_id=NULL,deleted_at=now() WHERE id=:team", team=t)
    rejected(lambda: validate(connection), "23514", "ct_team_deleted_empty")


def test_soft_deleted_team_cannot_be_resurrected(connection):
    h, u = seed(connection)
    t = create_team(connection, h, u[0])
    execute(connection, "DELETE FROM public.memberships WHERE team_id=:team", team=t)
    execute(connection, "UPDATE public.teams SET leader_user_id=NULL,deleted_at=now() WHERE id=:team", team=t)
    validate(connection)
    rejected(lambda: execute(connection, "UPDATE public.teams SET leader_user_id=:user,deleted_at=NULL WHERE id=:team", user=u[0], team=t), "23514", "guard_team_tombstone")


@pytest.mark.parametrize("table", ["users", "hackathons", "teams", "memberships", "idempotency_records", "audit_events", "outbox_events"])
def test_truncate_rejected(connection, table):
    assert execute(connection, "SELECT count(*) FROM pg_trigger WHERE tgname=:name AND tgenabled='O' AND NOT tgisinternal", name=f"tr_{table}_no_truncate").scalar_one() == 1
    # CASCADE would include only the known domain graph; the first statement
    # trigger raises before PostgreSQL can remove any rows. Outer tx rolls back.
    rejected(lambda: execute(connection, f"TRUNCATE TABLE public.{table} CASCADE"), "23514", "guard_domain_truncate")


def test_multiple_changes_and_successor_validate_final_rows(connection):
    h, u = seed(connection, maximum=2)
    t = create_team(connection, h, u[0], maximum=2)
    join(connection, h, t, u[1])
    join(connection, h, t, u[2])  # Temporary overflow, never visible as committed state.
    execute(connection, "DELETE FROM public.memberships WHERE team_id=:team AND user_id=:user", team=t, user=u[0])
    execute(connection, "UPDATE public.teams SET leader_user_id=:user WHERE id=:team", team=t, user=u[1])
    validate(connection)
    assert execute(connection, "SELECT count(*) FROM public.memberships WHERE team_id=:team", team=t).scalar_one() == 2


def test_cross_hackathon_reference_fails(connection):
    h, u = seed(connection)
    other, _ = seed(connection)
    t = create_team(connection, h, u[0])
    rejected(lambda: join(connection, other, t, u[1]), "23503", "fk_memberships_team_hackathon")


def test_frozen_size_configuration(connection):
    h, u = seed(connection)
    create_team(connection, h, u[0])
    rejected(lambda: execute(connection, "UPDATE public.hackathons SET max_team_size=4 WHERE id=:id", id=h), "23503", "fk_teams_hackathon_sizes")


@pytest.mark.parametrize("column,value", [("id", "gen_random_uuid()"), ("min_team_size", "1")])
def test_team_identity_is_immutable(connection, column, value):
    h, u = seed(connection)
    t = create_team(connection, h, u[0])
    rejected(lambda: execute(connection, f"UPDATE public.teams SET {column}={value} WHERE id=:id", id=t), "23514", "guard_team_identity")


def test_physical_team_delete_rejected(connection):
    h, u = seed(connection)
    t = create_team(connection, h, u[0])
    rejected(lambda: execute(connection, "DELETE FROM public.teams WHERE id=:id", id=t), "23514", "guard_team_soft_delete")


def test_pending_idempotency_cannot_commit(connection):
    h, u = seed(connection)
    execute(connection, "INSERT INTO public.idempotency_records(id,actor_id,hackathon_id,operation,key,request_hash) VALUES (:id,:user,:hackathon,'test.v1','key',:fingerprint)", id=uuid4(), user=u[0], hackathon=h, fingerprint=b'x'*32)
    rejected(lambda: validate(connection), "23514", "ct_idempotency_completed")


def test_completed_idempotency_final_state_and_immutability(connection):
    h, u = seed(connection)
    record = uuid4()
    execute(connection, "INSERT INTO public.idempotency_records(id,actor_id,hackathon_id,operation,key,request_hash) VALUES (:id,:user,:hackathon,'test.v1','key',:fingerprint)", id=record, user=u[0], hackathon=h, fingerprint=b'x'*32)
    execute(connection, "UPDATE public.idempotency_records SET state='completed',http_status=409,response_body='{}',response_headers='{}',completed_at=now() WHERE id=:id", id=record)
    validate(connection)
    rejected(lambda: execute(connection, "UPDATE public.idempotency_records SET http_status=200 WHERE id=:id", id=record), "23514", "guard_idempotency_immutable")


def test_safe_function_resolution(connection):
    h, u = seed(connection)
    execute(connection, "SET LOCAL search_path = pg_catalog")
    create_team(connection, h, u[0])
    validate(connection)
    functions = execute(connection, "SELECT provolatile,prosecdef,proconfig FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'merge_%'").all()
    assert len(functions) == 5
    assert all(volatility == 'v' and not security_definer and config == ['search_path=pg_catalog, pg_temp'] for volatility, security_definer, config in functions)


def test_orm_schema_resolution_is_not_caller_search_path(connection):
    h, u = seed(connection)
    t = create_team(connection, h, u[0])
    execute(connection, "SET LOCAL search_path = pg_catalog")
    with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
        team = session.scalar(select(Team).where(Team.id == t))
        assert team.member_count == 1
    validate(connection)


def test_same_user_can_join_different_hackathons(connection):
    h, u = seed(connection)
    other, _ = seed(connection)
    create_team(connection, h, u[0])
    create_team(connection, other, u[0])
    validate(connection)


def test_last_departure_without_soft_delete_fails(connection):
    h, u = seed(connection)
    t = create_team(connection, h, u[0])
    execute(connection, "DELETE FROM public.memberships WHERE team_id=:team", team=t)
    with pytest.raises(IntegrityError) as error:
        validate(connection)
    assert error.value.orig.sqlstate in ('23503', '23514')


def test_transactional_audit_outbox_schema_only(connection):
    h, u = seed(connection)
    t = create_team(connection, h, u[0])
    operation, audit, event = uuid4(), uuid4(), uuid4()
    execute(connection, """INSERT INTO public.idempotency_records
        (id,actor_id,hackathon_id,operation,key,request_hash,state,http_status,response_body,response_headers,completed_at)
        VALUES (:id,:user,:hackathon,'test.v1','key',:fingerprint,'completed',201,'{}','{}',now())""",
        id=operation, user=u[0], hackathon=h, fingerprint=b'x'*32)
    execute(connection, """INSERT INTO public.audit_events
        (id,idempotency_record_id,actor_id,hackathon_id,team_id,team_version,action,new_state)
        VALUES (:id,:operation,:user,:hackathon,:team,1,'test.created','{}')""",
        id=audit, operation=operation, user=u[0], hackathon=h, team=t)
    execute(connection, "INSERT INTO public.outbox_events(id,audit_event_id,event_type,payload) VALUES (:id,:audit,'test.changed','{}')", id=event, audit=audit)
    execute(connection, "UPDATE public.outbox_events SET attempt_count=1 WHERE id=:id", id=event)
    validate(connection)
    rejected(lambda: execute(connection, "UPDATE public.audit_events SET action='changed' WHERE id=:id", id=audit), "23514", "guard_audit_append_only")


def test_migration_metadata_consistency(connection):
    assert execute(connection, "SELECT version_num FROM public.alembic_version").scalar_one() == "0002_domain"
    context = MigrationContext.configure(connection, opts={"include_schemas": True, "compare_type": True, "compare_server_default": True})
    assert compare_metadata(context, Base.metadata) == []
    fk = next(fk for fk in inspect(connection).get_foreign_keys('teams', schema='public') if fk['name'] == 'fk_teams_leader_member')
    assert fk['options']['deferrable'] is True and fk['options']['initially'] == 'DEFERRED'


def test_migration_upgrade_repeat():
    backend = Path(__file__).resolve().parents[1]
    for command in [('upgrade','head'), ('upgrade','head'), ('current',)]:
        result = subprocess.run([sys.executable,'-m','alembic',*command], cwd=backend, capture_output=True, text=True)
        # Do not emit captured driver output, which could contain configuration.
        assert result.returncode == 0, 'Migration command failed; inspect locally without logging credentials'
        if command == ('current',):
            assert '0002_domain (head)' in result.stdout

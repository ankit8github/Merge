"""Test-only SQL fixtures and bounded schedules; not application service logic."""
from dataclasses import dataclass
from queue import Queue
import re
from threading import Barrier, Event, Thread
from time import monotonic
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_support.database import test_connection


def sql(connection, statement, **values):
    return connection.execute(text(statement), values)


@dataclass(frozen=True)
class Outcome:
    status: str
    state: str = ''
    constraint: str = ''


def database_error(error):
    state = getattr(error.orig, 'sqlstate', None)
    constraint = getattr(getattr(error.orig, 'diag', None), 'constraint_name', None)
    return Outcome('rejected', state if isinstance(state, str) and re.fullmatch(r'[0-9A-Z]{5}', state) else 'UNKNOWN',
                   constraint if isinstance(constraint, str) and re.fullmatch(r'[a-z_]{1,80}', constraint) else '')


def wait(event):
    if not event.wait(8):
        raise AssertionError('Synchronization deadline exceeded')


def workers(actions):
    """Daemon workers, bounded joins; SQL has separate server-side deadlines."""
    results = Queue()

    def run(index, action):
        try:
            results.put((index, action()))
        except Exception:
            # Do not retain raw exception objects in the result/report channel.
            results.put((index, Outcome('infrastructure-error')))

    threads = [Thread(target=run, args=(i, action), daemon=True) for i, action in enumerate(actions)]
    for thread in threads:
        thread.start()
    deadline = monotonic() + 30
    for thread in threads:
        thread.join(max(0, deadline - monotonic()))
    if any(thread.is_alive() for thread in threads):
        raise AssertionError('Worker deadline exceeded; stop this run')
    ordered = [None] * len(threads)
    while not results.empty():
        index, outcome = results.get_nowait()
        ordered[index] = outcome
    assert all(isinstance(result, Outcome) for result in ordered), 'Missing worker result'
    print('outcomes:', ordered, flush=True)
    assert all(result.status != 'infrastructure-error' for result in ordered), 'Worker infrastructure failure'
    return ordered


class RaceDatabase:
    def __init__(self, settings):
        self.settings = settings
        self.hackathons = []

    def connection(self):
        return test_connection(self.settings)

    def transaction(self, action, rollback=False):
        try:
            with self.connection() as c:
                action(c)
                if rollback:
                    c.rollback()
                    print('transaction outcome: rolled-back', flush=True)
                    return Outcome('rolled-back')
                c.commit()
                print('transaction outcome: committed', flush=True)
                return Outcome('committed')
        except DBAPIError as error:
            outcome = database_error(error)
            print('transaction outcome:', outcome, flush=True)
            return outcome

    def seed(self, maximum=2, teams=1, members=1, hackathon=None):
        h = hackathon or uuid4()
        users = [uuid4() for _ in range(16)]
        team_ids = [uuid4() for _ in range(teams)]
        # Track before writes, so invariant inspection also runs after seed failure.
        if h not in self.hackathons:
            self.hackathons.append(h)
        with self.connection() as c:
            if hackathon is None:
                sql(c, "INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:id,'race-test',1,:maximum)", id=h, maximum=maximum)
            for user in users:
                sql(c, "INSERT INTO public.users(id,display_name) VALUES (:id,'race-test')", id=user)
            for index, team in enumerate(team_ids):
                founder = users[index * members]
                sql(c, """INSERT INTO public.teams(id,hackathon_id,name,min_team_size,max_team_size,leader_user_id,created_by)
                    VALUES (:id,:h,'race-test',1,:maximum,:u,:u)""", id=team, h=h, maximum=maximum, u=founder)
                for user in users[index * members:(index + 1) * members]:
                    self.join(c, h, team, user)
            c.commit()
        return h, users, team_ids

    @staticmethod
    def join(c, h, team, user):
        sql(c, 'INSERT INTO public.memberships(hackathon_id,team_id,user_id) VALUES (:h,:t,:u)', h=h, t=team, u=user)

    @staticmethod
    def lock(c, team):
        sql(c, 'SELECT id FROM public.teams WHERE id=:t FOR NO KEY UPDATE', t=team).one()

    @staticmethod
    def depart(c, h, team, user):
        # Explicit team-first schedule for this test, not a production service.
        RaceDatabase.lock(c, team)
        sql(c, 'DELETE FROM public.memberships WHERE hackathon_id=:h AND team_id=:t AND user_id=:u', h=h, t=team, u=user)
        leader = sql(c, 'SELECT leader_user_id FROM public.teams WHERE id=:t', t=team).scalar_one()
        remaining = sql(c, 'SELECT user_id FROM public.memberships WHERE team_id=:t ORDER BY joined_at,user_id', t=team).scalars().all()
        if not remaining:
            sql(c, 'UPDATE public.teams SET leader_user_id=NULL,deleted_at=now() WHERE id=:t', t=team)
        elif leader not in remaining:
            sql(c, 'UPDATE public.teams SET leader_user_id=:u WHERE id=:t', u=remaining[0], t=team)

    def roster(self, team):
        with self.connection() as c:
            return set(sql(c, 'SELECT user_id FROM public.memberships WHERE team_id=:t', t=team).scalars())

    def team(self, team):
        with self.connection() as c:
            return sql(c, 'SELECT leader_user_id,deleted_at FROM public.teams WHERE id=:t', t=team).one()

    def check_invariants(self):
        with self.connection() as c:
            sql(c, 'SET TRANSACTION READ ONLY')
            for h in self.hackathons:
                rows = sql(c, '''SELECT t.id,t.deleted_at,t.leader_user_id,t.max_team_size,
                    count(m.user_id),bool_or(m.user_id=t.leader_user_id),
                    bool_and(m.hackathon_id=t.hackathon_id),
                    t.min_team_size=h.min_team_size AND t.max_team_size=h.max_team_size
                    FROM public.teams t JOIN public.hackathons h ON h.id=t.hackathon_id
                    LEFT JOIN public.memberships m ON m.team_id=t.id
                    WHERE t.hackathon_id=:h GROUP BY t.id,h.id''', h=h).all()
                for _, deleted, leader, maximum, count, leader_present, consistent, frozen in rows:
                    assert frozen, 'Frozen sizes violated'
                    if deleted is None:
                        assert 1 <= count <= maximum and leader is not None and leader_present, 'Live-team invariant violated'
                        assert consistent, 'Membership hackathon mismatch'
                    else:
                        assert count == 0 and leader is None, 'Deleted-team invariant violated'
                assert not sql(c, '''SELECT user_id FROM public.memberships
                    WHERE hackathon_id=:h GROUP BY user_id HAVING count(*)>1''', h=h).all(), 'Duplicate assignment'
                assert not sql(c, '''SELECT m.user_id FROM public.memberships m
                    LEFT JOIN public.teams t ON t.id=m.team_id AND t.hackathon_id=m.hackathon_id
                    WHERE m.hackathon_id=:h AND t.id IS NULL''', h=h).all(), 'Orphan membership'
        print('fresh committed invariants: verified', flush=True)

    def ordered_pair(self, first, second):
        """Hold first transaction until pg_blocking_pids proves second is waiting."""
        held, release = Event(), Event()
        identities = Queue()

        def first_action(c):
            first(c)
            identities.put(('first', sql(c, 'SELECT pg_backend_pid()').scalar_one()))
            held.set()
            wait(release)

        def second_action(c):
            wait(held)
            identities.put(('second', sql(c, 'SELECT pg_backend_pid()').scalar_one()))
            second(c)

        def observe():
            try:
                pids = dict(identities.get(timeout=8) for _ in range(2))
                deadline = monotonic() + 3
                with self.connection() as observer:
                    while monotonic() < deadline:
                        blockers = sql(observer, 'SELECT pg_blocking_pids(:pid)', pid=pids['second']).scalar_one()
                        if pids['first'] in blockers:
                            print('server-confirmed lock wait: observed', flush=True)
                            return Outcome('lock-observed')
                        Event().wait(0.01)
                raise AssertionError('Expected server lock wait not observed')
            finally:
                release.set()

        results = workers([lambda: self.transaction(first_action),
                           lambda: self.transaction(second_action), observe])
        assert results[2] == Outcome('lock-observed'), 'Lock observation infrastructure failed'
        return results[:2]


def simultaneous(db, actions):
    barrier = Barrier(len(actions), timeout=8)

    def operation(action):
        def body(c):
            barrier.wait()
            action(c)
        return db.transaction(body)
    return workers([lambda action=action: operation(action) for action in actions])

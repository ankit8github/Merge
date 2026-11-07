"""Real PostgreSQL direct-SQL tests. Owner execution required; no API claims."""
from threading import Barrier, Event

import pytest
from test_support.races import Outcome, simultaneous, sql, wait, workers


def test_competing_final_seat_joins(db):
    h, users, teams = db.seed(maximum=2)
    team = teams[0]
    outcomes = simultaneous(db, [lambda c, u=u: db.join(c, h, team, u) for u in users[1:9]])
    assert outcomes.count(Outcome('committed')) == 1
    assert outcomes.count(Outcome('rejected', '23514', 'ct_team_capacity')) == 7
    roster = db.roster(team)
    assert len(roster) == 2 and users[0] in roster


def test_same_user_different_teams_one_hackathon(db):
    h, users, teams = db.seed(teams=2)
    user = users[2]
    outcomes = simultaneous(db, [lambda c, t=t: db.join(c, h, t, user) for t in teams])
    assert outcomes.count(Outcome('committed')) == 1
    assert outcomes.count(Outcome('rejected', '23505', 'pk_memberships')) == 1
    assert sum(user in db.roster(team) for team in teams) == 1


def test_same_user_different_hackathons(db):
    h, users, first = db.seed()
    other, _, second = db.seed()
    user = users[2]
    outcomes = simultaneous(db, [lambda c: db.join(c, h, first[0], user),
                                  lambda c: db.join(c, other, second[0], user)])
    assert outcomes == [Outcome('committed')] * 2
    assert user in db.roster(first[0]) and user in db.roster(second[0])


def test_lock_wait_snapshot_freshness(db):
    h, users, teams = db.seed()
    team = teams[0]
    outcomes = db.ordered_pair(lambda c: db.join(c, h, team, users[1]),
                               lambda c: db.join(c, h, team, users[2]))
    assert outcomes == [Outcome('committed'), Outcome('rejected', '23514', 'ct_team_capacity')]
    assert db.roster(team) == {users[0], users[1]}


def test_rolled_back_admission_consumes_no_capacity(db):
    h, users, teams = db.seed()
    team = teams[0]
    assert db.transaction(lambda c: db.join(c, h, team, users[1]), rollback=True) == Outcome('rolled-back')
    assert db.roster(team) == {users[0]}
    assert db.transaction(lambda c: db.join(c, h, team, users[2])) == Outcome('committed')
    assert db.roster(team) == {users[0], users[2]}


def test_direct_sql_over_capacity_rejection(db):
    h, users, teams = db.seed()
    team = teams[0]

    def overflow(c):
        db.join(c, h, team, users[1])
        db.join(c, h, team, users[2])

    outcome = db.transaction(overflow)
    print('direct overflow outcome:', outcome)
    assert outcome == Outcome('rejected', '23514', 'ct_team_capacity')
    assert db.roster(team) == {users[0]}
    assert db.transaction(lambda c: db.join(c, h, team, users[3])) == Outcome('committed')
    assert db.roster(team) == {users[0], users[3]}


@pytest.mark.parametrize('leader_first', [True, False])
def test_leader_departure_versus_successor_departure(db, leader_first):
    h, users, teams = db.seed(maximum=3, members=3)
    team = teams[0]
    # All joined_at values share the seed transaction timestamp; UUID is tie-break.
    successor, survivor = sorted(users[1:3])
    departing = [users[0], successor] if leader_first else [successor, users[0]]
    outcomes = db.ordered_pair(lambda c: db.depart(c, h, team, departing[0]),
                               lambda c: db.depart(c, h, team, departing[1]))
    assert outcomes == [Outcome('committed')] * 2
    assert db.roster(team) == {survivor}
    assert db.team(team) == (survivor, None)


@pytest.mark.parametrize('departure_first', [True, False])
def test_last_member_departure_versus_join(db, departure_first):
    h, users, teams = db.seed()
    team = teams[0]
    departure = lambda c: db.depart(c, h, team, users[0])
    admission = lambda c: db.join(c, h, team, users[1])
    if departure_first:
        outcomes = db.ordered_pair(departure, admission)
        assert outcomes == [Outcome('committed'), Outcome('rejected', '23514', 'guard_team_deleted')]
        assert db.roster(team) == set()
        leader, deleted = db.team(team)
        assert leader is None and deleted is not None
    else:
        outcomes = db.ordered_pair(admission, departure)
        assert outcomes == [Outcome('committed')] * 2
        assert db.roster(team) == {users[1]}
        assert db.team(team) == (users[1], None)


def test_invalid_leader_reference_rejected_at_commit(db):
    _, users, teams = db.seed()
    team = teams[0]
    outcome = db.transaction(lambda c: sql(c, 'UPDATE public.teams SET leader_user_id=:u WHERE id=:t', u=users[1], t=team))
    print('invalid leader outcome:', outcome)
    assert outcome == Outcome('rejected', '23503', 'fk_teams_leader_member')
    assert db.team(team) == (users[0], None)
    assert db.roster(team) == {users[0]}


def test_deferred_validator_uses_final_rows(db):
    h, users, teams = db.seed()
    team = teams[0]

    def changes(c):
        db.join(c, h, team, users[1])
        db.join(c, h, team, users[2])  # Temporarily over capacity.
        sql(c, 'UPDATE public.teams SET leader_user_id=:u WHERE id=:t', u=users[3], t=team)  # Temporarily invalid leader.
        sql(c, 'DELETE FROM public.memberships WHERE team_id=:t AND user_id=:u', t=team, u=users[0])
        sql(c, 'UPDATE public.teams SET leader_user_id=:u WHERE id=:t', u=users[2], t=team)

    assert db.transaction(changes) == Outcome('committed')
    assert db.roster(team) == {users[1], users[2]}
    assert db.team(team) == (users[2], None)


def test_transaction_rollback_restores_all_mutations(db):
    h, users, teams = db.seed(maximum=3, members=2)
    team = teams[0]

    def changes(c):
        db.join(c, h, team, users[2])
        db.depart(c, h, team, users[0])

    assert db.transaction(changes, rollback=True) == Outcome('rolled-back')
    assert db.roster(team) == {users[0], users[1]}
    assert db.team(team) == (users[0], None)


def test_bounded_lock_timeout_rolls_back_admission(db):
    h, users, teams = db.seed()
    team = teams[0]
    held, release = Event(), Event()

    def holder(c):
        db.lock(c, team)
        held.set()
        wait(release)

    def contender():
        try:
            def admission(c):
                wait(held)
                sql(c, "SET LOCAL lock_timeout='250ms'")
                db.join(c, h, team, users[1])
            return db.transaction(admission)
        finally:
            release.set()

    outcomes = workers([lambda: db.transaction(holder), contender])
    assert outcomes == [Outcome('committed'), Outcome('rejected', '55P03')]
    assert db.roster(team) == {users[0]}


def test_deadlock_victim_has_no_partial_membership(db):
    h, users, teams = db.seed(teams=2)
    barrier = Barrier(2, timeout=8)

    def operation(index):
        def changes(c):
            db.join(c, h, teams[index], users[index + 2])
            barrier.wait()  # Both transactions now own their first team lock.
            db.lock(c, teams[1 - index])
        return db.transaction(changes)

    outcomes = workers([lambda: operation(0), lambda: operation(1)])
    assert outcomes.count(Outcome('committed')) == 1
    assert outcomes.count(Outcome('rejected', '40P01')) == 1
    for index, outcome in enumerate(outcomes):
        expected = {users[index]}
        if outcome.status == 'committed':
            expected.add(users[index + 2])
        assert db.roster(teams[index]) == expected

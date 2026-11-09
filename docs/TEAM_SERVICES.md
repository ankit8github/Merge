# Internal team services — M-007A

Owner verified the expanded M-007A-R1 suite: **48 service tests passed in 37.23
seconds** against guarded merge_test, with three repetitions requested. This
includes real AUTOCOMMIT rejection, zero-write and rollback regressions as well as
the existing service races and fresh committed-state checks. This is owner-executed
evidence, not a PostgreSQL rerun by Codex. The earlier 42-pass result is retained
in PROGRESS.md as pre-R1 history. Final review found no remaining blocker within
the supported driver contract. No HTTP routes, authentication,
invitation/approval/departure services, idempotency/audit/outbox writers or schema
changes are included. Actor IDs must come from a trusted internal caller; they
are checked for existence, not authenticated or authorized by these services.

## Interfaces and ownership

```python
service = TeamService(engine)
service.create_team(hackathon_id=hackathon_id, actor_id=user_id, name="Team")
service.join_team(hackathon_id=hackathon_id, team_id=team_id, actor_id=user_id)
```

The constructor accepts a SQLAlchemy Engine, never a Session or caller Connection.
The supported driver is synchronous postgresql+psycopg. Other/missing/ambiguous
driver configuration is rejected with transaction_configuration.
Each call acquires a connection, requires PostgreSQL READ COMMITTED with no active
caller transaction, begins one owned transaction, and commits before returning an
immutable TeamResult(team_id, hackathon_id, user_id, member_count). Counts are row
counts inside the locked transaction; concurrent changes after commit may make a
returned count stale. No persistent counter/readiness field is used. The Engine
and credentials remain caller-owned; the service does not load Settings or dotenv.
Statements are public-qualified and parameterized. Local lock/statement deadlines
are 5s/15s. There are no external calls inside the transaction.

### AUTOCOMMIT boundary — M-007A-R1

Installed source inspected without connecting: SQLAlchemy 2.1.8, psycopg 3.3.8.
SQLAlchemy documents that get_isolation_level() reports actual SQL isolation and
never reports the independent DBAPI AUTOCOMMIT mode. Its Connection.connection
API exposes a pool proxy; the documented dbapi_connection attribute accesses the
underlying driver connection. psycopg.Connection.autocommit is its actual bool
state; SQLAlchemy's psycopg isolation setter changes that property for AUTOCOMMIT.

The service first requires the supported synchronous PostgreSQL psycopg dialect,
then reads `c.connection.dbapi_connection.autocommit` and requires **is False**.
True, missing/unreadable properties, None, numeric or string substitutes are
rejected. Only then can it check actual READ COMMITTED; active caller transactions
are also rejected. The guard does not set autocommit, apply execution_options,
change Engine configuration, rollback caller work or guess a default. It never
normalizes an unsafe Engine silently.

This check precedes every service SQL statement, including SET LOCAL and the
isolation metadata query, and precedes begin()/domain operation execution. Engine
initialization and the test Engine's identity event may perform metadata-only
queries before the service guard; no service/domain statements are issued there.
Caller-installed Engine event listeners remain trusted code and must not perform
domain writes or change connection modes behind the service. A shared DBAPI
connection must not be modified concurrently by external code.

Creation locks hackathon FOR SHARE, then actor FOR NO KEY UPDATE. Under these locks
it checks existing hackathon assignment, copies frozen min/max configuration and
inserts the new team plus founder membership with founder as leader/creator. The
new team belongs exclusively to this transaction; no preexisting row lock is needed.

Joining locks hackathon FOR SHARE, actor FOR NO KEY UPDATE, then the exact team in
that hackathon FOR NO KEY UPDATE. It rejects missing/deleted teams, any existing
assignment in that hackathon (including repeat joins), and a full roster using a
separate fresh COUNT query after the team lock. It inserts membership and derives
the resulting count. No pre-lock cached eligibility/count is trusted. Different
hackathons are allowed; the shared user row conservatively serializes that user's
operations even across hackathons. FK KEY SHARE locks are compatible with the
chosen NO KEY UPDATE locks. Constraints remain the final authority against SQL
writers not following this service protocol.

## Dependency check and limits

Inspection of 0002 showed no reverse dependency requiring transactional-support
rows for a team/membership mutation. Audit requires an idempotency row when audit
is written; outbox requires audit when outbox is written. The completed-idempotency
constraint trigger only validates idempotency rows that are inserted/updated.
No empty/fake support rows are manufactured. This is the owner-scoped internal
foundation, not the complete mutation contract in the architecture: before public
use, M-008 must integrate idempotency, audit, outbox and future version/event policy
in the SAME owned transaction. Do not call this committing facade from an outer
transaction expecting to add those records afterward. Composition must be designed
explicitly in that later task. No audit compliance or API authorization is claimed.

## Error contract

DomainError carries ErrorCode and retryable, without raw SQL/driver text. No HTTP
status mapping is implemented. Eligibility codes include invalid_input,
hackathon_not_found, user_not_found, team_not_found, team_deleted,
already_assigned and team_full. Name validation matches the existing nonempty
space-trimmed / at-most-120-character contract without normalizing the name.

| Database condition | Error code |
|---|---|
| 23505 + pk_memberships | already_assigned |
| 23514 + ct_team_capacity | team_full |
| 23514 + guard_team_deleted | team_deleted |
| Other class 23 integrity errors, including leader/frozen-size faults | integrity_fault |
| 40P01 / 40001 | transaction_conflict, retryable |
| 55P03 | lock_timeout, retryable |
| 57014 | statement_timeout, not automatically retried |
| Other DBAPI failures | database_failure |

Database errors are mapped outside the transaction context, after rollback/unwind;
deferred commit errors are included. Unknown constraints are not disguised as
business conflicts. No retry loop is implemented here. A caller may retry a fully
rolled-back transaction conflict only as a complete operation, never from a partial
step. Connection loss during COMMIT can have an ambiguous durable outcome; without
idempotency, do not blindly retry database_failure. Normal SQL/business failures
roll back the whole team/membership operation. No success is returned before COMMIT.

## Owner verification

The existing guarded runner now accepts --suite schema (default) or --suite services.
Use only the dedicated merge_test target. Every service connection gets the same
actual identity/isolation check through the test Engine connection event. UUID
fixtures commit only in merge_test and remain there; no destructive cleanup. Fresh
invariant checks run after each case. The guarded runner fails fast and never
executes ordinary development tests/migrations. Hidden input is only in an
interactive terminal; no password is passed as an argument or copied from backend/.env.

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite services --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Service verification failed. Stop and review; do not modify constraints.' }
```

There are now 16 service scenarios / 48 cases at three repetitions, covering atomic
creation, post-insert and deferred-COMMIT rollback, joins/counts, full/deleted/team
assignment conflicts, repeat joins, cross-hackathon eligibility, final-seat and
same-user races, concurrent creation, wrong hackathon and missing subjects/teams.
The two rollback cases inject test-only failing/omitted statements using Engine
events; they do not change schema/triggers or add production fault hooks.
R1 adds create/join tests using an explicit AUTOCOMMIT OptionEngine inheriting the
existing actual merge_test identity hook. They observe the actual service DBAPI
state True, require transaction_configuration rejection, assert zero domain/SET
LOCAL statements, compare fresh scoped team/membership counts, and check the
original Engine configuration remains transactional. Existing real failure tests
still require all team/founder mutations to roll back; the statement-failure case
now explicitly verifies DBAPI autocommit False and READ COMMITTED first.

Run the existing schema suite separately if desired, never in a broad development
database suite:

```powershell
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite schema --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Schema verification failed. Stop.' }
```

These commands have NOT been executed by Codex for M-007A. Owner execution above
verified the existing scenarios. Database-free checks/collection do not add live
PostgreSQL evidence beyond the owner-verified run above. Final checkpoint
database-free regressions: 94 passed, 32 deselected, one existing HTTPX warning.
Live cases: 48 collected by Codex; execution was performed only by the owner.
No 50-way HTTP race, CI or load acceptance is established. Owner exercise: explain
why actor locking prevents two same-user service calls from passing membership
checks simultaneously, and why the database PK is still necessary for raw writers.

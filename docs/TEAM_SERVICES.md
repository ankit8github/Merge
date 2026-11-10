# Internal team services — M-007A

## M-008D composed entry points — owner-verified checkpoint

Owner verified guarded merge_test / merge_app, READ COMMITTED, 0003_auth (head):
81 mutation cases in 101.23s, 57 service regressions in 59.59s and 60 idempotency
regressions in 40.81s, **198 passed**, corrected suite-time sum **201.63s**.
Three repetitions requested for each suite, fresh committed chains/invariants
verified and fixtures retained. Codex did not rerun PostgreSQL. Full evidence
and the owner's arithmetic correction are in TEAM_MUTATIONS.md/PROGRESS.md.

New create_team_idempotent()/join_team_idempotent() compose reservation, existing
transaction-local mutation, version, audit, outbox and successful reply completion
under the unchanged _execute owner. Legacy create_team()/join_team() stay internal
compatibility facades and must not back future HTTP mutations. No HTTP routes,
schema/migration, dependency, dispatcher or retry framework is added. See
[TEAM_MUTATIONS.md](TEAM_MUTATIONS.md) for exact interfaces, graph, payloads,
fault tests, owner commands and checkpoint evidence. Earlier entries below describe
their original milestones, not M-008D live verification. G1 remains open.

## M-008C private idempotency primitives — owner-verified checkpoint

Owner verified **60 passed in 40.82s** on guarded merge_test / **0003_auth**,
three repetitions requested, fresh committed-state invariants verified and
fixtures retained. This supersedes the earlier test-only bind failure; the R1
bound-value correction preserves the original one-effect assertion. Codex did
not rerun PostgreSQL. Public composition and G1 remain open.

The new private `services/idempotency.py` module accepts the existing private
commands and an already guarded active connection. It does not change this
service or its public interfaces. Test-only composition uses `_execute` as the
sole owner; no public idempotent create/join path exists. See IDEMPOTENCY.md for
reservation/replay/completion, response limits and owner-run verification.
No team, membership, audit or outbox writes were added by M-008C. The approved
future order is reservation before the unchanged hackathon -> user -> team
locking protocol. The M-008B evidence below is historical, not M-008C live proof.

## M-008B transaction-local extraction — 2026-11-10

Owner-verified final checkpoint: guarded merge_test verification passed at
**0003_auth (head)**; full service suite **57 passed in 40.99s**, three
repetitions requested, fresh committed-state invariants verified. The reduced
diagnostic previously passed **19 in 13.19s**. This records owner execution,
not a Codex PostgreSQL rerun; no separate per-case transcript was supplied.

The earlier M-008B-R1 run stopped with KeyboardInterrupt after 8 passes in 13.17s.
That interruption remains inconclusive; the full suite subsequently completed
successfully. Its historical investigation is retained in PROGRESS.md and does
not supersede the completed 57-case result. G1 remains open.

Implemented for owner review against baseline
35b14080be905f8a7d3e0921724cf4d07fd779c4. Public create_team()/join_team()
signatures, validation, UUID generation timing, TeamResult and SQL behavior are
unchanged. The owner's M-008A approval for this task covers extraction only;
idempotency, audit/outbox, version/reply policies and retry implementation remain
separate work. No migration, dependency, schema, HTTP or frontend change.

Before:

```text
public validation -> _execute -> guarded connection -> begin + SET LOCAL
    -> nested operation closure -> locks/checks/writes/count -> COMMIT -> TeamResult
```

After:

```text
public validation + private frozen command -> _execute
    -> guarded connection -> begin + SET LOCAL
    -> _create_team_in_tx(connection, command) / _join_team_in_tx(connection, command)
    -> unchanged locks/checks/writes/count -> COMMIT -> TeamResult
```

_execute remains the only connection/transaction owner. The private command types
are _CreateTeamCommand and _JoinTeamCommand; the creation UUID is still generated
before acquiring a connection. The extracted methods accept only the supplied
owner-guarded connection and never open, begin, commit, roll back or close one.
Their internal preconditions are an already validated command and the owner's
active guarded transaction. They are not public standalone APIs or a security
sandbox against trusted Python callers. Public APIs still reject caller-owned
Connection/Session objects. No new public mutation method was added.

No _join_locked_in_tx was introduced: there is only one admission path today,
so further splitting would add an unused boundary. Future authorization/composition
must be designed under the same owner, rather than call a committing facade from
an outer transaction.

Creation retains hackathon SHARE -> user NO KEY UPDATE -> new team/founder insert.
Joining retains hackathon SHARE -> user NO KEY UPDATE -> team NO KEY UPDATE, then
fresh membership/count checks. Founder leadership, deleted-team rejection,
frozen size copies and database constraints are unchanged. _execute, the actual
DBAPI AUTOCOMMIT/isolation guard, 5s/15s timeouts, SQL helpers and error mapper
retain their baseline behavior. No support-table writes or team-version updates.
Local results do not escape through public methods until COMMIT succeeds;
statement and deferred-COMMIT failures still unwind the entire transaction.

Executed M-008B checks (Windows PowerShell, existing backend venv):
- Backend `.\.venv\Scripts\python.exe -m pytest -q tests/test_team_services.py --tb=short`:
  **55 passed in 0.57s**, exit 0.
- Backend `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short`:
  **554 passed, 32 deselected, one existing Starlette/HTTPX warning in 10.58s**,
  exit 0; includes authentication/throttling regressions.
- Backend `.\.venv\Scripts\python.exe -m pip check`:
  **No broken requirements found**, exit 0; no dependency changes.
- Backend `.\.venv\Scripts\python.exe -m pytest service_tests --collect-only -q`:
  **57 cases collected in 0.07s**, exit 0; no fixtures executed.
- AST comparison against baseline confirms unchanged owner/guard/helpers,
  signatures/validation, moved operation bodies and all original test functions.

Eight added database-free cases check exact supplied-connection use, one owner
begin/commit, no local lifecycle calls and rollback/error mapping for create/join
statement and deferred-COMMIT failures. The fake now records active transaction
state and counts; it does not simulate PostgreSQL concurrency/invariants.

The guarded suite retains the original 48 executions and adds nine: create/join
connection/root-transaction/commit observation with fresh roster/leader/version/
empty-support checks, and injected join INSERT failure followed by successful
admission. Existing real race, founder/deferred rollback and actual AUTOCOMMIT
assertions remain unchanged. **Owner verified all 57 post-refactor cases in
40.99s**; the old 48-pass M-007A result below remains historical evidence.

No private test credential was supplied to Codex; Codex did not prompt for one or
open a database. The owner completed the full run above; these current-target
commands are retained for reproduction in an owner PowerShell terminal,
without transcripts; the password prompt is hidden. They supersede the historical
default-revision examples below. No migration/reset/cleanup is needed:

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Read-only target verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite services --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'M-008B service verification failed. Stop; do not change constraints.' }
```

The final live count/timing/invariant result is recorded separately in PROGRESS.md.
Final review reran 554 database-free cases in 23.07s, with 32 deselected and the
existing Starlette/HTTPX warning; dependency checks passed and 57 cases collected
in 0.06s. The baseline AST, five-file scope, secret-pattern and whitespace audits
passed. No implementation fix was required during final review.
G1 remains open; no idempotency/audit/outbox, authorized team API, 50-way HTTP race,
CI/load or production-readiness claim. Owner authorized exactly one local commit:
`refactor: extract transaction-local team mutations (M-008B)`. The resulting full
hash/status are read from Git and reported after commit. No remote/push action.

Owner exercise: follow a join from its public validation into the extracted method,
then explain why an exception after its return but during COMMIT still prevents
the public TeamResult from escaping and rolls back the membership.

## Historical M-007A contract and verification

M-007B.3A-R1 exposes authentication only; TeamService and its transaction protocol
are unchanged. No public create/join/leader/invite/request route exists. Future
team actors must come from the real validated-session dependency described in
[HTTP_AUTH.md](HTTP_AUTH.md), followed by server-side authorization. Public UUIDs,
registration results and submitted actor_id/leader flags are never login proof.
M-008's same-transaction idempotency/audit/outbox integration remains required
before public team mutations. Authentication alone does not supply that behavior.

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

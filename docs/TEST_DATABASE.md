# Dedicated disposable PostgreSQL database — M-006B.1

**M-011A-R4: shutdown defect corrected offline; stop for owner review.** The R3
regression now passes. Timeout/incomplete drains remain unsuccessful independently
of later snapshots; final success is printed only after Engine/listener cleanup.
[BROWSER_HOST_AUDIT.md](BROWSER_HOST_AUDIT.md) records the minimal source diff and
R3/R4 evidence. Live reads, scoped auth writes and all account/fixture prerequisites
still require separate owner approval; no live startup is authorized by this fix.

M-011A-R2 implements a separate retained-account-only test browser launcher in
`backend/test_support/browser.py`. Exact guarded inspect/serve/verify commands,
manifest budgets, per-connection/dependency checks and shutdown procedure are in
[BROWSER_ACCEPTANCE.md](BROWSER_ACCEPTANCE.md). Registration remains blocked;
ordinary app.serve is not safe for merge_test browser acceptance. Implementation
is offline verified only; live reads and scoped session/throttle writes require
separate owner approval. No browser, database access or G1 closure is claimed.

M-010A adds fixed guarded `--suite reads`, requiring explicit revision 0003_auth
before credentials. Owner verified at 0003_auth: reads 87 passed in 73.35s and
auth API regressions 54 in 28.28s; total 141 passed, suite-time sum 101.63s.
Three repetitions requested; one existing Starlette/HTTPX warning. This is owner
execution, not a Codex database run. Fixtures retain accounts, sessions and teams;
every connection
checks identity/isolation/revision and fresh committed invariants are inspected.
No schema, privilege or cleanup change. Exact commands: [READ_API.md](READ_API.md).

M-008E adds fixed guarded `--suite retries`, requiring explicit
`--revision 0003_auth` before credentials. It reuses retained mutation fixtures,
identity/isolation/revision guards and fresh complete-chain/invariant verification.
No migration or cleanup. Owner verified merge_test / merge_app, READ COMMITTED,
0003_auth (head): retries 54 passed in 48.66s, mutations 81 in 72.40s, services
57 in 36.15s and idempotency 60 in 42.84s; **252 passed**, suite-time sum
**200.05s**. Three repetitions requested for all suites; fresh committed-state
invariants verified and fixtures retained. Codex did not execute PostgreSQL tests.
Historical results below remain history. Exact reproduction and fault descriptions:
[TRANSACTION_RETRY.md](TRANSACTION_RETRY.md). Collecting this suite opens no DB.

M-007B.3B adds fixed `--suite throttles`, explicit --revision 0003_auth. Codex
collected 33 dedicated cases; updated real-service HTTP/session suites collect
54/78. Owner verified 33 throttles in 31.42s, 54 updated API cases in 30.94s
and 78 session cases in 48.33s: 165 passed in 110.69s, three repetitions
requested, fresh committed-state invariants verified. Existing Starlette/HTTPX
warning remains. This is owner execution, not a Codex PostgreSQL rerun.
Fixtures use unique private test keys to scope retained rows, deliberately
sharing keys across service/app instances for races; they never initialize ordinary Settings or read backend/.env.
Actual per-connection identity guards and fresh invariants remain in force.
Exact hidden-password commands: [AUTH_THROTTLING.md](AUTH_THROTTLING.md).

M-007B.3A-R1 adds fixed guarded `--suite auth-api`, requiring explicit
`--revision 0003_auth`. Real credential/session services are injected into the
HTTP app with the guarded Engine; ordinary runtime Settings are never loaded.
Owner verified the expanded session suite **78 passed in 72.48s** and HTTP API
suite **54 passed in 40.90s**, 132 live executions total on merge_test /
0003_auth (head). Fresh committed-state invariants verified; one existing
Starlette/HTTPX warning. Codex did not rerun PostgreSQL. Private-prompt commands and
retained-fixture/invariant policy: [HTTP_AUTH.md](HTTP_AUTH.md).

M-007B.2B adds guarded --suite sessions, requiring explicit --revision 0003_auth.
Owner verified **63 session cases passed in 51.63s**, guarded merge_test /
0003_auth, three repetitions requested; fresh session invariants verified and
fixtures retained. Codex checkpoint: **222 database-free tests**; no PostgreSQL
rerun or additional post-change live regression result supplied.
Every service connection and fresh observer checks actual test identity. Fixtures
are retained only in merge_test; no cleanup/reset or migration is needed. Exact
private-prompt commands and lifecycle/handoff/lock-test limitations:
[SESSION_SERVICES.md](SESSION_SERVICES.md). Existing suites run separately.

M-007B.2A adds guarded --suite credentials, requiring explicit --revision 0003_auth.
Owner verified **51 credential cases passed in 28.76s**, three repetitions requested,
fresh committed-state checks verified; fixtures intentionally retained without
cleanup. Codex checkpoint: 175 database-free tests passed, no database rerun.
Private-prompt instructions, retained fixtures and remaining regression work:
[CREDENTIAL_SERVICES.md](CREDENTIAL_SERVICES.md). Existing suites run separately.

M-007B.1 adds auth storage. Runner defaults remain 0002_domain; auth migration
and verification require explicit --revision 0003_auth, auth tests also --suite auth.
Do not expect older defaults to accept an upgraded DB. Private-prompt commands
and preservation checks: [AUTH_SCHEMA.md](AUTH_SCHEMA.md).

Current owner-verified target (2026-11-09): merge_test at **0003_auth (head)**.
Auth migration and repeat succeeded; existing domain counts/fingerprints were
preserved. **78 auth schema cases passed in 11.75s**, three repetitions requested;
expected 23514 / ck_throttle_expiration rejection reported. Codex checkpoint:
116 database-free tests passed; no database rerun. Older default-0002 commands
below document the original setup and intentionally refuse the current target.
Use explicit --revision 0003_auth for current verification and guarded suites.
Post-0003 service/domain live regressions were not reported and remain pending.

Owner verified provisioning, guarded migration/repeat to 0002_domain and the
M-006B concurrency run on 2026-11-08: **45 passed in 39.72 seconds**, three
repetitions, fresh committed-state invariants verified. These are owner-reported
execution results; Codex did not rerun PostgreSQL tests for the checkpoint.
Provisioning commands below are retained for fresh approved setup only; never
rerun them against the existing database. Only
`merge_test` on `127.0.0.1:5432` is approved. Ordinary backend configuration and
Alembic commands still target merge_dev; never use them for test provisioning.

## Owner-run provisioning (review first)

Use your own PowerShell terminal without transcripts. `-W` prompts privately;
do not put passwords in SQL, command arguments, chat or source. These commands
use the existing administrator `postgres`. No passwords or roles are changed.

First inspect server identity, absence of merge_test and existing role flags:

```powershell
Set-Location I:\Merge
psql -X -h 127.0.0.1 -p 5432 -U postgres -d postgres -W -v ON_ERROR_STOP=1 -f scripts/inspect_merge_test.sql
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed. Stop.' }
```

After reviewing the script, creation rechecks absence, administrator identity,
non-elevated role flags and absence of role memberships. It creates only the new
database from template0, owned by existing NOLOGIN merge_owner; revokes its PUBLIC
database privileges; grants existing merge_app CONNECT; reconnects and verifies
identity/ownership; revokes PUBLIC public-schema privileges and grants merge_app
USAGE/CREATE. The app owns its future migration objects, not the database. No
cluster role attributes, memberships, other database ACLs or global settings change.

```powershell
psql -X -h 127.0.0.1 -p 5432 -U postgres -d postgres -W -v ON_ERROR_STOP=1 -f scripts/provision_merge_test.sql
if ($LASTEXITCODE -ne 0) { throw 'Provisioning failed. Stop; do not rerun.' }
```

Reconnection may prompt again for the administrator password. Database creation
cannot be transactional with subsequent ACL statements: failure can leave partial
setup, including default PUBLIC database access until its revoke succeeds. Stop
and inspect metadata; do not rerun, replace or automatically repair existing objects.
The server is local; concurrent administrator provisioning is outside this script's
protection. CREATE DATABASE itself refuses an existing name.

## Read-only recovery inspection after any provisioning failure

Keep the existing preflight unchanged: it intentionally refuses an existing
merge_test. Never rerun provisioning to repair a partial setup. Instead, if
merge_test exists, connect directly as the known local postgres administrator:

```powershell
Set-Location I:\Merge
psql -X -h 127.0.0.1 -p 5432 -U postgres -d merge_test -W -v ON_ERROR_STOP=1 -f scripts/inspect_merge_test_recovery.sql
if ($LASTEXITCODE -ne 0) { throw 'Recovery inspection failed. Stop; do not repair or rerun provisioning.' }
```

The password prompt is local and hidden. Do not use a transcript or put secrets
in commands/chat. This script enforces database, effective/authenticated role,
server address and port before reporting metadata, inside an explicit REPEATABLE
READ READ ONLY transaction with bounded statement/lock timeouts. It reports raw
database/schema ACLs (NULL means default ACLs, not absence of access), effective
merge_app privileges, role flags/memberships, public relation/routine/type metadata
and the Alembic revision if its table exists. It reads no password hashes, routine
bodies or application rows. An absent Alembic table is reported without error;
a malformed existing version table can fail safely and requires owner review.
It neither repairs nor automatically accepts unexpected ownership or objects.

Possible partial outcomes:
- Before successful database creation: merge_test may be absent. Direct recovery
  connection then fails safely; use the original maintenance preflight to confirm
  absence. Stop on unexpected results; no automatic retry.
- After creation, before database ACL completion: merge_test remains and database
  CONNECT/PUBLIC ACLs may be incomplete. Administrator inspection works without
  relying on merge_app access.
- After database grants, during reconnect or schema transaction: database creation
  and earlier grants persist. Schema grants roll back if that transaction fails
  before COMMIT. Inspect instead of assuming which permissions survived.
- After schema COMMIT, during final verification: grants remain committed despite
  verification failure. A missing Alembic table is expected before migrations.

Any required repair needs a separate, specific owner-approved plan derived from
the metadata. Do not change ACLs, roles, ownership or objects during inspection.
If authentication/connection is unavailable, stop and resolve it locally without
sharing secrets. This recovery command has been prepared, not executed here.

## Test-only verification and migration (after provisioning approval/execution)

The following commands are prepared, NOT executed during M-006B.1. Each prompts
privately for the **existing merge_app password**. No credential file is needed.
Automation may inject `MERGE_TEST_DB_PASSWORD` through a private secret mechanism;
never type a literal password assignment into shell history. No dotenv is loaded,
no ordinary MERGE_DB_* setting is consumed and backend/.env is untouched. Existing
gitignore excludes local .env variants if an owner stores a secret separately.

Verify uses READ ONLY for identity, CONNECT, schema USAGE/CREATE and revision;
absence of a version table is reported as base, not as successful migration.

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test
if ($LASTEXITCODE -ne 0) { throw 'Test verification failed. Stop.' }
```

The separate online-only Alembic entry point uses unchanged migration files from
`backend/alembic/versions`. It refuses unexpected revision state or preexisting
public relations on a fresh target. It upgrades explicitly to 0002_domain and
allows a repeat at that head. Both connection and migration entry point check
actual database, role, server address/port and READ COMMITTED before writes.

```powershell
.\.venv\Scripts\python.exe -m test_support.database migrate --confirm-merge-test
if ($LASTEXITCODE -ne 0) { throw 'Test migration failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.database migrate --confirm-merge-test
if ($LASTEXITCODE -ne 0) { throw 'Repeated test migration failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test
if ($LASTEXITCODE -ne 0) { throw 'Final verification failed. Stop.' }
```

There is no fallback to merge_dev, implicit target environment switch or change to
ordinary application/Alembic configuration. Exceptions suppress raw connection
details. No new dependencies. Owner-verified online results are recorded above;
checkpoint review did not rerun database commands.

## Future fixtures and separately approved cleanup

M-007A adds internal service integration tests through the same guarded runner:
`--suite services` selects only backend/service_tests; `--suite schema` (default)
keeps the existing schema suite. Both require --confirm-merge-test and the same
private credential flow. Owner verified the expanded service suite: 48 passed in
37.23s, three repetitions requested, including R1 AUTOCOMMIT rejection. Exact
commands, service contract and evidence:
[TEAM_SERVICES.md](TEAM_SERVICES.md). Do not run a broad development database suite.

### Implemented owner-run adversarial suite — M-006B.2B

Owner verified all 45 cases passed in 39.72 seconds with three repetitions on
merge_test at 0002_domain, including fresh committed-state invariants. The suite
asserts 23514 capacity/deleted-team, 23505 assignment uniqueness, 23503 leader FK,
55P03 deliberate lock-timeout and 40P01 deliberate deadlock outcomes. This records
the successful asserted run; no separate raw SQLSTATE transcript was supplied.
No unexpected failures were reported. Implementation/collection and checkpoint
regressions by Codex remain database-free; the PostgreSQL run was owner-executed.
Use the dedicated runner in an interactive terminal (not ordinary `pytest` or
ordinary Alembic, which retain development-database tests). It prompts once for
the existing merge_app password using hidden input, or consumes explicitly injected
MERGE_TEST_DB_PASSWORD. No backend/.env or development credential is read/copied.
Empty/unavailable credentials fail closed. No migration is performed by this runner.

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Concurrency verification failed. Stop and review outcomes; do not change schema or retry blindly.' }
```

Do not run in a transcript. Do not manually put passwords in commands. Report only
test names, sanitized outcomes, SQLSTATEs/constraint names and lock observations.
The runner disables external pytest plugin autoload and option/plugin environment
overrides, fixes the suite directory, suppresses exception/local-variable dumps,
and fails fast. It checks test identity/revision before pytest; all worker and
observer connections independently use the existing guarded connection helper.
Direct pytest execution cannot obtain its private settings and fails before writes.

Credential-free collection:

```powershell
.\.venv\Scripts\python.exe -m pytest concurrency_tests --collect-only -q
```

There are 13 test functions / 15 scenarios, 45 collected executions at default
three repetitions: final-seat race (8 contestants); cross-team same-user race;
cross-hackathon same-user joins; server-observed lock/snapshot race; rolled-back
admission; direct over-capacity commit rejection; leader/successor departures in
both orders; last-member departure/join in both orders; invalid leader commit;
multiple deferred changes; multi-mutation rollback; bounded lock timeout; forced
two-team deadlock with partial-mutation rollback. These are database tests, not
the required 50-way authenticated API acceptance test.

Fixtures use UUIDs, commit only in merge_test and are intentionally retained with
no destructive cleanup. Fresh connections check scoped capacity, leader, deletion,
assignment, FK consistency and frozen sizes after each test, including failures.
Unexpected errors, timeouts outside the specific timeout case, missing server
blocking observations, or failure to observe the required deadlock are failures.
No automatic retries mask them. The runner stops at the first failed case.

Limitations: this successful local run covers the implemented schedules, not all
possible interleavings, future service lock order or other isolation levels.
Barriers/events have 8-second deadlines; lock
observation has 3 seconds, workers share a 30-second join deadline, and all SQL
connections retain 5-second connect/lock and 15-second statement deadlines.
Workers are daemon threads so a failed deadline cannot hold the process open;
stop the failed run before retrying. Busy hosts may fail timing checks. The
deadlock case expects server deadlock detection before lock_timeout; it does not
change server settings. pg_blocking_pids access must be available to merge_app;
no privileges are changed if it is unavailable. Fixture growth requires later
separately approved disposal. No load, HTTP, service-lock/retry or CI proof claimed.

### Safe verification diagnostics

`verify` is intended to succeed before the first migration and report base when
alembic_version is absent. Do not run a migration merely to address verification
failure. Failures now report a fixed bracketed category: authentication,
connection, driver-configuration, identity, permission, migration-state,
verification or migration. Raw exception text, passwords and URLs remain hidden.
Authentication/connection SQLSTATEs are classified when supplied by the driver;
an error without SQLSTATE during connection setup is reported as connection and
does not prove a bad password. Permission/migration-state categories can identify
the failing query stage as well as explicit rejected results.

One safe owner-run diagnostic step is to rerun only the documented guarded
`verify --confirm-merge-test` command in the backend terminal and report just its
bracketed category (or success), never the password. An existing
MERGE_TEST_DB_PASSWORD environment value takes precedence over the hidden prompt;
successful psql authentication does not prove that value is the same. Do not print
it. URL.create accepts the password verbatim; do not manually URL-encode it.
No target guards or connection fallback rules have changed.

Future M-006B fixtures must call `test_connection` for **each** independent
connection, commit UUID-scoped seeds, use barriers/events with bounded waits,
classify SQLSTATEs, and inspect final committed invariants. Connection defaults
are 5-second connect/lock and 15-second statement deadlines; thread/barrier/join
deadlines are implemented by the dedicated harness above.

Committed tombstones accumulate. Cleanup must be whole-database disposal after
separate explicit owner approval, never TRUNCATE, trigger disabling or migration
downgrade. No executable DROP script is supplied in this task. Proposed procedure:
stop owned test clients; administrator connects to local postgres; require typed
exact confirmation of merge_test; verify owner merge_owner and database identity,
expected migration/objects and no unexpected users/connections; stop on mismatch;
review the exact DROP DATABASE merge_test operation separately. Do not use FORCE,
terminate unrelated sessions or accept arbitrary database names. Re-provision only
after verified absence and renewed approval. Never target merge_dev. Shared-role
reuse is convenient but does not create a security boundary against malicious code
that deliberately uses ordinary development credentials; these are safety guards.

Owner exercise: omit `--confirm-merge-test` and explain why argparse stops before
credentials or connection creation. Explain why each new connection needs its own
server-side identity check.

## M-008C guarded idempotency suite

`test_support.concurrency --suite idempotency` requires explicit
`--revision 0003_auth` and `--confirm-merge-test`. It keeps the existing fixed
merge_test target, hidden credential prompt, fail-fast sanitized output, retained
fixtures and fresh committed-state checks. All new independent connections also
check revision before writes. No migration or cleanup runs. The exact two-step
owner PowerShell command, scenario/timeout contracts and checkpoint evidence
are in [IDEMPOTENCY.md](IDEMPOTENCY.md#schema-and-live-verification).
Collection alone opens no connection. Owner verified **60 passed in 40.82s** on
guarded merge_test / **0003_auth**, three repetitions requested, fresh committed-state
invariants verified and fixtures retained. This successful full run supersedes
the earlier first-test failure; see the R1 and final entries in PROGRESS.md.
Codex did not rerun PostgreSQL. This verifies private primitives, not a public API.

## M-008D guarded composed-mutation suite

`--suite mutations` selects team_mutation_tests only and requires explicit
`--revision 0003_auth`. It preserves fixed-target identity checks, bounded waits,
retained fixtures and fresh independent committed-chain/team-invariant checks.
Owner verified merge_test / merge_app, READ COMMITTED, 0003_auth (head): mutations
81 passed in 101.23s, services 57 in 59.59s and idempotency 60 in 40.81s. Total 198
passed, corrected suite-time sum 201.63s, three repetitions requested per suite,
fresh composed chains/committed invariants verified and fixtures retained. Codex
did not rerun PostgreSQL. Exact reproduction commands and the correction of the
earlier arithmetic total are in TEAM_MUTATIONS.md. No migration, reset, privilege
change or fixture cleanup is performed.

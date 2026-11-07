# Dedicated disposable PostgreSQL database — M-006B.1

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

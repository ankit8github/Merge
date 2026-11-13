# Dedicated disposable PostgreSQL database — M-006B.1

## M-019 lifecycle suite - guarded local acceptance passed (M-019E)

Owner-run suite accepted after M-019D review: lifecycle / exact 0005_invitations /
one repetition / 10 collected / 10 completed teardowns / zero failures, skips or
incomplete cases / status passed / stage pytest / exit 0 /
suite_and_fixture_checks_completed. The owner confirms native exit 0. M-019E only
reconciles documentation and rechecks the retained report; it opens no database.

Report: `backend/test-results/guarded/run-114f00ece8514d9ebd9c54d738b6cd3e.json`

SHA256: `9aba72d5f97d32479cb0bcc97caf1acc7dccd34ee38e0fe261202777497f9c86`

This ignored report is aggregate evidence, without per-case race winners, execution
timestamps or a Git/source hash. No owner source-hash/native-exit receipt was
found; independently captured process exit and exact worktree binding cannot be
reconstructed from the JSON. Filename/filesystem metadata support retention, not
independent execution provenance. One repetition does not exercise every ordering;
only simultaneous departures require observed rooted PostgreSQL lock waiters.
Real COMMIT transport-loss coverage remains offline only. Prior G1 evidence is
unchanged; no new G1, browser lifecycle, HTTPS, load, CI, deployment or production
certification is claimed. Those separate validations remain pending.

Separate explicit `--suite lifecycle --revision 0005_invitations` uses new retained
fixtures and all current production service APIs. Collection is credential-free.
Initial/new/pooled/observer connections reuse the full exact-0005 ConnectionGuard;
ordinary Settings/merge_dev never supply a test engine. Existing suites/revision
restrictions are unchanged. No schema migration or cleanup is needed or performed.

Any further run still needs separate owner approval for fresh accounts, sessions,
hackathons, teams, admission/invitation/lifecycle/auth-throttle/audit/outbox/
idempotency writes and read-only final observers. The supported one-repetition
command is:

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite lifecycle --revision 0005_invitations --repetitions 1
if ($LASTEXITCODE -ne 0) { throw 'Lifecycle run failed or incomplete. Preserve evidence; stop.' }
```

Enter an existing DB-role password only at the hidden prompt; never include it in
argv/transcripts. The accepted run does not authorize another execution. Require
exit 0, all cases and teardown checks completed and `suite_and_fixture_checks_completed` in the
sanitized unique report. Retain fixtures on success/failure. Separate review can
approve further repetitions; no blind retry. Earlier browser manifests grant no
lifecycle scope and must not be reused. Details: [LIFECYCLE.md](LIFECYCLE.md).

## M-015B browser host - implemented offline only, 2026-11-11

The separate `test_support.browser_full` CLI supports inspect/prepare/serve/verify
at exact 0005 with per-connection identity/isolation/driver/timeout guards, five
real dependency overrides and bounded scopes. Preparation is a separate explicit
two-hackathon INSERT action; four fresh approved accounts register through the UI.
There is no automatic seeding/migration/cleanup or ordinary Settings fallback.
Complete scope schema, private prompts, supported commands, write effects,
certification/shutdown rules and approval gates: [BROWSER_ACCEPTANCE.md](BROWSER_ACCEPTANCE.md).
No command was run live in M-015B; 0005 remains previously owner-applied. All
legacy runners/0003 browser restrictions are unchanged. No 0005 compatibility is
inferred for 0003/0004 suites. No full browser/HTTPS/G1 acceptance is claimed.

## Historical M-015A browser readiness - analysis only, 2026-11-11

[BROWSER_ACCEPTANCE.md](BROWSER_ACCEPTANCE.md) records ordinary startup's fixed
merge_dev Settings hazard and proposes a separate exact-0005 guarded full-stack
host plus a fresh retained two-hackathon/four-account acceptance plan. No source
host, new CLI, fixture or approval manifest was implemented here; no database
connection or live action. Preserve the legacy exact-0003 browser host and all
suite revision gates. Existing guarded identity/revision verify-0005 is optional
only after separate live-read approval and does not authorize writes/startup.
0005 is already applied; do not rerun migration, downgrade, reset or cleanup.
The new plan explicitly separates fixture, registration, auth/throttle, domain
mutation, observer and browser-fault approvals; no approval is implied by analysis.

## Current M-014B-R2 checkpoint - 2026-11-11

The owner reports **0005_invitations already applied to merge_test** and a
screenshot verifying merge_test / merge_app / 0005_invitations. R2 inspected the
existing sanitized `run-b7498102ceca4576b17a780aa7296157.json`: invitations,
0005, repetitions 3, passed/exit 0, 39 collected and completed teardowns, zero
skips/failures, suite_and_fixture_checks_completed. This is **13 cases x 3 = 39
total**, including three distinct-caller G1 races, not 117 cases. Exact provenance,
source-derived counts, oracle and gate scope: [G1_ACCEPTANCE.md](G1_ACCEPTANCE.md).
Original Phase 1 G1 is closed for that owner-run local PostgreSQL scope; CI,
production HTTPS/browser and load remain open. No Codex database action occurred.

**Do not rerun 0005, provisioning, migrations, cleanup, reset or live tests.** All
earlier proposed/0004-current/no-live/G1-open statements and preparation commands
below are dated history. The invitation suite still requires exact 0005 on every
new/pooled/observer connection; admission still requires 0004, legacy auth/browser
0003, and schema/services reject 0005. No legacy compatibility certification or
independent full schema/retained-data drift inspection is inferred from this run.

## Historical M-014B - proposed 0005 invitation target, offline only

[INVITATIONS.md](INVITATIONS.md) records the additive migration, fixed
`--suite invitations --revision 0005_invitations`, complete compatibility matrix
and separate owner migration/live prerequisites. Existing merge_test is still
owner-reported 0004; no upgrade has occurred here. Eleven old tables, including
join_requests, are fingerprinted/locked inside the owned migration transaction.
New worker/observer connections require exact 0005; old admission remains exact
0004, legacy auth/browser exact 0003, schema/services explicitly reject 0005.
Diagnostics remain metadata-only; fixtures retained. Collection is not execution
or a G1 pass. The historical M-014A blocker below is superseded only by the new
offline prerequisite, not live acceptance or broader legacy compatibility.

## M-014A - distinct-caller acceptance design blocked

[G1_ACCEPTANCE.md](G1_ACCEPTANCE.md) records why the existing 0004 admission API
cannot supply 50 distinct authorized capacity-changing callers for one team.
There is no new G1 suite/command. The existing admission suite remains a
single-leader approval regression; neither its rerun nor credential-free
collection closes G1. No runner, revision gate, diagnostics, fixture or permission
change is made. A secure admission-capability prerequisite needs owner review;
no live run, migration or cleanup is authorized by the analysis.

## Current M-013A checkpoint - 2026-11-11

Owner verified merge_test at 0004_admission and completed guarded admission runs
of one repetition (35 cases) and two repetitions (70 cases). Both exited 0 with
suite_and_fixture_checks_completed; total 105 executions across three repetitions
in two runs. Existing local reports match; PROGRESS.md records the report IDs and
distinguishes owner execution from Codex's database-free review.

**0004 is already applied. Do not manually rerun migrations, provisioning,
downgrade, reset or cleanup against this database.** Earlier setup/migration
commands and pending/unknown-revision statements below are dated history, not
current execution instructions. No live command is authorized by this review.
Legacy auth-dependent suites/browser host remain 0003-only; schema/services
accept explicit 0004 at CLI but lack per-connection revision checks and are not
certified here. Preserve ADMISSION.md's exact compatibility matrix and guards.
The successful race uses one leader's decision identity; distinct-caller G1,
browser/HTTPS, CI/load and deployment acceptance remain open.

## M-013A-R3: guarded-run diagnostics (offline verified only)

R2 could not identify the owner's reported 90-pass/one-failure run. No local
traceback or migration execution record established its suite or cause. The live
PostgreSQL revision is **unknown**; older revision/run statements below are
historical evidence, not a current inspection. R3 does not authorize any live run.

The existing `test_support.concurrency` commands and exact revision/identity/
transaction gates remain in force. Each future invocation that passes CLI gates
creates a unique report before credential acquisition and prints its relative
path: `test-results/guarded/run-<printed-run-id>.json` (relative to backend).
This fixed directory is covered by Git's existing `test-results/` exclusion.
There is no arbitrary output-path option, credential argument, rerun or cleanup.
An unavailable/redirected diagnostic destination fails before a database opens.

Reports contain only approved suite/revision/repetition metadata, progress counts,
exit code, status, active node and bounded failure records (maximum 16). A failure
record has node ID, setup/call/teardown/collection phase and a fixed assertion/
exception/collection_error category. Exception messages, assertion operands,
source/tracebacks, locals, SQL/parameters, headers, captured output and warnings
are deliberately omitted: safely redacting arbitrary values cannot be guaranteed.
The current static parameter labels are allowlisted; unfamiliar parameter labels
are replaced with `[parameter_id_withheld]`, and unsafe node paths are withheld.
Normal reviewed IDs, including both R2 candidate nodes, are preserved exactly.
Future static labels require review before adding them to the output allowlist.

Pytest terminal rendering, Python stdout/stderr and OS descriptors 1/2 are sent
directly to the null device without captured-output temp files. Warning/short-
summary rendering and file/CLI logging are disabled. The existing `-s`, `-x`, plain
assertions, disabled cache/plugin autoload,
fixed suite and private settings injection remain. Fresh invariant checks still
execute in the existing fixtures; no fixture/assertion was changed or bypassed.
The launcher prints sanitized failed nodes/categories and final metadata instead
of private pytest output. Reports remain bounded below 16 KiB and are atomically
replaced, preserving the previous complete record if an update is interrupted.
On Windows only the metadata rename gets up to four attempts with 25 ms pauses
for transient file-sharing errors; no fixture, test or database operation retries.

Initial status is `incomplete`, with exit_code null and invariants `not_certified`.
`suite_and_fixture_checks_completed` requires exit 0, nonempty collection, every
teardown completed, and no recorded failure/skip/interruption. It means existing
suite fixture checks returned; it is not an independent database inspection.
Failure in a test or fixture (including final invariants), interruption, internal
error, zero collection or skip leaves invariants uncertified. Setup/teardown
phases do not distinguish an invariant assertion from other fixture assertions.
Pytest exit codes are preserved; an uncaught interrupt returns 2, unexpected
runner errors return 1, and report-finalization failure cannot turn failure into
success (a would-be exit 0 becomes 1). A second interrupt during finalization also
remains nonzero. A hard kill may leave only the last incomplete record or a temp
file; it cannot prove workers/transactions stopped. Accept completion only with
the matching run's terminal exit code and complete report, never a report alone.

To retrieve existing evidence without opening PostgreSQL:

```powershell
Set-Location I:\Merge\backend
Get-ChildItem -LiteralPath .\test-results\guarded -Filter 'run-*.json'
# Substitute the exact filename printed for the run being investigated:
Get-Content -LiteralPath '.\test-results\guarded\run-PRINTED_RUN_ID.json'
```

Match the printed run ID rather than assuming the newest file is the failed run.
Keep its exit code, suite, revision, failed node, phase and category together.
There is no raw traceback to retrieve from this metadata-only report. If this is
insufficient, stop for a separately reviewed focused diagnostic; never enable raw
exception/SQL/header dumps or rerun the entire suite merely to recover a name.
No report exists retroactively for the unidentified earlier run. No PostgreSQL
connection, migration, live test or credential inspection occurred during R3.

M-013A prepares explicit 0004_admission migration and fixed --suite admission.
Nothing has been applied or run live. The separate owner-approved sequence in
[ADMISSION.md](ADMISSION.md) preserves existing domain/auth fingerprints atomically,
retains scoped fixtures and verifies fresh committed invariants. Existing runner
defaults and legacy 0003_auth suite gates are intentionally unchanged. After
upgrade, auth-dependent suites/browser host refuse 0004. R1's exact compatibility
matrix in ADMISSION.md notes that schema/services accept explicit 0004 at CLI but
lack per-connection revision checks; this is not reviewed upgrade compatibility.

M-012A adds fixed guarded `--suite team-api`, requiring explicit 0003_auth before
credentials. Real auth/read/team dependencies share the guarded test Engine; new
UUID fixtures are retained and fresh committed chains/invariants checked. The
owner verified 105 cases in 140.81s at guarded 0003_auth. Codex did not rerun
PostgreSQL. Reproduction commands and exact writes are in
[TEAM_API.md](TEAM_API.md); no schema, privilege, cleanup or browser-host expansion.

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

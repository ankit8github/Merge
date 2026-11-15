# Batch B owner execution runbook (NOT EXECUTED)

Prepared 2026-11-14 against main HEAD
`abfea1a6116dbe0295b45d21e290c56f84a91eb5` plus uncommitted Batches A/B.
This document authorizes nothing live. Stop for owner review before each approved
scope below. Existing exact-0005 evidence/manifests and retained rows stay intact.
Do not use ordinary application startup, `alembic upgrade head`, arbitrary DB URLs,
cleanup/reset, fixture deletion, downgrade or an old browser acceptance manifest.

## 1. Freeze and offline checks

Review the complete pending diff and untracked files before approval. Preserve
the ignored `backend/test-results/batch-b/baseline.patch` and `baseline.json`.
New receipts capture HEAD, SHA256 of every tracked/nonignored untracked source,
Python/platform and native exit codes before/after execution. Do not edit source
or run validators concurrently during a live evidence run. These are local
integrity receipts, not signed independent provenance. Historical aggregate
certificates cannot retroactively acquire a source hash.

From PowerShell, the minimum offline checks are:

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short
if ($LASTEXITCODE -ne 0) { throw 'Backend failed; stop' }
.\.venv\Scripts\python.exe -m pytest profile_tests --collect-only -q --confirm-profile-test
if ($LASTEXITCODE -ne 0) { throw 'Collection failed; stop' }
Set-Location I:\Merge\frontend
npm test -- --reporter=dot --maxWorkers=1
if ($LASTEXITCODE -ne 0) { throw 'Frontend failed; stop' }
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Typecheck/build failed; stop' }
Set-Location I:\Merge
node --check load/board.js
git -c safe.directory=I:/Merge diff --check
```

The focused `backend/tests/test_release_support.py` checks JSON/YAML syntax,
matrix/count/worker contracts, additive migration SQL rendering, guards, seed
invariants, synthetic load reports and failed/stale receipts. JSON syntax in
`.github/workflows/ci.yml` is a YAML 1.2 subset. A real Actions run remains required
for GitHub expression, service, Docker/network-namespace and Linux validation.
Frontend parallel initial-loading timeouts remain known; use one worker. No
assertion or timeout was weakened, and default-worker success is not claimed.

## 2. Approve and run exact-0005 SSE separately

Approval scope: connect only to existing `merge_test` / `merge_app`, actual
127.0.0.1:5432, exact `0005_invitations`; four fresh retained SSE scenarios using
real account/session, hackathon/team/membership, request/invitation/lifecycle,
idempotency/audit/outbox writes and read-only invariant observers. No migration
or cleanup. The original runner and four cases are unchanged. The new wrapper
adds source/native-exit binding and strict aggregate checks only.

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m release_support.realtime_acceptance --confirm-merge-test
if ($LASTEXITCODE -ne 0) { throw 'SSE incomplete; preserve evidence and stop' }
```

Enter the existing role password at the hidden prompt. Require a unique
`test-results/release/realtime-*.json`: native exit 0, unchanged source, suite
realtime / exact0005 / one repetition / collected4 / teardown4 / skip0 /
failures[] / statuspassed / stagepytest / `suite_and_fixture_checks_completed`.
This certifies actual polling SQL/transaction visibility and privacy composition;
it does not certify browser/proxy transport, HTTPS or sustained SSE capacity.

## 3. Approve new profile target and additive migration

Approve **new** `merge_profile_test` creation, grants, preparation through0005,
then separate0005->0006 migration, then the30-case profile acceptance run. This
does not approve any change to `merge_test` or `merge_dev`. Existing unprivileged
login role `merge_app` is reused without changing its password/memberships. Review
`scripts/provision_merge_profile_test.sql`; it refuses an existing target and
unexpected admin/server/role. No existing role or database is dropped/adopted.

From repo root, only after approval:

```powershell
psql -X -h 127.0.0.1 -p 5432 -U postgres -d postgres -W -f scripts/provision_merge_profile_test.sql
if ($LASTEXITCODE -ne 0) { throw 'Provision incomplete; stop, never rerun blindly' }
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m release_support.migrations prepare --target profiles --confirm-target merge_profile_test
if ($LASTEXITCODE -ne 0) { throw 'Prepare failed; stop' }
.\.venv\Scripts\python.exe -m release_support.migrations migrate --target profiles --confirm-target merge_profile_test
if ($LASTEXITCODE -ne 0) { throw 'Migration failed; stop' }
.\.venv\Scripts\python.exe -m release_support.migrations verify --target profiles --confirm-target merge_profile_test
if ($LASTEXITCODE -ne 0) { throw 'Revision preflight failed; stop' }
.\.venv\Scripts\python.exe -m release_support.acceptance --confirm-profile-test
if ($LASTEXITCODE -ne 0) { throw 'Profiles incomplete; preserve fixtures and stop' }
```

Prompts use the existing merge_app password. New targets require actual loopback,
port5432, exact DB/role/revision, psycopg synchronous PostgreSQL, no elevated role
flags or role memberships, READ COMMITTED, non-autocommit and fixed5s lock/15s
statement timeouts on every engine connection. No Settings/dotenv fallback.

Prepare accepts an empty public schema only. Migrate accepts exact0005 only and
SHARE-locks/fingerprints all12 existing tables, including invitations, inside the
same transaction that owns the DDL. It compares counts/content before commit.
Failures roll back; reports retain counts only. 0006 creates one optional table
with PK(user_id), users FK and four checks. The PK index is sufficient for profile
lookup; ranking scans a bounded pool and has no claimed measured index tuning.
No old row backfill/update/delete or privilege change. No retained rows require
deletion. Database zone checks constrain syntax; application validation enforces
installed IANA zones. Downgrade intentionally refuses data removal.

Thirty fresh cases retain roughly120 account/credential/session rows,31
hackathons and31 teams (including a tombstone), associated commands/memberships/
invitations/audit/outbox and successful profile edits. Failed constraints and
uncommitted updates roll back; no fixture cleanup. Cases cover real schema/FK,
own-account/CSRF/Origin/actor boundaries, invalid fields, empty skills, formula,
UUID ties, opt-out/current/other-hackathon membership, full/deleted/nonleader
teams, snapshot paging, CAS races, invisibility/rollback and lifecycle/SSE
compatibility. Existing global opt-in users are preserved and paginated normally;
the suite fails if retained candidate growth exceeds the production pool bound.
Require profiles / exact0006 / repetition1 / collected30 / teardown30 / skip0 /
failures[] / exit0 / completed invariant checks plus30 unique successful node IDs.
No admission/G1 certification is inferred from the two-writer profile CAS case.

### Profile 0005 read-only inspection: interactive authentication repair

The first independent inspection stopped at connection setup: one attempt, no
inspection SELECTs, native1. Its launcher used environment passwords or libpq's
password file without a hidden-input prompt. The recorded local preflight found
neither an environment password nor a matching profile password-file entry. The
suppressed connection exception does not establish its precise transport/auth
cause. The successful preparation runner supports hidden `getpass` input.

`release_support.profile_inspection` preserves the historical collector and adds
the missing hidden-input path: existing `MERGE_RELEASE_DB_PASSWORD`, otherwise
existing `PGPASSWORD`, otherwise `getpass`. Empty input, EOF, cancellation or an
unavailable hidden console stops before connecting; `GetPassWarning` is fatal
before echoed fallback input. The password stays in process memory and is passed
directly to psycopg, never written into environment variables, reports or command
arguments. Exception reports retain only class, SQLSTATE and stage.

Only `127.0.0.1:5432 / merge_profile_test / merge_app` is allowed. The explicit
loopback `hostaddr` also prevents inherited `PGHOSTADDR` redirection. Confirmation,
non-autocommit, read-only REPEATABLE READ snapshot, 5s connect/lock and 15s statement
bounds, role/identity/revision guards and rollback are retained. This launcher
collects a snapshot; even native0 means `snapshot_complete_requires_definition_review`,
not certification. Constraints/indexes/triggers/functions still require the full
independent definition review. Existing migration `verify` expects0006 and cannot
substitute for this inspection. No migration authorization follows automatically.

The stdout-only worker previously relied on an optional multi-line owner block
for persistence. The shorter module command bypassed that block: native0 and
printed JSON alone did not create reviewable evidence. Direct module invocation
now enters `profile_inspection_capture`; only its supervised child calls the
unchanged inspection function. The child inherits the console for hidden input;
no password is sent in arguments, environment changes or saved diagnostics.

After separate owner approval of ONE new read-only inspection, run this ONE
command in a native PowerShell console, without output redirection or Tee-Object:

```powershell
& 'I:\Merge\scripts\inspect_merge_profile_0005.ps1'
```

The script anchors the repository/backend/interpreter regardless of the current
directory. The supervisor creates a fresh ignored
`backend/test-results/profile-0005-readonly-<uuid>/` directory and retains:

- `source-manifest.json`: HEAD and tracked/nonignored source SHA256 values.
- `started.json`: an incomplete, uncertified start marker binding source and
  worker/supervisor hashes before launching exactly one child process.
- `database-snapshot.json`: the approved worker JSON, including sanitized partial
  results on ordinary inspection failure; raw/unparseable output is discarded.
- `process-receipt.json`: the independently observed child return code, source
  stability, interruption state and SHA256 bindings to the three other files.

Files are UTF8, exclusively created and never overwritten. Failed/unknown worker
exits, timeout/cancellation, source drift, invalid JSON, failed persistence, missing
conditions or missing definition inventories return nonzero and preserve evidence.
No child retry or fixture cleanup follows failure. Raw stderr, exception messages,
password fields and DSNs are never retained in the capture reports.

The offline `profile_inspection_capture.validate_capture` gate checks all four
files, source bindings, SHA256 consistency, actual native0 and all19 exact-true
conditions. Even a complete capture is only
`capture_complete_requires_definition_review`, with `final_certified=false`.
Independent identity/grants/definition review remains mandatory before a separate
0006 approval. A snapshot alone, a start marker or native0 alone cannot certify.
The supervisor prints the unique evidence directory and child exit. This is local
integrity evidence, not signed independent provenance. Freeze source before the
approved run; retain failed/incomplete artifacts unchanged.

Source hashes will differ from earlier preparation receipts after this repair;
retain those original receipts unchanged. The fresh inspection binds the current
source tree and does not rewrite or extend the historical preparation evidence.

## 4. Approve isolated public CI separately

Publishing/committing/pushing/dispatching Actions needs separate owner approval.
Prepared workflow has an offline job and four independent PostgreSQL16 service
jobs:0003 auth-api18 + team-api35;0004 admission35;0005 invitations13 + lifecycle10
+ realtime4;0006 profiles30. All are actual composed services/HTTP tests; the
invitations suite includes `test_distinct_authenticated_50_caller_last_seat`.
Required exact counts, completed fixture checks, zero skips and exit0 fail closed.
Missing reports/artifacts fail. No broad legacy revision exception is introduced.

Each GitHub-hosted job creates a fresh unprivileged role and DB, refuses an
existing Merge namespace, runs exact migrations and destroys only its ephemeral
container by runner lifecycle. A CI administrator credential is ephemeral; the
application credential is random/in-memory. `sudo nsenter --net` enters only the
Postgres container network namespace so the server observes actual127.0.0.1,
preserving the original strict server-address guard. Host source/dependencies
remain available. Docker/sudo/nsenter and GitHub environment propagation must
work; any incompatibility fails rather than weakening guardrails.

Artifacts `acceptance-<revision>-<attempt>` retain metadata-only diagnostic JSON
and source-bound receipts for14days, including failures. Third-party tracebacks
are suppressed to avoid secrets; missing/incomplete steps remain uncertified.
No successful public CI run exists from this task. Owner must retain actual run
URL, all required green jobs and downloaded sanitized artifacts. Compare source
hashes against that run's checkout; do not compare a changed local tree.

## 5. Approve dedicated benchmark provisioning and seed

Approve new role `merge_bench_app` (new private password), new `merge_bench`,
grants, prepare/migrate/verify and a one-time atomic seed. Neither retained
merge_test nor merge_dev is accepted by any benchmark tool. Review the create-only
script; psql prompts privately for the new role password. If interrupted after
role/database creation, stop for review; do not drop or automatically reuse it.

```powershell
Set-Location I:\Merge
psql -X -h 127.0.0.1 -p 5432 -U postgres -d postgres -W -f scripts/provision_merge_bench.sql
if ($LASTEXITCODE -ne 0) { throw 'Provision incomplete; stop' }
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m release_support.migrations prepare --target benchmark --confirm-target merge_bench
if ($LASTEXITCODE -ne 0) { throw 'Prepare failed; stop' }
.\.venv\Scripts\python.exe -m release_support.migrations migrate --target benchmark --confirm-target merge_bench
if ($LASTEXITCODE -ne 0) { throw 'Migration failed; stop' }
.\.venv\Scripts\python.exe -m release_support.migrations verify --target benchmark --confirm-target merge_bench
if ($LASTEXITCODE -ne 0) { throw 'Revision check failed; stop' }
.\.venv\Scripts\python.exe -m release_support.seed --confirm-merge-bench --seed 2026
if ($LASTEXITCODE -ne 0) { throw 'Seed incomplete; stop' }
.\.venv\Scripts\python.exe -m release_support.seed --confirm-merge-bench --seed 2026 --verify-only
if ($LASTEXITCODE -ne 0) { throw 'Dataset check failed; stop' }
```

Default deterministic UUID5 seed2026 creates10000 users/credentials/profiles,
one hackathon,2000 teams,5000 unique memberships and5000 unassigned participants.
Team sizes cycle1/2/3/4, capacity4, readiness minimum2, exactly one rostered leader;
8000 users opt in. Eight skill patterns plus empty skills and eight IANA zones
plus null exercise realistic varied profiles without claiming a real population.
All fixed IDs, names, credential mappings, skills/zones/version, team/hackathon
size/leadership and exact rosters are checked. Validation SQL is exported as
`release_support.seed.VALIDATE_SQL`; it returns counts, duplicates, invalid teams
and orphans. Receipts record counts and deterministic dataset SHA256.

Every application table must be empty under exclusive locks before insertion;
no truncation/delete. One transaction inserts batches500, forces deferred DB
constraints and validates before commit. Initial-state fixture insertion uses
direct SQL under unchanged constraints, not application mutation service calls.
Consequently audit/outbox/idempotency start empty. It proves a benchmark dataset,
not a race, auditing or mutation certificate. All benchmark accounts share one
private benchmark-only cohort password, hashed with the existing Argon2 codec;
passwords/hashes/tokens never enter reports/source or CLI arguments.

## 6. Approve benchmark host and local load separately

Prerequisites: owner-reviewed installed k6 available on PATH; fill every actual
hardware/topology/cache field from `load/environment.example.json` in ignored
`backend/test-results/bench-environment.json`. Placeholders are rejected. Disclose
shared client/server hardware, PostgreSQL version/process/container/storage/RAM
limits, competing workloads and cache state. No measured values are supplied here.

Approve host127.0.0.1:8766 only, real session validation and bounded GET board/SSE
reads; the load command also writes100 real auth sessions before measurement.
Sessions are issued by real credential/KDF/session services outside measurement,
avoiding the shared-IP HTTP login throttle without weakening it. This excludes
registration/login throughput. No mutation HTTP routes, public binding/proxy,
browser or production endpoint are exposed. No TLS/production capacity claim.

In terminal1 (existing benchmark DB-role credential at hidden prompt):

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m release_support.benchmark_host --confirm-merge-bench --seed 2026
```

In terminal2, approve and execute baseline then SSE-overhead comparisons separately:

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m release_support.load --confirm-merge-bench --seed 2026 --sse-clients 0 --environment test-results/bench-environment.json
if ($LASTEXITCODE -ne 0) { throw 'Baseline failed/inconclusive; preserve evidence and stop' }
.\.venv\Scripts\python.exe -m release_support.load --confirm-merge-bench --seed 2026 --sse-clients 32 --environment test-results/bench-environment.json
if ($LASTEXITCODE -ne 0) { throw 'SSE load failed/inconclusive; preserve evidence and stop' }
```

Both commands independently verify exact DB/revision/dataset and authenticated
host attestation before workload. Private cookies pass only through the k6 child
environment, never argv/files/logs.100 constant VUs warm up20s then measure60s,
with5s graceful tail. Closed-loop continuous authenticated reads request the first
20-team board page. No think time, mutation mix, other pages, ranking throughput
or login performance is implied. Latency is k6 HTTP request duration (not DNS/
socket queue setup); p50/p95/p99, measured request count/error rate and throughput
are reported. Throughput uses actual measured elapsed60-66s, not the whole-window
Counter rate. Target is strict p95<200ms and zero invalid/failed responses; k6
threshold exit99 is preserved and never certified. Missing metrics/samples,
contradictory exit/thresholds, SSE failure or changed sources fail the run.

32 optional real SSE clients validate frames and reconnect after normal leases.
At2s sampling,32 subscribers imply nominal16 polls/s, each with real session
validation plus the outbox snapshot and connection guards. Actual query/CPU cost
is not estimated as measured. The existing64/process and2/account limits remain.
Snapshot counts scan retained history; SQL timeout bounds execution, not scanned
rows. This seed has zero outbox history and measures idle SSE overhead only.
Receipt records actual outbox row count; mutation-heavy/history growth, proxy
buffering, browsers, multi-instance fanout and production HTTPS remain separate
tests. Do not tune or claim scale acceptance before real results and disclosure.

## 7. Verify receipts, stop and retain

Every command above must produce native exit0 before the next dependent step.
`release_support.verify` is offline and accepts only a fixed release-directory
receipt, unchanged source, success exit and complete kind-specific contracts:

```powershell
# Replace only the unique receipt filename printed by the approved command.
.\.venv\Scripts\python.exe -m release_support.verify test-results/release/profiles-RECEIPT_ID.json
if ($LASTEXITCODE -ne 0) { throw 'Receipt not certified; stop' }
```

Use migration/seed/realtime/ci/load filenames similarly. Archive sanitized
receipts plus source/environment and independent native exits in the owner's
release record; keep private environment/cohort secrets out of Git/artifacts.
Reports alone are not proof of a public CI run or deployment.

On any failed, skipped, interrupted, stale or ambiguous result, stop. Preserve all
fixtures and reports. Do not blindly retry CAS/races/seeding/provisioning or edit
old certificates. Migration/seed transactions roll back on ordinary failures;
an ambiguous COMMIT needs a separately approved read-only verify before a new
write. Provisioning CREATE DATABASE/ROLE cannot be rolled back as one transaction;
partially created targets require owner inspection, never automatic cleanup.
Ctrl+C terminal1 to stop the approved benchmark host; no production service is
touched. Application rollback should stop use of new profile routes and retain
0006 data; no destructive database downgrade is prepared. Commit/push/deployment
and real browser/mobile/keyboard/HTTPS checks require separate approval.

# M-019A team lifecycle contract

Design recorded before implementation. Owner's M-019A request authorizes these
additive APIs and UI, not live database execution or changes to old browser scopes.
No migration, dependency, constraint, session or existing mutation protocol change.

## Current acceptance - M-019E

Guarded local PostgreSQL lifecycle acceptance PASSED in the owner-run report
reviewed by M-019D and accepted for documentation/local commit by M-019E.

Report: `backend/test-results/guarded/run-114f00ece8514d9ebd9c54d738b6cd3e.json`

SHA256: `9aba72d5f97d32479cb0bcc97caf1acc7dccd34ee38e0fe261202777497f9c86`

Exact results: suite lifecycle; revision 0005_invitations; repetitions 1; collected
10; completed teardowns 10; failures 0; skips 0; incomplete cases 0; active_node
null; status passed; stage pytest; exit_code 0; invariant_verification
suite_and_fixture_checks_completed. The owner confirms native exit 0. Offline
evidence remains 1464 backend tests passed and 350 frontend tests passed with
typecheck/build passed. No tests or database commands are rerun by M-019E.

Provenance limits: the retained ignored report records aggregate counters, not
individual race winners, execution timestamps or a Git/source hash. No owner
source-hash/native-exit receipt was found. File identity and filesystem metadata
support retention/freshness but cannot independently bind the report to the exact
executed worktree or capture native exit. Owner confirmation and the actual report
are the accepted evidence; no stronger receipt is fabricated after execution.
One repetition does not force every interleaving. Only simultaneous departures
require observed rooted PostgreSQL waiters; real COMMIT transport loss remains
covered offline only. Prior G1 and M-017 evidence remain unchanged.

Browser lifecycle/mobile/keyboard, HTTPS, load, CI and deployment verification
remain pending. This is not a new G1/50-caller run or production certification.
Old browser hosts/manifests still exclude lifecycle operations. All fixture data
and old evidence are retained. M-019E authorizes only documentation reconciliation
and one local commit, with no production-code edit, live execution or remote action.
Historical M-019A/B checkpoints and the future-run proposal below retain their
original scope; this section supersedes their pending local PostgreSQL status.

## Transactions and authorization

Reuse TeamService._execute, _run_composed, reservation/completion and outbox helpers.
Order: idempotency reservation; hackathon FOR SHARE; affected users in sorted UUID
order FOR NO KEY UPDATE; exact team FOR NO KEY UPDATE; membership deletion and
team update; audit/outbox/completed reply; commit. Never lock a user after a team.
Leave locks the actor; remove locks actor and subject. Current team leadership is
checked under the team lock before removal or its replay. Self-removal is rejected;
use leave. The departing subject must currently belong to this exact team.

Every supported membership mutation takes the team lock. After deletion, choose
the earliest remaining (joined_at, user_id) as successor if the leader departed.
Selection does not alter the successor membership or take a late user lock. A
simultaneous successor departure waits for the team lock, then sees current state.
No remaining membership means leader NULL and deleted_at=clock_timestamp() in the
same update. Existing deferred FK/final-state checks remain enabled. Below-minimum
nonempty teams become forming. Existing reads exclude tombstones.

Leave's exact actor-scoped stored replay must work after departure/deletion and
after the actor joins elsewhere; it returns the original receipt, never deletes
another membership. Authentication/CSRF still run. Remove replay requires current
leadership even when its subject already left. Do not note replay proof before
this authorization (the existing runner can return a noted replay on later errors).
Failures roll back their reservations. Each success increments version exactly
once and records actor, affected subject, before/after leader/count/deleted state,
one append-only audit and one existing team.changed.v1 outbox event. No dispatcher.

## HTTP

All paths start /api/hackathons/{hackathon_id}/teams/{team_id}.

- POST /leave, JSON {}: validated cookie actor leaves own membership.
- POST /members/{user_id}/remove, JSON {}: current leader removes another member.
- GET /members?limit=20&cursor=<user UUID>: member-only bounded roster, UUID ordered,
  items {user_id,display_name,joined_at}, next_cursor. A removed cursor is invalid.

Both POSTs reuse exact Origin/Fetch Metadata, session-bound CSRF, strict empty JSON,
no identity selectors/query parameters and one Idempotency-Key (1-128 printable
ASCII). Response 200: {schema_version:1,data:{hackathon_id,team_id,user_id,
member_count,team_version,leader_user_id,deleted}}. user_id is the departing subject;
leader_user_id is nullable only for deletion. This is an immutable receipt, not a
current team DTO. Refetch canonical reads; do not reconstruct state from a receipt.

401 invalid_session; 403 forbidden/invalid_csrf/browser policy; 404 team_not_found;
409 member_not_found/idempotency_mismatch; 422 use_leave/invalid_request;
503 service_unavailable or outcome_uncertain. Error bodies never expose SQL/input.
As in existing creation, a nonexistent parent hackathon can fail the reservation
foreign key first and produce sanitized 503; no speculative preflight is added.
Uncertain delivery keeps exact account/hackathon/team/subject/key for explicit retry.
An earlier uncertainty is not erased by a subsequent denial. No automatic mutation
replay. Frontend command journal stays App-lifetime memory only; reload/crash loses
keys, as with existing commands. Confirm leave/removal before first submission;
unchanged uncertain retry uses its existing confirmation. Display names accompany
roster IDs; IDs remain command selectors, never authority.

## Required verification

Offline: deterministic succession/tie break; ordinary/final leave; self-removal,
outsider/former-leader denial; exact replay/mismatch; rollback at every write and
COMMIT; lock order; typed HTTP/security; bounded private roster; account/workspace
isolation, confirmation, failure/retry and canonical refresh in React.

Real PostgreSQL (PASSED for the ten cases / one repetition recorded above):
simultaneous departures, removal/departure races; leave vs approval,
redemption, cross-team admission; leadership changes vs old-leader commands;
same-key contention; fresh committed capacity/uniqueness/leadership/version/audit/
outbox/reply checks. Use a separate exact-0005 lifecycle suite and fresh retained
fixtures only. Old suites' historical approved/redeemed-member assertions assume
no departures; do not weaken them or run lifecycle against their retained scopes.
Old browser hosts explicitly exclude lifecycle routes. A new browser acceptance
plan is separate work; no old manifest or budget is extended.

## M-019A offline checkpoint and owner review (historical)

Final database-free backend suite: 1455 passed, 32 database tests deselected, one
existing Starlette/HTTPX warning. Full frontend: 350 passed / 12 files; production
build/typecheck passed. Focused backend lifecycle/API/readiness plus existing
read/team API regressions: 222 passed. The ten PostgreSQL lifecycle cases collect
at one repetition; none had executed at that checkpoint. The current acceptance
section above supersedes that execution status. See PROGRESS.md for exact evidence.

Before live approval, review the six-override exact-0005 test host, fresh retained
fixture effects and full chain checks. Simultaneous departure requires at least
two registered backend team-lock waiters rooted at its own observer; other paired
races use bounded concurrent starts. These schedules do not prove every possible
interleaving. They are additional local transaction/API acceptance, not load/TLS.
Every test seeds a fresh hackathon and three fresh accounts/sessions, creates its
own team, and performs only its declared setup/actions; the cross-team case adds
one founder/team. No existing fixture is adopted or cleaned. All effects retained.

Owner review sequence: inspect diff and offline results; separately approve one
guarded lifecycle repetition using TEST_DATABASE.md; require completed teardown
certification and exit 0; then review any additional repetitions or G1 rerun.
Real-browser lifecycle validation needs a separately approved new browser host/
manifest contract. Never launch ordinary app.serve against merge_dev for tests.
Only after these results review a local commit. None of these live/commit steps
was performed or implicitly authorized by implementation.

Owner explanation exercise: with two members leaving concurrently, explain why
the first transaction may select the second as successor safely without taking a
late user lock, and why the second must re-read the team after acquiring its lock.

## M-019B independent offline acceptance review (historical)

At the M-019B checkpoint: CONDITIONAL for an owner-approved first PostgreSQL execution;
not a PostgreSQL acceptance pass. No production concurrency or authorization
defect was demonstrated. The shared lock order remains reservation, hackathon,
sorted affected users, team. A successor is selected while the team lock is held,
without a late user lock. Concurrent departures cannot delete their memberships
until they acquire that same team lock and reread committed state. Approval,
redemption and removal use the same parent serialization and existing deferred
constraints. A leader's leave replay returns its immutable actor-scoped receipt;
a removal replay must still pass current leadership authorization.

One acceptance-oracle defect was demonstrated offline: the teardown accepted a
wrong receipt hackathon, team, count, version, schema, HTTP status, headers or
outbox event type. Eight negative examples failed to raise before correction.
The checker now verifies the entire lifecycle receipt, event identity/schema,
reply headers, adjacent audit-state continuity and deletion/readiness consistency.
The succession test now successfully removes a member before leadership changes,
then retries that exact successful removal key as the former leader and requires
403. Two race losers also require their exact domain error, not just HTTP 409.
These are acceptance-check/test corrections; production behavior is unchanged.

Actual M-019B offline commands (from backend):

| Command | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_lifecycle_acceptance_review.py tests/test_lifecycle.py tests/test_lifecycle_api.py tests/test_lifecycle_readiness.py --tb=short` | 64 passed, 4.03s, exit 0 |
| `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short` | 1464 passed, 32 deselected, 42.63s, exit 0 |
| `.\.venv\Scripts\python.exe -m pytest --collect-only -q lifecycle_tests --race-repetitions=1` | 10 collected, 0.04s, exit 0; no database/fixture execution |

All three commands emitted the existing Starlette/HTTPX deprecation warning.
The frontend is unchanged by M-019B; its 350-test/build result above is the prior
M-019A evidence, not a new frontend execution. The new offline regression file is
backend/tests/test_lifecycle_acceptance_review.py. No dependency or migration.
The proposed PowerShell block passed AST parsing without execution. Its isolated
metadata-only certification condition accepted a valid synthetic report and
rejected eighteen failure cases (including missing fields, interruption, wrong
suite/revision/counts, pending work, source drift and native failure). Sixteen
pending Python files parsed; targeted private-key/token/credential-URL and artifact
checks found no hits. Whitespace checks passed. The three prior manifests and
retained G1 report SHA256 values are unchanged; reports/owner receipts are ignored.

### Scope and approval prerequisites for one live repetition

Do not execute the following block until the owner separately approves live
database tests, the reviewed diff and these persistent fixture effects. Use a
private interactive Windows PowerShell console with the existing virtualenv and
Git/NetTCPIP cmdlets available. Do not use a transcript, console recording, Tee,
redirection or a pipe around the Python invocation. Never paste a password into
command text. The environment credential path is deliberately refused below;
the runner requests the existing merge_app password through getpass. Its fallback
warning is made fatal so unavailable hidden input cannot silently echo a secret.
This warning policy was tested offline without opening a connection or prompting.

The already-provisioned target must be 127.0.0.1:5432 / merge_test / merge_app at
exact 0005_invitations. No setup/migration/cleanup is part of this proposal.
The target settings do not load application Settings or merge_dev defaults. The
initial preflight is read-only; lifecycle fixture, pooled, fresh and observer
connections additionally use ConnectionGuard for exact identity/revision, actual
and default READ COMMITTED, DBAPI autocommit off and 5s lock / 15s statement
timeouts. Guard inspection is rolled back before fixture work. Retries bound
timeouts further to the remaining transaction budget. Role-name verification is
not a complete role-attribute or database-DDL drift audit.

Reserve a quiet test window: no other test runner, browser/app host, migration,
administrative writer or outbox dispatcher. The port check below is only a local
listener check; it cannot establish the absence of database writers elsewhere.
The suite does not acquire a database-wide exclusive lock. Retained data may be
present: each case uses its own fresh UUID4 hackathon and accounts, not an empty
database or the old browser scopes. Concurrent unrelated scopes are isolated by
IDs, but clean certification requires avoiding uncontrolled test/load activity.

One successful repetition retains ten hackathons (m019a_<full fresh UUID hex>),
31 accounts/credentials and sessions (admit_<24 fresh UUID hex> usernames), eleven
teams, thirteen invitations and one join request. Memberships, tombstones,
idempotency, audit/outbox rows and invitation throttle charges also persist;
race winners affect the final row counts. Fixture passwords/session material
are generated privately in memory, never added to reports. The case which injects
an outbox failure must roll back the attempted departure, not its earlier setup.
No reset, DROP, fixture deletion or old manifest/budget reuse is supported here.
The teardown certifies its fresh scopes; it does not fingerprint every prior row.

### Owner-only PowerShell execution and certification proposal

Review/freeze the entire working diff before running this block. It refuses the
wrong HEAD, ambient test credential and common running service ports, hashes the
reviewable source before/after, and identifies a new report by set difference
rather than selecting the latest retained report. The separate metadata receipt
contains no credentials and records the native exit code even when certification
fails. It is a new ignored artifact and never overwrites earlier evidence.

```powershell
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'I:\Merge\backend'
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}
if (-not (Test-Path -LiteralPath '.\.venv\Scripts\python.exe' -PathType Leaf)) {
    throw 'Existing backend virtualenv required; do not install or start anything.'
}
$lifecycleHead = & git -c safe.directory=I:/Merge rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $lifecycleHead -ne '14e64cb2315fd4301b0fe4dfa908298b25bcce90') {
    throw 'Unexpected Git baseline; stop for review.'
}
if (Test-Path Env:\MERGE_TEST_DB_PASSWORD) {
    throw 'Ambient test credential present; review privately before proceeding.'
}
$lifecycleListeners = @(Get-NetTCPConnection -State Listen -ErrorAction Stop |
    Where-Object { $_.LocalPort -in 8000, 5173, 8100 })
if ($lifecycleListeners.Count -ne 0) {
    throw 'Service listener found; this block never stops processes.'
}
function Get-LifecycleSourceHashes {
    $paths = @(& git -C 'I:\Merge' -c safe.directory=I:/Merge ls-files --cached --others --exclude-standard -- backend frontend docs AGENTS.md .gitignore)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inventory reviewed source.' }
    @($paths | Sort-Object -Unique | ForEach-Object {
        $digest = Get-FileHash -LiteralPath (Join-Path 'I:\Merge' $_) -Algorithm SHA256
        '{0} {1}' -f $_, $digest.Hash
    })
}
$lifecycleSourceBefore = @(Get-LifecycleSourceHashes)
$lifecycleReportDirectory = 'I:\Merge\backend\test-results\guarded'
$lifecycleReportsBefore = @()
if (Test-Path -LiteralPath $lifecycleReportDirectory) {
    $lifecycleReportsBefore = @(Get-ChildItem -LiteralPath $lifecycleReportDirectory -Filter 'run-*.json' -File |
        Select-Object -ExpandProperty Name)
}

# First database access is inside this separately approved guarded command.
& .\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m test_support.concurrency --confirm-merge-test --suite lifecycle --revision 0005_invitations --repetitions 1
$lifecycleExit = $LASTEXITCODE

$lifecycleNewReports = @(Get-ChildItem -LiteralPath $lifecycleReportDirectory -Filter 'run-*.json' -File |
    Where-Object { $_.Name -notin $lifecycleReportsBefore })
if ($lifecycleNewReports.Count -ne 1) {
    throw "NOT CERTIFIED: exit=$lifecycleExit; expected exactly one new report. Preserve all evidence."
}
$lifecycleReportFile = $lifecycleNewReports[0]
$lifecycleSourceAfter = @(Get-LifecycleSourceHashes)
$lifecycleSourceStable = @(Compare-Object $lifecycleSourceBefore $lifecycleSourceAfter).Count -eq 0
$lifecycleReceipt = [ordered]@{
    schema_version = 1
    captured_utc = [DateTime]::UtcNow.ToString('o')
    head = $lifecycleHead
    report = $lifecycleReportFile.Name
    native_exit_code = $lifecycleExit
    reviewed_source_unchanged_during_run = $lifecycleSourceStable
    source_sha256 = $lifecycleSourceBefore
}
$lifecycleReceiptPath = Join-Path $lifecycleReportDirectory ('owner-' + [Guid]::NewGuid().ToString('N') + '.json')
$lifecycleReceiptStream = [IO.File]::Open($lifecycleReceiptPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
try {
    $lifecycleReceiptBytes = [Text.Encoding]::UTF8.GetBytes(($lifecycleReceipt | ConvertTo-Json -Depth 4))
    $lifecycleReceiptStream.Write($lifecycleReceiptBytes, 0, $lifecycleReceiptBytes.Length)
} finally { $lifecycleReceiptStream.Dispose() }
Write-Host ('Native exit: {0}; report: {1}; owner receipt: {2}' -f $lifecycleExit, $lifecycleReportFile.FullName, $lifecycleReceiptPath)
$lifecycleReport = Get-Content -LiteralPath $lifecycleReportFile.FullName -Raw | ConvertFrom-Json
$lifecycleRequiredFields = @('schema_version','suite','revision','repetitions','status','exit_code',
    'stage','invariant_verification','collected','teardowns_completed','skipped','failures','active_node')
foreach ($field in $lifecycleRequiredFields) {
    if ($field -notin $lifecycleReport.PSObject.Properties.Name) { throw 'NOT CERTIFIED: incomplete report.' }
}
if ($lifecycleExit -ne 0 -or -not $lifecycleSourceStable -or
    $lifecycleReport.schema_version -cne 1 -or $lifecycleReport.suite -cne 'lifecycle' -or
    $lifecycleReport.revision -cne '0005_invitations' -or $lifecycleReport.repetitions -cne 1 -or
    $lifecycleReport.status -cne 'passed' -or $lifecycleReport.exit_code -cne 0 -or
    $lifecycleReport.stage -cne 'pytest' -or $lifecycleReport.collected -cne 10 -or
    $lifecycleReport.teardowns_completed -cne 10 -or $lifecycleReport.skipped -cne 0 -or
    $null -eq $lifecycleReport.failures -or @($lifecycleReport.failures).Count -ne 0 -or
    $null -ne $lifecycleReport.active_node -or
    $lifecycleReport.invariant_verification -cne 'suite_and_fixture_checks_completed') {
    throw 'NOT CERTIFIED: preserve report/receipt and retained fixtures; do not retry or clean automatically.'
}
Write-Host 'One lifecycle repetition certified; fixtures retained. Stop for owner review.'
```

The block remains a future-execution proposal, not authorization for another run.
The accepted result and its separate provenance limits are recorded above; the
proposal does not prove which wrapper was used for that result. If a future run
is interrupted before the owner receipt is written, retain its report and classify
it as uncertified until separately reviewed. Do not infer success from
an absent process/listener, a teardown message, an old report or exit 0 alone.
No automatic rerun, additional repetition, G1 rerun or browser action is approved.

Coverage limits: ten cases cover required departures/removal/succession, same-key
contention, admission/invitation interactions and transactional outbox rollback.
Only the simultaneous-departure case requires observed rooted PostgreSQL waiters;
the other races do not force every serial outcome. Real COMMIT transport loss and
every deferred-failure schedule remain untested by this live suite (offline retry
tests cover their logic). This is neither a new 50-caller G1 run nor real-browser,
TLS, load or deployment evidence. Keep the prior G1/M-017 evidence unchanged.

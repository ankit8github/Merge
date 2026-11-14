# M-020A realtime invalidation contract

Design recorded before implementation on 2026-11-14. The owner's M-020A request
authorizes this bounded additive SSE API and React subscription. No schema,
mutation/lock protocol, session model, dependency or test-target guard changes.

## API and privacy

GET /api/hackathons/{hackathon_id}/events requires the existing validated cookie
session and unchanged AuthBoundary Origin/Fetch Metadata/HTTPS/proxy policy. No
query parameters or actor selectors. Last-Event-ID, when present, must be one
64-character lowercase hexadecimal fingerprint. It is a hint, never authority.
An existing hackathon has the same authenticated discovery boundary as its board;
team membership is not required to see public board changes. Unknown scope is 404.

Frames are reset or invalidate, with an id fingerprint and JSON containing only
schema_version=1, hackathon_id and the authenticated user_id. No audit/outbox
payload, team/member/request/invitation IDs, private fields, counts, keys or tokens
are exposed. Public membership/leadership/deletion changes invalidate everyone in
that hackathon. Private request changes invalidate only their requester/current
live-team leader; private invitation issuance only its recipient. Authorization
is recomputed from current rows each poll. Revocation/expiry or identity mismatch
terminates the stream with an expired signal; unavailable storage terminates with
an unavailable signal. No exception/SQL detail crosses the stream boundary.

## Commit visibility and reconnect

Each sample counts retained outbox rows joined to their audit records under one
READ COMMITTED statement, filtered by hackathon and current subscriber visibility.
Only committed rows are visible. Hash the actor, hackathon and separate public/
private counts into a bounded fingerprint: loss of private visibility cannot
cancel an increase in the public count. Outbox/audit retention makes public counts monotonic;
private visibility can change with leadership and must also invalidate. Counts
avoid a commit-order bug in UUID/timestamp/high-water cursors: a late commit adds
to the next count even if its ID/timestamp precedes previously visible records.

Every connection emits reset, even when Last-Event-ID matches, then emits an
invalidate when the fingerprint changes. There is no event-history replay or
exactly-once claim: duplicates, dropped events, server replacement and any gap are
repaired by a fresh canonical read. A client deduplicates identical invalidations
within a connection but always refetches on reset. The fingerprint is not saved
in browser storage and cannot authorize access. No mutation is replayed by SSE.

## Resource and deployment bounds

Poll every two seconds with a nominal sixty-second renewal lease. In-flight
database work can extend wall time under existing connection/query deadlines.
Network sends have a ten-second deadline so stalled clients release their slot. Each
poll revalidates the original session and runs a separate bounded read-only sample.
All connections/transactions close before yielding or waiting. Sync database work
runs in the existing worker thread pool, never on the async event loop. A cancelled
in-flight sync query finishes under database deadlines, then releases resources.
No per-subscriber event queue, background dispatcher or persistent DB connection.
Fixed per-process limits: 64 subscriptions total, two per authenticated account;
429 with Retry-After when full. Heartbeats and SSE retry hints keep idle streams
observable. Frontend reconnect uses bounded exponential backoff and closes the
old EventSource before retrying; connection errors probe the current session to
avoid indefinitely retaining an expired/replaced account.

Initial deployment remains one backend instance. Independent workers/instances
can observe the same durable primary database through polling without sticky
sessions or a process-local fanout broker; reconnect resets survive worker changes.
This is eventual invalidation, not ordered per-event multi-instance delivery.
No multi-instance/load/proxy behavior is claimed verified. Per-subscriber COUNT
queries over retained history are a deliberate initial cost; large histories,
polling load, pool budgets and horizontal scaling require measurements before
capacity claims. No migration/index optimization is assumed or silently added.
Configure deployment proxies to disable SSE buffering/compression, preserve the
existing trusted identity/Origin boundary and allow the stream lease plus margin.
Outbox published_at and attempt_count are never changed by this read path.

## Frontend and acceptance

Subscribe only after current-identity discovery restoration successfully verifies
the active hackathon. A workspace/session change closes the source, aborts probes,
clears reconnect timers and fences old callbacks during layout cleanup, before
the new workspace's layout effects; actual connection setup remains passive.
Reset/invalidate refetch current
membership, board/detail and visible private reads without remounting command
forms or replaying journals. Keep pagination and navigation hints independent;
show existing stale-cursor recovery rather than silently switching pages. Refresh
must not discard confirmation/input or rotate mutation workspace ownership.

Required offline checks: auth/Origin/query/cursor failures, actor/hackathon privacy,
owned read-only connection lifecycle, committed/rollback sample model, late-commit
reconnect behavior, removal/deletion, cancellation/caps/storage errors, browser
reset/duplicate/backoff/session/workspace ownership and stale canonical responses.
Real PostgreSQL commit visibility, live browser/mobile/keyboard, proxy buffering,
HTTPS and load remain separate approval/verification gates. Old browser manifests
and test hosts gain no new permissions; no live command is authorized here.

## Proposed owner-only guarded PostgreSQL acceptance

Offline checkpoint: final backend 1494 passed / 32 database deselected; focused
SSE 30 passed; frontend 365 passed / 13 files; TypeScript/production build passed
(48 modules, 5.42s); pip check passed. Four guarded cases collected in 0.06s, not
executed. Existing Starlette/HTTPX deprecation warning remains. Exact commands
and honest red/fix history: PROGRESS.md / M-020A. The owner block passed syntax
parsing only; its metadata guard accepted a valid synthetic report and rejected
eighteen failure cases without executing a launcher/prompt/database command.

Use the unchanged same-origin Vite /api proxy for later approved local browser
work; configure the backend Origin to the exact browser origin. No proxy header,
Origin or CSRF bypass is introduced. HTTPS/trusted-proxy settings remain the
existing deployment contract and still need live verification.

NOT EXECUTED. Only after separate approval of this reviewed working tree and
persistent effects, use a private interactive Windows PowerShell console. Keep
all app/browser hosts, other test runners, migrations and outbox dispatchers out
of the test window. Do not pipe, transcribe, record or redirect the credential
prompt. No dependency installation, server startup, fixture preparation, migration,
cleanup or old manifest is part of this command.

Target remains 127.0.0.1:5432 / merge_test / merge_app / exact 0005_invitations.
The fixed suite reuses unchanged lifecycle connection/retention guards. One full
successful repetition retains five fresh m020a_<UUID hex> hackathons, twelve
fresh admit_<random UUID prefix> accounts/credentials/sessions, five teams, one
join request, one invitation and associated membership/tombstone/idempotency/
audit/outbox/throttle effects. Fixture passwords are generated privately in memory.
One tested departure rolls back; the other setup/success effects remain retained.
This is four database cases, not a new G1 race or browser/transport certification.

The wrapper below captures a new report and native exit immediately, preserves a
source-hash receipt in the ignored report directory, and rejects scope drift or
incomplete certification. It is a proposal for later review, never permission to
execute now. If interrupted or unsuccessful, preserve all partial effects/reports;
do not automatically rerun or clean. The local port check cannot establish that no
other database writer exists; the quiet window is an explicit owner prerequisite.

```powershell
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'I:\Merge\backend'
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) { $PSNativeCommandUseErrorActionPreference = $false }
$realtimeHead = & git -c safe.directory=I:/Merge rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $realtimeHead -ne 'abfea1a6116dbe0295b45d21e290c56f84a91eb5') { throw 'Review the changed baseline first.' }
if (Test-Path Env:\MERGE_TEST_DB_PASSWORD) { throw 'Review ambient credentials privately; this proposal requires hidden input.' }
if (@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { $_.LocalPort -in 8000,5173,8100 }).Count) { throw 'Service listener found; no process is stopped by this block.' }
function Get-RealtimeSourceHashes {
    $paths = @(& git -C 'I:\Merge' -c safe.directory=I:/Merge ls-files --cached --others --exclude-standard -- backend frontend docs AGENTS.md .gitignore)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inventory source.' }
    @($paths | Sort-Object -Unique | ForEach-Object {
        $digest = Get-FileHash -LiteralPath (Join-Path 'I:\Merge' $_) -Algorithm SHA256
        '{0} {1}' -f $_,$digest.Hash
    })
}
$realtimeSourceBefore = @(Get-RealtimeSourceHashes)
$realtimeDirectory = 'I:\Merge\backend\test-results\guarded'
$realtimeBefore = @()
if (Test-Path -LiteralPath $realtimeDirectory) { $realtimeBefore = @(Get-ChildItem -LiteralPath $realtimeDirectory -Filter 'run-*.json' -File | Select-Object -ExpandProperty Name) }

& .\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m test_support.concurrency --confirm-merge-test --suite realtime --revision 0005_invitations --repetitions 1
$realtimeExit = $LASTEXITCODE

$realtimeNew = @(Get-ChildItem -LiteralPath $realtimeDirectory -Filter 'run-*.json' -File | Where-Object { $_.Name -notin $realtimeBefore })
if ($realtimeNew.Count -ne 1) { throw "NOT CERTIFIED: exit=$realtimeExit; require exactly one new report." }
$realtimeFile = $realtimeNew[0]
$realtimeSourceAfter = @(Get-RealtimeSourceHashes)
$realtimeStable = @(Compare-Object $realtimeSourceBefore $realtimeSourceAfter).Count -eq 0
$realtimeReceipt = [ordered]@{
    schema_version = 1
    captured_utc = [DateTime]::UtcNow.ToString('o')
    baseline_head = $realtimeHead
    report = $realtimeFile.Name
    report_sha256 = (Get-FileHash -LiteralPath $realtimeFile.FullName -Algorithm SHA256).Hash
    native_exit_code = $realtimeExit
    source_unchanged_during_run = $realtimeStable
    source_sha256 = $realtimeSourceBefore
}
$realtimeReceiptPath = Join-Path $realtimeDirectory ('owner-' + [Guid]::NewGuid().ToString('N') + '.json')
$realtimeReceiptStream = [IO.File]::Open($realtimeReceiptPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
try {
    $realtimeReceiptBytes = [Text.Encoding]::UTF8.GetBytes(($realtimeReceipt | ConvertTo-Json -Depth 4))
    $realtimeReceiptStream.Write($realtimeReceiptBytes,0,$realtimeReceiptBytes.Length)
} finally { $realtimeReceiptStream.Dispose() }
Write-Host ('Native exit={0}; report={1}; receipt={2}' -f $realtimeExit,$realtimeFile.FullName,$realtimeReceiptPath)
$realtimeReport = Get-Content -LiteralPath $realtimeFile.FullName -Raw | ConvertFrom-Json
$realtimeFields = @('schema_version','suite','revision','repetitions','status','exit_code','stage','collected','teardowns_completed','skipped','failures','active_node','invariant_verification')
foreach ($field in $realtimeFields) { if ($field -notin $realtimeReport.PSObject.Properties.Name) { throw 'NOT CERTIFIED: incomplete report.' } }
if ($realtimeExit -ne 0 -or -not $realtimeStable -or
    $realtimeReport.schema_version -cne 1 -or $realtimeReport.suite -cne 'realtime' -or
    $realtimeReport.revision -cne '0005_invitations' -or $realtimeReport.repetitions -cne 1 -or
    $realtimeReport.status -cne 'passed' -or $realtimeReport.exit_code -cne 0 -or $realtimeReport.stage -cne 'pytest' -or
    $realtimeReport.collected -cne 4 -or $realtimeReport.teardowns_completed -cne 4 -or $realtimeReport.skipped -cne 0 -or
    $null -eq $realtimeReport.failures -or @($realtimeReport.failures).Count -ne 0 -or $null -ne $realtimeReport.active_node -or
    $realtimeReport.invariant_verification -cne 'suite_and_fixture_checks_completed') {
    throw 'NOT CERTIFIED: preserve evidence/fixtures; stop before any retry.'
}
Write-Host 'One realtime database repetition certified; retain fixtures and stop for review.'
```

This proposal preserves hidden native I/O and makes getpass echo-fallback warnings
fatal. The schema has no migrations or broker setup to run. Independent browser
SSE/proxy validation needs a separately reviewed fresh host/scope; old hosts exclude
the SSE router before their unchanged route/dependency audits. The added CLI choice
and exact-revision rejection do not change any target/role/driver/isolation,
AUTOCOMMIT, timeout, fixture-retention, diagnostic or old-suite restrictions.

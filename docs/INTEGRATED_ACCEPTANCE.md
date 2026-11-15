# Final integrated acceptance preparation — 2026-11-14

**Follow-up infrastructure, 2026-11-14:** the separate exact0006 host, server
ledger, native read-only observer and evidence verifier are now implemented and
offline tested in [INTEGRATED_HOST.md](INTEGRATED_HOST.md). Its new owner commands
supersede the missing-host blocker below; all database/browser stages still need
separate approval and real evidence. The public campaign/budget is unchanged.
The preparation checkpoint, tests and limitations below remain historical evidence.

**Decision: profile execution is CONDITIONAL for separate owner approval;
integrated browser execution is BLOCKED. No live acceptance was run.**

The starting branch is main, actual HEAD
`db17f3ef2c2934d2d4cc7db06499a291949a3d16`, matching the supplied baseline.
The twelve existing product-audit paths were present, unstaged. They are preserved;
only PROGRESS receives an additive entry. This preparation changes no application,
database, migration, dependency, old acceptance condition, manifest or fixture.

## Component and dependencies

This component prepares a public, uniquely scoped campaign, offline assertion and
receipt contracts, and owner execution gates. Sources: REQUIREMENTS R-01–13/R-17,
ARCHITECTURE Batch A/B and M-019/020, DECISIONS matching/lifecycle/realtime ADRs,
current PROGRESS, RELEASE_VALIDATION, RANKING, and the actual guarded hosts.

New files: acceptance/integrated-campaign.json;
backend/release_support/integrated_plan.py; backend/tests/test_integrated_plan.py;
frontend/test_support/integratedCampaign.js and integratedCampaign.test.js;
this document. PROGRESS is the sole edited tracked file in this task.
Acceptance: fail closed on altered target/revision/scope/budgets; expose the real
legacy route gap; reject failed/stale/partial receipt metadata; rehearse exact
command routing, retries, ranking and terminal state without network operations.
Existing PostgreSQL/driver/session/CSRF/transactions remain authoritative.

These are preparation tests and browser assertion helpers, **not an automated
end-to-end browser runner**. The local rehearsal budget grants no live authority.
No integrated host/ledger/database final observer has been implemented. Do not
start ordinary app.serve, app.main, Vite, or either old guarded host to work around
this gate. A separate bounded implementation/review must supply that host before
the browser steps below can run. This is an explicit remaining release blocker.

## A. Exact profile preflight

Source review supports the following ordered proposal; actual PostgreSQL identity,
privileges, schema, rows and current migration state are **unknown**, not verified.
The reported unapplied 0006 is retained as the baseline. No database was queried.

| Stage | Exact contract reviewed | Decision / failure behavior |
| --- | --- | --- |
| Provision SQL | scripts/provision_merge_profile_test.sql: postgres on actual 127.0.0.1:5432/postgres; existing LOGIN merge_app without elevated flags or role memberships; existing target forbidden | Create merge_profile_test OWNER merge_app from template0; revoke PUBLIC database/schema privileges; grant schema USAGE/CREATE only to merge_app. No role/password alteration, DROP, DELETE, reset, adoption, merge_test or merge_dev access. |
| Provision atomicity | psql -X, ON_ERROR_STOP, -W; CREATE DATABASE outside a transaction; post-connect identity rechecked | **Not wholly atomic.** Creation/grant/connection failure can retain a partial new target. Stop; never rerun or remove it automatically. Quiet owner-controlled window; simultaneous provisioning is prohibited. |
| Prepare | release_support.migrations prepare --target profiles --confirm-target merge_profile_test | Guard expects no version table/revision. Public relation/function count must be zero before exact upgrade to 0005_invitations. This check is not a complete arbitrary-type/ACL inventory; template0/new-target provenance is required. No retained database preparation. |
| Upgrade | same wrapper, action migrate | Exact one-row 0005 only. Caller owns transaction and SHARE locks/fingerprints all 12 existing application tables, including invitations, before/after DDL. Equality required before commit. Counts only enter report. No row backfill/update/delete. Ordinary failure rolls back; uncertain COMMIT requires separately approved read-only inspection. |
| 0006 SQL | backend/alembic/versions/0006_profiles.py, parent 0005_invitations | Reject existing participant_profiles relation/type; create only optional profile table, PK/user FK/four checks, defaults empty/private/version1. Downgrade refuses. SQL checks zone shape; app validates IANA membership. No grant or existing-table change. |
| Verify | same wrapper, action verify | Actual fixed database/role/server/port/revision; synchronous psycopg PostgreSQL, READ COMMITTED, non-autocommit, lock5s/statement15s on every logical engine connection, including pooled reuse. Elevated role flags/memberships rejected. No dotenv/Settings/URL override. |
| Accept | release_support.acceptance --confirm-profile-test | Exact0006 fixed profiles target; exactly30 unique safe collected IDs, exactly30 passed call IDs and completed teardowns; no skip/failure/active node; one repetition; invariant marker and exit0. A bare pytest live run cannot provide the required configured target. |

Review of all30 cases: default/normalized own profile and CAS conflict (1), invalid
fields (8), session/CSRF/Origin/actor/extra-body boundaries (5), stable ties/opt-out
(1), exact formula/empty skills (1), leader/foreign/deleted permissions (1),
membership/lifecycle/SSE composition (1), other-workspace/full-team eligibility
(1), snapshot cursor (1), bounded query validation (4), simultaneous CAS (1), real
array constraints (3), uncommitted invisibility/rollback (1), schema/FK (1).
Total30. Collection alone executes none of these fixtures or SQL statements.

The suite retains approximately120 fresh accounts/credentials/sessions,
31 hackathons and31 teams (including a tombstone), profile edits, grants,
memberships, idempotency/audit/outbox and throttle effects. No cleanup. Globally
opted-in older candidates remain visible; pagination must find fresh IDs without
filtering or deleting prior candidates. Pool-limit failures stop the run.
This is profile SQL/CAS acceptance, not a new G1 or SSE certificate.

## B. Proposed fresh browser scope

Public plan: [integrated-campaign.json](../acceptance/integrated-campaign.json).
Run ID: `17ff1152-1ac0-4ace-a887-13436dd2963f`.
H1: `69ec4040-6fc3-4d10-a3ab-92094b8affa4`.
H2: `71b4fa24-4b3c-4d96-ab36-f2cfed8c6aeb`.
Username prefix: `ia_17ff11521ac04acea8871343_`, roles l/q/r/x.
These are new planned identifiers, not evidence of database freshness. A future
guarded preflight must refuse any existing username/scope row; no interrupted
scope can be adopted or resumed. Preserve all prior manifests and fixture rows.
User/team/request/invitation IDs must bind from real server replies, never caller
chosen UUIDs. New private passwords stay in owner memory/private browser contexts.

| Fixture / effect | Exact proposal |
| --- | --- |
| Accounts | 4; one registration each; login l twice, q/r/x once; logout x once |
| Sessions | 5 total newly issued, 1 revoked; closing a context does not revoke a session |
| Workspaces | 2 new hackathons, min2/max3; A in H1 by l; B in H2 by q |
| Profiles | 4 rows, 5 successful saves; l version2, others version1 |
| Requests / grants | 2 join requests (q approved, r rejected); 2 recipient-bound invitations (r and later q), both redeemed |
| Membership end state | A tombstone/no leader/no memberships; B live, q leader and sole member |
| Successful domain commands | 14, exactly14 completed idempotency records,14 audit and14 outbox rows; A versions1–13, B version1 |

Transport ceiling **38 POSTs** =10 auth +7 profile +18 domain +3 security.
The closed plan gives each command its actor, maximum attempts, expected effect
and status. All commands have one attempt except create_a (two exact attempts,
one effect). No replenishment/retry on a failed checkpoint. No spare mutation
allowance for screenshots, mobile repeats, Cancel, navigation or cleanup.
The command status contract records actual server outcomes: create_a has two201
server replies while the browser observes a lost first acknowledgement, then201
on explicit retry. Preserve that distinction in checkpoint evidence. Each
distinct command requires its own key; final_q cannot reuse leave_q's old receipt.
Registration/login keep the real five-per-window registration and normal login
limits; four registrations fit. Unexpected auth failures consume their attempts
and stop; never relax throttling or restart with a new secret to bypass it.

Four separate cookie contexts are required initially. Two tabs in one context
share a cookie and do not demonstrate account isolation. Open an extra l tab only
for the stale-profile read, keeping the application's two-SSE-per-account cap.
After logout x, that context may sign in as l once, within the declared budget.
Do not keep an extra l workspace subscription open. Record actual browser/version,
OS, private-context identities, reference date and both viewport dimensions.

### Ordered checkpoints — all PLANNED

| Step / coverage | Actions and exact expected acceptance |
| --- | --- |
| 1 auth / keyboard | At1280x800, register and sign in l/q/r/x with keyboard. Four201 registrations, four200 logins; registration itself issues no session. Invalid local blank input must focus its field and emit no POST. Restore session by GET/focus, without credentials in storage/logs. |
| 2 profiles | Save the four exact initial bodies in plan.profile_values. l python/UTC/private; q sql/UTC/discoverable; r python+sql/Asia/Kolkata/discoverable; x empty/UTC/private. Each initial version0 becomes1. Verify saved normalized values and labels. Profile save does not produce team audit/outbox. |
| 3 profile recovery | In a private l API context retain the observed version1. One diagnostic invalid timezone POST (profile_invalid, exactly422) leaves version1; then the UI saves an explicit valid unchanged-value edit with version1 ->2. The API context submits retained stale version1 once ->409 profile_changed; UI loads current2 before editing again. Invalid UI timezone input itself must focus the field and send no POST. Unknown profile delivery requires refetch, not original-key retry; this rule is verified offline. This budget does not inject another unknown profile save or claim browser certification of that failure mode. |
| 4 discovery / creation / retry | Discover and explicitly select H1/H2 by exact public ID and verify name. q creates B in H2 (create_b). l creates A in H1 (create_a), using the separately approved response gate to lose the single real201 acknowledgement. While uncertain, navigate H2/back/forward and return H1; no background POST. Explicit retry retains exact key/payload/actor/H1 and receives same201 receipt/team ID. Two attempts, one A/version1/audit/outbox. Never reload a pending memory-only command. |
| 5 explained ranking / eligibility | l finds teammates; paginate canonical results until q and r appear. No test-only filtering of older opted-in accounts. l/x absent. q remains eligible despite membership in H2. Team coverage python; q100.00 =70+30; r44.38 =35+9.375, novel skill sql, overlap150/480. Verify displayed component explanation/reference date and named selection; selection alone emits no POST. |
| 6 requests / leader decisions | q and r request A (request_q/request_r), each201. q attempts decision on r once (deny_decision) ->403, no committed effect. l rejects r once (reject_r) ->200 then approves q (approve_q) ->200. Names and persisted statuses must match; A roster l/q, count2. No optimistic membership from pending request. |
| 7 invitation / full eligibility | l selects r from ranking, creates invitation (issue_r) ->201. x attempts that recipient-bound grant once (deny_redeem) ->404 invitation_not_found, preserving recipient privacy. r sees named team inbox and confirms redemption once (redeem_r) ->200; A count3. Leader ranking has no eligible results while full. No code/token/cookie/CSRF capture or new guess/race load. |
| 8 member removal / mobile | Resize to390x844 **before** these same planned actions; no duplicate fixture actions. q attempts removal of r once ->403 (deny_remove). l opens removal confirmation, Cancel with keyboard returns focus/no POST, reopens and confirms remove_r once ->200. r loses roster/member controls and canonical membership; A count2, r eligible on explicit ranking refresh. No horizontal page overflow, clipped confirmation/actions or inaccessible focus. |
| 9 ordinary leave / readmission | q cancels then confirms leave_q once ->200; A count1/l leader; B in H2 unchanged. l issues issue_q ->201, q sees inbox then redeems (redeem_q) ->200; A l/q count2. Rejected request history for r and approved history for q remain historical, not proof of current membership. |
| 10 automatic succession | l confirms leave_l once ->200. q is the only remaining member, automatically leader, count1/version12. q gains leader controls; l loses private/leader content and is unassigned in H1. Do not add a manual transfer request or reuse an old leader command. |
| 11 final-member deletion | q confirms final_q once ->200; A version13 deleted, leader null/count0. A absent from board, detail unavailable, H1 membership empty for all. Preserve tombstone, audit/outbox/history. B remains q's live H2 team/version1. |
| 12 two-client SSE / recovery | Interleave observations during steps6–11: l/q isolated contexts subscribe H1; q sees A's canonical count/roster/leadership/deletion change after l's actions without Refresh; l sees q's leave/readmission/deletion. Record actual elapsed time with bounded15s waits; failure stops. Observe a normal60s lease/reconnect/reset causing canonical GET refetch without POST. Close irrelevant streams before account/workspace changes. This is browser transport coverage, not a rerun of the four PostgreSQL SSE schedules. |
| 13 account/workspace isolation | During step4 hold a permitted H1 board GET, change to H2, then release it within15s; H1 reply cannot replace H2. After final deletion leave an unsubmitted x draft; sign out x once and sign in l once in that context. Back/forward/focus restore must validate l; old x inbox/draft/private content and stale callbacks cannot populate l. No command is submitted in this account-switch step. Reload only after all commands are settled: restore public UUID navigation from fresh canonical reads, no automatic mutation or persisted pending command. |

All successful user commands use the real UI. Nonleader controls and another
recipient's grant are intentionally unavailable there: the three deny_* commands
and two profile error diagnostics use separately reviewed private API contexts.
They use the browser's managed session and a fresh session GET/CSRF in memory,
never log/copy credentials into scripts or artifacts, and count toward the same
38-POST ceiling. Do not claim those negative cases were clicked through hidden UI.

The JS helpers cover fixed command paths/bindings and local budgets, exact
ranking fixtures, and final scoped totals. They do not drive a browser, install a
fault, intercept authentication, capture headers or fetch anything. Browser
checkpoint evidence still needs actual reviewed observations/screenshots with
private material excluded. Testing keyboard actions and the390 viewport on these
same actions avoids spending additional mutation budget. Read-only revisits may
inspect responsive layout after the final state.

## C. Safety and future certification requirements

The current browser_full ENDPOINTS contains16 entries plus health; it requires
exact0005. Its closed dependency audit explicitly removes profile/ranking,
lifecycle and SSE routers. Seven required method/path entries are absent:
GET/POST /api/me/profile; GET suggestions; GET members; POST leave; POST member
remove; GET events. The older read-only host requires0003 and cannot substitute.
Offline tests prove reinserting any of these routers breaks the old audit.
**Never widen the old map, revision allowlist, manifest, budgets or certificate.**

A future independent host must fix merge_profile_test/merge_app/actual
127.0.0.1:5432/exact0006 before any service call or SQL mutation; bind API to
127.0.0.1:8000, frontend origin http://127.0.0.1:5173, one worker, no reload,
no trusted proxy or forwarded-header processing. All nine service dependency
factories (auth, reads, team, admission, invitations, lifecycle, profiles,
matching, realtime) must be explicitly overridden with guarded real services.
Audit exact route objects and the complete dependency graph at startup, each
request and shutdown; no fallback to ordinary Settings/merge_dev. Claim commands
before durable invitation throttles; latching unexpected failures closes host.
Check fresh identities/scopes before preparation; same-transaction additive
hackathon preparation; preserve all prior rows with independent final observer,
including older profiles and unrelated auth/throttle state allowed only as
documented. Snapshot/hash secrets in memory only, never raw row dumps.

The production AuthBoundary remains unchanged: exact Origin (mandatory on
mutations), same-origin/none Fetch Metadata only, strict JSON Content-Type,
X-Merge-Request:1 for register/login, real HttpOnly SameSite=Lax dev cookie and
current-session CSRF for protected POST. Supplied actor selectors grant nothing;
profile/ranking reject them. Session identity is server validated. SSE revalidates
sessions and guards query/actor/Last-Event-ID inputs, caps2/account/64/process.
Loopback HTTP does not certify production Secure __Host cookie/HTTPS/proxy behavior.
The no-merge_dev guarantee applies to the proposed acceptance entry points;
separate opt-in development tests still exist and are deselected here. Do not
replace the approved commands with general database-test or application startup.

Three explicit **future** no-effect API-context probes are budgeted: unauthenticated
profile POST ->401, authenticated without CSRF ->403, foreign Origin ->403. Use
the exact valid profile shape/current version, not a malformed body masking an
authorization defect. Browser JS cannot forge Origin; the foreign-Origin probe
requires a separately reviewed API request context with private managed auth,
never a copied bearer/token in source/logs. Stop if a probe succeeds. These do not
replace offline duplicate-Origin/Fetch Metadata/proxy/CSRF tests.

Receipt contract in integrated_plan.validate_receipt is a metadata consistency
review only. No live receipt is written by this preparation tool. Future run must
write unique CreateNew files in ignored test-results, before starting and after
every checkpoint, leaving failed/interrupted evidence intact. Bind full tracked
and nonignored source hashes (including this uncommitted product audit), exact
HEAD, public plan digest/run ID, actual server bindings, revision, environment,
browser/version/viewports, timestamps and evidence hashes. Record **native
host/browser/observer process exits** independently of reported status. Require
all0, all13 unique checkpoints passed, no skip/failure/active checkpoint,
unchanged sources, server-enforced38-POST ceiling, exact14-effect chain,
same-key creation replay, final scope and prior-row preservation, drained server.
Inspect each evidence artifact and host/observer source; a synthetic JSON that
fits the shape is not proof. Source-bound receipts are local integrity, not signed
independent provenance. No post-run source binding can be invented for old runs.

On unexpected denial, timeout, skipped checkpoint, stale hash, uncertain write,
budget overrun or process failure: stop immediately, close browser interaction,
drain owned services, record sanitized failure/native exits, retain partial rows,
private diagnostics and all prior evidence. No automatic rerun, new key, cleanup,
resume, fixture adoption, downgrade or old receipt edit. A separately reviewed
new scope/approval is needed after diagnosis. Existing G1/SSE/lifecycle certificates
retain their original scope and are not repeated or extended by this plan.

## D. Exact owner commands — proposals, NOT EXECUTED

First freeze/review this full diff plus the twelve preexisting paths. Profile
steps below require separate explicit owner approval; they do not authorize a
browser/service, merge_test migration, benchmark, remote operation or deployment.
Use an interactive private terminal; no transcript/piping of credential commands.
Do not set credentials in CLI/source or a retained script. Refuse ambient
MERGE_RELEASE_DB_PASSWORD (rather than silently adopting it). The reviewed
modules accept that variable; the command policy below deliberately requires the
hidden prompt. Their bare getpass calls do not themselves make GetPassWarning
fatal: **keep the -W flag on every Python live command**. The offline subprocess
test proves this flag stops fallback before input can echo.

```powershell
Set-Location -LiteralPath 'I:\Merge'
if (Test-Path Env:MERGE_RELEASE_DB_PASSWORD) { throw 'Use reviewed private hidden input; stop' }
if (Test-Path Env:PGPASSWORD) { throw 'Ambient psql credential present; stop for review' }
# APPROVAL 1: create-only provisioning; uses existing postgres/merge_app roles.
psql -X -h 127.0.0.1 -p 5432 -U postgres -d postgres -W -f scripts/provision_merge_profile_test.sql
$provisionNativeExit = $LASTEXITCODE
if ($provisionNativeExit -ne 0) { throw 'Provision incomplete; retain state and stop' }
```

Then individually approve each action and its source-bound receipt. Run no other
writer/validator/editor concurrently. Preparation/upgrade/verify use fixed
profiles only, not a changed environment database URL.

```powershell
Set-Location -LiteralPath 'I:\Merge\backend'
# APPROVAL 2: empty new target -> exact0005.
.\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m release_support.migrations prepare --target profiles --confirm-target merge_profile_test
$prepareNativeExit = $LASTEXITCODE
if ($prepareNativeExit -ne 0) { throw 'Prepare incomplete; stop' }
# APPROVAL 3: exact0005 -> exact0006 with old-row preservation in DDL transaction.
.\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m release_support.migrations migrate --target profiles --confirm-target merge_profile_test
$migrateNativeExit = $LASTEXITCODE
if ($migrateNativeExit -ne 0) { throw 'Upgrade incomplete/uncertain; stop' }
# APPROVAL 4: read-only target/revision/role verification.
.\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m release_support.migrations verify --target profiles --confirm-target merge_profile_test
$verifyNativeExit = $LASTEXITCODE
if ($verifyNativeExit -ne 0) { throw 'Target not verified; stop' }
# APPROVAL 5: exactly30 real PostgreSQL profile cases, fresh retained fixtures.
.\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m release_support.acceptance --confirm-profile-test
$profilesNativeExit = $LASTEXITCODE
if ($profilesNativeExit -ne 0) { throw 'Profile acceptance incomplete; preserve evidence and stop' }
```

After **each** process, record its saved native exit in a new ignored owner note,
the unique receipt filename/hash printed by that process, start/end UTC and the
reviewed source snapshot. Do this before the next dependent action. Native exit
capture above is separate from a report's own exit field; do not pipeline the
interactive process through Tee-Object. Receipt verifier commands are offline:

```powershell
# Replace only the unique basename printed by the approved process. Never reuse
# an old file; require exactly one fresh receipt for that action.
.\.venv\Scripts\python.exe -m release_support.verify test-results/release/migration-RECEIPT_ID.json
if ($LASTEXITCODE -ne 0) { throw 'Migration receipt uncertified; stop' }
.\.venv\Scripts\python.exe -m release_support.verify test-results/release/profiles-RECEIPT_ID.json
if ($LASTEXITCODE -ne 0) { throw 'Profile receipt uncertified; stop' }
```

Profiles require30 collected/passed unique nodes and30 teardowns, exact0006,
repetition1, zero skips/failures, active_node=null, stagepytest/statuspassed,
suite_and_fixture_checks_completed, report exit0, wrapper native0 and unchanged
source. Preparation/migration/verification receipts each require their exact
action/target; upgrade requires all12 old-table counts/preservation. Keep original
reports/receipts untouched. Wrapper failures before receipt creation still fail
the gate; retain the native failure rather than manufacturing a success receipt.

**Browser execution commands are intentionally unavailable:** no reviewed
exact0006 integrated host/ledger/certifier exists. Approval6 is a future separate
host implementation/review, followed by approval of fresh hackathon preparation,
loopback services, browser/API probes and the exact38-POST campaign. It cannot
be granted by passing an old --allow-browser-writes flag. Do not run earlier
G1/lifecycle/PostgreSQL SSE commands as part of this campaign.

Offline commands that require no live approval:

```powershell
Set-Location -LiteralPath 'I:\Merge\backend'
.\.venv\Scripts\python.exe -m release_support.integrated_plan validate
.\.venv\Scripts\python.exe -m release_support.integrated_plan readiness
# Expected native2/BLOCKED; never interpret this as successful execution readiness.
.\.venv\Scripts\python.exe -m pytest profile_tests --collect-only -q --confirm-profile-test
.\.venv\Scripts\python.exe -m pytest tests/test_integrated_plan.py tests/test_release_support.py tests/test_browser_full_harness.py tests/test_browser_harness.py -q --tb=short
Set-Location -LiteralPath 'I:\Merge\frontend'
node --check test_support/integratedCampaign.js
node --check test_support/integratedCampaign.test.js
npm.cmd test -- test_support/integratedCampaign.test.js test_support/browserFaults.test.js --reporter=dot --maxWorkers=1
Set-Location -LiteralPath 'I:\Merge'
git -c safe.directory=I:/Merge diff --check
```

## E. Offline evidence and inventory

Environment: Windows PowerShell, existing Python3.11.9 venv, Node22.15.0 /
npm10.9.2 and installed locked dependencies. Sandbox process setup failed before
startup; reviewed outside-sandbox commands used per-command Git safe.directory,
without a global config edit. In-process HTTP harness tests use fake services;
none opens a live server or PostgreSQL connection. No dependency installation.

| Working directory / exact command | Actual result |
| --- | --- |
| backend: `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short` | 1773 passed,32 deselected,93.28s, native0. Preceded final404 plan correction and one added mapping test; final focused result below covers those changes. No claim of a final1774 full run. |
| backend: `.\.venv\Scripts\python.exe -m pytest tests/test_integrated_plan.py tests/test_release_support.py tests/test_browser_full_harness.py tests/test_browser_harness.py -q --tb=short` | FINAL338 passed,26.31s,native0. Includes55 new campaign cases, live-operation traps, source/receipt/target/budget adversaries and fatal GetPassWarning subprocess. |
| backend: `.\.venv\Scripts\python.exe -m pytest profile_tests --collect-only -q --confirm-profile-test` | FINAL30 collected,0.07s,native0; fixtures/credentials/SQL not executed. |
| backend: `.\.venv\Scripts\python.exe -m release_support.integrated_plan validate` | native0, plan_valid_only,38-POST ceiling. Canonical plan SHA256 `068e7f46c6af89db3be855cf72cf91c932f7337c1fc339b77d2707b9477214b1`. |
| backend: `.\.venv\Scripts\python.exe -m release_support.integrated_plan readiness` | Expected native2/BLOCKED; fixed exact0006 target and seven absent old-host routes reported. This is a successful fail-closed preparation check, not execution readiness. |
| frontend: `node --check test_support/integratedCampaign.js` and `node --check test_support/integratedCampaign.test.js` | Both native0; no browser or JavaScript fetch execution. |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1` | FINAL418 passed/17 files,154.00s,native0; all408 existing cases plus10 new helper cases. No browser/server startup. |
| root: PowerShell Parser.ParseInput on every fenced powershell proposal block | 4 blocks parsed with0 syntax errors; none executed. |
| root: `git -c safe.directory=I:/Merge diff --check` plus new-file trailing-whitespace/final-newline scan | native0 / clean. Git emits existing LF/CRLF normalization warnings; no normalization was performed. |
| Production frontend build / live PostgreSQL / migration / browser / load / CI / deployment | NOT RUN in this task. Test-support is outside src; baseline build evidence retains its original scope. |

Retained new ignored logs/hash inventories:
`backend/test-results/integrated-preparation-7b891b737d99440eb9c9f091d98907f0/`.
Historical-hashes comparison checked733 preexisting backend/frontend evidence
files: all present/byte-identical. All12 initial pending paths matched their
starting hashes before the additive PROGRESS entry; final check permits only
that documented progress overlay. New synthetic guarded diagnostics generated
by offline launcher unit tests are not PostgreSQL certificates.

Failure history retained: initial wiring test1 failed/335 passed (missing inert
app-state sentinels in a static test; supplied without entering lifespan); then
336 passed, and final338 after two additional tests. The first Node test command
incorrectly invoked the existing Vitest fault suite: its extensionless import
failed, while the new nine Node cases passed. The corrected Vitest invocation
then exposed Vite's transformed URL being unsuitable for fs.readFileSync; use a
repository-relative path. A subsequent full run passed408 existing tests but the
new nine tests failed because their Node environment invoked shared window-based
setup. Removed the per-file environment override; retained normal repository
setup. One standalone PowerShell-quoted synthetic warning probe failed Python
syntax before input; the real subprocess unit test replaces that probe and passes
the actual -W policy without shell quoting. No assertion/timeouts/acceptance
conditions were disabled, and no failed run is labeled a pass. Source review
corrected the draft foreign-recipient expectation to the real privacy-preserving
404 rather than changing the API to match the draft.

Full final pending inventory:18 paths =10 tracked modifications +8 untracked
files, all unstaged; no deletion. Six new paths are from this task; PROGRESS is
the only tracked path edited here. Eleven other original pending paths remain
byte-identical; the original PROGRESS content is retained below its new entry.

```text
M  README.md
M  docs/PROGRESS.md
M  frontend/src/App.test.tsx
M  frontend/src/DiscoveryNavigation.test.tsx
M  frontend/src/api.ts
M  frontend/src/components/Admission.tsx
M  frontend/src/components/HealthStatus.tsx
M  frontend/src/components/Invitations.tsx
M  frontend/src/components/Lifecycle.tsx
M  frontend/src/components/Profile.tsx
?? acceptance/integrated-campaign.json
?? backend/release_support/integrated_plan.py
?? backend/tests/test_integrated_plan.py
?? docs/INTEGRATED_ACCEPTANCE.md
?? docs/PRODUCT_AUDIT.md
?? frontend/src/ProductAudit.test.tsx
?? frontend/test_support/integratedCampaign.js
?? frontend/test_support/integratedCampaign.test.js
```

## F. Release blockers and owner explanation

Blocking prerequisites: actual isolated provisioning/0006/profile30 success;
separate exact0006 guarded integrated host/ledger/certifier; then actual full
browser/keyboard/mobile/retry/SSE-transport observations. Public Actions including
50-way race, verified10k/2k seed and100-client p95<200ms measured load, production
HTTPS/proxy/session/security validation, deployment/live URL and final submission
artifacts still require their own evidence. Nothing here certifies those gates.

The owner should explain that revision awareness does not grant execution
permission:0006 SQL can exist while the old0005 host correctly refuses it.
The new public plan describes38 attempts; only a reviewed server ledger could
enforce them. Exercise: change create_a's synthetic retry key or receipt's
effects to2 and run the new offline tests; explain why one team/audit effect must
remain1. Restore the edit; never use retained fixtures for the exercise.

STOP for owner review. No PostgreSQL connection, migration/provisioning execution,
server/browser startup, fixture deletion, historical evidence modification,
Git staging/commit/push, deployment or remote action is authorized by this document.

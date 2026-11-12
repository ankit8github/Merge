# Merge browser acceptance readiness

## M-015B - implemented exact-0005 host, offline review only, 2026-11-11

Implemented separately in `backend/test_support/browser_full.py`,
`browser_full_scope.py`, `browser_full_state.py` and offline harness tests.
The legacy 0003 browser host and production code remain unchanged. The supported
commands below are **not executed** and require separate owner live approval.
0005 is already applied: no migrations/reset/cleanup or merge_dev access.
The M-015A proposal below is historical and superseded by this bounded contract.

### Implemented safety and fixture contract

- Fixed 127.0.0.1:8000 / origin http://127.0.0.1:5173; single worker, no reload,
  proxy trust, access/SQL/error detail logs or ambient Settings/credential fallback.
  Hidden interactive role-password entry refuses echo fallback. Argument errors
  suppress values; unexpected failures print only fixed diagnostic categories.
- Every initial/new/pooled/observer engine connection rechecks exact merge_test /
  merge_app / 127.0.0.1:5432 / 0005, synchronous psycopg, real DBAPI autocommit false,
  no inherited/nested transaction, actual/default READ COMMITTED and 5s/15s timeouts.
  Guard SQL is read-only and rolled back; real services retain sole transaction
  ownership. A failed checkout or wiring audit latches the host closed.
- All five service dependencies are overridden with real guarded services behind
  scope facades. Exact route/dependency identities are audited before requests,
  including health, and at startup/shutdown. Ordinary runtime engines stay unset.
  Original cookie/CSRF/Origin/Fetch Metadata/throttle/strict JSON/idempotency and
  current-leader/recipient authorization still execute. There is no public join.
- `prepare` alone inserts exactly two fresh retained hackathons, min2/max3, in
  one owned transaction after freshness checks; all prior row fingerprints must
  remain unchanged and no other new row may appear before commit. An independent
  fresh observer checks prepared state after commit. Any ambiguous commit/final
  failure stops, retaining rows; it must not be retried blindly.
- Four approved fresh usernames use `m015b_<first 8 run UUID hex>_<l|q|r|x>`.
  Registration happens through the real UI and binds server-returned UUIDs.
  Known preexisting accounts are not adopted; login before a confirmed registration
  binding is refused. No account password, token, CSRF or hash enters the manifest.
  The preparer creates no account, session, team or membership.
- Domain attempt budgets are separate from registration/login/logout budgets.
  Every declared command has one frozen key/body/actor/scope in the host ledger;
  a changed key or command is refused before the real mutation. Retries remain
  explicit and retain current browser-session CSRF. Invitation attempt budgets
  are checked before the separately committing real durable invitation throttle.
- Only H-A (first manifest hackathon) permits domain writes. H-B is for empty-state
  navigation. Catalog GETs remain canonical and may show other retained public
  fixtures; other hackathons/teams cannot be selected through scoped service calls.
  Only teams/requests/invitations bound from real successful results may be used.

The required journey is create A as L -> Q/R request A -> L approves Q and rejects
R -> L issues R/X invitations -> R redeems -> X gets full conflict -> X creates B.
Both teams are in H-A. X's redemption is refused by the harness until approval Q
and redemption R are confirmed, preventing an early accidental admission; B's
creation requires the observed real team_full conflict first. The backend still
owns all actual membership/capacity/authority decisions. Main command budgets:

| Command | Actor and exact command |
|---|---|
| create_a / create_b | L/X; declared team_a/team_b name, H-A |
| request_q / request_r | Q/R create own request for A |
| approve_q / reject_r | L decides the server-bound Q/R request with approve/reject |
| issue_r / issue_x | L issues for the bound R/X account, team A |
| redeem_r / redeem_x | R/X redeems its own bound grant, team A |
| deny_issue_q / deny_decide_q / deny_redeem_x | Optional explicitly budgeted negative calls: Q issues to R, Q approves own request, X redeems R's grant. Real services must deny them |

Budgets count admitted HTTP/service attempts, including failures and replays; no
refunds or automatic retries. Each command allows 0-3 attempts; registration 0-1,
login/logout 0-4 per account. Original throttle limits remain unchanged. This small
plan does not naturally exhaust auth throttles; 429 acceptance needs separately
reviewed scope. An unexpected successful negative/full-denial command latches
failure; retain the effects and stop. Never clean or alter them to get a pass.

### Manifest preparation - public data only, owner review before live commands

The following optional PowerShell creates a **new public approval candidate** in
the ignored test-results directory. It is not database fixture preparation or
approval. Do not execute it on behalf of the owner in M-015B. Review generated
UUIDs/names, counters and intended writes before authorizing live commands.

```powershell
Set-Location I:\Merge
$browserRun = [guid]::NewGuid().ToString()
$browserPrefix = 'm015b_' + $browserRun.Replace('-', '').Substring(0,8) + '_'
$browserPlan = [ordered]@{
  run_id = $browserRun
  accounts = @('l','q','r','x') | ForEach-Object {
    [ordered]@{ role=$_; username=($browserPrefix+$_); register_attempts=1; login_attempts=4; logout_attempts=4 }
  }
  hackathons = @('a','b') | ForEach-Object {
    [ordered]@{ id=[guid]::NewGuid().ToString(); name=($browserPrefix+'challenge_'+$_) }
  }
  team_a = $browserPrefix+'team_a'
  team_b = $browserPrefix+'team_b'
  commands = @('create_a','create_b','request_q','request_r','approve_q','reject_r','issue_r','issue_x','redeem_r','redeem_x','deny_issue_q','deny_decide_q','deny_redeem_x') | ForEach-Object {
    [ordered]@{ command=$_; attempts=$(if ($_.StartsWith('deny_')) { 0 } else { 2 }) }
  }
}
$browserPlanPath = 'I:\Merge\frontend\test-results\m015b\' + $browserRun + '\approval.json'
if (Test-Path -LiteralPath $browserPlanPath) { throw 'Existing plan. Stop.' }
git -c safe.directory=I:/Merge check-ignore -- $browserPlanPath
if ($LASTEXITCODE -ne 0) { throw 'Plan path must be ignored. Stop.' }
New-Item -ItemType Directory -Path (Split-Path -Parent $browserPlanPath) -ErrorAction Stop | Out-Null
$browserPlanJson = $browserPlan | ConvertTo-Json -Depth 8
$browserPlanFile = [System.IO.File]::Open($browserPlanPath, [System.IO.FileMode]::CreateNew)
try {
  $browserPlanBytes = [System.Text.UTF8Encoding]::new($false).GetBytes($browserPlanJson)
  $browserPlanFile.Write($browserPlanBytes, 0, $browserPlanBytes.Length)
} finally { $browserPlanFile.Dispose() }
```

All objects forbid extra fields, duplicate JSON keys, duplicate roles/commands/IDs,
bad names/UUID versions, oversized manifests and boolean/negative/excessive budgets.
No `faults` field: browser fault approval is separate and uses actual public IDs
only after they exist. Account passwords are chosen privately by the owner and
typed only in the UI (15-128 characters). The database-role password is separate;
never pass any credential through arguments, JSON, chat, screenshots or transcripts.

### Supported commands - conditional on separate owner approval, NOT RUN

In the owner's private interactive PowerShell, set `$browserPlanPath` to the exact
reviewed file above. Gate B approval covers global fingerprint/metadata reads and
freshness checks. No server or write occurs in inspect:

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m test_support.browser_full inspect --confirm-merge-test --revision 0005_invitations --manifest $browserPlanPath
if ($LASTEXITCODE -ne 0) { throw 'Inspection failed. Stop.' }
```

Only after approving exactly those two retained hackathon INSERTs (gate C):

```powershell
.\.venv\Scripts\python.exe -m test_support.browser_full prepare --confirm-merge-test --revision 0005_invitations --manifest $browserPlanPath --allow-fixture-writes
if ($LASTEXITCODE -ne 0) { throw 'Preparation or final check failed. Stop; do not rerun.' }
```

Only after approving four UI registrations and bounded auth/throttle/domain writes,
listeners, browser profiles and final read-only observers (gates D/F):

```powershell
.\.venv\Scripts\python.exe -m test_support.browser_full serve --confirm-merge-test --revision 0005_invitations --manifest $browserPlanPath --allow-browser-writes
if ($LASTEXITCODE -ne 0) { throw 'Host or final certification failed. Stop.' }
```

Wait for `Full browser host ready; exact-0005 guarded loopback only.` Then in a
second owned terminal start Vite, without opening external/LAN bindings:

```powershell
Set-Location I:\Merge\frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open http://127.0.0.1:5173 only. Follow the required order above in separate
clean profiles or carefully scoped sign-out/sign-in sessions. Do not reuse an
unrelated account's cookie/profile; do not enable transcripts, APM, raw request/
state debugger capture or session recording. Generate no third team,
H-B membership, new-key repeat command or extra applicant. Stop on scope rejection
and review the expected command, rather than increasing budgets or changing keys.
The wider application remains unchanged; the harness intentionally narrows it.

Finish or restore response gates; stop new clicks; retain uncertain-command tabs.
Stop owned Vite with Ctrl+C, then press Ctrl+C once in the backend terminal. Final
success requires positive drain, empty tasks/connections, lifespan completion,
fresh independent observer certification and successful engine/listener cleanup.
Require both exit 0 and `Full browser host final journey invariants verified;
fixtures retained.` A complete journey is required: stopping halfway is unsuccessful
even if the partial rows are valid. A forced/second interrupt cannot pass.

Optional separately approved current-state read after a failed/incomplete run:

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m test_support.browser_full verify --confirm-merge-test --revision 0005_invitations --manifest $browserPlanPath
if ($LASTEXITCODE -ne 0) { throw 'Current-state verification failed. Stop.' }
```

Inspect/verify print `Full browser current-state checks verified; no server started;
no run certification.` Verify checks current scoped shapes/invariants and target,
not a lost before-state, complete journey or prior shutdown. No command migrates,
downgrades, cleans, repairs, changes passwords or automatically resumes a run.
CLI input/approval errors exit 2 before prompts; operational failures exit 1 with
fixed categories. Preparation completion means retained fixtures checked, not UI
acceptance. Missing passwords/ports/target/manifest/state never trigger fallback.

### Browser-only response gate (separate approval, not part of the app bundle)

`frontend/test_support/browserFaults.js` is not imported by src or production
builds. Vite can serve it during this approved local session; install manually
in private DevTools only after approving each exact resolved public URL/method/
mode and its already budgeted attempt/retry. No backend fault endpoint exists.
Modes: hold a real completed response, lose its acknowledgement, or deliver a
labelled synthetic invalid_session after the real request. The last mode is UI
isolation evidence only; it may follow a real committed mutation, not a server
authentication failure. It never authorizes/duplicates the real request.

```javascript
const { installBrowserFaults } = await import('/test_support/browserFaults.js');
// Replace path with ONE actually resolved, explicitly approved public URL.
const browserGate = installBrowserFaults(window, {
  approved: true, origin: 'http://127.0.0.1:5173',
  cases: [{ path: '/api/hackathons/ACTUAL_UUID/teams/ACTUAL_TEAM_UUID/invitations', method: 'POST', mode: 'hold' }]
});
browserGate.arm(0);
// Perform the approved UI action. status() reports a phase only.
browserGate.status();
// Once held, navigate/change session as approved, then release within 15 seconds:
browserGate.release();
browserGate.restore(); // Also run in finally/on failure; do not leave the hook installed.
```

Placeholder UUIDs are deliberately refused. Copy exact canonical lower-case
public IDs from the run's UI; never copy cookies, CSRF, key/body/header dumps or
auth responses. /auth, foreign origins, query-bearing/unknown paths, unapproved
methods, simultaneous gates and oversized bodies are refused/not intercepted.
The real fetch gets unchanged session/CSRF/signal; there is one dispatch only.
Actual response buffering is bounded to 64 KiB; held delivery expires after 15s
and restores fetch on timeout. Old-aborted delivery is deliberately permitted
only after a real response was obtained, to test workspace ownership. Restore
does not undo a committed effect. Reload loses both hook and app recovery journal.

### Certification and honest remaining limits

Snapshots hold only per-row fingerprints, public scoped domain state and private
session/throttle metadata; no raw credential hash/session token/CSRF is selected
or output. All twelve preexisting table row fingerprints must remain identical;
every added row must be accounted for by the scoped journey/auth/throttles. Final
state requires 4 newly registered actors, A=L/Q/R, B=X, 2 resolved requests, 2 grants
(R redeemed, X pending), 9 exact completed idempotent replies/fingerprints, A version
8/B version1 and 9 connected, sequential audit/outbox chains. It checks scopes,
actors, member counts, grant timing, stored reply identity/status, history state
and unpublished outbox linkage. Throttle/session additions stay within charged
budgets; full-team/negative attempts add no domain effects. Observers use a fresh
guarded engine. No receipt/snapshot is written as a raw artifact.

The host is trusted test tooling, not a malicious-code/role/OS sandbox. Exclusive
access is mandatory; fingerprints across READ COMMITTED statements are not a
global simultaneous snapshot. Current-state verify is not a full schema drift
audit. Source/run/browser/manifest/evidence records still need owner recording;
there is no new historical per-node roster or durable command recovery store.
Host ledger and browser command keys are memory-only. A host crash/restart cannot
resume an existing scope: fresh-start checks refuse retained accounts/domain rows;
stop for a separately reviewed read-only recovery plan. Same-process logout/login
and navigation recovery remains supported. A lost registration response is
recoverable by login only when the server confirmed/bound registration first;
an ambiguous registration COMMIT requires separate diagnosis, not blind adoption.

UUID-only recipient entry, small-fixture pagination limits, absence of natural
expired/stale-leader schedules, local HTTP and mobile-emulation limits remain.
No live browser/HTTPS/accessibility/G1/load proof follows from offline tests or
the terminal certification alone. Complete the pending checklist below and
record actual browser outcomes separately. The earlier intermittent loading/
fetch-count concerns remain documented. All live actions and commit await review.

## Historical M-015A - exact-0005 full-stack readiness, 2026-11-11

**Offline analysis and proposed next setup only. Full-stack browser execution is
blocked pending implementation/review of a separate guarded 0005 host and owner
approval of concrete accounts, fixtures and writes.** No server, browser, database
connection, credential prompt, migration or fixture operation occurred. Baseline:
`b8abacd5c0f5796488916da4884d2c672ee4eb6d` (M-014C committed).
0005_invitations is already applied according to prior owner evidence; no new
revision/drift verification or G1 result is claimed. G1 remains closed only within
its audited local PostgreSQL scope. The M-011A operational contract below remains
unchanged and historical; its 0003 commands cannot serve the present database.

### Startup inventory and concrete hazards

| Path | Implemented behavior | Suitability for this acceptance |
|---|---|---|
| `backend/app/serve.py` / `python -m app.serve` | Ordinary full application; defaults loopback:8000, one worker, disables Uvicorn proxy-header rewriting/access log; host/workers are configurable | Not a merge_test launcher; no test identity/revision/scope/final-state guard |
| Direct `uvicorn app.main:app` | Same ordinary application; bypasses controlled launcher options | Unsuitable; can also restore Uvicorn proxy rewriting/log defaults |
| `backend/app/main.py::create_app` | Auth/read/create/request/invitation routers; lifespan loads AuthSettings and lazily initializes runtime services | Factory alone does not isolate a test database or authorize writes |
| `backend/test_support/browser.py` | Guarded inspect/serve/verify, exact 0003, 1-3 retained accounts, auth-write budgets | Refuses 0005; removes create/admission/invitation routers and blocks registration. Preserve it |
| `test_support.concurrency --suite invitations` | Exact-0005 in-process real-service acceptance with retained generated fixtures | Not a browser server; do not rerun it or use its random credentials as browser accounts |
| `frontend` / `npm.cmd run dev` | Vite loopback:5173, strict port, proxies /auth, /api and /health to 127.0.0.1:8000 | Suitable only after the newly reviewed guarded backend is ready; use exact numeric host |
| `npm.cmd run build` | Typecheck and static production assets | Build proof only; neither a server nor production routing/HTTPS proof |
| `scripts/check_local_http.py` | Ordinary local HTTP/proxy smoke launcher, not the new guarded acceptance host | Not an alternative startup path for this task |

The precise Settings chain is `auth.get_services -> build_engine(Settings()) ->
settings.database_url()`. Settings loads absolute `backend/.env` plus overriding
MERGE_DB_* environment values. Defaults are 127.0.0.1:5432 / merge_dev / merge_app;
database_url explicitly refuses any different database, including merge_test.
An empty password becomes None and may allow driver password-file/environment
credential resolution. Do not inspect those private stores or rely on defaults.
The ordinary engine has READ COMMITTED/hide_parameters/connect timeout but no
actual test identity/exact revision/per-checkout latch or run write budget.
Health and import need not connect, so a healthy process is not safe-target proof.
Login/registration and valid-session requests can initialize services and connect.
Auth/read/team/admission/invitation services then share that ordinary engine.

AuthSettings separately requires an exact origin and 32-byte throttle secret,
defaults to production/HTTPS, reads MERGE_AUTH_* (not dotenv) and distinguishes
production __Host-merge_session from local merge_session_dev. Missing config
fails lifespan; valid auth config does not change the database target. Setting
MERGE_DB_NAME=merge_test, using ordinary app.serve, monkeypatching Settings or
overriding only auth is not a supported solution. No .env/configuration was read
or changed by this review. README's ordinary provisioning/migration/start commands
remain development history, not instructions for this acceptance run.

### Minimum proposed environment and implementation boundary

Use the existing local PostgreSQL 17 merge_test / merge_app at exact 0005,
exclusive of other writers, with two fresh retained hackathons. One backend
process on 127.0.0.1:8000 and existing Vite on 127.0.0.1:5173. Separate browser
profiles/contexts for leader and participants; ordinary tabs share a cookie and
cannot stand in for distinct signed-in users. This is logical fixture isolation
in the shared test database, not a database-role/OS/malicious-code sandbox.
No new database, role, grant, schema, migration, dependency or production service
change is needed for this local phase. HTTP development cookies do not establish
deployed HTTPS security. Physical-phone access over a LAN is outside this origin/
loopback scope; begin with browser mobile viewport emulation.

Smallest source work still needed (proposed names, **not implemented commands**):

1. Add `backend/test_support/browser_full.py`: separate exact-0005 CLI/host,
   preserving browser.py's revision/routes/manifest. Reuse reviewed lifecycle,
   hidden-input and loopback policy helpers where safe, never its 0003 engine
   guard. Reject missing approval, unknown options, optimized Python, malformed
   scope or occupied ports before credentials/connections/listeners as applicable.
   No import-time app/engine or ordinary Settings/dotenv/URL/password fallback.
   Disable access/SQL/exception/body logs and external telemetry; errors/CLI
   rejections must use fixed categories without values, URLs or tracebacks.
   DB credentials enter only at hidden interactive input with echo fallback
   refused; no password arguments/files/environment inheritance.
2. Supply all five real dependencies on one guarded engine: auth.get_services,
   read_api.get_read_service, team_api.get_team_service,
   admission_api.get_admission_service, invitation_api.get_invitation_service.
   Leave ordinary runtime engine/services unset. Audit exact endpoint/dependency
   identity before every request and fail closed if any override/router changes.
   Keep real Credential/Session/Throttle/Team/Admission/Invitation services and all
   CSRF/Origin/strict-body/idempotency/backend authorization behavior unchanged.
3. Guard initial, new/pooled and independent observer connections: fixed target,
   actual database/role/IP/port, synchronous psycopg, DBAPI autocommit false,
   no inherited/nested transaction, actual/default READ COMMITTED, 5s lock/15s
   statement limits, read-only guard transaction and exactly [0005_invitations].
   Roll back guards before real service transactions; latch every failure. Keep
   sole service transaction owners, lock order and retry/reconciliation untouched.
4. Add `browser_full_state.py` with a strict public-ID/run/attempt manifest,
   bounded per-account/per-operation attempts (including failed/replayed calls)
   and dynamic public ID bindings from real registration/team/grant results.
   A manifest narrows test scope; it never supplies actor authority. Fresh
   approved usernames must be absent at preflight; bind returned server UUIDs
   before login and reject collisions. Lock budget reservations before dispatch;
   counters bound test writes, not domain concurrency correctness.
5. Add a small separately guarded retained-hackathon preparer (for example
   `browser_full_fixtures.py`): explicit approval, fresh run IDs, exactly two
   INSERTs in one owned transaction with target/revision/pre/post checks. No
   account passwords or prejoined memberships; registration and team creation
   must occur through the real UI. No idempotency guessing, upsert/adoption,
   expiry mutation, resets or cleanup. There is no public hackathon-create API.
6. Extend new read-only before/after certification to all 12 tables, including
   join_requests and invitations. Preserve unrelated rows/credentials and schema;
   validate only declared new users, sessions/revocations, throttle charges and
   scoped domain effects. Check capacity, unique membership, valid leadership,
   request/grant state, complete idempotent replies and version/audit/outbox
   linkage from fresh observers. Legacy browser_state.compare deliberately
   requires domain/credential tables unchanged and cannot certify these writes.
7. Add offline `tests/test_browser_full_harness.py` refusal, scope/budget,
   registration binding, five-dependency, 0005 checkout, sanitized failure,
   certification and shutdown tests. Prove legacy browser source/policy and
   production modules unchanged. No new runner compatibility claims for legacy
   0003 auth/browser or 0004 admission suites at 0005.

A bounded browser-only response gate is a second, separately reviewed test helper,
not a production fetch change or backend bypass. Scope it to one exact approved
read or mutation command. Send once through real HTTP/auth, then hold the actual
response (up to 15s, below the client's 20s deadline), or deliberately lose one
acknowledgement after the server responds. Never pause inside a DB transaction,
capture auth bodies/secret headers or dispatch twice. Allow delivery after abort
to exercise stale-result guards; restore fetch/clear timers and held data in
finally. Record only held/released/injected and same-command booleans, not keys,
CSRF, cookies or response dumps. Offline refusal/restoration/timeout tests are
required before use. This helper is currently absent. Generic Slow 3G/offline
toggles alone cannot prove a late completion or exact ambiguous-response schedule.

### Concrete proposed fixtures and writes for owner review

No approved current account mapping was found in the reviewed docs; the legacy
`frontend/test-results/m011a/approved-run.json` path still does not exist (existence
check only). No private manifest/password/credential data was read. Existing
random suite credentials are not recoverable browser prerequisites.

Propose four new test usernames, e.g. `m015a_<8hex>_l`, `_q`, `_r`, `_x` (schema
illustrations, not actual accounts), approved before creation. Owner chooses and
keeps unique 15-128-character passwords privately; never place them in manifests,
CLI arguments, environment, screenshots or chat. The DB-role password is separate
and entered only through fail-closed hidden interactive input. The host generates
one process-lifetime test throttle HMAC secret privately; never rotate it/restart
to evade throttles. Restore/sign-in after browser focus must stay within budgets.

| Proposed scope | Purpose / explicit bound |
|---|---|
| H-A and H-B, fresh UUIDs and recognizable run labels, min=2/max=3 | Two retained hackathon INSERTs only; H-B can remain empty for navigation tests |
| L, Q, R, X | Four fresh username registrations through UI, one attempt each; server generates actor UUIDs. Four fits the existing register IP limit of 5/300s |
| Per account login <=4, logout <=4 | At most 16 login attempts/sessions and 16 revocations; incorrect-password attempt counts within X's allowance. Original login limits 5/account, 30/IP per 300s remain |
| Team A by L in H-A; Team B by X in H-A | Two new create commands, at most two HTTP attempts each to allow an exact same-key retry; no third team or H-B membership needed |
| Q and R request Team A | Two request commands, at most two attempts each; L approves Q and rejects R, at most two attempts per exact decision |
| L invites R and X to Team A | Two separate recipient-bound issue commands, at most two attempts each; issuance reserves no seat |
| R redeems, X tries full Team A before creating Team B | R adds the third/final member; X gets team_full, stays unassigned and grant stays pending; at most two attempts per exact redemption |
| Negative authorization/recovery | Enumerate exact extra attempts separately in the concrete manifest: e.g. nonleader issue, wrong-recipient redeem, lost-ack retry. No blanket wildcard/write budget |

Main sequence: create A -> Q/R requests -> approve Q/reject R -> issue R/X ->
redeem R -> X full conflict -> X creates B. Team A ends with L/Q/R, Team B with X;
H-B has no memberships. R's rejected request is a separate record and does not
authorize or block its legitimate invitation. With no extra distinct commands,
the expected domain effects are 2 teams, 4 memberships, 2 resolved requests,
2 invitations (one redeemed, one pending), 9 successful idempotency records and
9 audit/outbox links; Team A version 8, Team B version 1. Matching-key success
replays add no such effects; full failure adds none. These are proposed expected
counts, **not measured results**. New-key duplicate requests have their own
documented idempotency semantics, so they are not interchangeable with same-key
retries. Throttle/session/account writes must be counted separately.

All registration writes users/account_credentials plus register throttle state.
Login attempts can commit IP/account throttle charges even on failure, successful
login creates auth_sessions, logout updates scoped revoked_at. Invitation attempts
charge separate durable account issue/redeem buckets even on domain failure.
Domain writes include memberships, team version/time, request/grant resolution,
stored idempotent result and audit/outbox atomically through the existing services.
No deletes, email, password reset, leadership change or outbox dispatch is approved.
Retain everything; reruns require separately approved fresh scopes and budgets.

### Owner gates and operating sequence

| Gate | Approval/evidence needed before action |
|---|---|
| A: offline implementation | Approve the bounded host/preparer/certifier design above, implement and review actual files/tests/CLI. This analysis grants no live rights |
| B: read-only preflight | Explicitly approve local merge_test/merge_app connection, exact 0005 identity/permissions and account-name/fixture checks plus global invariant/fingerprint reads; private DB password, no server/writes |
| C: fixture preparation | Approve the exact fresh run ID, two hackathon UUIDs/labels/sizes and two retained INSERTs. Fail closed on existing IDs or drift; no adoption/repair |
| D: browser run | Approve real four usernames/returned ID bindings, private credentials, exact endpoint/account/hackathon/command attempt budgets, registration/session/throttle/domain writes, localhost listeners/browser and retained evidence policy |
| E: injected recovery | Separately review/approve the specific browser-only delivery/lost-ack/401 injection cases and their retry attempt budgets. Injection proves labelled UI behavior, not natural COMMIT failure or real revoked-session authentication |
| F: final certification / incomplete run | Approve fresh read-only observers. Missing before-state, timeout, forced exit or unrelated writer means inconclusive, never repaired by a later current-state snapshot or automatic restart |
| Later: deployment/HTTPS | Separate topology/proxy/TLS/origin/privilege and production-secret review. No deployment authorization here |

Gate B has one **existing** optional identity/revision-only command, after separate
owner approval in a private interactive PowerShell terminal; **not run here**:

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0005_invitations
if ($LASTEXITCODE -ne 0) { throw 'Read-only target verification failed. Stop.' }
```

Enter the existing role password only at a genuinely hidden prompt; abort on any
getpass echo warning (this older CLI does not trap GetPassWarning as strictly as
the browser host). It checks actual target, READ COMMITTED, schema permissions
and recorded revision, not fixture ownership/full schema drift or credentials.
It runs no migration. The future host must repeat stronger guards on every
checkout; this optional command is not authorization to serve or proof of safety.

**No supported full-stack backend serve command exists at this checkpoint.**
Do not substitute `test_support.browser --revision 0005_invitations`, change its
constant, downgrade, use ordinary app.serve or publish a guessed new CLI. Gate A
must deliver exact inspect/prepare/serve/verify commands and sanitized readiness/
completion labels together with offline tests; until then startup is blocked.

After A-D actually pass: inspect -> prepare the approved two fixtures -> independent
read-only scope/before snapshot -> guarded single backend -> wait for its specific
ready label -> start existing Vite in a second private terminal:

```powershell
Set-Location I:\Merge\frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open only http://127.0.0.1:5173 in the approved profiles. Do not change to localhost,
another port/host, trusted proxy, wildcard Origin, CORS relaxation, secure-cookie
override, public join or client actor header. Stop if either port is occupied;
do not kill unrelated listeners. Local HTTP verifies local policy, not HTTPS.

Shutdown contract for the proposed host: finish/release test gates; stop new
clicks; retain any uncertain-command tab; log out within approved budgets only
when doing so does not discard needed recovery; stop owned Vite with Ctrl+C;
press Ctrl+C once in owned backend terminal. Require positive completed drain,
empty tracked connections/tasks, complete lifespan, fresh final comparison,
Engine/listener disposal, fixed final certification label and exit 0. A second
interrupt, forced stop or timeout is inconclusive even if rows later look valid.
Existing BrowserServer supplies this lifecycle behavior; the new host must
preserve and test it, not merely copy a successful print statement.

If target/auth/route/budget/drift/final checks fail, stop, retain fixtures and
sanitized run IDs/categories, do not rerun seed/migration/cleanup or increase
budgets automatically. A lost mutation response needs the same in-memory command
and key after authorized session restoration; check canonical membership/inbox
before interpreting it. Reload/crash loses exact recovery; stop for separately
approved read-only diagnosis, never invent a new key or assume rollback. A lost
registration reply has no command journal: try the known credentials/check the
approved username through separately scoped verification, not blind re-register.

### Browser record - every live item below remains pending

Record source hash + diff scope, run/manifest ID, browser/version/profile, exact
target/preflight, viewport, case, expected/actual result and injection label. No
HAR, trace, raw Network/header/auth-body/storage dumps or credential screenshots.
Keep only reviewed UI captures and metadata under Git-ignored test-results; hide
password forms and DevTools. Inspect captures before retaining/sharing. Real
service observers, not screenshots alone, certify committed-state invariants.

| Case | Acceptance to record |
|---|---|
| Registration | Four approved names: 201, confirmation then sign-in, no automatic membership/session. Invalid input safe; private password cleared. Registration stays blocked in legacy host |
| Login/restore | Known credentials -> correct account; one budgeted wrong password -> safe 401. Reload/focus/session restore shows only canonical account data. Inspect cookie attribute booleans privately, never its value |
| Cookies/security | Development cookie HttpOnly/Lax/Path=/, no Domain, Secure false locally; bearer absent from JSON/DOM/JS storage/URLs/logs; CSRF is allowed in session JSON/memory. Original CSRF/Origin/header/strict-JSON negative calls stay denied with no domain effect |
| Discovery/scope | Select the exact two approved UUIDs; H-B empty is legitimate. Detail/My Team show canonical counts/leader. Pagination beyond 20 needs additional separately approved data; this small fixture plan does not prove multi-page browser behavior |
| Team creation | L creates A and X later B; rapid submit yields one command/effect; confirmed result triggers canonical reads. No optimistic membership from mutation response; another account sees only its own state |
| Requests/decisions | Q/R create one each; canonical mine supplies status. Only L sees applicants; approve Q/reject R exactly, then refresh canonical membership/list/detail. Nonleader list/decision stays denied; no applicant leakage |
| Invitations | Recipients share session-derived account UUID privately as public ID; L enters exact recipient_id, no username lookup. Inbox only addressed grants, server availability/expiry, labelled team UUID opens canonical details; issue reserves no seat |
| Redemption | R redeems with its current session/CSRF, third member appears through GETs; X receives team_full and remains unassigned with pending/null-redeemed grant, then can create B. Wrong account/known invitation UUID is never authority |
| Error/expiry/permission | Full/assigned/expired/stale/used/missing/403/429 states stay accurate; no optimistic consumption. Natural expiry needs approved expired data/time, stale issuer has no UI transfer route. Mark unavailable live cases skipped; synthetic responses prove UI only, never modify immutable expiry/leader rows |
| Workspace/session races | Hold a real read/issue/redeem reply, select H-B or Team B, release; current account/draft/reads stay intact. Away/back must not revive old ownership; returning can recover original command. Hold old-account success/401 across logout/login and current-session restoration; no leakage/new-session expiry. A real or explicitly labelled injected old-workspace 401 must not expire the new selection; a current-workspace 401 must preserve expiry behavior |
| Uncertain retries | Lose a real acknowledgement after one dispatch, keep tab, refresh inbox/remove row only through naturally changed canonical state, retry exact URL/body/key/scope with current CSRF. One committed effect; no new automatic key/POST. Row disappearance on demand requires separately reviewed response gate; no DB deletion. Recovery after reload/crash is explicitly unsupported |
| Desktop/mobile/keyboard | 1440x900, 375x812, 320x740, 200% zoom; no clipping/UUID overflow. Skip link/Tab/Shift+Tab/Enter/Space, visible focus, labels/errors, loading/empty/denied states, heading focus, status announcements; record actual screen reader/reduced-motion coverage. Viewport emulation is not a physical-phone test |
| Logout | Real scoped revoke and cookie removal, guest UI, next protected read 401; delayed old result ignored. Lost logout acknowledgement hides private data and offers session verification; it is not confirmed logout until verified |
| Final state | Independent exact-0005 certification of declared effects and unchanged unrelated rows, version/audit/outbox/idempotency/membership/request/grant invariants; positive shutdown and exit 0 |

UUID-only selection is a real usability limit: no username search, delivery,
team-name inbox field or transferable bearer invite. Public UUID possession is
not authority. Recovery is memory-only; even canonical membership cannot recover
a lost exact key/reply after reload/crash/tab closure. Document these in the demo.

### Flakiness and release priority

M-014C's first concurrent frontend run: 258 passed/3 initial-loading failures;
unchanged standalone: 261 passed. Scheduling/resource contention is plausible,
not demonstrated. Historical M-013A fetch-count mismatch was consistent with
unflushed new-workspace effects; M-013B added a bounded wait for those expected
reads. Preserve the concern: neither that synchronization repair nor a later pass
proves all timing risks solved. In contrast, R1's five old-hackathon 401 failures
were reproduced before a source repair and pass afterwards: a demonstrated
product defect with regression evidence. Do not conflate the two categories.
This review changes no tests/assertions/timeouts. Run future UI verification
standalone; keep any failed result and diagnose repeatable failures before release.

Local browser blockers: new exact-0005 host/certifier/preparer, approved private
account plan and write budgets, exclusive target preflight, reviewed response gate
for deterministic races, and actual browser execution. Browser/HTTPS deployment
acceptance, CI API/race runs, 10k/2k seed and measured 100-client p95, public repo/
URL/design/load/video artifacts remain release blockers, not post-submission
polish. Current routes also lack required departure/succession/last-member deletion/
removal, realtime and matching flows; this browser milestone cannot certify those.
Requirements R-05/06/09/10/13 and the remaining submission gates require separate
bounded work. No feature is added here. Search/delivery polish, durable recovery
UX, broader device coverage and optional tooling can follow only after mandatory
acceptance; documented limitations do not waive required accessible usable UI.

Owner exercise: explain why health can pass before the wrong ordinary Settings
path connects. In an offline host test remove one of the five service overrides;
the proposed host must refuse before Settings or any SQL can run. Confirm that
changing legacy REVISION is not a legitimate 0005 readiness implementation.

## Historical M-011A-R4 - test-only guarded browser host

M-013A's admission router is also explicitly excluded by router identity; the
exact dependency/route inventory still guards every request. The host remains
0003_auth-only and its manifest authorizes no request/team writes. The owner now
reports applied 0004 on merge_test, so this host refuses that target. Do not
downgrade or bypass guards to start it. No browser scope expansion
or acceptance claim; see [ADMISSION.md](ADMISSION.md).

M-012B now exposes a Create Team form in React. This host still excludes that
router and its manifest authorizes no team mutations. Do not exercise creation
through it or switch to ordinary app.serve to bypass the guard. Separately reviewed
host/write scope is required for live creation UI acceptance. M-012B is offline
verified only; no browser acceptance is claimed.

M-012A adds team creation to the ordinary application, but this test-only host
explicitly excludes that router and retains its original exact dependency/route
audit. Its approval manifest never authorizes team writes. Team creation is not
supported by these browser commands; separate HTTP test instructions are in
[TEAM_API.md](TEAM_API.md).

**M-011A-R4: shutdown defect corrected offline; stop for owner review.** The R3
regression now passes. Timeout/incomplete drains remain unsuccessful independently
of later snapshots; final success is printed only after Engine/listener cleanup.
[BROWSER_HOST_AUDIT.md](BROWSER_HOST_AUDIT.md) records the minimal source diff and
R3/R4 evidence. Live reads, scoped auth writes and all account/fixture prerequisites
still require separate owner approval; no live startup is authorized by this fix.

Implemented for offline owner review against HEAD
`cc67e18ffd6a6845642170fa358ecc48d2fef38b`. **No live startup, browser,
credential prompt, PostgreSQL access or fixture write was performed. G1 is open.**
R4 corrects R3's shutdown blocker; prior R1/R2/R3 evidence remains historical in
PROGRESS and BROWSER_HOST_AUDIT. The commands still require owner review/approval.
The pending browser checklist and separate delay-instrument proposal below remain
unexecuted. This document is the operational contract for this harness.

## M-011A-R5 - controlled live preflight preparation (not executed)

**Implementation supported offline; live inspect is not yet ready to execute.**
R5 found no approved retained-account UUID/username mapping in repository docs or
README. The documented frontend/test-results/m011a/approved-run.json path does
not exist (existence check only). This is not a claim that no accounts exist in
PostgreSQL or that no private owner record exists elsewhere. No credential store,
private IDE attachment, ignored manifest contents or database was read to obtain
identifiers, and no approval manifest was generated.

The exact inspect path is main -> read_scope -> hidden_password ->
TestDatabaseSettings -> guarded_engine -> Engine.connect -> snapshot -> resource
cleanup -> fixed success output. It does not construct browser_app or auth/read
services, issue a session, call a throttle, invoke register/revoke, bind an HTTP
socket or generate any manifest. snapshot uses SET TRANSACTION READ ONLY, SELECTs
and rollback; the initial identity/revision/settings guards use read-only/control
SQL too. It cannot create application accounts/sessions/throttle/domain records
through the inspected code paths. Reading invariants does not prove credentials
are known, fixtures are sufficient, or a later browser run has succeeded.

| Proposed input | Supported behavior |
| --- | --- |
| Missing manifest, {}, or accounts=[] | Refused before password prompt or database access; accounts must contain 1-3 objects. No identity-only bypass is implemented. |
| One actual approved account with both budgets 0 | Valid no-auth-write scope for inspect, provided all strict fields and existing UUID/username mapping are correct. It still reads account/global invariants; it is not an identity-only command. |
| Synthetic/placeholder IDs, unknown mapping or nonzero unapproved budgets | Not an acceptable owner-approved preflight. Placeholders are schema examples only; real mapping checks can fail after connecting. |

Minimum prerequisites/approval for one later inspect:

1. Owner supplies and approves a real existing test-account UUID and exact username
   from an existing public-ID record (1-3 accounts supported; one is sufficient).
   If unavailable, a separate narrowly scoped read-only identifier-discovery task
   needs owner approval; inspect cannot discover its own unknown manifest IDs.
   Do not recover identifiers by reading password/session stores or create/reset
   an account as a workaround.
2. Owner manually reviews a strict manifest with a fresh run UUID, those account
   mappings, login_attempts=0 and logout_attempts=0 for each account. No password,
   token, hash or HMAC key belongs in the file. R5 creates none of this file.
3. Owner explicitly authorizes the live local database connection and read-only
   target/revision/isolation/timeout checks, account-mapping check, and whole-test-
   database invariant/aggregate fingerprint reads. These include private auth
   metadata held only in process memory; outputs remain fixed and sanitized.
   Approval is for no application writes, no server and no browser. It is distinct
   from later session/throttle-write approval; this task grants neither.
4. Existing merge_app DB-role password is entered by the owner at the hidden
   interactive prompt, with no recording/transcription/APM. No application-account
   password is required by inspect. Arrange an exclusive inspection without
   unrelated writers, and the expected local target at 0003_auth; do not migrate,
   alter privileges or repair state to make inspection pass.

Suggested approval wording for later owner review, not a request or an approval:
"Approve one read-only browser inspect of 127.0.0.1:5432 / merge_test / merge_app /
0003_auth using the reviewed <manifest path> and <existing username/UUID>, with
zero login/logout budgets, identity/settings/account/global invariant reads only,
private interactive DB-role input, no application writes or HTTP/browser startup."

Only once those prerequisites and that separate approval exist, supported syntax:

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m test_support.browser inspect --confirm-merge-test --revision 0003_auth --manifest I:\Merge\frontend\test-results\m011a\approved-run.json
if ($LASTEXITCODE -ne 0) { throw 'Guarded inspection failed. Stop.' }
```

Expected safe interaction, conditional example only (not an observed live result):

```text
Existing merge_app password (hidden):
Browser host read-only scope and invariants verified; no server started.
```

Require exit 0. No password, account data, fingerprint, bearer, HMAC secret or URL
is printed. Failure uses fixed sanitized categories and exit 1; invalid CLI is 2.
A missing manifest at the documented current path fails before any prompt.

**This command does open PostgreSQL connections.** Normal successful inspect holds
an anchor and a second logical connection on the same owned Engine (normally two
physical connections while the anchor is held). Both are configured only for
127.0.0.1:5432 / merge_test / merge_app, with no Settings/merge_dev fallback. Actual
identity, exact revision, transactional psycopg/DBAPI AUTOCOMMIT, READ COMMITTED and
timeouts are checked before snapshot work. A socket/authentication attempt precedes
verification of the responding server's identity; failed identity verification
stops further work. Do not describe inspect as database-free or as verifying a
server without connecting. It leaves no application records, rolls back read
transactions, closes connections and disposes its Engine.

R4's shutdown wrapper preserves original database/dependency/policy gates. This
was confirmed by source review and a fresh R5 127-case offline harness pass. The
inspect path does not run the shutdown server at all. Later serve requires positive
normal drain, empty tracked request/connection sets, no sticky drain/guard failure,
completed lifespan, independent final comparison and successful Engine/listener
cleanup before the final success label and exit 0. Forced/incomplete interruption
or missing evidence is inconclusive; cancellation/disposal does not prove a worker
stopped or a transaction rolled back. Standalone verify cannot recover a lost
before-state or clear failed-run evidence.

Future browser step only: after inspect passes, separately review and approve a
concrete auth-write manifest/operation budget, retained private account passwords
and domain fixtures, then use the conditional serve/Vite commands below. Do not
silently raise zero budgets or add --allow-scoped-auth-writes to this read-only
approval. Login generally writes throttle/session state; logout can revoke a
session. Registration stays blocked; all existing guards remain mandatory. A
read-only inspect pass never authorizes browser startup or proves page fixtures.

## Supported scope and files

- `backend/test_support/browser.py`: explicit CLI, fixed policy, Engine ownership,
  per-connection guard, both real service overrides, scope budgets and ASGI audit.
- `backend/test_support/browser_state.py`: strict public-ID manifest, read-only
  before/after evidence and membership-compatible invariant checks.
- `backend/tests/test_browser_harness.py`: offline failure/HTTP/lifecycle tests.
- Documentation updated: this file, FRONTEND.md, TEST_DATABASE.md, PROGRESS.md.

No production code, endpoints, dependency manifest, migration, privilege or schema
change. Setuptools already includes only `app*`; neither `test_support` nor the
harness is in the production package. Production sources must never import it.
The CLI constructs an ASGI object only after explicit confirmation and preflight;
there is no module-level browser `app` or factory usable by ordinary Uvicorn CLI.

**This minimal version reuses retained accounts only. Registration is blocked.**
It can support login/session restore/logout and authenticated discovery, including
negative auth/CSRF/throttle cases within the declared budgets. It cannot create
accounts or teams, reset credentials, seed, clean up, or complete registration
browser acceptance. Those require a later separately reviewed implementation and
write plan. Existing fixture passwords generated randomly in past test processes
are not recoverable; do not extract hashes, reset credentials or guess passwords.
If no retained account has known private credentials, stop and report that blocker.
Three ReadEnvironment teams do not establish a second page of 20 teams. Reuse
existing sufficient fixtures or review separate fixture preparation later.

## Guard and dependency ownership

The host reuses `TestDatabaseSettings` / `test_connection`, with no ordinary
Settings, dotenv, URL, environment-password, credential-file or database fallback.
Target is exactly 127.0.0.1:5432 / merge_test / merge_app / **0003_auth**.
An empty password, another configured target or Python `-O`/`-OO` is refused.
The hidden interactive prompt treats getpass echo-fallback warnings as errors.
CLI errors suppress argument values; passwords/secrets are never valid arguments.

The initial anchor and every subsequent logical Engine connection (new physical
connection or pooled reuse) check synchronous PostgreSQL/psycopg, actual DBAPI
`autocommit is False`, no inherited transaction, no AUTOCOMMIT execution option,
actual database/role/server IP/port, actual and default READ COMMITTED, read-only
guard transaction, 5s/15s lock/statement limits and exactly one revision 0003_auth.
The guard ends its own transaction with rollback. Service transactions keep their
original ownership, isolation/autocommit checks, deadlines, locking and commits.
A failed check invalidates the connection and latches the host closed, including
health. There is no fallback or recovery within the run. Final observers use a
separate fresh Engine with the same guards, not the suspect pool.

Both actual dependencies are overridden before ASGI startup:
`app.auth.get_services` returns real CredentialService, real SessionService behind
a scope facade, and real ThrottleService on the guarded Engine;
`app.read_api.get_read_service` returns real TeamReadService on that same Engine.
Authentication/CSRF still come from the real session service. The facade restricts
the validated principal to the manifest before exposing reads or revoking it.
Logout revalidates its actual principal immediately before the budgeted revoke.

Startup and every request audit the exact endpoint/method and dependency inventory,
both exact overrides and absence of ordinary auth_engine/auth_services/read_service.
The installed FastAPI's `iter_route_contexts` audits lazy included routers using
their effective dependencies. Unknown/missing/duplicate routes or dependencies,
removed/replaced overrides or an ordinary Engine fail before dependency resolution.
Framework docs/schema routes are disabled only in this test host. No new endpoint
is added. `/health=200` is still liveness, never independent acceptance evidence.

Original AuthBoundary executes before harness body/scope parsing. Exact Origin,
Fetch Metadata, JSON media, X-Merge-Request, actual peer/forwarded-header checks,
CSRF, cookie/session validation, throttle limits, safe errors and no-store remain
active. Scope refusal is 403 `browser_scope_rejected`; exhausted harness budgets
are not 429. Real throttle denial remains 429 with original Retry-After behavior.
No permissive CORS, header identity, proxy trust or security bypass is installed.

Policy is constructor-only (even malformed MERGE_AUTH_* is not parsed):

| Setting | Fixed value |
| --- | --- |
| origin / mode | http://127.0.0.1:5173 / development |
| cookie | merge_session_dev; HttpOnly; SameSite=Lax; Path=/; no Domain; Secure=False |
| backend bind | 127.0.0.1:8000; one worker; no reload |
| proxy policy | proxy_headers=False; forwarded_allow_ips=''; no trusted proxies |
| throttle | Original 300s / account-login 5 / IP-login 30 / IP-register 5 |
| throttle key | Fresh memory-only 32-byte test key shared for the whole process |

Both ports must be free before serving. The backend socket is reserved without
SO_REUSEADDR (Windows exclusive binding); no unrelated process is stopped. The
frontend port is checked then released for the owner's later Vite startup.
Logs are disabled process-wide while the CLI runs; Uvicorn request/access and SQL
debug logs are disabled. Only fixed phase/failure labels are printed. No exception
text, traceback locals, URL, bearer, HMAC key, row fingerprint or session details
are output. Do not attach external APM, debugger capture, request telemetry or
terminal transcription; this harness cannot sandbox arbitrary instrumentation.

## Manifest and separately approved write scope

Before inspect, identify and approve one to three **existing test accounts** by
exact public UUID and username, using zero write budgets. Inspect needs only the
DB-role password; account passwords are required for later login exercises.
Before serve, separately approve the exact login/logout budgets and run.
The CLI flag acknowledges that approval; it is not itself an authorization from
this implementation task. No manifest or live account was created by Codex.

Store a UTF-8 JSON manifest under the existing ignored directory, for example
`frontend/test-results/m011a/approved-run.json`. Exact keys:

```text
{
  "run_id": "<fresh UUID for this process/run>",
  "accounts": [
    {
      "user_id": "<actual retained account UUID>",
      "username": "<actual retained test username>",
      "login_attempts": <approved integer 0..30>,
      "logout_attempts": <approved integer 0..30>
    }
  ]
}
```

This is a schema illustration, not runnable JSON or fabricated fixtures. Duplicate
keys/accounts, extra fields, booleans as budgets, oversized files and secret fields
are rejected. The file contains no password, key, token, hash or session data.
Read-only inspection confirms each username maps to its declared UUID. The scope
file does not grant access: original credentials and validated sessions do that.

Budgets count admitted HTTP attempts, including invalid-password/429/failed-service
or lost-acknowledgement attempts; they do not automatically retry or refund. Strict
invalid bodies and out-of-scope usernames are rejected before throttle charging.
Concurrent budget reservations use a local mutex solely as a harness safety bound;
PostgreSQL remains the authority for sessions, throttles and domain correctness.
Logout budgets are charged only after real session/CSRF validation. Reads with a
valid cookie belonging to another account are rejected after real validation.

### Exact possible writes to merge_test

| Action | Possible committed effects |
| --- | --- |
| inspect / verify / preflight / final comparison / health | None; read-only SQL or no SQL |
| GET session / catalog / team pages/detail/My Team | None; real services use read-only transactions |
| Scoped login, incorrect password, unknown-password attempt or rate-limit attempt | Original login IP bucket charge; account bucket charge when IP admitted; rows can be inserted or counters updated, even on 401/429 |
| Scoped successful login | Those throttle charges plus one auth_sessions row; at most one issuance per admitted login attempt |
| Scoped valid logout | auth_sessions.revoked_at on the validated scoped session; no credential/team writes |
| Registration, malformed/out-of-scope/budget-exhausted login, rejected Origin/header/media, invalid CSRF | No harness-authorized writes; registration is always blocked; invalid CSRF never reaches revoke |

No user/account credential, membership/team/hackathon, idempotency, audit or outbox
write is supported. Do not confuse these limited writes with approval for a team
fixture or account-creation script. Nothing seeds or removes rows automatically.

## Exact owner commands - conditional on separate approval, NOT RUN in R4

After offline review and separate approval of live reads, in an interactive terminal
with no transcript/recording/APM, with an already reviewed manifest:

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m test_support.browser inspect --confirm-merge-test --revision 0003_auth --manifest I:\Merge\frontend\test-results\m011a\approved-run.json
if ($LASTEXITCODE -ne 0) { throw 'Guarded inspection failed. Stop.' }
```

Enter the existing merge_app password only at the hidden prompt. Environment
passwords are ignored; no environment setup is required. A noninteractive terminal
or unavailable hidden input refuses. Inspect does not start any HTTP listener or
create/repair fixtures. It verifies existing account identities and invariants,
not that their private passwords are known or that discovery has sufficient pages.

Only after separate approval of that run's scoped session/throttle writes:

```powershell
.\.venv\Scripts\python.exe -m test_support.browser serve --confirm-merge-test --revision 0003_auth --manifest I:\Merge\frontend\test-results\m011a\approved-run.json --allow-scoped-auth-writes
if ($LASTEXITCODE -ne 0) { throw 'Guarded host failed or final verification is incomplete. Stop.' }
```

The host prompts again and repeats all guards. Wait for
`Browser host ready; guarded loopback only.` It means startup guards and overrides
were accepted; it is not a browser pass. Then start only the owned frontend:

```powershell
Set-Location I:\Merge\frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Use exactly http://127.0.0.1:5173 in a fresh private profile with no loopback cookies,
extensions, sync or password saving. Existing Vite proxies /auth, /api and /health
without changing Origin. Never submit credentials directly to :8000 or localhost.
Do not capture forms/DevTools/private headers, HARs, traces or raw storage.

**Never run for this browser task:** ordinary `python -m app.serve`, direct
`uvicorn app.main:app`, any test_support Uvicorn factory/import-string shortcut,
URL/Settings overrides, Python optimization, alternate host/port, extra workers,
reload, database migrate/Alembic/provision/reset/cleanup, fixture seed scripts,
credential/role changes or unapproved guarded live suites. No --password, --url,
--host, --port, --workers or --reload option is accepted by this launcher.

## Shutdown and invariant verification

Stop browser interaction, close the private profile and Ctrl+C only the owned Vite
terminal, then Ctrl+C the owned backend once. Uvicorn stops accepting requests and
allows up to 25 seconds to drain. BrowserServer delegates to installed Uvicorn
0.54.0, observes _wait_tasks_to_complete and requires positive normal completion
with empty protocol connection and request-task sets. Cancellation, timeout,
forced exit, shutdown exceptions or unresolved work set a sticky failed-run bit.
A zero-deadline timeout before the callback even starts also fails closed.
Residual work at server.run return is latched before final snapshots, so later
completion or a successful snapshot cannot erase that failure. The predicate is
checked again before allowing success. The original request-cancellation/database
failure latch and lifespan-completion marker remain mandatory too.

Uvicorn cancellation is not proof a synchronous worker or PostgreSQL transaction
stopped. A timed-out/forced run remains unsuccessful even if work later finishes.
Final snapshots on those paths are read-only diagnostics and never a pass. The
owned listener is closed by Uvicorn and its outer context; Engine/listener cleanup
still runs through finally/context managers. Engine.dispose does not forcibly
terminate an already checked-out worker connection. A hard kill or repeated
interrupt can prevent cleanup/final inspection entirely; retain the run as
inconclusive and do not infer rollback, stopped transactions or intact evidence.

Do not kill unrelated processes, rotate the key or restart to evade a 429. This
process is the whole run; no resume/restart mechanism or persisted throttle key
exists. A later run needs a fresh reviewed scope after prior cooldowns/evidence.

After draining, an independent Engine checks fresh committed state and compares it
with the private pre-run snapshot. Users, credentials and all domain table
counts/fingerprints must match. Existing session immutable fields must match;
only scoped terminal revocations and bounded new scoped sessions may differ.
Only bounded run-key login IP/account buckets may be added; unrelated buckets must
match and no rows may disappear. Team capacity, leadership, frozen sizes, deletion,
one-membership, orphan and session invariants are checked before and after. These
checks allow real retained memberships; they do not impose SessionEnvironment's
zero-membership assumption. No existing fixture invariant was changed.

Require `Browser host final invariants verified; fixtures retained.` **and exit 0**.
The label is now emitted by main only after final comparison, both Engine-owner
contexts and the outer listener context have exited successfully. Missing/failing
checks, drain/guard latch, forced exit or incomplete lifespan shutdown return 1
through the sanitized operational failure handler. Observer/comparison/cleanup
exceptions and interruption during final inspection also return 1; bad CLI input
is exit 2. No finally block returns success or clears an earlier failure. An OS
termination may bypass this handler and leave no final evidence; it is not a pass.
Final verification is attempted even if server startup/shutdown fails, but cannot
qualify an incomplete drain. Preserve rows; no database cleanup runs.

An optional independently approved post-run current-state inspection is:

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m test_support.browser verify --confirm-merge-test --revision 0003_auth --manifest I:\Merge\frontend\test-results\m011a\approved-run.json
if ($LASTEXITCODE -ne 0) { throw 'Current-state verification failed. Stop.' }
```

Verify is read-only and prompts privately. It cannot reconstruct a lost in-memory
before-state, prove a forced run had no extra effects, or turn missing final
comparison into a pass. Do not rerun serve to repair an incomplete result.

## Remaining limits and offline evidence

This is a safety harness, not a malicious-code/OS/role isolation boundary. The
shared merge_app role, trusted local Python, browser origin and Vite remain trusted.
No unrelated database writers may run during acceptance: READ COMMITTED evidence
is a series of snapshots, and changes by another writer deliberately fail the
comparison. Whole-table aggregate fingerprints can be costly and are not a load
benchmark or adversarial tamper proof. Real server/revision/DDL and SQL
behavior have not been exercised by R4; live owner verification remains required.
Original auth error/timing and production HTTPS/XSS/telemetry limitations remain.

Offline test commands and actual results are recorded in PROGRESS.md. TestClient
uses in-process ASGI transport and service doubles; no live browser/server or
PostgreSQL result is inferred. Registration acceptance, absent known retained
credentials, adequate page fixtures and deterministic delayed delivery remain
separate blockers. No G1, production, HTTPS or full-browser claim.

Owner exercise: remove either dependency override in an offline test; explain why
the next request returns 503 before ordinary Settings can run. Then lower one
manifest login budget and predict the distinction between harness 403 and real
throttle 429.

## Browser acceptance record — every item pending

Record browser/version, source HEAD plus uncommitted scope, run ID, target/revision
guard result, viewport, expected/actual outcome and sanitized evidence filename.
Do not mark a pass from a component test or a missing-cookie HTTP check.

1. **Auth:** register approved account -> 201 confirmation without sign-in;
   login -> 200 workspace; reload -> restored session; logout -> 204, cleared
   cookie and guest UI; next GET -> 401. Incorrect credentials must give safe
   feedback and no invented session. A lost logout acknowledgement must hide
   private data and show uncertainty/session recovery.
2. **Cookies/storage:** privately inspect attributes only, recording booleans:
   correct development cookie name, HttpOnly/Lax/Path=/, no Domain, local Secure
   false. Session bearer must be absent from JSON/DOM/JS stores/URLs/logs and
   unreadable via document.cookie. HttpOnly browser cookie storage is expected;
   privileged DevTools can inspect it and must not be captured. CSRF appearing
   in session JSON and memory is intentional, not a bearer leak. No cookie copy,
   raw storage dump, HAR, trace, heap snapshot or Network/React-state screenshot.
3. **Reads:** catalog and both cursor pages in declared ordering, Previous and
   reset behavior; selected-hackathon teams/detail remain scoped. Show actual
   counts/readiness/leader. Correlate the selected public UUID with the manifest;
   repeated retained fixture names alone do not identify the intended hackathon.
   Check membership and exact 200 {"team":null} using
   the declared two users/fixtures; no invented memberships. Disabled join must
   send no request. A missing team/hackathon must show safe 404 feedback.
4. **Desktop/mobile/keyboard:** desktop 1440x900, mobile 375x812 and 320x740,
   plus 200% zoom; no horizontal clipping, visible focus and labelled controls.
   Tab from skip link through forms, hackathon selector, page controls, detail,
   My Team and logout. Enter/Space must work. Verify heading focus after view
   changes, status/error announcements and reduced-motion preference. Record
   screen-reader coverage honestly; jsdom is not accessibility acceptance.
5. **Failure recovery:** 401 after normal scoped revocation/expiry must clear
   the workspace; 403 must not be reported as login success; scoped 429 must
   honor cooldown and never auto-resubmit; network/503 recovery must be explicit.
   Use a reviewed browser-only response fault for otherwise unavailable faults,
   mark it injected and leave real auth/throttle validation intact. Do not damage
   the database or change production policy to create an error.
6. **Stale response:** use the reviewed browser-only gate described below for
   both an old successful GET and a real revoked-session 401 when available.
   After new login, release the old response: neither old data nor its 401 may
   change the new workspace. Also switch hackathons during a delayed read.

### Deterministic stale-response gate, proposed separately

Generic Slow 3G throttling affects auth too and does not reliably hold one
completed response. Browser abort may cancel it entirely; cancellation alone
does not prove the late-completion branch. Prefer a tiny test-only browser
instrument reviewed before use, not a backend endpoint or production fetch edit:

- Arm only one exact manifest-scoped team GET, never /auth or a POST. Fetch it
  through the real same-origin transport, consume its actual response in memory,
  then pause delivery of that response to the application. Fabricate no team,
  identity or membership. Do not capture Cookie/CSRF headers or auth bodies.
- Hold at most 15 seconds (application deadline is 20s); stop if login/logout
  cannot finish in that interval. Expose boolean armed/held/released states and
  a release control only, with no payload output. Keep all other requests normal.
- While held, sign out and sign in with the approved other account. Release even
  after the old AbortSignal fires to exercise the active/generation guard, using
  the already obtained real response. A real-browser injected late-delivery test
  is distinct from a natural network race; label the evidence accordingly.
- Restore original fetch and clear the gate/body/timer in finally, including
  timeouts/navigation. Do not delay a database transaction, introduce a test
  bypass route or persist response data. Offline tests must cover restoration,
  timeout and refusal to arm auth/unscoped URLs. No browser tool/dependency is
  assumed installed; review the delivery method before claiming reproducibility.

Safe screenshots, once actually run: blank auth page, discovery desktop/mobile,
team details, null/present membership and a sanitized error state using approved
public test labels. Capture UI only after hiding forms/DevTools/notifications;
inspect each capture privately before retaining under existing ignored
frontend/test-results/m011a/<run-id>/. No credentials, cookie values, CSRF, raw
headers or real personal data. Record skipped captures as skipped, not evidence.

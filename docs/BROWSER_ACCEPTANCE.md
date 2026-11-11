# M-011A-R4 - test-only guarded browser host

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

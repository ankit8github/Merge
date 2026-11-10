# Guarded browser host - R4 correction and historical R3 audit

**R4: B1 corrected and offline regression green; owner review before live work.**
No live backend/browser/Vite, PostgreSQL access, credential prompt or approval
manifest was created. R3 findings below describe the audited pre-fix state; this
section and the R4 PROGRESS entry control the current shutdown status. Existing
account/fixture/write-approval prerequisites remain in force. G1 is open.

## R4 root cause and smallest correction

Uvicorn 0.54.0 catches drain TimeoutError internally and does not set force_exit.
R2's indirect reliance on cancellation reaching an ASGI request missed lingering
connections without active requests. A successful database snapshot could then be
mistaken for a fully completed run. R3 reproduced this with real installed Uvicorn
shutdown code and fake resources; its required-behavior assertion was left red.

R4 adds only test_support.browser.BrowserServer to wrap the pinned Uvicorn drain
hook and shutdown, uses it in serve, and moves the success print to main after
resource contexts close. The subclass delegates actual shutdown/closing to Uvicorn;
it does not replace its algorithm, install global patches or alter production
app.serve. No database transaction/service, dependency guard, auth boundary,
manifest, policy, schema or dependency change is needed.

Guarantees now required before a success label/exit 0:

1. The drain coroutine has returned normally, with no protocol connections or
   request tasks left. Neither server.run returning nor cancellation is sufficient.
2. A sticky drain_failed bit is clear. Timeout cancellation (including timeout
   before callback entry), forced exit, shutdown exceptions and unresolved work
   latch failure. Residual work at server.run return is latched before observer
   work and rechecked later; finishing during a snapshot cannot clear failure.
3. Existing database/request failure latch is clear, original app state is still
   safe, and the application lifespan shutdown marker is present.
4. Independent fresh guarded final snapshots and comparison have passed, all
   Engine-owner contexts have disposed their owned resources, and the listener
   context has closed. Only then does main print final verification success.

The first handled Ctrl+C may finish normally and qualify only if all checks pass.
Uvicorn's second interrupt sets force_exit; interrupted observers/cleanup and
exceptions propagate to the sanitized exit-1 handler. Invalid CLI is exit 2. A
hard OS kill can skip Python cleanup and produce missing evidence; no successful
verification is inferred. No cancellation, Engine disposal or failed snapshot
proves a remote transaction rolled back or an in-flight worker stopped. Diagnostic
snapshots after an incomplete drain cannot certify the run. No fixture cleanup or
new write is introduced.

The supported synchronous services finish their worker call before a normally
completed request task returns; timeout/cancel paths cannot qualify. Offline tests
hold a simulated database worker, prove clean drain waits for its completion,
and separately prove cancelled request tasks can coexist with a still-running
worker. That run remains failed even after the worker and later snapshots finish.
This is not real PostgreSQL termination or browser evidence. Arbitrary detached
workers/external writers are outside this inspected application's guarantees.

The hook is a private Uvicorn method: the project pins 0.54.0, the tests exercise
that installed implementation, and any future Uvicorn upgrade must re-audit the
hook/cancellation/timeout contract. No library change is made by R4.

## Exact minimal R4 source diff against the reviewed R3 file

```diff
--- R3/browser.py
+++ R4/browser.py
@@ -367,0 +368,39 @@
+class BrowserServer(uvicorn.Server):
+    """Record the drain Uvicorn's shutdown() otherwise swallows on timeout.
+
+    Uvicorn 0.54.0 wait_for cancels _wait_tasks_to_complete on timeout; a zero
+    deadline can cancel it before entry. Require positive completion as well as
+    a sticky failure bit and empty protocol/task sets. Cancellation is not proof
+    that a synchronous request worker or its database transaction has stopped.
+    """
+    def __init__(self, config):
+        super().__init__(config)
+        self.drain_complete = False
+        self.drain_failed = False
+
+    def drained(self):
+        return (self.drain_complete and not self.drain_failed and not self.force_exit
+                and not self.server_state.connections and not self.server_state.tasks)
+
+    async def _wait_tasks_to_complete(self):
+        try:
+            await super()._wait_tasks_to_complete()
+        except BaseException:
+            self.drain_failed = True
+            raise
+        self.drain_complete = not (self.force_exit or self.server_state.connections
+                                   or self.server_state.tasks)
+        if not self.drain_complete:
+            self.drain_failed = True
+
+    async def shutdown(self, sockets=None):
+        try:
+            await super().shutdown(sockets=sockets)
+        except BaseException:
+            self.drain_failed = True
+            raise
+        finally:
+            if not self.drained():
+                self.drain_failed = True
+
+
@@ -377 +416 @@
-        server = uvicorn.Server(config)
+        server = BrowserServer(config)
@@ -385,2 +424,4 @@
-            # server.run returns only after draining/shutdown. A forced exit cannot
-            # count as a pass, even if a new independent observer can still connect.
+            if not server.drained():
+                server.drain_failed = True
+            # The observer is diagnostic after an incomplete drain: workers may
+            # still finish. Its result cannot clear the server drain failure.
@@ -391 +432 @@
-        if (not server.started or server.force_exit or guard.failed.is_set()
+        if (not server.started or not server.drained() or guard.failed.is_set()
@@ -395 +435,0 @@
-        print('Browser host final invariants verified; fixtures retained.', flush=True)
@@ -406,0 +447,2 @@
+                # Only after observer comparison, Engine disposal and socket close.
+                print('Browser host final invariants verified; fixtures retained.', flush=True)
```

## R4 verification

The unchanged R3 timeout regression passes. New offline cases cover normal clean
drain with a held worker, a first graceful interrupt, timeout with an active
request and surviving worker, zero-timeout before callback entry, sticky failure
after later completion, residual requests (including completion during observer
work), double interruption, observer/comparison/lifespan/listener/Engine cleanup
failure, and interruption during final checks. All original assertions are
preserved; the preexisting lifecycle fake now models the selected BrowserServer
and its explicit drain outcome. No test was skipped, weakened or xfailed.

Final R4 harness suite: **127 passed in 7.26s**; full offline backend:
**933 passed, 32 deselected in 23.43s**, both exit 0 with one existing warning.
Frontend typecheck, **52 tests in 14.86s**, and build passed. Exact commands,
protected-source/AST checks and Git inventory are in the R4 entry of PROGRESS.md. FRONTEND/TEST_DATABASE/BROWSER_ACCEPTANCE
notices now distinguish the corrected offline defect from still-pending owner
approval and live verification. The historical R3 audit evidence
below remains unchanged except its explicit historical-status annotation.

Owner exercise: keep a fake worker blocked in the timeout test; explain why the
request task's cancellation and a later passing snapshot cannot grant success.
Change the test deadline and identify the positive drain-completion evidence,
without deleting or weakening the original R3 assertion.

## Historical R3 audit - pre-fix findings and evidence

**Historical R3 verdict: HOLD; B1 was reproducible before the R4 correction.**
Audited 2026-11-10 against HEAD `cc67e18ffd6a6845642170fa358ecc48d2fef38b`
and the uncommitted M-011A/R1/R2 tree. No PostgreSQL, live backend/Vite/browser,
credential prompt, approval-manifest creation, migration, fixture mutation,
cleanup, privilege change, staging, commit or push was performed.

This is an offline source/test audit, not certification of a live PostgreSQL or
browser environment. It supersedes R2's claim that every drain timeout necessarily
makes the run nonzero. The two harness implementation files are unchanged in R3.

## Blocking finding B1: a drain timeout can report success

Source: browser.py:381-395 and the installed uvicorn/server.py:282-311.
The installed Uvicorn 0.54.0 shutdown method catches asyncio.TimeoutError, logs an
error, cancels the current request-task set, then completes lifespan shutdown.
It does not set force_exit or expose a timeout flag to this harness.

The host only detects the timeout indirectly when a cancelled ASGI request reaches
ClosedHost's BaseException handler. With a lingering protocol connection and no
active request task, nothing sets ConnectionGuard.failed. Uvicorn can return with:

- server.started = True;
- server.force_exit = False;
- guard.failed = False;
- app.state.browser_shutdown_complete = True;
- an unchanged before/after database snapshot.

The predicate at browser.py:391 then accepts the run; it prints the final success
label and main returns 0 despite exceeding the graceful drain deadline. Logging is
disabled, so the Uvicorn timeout diagnostic is also suppressed. This is an evidence
and shutdown-safety defect; it is not evidence of a merge_dev connection or a
security-policy bypass.

The new test `test_drain_timeout_without_request_task_must_exit_nonzero` reproduces
this using the **installed Uvicorn shutdown implementation**, one fake lingering
connection, no request tasks and a zero-second timeout to enter the same branch
without waiting 25 seconds. Uvicorn run/startup/serve, HTTP binding, credentials,
Engine creation and snapshots are replaced by fakes. The required assertion
`result == 1` fails because the current harness returns 0. The test remains red:
no xfail/skip and no weakened existing assertion. It must turn green before live
startup is proposed.

Required bounded repair, not implemented by this audit: explicitly latch/report
the server drain-timeout outcome and reject it independently of request-task
cancellation; check drain/lifespan completion and outstanding work directly. Do
not infer graceful completion solely from server.run returning. Preserve the fresh
final observer and resource disposal; a timeout's final snapshot may be diagnostic
but must never earn a success label. Add coverage with and without active tasks,
forced/repeated interruption and a normal successful shutdown. Production auth,
TeamService and database invariants need no change to repair this host-only issue.

## Startup trace, manifest through first accepted request

| Phase | Exact path and safety boundary |
| --- | --- |
| Import | browser imports app.main.create_app; the ordinary module app is constructed but never served and its lifespan is not entered. No ordinary Settings or Engine is initialized by that construction. |
| CLI | arguments() requires inspect/serve/verify, --confirm-merge-test, exact --revision 0003_auth and a manifest path. serve also requires --allow-scoped-auth-writes; read commands reject that flag. Optimization and unknown arguments are rejected with fixed text before prompt/connection. |
| Manifest | main -> quiet_logs -> read_scope. JSON duplicate-key detection, 8192-byte bound and strict frozen RunScope/AccountScope validation precede credential prompting and Engine creation. |
| Socket reservation | serve calls reserved_socket: exact 127.0.0.1:8000, no SO_REUSEADDR; Windows exclusive bind. Port 5173 is checked and released. Binding reserves a socket; it does not accept HTTP requests. Occupied ports stop startup. |
| Credential | isatty plus getpass; empty input and GetPassWarning echo fallback refuse. Only the database role password is prompted here. Account passwords are never manifest/CLI values. |
| Initial connection | guarded_engine validates TestDatabaseSettings.url/password, enters the existing test_connection owner, applies the full guard to its anchor, then installs engine_connect before exposing the Engine. The helper's first identity SELECT precedes the full browser guard; it is read-only SQL and no service/domain work is reachable before full verification. |
| Preflight state | Engine.connect invokes the installed guard. snapshot sets READ ONLY, confirms each username maps to the declared UUID, checks session/team invariants and privately fingerprints state; rollback ends that transaction. No fixture writes occur. |
| App composition | local_policy uses BrowserPolicy constructor input only. browser_app checks fixed policy/write opt-in, creates original routes/middleware, disables framework docs/schema, builds real services on the guarded Engine and installs both overrides. |
| Uvicorn | One worker, no reload, proxy_headers=False, forwarded_allow_ips='', access_log=False. The in-memory ASGI object and reserved socket are supplied directly; no ordinary app import-string launcher is used. |
| Lifespan | Original lifespan receives the explicit policy and sets ordinary auth/read state to None. The wrapper audits wiring, checks the latch, then prints its ready label. This label precedes the listener's completed startup and is not independent readiness/browser evidence. |
| HTTP entry | ClosedHost audits wiring and the latch before calling FastAPI. A missing/replaced override or unexpected route/dependency returns private no-store 503 and latches closed before dependency resolution. |
| Original policy | AuthBoundary checks actual peer/forwarding, Origin, Fetch Metadata, media type and X-Merge-Request before FastAPI body/dependency processing. |
| Resolution | Login bodies are validated again by the strict original model before the scope budget is charged. Registration is refused. Authenticated reads/logout decode the cookie and call real session validation plus the scope facade; read services are guarded and read-only. |

The startup path currently passes these offline checks, but B1 prevents a ready
verdict for the whole run.

## Dependency and ordinary-Settings proof

browser.py:249 installs exactly:

- app.auth.get_services -> scoped_auth, returning real CredentialService,
  ScopedSessions(real SessionService), real ThrottleService;
- app.read_api.get_read_service -> scoped_reads, returning real TeamReadService.

All four real services receive the **same guarded Engine**. scoped_reads does not
need to call the ordinary dependency: the original read router independently
requires authenticated_session, and the audited effective dependency inventory
contains authenticated_session, session_cookie, get_services, get_read_service
and read_request. scoped_auth neither calls its ordinary counterpart nor builds
Settings. In the ordinary code, Settings/build_engine is only reached inside
get_services when auth_services is None. The original get_read_service can only
use auth_engine and is also replaced.

At startup and before each HTTP request, audit_wiring checks exact override
function identities, exact endpoints/methods, expected dependency sets, one health
route, no duplicate/unknown routes and auth_engine/auth_services/read_service all
None. It uses installed FastAPI iter_route_contexts for effective lazy included
routers. The request wrapper executes this audit **outside and before** the
FastAPI application. Removing an override cannot first reach the ordinary lazy
initializer. Existing and new tests make ordinary Settings/build_engine raise if
called; authorized auth/read paths, missing overrides and unknown dependencies
exercise that boundary without calling them. Production imports/package selection
exclude test_support. These are proofs for this inspected code and the trusted
Python/application boundary, not protection against arbitrary in-process code
rewriting functions or injecting middleware after the audit.

## Connection audit

browser.py:58-112 applies the guard to the initial anchor and via engine_connect to
every subsequent logical Engine.connect, whether backed by a new or pooled DBAPI
connection. Each owned final observer creates a fresh guarded Engine too.

| Check | Required value |
| --- | --- |
| Configured target | confirmed=True; 127.0.0.1:5432 / merge_test / merge_app; nonempty explicit password |
| Driver | synchronous postgresql / psycopg |
| Transaction entry | no inherited SQLAlchemy transaction; actual DBAPI autocommit is False; no AUTOCOMMIT execution option |
| Actual identity | current_database merge_test; current_user merge_app; inet_server_addr 127.0.0.1 (optional /32); inet_server_port 5432 |
| Isolation | connection.get_isolation_level READ COMMITTED; server transaction_isolation and default_transaction_isolation read committed |
| Guard transaction | SET TRANSACTION READ ONLY and current_setting transaction_read_only = on |
| Deadlines | connect_timeout 5 seconds; guard verifies lock_timeout 5s and statement_timeout 15s |
| Revision | public.alembic_version yields exactly [0003_auth] |

A guard exception sets the shared failure Event, attempts connection.invalidate,
and raises a fixed sanitized DiagnosticFailure. Invalidation errors are suppressed;
even if invalidation itself fails, no guarded connection is yielded and the latch
continues to block requests/checkouts. Successful guards roll back their own read
transaction so services can begin theirs. Existing services independently reject
AUTOCOMMIT, wrong dialect/isolation and inherited transactions. Credential/session
transactions use 5s/15s; original throttle transactions deliberately tighten these
to 1s/2s with SET LOCAL, which resets at transaction end. There is no fallback Engine
or merge_dev target. A connection-creation/checkout exception before engine_connect
runs does not itself set the running-host latch; it still fails the request/startup
without fallback. That distinction is outside the narrower failed-guard claim.

No real PostgreSQL/pool/reconnect behavior was exercised. Offline doubles verify
the callback, repeated guard execution and event registration/removal; source
inspection establishes the connection ownership. A revision marker is not an
adversarial DDL/ACL attestation.

## Manifest schema, client input and owner approval

Exact schema: required UUID run_id; accounts array of 1-3 objects. Each object has
required UUID user_id, username matching ASCII [a-z0-9_]{3,32}, and required strict
integer login_attempts/logout_attempts, each 0-30 inclusive. Duplicate user UUIDs
or usernames, unknown/missing fields, invalid UUIDs, non-integer/boolean budgets,
out-of-range budgets, duplicate JSON keys, malformed/missing/oversized files refuse.
There are no account/budget defaults or environment sources. Invalid scopes are
rejected before the hidden prompt; account mapping is then confirmed by read-only
SQL before service use.

Safe schema example using placeholders only (deliberately not executable JSON):

```text
{
  "run_id": "<OWNER-SELECTED FRESH RUN UUID>",
  "accounts": [
    {
      "user_id": "<EXISTING APPROVED TEST ACCOUNT UUID>",
      "username": "<EXISTING APPROVED TEST USERNAME>",
      "login_attempts": <APPROVED INTEGER 0 THROUGH 30>,
      "logout_attempts": <APPROVED INTEGER 0 THROUGH 30>
    }
  ]
}
```

No approval manifest was written by this audit. Parser tests use in-memory mocked
file contents; existing R2 parser tests use only pytest temporary synthetic files.
No file under frontend/test-results was generated or inspected.

The reviewed file is the human approval boundary: the program cannot determine
that an owner approved an otherwise syntactically valid existing account. There
is no signed approval registry or special fixture-account database flag. The
owner must approve the exact file and account usage separately from this audit.
Membership/account UUIDs in client bodies do not create authority; strict input
models reject attempted user_id/run_id/budget/identity fields. Client usernames
can select only manifested accounts and cannot change their UUIDs or budgets.
Actual authenticated principals are checked against both UUID and username.

Budgets are frozen at parse time and reserved under a mutex. Admitted login
attempts consume budget even when credentials fail, throttling denies, a service
fails or the response is lost. Logout charges only after actual session and CSRF
validation. This is a test-run safety budget, not domain race synchronization.

## Endpoint and browser protections

Registration remains a known original route but its scoped dependency refuses it
before throttle/register work; encoded/trailing-slash forms are also covered by
new tests. No domain mutation route is included. Exact route inventory rejects
new/unknown endpoints; domain POST probes return 404/405. TeamService and all
production auth code are unchanged.

Original Origin/Fetch Metadata/media/custom-header/forwarding checks precede scope
parsing. Cookie encoding/validation, real CSRF verification before revoke, durable
throttle behavior and Retry-After handling remain the original implementations.
Fixed development cookie: merge_session_dev, HttpOnly, SameSite=Lax, Path=/,
no Domain, Secure=False. Origin is exactly http://127.0.0.1:5173. No CORS/proxy trust
or alternate client identity is introduced. Fixed CLI has no host/port/worker/reload
options; direct non-loopback helper inputs are refused. BrowserPolicy ignores all
environment/dotenv/file-secret settings. Fixed database settings ignore MERGE_DB_*.

The database password enters only through interactive hidden getpass; no password
argument or environment fallback is accepted. SQLAlchemy internally stores it in
its URL/connect configuration to authenticate: **it is not absent from all memory
or internal URL objects**. It is excluded from printed/browser URLs, output,
argument history and normal logs/tracebacks. Secret repr fields are redacted and
SQL parameters hidden. CLI/runtime failures use fixed allowlisted diagnostics,
logging is disabled while running, and no private snapshot/session values are
printed. External debuggers, tracing/APM, OS inspection and modified libraries are
trusted and cannot be certified by this harness. Do not enable them during a run.

## Shutdown audit, including what does fail closed

Normal intended sequence: Uvicorn stops accepting, drains, enters application
shutdown; wrapper re-audits and sets shutdown-complete; independent guarded Engine
reads committed after-state; compare requires unchanged users/credentials/domain,
bounded scoped session issuance/revocation and run-key login buckets only; owned
resources are disposed. Exceptions from observer/compare/disposal propagate to
main's fixed diagnostic and return 1. __main__ raises SystemExit(main()), so the
status reaches PowerShell. CLI rejection is exit 2. Startup failure, force_exit,
guard latch or missing shutdown marker rejects success. Interrupted final checks
return nonzero/missing final evidence; standalone verify cannot recover a lost
before-state. Those paths are covered by existing tests.

**The timeout-without-cancelled-request case B1 is not rejected.** Thus task 12
cannot be confirmed and the implementation is not ready. Do not use the prior R2
success/exit-0 rule as sufficient evidence until B1 is repaired. No revised live
startup commands are proposed in R3. R2 commands are retained as historical,
conditional syntax under a HOLD banner; do not run them based on this audit.

## Required owner accounts, data and approvals

Actual retained IDs, account passwords and browser sessions are **unknown to this
audit**; no database/private attachment/credential-store inspection was performed.
Do not infer usable accounts from old fixture names or aggregate test counts.

| Exercise | Required retained prerequisites |
| --- | --- |
| Read-only inspect/verify | Existing merge_app database-role password, local merge_test at exact 0003_auth and approved account UUID/username mappings. No account password is needed merely to inspect mappings/invariants. |
| Authenticated session/discovery reads | A scoped live valid browser-managed session. In a fresh profile it normally requires login with a known private retained-account password, which writes session/throttle state and requires separate approval. Never extract/copy stored hashes, bearer or CSRF material to manufacture access. |
| Login/logout/cookies/failure/throttle | 1-3 approved retained credentialed accounts, known private test passwords, exact per-account attempt/revocation budgets and explicit scoped-auth-write approval. A dedicated account/budget for deliberate failures/429s is preferable; normal limits stay unchanged. |
| Present/null My Team | A credentialed manifested account already a member and another credentialed account without membership in the same declared existing hackathon. Public UUID-only fixture founders are not necessarily login accounts. No joining or credential reset is authorized. |
| Detail/order/pagination | Owner-declared existing hackathon/team UUIDs; at least 21 visible live teams in one hackathon for two default 20-item team pages. Catalog pagination separately needs enough hackathons. ReadEnvironment's three teams do not satisfy team-page acceptance. |
| Cross-login stale responses | Two usable approved accounts, login/logout budgets, suitable real read data and a separately reviewed deterministic delay instrument. That instrument is still unimplemented. |
| Expired/revoked session | Natural expiry or normal budgeted logout; no direct backdating/revocation SQL or new endpoint. |

Before later live work: repair B1 and rerun its tests; approve that concrete host
revision; identify and approve retained account mappings and exact public domain
fixtures; confirm known private passwords without sending them into chat/files;
approve live reads separately from session/throttle writes; review the exact
manifest and row/attempt budgets; arrange an exclusive run with no unrelated DB
writers, free loopback ports, private terminal/profile and no secret telemetry.
No approval is requested or inferred by this audit.

Unavailable credentials prevent real login, session issuance/restore/logout,
authenticated discovery and cookie/CSRF browser acceptance. Missing memberships
prevent present/null comparison; too few teams prevent second-page evidence.
Registration is impossible through this host regardless of fixtures. This local
HTTP host cannot prove production Secure/HTTPS/proxy behavior, complete accessibility,
real browser layout, load/CI/concurrency gates or G1. Mocked errors/delay do not prove
natural network races. No seeding, resets, extraction or weakened page size is a
substitute for missing prerequisites.

## Nonblocking limitations and follow-up scope

- Manifest approval is human/file based; arbitrary trusted local code, shared
  merge_app privileges and external instrumentation remain outside isolation.
- Initial account-to-UUID mapping is checked before serving and again at final
  inspection. ScopedSessions.login checks the returned principal after the real
  login has committed. Therefore exclude concurrent credential/account writers;
  this facade is not a pre-commit UUID guard against a malicious concurrent rename.
- The run_id is metadata, not a durable single-use authorization. Budgets and the
  random throttle key reset in a new process. The documented no-restart/no-key-
  rotation rule requires owner discipline; it is not enforced across processes.
- Whole-table fingerprints require an exclusive run, can be costly and are not
  adversarial tamper proof; READ COMMITTED statements are not one global snapshot.
- A frozen revision marker is not live schema/permission verification. Timeouts,
  cookie enforcement, socket behavior and actual PostgreSQL queries need later
  approved live evidence. No failure category implies a proven connection target
  when connection establishment itself failed.
- Ready is printed during lifespan before the listener finishes startup. Treat it
  only as guard/wiring acceptance, as R2 already says; no live readiness was proved.

Owner exercise: run the new failing offline timeout test, trace why the four
current success flags all pass, and explain which explicit shutdown outcome a
host-only fix must capture. Do not remove/weaken the assertion to obtain green CI.

## R3 evidence

Exact commands and environment are in PROGRESS.md. Fresh harness suite:
**1 failed, 112 passed in 5.74s**; full database-free suite:
**1 failed, 918 passed, 32 deselected in 29.33s**, both exit 1 with the same new
timeout regression and one existing warning. Original 82 cases remain green.
Compile/AST/import/packaging/protected-source, pip check and git diff --check
passed. Pending Git inventory: 28 files (12 tracked modifications, 16 untracked),
empty index, unchanged HEAD. No current all-green or live-ready claim is made.

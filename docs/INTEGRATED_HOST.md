# Independent exact-0006 integrated acceptance host

**2026-11-15 recovery overlay:** the original run is permanently consumed and
uncertified. Its saved drain-stage failure cannot distinguish readiness, drain
predicates or incomplete ledger. See [BATCH_D_RECOVERY.md](BATCH_D_RECOVERY.md)
for the immutable receipt identities, diagnostic-only correction, offline results
and release priorities. No old command below authorizes a restart of that scope.
New instrumentation records startup/readiness/shutdown flags, aggregate GET/auth
counts and exact failed drain predicates; ledger completion has its own stage.
The fixed ready banner follows successful Uvicorn startup; it is not final
campaign certification or an external HTTP health response. No live correction
or fresh campaign was exercised. Existing completion/create-once rules remain.

2026-11-14. **CONDITIONAL for owner review; implemented and offline tested only.**
No PostgreSQL connection, provisioning/migration, Uvicorn/Vite/browser startup,
fixture reset/deletion/adoption, deployment or Git commit/push occurred here.

## Bounded component and starting state

Actual main HEAD is db17f3ef2c2934d2d4cc7db06499a291949a3d16. All18 starting
pending paths were unstaged and matched the supplied baseline. No reset/discard.
The starting evidence inventory contained754 files, rather than the reported733;
the earlier733 subset and the additional existing ignored logs/diagnostics are
preserved. The difference is16 JSON files and5 logs already present at task start.
This count difference is not new live evidence.

Objective: implement the missing host, server ledger, independent observer and
source/native-exit evidence composition for the unchanged public campaign.
Targets: five new backend release_support modules, two new backend harness-test
files, a test-only JS evidence verifier/test, this document, the existing offline
readiness helper/test and additive INTEGRATED_ACCEPTANCE/PROGRESS overlays.
No application, schema, dependency, migration, session, lock, domain transaction
or production deployment change. No change to either old browser host, old
manifest, old fixture, old allowlist or original G1/SSE/lifecycle certificate.

Acceptance: exact target/revision/role/Origin, closed route/dependency graph,
all38 HTTP attempts and14 effects, fresh namespace refusal, current-session
CSRF/actor authority, no retry after unknown outcome, exact final scoped/global
checks, true native exits, complete source-bound owner observations, failure
retention, and all requested offline suites/build/static checks.

## A. Architecture and closed route coverage

```text
owner CLI supervisor (hidden credential; fixed profile30 proof)
  -> native host worker / loopback8000 / one worker / no reload
       -> closed ASGI POST gate and identity-scoped ledger
       -> unchanged AuthBoundary / session / CSRF / real services
       -> unchanged PostgreSQL transactions, constraints and outbox
       -> drain and complete ledger
       -> separate native READ-ONLY observer process over private stdin
  -> source/native-exit process receipt

owner-operated browser observations + hashed artifacts
  -> fixed Node evidence verifier (no browser/network startup)
  -> offline final evidence join / new retained review report
```

`integrated_host.py` is independent of browser_full.py. It has23 exact
method/path/endpoint entries plus GET /health (24 total), nine explicit service
overrides, and a closed transitive dependency audit at lifespan entry, every
request and shutdown. It checks effective **and retained original** endpoint
identity. Missing/extra route, method, endpoint, dependency or override fails.
Docs/OpenAPI routes are absent. auth_engine/auth_services/read_service stay None;
there is no ordinary Settings or merge_dev engine fallback. No module-level
live ASGI entry point is exported.

| Route group | Supported methods / coverage |
| --- | --- |
| /auth/register, /auth/login, /auth/logout; /auth/session | POST registration/login/logout; GET real current session |
| Catalog, board, detail, own membership | Existing four authenticated GETs |
| Team creation | Existing POST /api/hackathons/{h}/teams |
| Requests | POST create/decision; GET own request and leader pending requests |
| Invitations | POST issue/redeem; GET own inbox |
| **Additional lifecycle** | GET /teams/{t}/members; POST /teams/{t}/leave and /teams/{t}/members/{u}/remove |
| **Additional profiles/matching** | GET/POST /api/me/profile; GET /teams/{t}/suggestions |
| **Additional realtime** | GET /api/hackathons/{h}/events, original authenticated SSE endpoint |

The old exact0005 host still excludes those seven additional method/path
entries. Its own16 entries plus health and original dependency audit remain
byte-identical. The old exact0003 host is also unchanged.

The new entry points select only Target('profiles', True, hidden_password), never
an arbitrary URL/database/user. profile_engine rejects benchmark and all retained/
development/production targets **before** the shared factory. Every logical
connection, including pool reuse, checks actual merge_profile_test / merge_app /
127.0.0.1:5432 / exact0006_profiles, unprivileged flags/no role memberships,
synchronous psycopg PostgreSQL, READ COMMITTED defaults, autocommit off,
lock_timeout5s/statement_timeout15s. The observer then owns a short repeatable-read,
read-only transaction for a consistent fingerprint/row snapshot; it never changes
the mutation isolation or holds a transaction across network calls.

AuthSettings is explicit loopback development mode, origin
http://127.0.0.1:5173, no trusted proxy, unchanged throttle limits, a fresh private
in-memory throttle HMAC secret. Uvicorn binds127.0.0.1:8000, one worker, reload
off, forwarded-header handling off, access logs off and25s graceful drain.
The exclusive socket check refuses existing backend/frontend listeners; start
Vite **after** the backend. Ordinary HTTP/JSON, exact Origin/Fetch Metadata,
X-Merge-Request, real HttpOnly SameSite dev cookie, current CSRF, authorization
and session revalidation remain unchanged. This does not verify HTTPS/Secure
__Host cookies or production proxy behavior.

## B. Campaign execution and budgets

The existing acceptance/integrated-campaign.json remains byte-identical.
Canonical SHA256: 068e7f46c6af89db3be855cf72cf91c932f7337c1fc339b77d2707b9477214b1.
Run17ff1152-1ac0-4ace-a887-13436dd2963f; four independent l/q/r/x accounts,
H1/H2, A/B, two requests, two invitations. No old scope is adopted or resumed.
Preflight rejects existing usernames, domain rows, profiles or planned hackathon
IDs. Preparation inserts only the two new min2/max3 hackathons, under one owned
transaction, with same-transaction prior-row/addition checks and a fresh-engine
post-commit check. Every fixture remains retained on success or failure.

Ledger ceilings are10 auth,7 profile,18 domain and3 security POSTs, **38 total**.
The global count is charged at ASGI entry, before durable throttles or writes,
including a rejected malformed POST. Body reading is bounded to8192 bytes/10s;
duplicate JSON keys, actor selectors and unexpected query/body/route/identity
close the run. One POST may be in flight; concurrent SSE/GETs remain supported.
The real session determines actor; no supplied UUID grants authority. Registration
binds fresh server IDs; teams/requests/invitations bind real stored reply IDs.

Before any serve-worker DB access, a CreateNew campaign-<run ID>.json marker
burns that namespace for one start. Even a failure before the first account/POST
cannot reset the ledger by restarting the host. The marker is immutable and
hash-bound into the worker/certification chain. Never delete it to resume.

The domain order is create_b, create_a, exact create_a replay, request_q,
request_r, deny_decision, reject_r, approve_q, issue_r, deny_redeem, redeem_r,
deny_remove, remove_r, leave_q, issue_q, redeem_q, leave_l, final_q. Each distinct
command uses a distinct actor/key scope; original path/body/key/actor are frozen.
Invitation attempts are claimed before the real durable invitation throttle.
All services still own their original database transactions and bounded internal
retry/reconciliation; the test ledger does not replace domain locks or prove races.

**Unknown outcomes close the campaign; no harness mutation retry follows them.**
The single planned creation replay is permitted only after the server ledger
recorded a committed stored reply and a completed201 HTTP response, then the
client-only response gate loses that acknowledgement. Its second reply must be
byte-equivalent and use the original key. A service outcome_uncertain, failed
send/disconnect, unexpected status/exception or changed request latches closed,
even if a write may have committed. The production UI may offer its normal
original-key recovery; this campaign must stop instead. No host restart/resume
or replacement key is allowed.

Negative requests require exact **error codes**, not only statuses. Expected:
forbidden for decision/removal; invitation_not_found404 for foreign recipient;
invalid_request422 for invalid profile; profile_changed409 for stale CAS;
invalid_session401, invalid_csrf403, origin_rejected403 for the three probes.
The foreign-Origin probe must carry valid current l CSRF, so a CSRF denial cannot
mask an Origin defect. Only bounded sanitized negative-response error codes are
retained; authentication response bodies/headers are never captured.

Positive actions run in the real UI; private API contexts handle unavailable
nonleader/wrong-recipient actions and the two profile error diagnostics. API
contexts keep cookie/CSRF in memory and use the exact probe header
X-Merge-Acceptance-Probe with missing_session/missing_csrf/foreign_origin only
for their planned profile request. Foreign Origin is exactly https://foreign.invalid.
No auth material goes into scripts, argv, source, notes, screenshots or logs.
The original test-only response gate supports the planned create/board faults;
it is not imported into src and is installed only after owner approval.

For ordering/body details and the13 actual browser checkpoints, use the retained
campaign table in INTEGRATED_ACCEPTANCE.md. Profile saves precede domain commands;
invalid/edit/stale use the planned l version1 bodies. The two workspaces and real
private readers remain scoped, while the public catalog and globally opted-in
candidate ranking are genuine production reads; old candidates are paginated,
never hidden/deleted. Read refresh/navigation/Cancel spend no POST allowance.
Use1280x800 then390x844 on the same planned actions, keyboard focus/confirmation/
Cancel and four separate cookie contexts. Two tabs with shared cookies do not
prove account isolation. Keep at most two SSE subscriptions per account, close
old subscriptions on workspace/account changes, observe l/q updates and a normal
lease reconnect without Refresh or POST. Do not repeat certified PostgreSQL SSE
or G1 schedules. Browser keyboard/mobile/transport observations remain unexecuted.

## C. Independent observer and certification

After a successful drain, complete ledger and unchanged guard, the host launches
a separate Python observer process with a fresh fixed-target guarded engine.
The initial snapshot, exact command fingerprints/replies and allowed throttle
HMAC identities travel only through a private stdin pipe (max8MB); the database
credential goes only in the private child environment and is removed there.
No raw credential/hash/session/CSRF value or row snapshot is serialized to disk.
stdout is a bounded counts/fixed-marker JSON; stderr is discarded. Timeout60s,
parse error, nonzero/unknown native exit or contradictory result fails closed.

The observer compares all13 application tables, including profiles. Every prior
row fingerprint must remain identical; every added global row must belong to the
fresh scope or an exactly charged new throttle bucket. Quiet owner-controlled
window required: no concurrent writer/dispatcher/runner. There is no claim of a
database-wide exclusive lock. No automatic cleanup/repair is prepared.

It verifies four exact identities/profiles (l version2, others1), five sessions
(only x revoked), two hackathons/teams, B q-only/live/version1, A empty/deleted/
leader-null/version13, exact approved/rejected requests and two redeemed grants
with real expiry bounds. It checks all14 idempotency fingerprints/keys/stored
replies,14 linked audit rows and14 outbox rows; full version/state/subject/request/
invitation chains and exact event payloads; no pending or denied-command receipts;
all38 attempt statuses and eight exact denial codes. It verifies all19 durable
throttle charges over the ten allowed identity/scope pairs, including split
windows, and no unrelated additions. Successful output contains counts and
fresh_scope_and_prior_rows_verified only. These SQL checks have not run live.

The supervisor records the worker's actual native exit separately from its
claimed report status. An append-only incomplete start receipt is written before
credential/child work; final process/worker/observer files use new UUIDs/CreateNew.
No old file is overwritten. Source snapshots include HEAD and hashes of every
tracked/nonignored untracked file, capturing all pending product-audit changes.
Changed source, missing receipt, incomplete drain or ledger, negative native exit,
interrupt, timeout or report inconsistency never becomes a pass. Ctrl+C allows
up to100s for25s drain plus60s observer/hash teardown; a second interrupt or
timeout fails, with partial state retained.
Failed host reports retain fixed stage, attempted/completed POST counters, public
tags/statuses/denial codes and any actual observer exit/report hash. They contain
no raw body, command key, password, token, exception or snapshot.

Browser execution is **owner-operated**, not an implemented Playwright driver.
The Node tool only verifies actual owner observation files and artifact hashes.
Native roles are explicitly host worker, read-only observer worker, and browser
**evidence verifier**. browser_engine_exit is not_captured; never invent a native
browser-engine0 for a manually controlled browser. This distinction is retained
in the final review report. No independent/signature or automatic truth claim is
made for owner-recorded observations.

The offline certifier requires source-current successful serve process/worker
hash chain, native host/observer0, exact target/run/plan/denial checks and observer
totals. It launches only the fixed Node verifier (no shell/arbitrary command).
That verifier requires all13 unique checkpoints passed with nonempty SHA256-bound
PNG/JSON artifacts in the fixed ignored directory, both exact viewports, browser/
version/OS, all ten required observation flags true, zero skips/failures and no
active checkpoint. Artifact paths reject traversal/redirects. Browser times must
lie inside the actual worker interval. Notes/report/source hashes are rechecked;
mutation during verification fails. The resulting report is a local integrity
review requiring owner inspection of the actual artifacts, not an independent
certificate. No successful live review report was generated in this task.

## D. Database prerequisites and owner approval gates

Actual database existence/identity/permissions/revision remain unknown. Migration
0006 is reported unapplied; nothing here changes that baseline. First approve and
complete the exact profile SQL/provision/prepare/migrate/verify/profile30 sequence
in INTEGRATED_ACCEPTANCE.md/RELEASE_VALIDATION.md. No migration of merge_test or
merge_dev. Provisioning is not wholly atomic: stop on partial creation, never
adopt/drop/retry blindly. Freeze source before profile30; keep its unique
source-bound successful receipt. Every live integrated command requires that
receipt, exact0006 and its own fixed-profile confirmation before hidden input or
connection. Refuse ambient MERGE_RELEASE_DB_PASSWORD/MERGE_TEST_DB_PASSWORD/
MERGE_INTEGRATED_CHILD_PASSWORD; the supervisor uses the existing fatal-warning,
TTY-only hidden password helper. Never pipe/transcribe interactive commands.

All commands below are **proposals for separate approval, NOT EXECUTED**. Replace
only receipt basenames printed by approved steps; placeholders are not evidence.

```powershell
Set-Location -LiteralPath 'I:\Merge\backend'
# APPROVAL A: real read-only isolated DB/revision and unused campaign namespace.
.\.venv\Scripts\python.exe -m release_support.integrated_run inspect --confirm-profile-test --revision 0006_profiles --profile-receipt test-results/release/profiles-RECEIPT_ID.json
$inspectNative = $LASTEXITCODE
if ($inspectNative -ne 0) { throw 'Preflight failed; retain evidence and stop' }
# APPROVAL B: two additive fresh hackathons; no other fixture preparation.
.\.venv\Scripts\python.exe -m release_support.integrated_run prepare --confirm-profile-test --revision 0006_profiles --profile-receipt test-results/release/profiles-RECEIPT_ID.json --allow-fixture-writes
$prepareNative = $LASTEXITCODE
if ($prepareNative -ne 0) { throw 'Preparation incomplete; do not retry' }
```

In backend terminal1, approve the38-POST scope and owned loopback listener:

```powershell
Set-Location -LiteralPath 'I:\Merge\backend'
# APPROVAL C: guarded host, real auth/domain/profile writes, SSE/GETs, final observer.
.\.venv\Scripts\python.exe -m release_support.integrated_run serve --confirm-profile-test --revision 0006_profiles --profile-receipt test-results/release/profiles-RECEIPT_ID.json --allow-browser-writes
$hostSupervisorNative = $LASTEXITCODE
if ($hostSupervisorNative -ne 0) { throw 'Host/campaign incomplete; retain all state and stop' }
```

Only after backend start, approve terminal2 liveness/frontend and actual isolated
browser contexts (no preexisting cookies; approved origin only):

```powershell
# APPROVAL D: live liveness read, Vite and owner browser campaign.
$liveness = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing
if ($liveness.StatusCode -ne 200) { throw 'Backend unavailable; stop' }
Set-Location -LiteralPath 'I:\Merge\frontend'
npm.cmd run dev
```

Execute the13 checkpoints once. Close browser contexts/streams after the final
observation (do not add logout/cleanup POSTs), stop owned Vite, then Ctrl+C the
owned host for drain/observer/certification. Never stop another process by name.
Require the final **passed serve process** receipt, its worker+observer hash chain
and native0; the incomplete start receipt is deliberately insufficient. On any
unknown result, stop immediately and retain partial writes/reports; no replay or
new namespace without diagnosis/review/new approval.

### Actual browser observations file

Create a new ignored file named browser-observations-<run UUID>-<new UUID>.json in
backend/test-results/integrated. This is an owner record of actual observations,
not an auto-passed template. Required fields:

- schema_version1; kind integrated-browser-observations; exact run_id/plan_sha256;
  full source snapshot copied from the matching serve worker report, verified
  unchanged; source_unchanged true only after that verification.
- status passed, owner_observed true, skipped/failures empty, active_checkpoint
  null **only after actual completion**; otherwise retain pending/failed status.
- browser, browser_version, os; actual started_at/finished_at with UTC offsets
  inside the host interval; viewports exactly those in the public plan.
- browser_engine_exit string not_captured. Native verifier exit is recorded by
  the certifier, not typed into this file.
- checkpoints:13 objects with id from plan.coverage, status, artifact basename,
  evidence_sha256. Use browser-<run UUID>-<checkpoint id>.png or .json. Each file
  must contain actual sanitized observations, never raw credentials or cookies.
- observations: two_isolated_clients, sse_without_manual_refresh,
  lease_reconnect_refetch, no_private_content_leak, old_account_callbacks_fenced,
  old_workspace_callbacks_fenced, keyboard_only_actions, mobile_390_no_overflow,
  cancel_no_posts_focus_restored, navigation_no_automatic_posts. Set true only
  after reviewing corresponding actual artifacts. No bulk auto-pass generator.

Use real screenshots for layout/focus and actual sanitized step records for
actions/reads; inspect every artifact. A schema-valid fabricated observation file
cannot establish that a browser action happened. The owner must attest truth and
understand the implementation. The certifier enforces integrity/completeness,
not independent provenance.

Offline review command after the separately approved live campaign:

```powershell
Set-Location -LiteralPath 'I:\Merge\backend'
.\.venv\Scripts\python.exe -m release_support.integrated_certify --host-process test-results/integrated/process-FINAL_RECEIPT_ID.json --browser-observations test-results/integrated/browser-observations-RUN_ID-NEW_UUID.json
$evidenceNative = $LASTEXITCODE
if ($evidenceNative -ne 0) { throw 'Evidence incomplete/stale; preserve and stop' }
```

The certifier itself has no DB/browser/network operations. Source changes between
approved profile30, preparation, serve, observations and final review invalidate
the source-bound chain; do not rewrite old receipts to make them current.

## E. Offline validation and limits

Existing Windows PowerShell/Python3.11.9 venv/Node22.15.0/npm10.9.2/locked
dependencies. Reviewed outside-sandbox commands after sandbox helper setup failed
before process startup. No global Git safe.directory configuration was changed.
In-process ASGI TestClient tests use fake engines/services; no live listener or
PostgreSQL. Synthetic scenes exercise corruption/control flow, not SQL execution,
browser transport, performance or PS1 concurrency acceptance.

| Working directory / actual command | Result |
| --- | --- |
| backend: `.\.venv\Scripts\python.exe -m pytest tests/test_integrated_host.py tests/test_integrated_evidence.py tests/test_integrated_plan.py tests/test_release_support.py tests/test_browser_full_harness.py tests/test_browser_harness.py -q --tb=short` | FINAL459 passed/14.75s/native0, including121 new host/evidence cases. |
| backend: `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short` | FINAL1895 passed/32 deselected/61.57s/native0 after all denial-code, notes/marker hash and restart/failure-report hardening. |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1` | FINAL434 passed/18 files/122.31s/native0. |
| frontend: `npm.cmd run build` | FINAL TypeScript passed, Vite50 modules/1.75s/native0. No server startup. |
| backend: `.\.venv\Scripts\python.exe -m pytest profile_tests --collect-only -q --confirm-profile-test` |30 collected/0.07s/native0; no fixture/credential/SQL execution. |
| backend: `.\.venv\Scripts\python.exe -m release_support.integrated_run readiness` | Static24-route/nine-override audit/native0/CONDITIONAL, live_operations_performed=false. |
| backend: `.\.venv\Scripts\python.exe -m release_support.integrated_plan validate` / `readiness` | Unchanged JSON digest validates/native0; readiness now reports CONDITIONAL/new infrastructure but retains native2 as an explicit unverified-live-prerequisite gate. |
| frontend: `node --check test_support/integratedCampaign.js`, `integratedCampaign.test.js`, `integratedEvidence.mjs`, `integratedEvidence.test.js` | All native0; no browser execution. |
| PowerShell proposal parsing / Git diff and new-file whitespace / source preservation |8 proposal blocks parsed without execution; Git diff --check clean;754 starting evidence files (including original733) and all old tracked hosts/support/application/migrations byte-identical. Final AST/new-file whitespace/targeted secret scan clean. |

Logs/baseline inventories are new ignored files under backend/test-results/
integrated-host-offline-cde8edda82dd44d1a5195433c28f4d93. Initial66-case focused
run passed. Expanded drift test run had135 pass/2 fail/3 teardown errors: changing
the shared original endpoint was not detected, and test mutation leaked into
shared original routers. Strengthened original/effective identity checks and
restored all test mutations before shutdown; next139 passed. Focused Node26
passed. Subsequent452/backend1888/frontend434/build passed before final denial/
note-race hardening. All intermediate logs are retained; no failing condition,
assertion, timeout or old host was weakened. Existing Starlette/httpx warning
and Git LF/CRLF warnings remain. Current full/targeted final results supersede
earlier checkpoints only for their actual tested source.

## F. Git inventory and recommendation

Final inventory:28 pending paths,10 tracked modifications +18 untracked
files, all unstaged; no deletion. Ten new files from this task, plus changes to
the previously pending offline readiness helper/test and additive two doc entries.

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
?? backend/release_support/integrated_ledger.py
?? backend/release_support/integrated_host.py
?? backend/release_support/integrated_observer.py
?? backend/release_support/integrated_run.py
?? backend/release_support/integrated_certify.py
?? backend/tests/test_integrated_plan.py
?? backend/tests/test_integrated_host.py
?? backend/tests/test_integrated_evidence.py
?? docs/INTEGRATED_ACCEPTANCE.md
?? docs/INTEGRATED_HOST.md
?? docs/PRODUCT_AUDIT.md
?? frontend/src/ProductAudit.test.tsx
?? frontend/test_support/integratedCampaign.js
?? frontend/test_support/integratedCampaign.test.js
?? frontend/test_support/integratedEvidence.mjs
?? frontend/test_support/integratedEvidence.test.js
```

Recommendation: CONDITIONAL for owner approval of the bounded live stages.
Infrastructure is implemented/offline tested; database SQL, observer subprocess
against PostgreSQL, Windows console signal/drain behavior, real browser actions,
SSE transport, keyboard/mobile and production HTTPS remain unverified. Manual
owner observations and their verifier are not an automated E2E driver. Public CI,
seed/load, deployment and final submission artifacts remain independent gates.

Owner explanation: the ledger grants fewer commands than production services,
while PostgreSQL still owns membership/leadership/transactions. The observer
checks both scoped effects and every preexisting global row; native exit and
report status are independent. Exercise: change a synthetic403 origin probe to
invalid_csrf or alter one prior-row fingerprint; run the focused tests and explain
why the campaign must close even though the status/counts might look correct.
STOP before all live operations; no commit/push/deployment authorization implied.

# Authenticated team creation HTTP API - M-012A

M-014B adds separate recipient-bound invitation routes, documented in
[INVITATIONS.md](INVITATIONS.md). Cookie/CSRF/Origin/key policy is reused; no
unrestricted join or actor selector. The existing create contract/service is
unchanged. The owner reports 0005 already applied; R2 audited the successful
39-case/three-repetition invitation run. Original Phase 1 G1 is closed within
local guarded PostgreSQL scope; [G1_ACCEPTANCE.md](G1_ACCEPTANCE.md) records limits.
Do not rerun migrations/live tests; browser/production HTTPS and CI remain open.

M-013A adds only scoped join-request creation, own status, leader pending list
and leader decision routes; [ADMISSION.md](ADMISSION.md) is their exact contract.
No unrestricted join is exposed. Existing creation/read contracts and the
unknown-hackathon 503 limitation remain. Owner separately verified applied 0004
and 35 + 70 admission executions, exit 0/completed fixture checks in both runs;
this does not close distinct-caller G1. M-012A's own 105 passes below remain
separate historical evidence. No frontend admission UI or browser-host expansion.

Final checkpoint against `2e5f678efd7348584eed2b6281c7448bc45f5d8e`: the owner
verified guarded merge_test / merge_app, READ COMMITTED, **0003_auth (head)** and
reported **105 team API cases passed in 140.81 seconds** after the R1 fixture
correction. This is owner-run PostgreSQL evidence; Codex did not rerun PostgreSQL.
Final offline checks and review are recorded in PROGRESS.md. One existing
nonblocking Starlette deprecation warning remains. No browser/deployed HTTPS/G1
acceptance, frontend create flow, join authorization, migration or dependency change.

## M-012B frontend integration

The React client now implements this contract with current useSession CSRF,
native cryptographic keys and an App-lifetime account/hackathon command journal.
Unresolved retries freeze exact name/key across navigation and same-account
reauthentication; session invalidation aborts/ignores old callbacks. Only validated
201 confirms creation, then canonical reads refresh. No automatic mutation retry,
backend change or new join authorization. Memory-only records cannot survive
reload/crash/tab closure. FRONTEND.md and PROGRESS.md record offline evidence,
recovery behavior and pending browser/write-approval prerequisites. Existing
browser host still blocks creation. Earlier React-milestone statements below
retain M-012A checkpoint scope.

## M-012A-R1 - first owner-run fixture failure

The owner verified merge_test / merge_app, READ COMMITTED and 0003_auth (head),
then the first case `test_success_and_exact_replay_with_fresh_stored_chain[0]`
errored with CredentialError: invalid_input; **1 error in 0.65s**. Fresh committed
invariants were reported verified. This was a fixture setup error, not a completed
HTTP test or successful live suite. No live rerun was performed by Codex.

TeamApiEnvironment.username used `team_api_` (9 characters) plus 24 UUID hex
characters, always 33, violating the unchanged 3-32-character username rule.
Registration rejects it before hashing or SQL, before session login or the team
POST. R1 changes only that fixture prefix to `teamapi_` (8 characters), preserving
the 24-hex suffix and producing 32 characters. Password generation and default
display-name handling, CredentialService, HTTP/session/CSRF policies and composed
mutation services are unchanged. Every case shares this account fixture.

Two offline regressions exercise the actual account fixture through real
credential and HTTP input validators with only hashing/verification and SQL
resources doubled, and retain rejection of the original 33-character value
before hashing/SQL. The regression reproduced the owner exception before the
one-line correction. Fresh commands/results are in PROGRESS.md. Full live
verification was pending at R1; the subsequent 105-pass owner checkpoint above
supersedes that pending status and retains this failure as historical evidence.

## Request and success

`POST /api/hackathons/{hackathon_id}/teams`

- Existing session cookie only: `__Host-merge_session` in production, or the
  approved explicit loopback development cookie. Authorization/X-User-ID/
  X-Actor-ID headers never establish identity; the latter two are rejected.
- Exact configured `Origin` is mandatory. Existing HTTPS, actual socket-peer,
  forwarded-header and Fetch Metadata checks remain active before body parsing.
  No CORS/preflight relaxation. Existing login/registration custom-header and
  durable throttle policies are unchanged; this route does not charge auth
  throttle buckets or introduce a new creation limiter.
- Exactly one canonical session-bound `X-CSRF-Token`. Existing
  `SessionService.verify_csrf(cookie, token)` validates the current session again
  before mutation. Missing/malformed/wrong-session token gives 403; invalid
  session gives 401 when browser-policy checks pass. Authentication is point in
  time: later revocation cannot cancel already-authenticated work.
- Exactly one `Idempotency-Key`, 1-128 printable ASCII characters U+0020-U+007E.
  Case and every space are significant; no trimming/normalization. Transport or
  proxy normalization of HTTP whitespace must not be relied upon for key design;
  future clients should choose an unambiguous random printable key.
- `Content-Type: application/json` (existing optional media parameters accepted).
  Strict body is exactly `{"name": string}`. Name is 1-120 characters, not all
  ASCII spaces, no NUL, valid UTF-8. Preserve accepted text exactly; no trimming
  or Unicode normalization. No actor, team UUID, size, leader, key or scope fields
  and no query parameters. Invalid path UUIDs and bodies are sanitized 422.

Initial creation AND matching replay return **201** with the stored envelope:

```typescript
type CreateTeamBody = { name: string };
type CreateTeamSuccess = {
  schema_version: 1;
  data: {
    team_id: string;       // UUID allocated by the service
    hackathon_id: string;  // UUID from the validated command
    user_id: string;       // authenticated founder UUID, never a client input
    member_count: 1;
    team_version: 1;
  };
};
type ApiError = { error: { code: string; message: string; retryable: boolean } };
```

This is the mutation's original committed result, not the discovery Team DTO.
The route returns `_StoredReply.http_status`, `body()` and its allowlisted headers
without a new domain read or DTO regeneration. Current counts/version/name can
change afterward; replay still returns its original result. Original stored
headers are `content-type: application/json` and `cache-control: no-store`.
The unchanged AuthBoundary strengthens caching on every response to
`Cache-Control: no-store, private`, `Pragma: no-cache`, `Expires: 0`, and nosniff.
No Set-Cookie, Location, replay marker or sensitive audit/session data is added.
JSON formatting is not a database byte-preservation guarantee; status, JSON value
and safe headers are the stored contract, with the fixed browser-policy overlay.

The React milestone should use relative same-origin cookie requests and the
current in-memory CSRF token, sending only name in JSON. Generate the key once
for a deliberate command and keep it stable with the exact hackathon/name/account
through retries. Never replace it after transport ambiguity or outcome_uncertain.
Reauthenticate as the same account if needed; another account has another scope.
On 201, refetch listing/current membership rather than casting this response to
TeamView. On membership conflict, refetch canonical `/me/team`. Existing GET
listing, detail, pagination and `{team: null}` contracts are unchanged. No
frontend code or automatic client retry was added here.

## Errors and retry semantics

Every error is `{error:{code,message,retryable}}`, with fixed sanitized text.
Submitted names/keys/UUID text, SQL, constraints, driver errors, token material and
private audit details are never copied into responses or deliberately logged.

| Condition | HTTP / code | retryable |
| --- | --- | --- |
| Missing/malformed/unknown/expired/revoked cookie | 401 / invalid_session | false |
| Missing/malformed/wrong-session CSRF | 403 / invalid_csrf | false |
| Origin/Fetch Metadata, peer/proxy or HTTPS rejection | 403 / existing security code | false |
| Invalid body/path/query/identity header/key (including duplicate key) | 422 / invalid_request | false |
| Unsupported or duplicate Content-Type | 415 / unsupported_media_type | false |
| Same actor/key with changed name or hackathon | 409 / idempotency_mismatch | false |
| Separate key but actor already assigned in that hackathon | 409 / already_assigned | false |
| Service hackathon_not_found, if emitted | 404 / hackathon_not_found | false |
| Exhausted confirmed conflict/deadline or lock timeout, marked retryable by service | 503 / service_unavailable | true |
| Unresolved COMMIT outcome | 503 / outcome_uncertain | true |
| Other domain/configuration/integrity/database/unexpected fault | 503 / service_unavailable | false |

`outcome_uncertain` says **Outcome is unknown. Retry with the SAME Idempotency-Key
and unchanged request.** It claims neither failure nor success. No route retry,
new key, compensating action or background work exists. A transport failure can
also hide a committed success. All retries must preserve the complete command.
Service retries/reconciliation remain bounded by M-008E (at most three owned
attempts); this HTTP adapter adds no attempts and no transaction owner.

Important existing service limit: reservation INSERT checks immediate actor and
hackathon foreign keys before the domain existence lookup. A fresh unknown
hackathon can therefore yield integrity_fault -> sanitized 503 instead of 404.
No route preflight query or constraint-text inference was added to manufacture a
404. A cross-hackathon reuse of a retained key with another existing hackathon is
409 mismatch; a separate key in another valid hackathon remains eligible.
Unexpected join-only domain codes on this create-only path fail closed as 503.

## Ownership and trust boundary

`authenticated_session -> creation_session -> get_team_service` reuses the
existing lazy auth-owned Engine. The factory neither reads Settings nor opens a
new engine; absent auth_engine fails closed. The route independently depends on
creation_session so a test service override cannot remove authentication/CSRF.
FastAPI caches that dependency once per request. Only
`auth.validated.principal.user_id` supplies actor_id.

Exactly one `create_team_idempotent()` call invokes existing validated command,
reservation-before-domain-lock ordering and `_execute` transaction ownership.
Founder team/membership, version 1, completed reply, audit and outbox all commit
or roll back together. Matching replay bypasses mutation and returns immutable
stored state after commit/reconciliation. The HTTP route does no SQL, begin,
commit, audit/outbox write, UUID generation or independent existence check.
Legacy create_team and unrestricted join are not HTTP paths. Existing locks,
membership PK/constraints, transaction guards and retry services are unchanged.

The M-011A guarded browser host explicitly removes only this new router by router
identity, retaining its exact existing closed inventory and dependency audits.
Reintroducing the router latches it closed before dependency resolution. Its
manifest grants only scoped auth writes, never team writes. The existing browser
launcher must not be used to exercise team creation without a separately reviewed
future host policy. Production packaging remains app-only; no test support is
imported by production runtime.

## Initial M-012A offline evidence (before R1)

Windows PowerShell, existing Python 3.11.9 venv / FastAPI 0.162.0 / SQLAlchemy
2.1.8 / psycopg 3.3.8 / Uvicorn 0.54.0:

- Full backend database-free suite: **1018 passed, 32 deselected in 30.41s**.
  Includes 83 new offline HTTP cases and all 128 browser-host security/shutdown
  cases. One existing Starlette/HTTPX deprecation warning; no test skipped/xfailed.
- Guarded collection only: **105 team HTTP cases** (35 scenarios x3), plus existing
  auth API 54, read API 87, composed mutations 81 and retries 54. Each suite was
  collected separately; no fixture execution or database access.
- Backend pip check, changed-Python compile/AST checks, scope/secret-format scan
  and whitespace checks passed. Frontend unchanged; typecheck, 52 tests, build
  and npm dependency inventory passed. Exact commands/history: PROGRESS.md.

## Guarded PostgreSQL verification - owner verified; reproduction commands

No credential was supplied to Codex and none was requested/read. Collection opens
no database. The fixed runner `--suite team-api` requires explicit 0003_auth and
confirmation before credentials, verifies loopback merge_test / merge_app, and
injects real auth/read/team services on its guarded Engine. Ordinary Settings,
backend/.env and merge_dev are not consulted. Every service checkout checks
identity, actual autocommit false, READ COMMITTED and exact revision; fresh
observers use independently guarded connections. No migration/reset/cleanup.

For separately approved reproduction in the owner's PowerShell terminal, without
transcripts (not rerun during final review):

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Read-only target verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite team-api --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Team HTTP verification failed. Stop; inspect owned workers before any rerun.' }
```

The existing private hidden prompt supplies the DB-role password, never an
argument or printed URL. Live execution writes only new scoped retained fixtures:
UUID hackathons/users, real credential/session rows and composed team/founder/
idempotency/audit/outbox chains. One replay test uses trusted internal composed
join for a scoped fixture. Expiry/revocation fixtures write scoped session rows.
No existing owner account/data is adopted; no DELETE/TRUNCATE/reset/cleanup,
schema/role/privilege change or live browser/server listener is involved.

Tests cover success/stored replay after later membership, real session and CSRF
failures, browser/input rejection, mismatch/scope/already-assigned, two HTTP
requests with matching or distinct keys, server-observed blocking on distinct
backend PIDs and old committed state before release, all five write-stage
rollbacks, actual deferred-COMMIT rejection, and injected lost acknowledgement
with actual commit or rollback plus available/unavailable reconciliation.
Acknowledgement faults are test hooks, not claims of a real network outage.
Fresh scoped record-chain/domain/account/session invariant checks run even on
failure. Unexpected faults/timeouts are failures; no broad accepted race outcomes.
Event waits are 8s, lock observation 3s, workers share a 30s join bound; existing
connect/lock/statement limits remain 5s/5s/15s. A deadline does not prove worker or
transaction termination; stop and inspect before rerunning an unfinished test.

Credential-free collection and separate regression runs:

```powershell
.\.venv\Scripts\python.exe -m pytest team_api_tests --collect-only -q
# The following are future live owner runs with the same target guards:
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite auth-api --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Authentication regressions failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite reads --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Read regressions failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite mutations --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Mutation regressions failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite retries --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Retry regressions failed. Stop.' }
```

The owner-verified 105-case suite covers its bounded local schedules, not an
authenticated 50-way join, CI/load/deployment/browser proof or G1 closure.
Owner exercise: trace same-key replay versus changed-key
already_assigned, then explain why a lost acknowledgement must retain the key
and why a later successful snapshot alone cannot erase an incomplete run.

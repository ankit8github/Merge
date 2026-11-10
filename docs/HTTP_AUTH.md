# HTTP authentication — M-007B.3A-R1

M-010A adds authenticated GET-only /api/hackathons discovery routes. They reuse
the existing validated-session dependency and extend the same AuthBoundary browser/
actual-peer/proxy/HTTPS and no-store policy to /api. No cookie, CSRF, session or
Origin policy change; no header-based identity or CORS. TeamService is unchanged.
Owner verified at 0003_auth: read API 87 passed in 73.35s and auth API regressions
54 in 28.28s; total 141 passed, suite-time sum 101.63s, three repetitions
requested, one existing Starlette/HTTPX warning. These are owner-run PostgreSQL
results, not Codex executions; earlier auth results below remain historical.
Contracts and guarded reproduction commands: [READ_API.md](READ_API.md).

M-007B.3B now adds durable login account/IP and registration IP throttling,
owner-verified on guarded merge_test / 0003_auth, 2026-11-10: 33 throttle cases
in 31.42s, 54 updated API cases in 30.94s and 78 session cases in 48.33s;
165 passes in 110.69s, three repetitions requested, fresh committed-state
invariants verified. The existing Starlette/HTTPX warning remains. This records
owner execution, not a Codex PostgreSQL rerun. Production HTTPS/browser
verification remains outstanding.
Startup additionally requires a shared throttle secret and the controlled
`python -m app.serve` launcher. Actual-peer/explicit single-hop proxy policy and
429/Retry-After contract: [AUTH_THROTTLING.md](AUTH_THROTTLING.md). Earlier
no-throttling checkpoint descriptions below retain their historical scope.

Owner-verified checkpoint, 2026-11-10: guarded merge_test / 0003_auth (head),
**78 session cases passed in 72.48s** and **54 HTTP API cases passed in 40.90s**,
132 live executions total. Fresh committed-state invariants verified; one existing
Starlette/HTTPX warning. This is owner execution, not a Codex database rerun.
At that M-007B.3A checkpoint, shared throttling was still pending; the
M-007B.3B results above now cover it. See PROGRESS.md for final checkpoint checks
and the unresolved proxy timing limitation. Unchanged 0003_auth, no TeamService mutations, no migration/dependency
additions, no route-owned transactions or commits.

## Approved session interface extension and trust boundary

The original validate() returned only SessionPrincipal and could not supply the
existing CSRF token for GET /auth/session. Owner explicitly approved R1:
`validate_with_csrf(raw_token) -> ValidatedSession(principal, csrf_token)`.
The frozen, slotted result excludes its SecretBytes field from repr. It has no
bearer, password hash or database row. It calls the existing _read_active exactly
once, with the same read-only transaction, active-account checks, absolute expiry,
actual DBAPI AUTOCOMMIT rejection and READ COMMITTED guard. Principal and CSRF
come from that single validated snapshot. Nothing rotates, renews or writes.
Existing login/validate/verify_csrf/revoke behavior is preserved.

HTTP code uses public services only. A synchronous authentication dependency
decodes the cookie and calls validate_with_csrf; identity is always derived from
the result. The raw bearer is retained only in an internal repr-redacted
SecretBytes field for logout. The adapter deliberately unwraps CSRF for JSON and
bearer for Set-Cookie, never for a JSON response. Never serialize the internal
dataclasses or log headers, bodies, SQL parameters, exception locals or sensitive
results. Python secrets cannot be reliably zeroized. Trusted same-origin JS can
read CSRF: XSS defeats this browser boundary and needs separate mitigation.

## Endpoint contracts

All mutation bodies use application/json (optional media parameters accepted).
Models are strict and forbid extra fields. Username/password/display_name policies
are unchanged from CREDENTIAL_SERVICES.md. Secrets are not echoed in validation
errors; FastAPI's raw Pydantic error inputs/body are never returned.

| Endpoint | Request | Success |
|---|---|---|
| POST /auth/register | username, password, optional display_name | 201: {user_id, username}; no cookie or session |
| POST /auth/login | username, password | 200: {identity: {user_id, username}, expires_at, csrf_token}; set session cookie |
| GET /auth/session | session cookie | 200: same session response with existing CSRF; no Set-Cookie or renewal |
| POST /auth/logout | JSON {}; session cookie; X-CSRF-Token | 204, no body; revoke current session and expire cookie |

Bearer cookie and CSRF HTTP encodings are canonical unpadded base64url, exactly
43 ASCII characters encoding 32 bytes. Malformed/noncanonical encodings and
duplicate session-cookie names are rejected; no alternative bearer/header/user-ID
authentication path exists. No actor_id, user_id, identity or leader flag is an
accepted request-body field. Public account IDs are identifiers, never proof.

## Browser checks and caching

- Every mutation requires one Origin header exactly equal to configured origin.
  Missing, null, mismatched, duplicate, prefix-match, trailing-slash and sibling
  origins fail. Origin is never derived from arbitrary Host/Forwarded headers.
- Register/login also require exactly `X-Merge-Request: 1`. This non-simple header
  plus JSON and Origin checks rejects simple cross-site forms/login CSRF.
- Logout requires canonical X-CSRF-Token and service verify_csrf before revoke.
  Missing/malformed/wrong-session CSRF gives 403 and leaves the session active.
  A missing/invalid session gives 401 when the browser-policy checks pass.
- When Sec-Fetch-Site is present, only same-origin or none is accepted. Cross-site,
  same-site (including sibling hosts), unknown and duplicate values fail. The
  header is defense in depth: nonbrowser clients may omit/spoof it and Origin.
- GET /auth/session accepts absent Origin because same-origin GETs commonly omit
  it, but rejects a supplied hostile Origin or non-same-origin Fetch Metadata.
  Browser same-origin policy protects response readability. No CORS middleware,
  arbitrary reflection, credentialed wildcard or cross-origin preflight support.
- All /auth responses, including failures, 404/405 and 204, receive
  Cache-Control: no-store, private; Pragma: no-cache; Expires: 0; nosniff.
  Reverse proxies/CDNs must honor this and must not log Cookie, Set-Cookie, CSRF,
  credentials or request bodies. Do not put secrets into query strings/URLs.

SameSite is additional defense; authentication alone does not prevent CSRF.
The browser policy runs before body parsing and route/service work. Unsupported
mutation media types receive 415; other policy checks may reject hostile requests
first. Nonbrowser clients must also send the required Origin/custom headers.

## Startup and cookie configuration

AuthSettings reads only MERGE_AUTH_* process environment, not backend/.env.
Default mode is production. An explicit exact serialized origin is required;
missing/invalid config rejects startup, including /health availability. No path,
wildcard, credentials, trailing slash, invalid port or insecure production origin.
The origin must be the public frontend/backend origin, not the private upstream.

| Setting | Production | Explicit local development |
|---|---|---|
| MERGE_AUTH_MODE | production (default) | development |
| MERGE_AUTH_ORIGIN | exact https://host[:port] | exact loopback http[s]://host[:port] |
| cookie | __Host-merge_session | merge_session_dev |
| Secure | true | false |
| HttpOnly / SameSite / Path / Domain | true / Lax / / / omitted | same |

Cookie Max-Age is 28800 seconds; Expires comes from the service's authoritative
absolute expiry. Server validation remains authoritative even if a browser keeps
a cookie longer. Logout deletion uses the same name/path/security/SameSite policy.
No client-selected cookie name, Domain or insecure-production override exists.
Production auth requests also require the ASGI scheme to be HTTPS. A TLS proxy
must provide the correct scheme through narrowly trusted proxy forwarding; never
trust arbitrary forwarded headers from public clients. TLS/proxy deployment has
not been verified here. Production database topology/configuration remains a
separate task; ordinary local Settings retain their existing merge_dev guard.

Local startup from backend (public configuration only):

```powershell
$env:MERGE_AUTH_MODE = 'development'
$env:MERGE_AUTH_ORIGIN = 'http://127.0.0.1:5173'
# Privately provision/reuse MERGE_AUTH_THROTTLE_SECRET first; see AUTH_THROTTLING.md.
.\.venv\Scripts\python.exe -m app.serve --host 127.0.0.1 --port 8000
```

Vite proxies /health and /auth to 127.0.0.1:8000. Open the frontend at exactly
http://127.0.0.1:5173 and use relative /auth URLs with normal same-origin cookies.
Changing to localhost changes the origin and needs matching configuration.
Origin is preserved by the proxy. The frontend UI remains the existing health
screen; no login form/redesign is included. Development mode must remain local.

The runtime Engine is initialized lazily by the service dependency, never by
/health or a missing-cookie request. Guarded tests replace that dependency with
real services bound to the guarded Engine; they never load ordinary Settings,
backend/.env or merge_dev. Database-free tests use explicit service doubles and
do not establish real PostgreSQL outcomes. The app disposes its owned runtime
Engine on shutdown. Route code never issues SQL or commits; services still own
their existing transactions and perform no network work inside them.

## Public errors

Fixed shape: `{error: {code, message, retryable}}`. No raw exceptions, submitted
passwords/tokens, database constraint names, SQLSTATEs or connection details.

| Condition | Status / code |
|---|---|
| Wrong/unknown credentials or changed verification snapshot | 401 / invalid_credentials |
| Missing/malformed/unknown/expired/revoked session | 401 / invalid_session |
| Session-bound CSRF failure | 403 / invalid_csrf |
| Origin/Fetch Metadata failure | 403 / origin_rejected |
| Missing/invalid register/login custom header | 403 / request_header_required |
| Production request using HTTP | 403 / https_required |
| Duplicate username | 409 / username_unavailable |
| Unsupported mutation content type | 415 / unsupported_media_type |
| Invalid/extra fields, malformed JSON, invalid service input | 422 / invalid_request |
| KDF exhaustion, configuration, integrity, clock/entropy, database or unexpected fault | 503 / service_unavailable |

Only bounded KDF exhaustion and known rolled-back transaction conflicts/lock
timeouts advertise retryable=true. Other 503s are false, including ambiguous
COMMIT transport failure; no automatic client/server retry is implemented.
Unknown faults are sanitized without logging or copying their text. This is not
a substitute for trusted hosting/logging/APM configuration and secure telemetry.

## Guarded owner verification (owner-verified; commands retained)

Run interactively without transcripts. Existing hidden-password mechanism prompts
for merge_app; never put its password into arguments, source, history or chat.
No migration, reset, cleanup or ordinary database suite is needed. The owner has
completed both suites above; these commands are retained for reproduction.

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Read-only target verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite sessions --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Extended session verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite auth-api --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Auth API verification failed. Stop.' }
```

78 session and 54 API cases at three repetitions. API tests bind the actual
CredentialService and SessionService to the guarded Engine, retain unique fixtures
and inspect fresh scoped invariants. They require exact success/status/error
outcomes; unexpected faults, integrity errors and timeouts fail. The runner fails
fast, suppresses assertion/local dumps and rechecks actual merge_test/merge_app/
loopback/port/revision on service connections and fresh observers. Existing live
credential/auth-schema/team/domain regressions remain separate and pending.

Limitations: durable throttling is locally owner-verified; no claim of production
readiness, browser
E2E, deployed TLS/proxy validation, CI acceptance, timing equality, password-change
revocation, 50-way authenticated team race or gate closure. Logout cannot cancel
work already authenticated elsewhere. Stolen bearer tokens remain bearer tokens.
No team authorization/lifecycle/idempotency/audit/outbox or invitation routes.
The two-second auth proxy check has timed out in both concurrent and standalone
executions. Passing standalone runs and a separate timed 401 diagnostic do not
resolve that flakiness; no timeout is accepted as a successful assertion.

Owner exercise: remove X-Merge-Request from a login request and observe 403, then
explain why a valid cookie with another session's CSRF still cannot log out.

## Changed-file inventory

Runtime: backend/app/auth.py (new), backend/app/security/auth_policy.py (new),
backend/app/main.py, backend/app/services/sessions.py.

Tests/harness: backend/tests/test_auth_http.py (new),
backend/auth_api_tests/conftest.py (new), backend/auth_api_tests/test_auth_api.py
(new), backend/tests/test_sessions.py, backend/session_tests/test_sessions.py,
backend/test_support/concurrency.py, backend/tests/test_auth_schema_support.py,
backend/tests/test_concurrency_harness.py, backend/tests/test_health.py,
scripts/check_local_http.py. Integration config: frontend/vite.config.ts.

Documentation: README.md, docs/HTTP_AUTH.md (new), docs/SESSION_SERVICES.md,
docs/TEAM_SERVICES.md, docs/CREDENTIAL_SERVICES.md, docs/AUTH_SCHEMA.md,
docs/TEST_DATABASE.md, docs/ARCHITECTURE.md, docs/DECISIONS.md,
docs/REQUIREMENTS.md, docs/PROGRESS.md. Total: 26 files, no dependency/migration.

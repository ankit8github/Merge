# Durable authentication throttling — M-007B.3B

Owner-verified live checkpoint, 2026-11-10: guarded merge_test / 0003_auth,
three repetitions requested; fresh committed-state invariants verified.

| Suite | Owner-verified result |
|---|---|
| Throttles | 33 passed in 31.42s |
| Updated authentication API | 54 passed in 30.94s |
| Session regressions | 78 passed in 48.33s |
| Combined | 165 passed in 110.69s |

The existing Starlette/HTTPX deprecation warning remains. These are owner-run
results supplied for final review, not a Codex PostgreSQL rerun; no separate
per-case transcript was supplied. They supersede the pending-live status in
earlier preparation entries for these three suites only.
Uses unchanged 0003_auth.auth_throttle_buckets, no migration/dependency, team API,
role/permission changes, background process or cleanup. Production HTTPS/browser
verification remains outstanding. Final review evidence: PROGRESS.md.

## Limits and public contract

| Scope | Default per 300-second window | Configurable range |
|---|---|---|
| Login account, across IPs | 5 | MERGE_AUTH_LOGIN_ACCOUNT_LIMIT: 1–100 |
| Login client IP, across accounts | 30 | MERGE_AUTH_LOGIN_IP_LIMIT: 1–500 |
| Registration client IP | 5 | MERGE_AUTH_REGISTER_IP_LIMIT: 1–50 |

MERGE_AUTH_THROTTLE_WINDOW_SECONDS defaults to 300, range 60–3600 for HTTP.
There is no disabled/unlimited setting. The service accepts 1-second windows for
bounded real-clock tests only; HTTP startup rejects windows below 60 seconds.
All app workers/instances must share the same database, limits, window and secret.
Apply configuration changes together at a window boundary. Mismatched limits
are not detectable from existing storage; mismatched duration at a colliding
bucket expiry fails closed. Secret rotation partitions/resets counters and needs
coordinated owner review, not automatic per-worker generation.

All syntactically valid login/registration attempts consume admission budget,
including successes, wrong/unknown credentials, duplicates and later KDF/service
failures. No success-based reset. Login first charges the IP, then the account if
the IP permits. Account denial still commits the IP charge; denied IPs do not
create arbitrary account rows. Login and registration IP scopes are separate.
Account normalization is exactly the existing canonical lowercase ASCII username
representation. Uppercase/whitespace/Unicode aliases remain invalid HTTP input;
no credential policy changes or account-existence lookup in the limiter.

Origin, content-type, custom-header, Fetch Metadata and strict body checks precede
route admission. Invalid requests do no Argon2 work. Once valid, admission happens
before CredentialService.register / SessionService.login. A short independent
transaction must commit before those services run. GET /auth/session and POST
/auth/logout retain their existing validation/CSRF behavior and consume no new
login budget. No process-memory counters or per-process admission authority.

Denied admission returns 429:
`{error:{code:"rate_limited",message:"Too many authentication attempts.",retryable:true}}`.
Retry-After is ceil of remaining database-clock seconds, clamped to 1..window
(absolute maximum 3600). Auth no-store headers also cover 429. No scope, account,
IP, key hash, password or counter values appear in responses/errors/logs. A storage,
clock/configuration, integrity or unexpected failure gives sanitized 503 and never
continues to credential/session work. Existing known rolled-back lock/conflict
errors may be retryable; there is no automatic retry or fail-open fallback.

## PostgreSQL authority and privacy

Each scope uses HMAC-SHA256(secret, short_scope + NUL + canonical_identifier),
where short_scope is login_ip, login_account or register_ip. Only the
32-byte keyed digest and fixed scope label reach SQL; raw username/IP and the key
do not. Login account and IP keys are domain separated. IPv4-mapped IPv6 addresses
normalize to the corresponding IPv4 address; literal IPv6 is compressed. No
password participates in a key. HMAC storage is pseudonymous, not anonymous;
database dumps, matching keys, traffic correlation and secret compromise remain
privacy concerns. Never log keyed identifiers, headers, request bodies or locals.

A MATERIALIZED clock_timestamp snapshot assigns each counter statement to an
epoch-aligned date_bin window. A single INSERT ... ON CONFLICT ... DO UPDATE
on (scope,key_hash,window_start) performs the charge, returning its committed
decision. LEAST(existing_attempts, limit)+1 saturates at N+1 before addition,
avoiding BIGINT overflow. Database uniqueness/row updates serialize competing
connections. There is no check-then-insert or in-process lock for admission.
See the primary PostgreSQL documentation for
[date_bin/database clocks](https://www.postgresql.org/docs/17/functions-datetime.html)
and [atomic INSERT ON CONFLICT behavior](https://www.postgresql.org/docs/17/sql-insert.html).

The service reuses the existing credential transaction owner, safe Engine logging
requirements and actual synchronous psycopg AUTOCOMMIT-is-False / READ COMMITTED
guard. Its own lock/statement timeouts narrow to 1s/2s. It locks one IP bucket then
at most one account bucket in that order; no KDF, HTTP/network work or session
transaction is held inside it. Denial is raised only after the owned transaction
commits, preserving charges. A statement/COMMIT failure unwinds and returns 503;
ambiguous COMMIT loss never permits KDF and is not blindly retried. A charged
attempt followed by an unavailable login service remains charged intentionally.

Each scope statement uses its database observation time. An UPSERT queued before
expiry can complete in its old window after expiry; Retry-After then clamps to 1.
Fixed-window boundaries can admit up to 2N near a boundary. This is admission
counting, not a guarantee of constant work in every sliding interval. Expired
buckets remain retained and become inactive automatically by window selection.
No row deletion, reset, background cleanup or automatic expiration worker exists.
Distinct IP/account keys and windows grow storage; size monitoring and a separate
owner-approved retention/cleanup procedure are needed before sustained exposure.

## Actual client identity and server contract

Use the controlled launcher: `python -m app.serve`. It fixes Uvicorn
proxy_headers=False, forwarded_allow_ips='', access_log=False, overriding inherited
proxy-trust environment. Do not launch raw Uvicorn with default proxy middleware:
it can rewrite ASGI client/scheme before the application can verify the socket
peer. Any alternative ASGI host must preserve actual transport identity and disable
its forwarding interpretation. This trusted hosting contract is essential.

No proxy is trusted by default. Direct callers use the literal actual ASGI peer;
missing/non-IP peers, scoped IPv6 zone IDs and invalid schemes fail closed. Ports
are not part of keys. X-Forwarded-For/X-Forwarded-Proto from an untrusted peer, and
Forwarded/X-Real-IP from any peer, receive 403 client_identity_rejected before
storage or KDF. The server never derives identity from Host or arbitrary headers.

To trust one immediate proxy, explicitly set MERGE_AUTH_TRUSTED_PROXIES to a JSON
array of exact IPs/CIDRs, maximum 16, no wildcard or /0 (including mapped IPv4 /0).
That actual peer must overwrite and supply exactly one literal X-Forwarded-For
address and one X-Forwarded-Proto value of http or https on each auth request.
Missing, duplicate, chained/comma-separated, port-bearing, malformed or alternative
headers are rejected. Multi-hop forwarding is unsupported and needs separate review.
For trusted TLS termination, only this verified immediate peer may supply the
public HTTPS scheme; production still rejects HTTP. Restrict backend ingress to
that proxy and ensure the proxy overwrites client-submitted forwarding headers.
Never trust a broad network merely because headers claim to originate there.

Vite remains an untrusted local proxy, preserving the existing Origin policy and
using its loopback transport IP. All local Vite clients therefore share that IP
budget. Production reverse-proxy/TLS/real-browser behavior remains unverified.
Exact per-IP limits do not stop distributed IPs or IPv6 address rotation; NAT
users share a budget. Account throttling also permits deliberate account denial
by an attacker. No CAPTCHA, MFA, progressive lockout or global DDoS claim.

## Secret configuration and local startup

MERGE_AUTH_THROTTLE_SECRET is required at startup: exactly 64 lowercase hex
characters encoding a random 32-byte secret, read only from process environment,
redacted/excluded from settings repr. No dotenv/default/random runtime fallback.
Provision it through a private secret mechanism and reuse it across workers and
restarts. Never put a literal value into source, chat, reports or shell history.
For a fresh local development environment only, this assignment creates a key
without displaying its value; keep the shell environment for subsequent restarts:

```powershell
Set-Location I:\Merge\backend
if (-not $env:MERGE_AUTH_THROTTLE_SECRET) {
    $env:MERGE_AUTH_THROTTLE_SECRET = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
    if ($LASTEXITCODE -ne 0) { throw 'Throttle secret generation failed.' }
}
$env:MERGE_AUTH_MODE = 'development'
$env:MERGE_AUTH_ORIGIN = 'http://127.0.0.1:5173'
.\.venv\Scripts\python.exe -m app.serve --host 127.0.0.1 --port 8000
```

Do not use transcripts. Reopening a shell needs the same privately provisioned
key; generating a new one resets throttle partitions. The local HTTP regression
runner uses an ephemeral shared test key for its child servers and the controlled
launcher; it requests no credentialed auth operation and opens no database.

## Owner-verified guarded verification

Database-free fixtures use explicit synthetic secrets and service doubles for
HTTP-policy tests; those do not prove atomic SQL/concurrency. Guarded API tests
inject real throttling, credentials and session services, using a fresh private
fixture key per case to avoid unrelated retained-test budget collisions. Dedicated
tests deliberately share one key across independent services/app instances.
No production/runtime key fallback exists. The owner-verified live results above
cover these dedicated and updated suites; Codex performed database-free review.

The fixed throttles suite has 33 cases at three repetitions: first-N/saturation,
account/IP scope separation, eight server-observed independent connections for
both account and IP races, actual DB-clock expiry, two-app login/registration,
wrong/unknown credential charging, exact 55P03 storage-lock failure before KDF,
and actual AUTOCOMMIT no-counter-SQL rejection. Fresh guarded observers check
retained throttle and session/credential state, including after failures. Unknown
faults, timeouts and integrity errors cannot pass as expected 429 or the deliberate
timeout 503. One-second expiry tests have a bounded startup margin and can fail
on a busy host; deadlines/infra failures are never accepted as success.

The owner completed the suites above; commands are retained for reproduction.
Run separately in an interactive PowerShell terminal without transcripts. Each
command uses the existing hidden merge_app password prompt. Never run ordinary
development pytest or Alembic for this task; no migration/reset/cleanup is needed.

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Read-only target verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite throttles --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Throttle verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite auth-api --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Auth API regression failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite sessions --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Session regression failed. Stop.' }
```

Owner exercise: trace why raising 429 inside the database transaction would undo
the counter. Change login account limit from 5 to 3 consistently across app
instances and predict the fourth request's response before running the test.

## Changed-file inventory

Runtime additions: backend/app/services/throttling.py,
backend/app/security/client_identity.py, backend/app/serve.py. Runtime adapters:
backend/app/auth.py, backend/app/main.py, backend/app/security/auth_policy.py.

Tests: backend/tests/test_throttling.py, backend/tests/test_client_identity.py,
backend/tests/test_auth_throttle_http.py, backend/throttle_tests/conftest.py,
backend/throttle_tests/test_throttling.py (new); backend/tests/test_auth_http.py,
backend/tests/test_health.py, backend/tests/test_auth_schema_support.py,
backend/tests/test_concurrency_harness.py, backend/auth_api_tests/conftest.py,
backend/auth_api_tests/test_auth_api.py, backend/test_support/concurrency.py,
scripts/check_local_http.py (adapted).

Docs: README.md, docs/AUTH_THROTTLING.md (new), docs/HTTP_AUTH.md,
docs/AUTH_SCHEMA.md, docs/CREDENTIAL_SERVICES.md, docs/SESSION_SERVICES.md,
docs/TEST_DATABASE.md, docs/ARCHITECTURE.md, docs/DECISIONS.md,
docs/REQUIREMENTS.md, docs/PROGRESS.md. No frontend change.

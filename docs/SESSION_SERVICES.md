# Internal session lifecycle — M-007B.2B

Owner-verified checkpoint, 2026-11-10: **63 passed in 51.63 seconds** against
guarded merge_test / 0003_auth, three repetitions requested. Fresh session
committed-state invariants verified; fixtures intentionally retained. This is the
owner's PostgreSQL result, not a Codex database rerun. Codex checkpoint regressions:
**222 passed, 32 deselected in 7.49s**; dependency and static checks passed. No
database connection, migration or development-secret access occurred during the
Codex review. Existing credential evidence (51 passed in 28.76s) remains historical.

Uses unchanged 0003_auth. No HTTP endpoints, cookies, HTTP CSRF policy, durable
rate limiter, password-change workflow or authenticated team API. G1 stays open.

## Interfaces and sensitive material

```python
service = SessionService(engine)
material = service.login(username=username, password=password)
# IssuedSession(principal, created_at, session_token, csrf_token)
# Only deliberate unwrapping reveals the raw bytes:
raw_session = material.session_token.get_secret_value()
raw_csrf = material.csrf_token.get_secret_value()
principal = service.validate(raw_session)
principal = service.verify_csrf(raw_session, raw_csrf)
service.revoke(raw_session)
```

SessionPrincipal contains stored user_id, canonical username and expires_at. It
does not carry a password/hash/token. IssuedSession is an intentionally sensitive
internal result: token fields use Pydantic SecretBytes and are excluded from its
dataclass repr. Ordinary repr/str are redacted; unwrapping, custom serialization,
traceback locals and debug/APM capture can reveal secrets. Never log this material,
passwords, encoded hashes, SQL parameters or connection URLs. Python transient
bytes/strings cannot be reliably zeroized. This is not an HTTP encoding contract;
only exactly 32-byte immutable bytes are accepted as raw session/CSRF inputs.

Each login generates two independent `secrets.token_bytes(32)` values outside the
write transaction. Only SHA-256(raw session) reaches auth_sessions.token_hash;
the raw bearer is never a SQL parameter or persisted column. The independent CSRF
token uses the existing 32-byte server-side csrf_token representation. There is no
process-memory session store, JWT or externally accepted authentication ticket.
The [Python secrets API](https://docs.python.org/3/library/secrets.html) supplies
the CSPRNG and comparison primitive. Randomness tests check independent issuance
and calls, not a statistical proof of entropy.

## Verified-login handoff and trust boundary

The only issuance entry point is login(username,password). It invokes the approved
CredentialService verification path, including bounded real/dummy Argon2 work.
The public verify_credentials result remains CredentialIdentity with its original
interface. A registration result, constructed CredentialIdentity, user UUID or
SessionPrincipal cannot authorize issuance: no issuance method accepts one.

CredentialService adds a private verification snapshot consumed only within this
facade: user/username, credential creation/update timestamps and SHA-256 of the
successfully verified encoded password hash. The snapshot has no raw password or
encoded hash and is not a public proof/ticket. Verification closes its READ ONLY
connection before hashing. The facade then acquires locks and compares the current
credential against that exact snapshot. Deletion, replacement or relevant change
between verification and issuance rejects with authentication_changed and no row.

This is an internal trusted-Python/Engine boundary, not protection from malicious
code in the same process or an administrator holding database credentials. Python
private attributes are not unforgeable capabilities. Trusted Engine listeners must
not inject mutations, change connection mode or capture secrets. Future HTTP login
must call this facade rather than accepting an identity/snapshot from a client.
The facade intentionally does not support turning a previously returned public
CredentialIdentity into a session; callers must supply credentials to login.

## Transactions, locks and absolute lifetime

SessionService reuses CredentialService's private transaction owner and sanitized
database error mapping, rather than copying its safety boundary or altering
TeamService. It requires an Engine with hidden parameters and disabled SQL echo,
synchronous PostgreSQL+psycopg, actual DBAPI autocommit **is False**, no active
caller transaction and actual READ COMMITTED. Unsupported/unreadable/ambiguous
settings fail closed before service SQL; no Engine mode is silently changed.
Trusted test identity/Engine initialization reads may precede the service guard.

After verification and random generation, issuance owns one write transaction:

1. Lock the verified user `FOR KEY SHARE`.
2. Lock its current account_credentials row `FOR SHARE` and compare snapshot
   identity, username, timestamps and constant-time password-hash fingerprint.
3. Read database clock_timestamp(), normalize aware values to UTC, set creation
   to that instant and expiry to creation + eight hours.
4. Insert the digest, user, independent CSRF and timestamps; commit before any
   sensitive result is returned to the caller.

Credential SHARE blocks non-key hash/username/timestamp UPDATE and DELETE through
commit; KEY SHARE alone would not. It remains compatible with the session's FK
KEY SHARE checks. User KEY SHARE prevents principal deletion without taking the
team service's stronger membership lock. Concurrent logins may both succeed and
issue independent sessions. No hashing/network calls occur while these locks are
held. Future multi-record credential maintenance must review this user → credential
order; arbitrary SQL using a reverse order can still deadlock. Deadlocks/conflicts
are reported, not silently retried. Each transaction has 5s lock and 15s statement
timeouts, inherited from the credential boundary.

Validation opens a fresh READ ONLY transaction and joins the stored session to
both users and credentials. It requires an existing canonical credential with the
approved bounded Argon2id encoding profile, no revocation, creation <= current
database clock < expiry and the exact eight-hour lifetime. This structural
credential check is not another password verification or a database proof of KDF
provenance. It derives the principal from these rows. It does not write or extend
expiry. Malformed tokens fail before a connection is acquired. The database clock
must remain trustworthy; no caller-supplied clock is accepted. This implements
server-side absolute expiry as described by the
[OWASP session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

Validation is a point-in-time read: logout cannot cancel work already authenticated
in another transaction. No future password-change policy is claimed. Changing to
another supported credential hash does not automatically invalidate existing
sessions in this schema; a future reviewed password-change workflow must revoke
them explicitly. This component protects the check-to-issuance interval only.

## CSRF, revocation and errors

verify_csrf first validates the active session, then compares its stored CSRF value
with a correctly sized input using secrets.compare_digest. Another session's
token fails. This is an internal session-bound synchronizer primitive following
the [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html),
not implemented cookie/header/origin/CORS protection. Future HTTP logout and other
mutations must enforce the reviewed browser policy at their boundary.

revoke owns a transaction and updates only a matching digest with revoked_at IS
NULL, using GREATEST(clock_timestamp(),created_at). A concurrent READ COMMITTED
UPDATE rechecks that predicate after waiting. Repeat, unknown and already-revoked
tokens are safe no-ops; expired retained sessions can still be marked revoked.
Neither expiry nor an existing terminal revocation timestamp is rewritten.

| Condition | Error |
|---|---|
| Malformed, unknown, expired, revoked or unusable account/session | SessionError: invalid_session |
| Active session with incorrect/malformed CSRF | SessionError: invalid_csrf |
| Verified snapshot no longer matches locked credentials | SessionError: authentication_changed |
| Missing timezone-aware clock / entropy provider failure | SessionError: clock_configuration / entropy_failure |
| Incorrect username/password, KDF saturation or configuration failure | Existing fixed CredentialError contract |
| DBAPI integrity, deadlock, lock/statement timeout or connectivity failure | Existing sanitized CredentialError mapping, after unwind |

No native/driver secret-bearing message is copied into a public error. Session
token digest collision is an integrity fault, never silent reuse/overwrite or an
automatic retry. Injected statement/pre-COMMIT failures must roll back all session
writes. A network loss during COMMIT can be ambiguous: no raw material is returned
on failure, but an unreachable committed row could remain. No blind retry or
idempotency guarantee is claimed. Deployment logging/traceback-local capture
remains trusted configuration, even when fixed exceptions have no driver context.

## Executed checks and owner-verified live evidence

Final checkpoint: owner reports **63 passed in 51.63 seconds**, guarded merge_test /
0003_auth, three repetitions requested and fresh session committed-state invariants
verified. Fixtures intentionally retained. No separate raw per-case transcript or
post-change credential/auth/domain/team live regression results were supplied.
Codex reviewed all 63 collected cases and their shared fixtures/workers; unexpected
SQLSTATEs, timeouts and integrity faults cannot satisfy their success assertions.
The checkpoint database-free run passed 222 tests (32 deselected, one existing
Starlette/HTTPX warning) in 7.49s; pip check passed; collection found 63 in 0.04s.
Full review/static evidence and limitations: [PROGRESS.md](PROGRESS.md).

Earlier implementation-preparation commands below remain historical evidence.

Commands from backend, Python 3.11.9 / SQLAlchemy 2.1.8 / psycopg 3.3.8:

- `.\.venv\Scripts\python.exe -m pytest -q tests/test_sessions.py tests/test_credentials.py tests/test_passwords.py --tb=short`:
  **102 passed in 4.37s**.
- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
  **222 passed, 32 deselected in 5.94s**, one existing Starlette/HTTPX warning.
- `.\.venv\Scripts\python.exe -m pip check`: no broken requirements found.
- `.\.venv\Scripts\python.exe -m pytest session_tests --collect-only -q`:
  **63 collected**, no fixtures executed.
- Separate collection of credential_tests / auth_schema_tests / service_tests /
  concurrency_tests: **51 / 78 / 48 / 45** cases respectively. These are collection
  results, not post-change live passes. Guarded runner `--help` also executed.

The 63 session cases cover the required lifecycle, digest-only storage, redacted
representations, independent issuance, generic login rejection, cross-session CSRF,
terminal/concurrent revocation, expiry crossing, unsupported credentials, injected
post-INSERT/pre-COMMIT rollback, real AUTOCOMMIT zero-service-SQL rejection, stale
verification rejection and a server-observed SHARE-lock wait during issuance.
Synchronization uses events/barriers, independent actual PostgreSQL connections,
pg_blocking_pids and bounded workers; unexpected errors/timeouts fail the run.
Collection alone does not establish PostgreSQL behavior or SQLSTATEs; the owner
has since supplied the live pass above. Codex did not rerun PostgreSQL.

Fresh guarded observers verify scoped session/user/credential integrity, byte
lengths, immutable lifetime and revocation relationship after each case, including
failures. Fixture users, credentials and sessions use unique identities and are
intentionally retained only in merge_test. No DELETE/TRUNCATE/reset/trigger
disabling is needed. Fixture-only credential updates exercise adversarial schedules,
not a production password-change API. The expiry test requires its initial check
within a two-second window, then observes the actual database clock with a bounded
five-second deadline. A busy host, missing blocking-PID visibility or deadline
failure is a failed test, never accepted as successful concurrency evidence.

## Exact owner-run commands (session suite owner-verified)

Run in an interactive PowerShell terminal without transcripts. These commands
privately prompt for the existing merge_app password; never put it in chat,
arguments, history, source or reports. Clear only the process-local test variable
to select the existing hidden-password mechanism. No migration is needed.

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Read-only target verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite sessions --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Session tests failed. Stop; do not reset or weaken schema.' }
```

The entry point enforces explicit opt-in, local 127.0.0.1:5432, merge_test /
merge_app and explicit revision 0003_auth. Each service connection and observer
checks actual server identity before fixture writes. It never loads backend/.env,
falls back to merge_dev or runs migrations. Safe pytest output disables local/
parameter assertion dumps and third-party plugin autoload. Direct suite execution
without the private guarded settings fails before opening PostgreSQL.

Run existing guarded regressions separately after successful target verification:

```powershell
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite credentials --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Credential regression failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite auth --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Auth schema regression failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite services --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Team service regression failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite schema --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Domain regression failed. Stop.' }
```

Shared pytest option hooks require separate suite invocations. Never run the
legacy ordinary backend database suite for this task: it targets merge_dev.
No new dependency, schema, migration, credentials, roles, privileges, TeamService
or frontend changes. The session live pass is owner-verified; no additional
post-change live regression pass, authenticated HTTP/50-way race,
CI/load/deployment or gate closure is claimed.

Owner exercise: explain why a constructed CredentialIdentity is not login proof,
then trace the stale-snapshot test and why FOR SHARE (rather than KEY SHARE) is
needed to block a non-key password-hash update until session commit.

# Authentication storage — M-007B.1

M-007B.2B implements internal session login/validation, session-bound CSRF and
terminal revocation using this unchanged storage. Owner verified **63 passed in
51.63s**, guarded merge_test / 0003_auth, three repetitions requested, fresh session
invariants verified and fixtures retained. Codex: 222 database-free tests passed;
no PostgreSQL rerun. No HTTP endpoints or cookie policy. Handoff,
transaction/clock rules, limitations and reproducible private-
prompt owner commands: [SESSION_SERVICES.md](SESSION_SERVICES.md). Historical
storage-only descriptions below retain their original checkpoint scope.

M-007B.2A now implements internal credential hashing/registration/verification.
Owner verified 51 guarded live cases in 28.76s, three repetitions requested and
fresh committed-state checks; Codex checkpoint: 175 database-free tests passed.
No storage DDL changes or PostgreSQL rerun by Codex.
See [CREDENTIAL_SERVICES.md](CREDENTIAL_SERVICES.md). The storage-only checkpoint
description below records the earlier M-007B.1 scope, not runtime authentication.

Owner verified guarded merge_test migration/repeat, 0003_auth (head) and preserved
domain row counts/fingerprints. Live auth schema suite: **78 passed in 11.75
seconds**, three repetitions requested (2026-11-09). Codex checkpoint regressions:
**116 database-free tests passed**; PostgreSQL was not rerun by Codex. Storage
only: no registration/login, password verification, token issuance, CSRF validation,
rate-limit algorithm or auth/team endpoints. No Argon2 dependency added.

## Additive schema and integrity

0003_auth follows unchanged 0002_domain/0001_baseline. Frozen public-qualified DDL
creates three tables, three indexes, one new SECURITY INVOKER fixed-search-path
function and five triggers. No domain row backfill or credential adoption. New
table/type/function conflicts stop migration; nothing existing is replaced.
Downgrade refuses pending a separately approved retention procedure.

| Table | Storage |
|---|---|
| account_credentials | user_id PK/FK to users; UNIQUE canonical username; password_hash; created_at/updated_at |
| auth_sessions | token_hash BYTEA PK; user_id FKs to users AND credentials; csrf_token; creation/expiry/revocation timestamps |
| auth_throttle_buckets | PK(scope,key_hash,window_start); attempts default 0; expiry |

Usernames must be 3–32 ASCII lowercase letters/digits/underscores, checked using C
collation and an excluded-character class. No normalization occurs implicitly.
Credential timestamps are finite; updated_at cannot precede created_at. The user
and creation timestamp are immutable. Hash storage is bounded to 1024 characters
with an Argon2id prefix. This marker is NOT cryptographic validation; the future
service must generate/verify real Argon2id hashes. Test strings are synthetic,
not usable credentials. No existing user gets a credential automatically.

Session digest and independent CSRF token each require exactly 32 bytes. There
is no raw session-token column. The credential FK prevents sessions for existing
uncredentialed seeded users, but does not prove a login occurred. CSRF token is
stored server-side for future synchronizer-token use. Future services must create
random raw tokens, hash session tokens with SHA-256 and never log secrets; column
lengths alone cannot prove randomness/hash provenance.

All session timestamps are finite. Expiry is exactly creation + 8 hours; defaults
use the same transaction timestamp. Revocation cannot precede creation; revocation
after expiry is allowed for bookkeeping. Token hash/user/CSRF/creation/expiry are
immutable; revocation cannot be reversed or changed once set. New sessions are
needed for renewal. Future request authentication must still check time/revocation;
storing an expired row is allowed. Indexes cover session user and expiry.

Throttle scope is nonblank, key_hash is 32 bytes, attempts nonnegative, timestamps
finite and expiry after window start. Expiry is indexed. No policy thresholds,
atomic increment algorithm, client-IP trust or enforcement is implemented. Keys
must not contain raw IPs/usernames/passwords/tokens. Three new TRUNCATE guards
reuse the unchanged domain function. Ordinary auth DELETE remains available for
future reviewed cleanup; credential deletion with sessions is FK-restricted.
Tests use rollback, never deletion/TRUNCATE/trigger disabling for cleanup.

## Explicit guarded migration support

The runner accepts --revision {0002_domain,0003_auth}; its default remains
0002_domain. An auth DB is not accepted under that legacy default. Auth migration
requires explicit 0003 and current state exactly 0002 or 0003. Unknown/multiple
heads, base-to-auth shortcuts or downgrade attempts stop. Fresh setup first uses
the original 0002 migration command, then the explicit auth command.

The runner owns one transaction around DDL and before/after preservation checks.
The dedicated env rechecks identity inside it without rolling it back/committing
it independently. Auth upgrades/repeats take bounded SHARE locks on the seven
existing domain tables, compare counts/aggregate row fingerprints, and raise
before commit on mismatch. No contents/fingerprints are printed. Stop all other
merge_test writers first. This neither accesses nor depends on merge_dev.

The test runner adds --suite auth, requiring --revision 0003_auth. All suites
match the requested revision exactly. Existing opt-in, identity, loopback/role,
private-password and no-fallback safeguards remain. Schema/services can run on
the upgraded DB only with explicit --revision 0003_auth. Legacy backend database
tests still target merge_dev: do NOT run those for this task.

## Owner commands — retained for fresh approved setup

The owner has completed migration/repeat and the auth suite above. Do not rerun
the initial 0002 check against the current 0003 database. These commands document
the reviewed transition for fresh approved setup, not a checkpoint rerun or reset.

Run interactively without transcripts. Clear any process-local test password
environment variable as shown so each command privately prompts for the existing
merge_app password; this does not change the PostgreSQL password. Never put it
in chat or SQL/shell arguments. No
command below was executed by Codex; stop on any failure, do not repair/reset.

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0002_domain
if ($LASTEXITCODE -ne 0) { throw 'Baseline verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.database migrate --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Auth migration failed. Stop; do not reset.' }
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Auth revision verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.database migrate --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Repeated auth upgrade failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Repeated verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite auth --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Auth schema tests failed. Stop and review.' }
```

The initial 0002 verification intentionally refuses an already upgraded DB; inspect
with explicit 0003 verification rather than rerunning blindly. Optional regressions
after successful auth verification:

```powershell
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite services --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Service regression failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite schema --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Domain regression failed. Stop.' }
```

Auth tests use UUID-scoped users/auth rows in outer rollback transactions and
savepoints for expected errors. They check metadata drift without filtering,
uniqueness/FKs, digest/CSRF/timestamp relationships, immutable lifetime/revocation,
throttle storage and unchanged user rows/no additional adoption. No actual
password/session credentials are issued. The owner-verified 78-pass result covers
these collected checks, including the expected 23514 / ck_throttle_expiration
rejection. Unexpected SQLSTATEs, named constraints or non-integrity errors fail;
they are not treated as successful rejections. No separate per-case transcript
was supplied. Service/domain live regressions after 0003 were not reported and
remain pending; their earlier results are historical evidence only.

The rollback-only ORM relationship check uses the documented SQLAlchemy
[external-transaction/savepoint pattern](https://docs.sqlalchemy.org/en/21/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites).

Owner exercise: explain why a 32-byte CHECK cannot prove SHA-256 provenance or
randomness, and why expiry storage still requires request-time validation.

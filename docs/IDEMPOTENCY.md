# Private idempotency primitives — M-008C

M-014B adds invitation.issue.v1 and invitation.redeem.v1 to the private operation
allowlist. Fingerprints bind authenticated actor/hackathon/team and respectively
recipient or invitation UUID. Existing operation bytes and primitives are
unchanged. Current locked issuer/recipient/expiry authorization precedes replay
proof; only matching authorized redemption replay bypasses the pending rule.
Unknown COMMIT preserves exact-key recovery. [INVITATIONS.md](INVITATIONS.md)
documents expiry/leadership replay limits and exact-0005 validation. The R2
owner-run report/source audit and its provenance limits are in G1_ACCEPTANCE.md;
0005 is already applied to merge_test and must not be rerun for this review.

M-013A extends the private operation allowlist with request.create.v1 and
request.decide.v1. Existing team.create.v1/team.join.v1 fingerprints are unchanged.
Request commands bind team plus hackathon/actor; decisions additionally bind
request UUID and approve/reject. Key syntax, reservation/completion, retained
success bounds and same-key COMMIT reconciliation are unchanged. Request replay
proof is noted only after current authorization. [ADMISSION.md](ADMISSION.md)
defines the new stored reply and duplicate/terminal semantics. Owner completed
35 + 70 admission executions at 0004 in two successful guarded runs with completed
fixture checks; this includes the repaired admission COMMIT fault. It does not
certify legacy suites at 0004 or close the distinct-caller G1 requirement.

M-012A adds the create-only HTTP adapter using this unchanged exact key and
stored-reply contract. HTTP 201 replays and explicit outcome_uncertain same-key
retry instructions are in [TEAM_API.md](TEAM_API.md). No primitive/schema change;
the owner verified 105 HTTP cases in 140.81s at guarded 0003_auth. Codex did not
rerun PostgreSQL. Earlier no-public-route text is historical.

M-008E adds bounded retries and same-key ambiguous-COMMIT reconciliation around
the M-008D composed operations. Owner verified 54 retry / 81 mutation / 57 service /
60 idempotency cases, **252 passed in a 200.05s suite-time sum**, on guarded
merge_test / merge_app, READ COMMITTED, 0003_auth (head). Three repetitions
requested per suite, fresh committed invariants verified and fixtures retained.
Codex did not execute PostgreSQL tests. The primitive module/schema are unchanged.
Precise individual timings and the current orchestration policy:
[TRANSACTION_RETRY.md](TRANSACTION_RETRY.md).

M-008D now composes these primitives in explicit internal TeamService entry points;
see TEAM_MUTATIONS.md. Owner verified 81 composed cases in 101.23s, 57 service
regressions in 59.59s and 60 idempotency regressions in 40.81s: 198 passed, corrected
suite-time sum 201.63s, guarded 0003_auth, three repetitions requested per suite,
fresh invariants verified and fixtures retained. Codex did not rerun PostgreSQL.
A new frozen create request without an outcome UUID uses the same canonical V1
fingerprint as the
existing private create command; all reservation/replay/completion rules remain.
The M-008C checkpoint/history below records primitive-only evidence. No public
HTTP mutation routes exist.

Checkpoint against `35ddacecfd803c7fd1b1d1ed2a188873ba62f488`: owner verified
**60 passed in 40.82s** on guarded merge_test / **0003_auth**, three repetitions
requested, fresh committed-state invariants verified and fixtures retained.
This is owner execution evidence, not a Codex PostgreSQL rerun. The earlier
first-test bind failure is superseded by this full successful run; R1 changed
only test SQL, retaining the original one-effect assertion and adding an offline
regression. Historical details and checkpoint offline checks are in PROGRESS.md.
R-08 and G1 remain open. No composed idempotent team method existed at that
primitive checkpoint; M-008D later added internal composed methods. No public
HTTP mutation route exists.

## Contract

`app/services/idempotency.py` contains private frozen command, fingerprint,
reservation and reply types. `_command(team_command, key)` accepts the existing
private create/join command types. Operations are exactly `team.create.v1` and
`team.join.v1`; one reservation represents one future team mutation. Python
privacy is a trusted-code boundary, not a sandbox against malicious callers.

The existing `ck_idempotency_key` accepts 1–128 printable ASCII characters
(U+0020–U+007E). Spaces, including all-space keys, are significant; no trimming,
case folding or Unicode normalization occurs. Invalid keys fail before SQL.
The unique constraint is `uq_idempotency_scope(actor_id, operation, key)`.
Hackathon is deliberately compared after loading a conflict rather than included
in that unique scope. The database remains authoritative.

Fingerprint bytes are SHA-256 of UTF-8 JSON, sorted object keys, compact `,`/`:`
separators, literal Unicode and no non-finite numbers. The exact document is:

```json
{"actor_id":"canonical-lowercase-uuid","command":{"name":"exact validated name"},"hackathon_id":"canonical-lowercase-uuid","operation":"team.create.v1","schema_version":1}
```

Join replaces `command` with `{"team_id":"canonical-lowercase-uuid"}` and uses
`team.join.v1`. Actor/hackathon/target UUIDs and existing meaningful name rules
are validated; NUL and invalid UTF-8 are rejected before storage. Generated create
team IDs and the idempotency key are excluded from the fingerprint. Different
generated outcomes cannot turn a retry into a different command. Tests pin the
canonical bytes and preserve whitespace and canonically distinct Unicode names.

`_reserve_in_tx(connection, command)` executes exactly:

```sql
INSERT INTO public.idempotency_records
    (id, actor_id, hackathon_id, operation, key, request_hash)
VALUES (:id, :actor, :hackathon, :operation, :key, :fingerprint)
ON CONFLICT ON CONSTRAINT uq_idempotency_scope DO NOTHING RETURNING id;
```

A returned ID yields a `_Reservation` bound to that connection and its current
root transaction. On conflict, INSERT can wait for a competing transaction;
rollback lets the contender insert, while commit causes DO NOTHING. A **separate
SELECT statement** by actor/operation/key then gets a fresh READ COMMITTED
snapshot. A same-statement CTE would not supply this guarantee. Completed records
are immutable and retained by the existing triggers, so replay needs no UPDATE
or additional row lock. Missing/corrupt/pending records are `integrity_fault`.
Different fingerprint or hackathon is `idempotency_mismatch`, non-retryable and
containing only that fixed code, never hashes, keys or SQL details.

`_StoredReply._from_values(status, body, headers)` validates successful 2xx status,
the exact JSON envelope `{"schema_version":1,"data":{...}}`, and only these exact
optional lower-case headers: `content-type: application/json` and
`cache-control: no-store`. No cookies, arbitrary location, authorization or
caller-selected header values are stored/replayed. Body limits: 16,384 UTF-8 bytes,
depth 8, 1,024 visited values/keys, at most 128 entries per object/list, strings at
most 4,096 characters, signed 64-bit integers, booleans and null. Floats are
excluded: JSONB can expand exponent notation into an integer outside those bounds
on replay. Team result UUIDs/counts do not need floating-point values.
NUL, invalid UTF-8 and non-JSON objects fail closed. These are private V1 limits,
not a newly published HTTP response contract. Replies retain canonical JSON text
and immutable header tuples; `body()` returns a fresh object. Sensitive values
are excluded from repr. JSON equality, status and headers are replayed; original
HTTP byte formatting is not stored by JSONB.

`_complete_in_tx(connection, reservation, reply)` updates exactly the pending
record matching ID, actor, operation, key, hash and hackathon, sets the successful
reply and database `clock_timestamp()`, and requires one returned ID. A different
connection/root transaction, duplicate completion or invalid reply is an
integrity fault. It returns locally; **only the owner may expose the reply after
COMMIT succeeds**. Failures, including after completion, roll back the reservation
and all effects. There is no success-before-commit shortcut.

## Ownership, locks and failure policy

No helper opens, begins, commits, rolls back or closes a connection. Each requires
an active, non-nested PostgreSQL/psycopg READ COMMITTED transaction and checks the
actual DBAPI autocommit flag before reservation SQL. SQLAlchemy's logical begin()
cannot make DBAPI AUTOCOMMIT safe. `TeamService._execute` remains the only team
transaction owner; its initial guard and sanitized database-error mapper remain
unchanged. Legacy timeouts remain 5s/15s; M-008E clamps composed-operation lock/
statement timeouts to the remaining monotonic budget without raising those caps.

Legacy create/join call graphs and behavior remain unchanged. M-008D composes
`_execute -> reserve -> mutation/version/audit/outbox -> complete -> COMMIT`;
M-008E orchestrates bounded attempts around that complete owner call. Composition
reserves before hackathon SHARE -> user NO KEY UPDATE -> team NO KEY UPDATE,
then takes fresh post-lock counts. No mutation or domain lock is added in the
primitive helper. Reservation's unique-index wait and FK KEY SHARE locks
must not be introduced after domain locks by a future caller. Taking multiple
reservations per transaction, or mixing raw writers with the inverse order, risks
deadlocks and is outside this policy. Never hold the owner transaction across
external network work.

Existing mappings apply to deadlock/serialization conflict, lock timeout,
statement timeout and integrity errors; unexpected database failures fail closed.
Primitive helpers have no automatic retry, lease, expiry, deletion or takeover.
If COMMIT acknowledgement is lost, the caller cannot infer success from a local
reply; later same-command reservation/replay can discover a committed success.
M-008E now orchestrates automatic same-key reconciliation for composed operations;
unresolved outcomes return uncertainty. Public HTTP retry semantics remain
unimplemented. Failed commands have no retained result and can be attempted anew.
Future public composition must authenticate/authorize the actor; these primitives
do not grant team or invitation/request authorization.

## Schema and live verification

No migration is needed: the existing immediate unique scope, 32-byte hash,
pending/completed shape, immutable completed rows and retention triggers support
this policy. `ct_idempotency_final` raises `23514 / ct_idempotency_completed` if a
pending row reaches COMMIT. A committed pending row therefore cannot be seeded
without weakening an invariant. Tests instead cover own-transaction visible
pending rejection, exact deferred COMMIT rejection, and independent-connection
invisibility; offline tests inject a loaded pending row into the replay branch.
No trigger is disabled or fixture database reset.

The explicit `idempotency` suite in `test_support.concurrency` requires revision
`0003_auth` before requesting credentials. Every fixture, service, worker and
observer connection independently verifies merge_test identity, READ COMMITTED
and revision. Direct pytest execution fails before opening a connection. New
UUID-scoped fixtures are retained. Fresh independent connections verify completed
reply shape, no pending records, original team invariants, and zero teams,
memberships, audit/outbox rows in each new fixture hackathon. A test-only effect
appends to a fixture user's display name; no real team mutation is composed yet.

Concurrency tests require server-observed `pg_blocking_pids`, different backend
PIDs, matching replay after the winner commits and new reservation after rollback.
Unexpected database errors, timeout or missing observation fail the test. Event/
queue waits are 8s, observation 3s, worker join deadline 30s, server connect/lock
5s and statement 15s. Busy hosts can fail timing tests; no retry masks a failure.
Do not rerun a failed worker-deadline run before checking that owned clients ended.

From the owner's PowerShell terminal (hidden password prompts; no transcript or
password in command text), run:

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Database verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite idempotency --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'M-008C verification failed. Stop.' }
```

This verifies and tests, never migrates. Credential-free collection is
`.\.venv\Scripts\python.exe -m pytest idempotency_tests --collect-only -q`.
Actual offline evidence is recorded in PROGRESS.md. The owner-verified local
PostgreSQL result above covers these private primitives. Production HTTPS/browser
verification, authenticated 50-way API race and G1 closure remain outstanding.

Owner exercise: explain why a conflict SELECT needs its own statement; change
only a generated create team ID in the fingerprint test and predict why the hash
must stay identical. Trace a failure after completion through the owner's rollback.

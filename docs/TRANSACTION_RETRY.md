# Bounded transaction retries and reconciliation — M-008E

Checkpoint against `bdbbf3ddd46dd7e67aa04577f1d0d6969ac2eb8b`: owner verified
merge_test / merge_app, READ COMMITTED, **0003_auth (head)**:

| Guarded suite | Passed | Time |
| --- | ---: | ---: |
| Retries | 54 | 48.66s |
| Mutations | 81 | 72.40s |
| TeamService | 57 | 36.15s |
| Idempotency | 60 | 42.84s |
| Total / suite-time sum | **252** | **200.05s** |

Three repetitions requested for all suites; fresh committed-state invariants
verified and fixtures retained. These are owner-run PostgreSQL results, not
Codex database executions. M-008D's 198 passes remain historical baseline evidence.
Final checkpoint offline/static evidence is in PROGRESS.md. G1 remains open.
No HTTP mutation endpoints, schema, migration, dependency or infrastructure change.

## Scope and ownership

Only `create_team_idempotent()` and `join_team_idempotent()` enter this policy.
Their signatures, validation, canonical V1 fingerprint, success status/body/headers,
audit/outbox payloads and lock sequence are unchanged. Trusted actor input still
requires session-derived identity and current authorization at the future HTTP
boundary, including replay. Legacy `create_team()`/`join_team()` remain internal
single-attempt compatibility paths. No retry is attached to primitive helpers.

```text
composed entry point
  -> validate immutable request + key + canonical fingerprint ONCE
  -> _run_composed(same operation closure; one monotonic deadline)
     -> at most THREE total attempts, including reconciliation
        -> TeamService._execute (only connection / transaction owner)
           -> fresh guarded Connection; actual DBAPI autocommit=False
           -> PostgreSQL/psycopg sync, READ COMMITTED, no existing transaction
           -> bind private deadline/phase metadata; one begin
           -> same-key reservation INSERT / fresh conflict SELECT
              matching completed reply: no domain writes
              newly reserved: hackathon SHARE -> user NO KEY UPDATE
                -> existing team NO KEY UPDATE -> fresh count / mutation
                -> version -> one audit -> one unpublished outbox -> completion
           -> check remaining budget; one COMMIT
           -> record confirmed reply; remove metadata; close Connection
        -> only AFTER full unwind: classify / jitter / possible next attempt
  -> reply only on confirmed COMMIT or immutable matching committed-row replay
```

The owner accepts private `_attempt` metadata; this adds no second transaction
owner. Helpers never acquire connections or begin/commit/rollback/close one.
An attempt's metadata is removed from the captured pool-info dictionary even if
the handle becomes invalid, without accessing invalid `connection.info` again.
No SQL statement is retried inside an aborted transaction. Lock order and
post-lock counts remain unchanged; each attempt reacquires every lock and starts
reservation again. A rolled-back create may allocate a different outcome UUID;
the meaningful request, actor, operation, key, hackathon and hash remain identical.

## Policy, budget and failure classification

Configure with `TeamService(engine, retry_policy=TransactionRetryPolicy(...))`
from `app.services.transaction_retry`. Policy is immutable. `total_seconds` is a
finite number in **[1, 60]**, default **30**; `jitter_ms` is an integer in
**[0, 250]**, default **50**. Booleans are rejected. Total attempts are fixed at
three, never a configurable fourth. Policy is captured once per call. Jitter
is uniform from zero to its ceiling, capped by remaining operation budget,
and runs only after the previous owner's contexts have exited.

Monotonic deadline checks precede acquisition, every application SQL statement,
another attempt, and COMMIT preparation. Per-statement transaction-local
`set_config` clamps statement/lock timeouts to remaining milliseconds, capped at
the existing **15s/5s** maxima. Expired budget starts no further SQL/attempt.
Confirmed success is returned even if its acknowledgement/cleanup consumes the
remaining budget; it is never relabeled a failed mutation.

This is a cooperative operation budget, **not hard cancellation of a synchronous
driver call**. Connection/pool acquisition, network delivery and cleanup retain
their configured driver/transport bounds; a stalled transport can exceed the
budget before control returns. The guarded harness has connect_timeout=5s.
No background thread/worker is introduced, and a hard response-time bound under
a broken network is not claimed. SQL execution still has PostgreSQL timeouts.

| Evidence / phase | Action |
| --- | --- |
| Observed DBAPI SQLSTATE exactly 40P01 or 40001, work or COMMIT | Entire owner unwinds, then retry if attempts and budget remain |
| Business rejection, mismatch, integrity fault, 55P03, 57014, unknown SQLSTATE or connection error before COMMIT | Existing sanitized error; no automatic transaction retry |
| Known COMMIT rejection: 40P01/40001, 55P03/57014 or valid class 22/23 SQLSTATE | Confirmed rejection; only 40P01/40001 eligible for retry |
| Unknown/missing/connection SQLSTATE or other exception during COMMIT | Outcome unresolved: fresh same-key reservation protocol, within the same cap/budget |
| COMMIT confirmed, subsequent connection-cleanup error | Return the confirmed stored reply after unwind |
| Immutable matching committed reply loaded, subsequent read-transaction/cleanup error | Valid reconciliation: return that original stored reply after unwind |
| Budget exhausted without unresolved COMMIT | `transaction_deadline`, retryable=true; no extra attempt |
| Unknown COMMIT still unproven after cap/budget or reconciliation failure | `outcome_uncertain`, retryable=true; never claim failed or succeeded |

`DomainError.retryable` alone is never proof of a PostgreSQL abort. The error
mapper remains unchanged; private attempt flags preserve only the necessary
classification/phase, not raw SQLSTATE, SQL, exception text or credentials.
Original transaction classification is captured before connection cleanup;
later cleanup errors cannot replace an unknown COMMIT with apparent abort proof.
New codes are internal domain errors; no HTTP status contract is invented here.

## Ambiguous COMMIT contract

A locally completed `_StoredReply` is not commit proof. After an unknown COMMIT
acknowledgement the only recovery is the **same** actor/operation/key/hackathon/
fingerprint reservation on a fresh guarded connection. No immediate SELECT for
absence, generated replacement key, takeover lease or expiry exists.

The unique-index INSERT waits for the earlier transaction to resolve. If it
conflicts, the separate fresh READ COMMITTED SELECT must validate an immutable
matching successful row before replay. No mutation/version/audit/outbox stage
runs in this path. If INSERT instead returns a new reservation, PostgreSQL has
resolved that unique-key contest and the earlier reservation did not commit;
the full operation may safely run. That proof clears earlier uncertainty. A new
COMMIT loss restores uncertainty. A timeout/error while the earlier outcome is
still unresolved returns uncertainty, not an inference of rollback. Corrupt or
mismatched outcomes never become successful replies.

Caller recovery from uncertainty must preserve the same validated command and
key and reauthenticate/authorize at the eventual HTTP boundary. Business state
can change between aborted attempts. This policy cannot promise eventual success.
No events are published inside these transactions; only committed outbox rows
are eligible for a future dispatcher.

## Verification and owner run

Database-free tests use a committed-state ledger with independent handles,
injected exact DBAPI states, fake monotonic time/jitter and strict rollback/
effect counts. These prove orchestration behavior, not PostgreSQL races.

Fixed `--suite retries` selects `retry_tests`, requires explicit **0003_auth**
before credentials, and reuses the retained mutation fixtures and fresh complete
chain/invariant checks. Tests inject real server exceptions after domain/audit
writes with `DO ... RAISE` (no schema objects), requiring exact SQLSTATE and
attempt counts. COMMIT hooks either invoke the real PostgreSQL commit before
raising acknowledgement loss or raise before commit to exercise rollback.
These are controlled faults, not proof of natural deadlock or network outages.
Original 81 mutation / 57 service / 60 primitive cases remain separate live
regressions. Fresh connections, actual transaction guards and zero partial
effects must all pass. No timeout/database failure is accepted as a race success.

For reproduction, run in an interactive PowerShell terminal without a transcript; credentials are
entered only at the existing hidden prompt. Every step stops on failure:

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Database verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite retries --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'M-008E retries failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite mutations --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Mutation regressions failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite services --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Service regressions failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite idempotency --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Idempotency regressions failed. Stop.' }
```

No migrations/resets/cleanup run; UUID fixtures are retained. Current counts,
commands, timings and remaining limitations are in PROGRESS.md. G1, authenticated
50-way API/CI/load, production HTTPS and browser verification remain open.

Owner exercise: change an injected 40001 to 55P03 and explain why the second
attempt disappears; then trace lost acknowledgement after a real commit through
the unique reservation wait and stored reply without a second audit/outbox pair.

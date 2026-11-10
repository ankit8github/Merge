# Atomic composed team mutations — M-008D

M-012A exposes only create_team_idempotent through authenticated HTTP. The
composed services, transaction/retry/lock/audit/outbox contracts remain unchanged.
The owner verified 105 guarded HTTP cases in 140.81s at 0003_auth; Codex did not
rerun PostgreSQL. Current contract/evidence: [TEAM_API.md](TEAM_API.md). Earlier
no-HTTP statements retain milestone scope.

Checkpoint against `d8cf343a50cfaec4e83c47d318bfac79d10072ea`: owner verified
merge_test / merge_app, READ COMMITTED, **0003_auth (head)**. Composed mutations:
**81 passed in 101.23s**; service regressions: **57 passed in 59.59s**; idempotency
regressions: **60 passed in 40.81s**. Total **198 passed**, suite-time sum
**201.63s**, three repetitions requested for each suite. Fresh composed mutation
chains/committed-state invariants verified; fixtures retained. These are owner-run
PostgreSQL results, not Codex database runs. The earlier 202.63s combined figure
was an arithmetic error corrected by the owner, not an independent measurement.
Offline checkpoint evidence is in PROGRESS.md. No schema, migration, dependencies,
HTTP routes, dispatcher or retries at that checkpoint. G1, R-08 and R-12 remain open pending public
acceptance evidence; no production readiness is claimed.

M-008E adds bounded retry and ambiguous-COMMIT reconciliation. Owner verified
guarded merge_test / merge_app, READ COMMITTED, 0003_auth (head): retries 54 passed
in 48.66s, mutations 81 in 72.40s, services 57 in 36.15s and idempotency 60 in
42.84s; **252 passed**, suite-time sum **200.05s**. Three repetitions requested
for all suites; fresh committed invariants verified and fixtures retained. See
[TRANSACTION_RETRY.md](TRANSACTION_RETRY.md) for policy, classification and owner
commands. These are owner-run results; Codex did not execute PostgreSQL tests.
The M-008D checkpoint above remains historical evidence.

## Entry points and ownership

```python
service.create_team_idempotent(hackathon_id=h, actor_id=trusted_user, name=name, key=key)
service.join_team_idempotent(hackathon_id=h, team_id=t, actor_id=trusted_user, key=key)
```

Both return the existing frozen `_StoredReply` only after confirmed commit or
valid reconciliation from an immutable matching committed outcome.
The constructor still takes an Engine, never a caller Connection/Session. Actor
UUID validation is syntax validation, not authentication. A future HTTP boundary
must derive the actor from the authenticated session and authorize the action on
every request, including replay. Submitted actor IDs are never authentication.
No unauthenticated HTTP join, general request or invitation workflow is exposed.

The legacy create_team/join_team methods retain their exact signatures, validation,
UUID timing and TeamResult behavior. They remain trusted internal compatibility
facades without audit/version/outbox composition and must not back future HTTP
mutations. Guarantees below apply to the two composed methods. Mixing legacy/raw
mutations into an audited team's history is unsupported for public workflows.

The complete call graph is:

```text
TeamService.create_team_idempotent / join_team_idempotent
  -> private team_mutations facade: immutable input + _command validation/hash
  -> bounded _run_composed (same validated closure, at most three attempts)
  -> TeamService._execute (sole connection and transaction owner, each attempt)
     -> unchanged actual DBAPI AUTOCOMMIT / READ COMMITTED / driver guard
     -> one begin; lock/statement timeouts <=5s/15s and remaining deadline
     -> _reserve_in_tx (named unique conflict INSERT)
        -> matching immutable completed row: separate fresh SELECT -> stored reply
        -> new reservation:
           create: allocate outcome UUID -> _create_team_in_tx
           join: existing _join_team_in_tx
           -> _version_in_tx
           -> _audit_in_tx -> _outbox_in_tx
           -> bounded successful _StoredReply -> _complete_in_tx
     -> one COMMIT (including deferred constraints)
  -> owner fully unwinds before retry/reconciliation or returning a reply
  -> reply only after confirmed COMMIT or valid committed-row reconciliation
```

Private composition imports are local to the two TeamService wrappers to avoid
a module-load cycle with the existing fingerprint/command definitions. A new
frozen `_CreateTeamRequest` contains only meaningful inputs, so replay allocates
no team UUID. The fingerprint factory accepts it alongside the unchanged legacy
command type; canonical bytes/version remain identical. No supplied connection
helper opens/begins/commits/rolls back/closes a connection. No external work runs
inside the transaction and no event is published there.

## Locks, versions and failures

The order remains reservation -> hackathon SHARE -> affected user NO KEY UPDATE
-> existing team NO KEY UPDATE -> fresh count/membership -> version -> audit ->
outbox -> completed reply -> COMMIT. Create owns its new row without acquiring a
preexisting team lock. Join retains its existing parent lock until COMMIT; its
version UPDATE adds no new lock order. Supporting FKs take compatible KEY SHARE
locks on already-owned/referenced records. No user lock is acquired after a team
lock. One operation per transaction avoids cross-key reservation order ambiguity.

Create reads and requires the schema's initial version 1. Join updates version
exactly once and updated_at with database clock_timestamp(), returning the locked
leader/sizes/new version. A version already at signed-bigint maximum fails closed
as integrity_fault and rolls back the admission. Counts come from the original
fresh post-lock statements. Join changes exactly one membership and neither
leader nor sizes: therefore its before count/version are after minus one, while
the unchanged fields come from the retained locked row. No pre-lock state is used.

The unchanged domain and DBAPI error mapper governs failures. Malformed inputs
fail before connection acquisition. The immediate reservation actor/hackathon
FKs require existing identities; invalid/nonexistent UUID identities can yield
the existing integrity_fault mapping before the legacy domain existence lookup.
This internal boundary does not invent a public missing-entity HTTP error policy.
Team-full/already-assigned and mismatch failures roll back the reservation.

Exceptions before COMMIT and confirmed server rejections at deferred COMMIT
roll back every write in the chain, including a locally completed outcome.
There is no autonomous audit, outbox, completion or nested savepoint. M-008E
retries only observed 40P01/40001 after full unwind and within attempts/budget;
55P03/57014, business and work-phase connection failures are not retried.
Unknown COMMIT acknowledgement uses the same-key reservation protocol on a
fresh guarded connection, never absence inference. Unproven outcome returns
retryable outcome_uncertain. Raw writers, inverse lock order and future
multiple-subject operations still require review.

## Stored response, audit and outbox

Create returns status 201, join 200. Both store exactly:

```json
{"schema_version":1,"data":{"team_id":"uuid","hackathon_id":"uuid","user_id":"uuid","member_count":2,"team_version":2}}
```

The values are the actual mutation result and locked version, not replay-time
state. Headers are exactly `content-type: application/json` and
`cache-control: no-store`. All existing
M-008C size/depth/type/header bounds apply. No raw key, hash, cookie, CSRF, session,
token, display name or credential is included. Replay returns the stored status,
JSON body and safe headers without current-state regeneration, IDs or new effects.

One audit INSERT sets its server UUID, reservation FK, actor, hackathon/team IDs,
team_version, action (`team.create.v1` or `team.join.v1`), old_state/new_state.
occurred_at uses the database default. Create old_state is **SQL NULL**; otherwise
both snapshots use this bounded format:

```json
{"schema_version":1,"team":{"version":2,"member_count":2,"leader_user_id":"uuid","min_team_size":2,"max_team_size":3,"readiness":"ready"},"subject":{"user_id":"uuid","member":true}}
```

Join old_state records the preceding count/version, subject member=false and the
corresponding derived readiness. Create new_state records founder count/version 1,
leader=subject and member=true. This is a bounded summary, not a full roster or
profile snapshot. IDs/scope/action in the actual audit columns identify the
operation and affected team; subject identifies the affected membership.

One outbox INSERT references that audit UUID and sets event_type=`team.changed.v1`,
schema_version=1, published_at=SQL NULL and attempt_count=0. occurred_at uses the
database default. Payload contains **only**:

```json
{"hackathon_id":"uuid","team_id":"uuid","team_version":2}
```

This is an invalidation hint. No actor/subject, roster, count, audit snapshot,
secret or idempotency material is published in it. Database uniqueness gives at
most one audit per reservation/team-version and at most one outbox per audit;
the composed path supplies the corresponding exactly-one guarantee for successes.
Existing schema constraints do not automatically audit legacy or arbitrary SQL.

## Verification and owner run

New `--suite mutations` selects only `team_mutation_tests` and requires explicit
0003_auth before credentials. Every fixture/service/worker/observer connection
checks fixed merge_test identity, revision and READ COMMITTED. Collection opens
no database; direct unguarded execution fails before writes. UUID fixtures are
retained. Fresh independent reads check original team invariants plus completed
record chains, audit subject/scope/state/version, safe outbox payload/unpublished
state, sequential versions and current membership counts. No cleanup DML.

Fault tests raise an exact test-only exception after successful reservation,
founder/member, version, audit, outbox and completion SQL. They compare all five
affected tables on fresh connections before/after and retry explicitly only after
removing injection to prove the key/membership were released. This test action is
not a production retry framework. Actual deferred-COMMIT tests corrupt the leader
to a scoped nonmember after completion and require exact 23503 /
fk_teams_leader_member, zero returned reply and full rollback. No constraints are
disabled. Matching concurrent calls require different backend PIDs and observed
server blocking. While the first completed chain is held before COMMIT, another
connection must see the old full snapshot, including no new outbox, and neither
call may have returned. Capacity and same-user/different-key races accept only
one success and the exact intended rejection, never a timeout/database failure.

Event/queue/barrier waits are bounded (8s), lock observation 3s, worker join 30s,
server connect/lock 5s and statement 15s. Busy-host timing failures are failures;
do not blindly restart after an unfinished worker deadline. The successful owner
run above used this guarded workflow; retain these commands for reproduction
in PowerShell without a transcript:

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Database verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite mutations --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'M-008D mutations failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite services --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Service regressions failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite idempotency --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Idempotency regressions failed. Stop.' }
```

These commands verify/test only, never migrate/reset. Password prompts are hidden.
No public 50-way API, CI, load, deployment, browser/HTTPS or G1 proof is supplied.
Owner exercise: trace failure after outbox insertion through rollback; explain
why replay must preserve its original count/version after another caller joins.

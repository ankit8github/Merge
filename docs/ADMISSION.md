# Leader-approved admission - M-013A

M-014B adds a separate recipient-bound invitation workflow and exact-0005 guarded
race harness: [INVITATIONS.md](INVITATIONS.md). It uses the same
already-locked admission helper and transaction owner. The request API, original
0004 suite and its revision guards remain unchanged. The owner now reports 0005
already applied; the R2 audit of the successful three-repetition invitation run
closes original Phase 1 G1 within local PostgreSQL scope. Exact evidence and
limitations: [G1_ACCEPTANCE.md](G1_ACCEPTANCE.md). No legacy 0004-suite compatibility
at 0005 or new Codex database action; do not rerun migration or live tests.

At M-014A, source review confirmed a blocker for literal distinct-caller G1: request
creation reserves no seat, while only one current leader can make capacity-changing
decisions for a team. Fifty requesters and fifty approvals by that leader are
different concurrency scenarios. [G1_ACCEPTANCE.md](G1_ACCEPTANCE.md) records the
proof and acceptance rationale. That checkpoint added no race suite or authority
bypass; M-014B implements the separately authorized prerequisite. The historical
G1-open statements below precede the R2 evidence audit.

M-013B now implements the React request/status and current-leader decision flow
for offline owner review. It calls only the documented endpoints below, preserves
original keys/decisions under uncertainty and refetches canonical state. Backend
contracts, transactions, schema and browser-host restrictions are unchanged.
[FRONTEND.md](FRONTEND.md) records the component map and reload/browser recovery
limits; PROGRESS.md records actual tests. The M-013A checkpoint's no-UI wording
below describes that earlier backend-only snapshot, not the current frontend.

## Final checkpoint - owner live acceptance, 2026-11-11

The owner verified merge_test at **0004_admission** and completed two successful
guarded admission runs: one repetition / 35 cases and two repetitions / 70 cases,
both exit 0 with suite_and_fixture_checks_completed. Total: **105 admission test
executions across three repetitions in two processes**, not one three-repetition
run. Local metadata reports match these results; exact IDs and final offline
checks are in PROGRESS.md. These are owner executions, not Codex PostgreSQL runs.

**0004_admission is already applied to merge_test. Do not rerun migration SQL,
ordinary Alembic, provisioning, downgrade, cleanup or reset manually.** The
preparation commands below are historical, not instructions for this database.
No database action is authorized by this checkpoint. The migration adds retained
request storage/guards without rewriting existing data; the guarded migration
runner compares legacy domain/auth fingerprints in its owned DDL transaction.
No new data-preservation measurements or independent drift inspection are claimed.

The tested 50-candidate approval race uses one current leader's authenticated
decision session. It does not prove the official 50-distinct-authenticated-caller
race: **G1 remains open**. No frontend admission UI, unrestricted public join,
browser/HTTPS acceptance, CI/load or deployment evidence is added. Legacy auth
suites and browser host still require 0003; schema/services are not certified at
0004 despite accepting that explicit CLI flag. The exact matrix below is retained.

The R1/R3/R5 and preparation sections below preserve their original checkpoint
history; their pending-live statements are superseded only within this acceptance
scope. Earlier failed/interrupted reports remain unsuccessful evidence.

R3 adds metadata-only diagnostics to the existing guarded runner; retrieval and
precise completion/exit semantics are in [TEST_DATABASE.md](TEST_DATABASE.md).
At R3, the owner's earlier 90-pass/one-failure run remained unidentified and the
live revision was unknown. R5 now has an owner-reported verified 0004_admission
target and the specific local failed-run report reviewed below; this does not
retroactively identify the older run. The migration/test sequence below is a proposed
separately approved procedure, not evidence that migration occurred or approval
to run it now. Do not repeat migration/tests to recover existing failure output.
Future runner reports preserve sanitized node/phase/category without raw errors;
they do not replace fresh fixture invariants or establish G1 acceptance.

## M-013A-R5 - approval COMMIT fault placement, 2026-11-11

The owner reports merge_test verified at 0004_admission. The existing local report
`test-results/guarded/run-a582e8235c9c4f1d82e6207dd8594893.json` (under backend)
records admission / three repetitions, 105 collected, 91 teardowns completed,
one call/assertion failure at
`test_real_failure_rolls_back_or_reconciles_same_key[0-ambiguous-commit]`, exit 1
and invariants not_certified. It contains no assertion line or response values.
No PostgreSQL inspection or successful live rerun is claimed here.

Offline reproduction of the exact test body fails at the original line 298:
`if response.status_code==503: assert response.json()['error']['code']=='outcome_uncertain'`.
The engine-wide commit hook was armed before the HTTP decision. Real session
validation owns and commits a READ ONLY transaction on that same Engine before
approval; CSRF verification owns another. The first commit therefore physically
committed an authentication read and raised a synthetic lost acknowledgement.
The unchanged auth boundary correctly returned 503 service_unavailable, and
approval/reservation/reconciliation had not started. This deterministic fixture
defect demonstrates the supplied failure mechanism; metadata alone cannot prove
which assertion fired in the historical live process or exclude further defects.

The test now arms only after a successful UPDATE of its exact request UUID and
matches that SQLAlchemy Connection AND root transaction at COMMIT. That callback
still physically commits once before raising acknowledgement loss. It must fire;
all original assertions remain. Extra checks require a committed approved request,
one decision idempotency record, an exact approved same-key replay (including
initial response equality when reconciliation succeeds), and an unchanged fresh
scoped snapshot after replay. Existing final fixture invariants and retained rows
remain mandatory. No production/auth/retry/API/schema/permission change.

The 0004 replay path reserves the same key, loads the immutable stored response,
locks/checks current leader and exact request, and only then notes replay proof.
It returns that proof before applying the pending-only rule for NEW decisions;
the now-approved request is not a reason to regenerate a response or reject a
matching replay. Unavailable reconciliation remains retryable outcome_uncertain;
the caller must retry the SAME key and scope/body. Authentication failures remain
service_unavailable. No contract change or timing-based retry is justified.

`tests/test_admission_commit_fault.py` runs real HTTP/auth/session/credential
owners and admission/reconciliation code over the existing in-memory SQL double.
Physical Engine connection creation fails immediately. Simulated SQLAlchemy events
reproduce the old auth failure, exercise available/unavailable reconciliation,
require one admission chain/exact replay, and reject a nominal success if the
targeted fault never fired. These are control-flow checks, not PostgreSQL DDL,
driver/network, concurrency or deferred-COMMIT evidence. Full commands/results
are recorded in PROGRESS.md.

For separate owner approval only, the existing guarded validation command is:

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite admission --revision 0004_admission --repetitions 1
if ($LASTEXITCODE -ne 0) { throw 'Admission validation failed. Stop; retain fixtures and the printed report.' }
```

This fixed suite has no supported single-node selector: one repetition runs 35
cases, including the corrected fault case, with ordinary guarded preflight,
retained fixture writes and fresh committed invariants. It is not a read-only
inspection. No migration/reset/cleanup is included or authorized here. Require
matching terminal exit 0 and completed fixture verification; preserve the exact
printed report ID. A successful one-repetition run still leaves three-repetition
validation for separate review. No raw errors/headers/SQL/private values should
be enabled. Stop for owner review before any live action or commit.

Owner exercise: explain why accepting service_unavailable in the old assertion
would hide the misplaced fault, and why an approved request still permits the
original authorized same-key stored replay without a second membership/chain.

## Design recorded before implementation

Owner scope authorizes an additive request migration and the minimal internal
admission refactor. Proposed decision: retain one request per (team, requester),
including terminal history. No resubmission after rejection in this milestone.
Pending requests reserve no seats. A requester can request multiple teams while
unassigned; the membership PK remains authoritative at approval.

The additive 0004_admission migration adds join_requests with immutable UUID,
team/hackathon/requester, pending/approved/rejected state and database timestamps,
terminal decision actor. Composite team/hackathon FK, user FKs, unique team/user,
state/timestamp checks, identity/terminal/delete/truncate guards preserve history.
No existing rows, constraints, role grants or schema objects are replaced.

Transaction plan: reuse TeamService._execute and _run_composed (including actual
DBAPI AUTOCOMMIT/READ COMMITTED guards, timeouts, bounded conflict retries and
ambiguous-COMMIT same-key reconciliation). Reserve idempotency first, then lock
hackathon SHARE, affected user rows NO KEY UPDATE in UUID order, target team
NO KEY UPDATE, request NO KEY UPDATE. A nonlocking lookup supplies immutable
requester identity before locks; re-read the exact scoped request under lock.
Never take a new user lock after the team lock. Current leader and request scope
are checked before a replay can disclose its stored result.

Extract only the membership eligibility/count/insert portion of legacy join to
a private already-locked helper. Both old join and approval call that helper;
neither calls a committing service from inside another transaction. Approval
inserts membership, resolves the request, increments team version, writes one
audit/outbox chain and completes the stored result in that same owned transaction.
Creation/rejection also increment version and record request-state audit/outbox.
Duplicate request with a different key returns the existing request without a
second state transition/audit; its own completed idempotency record is retained.
Different-key decisions on a terminal request conflict, even if identical.
Same-key replay returns the original stored success after current authorization.
Failure rolls back all effects; full/assigned approval leaves pending unchanged.

Per-user locks serialize competing team assignments; the team lock serializes
capacity checks and decisions against leadership replacement. Auxiliary request
locks follow team locks. A future leadership writer must follow this protocol.
The existing internal trusted join remains internal and is never routed publicly.

HTTP contract (all under /api/hackathons/{hackathon_id}/teams/{team_id}):

- POST /join-requests, JSON {}, Idempotency-Key: create own request (201), or
  return existing own request (200). Current cookie actor only.
- GET /join-requests/mine: own request or null; no other account status selector.
- GET /join-requests?limit=20&cursor=<request UUID>: current leader only, pending
  requests in UUID order; 1-100 page bound, cursor scoped to this team/hackathon.
- POST /join-requests/{request_id}/decision, JSON {decision:"approve"|"reject"},
  Idempotency-Key: current leader only, stored 200 success.

Mutations reuse creation_session/idempotency_key and strict JSON extra-forbid
models. GETs use authenticated_session and reject unrecognized query/identity
headers. All existing Origin/Fetch Metadata/peer/HTTPS/no-store protections apply.
No actor/requester/leader IDs are accepted in bodies. Request DTO contains only
id, hackathon_id, team_id, requester_id, status, created_at, resolved_at; decision
actor and audit/private credential fields are not exposed. Mutation replies use
{schema_version:1,data:<request DTO>}; GET mine uses {request:DTO|null}, list uses
{items:DTO[],next_cursor:UUID|null}. No synthetic membership DTO.

403 forbidden for leader authorization; 404 request_not_found/team_not_found;
409 request_resolved/already_assigned/team_full/idempotency_mismatch. Other errors
use existing sanitized 401/403/415/422/503 contracts. Unknown COMMIT is explicitly
outcome_uncertain: retry the SAME key and exact scope/body. No automatic route retry.

Offline doubles cannot establish PostgreSQL races, DDL enforcement or G1. Live
validation requires separate owner migration/test approval against merge_test,
merge_app and explicit 0004_admission. No React, browser-host expansion, unrestricted
join, invite, departure, leadership-transfer, removal or deletion endpoint.

## Implementation and exact wire types

The design above is implemented with owner live acceptance within the final
checkpoint scope above. The migration additionally
has a deferred ct_request_admitted check: an approved transition must have the
exact scoped membership at commit. It checks resolution-time admission, not an
eternal membership requirement after future departure. The old membership
PK/composite FK/capacity and leader constraints are unchanged. Request SQL uses
only parameterized values; all table references are public-qualified.

```typescript
type JoinRequest = {
  id: string; hackathon_id: string; team_id: string; requester_id: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string; resolved_at: string | null; // timezone-aware ISO timestamps
};
type RequestReply = {schema_version: 1; data: JoinRequest};
type OwnRequest = {request: JoinRequest | null};
type PendingPage = {items: JoinRequest[]; next_cursor: string | null};
type DecisionBody = {decision: 'approve' | 'reject'};
type Failure = {error: {code: string; message: string; retryable: boolean}};
```

All identifiers are UUIDs. Requests contain no message, client subject, actor,
scope override or additional fields. The mutation's stored status/body/allowlisted
headers replay exactly; an original creation reply may still say pending after
a later decision, so use GET mine for current status. A new-key duplicate returns
the current retained request (200) and no second transition. Pagination orders
UUIDs ascending, has no stable cross-page snapshot, and accepts a cursor only
from the same team's retained request history (including now-terminal rows).
GET authorization is snapshot/point-in-time; mutation authorization holds locks
through commit. Revocation cannot undo already authenticated in-flight work.

New actual request transitions increment team version once, including creation
and rejection; pending requests do not alter membership counts or reserve seats.
Audit actor is the requester for creation and the leader for decisions; subject
is the requester. Before/after states add request id/status to the existing
team/subject snapshots. Outbox remains team.changed.v1 with only hackathon/team/
version identifiers; it exposes no request data. New-key duplicate idempotency
records intentionally have no new audit/outbox because no state changed.

The only join refactor is the already-locked membership helper. _execute,
transaction_retry, existing team fingerprints, creation HTTP behavior, production
authentication, read APIs, dependencies, privileges and older migrations are
unchanged. AdmissionError has a separate HTTP mapping. Missing hackathon during
reservation can still be sanitized 503, like existing create; do not infer absence
or successful rollback from transport failure. Original session/cookie/Origin/
CSRF/no-store protection is applied to every request/replay.

## Historical migration preparation - do not rerun on merge_test

**0004 is already applied; do not run this historical sequence on merge_test.**
Codex prepared these commands without executing them; the owner subsequently
reported the applied revision and acceptance above. For a future separate fresh
target, first obtain specific owner approval for the additive
0004 DDL, migration preservation scan/locks, retained fixture writes and fault
injections described below. Stop all fixture/browser writers during migration;
the migration takes SHARE locks on existing domain and auth tables and compares
aggregate row fingerprints before/after in the same DDL transaction. Do not run
ordinary alembic upgrade/head, app.serve, the browser host, provisioning or reset
commands. No downgrade/cleanup or trigger disabling is supported.

Use an owner PowerShell terminal without transcripts; existing merge_app password
is entered only at the hidden prompt. No password, cookie or key in args/URLs.

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
# Only after separate owner approval for read-only target inspection:
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Expected pre-migration merge_test / 0003_auth. Stop.' }
# Only after separate owner approval for migration and preservation scans:
.\.venv\Scripts\python.exe -m test_support.database migrate --confirm-merge-test --revision 0004_admission
if ($LASTEXITCODE -ne 0) { throw 'Admission migration failed. Stop; no repair/reset.' }
.\.venv\Scripts\python.exe -m test_support.database migrate --confirm-merge-test --revision 0004_admission
if ($LASTEXITCODE -ne 0) { throw 'Repeat migration check failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0004_admission
if ($LASTEXITCODE -ne 0) { throw 'Post-migration identity/revision verification failed. Stop.' }
# Only after separate owner approval for retained fixtures and race/fault tests:
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite admission --revision 0004_admission --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Admission tests/invariants failed. Stop; do not clean fixtures.' }
```

Every command opens PostgreSQL connections, confined by TestDatabaseSettings and
actual merge_test / merge_app / 127.0.0.1:5432 checks. The admission fixtures check
actual DBAPI AUTOCOMMIT false, READ COMMITTED, 5s/15s timeouts and exact revision
on every new/pooled connection. No default environment can choose another target.
Auth-dependent legacy suites and the browser host still require 0003_auth and
refuse 0004. The older schema/services suites are exceptions: their default 0002
preflight refuses 0004, but their CLI currently accepts an explicit 0004 flag;
their fixtures do not check that revision on every connection. Do not treat that
as reviewed post-upgrade compatibility. Run separately approved compatible legacy
regressions before migration, and only the admission suite afterward for now.
Porting the legacy fixtures to an exact explicit expected-revision guard is
separate review work; no backwards migration or broad revision bypass is allowed.
Offline regressions cover the old APIs. The R1 compatibility matrix below is exact.

Exact potential test writes: unique retained hackathons/users; Argon2 credentials;
sessions (including a deliberately expired fixture and scoped revocation);
teams/founder memberships; pending requests/approved or rejected terminal states;
admitted memberships; team versions/timestamps; idempotency, audit and outbox rows.
The stale-leader fixture additionally admits a replacement member then changes
only its own scoped team's leader under locks. Failure cases issue invalid scoped
INSERT/UPDATE operations that must roll back; one deferred-commit case deletes
only the newly uncommitted fixture membership to force rejection and rollback.
No committed cleanup/delete, fixture reset or physical team deletion occurs.
Ambiguous-COMMIT injection commits once, loses acknowledgement and checks same-key
reconciliation. Session/account creation happens through existing real services;
their secrets are generated privately and never printed. SQL/logging/exception
locals/private response dumps are excluded by the guarded runner.

Each case verifies fresh independently guarded committed membership/capacity/FK,
request status, complete idempotency, request audit transition and outbox chains.
An invariant or test failure produces a nonzero launcher exit. The owner-accepted
final-seat case queues 50 authenticated leader decisions for 50 independently
authenticated candidate requests. This remains single-leader decision evidence,
not the distinct-caller G1 requirement. No CI, browser, deployment or performance
acceptance is claimed.

## Remaining limits

No cancel/expiration/re-request after terminal rejection; terminal history is
retained. No new request-specific rate limiter. Auth throttling remains unchanged.
Unsupported raw/privileged writers can bypass service authorization; database
constraints protect membership/capacity/structural state, not authenticated HTTP
identity. Future membership/leadership writers must use the same lock order.
Offline tests cannot establish PostgreSQL behavior. The owner completed the live
admission cases described above; no independent DDL reflection/Alembic drift,
distinct-caller race, browser, CI/load or deployment verification is claimed.
G1 remains open. No frontend admission control was enabled.

Owner exercise: trace a leader decision from cookie/CSRF to the sorted user locks,
team/request locks and shared admission helper. Explain why a full-team rejection
leaves the request pending, and why replay proof must follow authorization.

## M-013A-R1 - migration and concurrency readiness review

**Offline review only; no live approval inferred.** One blocking defect was
reproduced and corrected: RequestPage inherited strict input-body configuration,
but pending_requests returns a string UUID cursor. A non-null next_cursor caused
response validation to return sanitized 503. Only that output model now uses
the existing extra-forbid, UUID-validating output configuration. Empty/decision
input models, pagination bounds, authentication and transactions are unchanged.
The new exact HTTP cursor regression failed before the fix and passes afterward.

Race evidence previously checked one HTTP 200, other 409/team_full responses and
two roster members, without explicitly tying every loser to pending state or
checking exact committed version/record counts. The strengthened fresh observer
now requires the winning request approved, all losing requests pending with null
resolution fields, founder plus winner only, version N+2, and exactly N+2 completed
idempotency/audit/outbox records (founder + N request creations + one decision).
Audit versions must be contiguous and records/outbox linked; admission audit
states/counts/subject must match the winner. Snapshot equality now includes scoped
outbox rows for failure/replay cases. Seven negative offline oracle corruptions
ensure these assertions fail closed; doubles are not PostgreSQL race evidence.

### Every migration operation and retained-data behavior

1. On online upgrade, inspect the exact table/type and two function signatures;
   refuse collisions before issuing DDL. No IF NOT EXISTS adoption or replacement.
2. CREATE TABLE public.join_requests and its composite FK, user FKs, PK, unique
   constraint and checks. The table starts empty even on populated 0003_auth.
   Existing rows are neither copied nor rewritten. PK/unique create their backing
   indexes; the FK creates ordinary enforcement catalog objects on its references.
3. CREATE the pending (team_id,id) partial index, matching the bounded list query.
4. CREATE two VOLATILE SECURITY INVOKER trigger functions with fixed search_path
   and public-qualified references. Neither replaces a prior function.
5. CREATE the row identity/initial/terminal/retention guard, statement TRUNCATE
   guard and deferred approved-membership constraint trigger, all on the new table.
6. Alembic changes only its version row from 0003_auth to 0004_admission. The
   dedicated runner owns one PostgreSQL DDL transaction, including before/after
   fingerprints of all seven existing domain and three auth tables. Installed
   Alembic source confirms its nested begin_transaction respects the externally
   owned transaction. Failure rolls back DDL/version update; commit acknowledgement
   loss remains operationally ambiguous and requires separately approved verify,
   not cleanup/adoption. A repeat at 0004 runs no migration DDL.

Model/DDL agree: non-null identity/scope/user/status/created_at; one request ever
per (team,requester); exact team/hackathon FK; pending has no resolution fields;
terminal status is approved/rejected with decider/time; timestamps finite and
ordered. Immediate constraints and guards reject invalid initial/identity/state
writes. Deferred ct_request_admitted checks the exact membership at resolution
commit. It intentionally does not require membership forever after future leave.
Current-leader authorization is a service guarantee under locks, not a SQL
constraint establishing HTTP identity. No changes to old membership/capacity FKs
or triggers. No destructive migration statement/backfill exists.

Downgrade always raises before DDL. **There is no supported downgrade.** A future
DROP TABLE would destroy retained request history and cannot be called safe just
because older membership data survives. It needs a separately reviewed retention
plan and explicit owner approval; never downgrade/reset to make old suites pass.

### Migration role and lock requirements

Use the existing non-administrative merge_app, never postgres or merge_dev. It
needs CONNECT, public schema USAGE/CREATE, SELECT on the ten preservation tables,
sufficient privileges for SHARE locks on those tables, REFERENCES on teams
(id,hackathon_id) and users(id), language plpgsql/type USAGE, and Alembic-version
SELECT/UPDATE. As creator it owns the new table/functions and can create their
indexes/triggers (TRIGGER/EXECUTE required). Existing ownership of the migrated
objects is sufficient for these object permissions; no new grants/roles are part
of this task. The implemented preflight checks identity, isolation, CONNECT,
schema USAGE/CREATE and revision; it does not prove every object/language privilege.
A missing permission must fail the migration transaction, never trigger a grant
or automatic repair. PostgreSQL 17 references:
[CREATE TABLE](https://www.postgresql.org/docs/17/sql-createtable.html),
[LOCK](https://www.postgresql.org/docs/17/sql-lock.html),
[CREATE FUNCTION](https://www.postgresql.org/docs/17/sql-createfunction.html),
[CREATE TRIGGER](https://www.postgresql.org/docs/17/sql-createtrigger.html).

Preservation locks are SHARE on all ten legacy tables until transaction end,
blocking ordinary writers while allowing plain reads. FK creation additionally
takes SHARE ROW EXCLUSIVE on referenced teams/users. New table/index/trigger DDL
locks its new objects, and the Alembic version update locks its row. Fingerprinting
scans nonempty retained tables (auth rows only as server-side aggregate hashes,
never private values in output). This is a maintenance window, not online/no-lock
DDL. Stop application/test/browser writers and run one migration at a time.
Existing 5s lock/15s statement limits can cause safe rollback; runtime and exact
server DDL behavior are unverified until the approved run.

### Lock/concurrency conclusions

Request create/reject/approve: reservation first, immutable requester lookup for
decisions only, hackathon SHARE, sorted distinct actor/requester users NO KEY
UPDATE, exact live team NO KEY UPDATE, scoped request NO KEY UPDATE. Create then
requires unassigned subject; duplicate returns retained own request without a
transition. Decision checks current leader before request state/replay proof.
Approval's shared helper rechecks assignment and counts fresh after the team
lock, then inserts; resolution and chain are completed before the owner's commit.
Capacity/assignment failures unwind the reservation and leave pending unchanged.

Team create uses reservation (composed only), hackathon SHARE, actor NO KEY UPDATE
and owned new team/founder inserts. Legacy join uses hackathon SHARE, actor NO KEY
UPDATE, team NO KEY UPDATE and the identical extracted fresh check/count/insert
tail; composed join adds reservation/chain/retry. All existing _execute/guard/
retry methods are unchanged. FK KEY SHARE locks are compatible with NO KEY UPDATE.

Same request/same key waits on reservation then replays only after current leader
authorization. Distinct keys serialize under users/team/request; a terminal loser
gets request_resolved and no second chain. Distinct candidates serialize on the
leader/team and re-count, leaving full-team losers pending. Cross-team admissions
share the requester user lock; only the first can insert, the second observes
already_assigned. Membership PK/capacity/FK constraints remain the final authority.
Future leader/member writers must follow this order. Bounded deadlock retry is
recovery, not a claim that privileged/inverse-order writers cannot deadlock.

The 50-candidate case registers/logs in 50 candidates and creates each request
through HTTP with its own cookie/CSRF, then barrier-starts 50 TestClient HTTP POST
decisions with the current leader cookie/CSRF and distinct keys. Real session and
admission services use guarded PostgreSQL. It is not a direct-service approval
approximation. It is in-process ASGI (no listener/browser), and all decisions use
one authorized leader account. Therefore it is NOT the official 50 distinct
authenticated admission callers scenario or completed G1 evidence. Worker pool/
server thread limits may queue calls after the barrier; no exact simultaneous
lock overlap or performance is claimed. Worker/invariant failure is nonzero;
timeout cannot prove daemon/database work stopped, and no successful suite result
can be reported after timeout. No fixtures are cleaned afterward.

### Exact compatibility matrix and next approval

| Runner/suite | Behavior at actual 0004_admission |
| --- | --- |
| database verify/migrate with explicit 0004 | Exact verify / no-op repeat migration supported |
| database default or explicit 0002/0003 | Refuses actual 0004; downgrade/adoption blocked |
| admission + explicit 0004 | Fixed new suite; per-connection exact revision/identity/settings guard |
| auth, credentials, sessions, auth-api, throttles, idempotency, mutations, retries, reads, team-api | --revision 0004 rejected before credentials; --revision 0003 fails actual-DB preflight |
| schema, services | Default 0002 fails preflight; explicit 0004 is accepted by CLI, but fixtures lack per-connection revision checks and are not certified for this milestone |
| browser inspect/serve/verify | CLI supports only 0003, and its guard refuses actual 0004; admission/team routes remain excluded |

Compatibility plan: keep all guards/defaults unchanged. If desired, separately
approve and run auth-dependent regressions at 0003 BEFORE migration. After the
approved migration run only the reviewed admission suite at exact 0004. A future
bounded port should carry an explicit expected revision into every fixture and
every pooled/new connection/observer; retain legacy defaults and test rejection
of wrong/missing/multiple revisions before credentials or writes. Do not use a
global either-revision allowlist, `head`, skipped guards, Settings fallback or
downgrade as a workaround. Schema/services also need that port before recommending
them as guarded post-upgrade regressions. No compatibility port was performed.

The PowerShell sequence above remains the implemented supported procedure;
separate owner approval is still required for its read-only preflight, DDL/scan
locks and retained fixture/fault writes. No new approval manifest or credential
file is generated. R1 does not expand the listed potential writes. Full tests,
static evidence, changed-file inventory and Git status are in PROGRESS.md.

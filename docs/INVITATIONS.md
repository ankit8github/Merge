# M-014B - recipient-bound invitations

Owner-scoped design recorded before implementation, 2026-11-11. Additive revision
**0005_invitations is already applied to merge_test**, according to the owner.
M-014B-R2 audited the existing successful invitation report: 39 total cases at
three repetitions, exit 0, completed suite/fixture checks. Original Phase 1 G1 is
closed within that owner-run local guarded PostgreSQL scope; production HTTPS,
browser, CI and load acceptance remain open. Evidence, exact node/assertions and
count/provenance limits: [G1_ACCEPTANCE.md](G1_ACCEPTANCE.md).
**Do not rerun migrations or live tests.** R2 is local evidence/offline review only.
R1's no-live/open statements below describe that earlier readiness checkpoint.

## Contract

All routes use the established authenticated cookie/browser/Origin/HTTPS/no-store
boundary. Mutations additionally use current CSRF, strict JSON and one existing
Idempotency-Key. Actor identity always comes from the session. recipient_id is
the intended subject, never an actor override.

- POST /api/hackathons/{h}/teams/{t}/invitations, exactly {recipient_id:UUID}:
  current leader issues a recipient-bound, fixed 24-hour invitation; stored 201.
- GET /api/hackathons/{h}/invitations/mine?limit=20&cursor=UUID: only the current
  recipient's invitations, bounded 1-100, ascending UUID; cursor must belong to
  this recipient/hackathon. {items:[DTO plus available:boolean],next_cursor:UUID|null}.
- POST /api/hackathons/{h}/teams/{t}/invitations/{id}/redeem, exactly {}:
  intended recipient only; stored 200 after membership commits/reconciles.

DTO: id, hackathon_id, team_id, recipient_id, issued_by, status (pending/redeemed),
created_at, expires_at, redeemed_at. Mutation envelope {schema_version:1,data:DTO}.
No transferable bearer code or client actor field. UUID4 supplies 122 random bits;
the ID is an inbox reference, not a secret or authority. Authentication, recipient
binding and current durable grant are required even if someone knows the ID.
No email, token-delivery channel, invitation UI or public self-join is added.
Each distinct issue command creates a separate grant; replay creates none.

Invitations reserve no capacity. Issuance requires an existing recipient. A grant
is stale when the team leader differs from issued_by; leadership changes do not
transfer grants. Expiration uses database clock_timestamp after locks. GET reports
availability without consuming or changing expired/stale rows. Redemption checks
recipient, issuer/current leader and expiry BEFORE noting stored replay proof.
A still-authorized same-key redeemed replay returns the original result without
testing unassigned/capacity again. After expiry or leader replacement even that
replay is denied; a canonical read is needed to distinguish historical membership.
Availability describes the grant, not a reserved seat or guaranteed membership.
The expiry sample taken under locks is also redeemed_at, avoiding a second clock
sample crossing the deadline after a valid decision. Expiry is checked at that
decision point, not redefined as a requirement that COMMIT finish before expiry.
Issuance replay still requires the current leader but returns its historical
acknowledgement even after expiry; only redemption needs a currently valid grant.
Leadership invalidation uses current equality, not a durable revocation marker:
if the original issuer becomes leader again before expiry, a pending grant is
usable again and an already-redeemed matching-key reply is accessible again.
No transfer route or permanent-revocation generation is implemented. A new
same-key call after expiry returns 409 invitation_expired without changing prior
membership or the stored success. If expiry prevents proof during an already
ambiguous COMMIT's reconciliation, that call remains 503 outcome_uncertain;
neither error establishes rollback of the earlier attempt.

403 forbidden: issuance by nonleader; 404 invitation_not_found: missing/wrong
scope/wrong recipient, without disclosing another recipient's grant. 409:
invitation_expired, invitation_stale, invitation_redeemed, already_assigned,
team_full, idempotency_mismatch. Unknown COMMIT: retryable outcome_uncertain,
same key/scope/body only. Existing sanitized auth/validation/503 policy remains.
Authenticated issuance/redemption charge separate durable per-account buckets,
60 attempts per existing configured throttle window (default 300 seconds),
including retries. Rejected admission rolls back domain effects, not the separate
attempt charge. No auth throttle policy or scope is repurposed.

## Ownership and lock proof

Reuse TeamService._execute and _run_composed; no route-owned/nested transactions.
Reserve idempotency first. Issue: hackathon SHARE -> sorted unique issuer and
recipient user NO KEY UPDATE -> team NO KEY UPDATE -> insert invitation.
Redeem: nonlocking immutable identity lookup -> hackathon SHARE -> recipient user
NO KEY UPDATE -> team NO KEY UPDATE -> exact invitation NO KEY UPDATE. Recheck
scope/recipient after lock, then current issuer/expiry. The issuer is not a
membership subject during redemption and needs no additional user lock; its
authority is protected by the team lock. Never acquire a user lock after a team.

Creation locks founder before a new owned team; trusted joining locks its subject
before team; requests lock their actor before team; leader decisions lock sorted
leader/requester before team then request. Invitations follow the same partial
order. No invitation code calls a committing join facade. Authorized redemption
calls only the shared already-locked membership helper. Membership, redeemed
state, one version increment, audit/outbox and stored response commit together.
Issue also advances version with one audit/outbox chain. Failure, including full
capacity and membership conflict, leaves the grant pending and rolls back the
reservation/chain. Matching replay rechecks current authority before proof.

DDL adds retained invitations with composite team/hackathon FK, recipient/issuer
FKs, finite ordered expiry/state timestamps, immutable identity, terminal/retention
guards and deferred redeemed-membership validation. It replaces no old object or
privilege. Guarded migration must preserve all eleven prior domain/auth/request
tables in its existing owned DDL transaction; no downgrade/adoption/repair.

## Guarded acceptance design

New fixed invitations suite requires explicit 0005 before credentials and on every
worker/observer connection. Existing admission directory/0004 guards are unchanged.
Legacy auth-dependent suites/browser stay 0003; schema/services keep their old
limits and are not certified at 0005. Browser host must exclude invitation routes.

For each fresh retained race fixture, 50 distinct real accounts/sessions/CSRF and
50 leader-issued grants target one team with a founder and one free seat. A
test-only wrapper gates all 50 real authenticated redemption arrivals before
transactions; it neither substitutes principals nor changes domain behavior.
The test host raises only its own sync-thread capacity to 64 to avoid a 40-thread
barrier deadlock. The ordinary connection pool may queue transactions. A guarded
observer holds only the team lock, then releases the gate and requires at least
two distinct redemption callers observed in a blocking chain rooted at that observer
before releasing the team. Bounded events/observations, not sleep-based success.
PID registration requires an active authenticated caller tag and exact team/
hackathon binds on the actual team-lock statement. Only same-role/current-database
lock waiters from that registry count; unrelated candidate cycles, external PIDs
and duplicate actors cannot supply proof. Tags/registry entries are removed using
the original mapping on exit, including when a connection is invalidated.
This proves 50 overlapping authenticated calls and observed database contention,
not 50 simultaneous database transactions. Timeout/missing caller/unknown outcome
fails the run; daemon timeouts are not proof workers stopped.

Expect exactly one 200, 49 409 team_full, one new membership, 49 pending grants,
one redeemed grant; no partial loser reservations/audit/outbox. Verify all scoped
membership uniqueness/capacity, exact version and linked audit/outbox and stored
reply, then unchanged canonical snapshot after exact winner replay. Repeat with
fresh retained fixtures; no cleanup. Negative recipient/stale/expiry/CSRF cases and
cross-team contention remain separate. Offline mocks and collection never close G1.

## M-014B-R1 readiness findings

The migration and production services are unchanged in R1. The offline review
reproduced and repaired a test-only false-positive overlap case: the earlier
intersection query could count candidate blocking unrelated to the observer.
The rooted graph and target-bound active registry above replace that check.
The oracle now also verifies every grant/issue actor, exact scope, stored reply
identity, audit/outcome linkage and outbox destination. Setup checks match each
of the 50 issued grants to its actual intended authenticated contender. Counts
alone are insufficient. No assertion was removed or relaxed.

Expiry coverage now requires the exact error and unchanged committed chain, and
the collected live suite includes both pending expiry and already-redeemed
same-key expiry cases. These use new past-dated fixture history under one owner,
not edits to existing retained expiry/identity fields. There are 39 collected
cases at three repetitions; no case has executed against PostgreSQL here.

Review of all seven migration DDL statements: one new table (PK, three FKs and
two checks), its inbox index, two functions and three triggers. The PK also
creates its own unique index. Identity/recipient/issuer/scope/expiry are immutable;
resolution is terminal; DELETE/TRUNCATE and downgrade are refused. There is no
team/recipient uniqueness constraint: distinct issuance keys intentionally create
separate grants. The existing idempotency scope enforces exact-key uniqueness.
Recipient/current-leader authorization is enforced by the service, not by a UUID
or FK alone. The deferred membership trigger checks redemption-time committed
admission, not every future departure. No migration was executed, so SQL rendering
and source review do not certify PostgreSQL enforcement or schema drift.

The guarded migration holds SHARE table locks on all eleven prior tables across
the before/after aggregate fingerprint scans and DDL. Ordinary reads can continue;
INSERT/UPDATE/DELETE, including auth/session/throttle writers, can wait or time
out. FK creation also locks referenced users/teams. Use an exclusive owner
maintenance window with no other test/fixture writer. Full-table hashing/sorting
cost is unmeasured; 5-second lock and 15-second statement limits remain. These are
per-statement bounds, not a measured total migration duration. Alembic's version
update and the seven DDL statements share the externally owned transaction with
the preservation comparison; failure rolls them back. Existing 0005 is a no-op
target, not an adoption/repair/drift verification tool. Independent post-command
verify still requires exact 0005.

Expected persistent writes after separate approval: migration creates the new
objects and updates Alembic metadata only, preserving the eleven old tables.
Tests retain fresh hackathons/users, credential/session/throttle rows, teams,
invitations, memberships and complete idempotency/audit/outbox history. Per G1
fixture, domain assertions require one team, two memberships, 50 invitations and
52 linked completed outcomes/audits/outbox rows. Losers roll back domain effects
but still retain the intentional separate throttle attempt charge. Observer and
canonical checks write no application rows; no fixture deletion/cleanup occurs.

Nonblocking limits: the observer's 3-second polling budget is checked between
queries; SQL/driver time is governed separately. Worker joins and observer joins
are bounded, but synchronous driver/OS failure or a daemon timeout is not proof
all work has stopped. Failures cannot certify success; stop and review instead
of rerunning. The test uses in-process HTTP/TestClient and a test-only 64-thread
limit; it proves neither real-network/browser/HTTPS behavior, performance, 50
simultaneous DB transactions nor observation of every uncommitted intermediate
state. Fresh committed fixture assertions and database constraints are the
capacity/uniqueness authority. Existing retained-data drift and legacy suites
at 0005 are not independently certified. G1 remains OPEN pending repeated live
evidence and owner review. Exact R1 commands/results are in PROGRESS.md.

## Compatibility and historical owner-only live prerequisites

R2 status supersedes the preparation history below: the owner reports applied
0005 and the successful guarded run is audited in G1_ACCEPTANCE.md. No migration,
database inspection or live rerun was performed by Codex. These unchanged exact
revision limits continue to apply; success at 0005 does not port older suites.

| Command/suite | Exact revision / limitation |
| --- | --- |
| invitations | Explicit 0005 only; every new/pooled/observer connection checks identity, revision, actual transaction mode and timeouts |
| admission | Unchanged explicit 0004 only; refuses 0005; original 105-case collection unchanged |
| auth, credentials, sessions, auth-api, throttles, idempotency, mutations, retries, reads, team-api | Unchanged explicit 0003 only; refuses 0004/0005 |
| schema/services | Legacy default 0002 and existing 0004 limitations retained; explicitly reject 0005 before credentials |
| browser inspect/serve/verify | 0003 only, excludes team/admission/invitation routers and rejects route reintroduction; no invitation-write permission |
| database verify/migrate | Explicit revision; 0005 migration accepts only exact 0004 or already-0005, with eleven-table preservation inside the owned DDL transaction |

No port of legacy suites to 0005 or live compatibility certification is claimed.
The old advice to run 0004 regressions before upgrade is now historical. Do not
downgrade, reset, bypass guards or accept either revision to run old suites at 0005.
The new suite includes real auth/CSRF, private inbox, exact replay, unauthorized
recipient/issuer, stale issuer, expired retained grant, cross-team uniqueness and
distinct-caller last-seat cases. Expired state is a past-dated fixture created
with its complete audit/outbox chain; existing immutable grants are never edited.
It does not independently reflect every DDL object/constraint or replace all
legacy/live migration-drift tests. No explicit revoke endpoint in this milestone;
expiry and changed issuer leadership invalidate grants. No transferable code UX.

**Historical preparation reference only: 0005 is already applied. Do not execute
the following migration sequence against the existing merge_test.** It records
the supported pre-upgrade process, not a current task or authorization.
Only after owner approval of migration preparation, in an interactive terminal
without a transcript (hidden merge_app password; never a password/URL argument):

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0004_admission
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed. Stop; do not migrate.' }
.\.venv\Scripts\python.exe -m test_support.database migrate --confirm-merge-test --revision 0005_invitations
if ($LASTEXITCODE -ne 0) { throw 'Migration unsuccessful. Stop; retain all data and review.' }
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0005_invitations
if ($LASTEXITCODE -ne 0) { throw 'Revision verification failed. Stop.' }
```

Historical validation command (the successful report matches this supported
invocation; it does not store literal argv). **Do not rerun it in R2:**

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite invitations --revision 0005_invitations --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Invitation validation unsuccessful. Stop; retain fixtures and the matching report.' }
```

This writes scoped retained fixtures. Require matching terminal exit 0, nonempty
collection, all teardowns and suite_and_fixture_checks_completed in the printed
metadata report. No password/URL/headers/SQL/private exception values are added
to diagnostics. R2 records the owner-run live evidence separately from
collect-only/offline gate/SQL-double control-flow evidence. Test-host 64-thread
capacity and the ordinary bounded DB pool must be reported with any result.
The observer needs its own same-role session visibility and pg_blocking_pids;
the test fails if those observations are unavailable, with no new privilege grant.
Timeout does not prove daemon work stopped; do not rerun blindly or clean fixtures.
No migration, backend host or live test was executed by Codex.

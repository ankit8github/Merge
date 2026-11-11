# G1 acceptance - distinct authenticated admission callers

## Current evidence audit - M-014B-R2, 2026-11-11

**Original Phase 1 G1: CLOSED within the owner-run local guarded PostgreSQL
acceptance scope.** This records owner execution and a local report/source audit,
not a new Codex database run. CI, production HTTPS, browser and load acceptance
remain unverified. Earlier open/blocker statements below are dated history.

The owner reports migration **0005_invitations already applied to merge_test**
and a screenshot showing merge_test / merge_app / 0005_invitations. That screenshot
was described in the request, not independently inspected in R2. The existing
sanitized report corroborates the exact revision required by the guarded suite;
R2 performs no current database inspection or independent migration/drift audit.
**Do not rerun migration, provisioning, cleanup or live tests for this review.**

Local evidence: `backend/test-results/guarded/run-b7498102ceca4576b17a780aa7296157.json`
(Git-ignored, retained locally). SHA-256 at audit:
`f75eaae1ad4ec664d388aa9e198def96e73a1f02f91c265c5a3f4cb59e5588bc`.

| Recorded field | Value |
| --- | --- |
| suite / revision / repetitions | invitations / 0005_invitations / 3 |
| status / exit_code / stage | passed / 0 / pytest |
| collected / teardowns_completed / skipped | 39 / 39 / 0 |
| failures / active_node | [] / null |
| invariant_verification | suite_and_fixture_checks_completed |

The supported PowerShell invocation consistent with this metadata and the fixed
runner is below, **for evidence reference only; do not execute it now**:

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite invitations --revision 0005_invitations --repetitions 3
```

The JSON does not retain argv, interpreter path, terminal transcript, credential
input method, source hash or successful-node roster. Therefore this is the exact
supported equivalent command, not recovery of the owner's literal shell text.
The report checksum identifies the audited JSON; it does not attest the code
executed. Attribution to the owner run relies on the owner's confirmation and
matching metadata, interpreted against the reviewed local suite/runner.

### Actual counts and source-derived conclusions

The report records **39 total collected/completed cases**, not 39 per repetition.
Credential-free R2 collection confirms 13 parametrized cases per repetition:
workflow/replay 1, security 5, authority/key reuse 1, stale issuer 2, G1 1,
cross-team 1 and expiry 2. At three repetitions this is 39, not 117.
The fixed runner selects the entire invitation directory, clears external pytest
selection options/plugins and fails fast. A zero-exit, zero-skip, fully completed
report therefore supports all 39 cases completing under that implementation.
There is no independent historical per-node pass log in this compact report.

The exact G1 nodes are
`invitation_tests/test_invitations.py::test_distinct_authenticated_50_caller_last_seat[0]`,
`[1]` and `[2]`. Thus three 50-caller races, 150 primary contender HTTP attempts,
three winners and 147 capacity conflicts follow from source plus completed-run
evidence; those are derived totals, not separately recorded diagnostic counters.
Winner replays and sequential setup calls are additional calls, not contenders
or extra pytest cases. No elapsed time, throughput or percentile is reported.

### Why this is literal distinct-caller contention

- Every race creates 50 real registered accounts and valid sessions through the
  actual credential/session services. It asserts 50 different actor UUIDs,
  session secrets and CSRF values, excluding the leader. Each explicit HTTP
  Cookie/CSRF pair authenticates its own recipient; no principal/auth override.
- The leader sequentially issues 50 legitimate grants over HTTP. Canonical setup
  matches every ID to its intended recipient/team/hackathon/issuer. Those calls
  do not count as concurrent admission. One founder occupies a capacity-2 team.
- Fifty worker requests each redeem their own grant with their own key. A
  test-only wrapper gates all 50 arrivals after real auth/CSRF checks, then calls
  the real service. Only the test host raises/restores AnyIO sync capacity to 64.
  One TestClient supplies these explicit independent identities; this is not 50
  separate network connections, browser profiles or client processes.
- Active backend registration requires a known authenticated actor, exact target
  hackathon/team binds and the actual team-lock statement. The observer holds
  that target's team lock, samples registered same-role/current-database Lock
  waiters, follows pg_blocking_pids edges rooted at its own PID and counts
  distinct actors. Unrelated blocking cycles, unregistered/external PIDs and
  duplicate-actor/self-blocking candidates cannot supply two rooted actors.
  Registry entries/tags are removed on transaction-body exit, even after handle
  invalidation. Overlap requires at least two relevant backend waiters, not 50
  simultaneous database transactions; the ordinary connection pool queues work.
- Arrival/observer/worker deadlines fail the test, with no uncertain result
  accepted as a capacity loser. The observer releases workers on every exit.
  Bounded joins do not establish that timed-out daemon/driver work has stopped.

### Committed assertions and final certification

`test_support/invitation_race.py::assert_race_state` requires exactly one 200 and
49 `409 team_full`, one redeemed grant and 49 pending grants with null redeemed_at.
The fresh canonical snapshot requires exactly founder plus winner membership,
one assignment per hackathon/user, the unchanged valid leader, capacity 2 and
team version 52: creation 1, issuance 50, redemption 1. Exactly 52 unique completed
idempotency records, 52 audits and 52 linked outbox rows must match operations,
actors, hackathon/team, version sequence 1..52, response status/headers/body,
invitation identities and membership transitions. Losers leave no redemption
reservation/history. The winner's exact key returns identical HTTP content and
an unchanged fresh snapshot. Separate cross-team races require one 200 and one
409 already_assigned with only one membership and an unconsumed losing grant.

Final fixture certification **includes the G1 state**: every function-scoped
environment tracks its fresh hackathon before writes and calls
`InvitationDatabase.check()` in finally. The inherited checks inspect canonical
capacity/leadership/uniqueness, all completed outcomes, versions and audit/outbox;
invitation checks inspect grant state, redeemed membership and issue/redeem audit
counts for that same hackathon. A teardown failure prevents the report's completed
invariant status. The exact race oracle runs in the test body and is stronger than
the generic teardown checks; neither scans unrelated retained hackathons.

G1 closure is limited to this repeatable local transaction/API acceptance, with
database enforcement plus committed-state checks. It does not independently
observe every uncommitted intermediate state or certify every DDL object, old
retained record, arbitrary schedule, production host or transport. Existing
legacy suite revision/browser restrictions remain in [INVITATIONS.md](INVITATIONS.md).
R-14/G4 GitHub Actions, real-network TLS/HTTPS, browser/mobile/assistive technology,
100-client load, 10k/2k seed and p95 remain open. Invitation UI, delivery, explicit
revocation and broader lifecycle flows are outside this milestone. R2 makes no
source/test change after the audited run; offline results are in PROGRESS.md.

Owner exercise: replace the offline observer graph with a two-node cycle that
has no path to the observer; explain why its two blocked PIDs must not close G1.

## Historical M-014A analysis and M-014B/R1 readiness

The analysis below predates invitation implementation and owner execution.
Its missing-command, proposed-prerequisite and G1-open statements retain that
historical scope; they are superseded by the evidence audit above.

2026-11-11; baseline `fa7cc6f00c690de08fa4d5e79b169a6f4506fb92`.
**Analysis complete; literal G1 harness implementation blocked by the available
admission authority. No G1 live execution or pass is claimed.** This proposal
changes no requirement, approved decision, API, service, schema or permission.

## Original gate and precise interpretation

[REQUIREMENTS.md](REQUIREMENTS.md), R-07 and mandatory scenario 1, require 50
distinct authenticated callers competing for one available seat: exactly one
success, 49 safe rejections and no over-capacity. [ARCHITECTURE.md](ARCHITECTURE.md),
Last-seat race proof, requires independently authenticated concurrent requests,
one newly inserted active membership, no duplicates, valid leadership and correct
audit/outbox counts. Its G1 gate also retains cross-team race/idempotency proof.
[PROGRESS.md](PROGRESS.md)'s gate remains partial, with authenticated API
acceptance outstanding. None is reinterpreted by this checkpoint.

For the literal last-seat proof, 50 different validated account UUIDs must each
issue an authorized capacity-changing admission attempt against the SAME team
in the SAME hackathon during an overlapping schedule. Fifty sessions of one
account, 50 subject UUIDs in one leader's commands, pre-created accounts, or
sequential admissions are different scenarios. Authentication alone does not
grant permission to add a membership. Rejection of unauthorized identities does
not demonstrate that they lost capacity contention.

## Why the current API cannot supply that experiment

| Existing operation | Authenticated actor and authority | Capacity effect |
| --- | --- | --- |
| POST scoped /join-requests, body {} | Each unassigned requester acts for self | Creates retained pending request; reserves no seat |
| POST scoped /join-requests/{id}/decision, approve | Current target-team leader only | Adds the requester's membership atomically |
| POST scoped /join-requests/{id}/decision, reject | Current target-team leader only | Resolves request without adding membership |
| POST scoped /teams | Authenticated founder | Creates a different team; cannot fill the target's last seat |
| Internal join_team_idempotent | Trusted Python caller supplies actor UUID | Adds membership, but UUID validation is not HTTP authentication or admission authority |

Source review: app.main registers auth, read, team-create and admission routers.
app/admission_api.py derives every actor from creation_session's validated cookie;
the only decision body is approve/reject. app/services/admission.py `_change`
locks the target team and requires `team.leader_user_id == actor` before decision
replay or mutation. Only approve calls `_admit_locked_in_tx`. Request creation
never calls that helper. TEAM_SERVICES.md and TEAM_MUTATIONS.md explicitly retain
trusted join as internal; no HTTP invitation redemption currently exists.

A team has one current leader. Fifty authorized distinct decision actors cannot
exist simultaneously for this target under the approved contract. Fifty
nonleader decision attempts must return forbidden, independent of the vacancy.
Leader replacement between attempts would be a different schedule/policy, would
not create 50 simultaneous authorized contenders, and is outside this task.

Existing `test_authenticated_final_seat_approval_race[...-50]` registers/logs in
50 distinct candidates and creates their requests SEQUENTIALLY before its
Barrier. The 50 concurrent `decide` calls all default to the subject's leader
session (`s[3]`); the distinct requester sessions authenticate setup only.
This is legitimate single-leader approval concurrency, not literal R-07.
The subject fixture also creates a leader and an additional account; counting
all accounts provisioned would further misstate actual concurrent participation.
The start Barrier proves worker release, not that 50 database transactions reach
the team lock together; synchronous HTTP workers and the connection pool can
queue calls. Existing bounded-worker timeout cannot prove database work stopped.

## Smallest secure path proposed for owner decision

Keep the current leader-approved workflow and its tests unchanged. Implement the
already-required expiring invitation capability (R-03/R-11, design policy D-03)
as a separate business-feature milestone, then target its authenticated
redemption operation with G1. A leader-issued valid invitation can grant a
participant authority to attempt admission without granting arbitrary public join
or leader powers. This serves an existing product requirement, rather than adding
an authorization exception solely for a test.

This is NOT approval or a ready contract. Invitation issuance/redemption scope,
expiry/revocation/use policy, secret storage, brute-force limits, error and replay
semantics, lock order and required schema revision must be reviewed first.
No invitation table/service/router is implemented here. An additive migration
may be necessary; no assumption is made that redemption can run at 0004. That is
an explicit additional prerequisite to the present exact-0004 task boundary.

Alternatively, an owner may separately authorize a supplemental existing-API
test with 50 concurrent self-requesters followed by one leader's approval race.
Its evidence must count requester and decision principals separately and keep
G1 open. That test cannot deliver the literal 1-success/49-capacity-conflict
distinct-caller acceptance result; it is not silently substituted here.

Rejected approaches: temporary/public/test-only join routes, overriding validated
principals or leader checks, calling trusted join after an unrelated HTTP login,
50 copies of the leader session, leadership churn, relaxed G1 assertions, or
accepting 49 forbidden responses as last-seat losses. None proves the required
authorized HTTP race.

## Proposed literal race protocol after the prerequisite exists

This is a reviewable plan, not implemented or measured evidence:

1. Use a dedicated fixed guarded suite, explicit reviewed schema revision and
   private test credentials. Check merge_test/merge_app/127.0.0.1:5432, actual
   READ COMMITTED/non-autocommit and exact revision on every pooled/new worker
   and observer connection. Do not broaden legacy revision gates. Preserve
   metadata-only diagnostics, fail-fast exits and final fixture checks.
2. Per repetition, create a fresh retained hackathon/team with capacity 2 and
   only its valid founder membership. Create 50 eligible distinct accounts and
   valid sessions with session-bound CSRF. Establish legitimate admission grants
   according to the reviewed invitation contract. Account/grant setup is not
   counted as concurrent participation. Never emit passwords, bearer/CSRF,
   invitation tokens, raw keys, connection URLs or response bodies in diagnostics.
3. Prepare one immutable command/key per caller. Prove 50 unique validated actor
   UUIDs, 50 distinct valid sessions and matching CSRF, with one command for each;
   retain only nonsecret counts/approved metadata in the report. Tokens must not
   be sent as explicit identity substitutes or shared across callers.
4. Synchronize actual HTTP calls with bounded events/barriers, not sleeps.
   Instrument the real test service/transport without replacing auth or domain
   logic. Record which distinct actors actually arrive and complete; fail on
   missing/duplicate actors. A common client start time alone is insufficient.
   Plan explicitly for sync-server thread/pool limits: a 50-party barrier inside
   a smaller synchronous pool can deadlock. Any test-only capacity configuration
   must be bounded, reviewed and reported rather than changing production defaults.
5. Demonstrate real contention using a guarded observer-held target-team lock
   and bounded observations of distinct contenders waiting for that lock; release
   only after the required overlap evidence is obtained. Do not hold a user lock
   that prevents those contenders reaching the team lock, or wait for an
   impossible number of pooled connections. Check identity/revision/timeouts on
   the observer, release it in finally, and fail on deadline rather than relaxing
   overlap assertions. Specify exact observation privileges and achievable counts
   in the future implementation. Never claim 50 simultaneous DB transactions
   from 50 outstanding HTTP calls when the server queues them.
6. Join all workers within a reviewed deadline. Any authentication failure,
   infrastructure error, uncertain outcome or timeout invalidates this acceptance
   run; no automatic new-key retry, success inference or cleanup. A timed-out
   worker/connection is not proven stopped. Reconciliation/fault cases need
   separate same-key tests, not a relaxed winner count in the race.
7. On fresh guarded read-only connections after successful worker termination,
   assert exactly one successful membership addition and 49 documented capacity
   conflicts. All 50 responses must belong to their original actor/command. Check
   canonical roster, unchanged valid leader, exact capacity and scoped membership
   uniqueness across ALL teams in the fixture hackathon. Verify database capacity
   constraints remain active; final snapshots/observer samples cannot alone prove
   every transient state, and are not a substitute for database enforcement.
8. Verify exactly one committed successful admission idempotency effect and its
   matching actor, version increment, audit event and linked outbox record;
   losers leave no partial admission chain. Compare against the PRE-RACE baseline
   so setup/grant effects are not counted as race mutations. Replay the winner's
   exact command/key and require the identical stored success and unchanged fresh
   snapshot. Verify grant use/revocation state against the reviewed future contract,
   without inventing pending/terminal states for an unimplemented feature.
9. Repeat at least three times with fresh retained fixtures, recording each
   repetition's actual participant/overlap/outcome/invariant evidence. Keep
   unauthorized, wrong-CSRF, missing/revoked/expired grant and stale-leader checks
   separate. Cross-team membership/idempotency acceptance also remains required.

For the EXISTING approval contract, the expected last-seat result remains one
200 approved request/membership and 49 409 team_full responses whose requests
remain pending with null resolved_at/resolved_by. Team version, audit, outbox and
successful decision idempotency increment once beyond setup. Same-key winner
replay changes nothing; stale leaders must fail before replay. These are already
the existing oracle's assertions, not new distinct-caller G1 proof.

## Supported commands and execution boundary

**No supported live command can establish literal distinct-caller G1 today.**
There is no --suite g1 or invitation-redemption suite; none is invented here.
The existing guarded admission command below is a reference for a separately
approved regression run ONLY. It cannot resolve this blocker or close G1, and
does not need rerunning merely to confirm this source-level mismatch:

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite admission --revision 0004_admission --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Admission run unsuccessful. Stop; retain fixtures and the matching sanitized report.' }
```

Owner-only, after separate live approval, in an interactive terminal without a
transcript: the existing runner obtains merge_app's password through hidden input.
Do not place credentials in the command or URL. It runs 105 existing admission
cases with retained writes and committed checks; it is not a read-only operation.
Accept only matching terminal exit 0 and suite_and_fixture_checks_completed.
No migration, downgrade, permission change, cleanup or reset is included.

Credential-free collection, actually performed in M-014A:

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m pytest admission_tests --collect-only -q
```

Collection does not execute fixtures or establish a live pass. Offline regression
commands/results and the final Git inventory are recorded in PROGRESS.md.
No new concurrency suite is implemented until the owner resolves the legitimate
admission-capability prerequisite. G1, CI and deployed/browser acceptance stay open.

Owner exercise: trace the two session arguments in the existing 50-candidate
test; explain why moving its requester POSTs inside the Barrier would still leave
only one identity authorized to perform capacity-changing decisions.

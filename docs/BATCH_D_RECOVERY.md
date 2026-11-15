# Batch D diagnostic recovery and release triage

2026-11-15. Deadline: **15 November 2026, 23:59 IST**. This work implements and
tests offline diagnostics; it does not certify live startup or authorize any live
operation. No database, host/browser, fixture, Git publication or deployment action.

## Diagnostic correction and limits

Scope: `release_support/integrated_diagnostics.py`, `integrated_host.py`,
`integrated_run.py` and focused tests. No production application change, migration,
dependency, API contract, session policy or domain transaction/lock change.
Both legacy browser hosts, mutation ledger, public campaign and certifier remain
unchanged. The inherited BrowserServer drain protocol still governs shutdown.

The new independent IntegratedServer subclass observes Uvicorn callbacks and
prints only a fixed readiness banner after Uvicorn sets `started`. No health
request is made. Failure reports include the following sanitized state:

| Field | Meaning / limit |
| --- | --- |
|startup_reached|Entered the server startup callback.|
|readiness_achieved|Uvicorn startup returned with `started=true`; not an observed HTTP response or campaign pass.|
|shutdown_requested|Signal handling or shutdown entry was reached; does not imply completion.|
|shutdown_completed|Inherited drain completed without a lifespan failure/error; application shutdown audit is checked independently.|
|run_returned / interrupted|Distinguish normal run return from handled KeyboardInterrupt.|
|lifecycle_failure|Fixed startup/shutdown exception/incomplete category; no exception text.|
|failed_predicates|Names of false original drain checks, or `ledger_complete`.|
|drain_failure_latched_guard|An undrained server forced the guard failure latch; do not mislabel that latch as proof of a database rejection.|

The five original drain predicates remain mandatory: server_started,
server_drained, guard_not_failed, mutation_ledger_healthy and
application_shutdown_complete. The unchanged exact 38-POST/18-domain-attempt
ledger completion now has its own `ledger_complete` stage, before the unchanged
independent final observer. A ready, drained host with zero POSTs must still fail.
No counter, readiness flag or successful shutdown can waive campaign completion.

Counters record total HTTP requests, GETs and requests to the four fixed `/auth`
routes, including denied/anonymous requests. Separate session-validation attempt/
success counts describe adapter calls, not unique users or requests: CSRF and
boundary checks can validate the same request more than once. Success is counted
only after real validation and campaign principal checks. GETs consume no POST
budget. Counts use a lock and retain no identities, paths, query strings, headers,
passwords, cookies, tokens, raw bodies, responses or exception values. Existing
logging suppression remains; this is not a raw diagnostic logging facility.

## Permanently consumed campaign

Run: `17ff1152-1ac0-4ace-a887-13436dd2963f`.
Original source: main / `db17f3ef2c2934d2d4cc7db06499a291949a3d16`, 299 source files.
All 15 existing integrated JSON artifacts and all other starting evidence are
retained; no old receipt is updated to include new diagnostic fields.

Paths below are under `backend/test-results/integrated/`:

| Evidence | SHA-256 |
| --- | --- |
|process-2e623a3994794fa39f03153f4b5a116c.json (incomplete start)|b05ba368db3a4c4b9de853d3e842d9f67d584270bf1c0134329ee92f55d0ecc9|
|process-e7a13ca940e9443993c07ecbc2ceae9f.json (failed, native child 1)|b6cd260d834a45ede74aa65d3de676f141225aa106531be3da023c477a43fc64|
|host-f1c9dc52e89a410f9ec95e6f06137c4f.json (stage drain)|98577cde5160737e7c6d23aaf415ad5d0a200162455373a8346d27aba90b4944|
|campaign-17ff1152-1ac0-4ace-a887-13436dd2963f.json|feffe70ce6be362b62d0fa07b4b199cfdcb6a458ecd899d785d2ebea073a3c30|

Report interval: 2026-11-15 08:55:41–08:55:52 IST. Marker status is
`started_not_certified`, permanently consuming this namespace even with 0 POSTs.
All report/marker hash links and canonical plan digest matched during diagnosis.
The plan byte hash is `8f0533f62b23a5838858b613949d2c5b6aeefe891f7e0b41d1530689f7623791`;
canonical digest is `068e7f46c6af89db3be855cf72cf91c932f7337c1fc339b77d2707b9477214b1`.

The existing later attempt (host-8531d6b5f0e741b99d43b4e04db841c9.json;
final process-61993516258548c38a15c7b5b8d5578b.json, native 1) stopped at
start_marker/scope_already_started around 08:57:10 IST. It is separate saved
history; this task performs no retry. CreateNew protection must not be deleted,
renamed, bypassed or reset. Old fixtures are never adopted for another campaign.

Known: 0/13 browser checkpoints (owner baseline), 0 attempted/completed POSTs,
0 completed domain attempts; no campaign effect is evidenced. Initial socket
reservation, guarded snapshot/preflight and app/config construction were passed.
The old stage covers both shutdown validation and ledger completion. HTTP
readiness, which drain predicate failed, graceful shutdown and authenticated GET
traffic were not recorded. There is no independent final observer/certificate.
No standalone host log is linked; quiet_logs suppresses Uvicorn diagnostics.
The historical exception cannot be recovered from these artifacts.

Zero ledger POSTs supports no normal host write path, but **does not certify
database-wide unchanged state**. Preparation already inserted two hackathons;
external writers are not excluded. The original full preflight snapshot existed
only in memory. A later read cannot recreate it or retrospectively certify the
original before/after preservation. Readiness also cannot be inferred from the
old initialization print. No runtime startup fix is claimed from an unknown cause.

## Historical PostgreSQL evidence reviewed without connection

| Suite | Retained evidence / scope |
| --- | --- |
|Profiles 30/30|release/profiles-56e3ff1b01d14fd8920fd47f61a74d84.json: exact 0006_profiles, native 0, 30 unique passed nodes/teardowns, no skips/failures, completed invariant checks; historical 299-file source snapshot at db17f3e. SHA256: `7ba72aab81c8d7b4a1daf418af91bb6282a66f66143b027dee09fb8b5d8a34e7`.|
|SSE 4/4|release/realtime-6ccc61aff99049678e262cc1cc724a3f.json: exact 0005_invitations, native 0, 4 collected/teardowns, no skips/failures, completed invariant checks; historical 276-file snapshot at 3650e62. SHA256: `165e4a21b60a94ec4ae90d3160c703a41465a54597d16e9bef0886ef73619c73`. Two prior failed SSE receipts remain failures.|
|Lifecycle 10/10|guarded/run-114f00ece8514d9ebd9c54d738b6cd3e.json: exact 0005, 10 collected/teardowns, no skips/failures, completed invariant checks. SHA256: `9aba72d5f97d32479cb0bcc97caf1acc7dccd34ee38e0fe261202777497f9c86`. Native 0 is owner-confirmed; this aggregate report has no independent native-exit/full-source receipt. See LIFECYCLE.md.|

These establish their documented historical local acceptance, not current-source,
browser, HTTPS, production-role, public CI or performance certification. This task
does not rerun PostgreSQL, manufacture stronger provenance or revise old hashes.
The diagnostic/doc changes make the old profile receipt source-stale for a NEW
integrated launch under the existing strict full-source eligibility gate.

## Fresh campaign decision

A fresh campaign is justified to obtain missing browser evidence, conditional on
owner approval and reviewed new sources/prerequisites. It is not created here and
is not required merely to publish the reviewed source repository. Prioritize the
public release and real HTTPS smoke over additional optional harness schedules.
Do not turn that prioritization into a browser-pass claim.

Before any future campaign: freeze/review sources; obtain eligible source-current
profile proof under the unchanged gate (any new PostgreSQL run requires separate
approval); review a new public plan with distinct UUID4 run/hackathon IDs and derived
account/team names; keep 38 POSTs/14 expected domain effects and all 13 checkpoints.
The current CLI loads a fixed plan path, so changing plans is an explicit reviewed
source change, not an ad hoc flag or edit to an old receipt. Then separately approve
freshness inspection, additive preparation, one guarded start, frontend/browser
scope and final observer. No existing certificate authorizes these operations.
Do not loosen source checks, completion, mutation budgets or marker protections
to make historical evidence eligible.

## Production triage and minimum release checklist

Reviewed pending UI changes: specific409 messages; definite422 draft correction
with CAS retained; unknown/conflicting saves require canonical reload; named
invitation/applicant controls retain exact UUID command targets; Cancel restores
focus without submitting; leadership loss withdraws unsubmitted removal; health
wording distinguishes liveness from team/account access. Existing regressions
cover these behaviors. No confirmed production P0 defect was established in this
review. No further speculative application edit was made.

The acceptance host is not the production server. Production starts through
app.production.serve/create_production_app, independent of integrated_run and its
ledger/marker. A failed or incomplete harness run does not demonstrate a production
startup defect. Offline tests/build cannot prove native container/grant/TLS behavior.

The actual release blockers are incomplete public delivery and unverified runtime
prerequisites, rather than an identified application-code failure:

- [ ] Owner reviews the complete existing dirty tree plus this bounded correction;
  authorizes commit/publication of one exact revision. Verify a public GitHub URL,
  push only after approval, and retain successful Actions URLs/artifacts including
  the authenticated50-caller race and >=20 API tests. Workflow source exists;
  no remote job or publication was executed/verified here.
- [ ] Use the already proposed PRODUCTION.md single-host Caddy/API/PostgreSQL
  topology; obtain owner-approved Linux host/domain/DNS, exact public HTTPS origin,
  secrets and image tag. Review/pin images and validate Compose/Caddy natively;
  local JSON topology checks are insufficient. No new hosting architecture proposed.
- [ ] After separate owner approval, create new production-only volumes/secrets,
  bootstrap restricted roles, explicitly migrate merge_prod through0006, verify
  runtime grants/readiness and add one approved demo hackathon. No retained test
  fixtures, benchmark accounts or database credentials belong in production/Git.
- [ ] Launch API then Caddy; verify public TLS/redirect, React deep links/assets,
  same-origin API, Secure host-only cookie, CSRF/Origin/proxy handling, real named
  team/invite/lifecycle/profile flows and two-client SSE/reconnect. Check keyboard
  and mobile behavior. Record actual URL/revision and sanitized evidence; no pass
  from /health alone. Retain volumes and stop ingress/API on failure.
- [ ] Complete the mandatory isolated10,000-user/2,000-team seed and100-client
  p95<200ms/error report with declared environment/native exits. None is measured
  here. Do not load-test production. Optional32-SSE comparison and extra repetitions
  must not displace publication, HTTPS smoke or required submission artifacts.
- [ ] Export/check the existing DESIGN_ONE_PAGE.md as one page; record a real
  walkthrough <=5 minutes using DEMO.md and fresh approved demo scope; publish
  actual repo/live/load/design/video links and verify public access. Submit in the
  organizer workspace before23:59 IST and retain the actual submission receipt.

No production resources, credentials, migrations, Docker image/native validation,
CI, seed/load, public URL, video or submission success is inferred from local files.
Finish with explicit pending labels if any mandatory item remains incomplete.

## Offline evidence

Exact commands/results and final preservation inventory are recorded in the new
2026-11-15 PROGRESS entry and ignored logs under
`backend/test-results/batch-d-recovery-7c70f6fc2a594620985d11c9f0f54307/`.
Baseline contains 299 source files and 885 preexisting evidence files. Final checks
must show all historical evidence bytes unchanged. Tests use fake lifecycle/DB
services and in-process ASGI, not a real listener or PostgreSQL connection.

Initial focused failures were test-helper defects: missing diagnostics constructor
argument (8 failed/186 passed), then the bind trap correctly rejected Windows
asyncio's internal TCP socketpair (7 failed/187 passed). The replacement directly
drives synchronously completing parent doubles; the bind/driver/server traps remain
active. Corrected focused run passed194 tests. A final added lifespan-error case
ensures shutdown completion never hides a lifespan error; final results are in
PROGRESS. No failing assertion, timeout, guard or completion condition was weakened.

Owner exercise: use the synthetic zero-POST regression to explain how readiness
and graceful shutdown can both succeed while ledger completion still fails. Then
change one fake drain flag and predict the precise failed_predicates name before
running the focused test. Never exercise this against the consumed campaign.

Recommendation: CONDITIONAL for the offline diagnostic component and owner release
review; BLOCKED for reuse of the consumed campaign or claims of verified deployment.
STOP for owner review. No commit/push/deployment or live action is authorized here.

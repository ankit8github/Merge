# Engineering review history

Dated development reviews retained for engineering rationale, failure analysis,
source inventories and evidence provenance. These snapshots are **historical**;
their old commands and permissions do not authorize any action. Use the current
[status](../PROGRESS.md), [testing](../TESTING.md), [deployment](../DEPLOYMENT.md)
and [submission checklist](../SUBMISSION.md). No generated certification receipt,
credential, fixture dump or private diagnostic was copied here.

Eight standalone reviews were consolidated without removing their substantive
text. Relative documentation links were rebased, obsolete report references now
point here, and namespaced anchors were added. Code blocks and dated test results
retain their original content. Exact original document hashes and classifications:
[documentation audit](DOCUMENTATION_AUDIT.md).

- [BATCH_A.md](#batch-a)
- [BATCH_B.md](#batch-b)
- [BATCH_C.md](#batch-c)
- [BATCH_D_RECOVERY.md](#batch-d-recovery)
- [BATCH_E_RELEASE.md](#batch-e-release)
- [PRODUCT_AUDIT.md](#product-audit)
- [BROWSER_HOST_AUDIT.md](#browser-host-audit)
- [RENDER_REVIEW.md](#render-preparation-review)

---

<a id="batch-a"></a>

<a id="batch-a-consolidated-batch-a--owner-review-2026-11-14"></a>
# Consolidated Batch A — owner review, 2026-11-14

Recommendation: **CONDITIONAL**. Profiles/ranking and essential UX are implemented
and reviewed offline. No PostgreSQL, live SSE, browser, deployment or performance
acceptance is claimed. No commit, push, migration, fixture cleanup/reset or service
startup is authorized by this report. The official PS1 request for complementary
skill/time-zone ranking and explanations was rechecked against the
[organizer statement](https://hack4hack.com/hackathons/hack4hack-crew-hiring-challenge-2026-tp3m).

<a id="batch-a-a-existing-sse-review-and-preservation"></a>
## A. Existing SSE review and preservation

Baseline main HEAD: abfea1a6116dbe0295b45d21e290c56f84a91eb5. The initial tree had
13 modified tracked files and eight new files. Read the complete SSE source,
tests, four guarded cases, REALTIME.md and tracked diff before implementation.
An ignored local patch/hash snapshot preserves that starting state.

- Public invalidations cover committed create/admission/redemption/departure,
  removal, succession and deletion. Private requests use requester/current live
  leader predicates; invitation issuance uses intended recipient. Every SQL poll
  is hackathon-scoped; projected frames contain only schema, own actor and scope.
- Original session validation, Origin, Fetch Metadata, HTTPS/proxy guards stay
  intact. Actor selectors and malformed stream parameters are rejected. No new
  auth/session model, domain write or outbox publication mutation.
- Separate public/private counts prevent loss of private visibility masking a
  public increment. Retained committed-row counts avoid UUID/time high-water gaps;
  reset always refetches on reconnect. This is invalidation, not event replay or
  exactly-once delivery. PostgreSQL visibility remains unverified for M-020A.
- Existing short read-only samples close before yield/wait. Worker-pool work,
  per-process/account subscriber caps, nominal lease and send deadlines are
  preserved. Cancellation releases ownership; in-flight synchronous DB calls
  finish under existing driver/query bounds. Actual wall time/pool load is not
  certified. COUNT over retained history remains an unmeasured scaling cost.
- Layout cleanup fences old account/hackathon callbacks, closes EventSource,
  aborts probes and clears timers. Canonical reads refresh without replaying
  commands or rotating mutation ownership. Existing reconnect/dedup/session and
  lifecycle tests remain intact. New compatibility tests cover live invalidation
  during confirmation/drafts/ranking and loss of private leader content.

No SSE production correction was justified by this review. Ten key source/test/
contract/runner files match their pre-Batch-A hashes, including both SSE services,
both guarded case files, both original offline test files, useRealtime, useRead,
REALTIME.md and the runner. Integration adds profiles without replacing the SSE
router, provider, workspace signal or existing evidence. New browser host filters
exclude the profile router; old manifests/budgets/ledgers remain unchanged.

<a id="batch-a-b-ranking-api-schema-and-formula"></a>
## B. Ranking API, schema and formula

The pre-implementation ADR refinement and exact contract are in RANKING.md.

- GET /api/me/profile reads only the authenticated account's own profile.
- POST /api/me/profile replaces skills, timezone and discoverability with an
  expected version, existing cookie/CSRF/Origin policy, strict body and no actor
  selector. Stale edits return 409; unknown delivery requires canonical reload.
- GET /api/hackathons/{h}/teams/{t}/suggestions requires current leadership of a
  live in-scope team. Candidates are credentialed, opted-in, non-self accounts
  with no membership in that hackathon. Full teams yield no candidates. Existing
  invitation/membership mutations independently recheck current permissions/seats.
- Additive 0006_profiles creates only participant_profiles (user FK/PK, bounded
  skills array, nullable zone, opt-in false, positive version). No backfill or
  old migration/data/grant change. **UNAPPLIED**; SQL rendering only. Existing
  guarded targets still reject 0006 and head. No new package dependency; installed
  IANA data is a deployment prerequisite (598 available zones inspected locally).
- Skills normalize trim/lowercase/deduplicate/sort, max 20 labels of 1–32 ASCII
  characters. Invalid IANA zones are rejected; opt-in requires a zone. Empty
  skills are valid and earn zero skill credit. Team members' saved fields
  contribute to their own teams even without candidate discovery, as disclosed.

Keep the architecture's weights:

`score = 70 * skill_complement + 30 * timezone_overlap` (0–100).

Skill complement is the fraction of candidate skills absent from current team
coverage. This uses novelty because no desired-skill taxonomy exists. Time-zone
overlap averages assumed 09:00–17:00 working-hour overlap across all current
members; missing member zones contribute zero. Offsets use the returned server
UTC-day noon reference, including applicable DST. This proxy is not actual
availability or skill verification, and is not AI/ML.

Each result returns novel skills, normalized components and weighted points.
Exact fractions determine order; UUID ascending breaks ties before display
rounding. One SQL snapshot supplies authority/eligibility; the connection closes
before CPU scoring. Offsets/zone overlaps are reused. Pool cap 10,000 (overflow
fails explicitly), page size 1–20, and bounded actor/scope/day/snapshot-digest
cursors reject changed pages with 409 ranking_changed. Cost remains unmeasured.

<a id="batch-a-c-essential-ux"></a>
## C. Essential UX

Explicit account-scoped profile editor, opt-in disclosure, field help/errors and
version-safe save/reload. Leaders explicitly open rankings, read explanations and
select a named recipient into the existing UUID issuance command. No automatic
command replay, new persistence or broad navigation refactor. Full-catalog name
search is deferred; exact UUID hackathon lookup and recipient fallback remain.

Pending applicants show display names/usernames; private inbox rows show team and
recipient labels. Only private GET projections change: stored mutation replies
and admission/invitation transaction methods remain AST-identical. Registration
validates/focuses username/password/display-name fields. Lifecycle confirmation
and status explain leave/removal/deletion/succession and Cancel. New form widths,
checkbox layout and long-label wrapping are narrow additions; no new responsive
or assistive-technology certification is claimed without real browser checks.

<a id="batch-a-d-integrated-verification-and-limitations"></a>
## D. Integrated verification and limitations

Environment: Windows PowerShell, existing Python 3.11.9 virtualenv, Node 22.15.0,
npm 10.9.2, installed pytest/Vitest/jsdom/TypeScript/Vite. No installation or host.
Backend commands below run in backend; npm commands run in frontend.

| Actual command | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_profiles_matching.py tests/test_realtime.py tests/test_read_api.py tests/test_browser_harness.py tests/test_browser_full_harness.py --tb=short` | Initial focused 371 passed, 19.29s, exit 0 |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_profiles_matching.py tests/test_admission.py tests/test_admission_api.py tests/test_invitations.py tests/test_invitation_api.py --tb=short` | 235 passed, 13.91s, exit 0 |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_product_labels.py --tb=short` | 2 passed, 1.27s, exit 0 |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_profiles_matching.py tests/test_product_labels.py tests/test_team_api.py tests/test_test_database_safety.py tests/test_realtime.py --tb=short` | Later focused 189 passed, 7.64s, exit 0 |
| `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short` | FINAL backend 1555 passed, 32 database deselected, 93.20s, exit 0 |
| `npm.cmd test -- src/ProfilesRanking.test.tsx src/Realtime.test.tsx src/Journeys.test.tsx src/Invitations.test.tsx src/Lifecycle.test.tsx --reporter=dot` | 151 passed, five files, 31.21s, exit 0 |
| `npm.cmd test -- src/BatchCompatibility.test.tsx --reporter=dot` | 2 passed, 2.56s, exit 0 |
| `npm.cmd test -- --reporter=dot` | Earlier full 394 passed, 15 files, 53.09s; later run 388 passed / 6 failed, 64.60s |
| `npm.cmd test -- --reporter=dot --maxWorkers=2` | 392 passed / 2 failed, 61.56s; startup/loading waits in first admission/invitation cases |
| `npm.cmd test -- --reporter=dot --maxWorkers=1` | FINAL full frontend 394 passed, 15 files, 95.00s, exit 0; unchanged assertions/timeouts |
| `npm.cmd run build` | FINAL TypeScript and Vite build passed, 50 modules, 2.33s, exit 0 |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements, exit 0 |
| `git -c safe.directory=I:/Merge -c core.safecrlf=false diff --check` | FINAL passed, exit 0 |
| `.\.venv\Scripts\python.exe -m pytest --collect-only -q realtime_tests --race-repetitions=1` | 4 collected, 0.02s, exit 0; not executed |
| `.\.venv\Scripts\python.exe -m pytest --collect-only -q lifecycle_tests --race-repetitions=1` | 10 collected, 0.04s, exit 0; not executed |
| `.\.venv\Scripts\python.exe -m pytest --collect-only -q invitation_tests --race-repetitions=1` | 13 collected, 0.19s, exit 0; not executed |

The existing Starlette/HTTPX deprecation warning remains. No online dependency
audit or standalone linter was run. Frontend first-render/loading wait failures
are retained in ignored logs; no timeout/assertion/configuration was weakened.
One successful run does not erase intermittent failures or establish their cause.
The complete single-worker run passes; no test runner configuration was changed.

Earlier red/fix history is retained: new tests initially used unavailable Chai
DOM matchers (replaced with equivalent native DOM assertions); an added sibling
profile panel reused Discovery's epoch key (fixed with a distinct key); an old
UUID-help assertion is preserved. Inherited disabled-fieldset state is checked
with :disabled and duplicate-submit count. Backend exact API/source graph
assertions were explicitly extended for the authorized additions, retaining all
domain idempotency assertions and strengthening negative migration-target checks.
Automatic review initially rejected the graph assertion change; read-only guard
evidence plus explicit unchanged allowlist/rejection assertions resolved it.
No execution permission was added. Combining collection conftests initially failed
duplicate CLI registration; separate collections above succeeded, no fixture ran.

Migration validation used Alembic Operations with as_sql=True and no engine or
connection; 0006 rendered 1,138 SQL characters into ignored local evidence.
Python AST/hash/targeted credential/artifact review passed; it proves ten SSE
files unchanged, core authentication/lifecycle/idempotency/retry code and old
migrations/scopes unchanged, and admission/invitation mutation methods identical.
These scans are limited checks, not exhaustive security or PostgreSQL proof.
Final scan covered 51 pending paths and 25 Python ASTs; index is empty and HEAD
unchanged. Build/log/SQL/snapshot artifacts are ignored. No new linter is configured.

<a id="batch-a-e-remaining-owner-only-live-work--ordering"></a>
## E. Remaining owner-only live work / ordering

1. Review this worktree and preserve the current exact-0005 database. Separately
   approve the unchanged four-case realtime proposal in REALTIME.md before any
   migration. Verify commit/rollback/late-commit/private visibility, cancellation
   and pool/query plans. No live SSE acceptance exists yet.
2. Separately review 0006 DDL, role privileges, preservation fingerprints and a
   fresh exact-0006 guarded harness. The old runner cannot apply/verify 0006 and
   must not silently adopt it. Test initial/update CAS contention, stale and
   ambiguous delivery, DB array constraints, no profile creation for another
   account, real query syntax and current-actor authentication/CSRF negatives.
3. At that reviewed scope, verify full/foreign/deleted teams, leader turnover,
   self/private/credentialless/assigned-user exclusion, other-hackathon membership,
   ties, empty/missing zones/skills, DST reference, cursor changes and overflow.
   Race eligibility changes with admission/departure while existing mutation
   locks/constraints remain authoritative. Recheck private GET label SQL too.
4. Review a new browser scope before profile/ranking/lifecycle/SSE interactions.
   Old M-017 manifests grant no new permission. Test two sessions, reconnect,
   stale responses, logout/account switch, confirmation/Cancel, pagination,
   leader loss, keyboard/mobile/zoom/screen reader and real validation/focus.
5. Verify real HTTPS/cookies/Origin/CSRF/trusted proxy, SSE buffering/timeouts,
   connection budgets, retained-count polling and 10k/2k/100-client load. Deployment,
   CI, required measured p95 and submission artifacts remain separate release gates.

Profile writes deliberately do not manufacture team audit/outbox events. Mounted
rankings respond to team SSE invalidation; profile edits require explicit refresh.
Versioned profile recovery reloads canonical data; existing domain command keys
remain memory-only and retain the earlier crash/reload limits.

Owner explanation/exercise: a ranking read suggests an eligible participant at
one snapshot; only the existing locked invitation/admission transaction grants a
seat. In test_exact_formula_empty_skills_and_missing_zones, remove sql from the
candidate's python/sql skills while team coverage is python and both zones are
UTC. Explain why the score changes from 65 to 30, then run that focused test.

STOP for owner review before database access, migration, commit or remote write.

<a id="batch-a-f-final-file-inventory"></a>
## F. Final file inventory

Inventory is recorded below after final offline review; ignored local logs,
baseline snapshots, compiled caches and dist artifacts are excluded.

```text
 M backend/app/admission_api.py
 M backend/app/invitation_api.py
 M backend/app/main.py
 M backend/app/models/__init__.py
 M backend/app/services/admission.py
 M backend/app/services/invitations.py
 M backend/test_support/browser.py
 M backend/test_support/browser_full.py
 M backend/test_support/concurrency.py
 M backend/tests/test_read_api.py
 M backend/tests/test_team_api.py
 M backend/tests/test_test_database_safety.py
 M docs/ADMISSION.md
 M docs/ARCHITECTURE.md
 M docs/DECISIONS.md
 M docs/FRONTEND.md
 M docs/INVITATIONS.md
 M docs/PROGRESS.md
 M docs/SCHEMA.md
 M docs/TEST_DATABASE.md
 M frontend/src/App.tsx
 M frontend/src/api.ts
 M frontend/src/components/Admission.tsx
 M frontend/src/components/AuthForm.tsx
 M frontend/src/components/Discovery.tsx
 M frontend/src/components/Invitations.tsx
 M frontend/src/components/Lifecycle.tsx
 M frontend/src/hooks/useRead.ts
 M frontend/src/style.css
?? backend/alembic/versions/0006_profiles.py
?? backend/app/models/profiles.py
?? backend/app/profile_api.py
?? backend/app/profile_models.py
?? backend/app/realtime_api.py
?? backend/app/services/matching.py
?? backend/app/services/profiles.py
?? backend/app/services/realtime.py
?? backend/realtime_tests/conftest.py
?? backend/realtime_tests/test_realtime.py
?? backend/tests/test_product_labels.py
?? backend/tests/test_profiles_matching.py
?? backend/tests/test_realtime.py
?? docs/BATCH_A.md
?? docs/RANKING.md
?? docs/REALTIME.md
?? frontend/src/BatchCompatibility.test.tsx
?? frontend/src/ProfilesRanking.test.tsx
?? frontend/src/Realtime.test.tsx
?? frontend/src/components/Profile.tsx
?? frontend/src/components/Rankings.tsx
?? frontend/src/hooks/useRealtime.ts
```

Final inventory: 29 modified tracked files + 22 new files = 51 paths.
All unstaged; index empty. HEAD remains abfea1a6116dbe0295b45d21e290c56f84a91eb5 on main.
One new migration, 0006_profiles, is included; no dependency or lockfile change.
The inventory includes the original 21 SSE paths and all additions in this batch.


---

<a id="batch-b"></a>

<a id="batch-b-batch-b-contract-and-release-evidence"></a>
# Batch B contract and release evidence

Pre-implementation contract, 2026-11-14. Owner authorizes preparation only: no
database, migration, service/browser, load, deployment or remote execution here.

Bounded components in dependency order:
1. Review and hash-preserve all 51 Batch A paths; retain frontend failure logs.
2. Add backend/release_support fixed-target migration/preflight/report modules,
   a separate release_alembic environment and profile_tests exact-0006 suite.
   Keep test_support legacy target/fixtures/reports/manifests unchanged. New DBs
   are merge_profile_test/merge_app and merge_bench/merge_bench_app, loopback:5432.
   Prepare empty targets to 0005, then preserve all twelve existing tables while
   migrating ONLY 0005 -> 0006 in one owned transaction. No downgrade/cleanup.
3. Add CI-only bootstrap and revision matrix at 0003/0004/0005/0006 using fresh
   PostgreSQL containers. Run original authenticated API/race suites plus new
   profile acceptance; require exact counts, no skips, complete teardowns and
   native exit 0. Bind sanitized receipts to worktree hashes. No public CI claim.
4. Add deterministic 10,000-user/2,000-team benchmark-only generation, one-time
   empty-table seed, invariant/count validation and fixed loopback read-only host.
5. Add k6 constant 100-VU authenticated board workload and optional 32 real SSE
   clients, strict report validation and environment disclosure. No measured
   performance result until owner execution. No tuning without evidence.
6. Add ordered owner runbook, offline tests/collection/YAML/migration checks,
   full regressions and final inventory/evidence. No runtime dependency change.

This is a proposed tooling ADR: independent targets and caller-owned migration
transactions keep old exact-0005 evidence usable. New tooling never imports
ordinary Settings or modifies production authentication/locking/SSE contracts.
Benchmark-only bootstrap writes initial memberships directly under unchanged DB
constraints, with a documented initial-state audit boundary; application mutation
race evidence continues to use the original composed production services.

Acceptance tests must prove target rejection before connection, exact revision
and driver checks on every pooled connection, atomic preservation on migration
failure, deterministic dataset/invariants, report failure on skips/missing tests,
and no secrets in generated evidence. Offline checks are not live certification.

CI network refinement: Docker port publication can make inet_server_addr() return
the container bridge address, which the original guards correctly reject. CI
therefore executes the host Python inside only the PostgreSQL container's network
namespace (sudo nsenter --net), retaining the source filesystem and connecting to
its actual 127.0.0.1:5432. No identity allowlist exception or bridge-IP acceptance
is added. This requires a GitHub-hosted Linux runner with Docker/sudo/nsenter and
remains unverified until a real CI run. The published port is loopback-only.

<a id="batch-b-integrated-review-findings"></a>
## Integrated review findings

Recommendation: **CONDITIONAL for owner execution review**. No live acceptance,
successful public CI, applied0006, seeded database or measured load is claimed.
Strict no-database/no-startup/no-remote/no-commit boundaries were observed.

All51 Batch A path hashes were captured before new implementation. Production
backend/frontend source, old runners/fixtures and migration0006 remain byte-for-
byte preserved. Only current documentation overlays are intentionally added to
Batch A docs. Original exact0005 manifests and ignored acceptance artifacts are
not edited; no fixture is deleted. Baseline patch/hashes and prior frontend
failure logs remain ignored local evidence.

- Ranking retains own-account CAS profile writes, cookie/Origin/CSRF/session
  boundaries, current live-team leadership authorization, same-hackathon
  membership exclusion, capacity rechecks, exact70/30 fractions and UUID ties.
  Authorized bounded SQL snapshot materializes at most10001 candidate/member
  rows to detect10000 overflow; CPU scoring occurs after connection release.
  Opt-in eligibility is global across hackathons; membership is per hackathon.
- Profile edits deliberately emit no team/SSE event. Open ranking pages offer
  explicit refresh and stale cursors409; they are not promised realtime profile
  subscriptions. Lifecycle/invitation commands retain their original independent
  server authorization and atomic mutation protocol. No profile change can grant
  membership or bypass capacity. New real-DB cases cover this composition.
- SSE public/private predicates, post-commit visibility design, reconnect reset,
  cancellation/lease/subscriber bounds and React identity/workspace fences are
  preserved. No DB connection is held over stream sleep/send. SQL samples remain
  time-bounded, but COUNT work grows with retained outbox history. At32 subscribers
  nominal16 polls/s include session validation, snapshots and guard costs; no
  measured capacity claim. History-heavy SSE load is still missing evidence.
- Retained full-parallel frontend logs show6 failures; maxWorkers2 shows2 failures
  in Admission/Invitations awaiting initial Test Challenge rendering. Single-worker
  Batch A and current full runs pass394. This supports worker contention as a
  hypothesis, not a proven root cause. No timeout/assertion was weakened, no
  failing test removed and no default-worker success claimed. CI explicitly uses1.
- No demonstrated blocking production defect required a Batch A source change.
  New tooling review fixed its own receipt-roster ambiguity: arbitrary parameter
  labels would be redacted to duplicate IDs. New profile cases use safe numeric
  labels; collection proves30 unique sanitized IDs before fixtures execute.

<a id="batch-b-migration-ci-scale-and-evidence-contracts"></a>
## Migration, CI, scale and evidence contracts

The complete executable proposal is [RELEASE_VALIDATION.md](../RELEASE_VALIDATION.md).
New runtime dependencies: **none**. External owner prerequisites: reviewed k6,
psql/PostgreSQL for approved local execution; Docker/sudo/nsenter and action
dependencies on GitHub-hosted CI. No install or remote resolution occurred here.
New migrations in Batch B: **none**; preserved Batch A0006 remains unexecuted.

0006 is additive: optional participant_profiles with user PK/FK, bounded skills,
zone syntax, opt-in/zone consistency and positive version checks. Existing users
need no row/backfill; profile GET yields empty defaults. The PK supplies one
index. IANA semantics are validated by application zoneinfo, not SQL syntax.
No data/grant/old-table change or automatic downgrade. New migration ownership
keeps all12 old-table locks/fingerprints and DDL in one transaction, comparing
content/counts before commit. Ordinary failures roll back; ambiguous commits
require approved read-only inspection. Live PostgreSQL DDL/retained-data safety
remains unverified despite offline rendering and synthetic rollback tests.

CI matrix uses isolated PostgreSQL16 services at exact0003 (18auth-api+35team-api),
0004 (35admission),0005 (13invitations+10lifecycle+4realtime),0006 (30profiles).
The invitation suite includes the distinct-authenticated50-caller last-seat race.
Native exit0, exact expected counts, no skips/failures, all teardowns and invariant
certificate are mandatory. Missing reports/artifacts fail; source-bound CI
receipts include each step's native code and sanitized report. Public CI execution
is NOT RUN. Syntax validated as strict JSON, a YAML1.2 subset; Actions runtime,
expressions, service container namespace and platform compatibility remain open.

Scale generator is bounded/deterministic (defaultseed2026):10000 participants,
2000 teams,5000 unique memberships,5000 unassigned,8000 discoverable. Skills/zones
vary; IDs, leader/roster/capacity, identity mappings and profiles are checked before
commit. All application tables must be empty under exclusive locks. Direct initial
fixture SQL obeys unchanged constraints, with no fake audit/mutation history.
No truncate/delete/adoption; merge_bench only. Receipt records counts/dataset hash.

Benchmark uses100 authenticated constant k6 VUs,20s warmup,60s measurement,5s
graceful tail; reports board p50/p95/p99/error/count/elapsed throughput, strict
p95<200ms and zero errors. Optional32 actual SSE consumers provide a comparison
against0; fixed GET-only loopback host and preflight scope/dataset attestation
prevent accidental other-target load. Real session/KDF bootstrap is outside the
measurement, with no login throttle relaxation. Hardware/topology/cache fields,
actual PostgreSQL/k6 versions, outbox row count and source hashes are captured.
Missing/inconsistent metrics and exit99 fail. Synthetic metrics in offline tests
are fixtures only. No actual throughput/percentile result exists from this task.

The fixture begins with empty outbox history and measures a warm first-page board
read workload. It cannot establish mutation-heavy SSE history, other board pages,
ranking throughput, production TLS, browser/mobile/keyboard or multi-instance
capacity. Those conditions require additional separately approved real evidence.

<a id="batch-b-owner-explanation-and-exercise"></a>
## Owner explanation and exercise

Version isolation preserves old certificates: each legacy suite still requires
its original schema; the new profile suite receives a different fixed database.
The migration owns both DDL and preservation checks. The benchmark owns an empty
disposable database and cannot address retained targets. Receipts certify only
unchanged source plus complete successful native results, not execution by an
independent authority. No destructive rollback is silently automated.

Offline exercise: change the synthetic p95 in test_release_support.summary to201
and explain why exit0 must be rejected while k6 exit99 produces an uncertified
threshold result. Alternatively remove a collected profile case and observe the
30-case roster contract fail before database fixture execution. Restore the edit
and rerun focused tests; never experiment with retained DB fixtures.

<a id="batch-b-actual-offline-evidence"></a>
## Actual offline evidence

Environment: Windows PowerShell, existing Python3.11.9 virtualenv, Node22.15.0,
npm10.9.2 and installed locked tooling. No dependency installation, PostgreSQL
connection, migration execution, live HTTP/browser/service, k6 workload or remote
action. In-process TestClient tests use fake engines only. One existing
Starlette/httpx deprecation warning remains; no dependency change was justified.

| Actual command (backend unless specified) | Outcome |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest tests/test_release_support.py -q --tb=short` | Final67 passed,4.85s, exit0 |
| `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short` | Final1622 passed,32 deselected,59.01s, exit0 |
| `npm test -- --reporter=dot --maxWorkers=1` (frontend) | 394 passed,15 files,59.51s, exit0 |
| `npm run build` (frontend) | `tsc --noEmit` passed; Vite build passed,50 modules,2.06s, exit0 |
| `.\.venv\Scripts\python.exe -m pytest profile_tests --collect-only -q --confirm-profile-test` | 30 collected only; final focused test also proves30 unique sanitized node IDs |
| `.\.venv\Scripts\python.exe -m pytest DIRECTORY --collect-only -q --confirm-merge-test --race-repetitions=1` (separate process per directory) | auth_api_tests18; team_api_tests35; admission_tests35; invitation_tests13; lifecycle_tests10; realtime_tests4; each exit0, none executed |
| `node --check load/board.js` (root) | passed, exit0; k6 runtime NOT RUN |
| Migration SQL rendering / graph and CI JSON-YAML syntax contracts | passed inside full/focused suites; no engine/DDL execution |
| `python test-results/batch-b/final_review.py` (ignored local review helper) | exit0;40 changed Python files parse;0006 sole migration head; strict JSON syntax;73-path inventory;47 Batch A hashes preserved plus4 documentation overlays; no high-confidence secret-pattern/artifact/whitespace findings |
| `git -c safe.directory=I:/Merge diff --check` (root) | passed, exit0; separate scan also checks trailing whitespace in new files |

The first focused run had52 pass/1 fail: the fake benchmark TestClient peer was
the non-IP default `testclient`, correctly rejected by unchanged client identity
validation. The fixture now explicitly uses loopback; subsequent focused runs
passed53,54,64,66 and final67 as coverage was added. This was a tooling fixture
defect, not a production permission bypass. Initial full backend before final
roster coverage passed1619; final1622 supersedes it. No failed assertion was
deleted or weakened. Frontend historical parallel failures remain in Batch A logs.

Ignored logs: `backend/test-results/batch-b/backend-full.log`, `backend-final.log`,
`collect-*.log`; `frontend/test-results/batch-b-frontend.log`, `batch-b-build.log`.
Baseline patch/hashes and final offline source/check metadata are retained in
backend/test-results/batch-b. No fake successful live receipt is generated.

<a id="batch-b-full-changed-file-inventory"></a>
## Full changed-file inventory

Combined tree: main at abfea1a6116dbe0295b45d21e290c56f84a91eb5;29 modified
tracked files +44 new files =73 paths, all unstaged. No deleted file, commit or
push. Batch B adds22 files; the original51 Batch A paths are retained. Batch B
changes only4 existing documentation files (ARCHITECTURE, DECISIONS, PROGRESS,
TEST_DATABASE). All47 other Batch A files match the captured starting hashes.

Modified tracked paths (29, including preserved Batch A changes):

```text
backend/app/admission_api.py
backend/app/invitation_api.py
backend/app/main.py
backend/app/models/__init__.py
backend/app/services/admission.py
backend/app/services/invitations.py
backend/test_support/browser.py
backend/test_support/browser_full.py
backend/test_support/concurrency.py
backend/tests/test_read_api.py
backend/tests/test_team_api.py
backend/tests/test_test_database_safety.py
docs/ADMISSION.md
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/FRONTEND.md
docs/INVITATIONS.md
docs/PROGRESS.md
docs/SCHEMA.md
docs/TEST_DATABASE.md
frontend/src/App.tsx
frontend/src/api.ts
frontend/src/components/Admission.tsx
frontend/src/components/AuthForm.tsx
frontend/src/components/Discovery.tsx
frontend/src/components/Invitations.tsx
frontend/src/components/Lifecycle.tsx
frontend/src/hooks/useRead.ts
frontend/src/style.css
```

New paths from Batch B (22):

```text
.github/workflows/ci.yml
backend/profile_tests/conftest.py
backend/profile_tests/test_profiles.py
backend/release_alembic/env.py
backend/release_support/__init__.py
backend/release_support/acceptance.py
backend/release_support/benchmark_host.py
backend/release_support/ci.py
backend/release_support/evidence.py
backend/release_support/load.py
backend/release_support/migrations.py
backend/release_support/realtime_acceptance.py
backend/release_support/seed.py
backend/release_support/targets.py
backend/release_support/verify.py
backend/tests/test_release_support.py
docs/BATCH_B.md
docs/RELEASE_VALIDATION.md
load/board.js
load/environment.example.json
scripts/provision_merge_bench.sql
scripts/provision_merge_profile_test.sql
```

Preserved new Batch A paths (22):

```text
backend/alembic/versions/0006_profiles.py
backend/app/models/profiles.py
backend/app/profile_api.py
backend/app/profile_models.py
backend/app/realtime_api.py
backend/app/services/matching.py
backend/app/services/profiles.py
backend/app/services/realtime.py
backend/realtime_tests/conftest.py
backend/realtime_tests/test_realtime.py
backend/tests/test_product_labels.py
backend/tests/test_profiles_matching.py
backend/tests/test_realtime.py
docs/BATCH_A.md
docs/RANKING.md
docs/REALTIME.md
frontend/src/BatchCompatibility.test.tsx
frontend/src/ProfilesRanking.test.tsx
frontend/src/Realtime.test.tsx
frontend/src/components/Profile.tsx
frontend/src/components/Rankings.tsx
frontend/src/hooks/useRealtime.ts
```

<a id="batch-b-remaining-release-gates"></a>
## Remaining release gates

Owner approval and successful execution are required for exact0005 SSE4; new
target provisioning/preparation/0006 preservation and profile30; actual public
Actions run with all matrix artifacts and50-caller race; verified10k/2k seed;
100-VU baseline/SSE comparisons with actual environment and p95<200ms. Then real
browser reconnect/lifecycle/ranking/mobile/keyboard and deployed HTTPS smoke
acceptance, repository/live URL, measured load report, one-page design and video
remain submission work. No public CI/performance/deployment readiness is claimed.
The deadline remains2026-11-15 23:59 IST. Stop for owner review; no live operation
is implied by this preparation.


---

<a id="batch-c"></a>

<a id="batch-c-batch-c--production-and-submission-preparation"></a>
# Batch C — production and submission preparation

Pre-implementation contract, 2026-11-14. Preparation only; no database access,
migration, service/browser startup, load, remote action, publication or commit.
Baseline main HEAD: abfea1a6116dbe0295b45d21e290c56f84a91eb5, 73 pending paths
(29 modified / 44 new), index empty. Preserve hashes/patch in ignored batch-c.

Bounded work in dependency order:

1. Inspect existing config/auth/peer/cookie/CSRF/runtime and propose production ADR.
2. Add app/production plus a separate production_alembic environment. Fixed
   merge_prod database, separate merge_runtime / merge_migrator roles, private
   container topology, secret files, startup schema/role/readiness checks. Never
   broaden Settings, test/release guards or existing service/locking contracts.
   Reuse Batch B preservation snapshots for an explicitly approved migration.
3. Add reviewed Docker/Compose/Caddy packaging, distinct initialization/migration
   actions, persistent PostgreSQL/certificate storage and offline unsafe-config
   regressions. No automatic migration, seed, cleanup or fallback target.
4. Replace stale README; add production runbook, one-page design, five-minute
   demo script and link-ready evidence/submission checklist. Label all live gaps.
5. Review required UI flows, names, mobile/keyboard semantics from source/tests;
   change UI only for a demonstrated release blocker. No redesign/name search.
6. Run focused config/package tests, full database-free backend, single-worker
   frontend, TypeScript production build, syntax/secret/artifact/diff checks;
   record exact results, combined inventory and next owner actions.

Acceptance: imports/config checks connect nowhere; invalid targets/origins/proxy
trust/secrets fail closed; production never loads local Settings or migrates at
startup; security uses the existing AuthBoundary/session/CSRF policy. Same-origin
compiled React and API/SSE use one HTTPS ingress with one sanitized proxy hop.
Production packaging runtime, TLS, volumes, privileges and live transport require
owner execution; offline tests cannot certify deployment or performance.

<a id="batch-c-implementation-and-review-outcome"></a>
## Implementation and review outcome

Recommendation: **CONDITIONAL for owner review**, not approved public release.
No database, migration, service/browser, load, deployment, remote, commit or push
action occurred. Production commands are proposals only. All existing Batch A/B
code, tests, CI, migration0006 and retained manifests/evidence remain preserved;
only current architecture/decision/progress documentation receives overlays.

The proposed platform is a Docker-capable Ubuntu24.04 VPS with direct DNS and one
HTTPS ingress: Caddy/static React -> single FastAPI worker -> private PostgreSQL17.
No current provider price/free-tier/availability claim is made. The production
configuration is intentionally separate from local Settings and every exact-version
test/release target. Runtime/migrator identities cannot select merge_dev/merge_test,
accept an arbitrary DSN, use a loopback/public DB endpoint, trust an arbitrary proxy
or inherit MERGE_AUTH_* relaxation. No CORS/auth/session/locking protocol is added.

Production imports perform no database action. Factory configuration loads mounted
secrets explicitly. Lifespan preflights fixed DB/server/role, nonprivileged role
flags/no memberships, no database CREATE/TEMP, required schema rights, actual
transaction defaults, writable primary and exact0006. Readiness checks table/grant
inventory in bounded SQL; engine disposes on startup failure and shutdown.
Startup has no role/DDL/catalog/seed side effect. Runtime dependency override
prevents lazy local Settings fallback. Uvicorn keeps real socket peer, one worker,
no forwarded-header middleware/access log, fixed sanitized logging and20s shutdown.

Roles/secrets are separated. Runtime has no DDL/TRUNCATE or history UPDATE/DELETE;
membership DELETE supports lifecycle. UPDATE on identity columns is explicitly
required by existing row-lock statements. Migrator owns tables/functions. Bootstrap
requires a fresh role/schema namespace; preparation/0005->0006/verification/catalog
are separate explicit operation-profile actions. The new migration environment
uses an owned production transaction and reuses Batch B's12-table preservation
snapshot, without editing or broadening Batch B guards. No new migration is added;
existing0006 remains unapplied. Native role/grant/migration behavior is unverified.

Private production files are create-only, Linux-root-owned directory0700 with
API-readable secret files0400/UID10001; they are Git/build-context excluded. API
does not receive admin/migration secrets. PostgreSQL and certificates use named
volumes. No volume deletion, destructive downgrade, fixture cleanup or reset is
provided. Fixed proxy configuration replaces forwarding headers, protects internal
readiness, serves same-origin assets/API, preserves private cache headers and
requests immediate SSE flush without compression. Existing60s leases fit its75s
stream ceiling. Actual proxy/TLS/ownership/volume/grace behavior needs rehearsal.

Zero Python/npm dependency or lockfile changes. The image currently installs the
existing complete Python lock (including development tooling); a slimmer reviewed
runtime lock is future work. Base image digests and current advisories must be
reviewed after separately approved pulls/builds; no native image/security scan ran.
The private single-host DB TCP leg is unencrypted and not publicly routable.

<a id="batch-c-submission-and-ux"></a>
## Submission and UX

README now describes real workflows, correctness/security, offline setup,
production separation and precise evidence limits. DESIGN_ONE_PAGE.md is a398-word
technical source covering data/transactions/locks/idempotency/audit/outbox, SSE,
70/30 deterministic ranking, G1 scope, trade-offs and extra-week plan; exported
pagination still needs checking. DEMO.md supplies a4:50 script with ordered fresh
account actions, expected state, proof/fallback capture checklist and disclosure
rules. No video or screenshot is fabricated or claimed. SUBMISSION.md holds
explicit PENDING public links and the full approval/execution order.

Reviewed AuthForm, Discovery, Admission, Invitations, Lifecycle, Profile, Rankings,
Feedback and responsive CSS/test journeys. Applicants/inboxes/rankings expose
human-readable names, usernames/team labels and score components. UUID lookup
and advanced recipient entry are retained; full-catalog name search/email delivery
remain absent. Native buttons/forms, labels/descriptions, visible focus/skip link,
validation focus, status regions, reduced motion, narrow-screen stacking and long
label wrapping are present in source. This is offline semantic review, not rendered
mobile/keyboard/assistive-technology certification. No demonstrated product blocker
justified modifying any Batch A frontend file. Existing tests/timeout assertions
are unchanged; flakes are reported below, including a new single-worker failure.

<a id="batch-c-risks-and-exact-next-owner-actions"></a>
## Risks and exact next owner actions

Start with review of the complete combined diff. Approve Batch B live scopes
separately: exact0005 SSE4; new profile target/migration/profile30; isolated CI;
disposable10k/2k seed and100-VU benchmark. Then approve source commit/publication,
image/advisory review and production-topology rehearsal on an isolated host.
Native Docker/Caddy validation is required: neither binary is installed here.
Rehearsal must prove secret ownership, restricted runtime grants, migrations,
actual HTTP flows and shutdown; mocked tests cannot certify PostgreSQL permissions.
Production launch additionally needs approved VPS/DNS/firewall, backup/restore,
private secrets/catalog, TLS/cookie/CSRF/proxy/SSE/ranking/lifecycle browser smoke
and mobile/keyboard evidence. First deployment has no known-good production image;
rollback stops ingress/API and retains data. Subsequent rollback uses a compatible
reviewed API+web image pair with0006 retained, never a destructive downgrade.
Detailed commands: PRODUCTION.md; complete submission gates: SUBMISSION.md.

Unresolved release risks include mutable/unbuilt base images, Linux dependency
installation/native configuration, unrun production grants and restore drill,
one-host failure domain/no monitored SLA, idle-only benchmark seed history,
unmeasured retained-outbox/ranking cost, flaky frontend loading tests, missing
public CI/load/deployment/video links and unverified real browser accessibility.
The deadline is unchanged; no successful release/submission is inferred.

<a id="batch-c-owner-explanation--exercise"></a>
## Owner explanation / exercise

Production isolation keeps test certificates meaningful: no old guard gains a
remote/production exception. A runtime cannot create schema; the separate migration
owner checks preserved rows before commit. Caddy is the sole trusted hop, so its
header replacement and disabled Uvicorn proxy handling are both necessary. An
offline exercise: change the synthetic compose API to publish8000 or change the
trusted proxy address; run test_production.py and explain why the contract fails.
Restore the edit. Explain why a healthy process is not a healthy schema, and why
ordinary merge_dev startup is never a production recovery command.

<a id="batch-c-actual-offline-results-and-limits"></a>
## Actual offline results and limits

Environment: Windows PowerShell, existing Python3.11.9 venv, Node22.15.0,
npm10.9.2, locked existing pytest/Vitest/TypeScript/Vite. No package installation
or network activity. TestClient uses synthetic engines/services, not a listening
server; SQL rollback/permission fixtures are synthetic and prove tooling only.
One existing Starlette/httpx deprecation warning remains.

| Actual command | Result |
| --- | --- |
| backend: `.\.venv\Scripts\python.exe -m pytest tests/test_production.py -q --tb=short` | final89 passed,2.38s, exit0 |
| backend: `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short` | final1711 passed,32 deselected,83.11s, exit0 |
| backend: `.\.venv\Scripts\python.exe -m app.production.check` | JSON/topology/security contracts passed, exit0; no engine/network |
| frontend: `npm test -- --reporter=dot --maxWorkers=1` | first393 passed/1 failed,61.18s, exit1; isolated unchanged rerun394 passed/15 files,44.66s, exit0 |
| frontend: `npm run build` | tsc --noEmit passed; Vite50 modules,1.77s, exit0 |
| Migration/CI consistency |0006 sole Alembic head, production REVISION matches it and CI matrix includes it; tested offline |
| Deployment syntax/contracts | Compose/Caddy strict JSON parsed; Dockerfile fixed packaging/grant/proxy/secret contracts pass unit tests; native Docker/Caddy validation NOT RUN (unavailable) |
| Submission links/design | local Markdown links resolve; design398 words; exported one-page rendering NOT RUN |
| backend: `python test-results/batch-c/final_review.py` (ignored local helper) | exit0;52 changed Python files AST-parse; Dockerfile instruction/JSON-CMD checks;97-path inventory;70 starting hashes preserved plus3 doc overlays; no targeted secret/artifact/whitespace/link findings |
| root: `git -c safe.directory=I:/Merge diff --check` | passed, exit0; separate trailing-whitespace scan covers new files too |
| root: `git -c safe.directory=I:/Merge check-ignore deploy/private/caddy.json` and `node --check load/board.js` | both exit0; no private directory created or k6 run |

Initial production-focused run had70 passes/13 failures from one malformed new
Caddy JSON closing bracket. Corrected syntax, then83 passed. Expanded bounded
readiness tests passed86, proxy cookie/CSRF test87. Cross-platform secret hardening
found one fixture failure (88 pass/1 fail): Windows write_text produced CRLF while
the Linux-only production helper writes LF. Corrected the valid fixture to write
exact LF bytes, retaining strict CRLF rejection; final89 pass. No failing test was
removed or weakened. Earlier full backend1709 passed before the two new primary/
read-only rejection cases; final1711 supersedes it.

The frontend failure is the unchanged lifecycle confirmation test waiting for
initial Test Challenge discovery. Its source and timeout are unchanged; previous
A/B parallel timing failures and this one-worker failure remain unresolved. The
isolated pass is recorded, not treated as proof of a fixed root cause. No frontend
source/test/config change was made.

Ignored evidence: backend/test-results/batch-c/baseline.json and baseline.patch,
production-focused.log, production-focused-final.log, backend-final.log; frontend/
test-results/batch-c-frontend.log (failed), batch-c-frontend-standalone.log (passed),
batch-c-build.log. Final source hashes/static inventory/check metadata are retained
in ignored batch-c/offline-review.json. No successful live receipt was invented.

<a id="batch-c-complete-combined-inventory-and-git-status"></a>
## Complete combined inventory and Git status

main / abfea1a6116dbe0295b45d21e290c56f84a91eb5;31 modified tracked +66 new
files =97 paths, index empty. No deleted file or commit/push. Batch C adds22
files and changes README/.gitignore plus3 existing documentation overlays. All70
other starting Batch A/B paths match their captured hashes; all executable A/B
code/tests/CI/0006 are preserved. The historical Batch B inventory retains its
checkpoint scope. No new dependency or migration.

Modified tracked paths (31):

```text
.gitignore
README.md
backend/app/admission_api.py
backend/app/invitation_api.py
backend/app/main.py
backend/app/models/__init__.py
backend/app/services/admission.py
backend/app/services/invitations.py
backend/test_support/browser.py
backend/test_support/browser_full.py
backend/test_support/concurrency.py
backend/tests/test_read_api.py
backend/tests/test_team_api.py
backend/tests/test_test_database_safety.py
docs/ADMISSION.md
docs/ARCHITECTURE.md
docs/DECISIONS.md
docs/FRONTEND.md
docs/INVITATIONS.md
docs/PROGRESS.md
docs/SCHEMA.md
docs/TEST_DATABASE.md
frontend/src/App.tsx
frontend/src/api.ts
frontend/src/components/Admission.tsx
frontend/src/components/AuthForm.tsx
frontend/src/components/Discovery.tsx
frontend/src/components/Invitations.tsx
frontend/src/components/Lifecycle.tsx
frontend/src/hooks/useRead.ts
frontend/src/style.css
```

All new paths (66; includes preserved A/B files):

```text
.dockerignore
.github/workflows/ci.yml
backend/alembic/versions/0006_profiles.py
backend/app/models/profiles.py
backend/app/production/__init__.py
backend/app/production/application.py
backend/app/production/bootstrap.py
backend/app/production/check.py
backend/app/production/config.py
backend/app/production/database.py
backend/app/production/grants.py
backend/app/production/migrate.py
backend/app/production/prepare.py
backend/app/production/serve.py
backend/app/profile_api.py
backend/app/profile_models.py
backend/app/realtime_api.py
backend/app/services/matching.py
backend/app/services/profiles.py
backend/app/services/realtime.py
backend/production_alembic/env.py
backend/profile_tests/conftest.py
backend/profile_tests/test_profiles.py
backend/realtime_tests/conftest.py
backend/realtime_tests/test_realtime.py
backend/release_alembic/env.py
backend/release_support/__init__.py
backend/release_support/acceptance.py
backend/release_support/benchmark_host.py
backend/release_support/ci.py
backend/release_support/evidence.py
backend/release_support/load.py
backend/release_support/migrations.py
backend/release_support/realtime_acceptance.py
backend/release_support/seed.py
backend/release_support/targets.py
backend/release_support/verify.py
backend/tests/test_product_labels.py
backend/tests/test_production.py
backend/tests/test_profiles_matching.py
backend/tests/test_realtime.py
backend/tests/test_release_support.py
deploy/Dockerfile.api
deploy/Dockerfile.web
deploy/caddy.template.json
deploy/compose.json
docs/BATCH_A.md
docs/BATCH_B.md
docs/BATCH_C.md
docs/DEMO.md
docs/DESIGN_ONE_PAGE.md
docs/PRODUCTION.md
docs/RANKING.md
docs/REALTIME.md
docs/RELEASE_VALIDATION.md
docs/SUBMISSION.md
frontend/src/BatchCompatibility.test.tsx
frontend/src/ProfilesRanking.test.tsx
frontend/src/Realtime.test.tsx
frontend/src/components/Profile.tsx
frontend/src/components/Rankings.tsx
frontend/src/hooks/useRealtime.ts
load/board.js
load/environment.example.json
scripts/provision_merge_bench.sql
scripts/provision_merge_profile_test.sql
```

New Batch C files (22) are .dockerignore; ten app/production modules;
production_alembic/env.py; tests/test_production.py; four deploy files; BATCH_C,
PRODUCTION, DESIGN_ONE_PAGE, DEMO and SUBMISSION documents. Runtime/domain/frontend
services and legacy targets are unchanged. STOP for owner review before live
actions or commit.


---

<a id="batch-d-recovery"></a>

<a id="batch-d-recovery-batch-d-diagnostic-recovery-and-release-triage"></a>
# Batch D diagnostic recovery and release triage

2026-11-15. Deadline: **15 November 2026, 23:59 IST**. This work implements and
tests offline diagnostics; it does not certify live startup or authorize any live
operation. No database, host/browser, fixture, Git publication or deployment action.

<a id="batch-d-recovery-diagnostic-correction-and-limits"></a>
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

<a id="batch-d-recovery-permanently-consumed-campaign"></a>
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

<a id="batch-d-recovery-historical-postgresql-evidence-reviewed-without-connection"></a>
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

<a id="batch-d-recovery-fresh-campaign-decision"></a>
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

<a id="batch-d-recovery-production-triage-and-minimum-release-checklist"></a>
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

<a id="batch-d-recovery-offline-evidence"></a>
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


---

<a id="batch-e-release"></a>

<a id="batch-e-release-batch-e-local-freeze-and-public-delivery-handoff"></a>
# Batch E local freeze and public delivery handoff

15 November 2026; deadline **23:59 IST**. Application code is frozen. Batch E
reviews the existing changes and runs offline checks, then creates exactly the
one owner-authorized local commit if staged gates pass. No remote/DB/service,
benchmark, provisioning, deployment or submission-form operation is performed.
Commit message: `chore(release): finalize application acceptance tooling`.
The actual hash belongs in the final response/ignored receipt after creation;
it cannot be embedded self-referentially in this commit's source.

<a id="batch-e-release-complete-starting-path-review"></a>
## Complete starting-path review

Starting main: `db17f3ef2c2934d2d4cc7db06499a291949a3d16`; 39 pending paths,
none staged. Every candidate is text source, tests, public plan or docs. No
credential, raw diagnostic, dump, binary, build output or installed dependency
belongs in the commit. This handoff and finalization of the previously clean
DEMO.md add two paths: **41 reviewed commit paths**. README/PROGRESS/SUBMISSION
updates are within the starting inventory. No feature, runtime-source, dependency
or migration change is made in Batch E.

Paths below are repository-relative; abbreviated sibling names use the nearest
preceding directory. The staged manifest records every full path and blob identity.

| Reviewed files | Disposition / reason |
| --- | --- |
|README.md; docs/DESIGN_ONE_PAGE.md; PROGRESS.md; RELEASE_VALIDATION.md; SUBMISSION.md|Honest current status, historical evidence/provenance and owner gates; old commands grant no new live permission.|
|frontend/src/api.ts|Specific 409 messages; transport/session/command behavior preserved.|
|frontend/src/components/Admission.tsx; Invitations.tsx|Named accessible actions/less duplicate feedback; UUID targets and uncertain recovery retained.|
|frontend/src/components/HealthStatus.tsx|Liveness wording does not claim account/domain readiness.|
|frontend/src/components/Lifecycle.tsx|Cancel restores focus; leadership loss withdraws unsubmitted removal; backend remains authoritative.|
|frontend/src/components/Profile.tsx|Only definite 422/invalid_request permits draft correction; unknown/CAS failures require reload; accessible errors.|
|frontend/src/App.test.tsx; DiscoveryNavigation.test.tsx; ProductAudit.test.tsx|Relevant UI regressions, actual effect/fetch synchronization and no unintended mutation.|
|acceptance/integrated-campaign.json|Public planned scope/budgets; consumed namespace remains preserved, not reusable.|
|backend/release_support/integrated_plan.py; integrated_ledger.py|Closed plan/target, exact 38-POST/14-effect protocol, one active command and no unknown-outcome retry.|
|backend/release_support/integrated_host.py; integrated_diagnostics.py|Fixed isolated target, nine service overrides/closed dependency audit; secret-free aggregate diagnostics.|
|backend/release_support/integrated_run.py; integrated_observer.py; integrated_certify.py|CreateNew fence, native exits, mandatory drain/ledger/observer, prior-row checks and hash-bound observations.|
|backend/release_support/profile_inspection.py; profile_inspection_capture.py; scripts/inspect_merge_profile_0005.ps1|Owner-only SELECT snapshot, hidden credentials and exclusive native/source capture. Historical 0005 tool, not a reason to rerun it on now-0006 profile state.|
|backend/tests/test_integrated_diagnostics.py; test_integrated_host.py; test_integrated_evidence.py; test_integrated_plan.py|Synthetic lifecycle/ASGI/evidence/ledger tests, live-operation traps and tamper/failure cases.|
|backend/tests/test_profile_inspection_auth.py; test_profile_inspection_capture.py|Hidden-input, persistence, source/native and tamper regressions; no real inspection in tests.|
|frontend/test_support/integratedCampaign.js; integratedCampaign.test.js; integratedEvidence.mjs; integratedEvidence.test.js|Offline budget/scope and owner-observation integrity checks; outside production src; no browser or credentials.|
|[historical batch d recovery review](ENGINEERING_HISTORY.md#batch-d-recovery); INTEGRATED_ACCEPTANCE.md; INTEGRATED_HOST.md; [historical product audit review](ENGINEERING_HISTORY.md#product-audit)|Contracts, offline results and historical failure boundaries. Current overlays supersede stale checkpoint status, not evidence.|
|docs/DEMO.md; [historical batch e release review](ENGINEERING_HISTORY.md#batch-e-release) (freeze additions)|Final <=5-minute script, concrete future commands and delivery checklist.|

All historical receipts/markers and both old browser hosts stay byte-identical.
Ignored evidence/logs stay local. Authentication, transactions, locks, constraints,
audit/outbox, mutation budgets and final observer requirements are not weakened.

<a id="batch-e-release-safeguards-and-proof-limits"></a>
## Safeguards and proof limits

Server-validated sessions/current CSRF, exact Origin/Fetch Metadata and durable
login/invite throttles remain. PostgreSQL and the existing transaction owner
enforce membership/capacity/leadership/idempotency; process counters grant nothing.
Production fixes merge_prod, separate restricted runtime/migration roles, exact
0006_profiles and one trusted Caddy peer, without Settings/merge_dev fallback.

Production uses app.production.serve and its separate factory. Production app
and frontend src import no integrated host/diagnostics/ledger or inspection tool.
Dockerfile.api copies only the four existing migration-related release_support
helpers, not integrated tooling/test_support. A harness failure is not a proven
production startup defect. Native containers, grants and TLS remain unverified.

Historical local PostgreSQL results: profile 30/30, SSE 4/4, lifecycle 10/10;
provenance limits remain in [historical batch d recovery review](ENGINEERING_HISTORY.md#batch-d-recovery)/LIFECYCLE.md. These are not new
source, production-role, public CI or HTTPS certificates. A commit changes HEAD;
never rewrite old receipts or loosen full-source eligibility to make them current.

Campaign `17ff1152-1ac0-4ace-a887-13436dd2963f` remains permanently consumed and
uncertified: browser checkpoints 0/13 (owner baseline), saved POST/domain counters
0, readiness/exact failed drain check unknown, no final observer. Zero POSTs does
not certify database-wide preservation. No campaign retry/adoption/reset is part
of the release or deployment proposal.

<a id="batch-e-release-github-publication-prerequisites-and-exact-proposal"></a>
## GitHub publication prerequisites and exact proposal

Local findings: author identity configured; only sample Git hooks; no remote;
GitHub CLI absent. No credential store/account/token or authenticated remote was
queried. Owner authentication is **unverified**. GitHub CLI is optional: a later
approved HTTPS push may use Git for Windows credential-manager/browser sign-in.

Owner must choose account/repository, authorize publication of the reviewed
history/workflow and have rights to publish both. Create an EMPTY public repo
without initial README/license/gitignore. Enable Actions/hosted Linux runner
access. Never place a password/PAT into a remote URL, command or retained log.

**Future PowerShell, NOT EXECUTED.** Replace placeholders with the owner-approved
public account/repository. Remote setup and push each require approval. Divergent
remote history is a stop; never force-push or merge automatically.

```powershell
Set-Location -LiteralPath 'I:\Merge'
$releaseCommit = git -c safe.directory=I:/Merge rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Cannot identify release' }
if (git -c safe.directory=I:/Merge status --porcelain) { throw 'Dirty release tree' }
if (git -c safe.directory=I:/Merge remote) { throw 'Review existing remote first' }
$publicRepository = 'https://github.com/OWNER/REPOSITORY.git'
if ($publicRepository -match '/OWNER/|/REPOSITORY\.git$') { throw 'Set approved repository URL' }
# APPROVAL G1: configure this credential-free public remote.
git -c safe.directory=I:/Merge remote add origin $publicRepository
if ($LASTEXITCODE -ne 0) { throw 'Remote configuration failed; stop' }
# APPROVAL G2: publish reviewed main history and trigger its workflow.
git -c safe.directory=I:/Merge push -u origin main
if ($LASTEXITCODE -ne 0) { throw 'Publication failed; stop without force/retry' }
```

Review the actual public URL and Actions run at the same commit. The workflow has
read-only repository permissions and isolated PostgreSQL 16 services at four exact
revisions. Its wrapper requires GitHub-hosted CI and enters the service network
namespace; it refuses local/retained target adoption.

| Revision | Required suites |
| --- | --- |
|0003_auth|18 authenticated auth API + 35 team creation API cases.|
|0004_admission|35 admission cases.|
|0005_invitations|13 invitation API cases including test_distinct_authenticated_50_caller_last_seat; lifecycle 10; realtime 4.|
|0006_profiles|30 profile cases.|

The race uses 50 distinct actors/sessions/CSRF values, gates after actual HTTP
authentication, observes PostgreSQL overlap and checks winner/rejections,
invariants and exact replay. Source coverage is verified; **no public Actions pass
is claimed**. Require every job green, no skipped/failed acceptance cases and
complete native/source artifacts. Inspect sanitized artifacts before sharing;
automatic upload is not a privacy review. Do not publish a fabricated CI badge.

<a id="batch-e-release-hosting-prerequisites-and-shortest-existing-route"></a>
## Hosting prerequisites and shortest existing route

Use the existing Caddy/static React -> one FastAPI worker -> private PostgreSQL
17 Linux single-host proposal. No alternative architecture is required. Docker,
Caddy and k6 are absent locally; native validation/image builds have not run.

Owner supplies approved VPS/SSH access, Docker/Compose, an owned domain and direct
DNS A/AAAA. Confirm costs/resources, subnet overlap, firewall, image provenance/
digests and fresh volumes/backups. Only 80/443 plus owner-restricted SSH are public;
API 8000/DB 5432 stay private. Fixed subnets are 172.30.240.0/29 and
172.30.241.0/29; sole trusted proxy is 172.30.240.2/32. No CDN/extra proxy is assumed.
Exact lower-case HTTPS origin has no path/port. Generate separate runtime,
migrator/admin DB password files and shared 32-byte throttle key with the existing
create-only helper; deploy/private is ignored. Retain Caddy certificate/config and
PostgreSQL volumes. Production restricted grants/readiness need real verification.

**Future Linux bash, NOT EXECUTED.** On the approved host obtain the actual frozen
revision; replace all placeholders. Each nonzero result stops. API startup never
initializes/migrates. These commands do not authorize provisioning or execution now.

```bash
set -euo pipefail
git clone 'https://github.com/OWNER/REPOSITORY.git' Merge
cd Merge
git checkout --detach 'OWNER_REVIEWED_RELEASE_COMMIT'
test -z "$(git status --porcelain)"
python3.11 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.lock
export MERGE_PROD_ORIGIN='https://REAL_OWNED_HOST'
export MERGE_IMAGE_TAG="$(git rev-parse HEAD)"
(cd backend && .venv/bin/python -m app.production.check)
# APPROVAL H1: create-only secrets and reviewed images/configuration.
(cd backend && sudo .venv/bin/python -m app.production.prepare \
  --confirm-new-secrets --origin "$MERGE_PROD_ORIGIN")
docker compose -f deploy/compose.json config --quiet
docker compose -f deploy/compose.json build api web
docker image inspect --format '{{.Id}}' "merge-api:$MERGE_IMAGE_TAG" "merge-web:$MERGE_IMAGE_TAG"
docker compose -f deploy/compose.json run --rm --no-deps --entrypoint caddy web \
  validate --config /etc/caddy/config.json
# APPROVAL H2: fresh production-only volume/roles/explicit migrations.
docker compose -f deploy/compose.json up -d postgres
```

STOP and verify PostgreSQL container health before continuing. Existing/partial
state is a stop for review, not cleanup/adoption/overwrite or automatic rerun.

```bash
set -euo pipefail
docker compose -f deploy/compose.json run --rm --no-deps bootstrap --confirm-new-merge-prod
docker compose -f deploy/compose.json run --rm --no-deps migrate prepare --confirm-merge-prod
docker compose -f deploy/compose.json run --rm --no-deps migrate migrate --confirm-merge-prod
docker compose -f deploy/compose.json run --rm --no-deps migrate verify --confirm-merge-prod
# APPROVAL H3: exactly one new approved demo catalog event.
docker compose -f deploy/compose.json run --rm --no-deps migrate catalog --confirm-merge-prod \
  --id OWNER_APPROVED_UUID --name 'Owner-approved demo hackathon' --min-size 2 --max-size 4
# APPROVAL H4: API launch; require actual /ready health before ingress.
docker compose -f deploy/compose.json up -d api
docker compose -f deploy/compose.json ps
```

STOP until API health/readiness is confirmed, then separately approve ingress:

```bash
docker compose -f deploy/compose.json up -d web
docker compose -f deploy/compose.json ps
```

Verify externally: valid TLS/redirect, React assets/deep links, restricted-role
auth/domain/profile workflows, Secure host-only cookie/CSRF/Origin/proxy policy,
two-client SSE/reconnect, keyboard/mobile. /health is liveness; /ready is internal
and blocked by Caddy. Retain actual URL/commit/image IDs/native exits and sanitized
smoke evidence. On failure stop web then API and retain volumes. Never down -v,
prune, reset or downgrade automatically. PRODUCTION.md contains full migration,
grant/backup/rollback semantics. No production pass exists here.

<a id="batch-e-release-performance-and-artifact-preparation"></a>
## Performance and artifact preparation

Reviewed seed/benchmark_host/load/board.js and their offline regressions. Seed:
exactly 10,000 users, 2,000 teams, 5,000 memberships and 10,000 profiles; deterministic,
atomic and empty-target-only, with true-row/identity/roster checks. Load: 100 real
authenticated clients, 20s warmup/60s measurement, board p95 <200ms, zero errors,
>=100 samples, real session setup before measurement and aggregate-only evidence.
Optional 32-SSE comparison is secondary to the mandatory baseline/public delivery.

Still missing: reviewed k6 installation, approved isolated exact-0006 merge_bench/
merge_bench_app, truthful hardware/cache/history disclosure, actual seed/load/native
outputs and report. Never load-test production/retained fixtures. After separate
provision/migration approvals in RELEASE_VALIDATION.md, the minimum **future
PowerShell proposals** in I:\Merge\backend are:

```powershell
.\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m release_support.seed --confirm-merge-bench --seed 2026
if ($LASTEXITCODE -ne 0) { throw 'Seed failed; retain state and stop' }
.\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m release_support.seed --confirm-merge-bench --seed 2026 --verify-only
if ($LASTEXITCODE -ne 0) { throw 'Seed verification failed; stop' }
# Approved foreground terminal 1; no transcript/piping of hidden input.
.\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m release_support.benchmark_host --confirm-merge-bench --seed 2026
# Approved terminal 2; complete private environment disclosure first.
.\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m release_support.load --confirm-merge-bench --seed 2026 --sse-clients 0 --environment test-results/bench-environment.json
if ($LASTEXITCODE -ne 0) { throw 'Load failed/incomplete; retain evidence and stop' }
```

Use load/environment.example.json's exact schema, not fabricated hardware values.
The report must include actual commit/revision/date, PG/k6 versions, topology/
resources/cache/outbox history, seed counts, workload/window, p50/p95/p99, errors,
requests/throughput, native exits and limits. Missing/failed outputs stay missing/
failed, including threshold exit 99. Never publish cohort passwords/cookies/CSRF
or headers. No benchmark was executed here and no percentile is invented.

Design export: open DESIGN_ONE_PAGE.md in a trusted local Markdown/document
renderer; export A4 portrait with roughly 14mm margins and readable 10–11pt body.
Verify the actual PDF is exactly ONE page, readable, unclipped and has current
evidence labels/links. Tighten wording/spacing if needed without omitting data
model, race prevention, trade-offs, extra-week plan or pending evidence. Source
length is not pagination proof. No renderer/browser/PDF export ran here.

DEMO.md targets 4:50/hard 5:00 on the same release with fresh separately approved
demo scope. Pause before credential entry, show actual results/score components,
review the whole exported recording/duration and public access, and never imply
that recording certifies the consumed campaign. No recording/publication ran.

<a id="batch-e-release-official-submission-checklist-and-missing-evidence"></a>
## Official submission checklist and missing evidence

This follows REQUIREMENTS.md's captured organizer specification and its official
challenge link. The live form was not opened or interacted with; current field
labels/options were not independently inspected.

- [ ] Individual/original PS1 work; owner can explain and live-modify it.
- [ ] Public GitHub URL for this revision, reproducible setup, honest README and
  successful Actions evidence with >=20 API tests and authenticated 50-caller race.
- [ ] Externally verified public HTTPS React/API URL, mobile/keyboard usability
  and real live-update/security/auditing/matching workflows.
- [ ] Actual 10,000-user/2,000-team evidence and 100-client board p95 <200ms load
  report with declared environment, native exits and reproducible script.
- [ ] Reviewed one-page design: data model, race prevention, trade-offs, extra week.
- [ ] Actual walkthrough <=5 minutes, no credentials/private data, public reviewer
  access without owner credentials.
- [ ] Enter actual repo/live/load/design/video links into the organizer workspace
  before 15 November 2026, 23:59 IST; verify access and retain the real submission
  confirmation/time. No form action or submission occurred in this task.

All public links and current CI/load/HTTPS/browser evidence remain missing.
Historical local PG certificates keep their original scope. A local commit and
offline build cannot establish deployment, performance or successful submission.

<a id="batch-e-release-freeze-evidence-and-next-owner-gate"></a>
## Freeze evidence and next owner gate

PROGRESS.md records exact new offline results. Ignored freeze directory:
backend/test-results/batch-e-freeze-8cd3dd0d101942f29f3ee99a9ecaf1d9/.
It holds starting source/evidence inventory, publication scan, new test/build logs,
staged path/blob manifest and the post-commit local receipt. The initial pre-stage
scan covered 302 source files and 603 reachable historical Git blobs, with no
high-signal secret tokens/private keys, suspicious artifact paths or oversized
unscanned blobs. This targeted review cannot guarantee unknown secret formats.

PASS applies only to verified local freeze gates. Public delivery remains
CONDITIONAL/BLOCKED on the concrete missing prerequisites above. Next protected
action: owner authentication and approval to create/select the public GitHub repo,
configure its credential-free remote and push main. No live action is implied.

Owner exercise: explain why a new commit cannot make an old full-source receipt
current, then trace the 50-caller case through the exact-0005 CI plan.


---

<a id="product-audit"></a>

<a id="product-audit-final-product-audit-and-simplification--2026-11-14"></a>
# Final product audit and simplification — 2026-11-14

Baseline: clean `main`, HEAD `db17f3ef2c2934d2d4cc7db06499a291949a3d16`,
confirmed locally. Scope: audit the existing PS1 product, fix demonstrated UI
defects in bounded components, and validate offline. No architecture, API,
authentication, transaction, database, dependency or deployment change.

<a id="product-audit-recommendation-and-scope-of-proof"></a>
## Recommendation and scope of proof

**CONDITIONAL for owner review; deployment approval is withheld.** Offline checks
do not complete the profile PostgreSQL or full browser acceptance gates. The
existing 0006_profiles migration remains unapplied. No newly discovered P0 code
defect was established in this source/component audit. The known migration
prerequisite prevents treating profile/ranking as a complete live workflow.

Owner-supplied baseline: SSE PostgreSQL acceptance 4/4, lifecycle 10/10, backend
offline 1719 and frontend offline 394. These historical live results were not
rerun or extended. Existing source-bound receipts keep their original scope;
changed frontend bytes need fresh browser evidence. Nothing here certifies a
public URL, CI run, scale seed, benchmark, TLS, production roles or submission.

<a id="product-audit-audit-findings"></a>
## Audit findings

P0 blocks a required journey or creates a security risk; P1 materially harms
correctness/usability; P2 is cosmetic or optional. Deferred items below are
deliberate limits, not verified defects silently marked fixed.

| ID | Priority | Proven finding / location | Resolution and evidence |
| --- | --- | --- | --- |
| G1 | P0 prerequisite | Profile/matching SQL needs unapplied 0006_profiles. | Known baseline release blocker, not corrected under the explicit no-database/no-migration instruction. Separate guarded profile acceptance required. |
| F1 | P1 | Every generic 409 became “That username is unavailable”, including profile CAS and ranking snapshot conflicts (`api.ts`). | Code-specific profile/ranking/username messages and a neutral unknown-conflict fallback. Four regression cases. |
| F2 | P1 | Exact server validation rejection disabled the entire profile until reload, which discards the draft (`Profile.tsx`). Browser Intl and server IANA support can differ. | Only exact 422/invalid_request permits correcting the retained draft at the same CAS version. Unknown failures/conflicts still require reload. Tests check no automatic retry, draft/version retention and reloaded version use. |
| F3 | P1 | Profile field errors were plain paragraphs, without alert semantics. | Keep associated descriptions and first-invalid-field focus; announce populated field errors. Component regression verifies alert/focus and no save. |
| F4 | P1 | Named inbox invitations still had UUID headings/action names; approval aria-labels spoke account UUIDs despite available applicant names. | Named team/applicant headings and accessible actions. Technical IDs remain in expandable reference details; old responses and uncertain-command recovery retain identifier fallbacks. Tests verify unchanged UUID command targets. |
| F5 | P1 | Cancel removed the focused membership button and left focus without a useful destination. Opening confirmation did not establish focus. | Opening focuses Cancel, avoiding accidental destructive activation. Cancel returns to its leave/remove trigger, with Manage membership as fallback. Both actions have component regressions. |
| F6 | P1 | An open removal confirmation survived a canonical change to another leader, despite removal controls disappearing. Server authorization still prevented an unauthorized mutation. | Hide and clear the unsubmitted removal confirmation on lost leadership. It cannot revive if leadership returns. Leave confirmations and command journals remain independent. Regression checks no mutation. |
| F7 | P2 | Successful redemption had both card-level and unconditional inbox-level success announcements. | Keep the summary only for successful commands absent from the current page. Present/absent-row tests verify one confirmation and preserve off-page feedback. |
| F8 | P2 | Footer called process liveness “healthy” and instructed participants to start the API. | State that the service responds, without claiming account/team access; give participant-facing failure/retry text. Existing network/HTTP/payload/JSON/timeout/retry tests retained. |
| D1 | P2 | Disabled creation form remains above each workspace view, even with known membership. | Deferred optional density reduction. It also hosts exact-command recovery and Start another team; no blanket removal or new navigation flow introduced. |
| D2 | P2 | UUID lookup/manual recipient fields are prominent and use technical vocabulary. | Retained functional fallbacks: no account search API exists, opt-in rankings intentionally exclude some recipients, and exact lookup crosses catalog pages. Collapsing these is optional polish. |
| D3 | P2 | Some roster pager/restart buttons use native styling; ranking reference time is raw ISO; brand “home” label targets the main-content anchor. | Deferred minor presentation/wording work. No dead link was found: both actual hrefs target the existing #main element. |
| D4 | P2 / verification | Real overflow, touch targets, focus announcements, contrast, zoom and keyboard traversal cannot be certified from jsdom/source. | Static review completed below. Full browser/mobile/assistive-technology checks remain pending; no browser/server was started. |

<a id="product-audit-bounded-implementation-contracts"></a>
## Bounded implementation contracts

1. Feedback/profile (`api.ts`, `Profile.tsx`, new component tests): distinguish
   conflict causes and recover a draft only on a known pre-write validation
   rejection. Keep CAS, session ownership and unknown-delivery reload rules.
2. Invitations/approvals (`Invitations.tsx`, `Admission.tsx`, new tests): names
   identify people/teams; UUIDs still identify every command internally. Remove
   duplicate presentation without changing eligibility, pagination or recovery.
3. Lifecycle (`Lifecycle.tsx`, new tests): explicit confirmation and useful
   keyboard focus; current leadership controls unsubmitted removal drafts. Keep
   the original lifecycle journal, locks, retries and confirmed outcomes.
4. Service wording (`HealthStatus.tsx`, `App.test.tsx`): describe the existing
   liveness-only endpoint accurately and retain all failure/retry tests.

Dependencies are the existing React/API DTOs and native controls. No package,
migration, backend source, service guard or public contract was changed.

<a id="product-audit-route-page-and-journey-coverage"></a>
## Route, page and journey coverage

The client is one App with local discover/mine/invitations/detail views and public
navigation hints; there is no client URL router. This audit inspected the
entrypoint, App, all eleven components, all nine hooks, API transport/parsers,
styles, index metadata and existing journey tests. Production import traversal
from main.tsx reached all 24 production TS/TSX/CSS files; no unused production
module was established. No file or existing test was deleted.

| Journey / UI | Existing API surface reviewed | Offline coverage / remaining boundary |
| --- | --- | --- |
| Register, explicit login, session restore and sign out | POST /auth/register, /auth/login, /auth/logout; GET /auth/session | Journeys, API, profile field validation and backend auth tests; no automatic auth retry, cookie/CSRF generation fencing retained. Real HTTPS/cookie interaction pending. |
| Profile edit/opt-in and explained ranking | GET/POST /api/me/profile; GET /api/hackathons/{h}/teams/{t}/suggestions | ProfilesRanking, ProductAudit, BatchCompatibility and backend profiles/matching tests; SQL/CAS/eligibility needs separate PostgreSQL acceptance at 0006. |
| Hackathon discovery and exact lookup | GET /api/hackathons | HackathonLookup, DiscoveryNavigation and read API tests cover bounded pages, missing/neighbor lookup and stale replies; name search remains outside scope. |
| Team board, details and own membership | GET /api/hackathons/{h}/teams, /teams/{t}, /me/team | Journeys, CreateTeam, navigation/read tests; canonical null/errors distinct from membership. |
| Creation and one-team guard | POST /api/hackathons/{h}/teams | CreateTeam/API/backend tests preserve exact name/key under uncertainty, double-submit prevention and account isolation. |
| Request and leader approval/rejection | POST /api/hackathons/{h}/teams/{t}/join-requests; GET same and /mine; POST /{request}/decision | Admission/API/backend tests plus named-action regression; permission loss hides applicant data, pending requests reserve no seat. |
| Issue/receive/redeem invitations | POST /api/hackathons/{h}/teams/{t}/invitations and /{invitation}/redeem; GET /api/hackathons/{h}/invitations/mine | Invitations/API/backend tests plus named identity and duplicate-feedback regressions; expiry, account binding, original-key recovery and no seat reservation retained. |
| Member leave/removal, succession and last departure | POST /api/hackathons/{h}/teams/{t}/leave and /members/{user}/remove; GET /members | Lifecycle tests cover confirmation/Cancel, refreshed membership/deletion, recovery, later rejoin/new key and named removal. New tests cover keyboard focus and lost-leadership draft removal. Prior owner PostgreSQL 10/10 remains historical. |
| Committed workspace updates/reconnect | GET /api/hackathons/{h}/events | Realtime/BatchCompatibility and backend SSE tests cover canonical invalidation, drafts, expiry, stale callbacks and permission loss. No SSE service/protocol change. Prior owner PostgreSQL 4/4 is not real browser/proxy proof. |
| Account isolation, Back/Forward, remount and recovery | Same authenticated scoped reads; no new route | DiscoveryNavigation/Journeys and all journal suites cover scoped storage hints, session recheck, late replies and original-key recovery. Reload/crash still loses mutation journals. |
| Footer connection check | GET /health | App.test checks liveness wording, bounded timeout, sanitized failures and explicit retry. It is not readiness. |

All protected domain routes retain validated-session dependencies; writes retain
CSRF/current authorization and original services. No direct-join bypass was
added. No broken primary link or speculative user-directory endpoint was found.
Generated FastAPI documentation routes are not product navigation controls.

<a id="product-audit-redundant-elements-and-code-removal-decisions"></a>
## Redundant elements and code removal decisions

- Removed the duplicate team-name paragraph when the invitation heading already
  names the team. IDs moved to secondary details rather than being discarded.
- Suppressed redundant inbox success when the same confirmed command has a card.
  Off-page success and all uncertain-command controls remain reachable.
- Cleared obsolete unsubmitted removal confirmation after permission loss and on
  collapsing Manage membership; confirmed/uncertain commands remain untouched.
- Replaced developer-facing liveness wording. Kept the bounded service check and
  existing timeout/retry tests, rather than introducing a new diagnostic feature.
- No deleted modules, hooks, guards, audit/outbox code or tests. Independent
  refresh controls serve different canonical reads; no blind deduplication.

<a id="product-audit-static-keyboardresponsive-review"></a>
## Static keyboard/responsive review

Reviewed explicit form labels, aria-invalid/describedby, role=status/alert,
native buttons/summary controls, skip link and #main focus target. Membership
Cancel/focus is now covered offline; existing detail/navigation heading focus
and first-invalid-field focus remain. Technical references use native details.
Names stay React text, not HTML. Session/account transitions still hide private
content and cancel/fence old responses.

CSS already stacks workspace/auth layouts at 700px, reduces the board to one
column at 1000px, wraps navigation/action rows and long headings/UUIDs, uses
minmax(0,1fr)/min-width:0 in key containers, and provides visible focus outlines
and reduced-motion rules. Standard .button controls have a 44px minimum height.
No CSS redesign was made. Browser checks at 320/375/768/1280px, 200% zoom,
long user/team names, all roster buttons, native details and keyboard/screen-reader
announcements are still required. Source rules do not prove rendered geometry.

<a id="product-audit-actual-commands-and-results"></a>
## Actual commands and results

Windows PowerShell, existing Python 3.11.9, Node 22.15.0, npm 10.9.2; installed
dependencies reused. Commands ran locally without a network server/database.
The sandbox failed before process startup; explicit runtime review permitted
the same bounded offline work outside it. Git used command-scoped
`-c safe.directory=I:/Merge`, with no global configuration change.

| Working directory / exact command | Observed result |
| --- | --- |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1 src/ProductAudit.test.tsx` before production fixes | 10 failed, 1 passed, 9.35s, exit 1. Demonstrated original defects; username-conflict control passed. Initial file-write attempt used a duplicated frontend path, wrote nothing, then Vitest correctly reported no tests; corrected before this reproduction. |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1 src/ProductAudit.test.tsx src/ProfilesRanking.test.tsx src/BatchCompatibility.test.tsx src/Lifecycle.test.tsx src/Invitations.test.tsx src/Admission.test.tsx src/api.test.ts` | 189 passed / 7 files, 89.03s, exit 0. Checkpoint before the final added cases/service wording. |
| backend: `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short` | 1719 passed, 32 deselected, 81.30s, exit 0. Existing Starlette/httpx deprecation warning; no dependency replacement. |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1` initial full run | 407 passed, 1 failed / 16 files, 146.31s, exit 1. Existing restored-inbox test checked an effect-owned fetch after only waiting for a static heading. |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1 src/DiscoveryNavigation.test.tsx src/ProductAudit.test.tsx src/App.test.tsx` diagnostic checkpoint | 56 passed, 1 failed, 22.90s, exit 1. New no-mutation assertion initially required method=GET even for the liveness fetch's implicit GET; corrected to allow omitted method. No production issue concealed. |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1` FINAL | 408 passed / 16 files, 122.18s, exit 0. Includes all fourteen new regressions and strengthened navigation coverage. |
| frontend: `npm.cmd run build` FINAL | TypeScript passed; Vite transformed 50 modules, built in 3.18s, exit 0. Earlier successful build: 2.96s. |
| root: `git -c safe.directory=I:/Merge diff --check` | Passed, exit 0; only LF-to-CRLF notices, no whitespace errors. Command-scoped safe.directory is needed because the fallback executor and repository have different Windows owners. |

The restored-inbox test now defers the response, waits for the actual GET,
asserts loading and absence of a fabricated empty state, resolves the canonical
response, checks the returned empty state and forbids mutations. No test was
deleted/skipped, no timeout was increased, and product guards were unchanged. Fourteen new cases
live in ProductAudit.test.tsx; the original six liveness tests are retained with
the new wording. No tests or historic evidence were deleted.

Static review already found all 24 production files reachable, zero targeted
secret-pattern hits in changed/new text, no backend or staged paths, and ignored
dist/node_modules/pytest-cache output. Targeted patterns cover private keys,
provider tokens and credential-bearing PostgreSQL URLs; this is not a claim of
comprehensive secret detection. Final inventory is ten modified files plus two
new files, matching the twelve paths below, with no staged/backend/dependency/
migration/evidence paths. No unexpected untracked deliverable was found.
An auxiliary diff check with core.autocrlf=false treated existing Windows CRLF
as trailing whitespace and showed README as a whole-file change. The repository's
normal line-ending configuration is retained; the final check uses ordinary Git
configuration. No global Git setting was changed.

<a id="product-audit-complete-task-file-inventory"></a>
## Complete task file inventory

Modified:

1. `frontend/src/api.ts` — conflict messages only; transport/DTOs unchanged.
2. `frontend/src/components/Profile.tsx` — exact validation recovery and alerts.
3. `frontend/src/components/Admission.tsx` — named accessible actions/reference IDs.
4. `frontend/src/components/Invitations.tsx` — named cards/actions, references and nonduplicated success.
5. `frontend/src/components/Lifecycle.tsx` — confirmation focus/current-leader draft handling.
6. `frontend/src/components/HealthStatus.tsx` — liveness-only participant wording.
7. `frontend/src/App.test.tsx` — preserve liveness failure/retry cases with accurate wording.
8. `frontend/src/DiscoveryNavigation.test.tsx` — strengthen canonical inbox synchronization.
9. `README.md` — link this review checkpoint.
10. `docs/PROGRESS.md` — append actual verified offline milestone only.

New:

11. `frontend/src/ProductAudit.test.tsx` — fourteen focused regressions.
12. `docs/PRODUCT_AUDIT.md` — audit, implementation/evidence/inventory and remaining gates.

No new dependencies, migrations or deleted files. Build output under frontend/dist
and test caches are ignored local artifacts. Old reports, receipts, manifests,
fixtures, migrations and backend sources were not edited by this task. No staging,
commit/push, deployment, fixture cleanup, database action, live API call or
browser/server startup occurred.

<a id="product-audit-remaining-owner-verification-and-explanation"></a>
## Remaining owner verification and explanation

Before release: separately review/apply 0006 to an authorized exact-version target
and run profile PostgreSQL acceptance; use a fresh correctly scoped browser host
to validate every journey, mobile/keyboard behavior, cookies/HTTPS and SSE/proxy
transport. Do not reuse old browser manifests as authorization for these routes.
CI/race evidence, benchmark seed 10,000/2,000, 100 clients and measured p95, public
deployment, design/video/submission gates keep their separate review requirements.

Owner explanation: names are display data; UUIDs still choose the exact command.
A rejected profile validation happens before the write and can retain its draft.
A lost response cannot establish rollback, so reload/CAS or the existing
original-key command recovery is still required. Client leadership hides controls;
the backend remains responsible for authorization and race safety.

Exercise: in ProductAudit.test.tsx, change the named team's label and verify the
accessible invitation name changes while the submitted team/invitation UUIDs do
not. Then change the synthetic profile error from 422/invalid_request to an
unrecognized 422 and explain why editing must wait for canonical reload.

STOP for owner review. This checkpoint authorizes no live operation or commit.


---

<a id="browser-host-audit"></a>

<a id="browser-host-audit-guarded-browser-host---r4-correction-and-historical-r3-audit"></a>
# Guarded browser host - R4 correction and historical R3 audit

**R4: B1 corrected and offline regression green; owner review before live work.**
No live backend/browser/Vite, PostgreSQL access, credential prompt or approval
manifest was created. R3 findings below describe the audited pre-fix state; this
section and the R4 PROGRESS entry control the current shutdown status. Existing
account/fixture/write-approval prerequisites remain in force. G1 is open.

<a id="browser-host-audit-r4-root-cause-and-smallest-correction"></a>
## R4 root cause and smallest correction

Uvicorn 0.54.0 catches drain TimeoutError internally and does not set force_exit.
R2's indirect reliance on cancellation reaching an ASGI request missed lingering
connections without active requests. A successful database snapshot could then be
mistaken for a fully completed run. R3 reproduced this with real installed Uvicorn
shutdown code and fake resources; its required-behavior assertion was left red.

R4 adds only test_support.browser.BrowserServer to wrap the pinned Uvicorn drain
hook and shutdown, uses it in serve, and moves the success print to main after
resource contexts close. The subclass delegates actual shutdown/closing to Uvicorn;
it does not replace its algorithm, install global patches or alter production
app.serve. No database transaction/service, dependency guard, auth boundary,
manifest, policy, schema or dependency change is needed.

Guarantees now required before a success label/exit 0:

1. The drain coroutine has returned normally, with no protocol connections or
   request tasks left. Neither server.run returning nor cancellation is sufficient.
2. A sticky drain_failed bit is clear. Timeout cancellation (including timeout
   before callback entry), forced exit, shutdown exceptions and unresolved work
   latch failure. Residual work at server.run return is latched before observer
   work and rechecked later; finishing during a snapshot cannot clear failure.
3. Existing database/request failure latch is clear, original app state is still
   safe, and the application lifespan shutdown marker is present.
4. Independent fresh guarded final snapshots and comparison have passed, all
   Engine-owner contexts have disposed their owned resources, and the listener
   context has closed. Only then does main print final verification success.

The first handled Ctrl+C may finish normally and qualify only if all checks pass.
Uvicorn's second interrupt sets force_exit; interrupted observers/cleanup and
exceptions propagate to the sanitized exit-1 handler. Invalid CLI is exit 2. A
hard OS kill can skip Python cleanup and produce missing evidence; no successful
verification is inferred. No cancellation, Engine disposal or failed snapshot
proves a remote transaction rolled back or an in-flight worker stopped. Diagnostic
snapshots after an incomplete drain cannot certify the run. No fixture cleanup or
new write is introduced.

The supported synchronous services finish their worker call before a normally
completed request task returns; timeout/cancel paths cannot qualify. Offline tests
hold a simulated database worker, prove clean drain waits for its completion,
and separately prove cancelled request tasks can coexist with a still-running
worker. That run remains failed even after the worker and later snapshots finish.
This is not real PostgreSQL termination or browser evidence. Arbitrary detached
workers/external writers are outside this inspected application's guarantees.

The hook is a private Uvicorn method: the project pins 0.54.0, the tests exercise
that installed implementation, and any future Uvicorn upgrade must re-audit the
hook/cancellation/timeout contract. No library change is made by R4.

<a id="browser-host-audit-exact-minimal-r4-source-diff-against-the-reviewed-r3-file"></a>
## Exact minimal R4 source diff against the reviewed R3 file

```diff
--- R3/browser.py
+++ R4/browser.py
@@ -367,0 +368,39 @@
+class BrowserServer(uvicorn.Server):
+    """Record the drain Uvicorn's shutdown() otherwise swallows on timeout.
+
+    Uvicorn 0.54.0 wait_for cancels _wait_tasks_to_complete on timeout; a zero
+    deadline can cancel it before entry. Require positive completion as well as
+    a sticky failure bit and empty protocol/task sets. Cancellation is not proof
+    that a synchronous request worker or its database transaction has stopped.
+    """
+    def __init__(self, config):
+        super().__init__(config)
+        self.drain_complete = False
+        self.drain_failed = False
+
+    def drained(self):
+        return (self.drain_complete and not self.drain_failed and not self.force_exit
+                and not self.server_state.connections and not self.server_state.tasks)
+
+    async def _wait_tasks_to_complete(self):
+        try:
+            await super()._wait_tasks_to_complete()
+        except BaseException:
+            self.drain_failed = True
+            raise
+        self.drain_complete = not (self.force_exit or self.server_state.connections
+                                   or self.server_state.tasks)
+        if not self.drain_complete:
+            self.drain_failed = True
+
+    async def shutdown(self, sockets=None):
+        try:
+            await super().shutdown(sockets=sockets)
+        except BaseException:
+            self.drain_failed = True
+            raise
+        finally:
+            if not self.drained():
+                self.drain_failed = True
+
+
@@ -377 +416 @@
-        server = uvicorn.Server(config)
+        server = BrowserServer(config)
@@ -385,2 +424,4 @@
-            # server.run returns only after draining/shutdown. A forced exit cannot
-            # count as a pass, even if a new independent observer can still connect.
+            if not server.drained():
+                server.drain_failed = True
+            # The observer is diagnostic after an incomplete drain: workers may
+            # still finish. Its result cannot clear the server drain failure.
@@ -391 +432 @@
-        if (not server.started or server.force_exit or guard.failed.is_set()
+        if (not server.started or not server.drained() or guard.failed.is_set()
@@ -395 +435,0 @@
-        print('Browser host final invariants verified; fixtures retained.', flush=True)
@@ -406,0 +447,2 @@
+                # Only after observer comparison, Engine disposal and socket close.
+                print('Browser host final invariants verified; fixtures retained.', flush=True)
```

<a id="browser-host-audit-r4-verification"></a>
## R4 verification

The unchanged R3 timeout regression passes. New offline cases cover normal clean
drain with a held worker, a first graceful interrupt, timeout with an active
request and surviving worker, zero-timeout before callback entry, sticky failure
after later completion, residual requests (including completion during observer
work), double interruption, observer/comparison/lifespan/listener/Engine cleanup
failure, and interruption during final checks. All original assertions are
preserved; the preexisting lifecycle fake now models the selected BrowserServer
and its explicit drain outcome. No test was skipped, weakened or xfailed.

Final R4 harness suite: **127 passed in 7.26s**; full offline backend:
**933 passed, 32 deselected in 23.43s**, both exit 0 with one existing warning.
Frontend typecheck, **52 tests in 14.86s**, and build passed. Exact commands,
protected-source/AST checks and Git inventory are in the R4 entry of PROGRESS.md. FRONTEND/TEST_DATABASE/BROWSER_ACCEPTANCE
notices now distinguish the corrected offline defect from still-pending owner
approval and live verification. The historical R3 audit evidence
below remains unchanged except its explicit historical-status annotation.

Owner exercise: keep a fake worker blocked in the timeout test; explain why the
request task's cancellation and a later passing snapshot cannot grant success.
Change the test deadline and identify the positive drain-completion evidence,
without deleting or weakening the original R3 assertion.

<a id="browser-host-audit-historical-r3-audit---pre-fix-findings-and-evidence"></a>
## Historical R3 audit - pre-fix findings and evidence

**Historical R3 verdict: HOLD; B1 was reproducible before the R4 correction.**
Audited 2026-11-10 against HEAD `cc67e18ffd6a6845642170fa358ecc48d2fef38b`
and the uncommitted M-011A/R1/R2 tree. No PostgreSQL, live backend/Vite/browser,
credential prompt, approval-manifest creation, migration, fixture mutation,
cleanup, privilege change, staging, commit or push was performed.

This is an offline source/test audit, not certification of a live PostgreSQL or
browser environment. It supersedes R2's claim that every drain timeout necessarily
makes the run nonzero. The two harness implementation files are unchanged in R3.

<a id="browser-host-audit-blocking-finding-b1-a-drain-timeout-can-report-success"></a>
## Blocking finding B1: a drain timeout can report success

Source: browser.py:381-395 and the installed uvicorn/server.py:282-311.
The installed Uvicorn 0.54.0 shutdown method catches asyncio.TimeoutError, logs an
error, cancels the current request-task set, then completes lifespan shutdown.
It does not set force_exit or expose a timeout flag to this harness.

The host only detects the timeout indirectly when a cancelled ASGI request reaches
ClosedHost's BaseException handler. With a lingering protocol connection and no
active request task, nothing sets ConnectionGuard.failed. Uvicorn can return with:

- server.started = True;
- server.force_exit = False;
- guard.failed = False;
- app.state.browser_shutdown_complete = True;
- an unchanged before/after database snapshot.

The predicate at browser.py:391 then accepts the run; it prints the final success
label and main returns 0 despite exceeding the graceful drain deadline. Logging is
disabled, so the Uvicorn timeout diagnostic is also suppressed. This is an evidence
and shutdown-safety defect; it is not evidence of a merge_dev connection or a
security-policy bypass.

The new test `test_drain_timeout_without_request_task_must_exit_nonzero` reproduces
this using the **installed Uvicorn shutdown implementation**, one fake lingering
connection, no request tasks and a zero-second timeout to enter the same branch
without waiting 25 seconds. Uvicorn run/startup/serve, HTTP binding, credentials,
Engine creation and snapshots are replaced by fakes. The required assertion
`result == 1` fails because the current harness returns 0. The test remains red:
no xfail/skip and no weakened existing assertion. It must turn green before live
startup is proposed.

Required bounded repair, not implemented by this audit: explicitly latch/report
the server drain-timeout outcome and reject it independently of request-task
cancellation; check drain/lifespan completion and outstanding work directly. Do
not infer graceful completion solely from server.run returning. Preserve the fresh
final observer and resource disposal; a timeout's final snapshot may be diagnostic
but must never earn a success label. Add coverage with and without active tasks,
forced/repeated interruption and a normal successful shutdown. Production auth,
TeamService and database invariants need no change to repair this host-only issue.

<a id="browser-host-audit-startup-trace-manifest-through-first-accepted-request"></a>
## Startup trace, manifest through first accepted request

| Phase | Exact path and safety boundary |
| --- | --- |
| Import | browser imports app.main.create_app; the ordinary module app is constructed but never served and its lifespan is not entered. No ordinary Settings or Engine is initialized by that construction. |
| CLI | arguments() requires inspect/serve/verify, --confirm-merge-test, exact --revision 0003_auth and a manifest path. serve also requires --allow-scoped-auth-writes; read commands reject that flag. Optimization and unknown arguments are rejected with fixed text before prompt/connection. |
| Manifest | main -> quiet_logs -> read_scope. JSON duplicate-key detection, 8192-byte bound and strict frozen RunScope/AccountScope validation precede credential prompting and Engine creation. |
| Socket reservation | serve calls reserved_socket: exact 127.0.0.1:8000, no SO_REUSEADDR; Windows exclusive bind. Port 5173 is checked and released. Binding reserves a socket; it does not accept HTTP requests. Occupied ports stop startup. |
| Credential | isatty plus getpass; empty input and GetPassWarning echo fallback refuse. Only the database role password is prompted here. Account passwords are never manifest/CLI values. |
| Initial connection | guarded_engine validates TestDatabaseSettings.url/password, enters the existing test_connection owner, applies the full guard to its anchor, then installs engine_connect before exposing the Engine. The helper's first identity SELECT precedes the full browser guard; it is read-only SQL and no service/domain work is reachable before full verification. |
| Preflight state | Engine.connect invokes the installed guard. snapshot sets READ ONLY, confirms each username maps to the declared UUID, checks session/team invariants and privately fingerprints state; rollback ends that transaction. No fixture writes occur. |
| App composition | local_policy uses BrowserPolicy constructor input only. browser_app checks fixed policy/write opt-in, creates original routes/middleware, disables framework docs/schema, builds real services on the guarded Engine and installs both overrides. |
| Uvicorn | One worker, no reload, proxy_headers=False, forwarded_allow_ips='', access_log=False. The in-memory ASGI object and reserved socket are supplied directly; no ordinary app import-string launcher is used. |
| Lifespan | Original lifespan receives the explicit policy and sets ordinary auth/read state to None. The wrapper audits wiring, checks the latch, then prints its ready label. This label precedes the listener's completed startup and is not independent readiness/browser evidence. |
| HTTP entry | ClosedHost audits wiring and the latch before calling FastAPI. A missing/replaced override or unexpected route/dependency returns private no-store 503 and latches closed before dependency resolution. |
| Original policy | AuthBoundary checks actual peer/forwarding, Origin, Fetch Metadata, media type and X-Merge-Request before FastAPI body/dependency processing. |
| Resolution | Login bodies are validated again by the strict original model before the scope budget is charged. Registration is refused. Authenticated reads/logout decode the cookie and call real session validation plus the scope facade; read services are guarded and read-only. |

The startup path currently passes these offline checks, but B1 prevents a ready
verdict for the whole run.

<a id="browser-host-audit-dependency-and-ordinary-settings-proof"></a>
## Dependency and ordinary-Settings proof

browser.py:249 installs exactly:

- app.auth.get_services -> scoped_auth, returning real CredentialService,
  ScopedSessions(real SessionService), real ThrottleService;
- app.read_api.get_read_service -> scoped_reads, returning real TeamReadService.

All four real services receive the **same guarded Engine**. scoped_reads does not
need to call the ordinary dependency: the original read router independently
requires authenticated_session, and the audited effective dependency inventory
contains authenticated_session, session_cookie, get_services, get_read_service
and read_request. scoped_auth neither calls its ordinary counterpart nor builds
Settings. In the ordinary code, Settings/build_engine is only reached inside
get_services when auth_services is None. The original get_read_service can only
use auth_engine and is also replaced.

At startup and before each HTTP request, audit_wiring checks exact override
function identities, exact endpoints/methods, expected dependency sets, one health
route, no duplicate/unknown routes and auth_engine/auth_services/read_service all
None. It uses installed FastAPI iter_route_contexts for effective lazy included
routers. The request wrapper executes this audit **outside and before** the
FastAPI application. Removing an override cannot first reach the ordinary lazy
initializer. Existing and new tests make ordinary Settings/build_engine raise if
called; authorized auth/read paths, missing overrides and unknown dependencies
exercise that boundary without calling them. Production imports/package selection
exclude test_support. These are proofs for this inspected code and the trusted
Python/application boundary, not protection against arbitrary in-process code
rewriting functions or injecting middleware after the audit.

<a id="browser-host-audit-connection-audit"></a>
## Connection audit

browser.py:58-112 applies the guard to the initial anchor and via engine_connect to
every subsequent logical Engine.connect, whether backed by a new or pooled DBAPI
connection. Each owned final observer creates a fresh guarded Engine too.

| Check | Required value |
| --- | --- |
| Configured target | confirmed=True; 127.0.0.1:5432 / merge_test / merge_app; nonempty explicit password |
| Driver | synchronous postgresql / psycopg |
| Transaction entry | no inherited SQLAlchemy transaction; actual DBAPI autocommit is False; no AUTOCOMMIT execution option |
| Actual identity | current_database merge_test; current_user merge_app; inet_server_addr 127.0.0.1 (optional /32); inet_server_port 5432 |
| Isolation | connection.get_isolation_level READ COMMITTED; server transaction_isolation and default_transaction_isolation read committed |
| Guard transaction | SET TRANSACTION READ ONLY and current_setting transaction_read_only = on |
| Deadlines | connect_timeout 5 seconds; guard verifies lock_timeout 5s and statement_timeout 15s |
| Revision | public.alembic_version yields exactly [0003_auth] |

A guard exception sets the shared failure Event, attempts connection.invalidate,
and raises a fixed sanitized DiagnosticFailure. Invalidation errors are suppressed;
even if invalidation itself fails, no guarded connection is yielded and the latch
continues to block requests/checkouts. Successful guards roll back their own read
transaction so services can begin theirs. Existing services independently reject
AUTOCOMMIT, wrong dialect/isolation and inherited transactions. Credential/session
transactions use 5s/15s; original throttle transactions deliberately tighten these
to 1s/2s with SET LOCAL, which resets at transaction end. There is no fallback Engine
or merge_dev target. A connection-creation/checkout exception before engine_connect
runs does not itself set the running-host latch; it still fails the request/startup
without fallback. That distinction is outside the narrower failed-guard claim.

No real PostgreSQL/pool/reconnect behavior was exercised. Offline doubles verify
the callback, repeated guard execution and event registration/removal; source
inspection establishes the connection ownership. A revision marker is not an
adversarial DDL/ACL attestation.

<a id="browser-host-audit-manifest-schema-client-input-and-owner-approval"></a>
## Manifest schema, client input and owner approval

Exact schema: required UUID run_id; accounts array of 1-3 objects. Each object has
required UUID user_id, username matching ASCII [a-z0-9_]{3,32}, and required strict
integer login_attempts/logout_attempts, each 0-30 inclusive. Duplicate user UUIDs
or usernames, unknown/missing fields, invalid UUIDs, non-integer/boolean budgets,
out-of-range budgets, duplicate JSON keys, malformed/missing/oversized files refuse.
There are no account/budget defaults or environment sources. Invalid scopes are
rejected before the hidden prompt; account mapping is then confirmed by read-only
SQL before service use.

Safe schema example using placeholders only (deliberately not executable JSON):

```text
{
  "run_id": "<OWNER-SELECTED FRESH RUN UUID>",
  "accounts": [
    {
      "user_id": "<EXISTING APPROVED TEST ACCOUNT UUID>",
      "username": "<EXISTING APPROVED TEST USERNAME>",
      "login_attempts": <APPROVED INTEGER 0 THROUGH 30>,
      "logout_attempts": <APPROVED INTEGER 0 THROUGH 30>
    }
  ]
}
```

No approval manifest was written by this audit. Parser tests use in-memory mocked
file contents; existing R2 parser tests use only pytest temporary synthetic files.
No file under frontend/test-results was generated or inspected.

The reviewed file is the human approval boundary: the program cannot determine
that an owner approved an otherwise syntactically valid existing account. There
is no signed approval registry or special fixture-account database flag. The
owner must approve the exact file and account usage separately from this audit.
Membership/account UUIDs in client bodies do not create authority; strict input
models reject attempted user_id/run_id/budget/identity fields. Client usernames
can select only manifested accounts and cannot change their UUIDs or budgets.
Actual authenticated principals are checked against both UUID and username.

Budgets are frozen at parse time and reserved under a mutex. Admitted login
attempts consume budget even when credentials fail, throttling denies, a service
fails or the response is lost. Logout charges only after actual session and CSRF
validation. This is a test-run safety budget, not domain race synchronization.

<a id="browser-host-audit-endpoint-and-browser-protections"></a>
## Endpoint and browser protections

Registration remains a known original route but its scoped dependency refuses it
before throttle/register work; encoded/trailing-slash forms are also covered by
new tests. No domain mutation route is included. Exact route inventory rejects
new/unknown endpoints; domain POST probes return 404/405. TeamService and all
production auth code are unchanged.

Original Origin/Fetch Metadata/media/custom-header/forwarding checks precede scope
parsing. Cookie encoding/validation, real CSRF verification before revoke, durable
throttle behavior and Retry-After handling remain the original implementations.
Fixed development cookie: merge_session_dev, HttpOnly, SameSite=Lax, Path=/,
no Domain, Secure=False. Origin is exactly http://127.0.0.1:5173. No CORS/proxy trust
or alternate client identity is introduced. Fixed CLI has no host/port/worker/reload
options; direct non-loopback helper inputs are refused. BrowserPolicy ignores all
environment/dotenv/file-secret settings. Fixed database settings ignore MERGE_DB_*.

The database password enters only through interactive hidden getpass; no password
argument or environment fallback is accepted. SQLAlchemy internally stores it in
its URL/connect configuration to authenticate: **it is not absent from all memory
or internal URL objects**. It is excluded from printed/browser URLs, output,
argument history and normal logs/tracebacks. Secret repr fields are redacted and
SQL parameters hidden. CLI/runtime failures use fixed allowlisted diagnostics,
logging is disabled while running, and no private snapshot/session values are
printed. External debuggers, tracing/APM, OS inspection and modified libraries are
trusted and cannot be certified by this harness. Do not enable them during a run.

<a id="browser-host-audit-shutdown-audit-including-what-does-fail-closed"></a>
## Shutdown audit, including what does fail closed

Normal intended sequence: Uvicorn stops accepting, drains, enters application
shutdown; wrapper re-audits and sets shutdown-complete; independent guarded Engine
reads committed after-state; compare requires unchanged users/credentials/domain,
bounded scoped session issuance/revocation and run-key login buckets only; owned
resources are disposed. Exceptions from observer/compare/disposal propagate to
main's fixed diagnostic and return 1. __main__ raises SystemExit(main()), so the
status reaches PowerShell. CLI rejection is exit 2. Startup failure, force_exit,
guard latch or missing shutdown marker rejects success. Interrupted final checks
return nonzero/missing final evidence; standalone verify cannot recover a lost
before-state. Those paths are covered by existing tests.

**The timeout-without-cancelled-request case B1 is not rejected.** Thus task 12
cannot be confirmed and the implementation is not ready. Do not use the prior R2
success/exit-0 rule as sufficient evidence until B1 is repaired. No revised live
startup commands are proposed in R3. R2 commands are retained as historical,
conditional syntax under a HOLD banner; do not run them based on this audit.

<a id="browser-host-audit-required-owner-accounts-data-and-approvals"></a>
## Required owner accounts, data and approvals

Actual retained IDs, account passwords and browser sessions are **unknown to this
audit**; no database/private attachment/credential-store inspection was performed.
Do not infer usable accounts from old fixture names or aggregate test counts.

| Exercise | Required retained prerequisites |
| --- | --- |
| Read-only inspect/verify | Existing merge_app database-role password, local merge_test at exact 0003_auth and approved account UUID/username mappings. No account password is needed merely to inspect mappings/invariants. |
| Authenticated session/discovery reads | A scoped live valid browser-managed session. In a fresh profile it normally requires login with a known private retained-account password, which writes session/throttle state and requires separate approval. Never extract/copy stored hashes, bearer or CSRF material to manufacture access. |
| Login/logout/cookies/failure/throttle | 1-3 approved retained credentialed accounts, known private test passwords, exact per-account attempt/revocation budgets and explicit scoped-auth-write approval. A dedicated account/budget for deliberate failures/429s is preferable; normal limits stay unchanged. |
| Present/null My Team | A credentialed manifested account already a member and another credentialed account without membership in the same declared existing hackathon. Public UUID-only fixture founders are not necessarily login accounts. No joining or credential reset is authorized. |
| Detail/order/pagination | Owner-declared existing hackathon/team UUIDs; at least 21 visible live teams in one hackathon for two default 20-item team pages. Catalog pagination separately needs enough hackathons. ReadEnvironment's three teams do not satisfy team-page acceptance. |
| Cross-login stale responses | Two usable approved accounts, login/logout budgets, suitable real read data and a separately reviewed deterministic delay instrument. That instrument is still unimplemented. |
| Expired/revoked session | Natural expiry or normal budgeted logout; no direct backdating/revocation SQL or new endpoint. |

Before later live work: repair B1 and rerun its tests; approve that concrete host
revision; identify and approve retained account mappings and exact public domain
fixtures; confirm known private passwords without sending them into chat/files;
approve live reads separately from session/throttle writes; review the exact
manifest and row/attempt budgets; arrange an exclusive run with no unrelated DB
writers, free loopback ports, private terminal/profile and no secret telemetry.
No approval is requested or inferred by this audit.

Unavailable credentials prevent real login, session issuance/restore/logout,
authenticated discovery and cookie/CSRF browser acceptance. Missing memberships
prevent present/null comparison; too few teams prevent second-page evidence.
Registration is impossible through this host regardless of fixtures. This local
HTTP host cannot prove production Secure/HTTPS/proxy behavior, complete accessibility,
real browser layout, load/CI/concurrency gates or G1. Mocked errors/delay do not prove
natural network races. No seeding, resets, extraction or weakened page size is a
substitute for missing prerequisites.

<a id="browser-host-audit-nonblocking-limitations-and-follow-up-scope"></a>
## Nonblocking limitations and follow-up scope

- Manifest approval is human/file based; arbitrary trusted local code, shared
  merge_app privileges and external instrumentation remain outside isolation.
- Initial account-to-UUID mapping is checked before serving and again at final
  inspection. ScopedSessions.login checks the returned principal after the real
  login has committed. Therefore exclude concurrent credential/account writers;
  this facade is not a pre-commit UUID guard against a malicious concurrent rename.
- The run_id is metadata, not a durable single-use authorization. Budgets and the
  random throttle key reset in a new process. The documented no-restart/no-key-
  rotation rule requires owner discipline; it is not enforced across processes.
- Whole-table fingerprints require an exclusive run, can be costly and are not
  adversarial tamper proof; READ COMMITTED statements are not one global snapshot.
- A frozen revision marker is not live schema/permission verification. Timeouts,
  cookie enforcement, socket behavior and actual PostgreSQL queries need later
  approved live evidence. No failure category implies a proven connection target
  when connection establishment itself failed.
- Ready is printed during lifespan before the listener finishes startup. Treat it
  only as guard/wiring acceptance, as R2 already says; no live readiness was proved.

Owner exercise: run the new failing offline timeout test, trace why the four
current success flags all pass, and explain which explicit shutdown outcome a
host-only fix must capture. Do not remove/weaken the assertion to obtain green CI.

<a id="browser-host-audit-r3-evidence"></a>
## R3 evidence

Exact commands and environment are in PROGRESS.md. Fresh harness suite:
**1 failed, 112 passed in 5.74s**; full database-free suite:
**1 failed, 918 passed, 32 deselected in 29.33s**, both exit 1 with the same new
timeout regression and one existing warning. Original 82 cases remain green.
Compile/AST/import/packaging/protected-source, pip check and git diff --check
passed. Pending Git inventory: 28 files (12 tracked modifications, 16 untracked),
empty index, unchanged HEAD. No current all-green or live-ready claim is made.


---

<a id="render-preparation-review"></a>

<a id="render-preparation-review-pending-deployment-adapter-review"></a>
# Pending deployment adapter review

Owner review stop: **nothing staged or committed**; no push, cloud resource,
production connection, migration, server startup, paid action or deployment.
Starting/ending HEAD remains `bb60ab3dd764e63de6a2261e4f3924e3d78bda33` on `main`.
The owner reports baseline GitHub Actions 5/5; pending adapters need fresh public CI.

<a id="render-preparation-review-complete-pending-file-inventory"></a>
## Complete pending-file inventory

All prior pending Railway work is retained. No source, document, test, script,
deployment file or historical evidence was removed, moved or archived. No
application feature, dependency, migration revision or workflow was modified.

Modified tracked documentation (7 paths; includes prior Railway edits):

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/DEPLOYMENT.md`
- `docs/PROGRESS.md`
- `docs/README.md`
- `docs/TESTING.md`

New pending paths (30 total, including retained Railway files):

- `backend/app/railway/__init__.py`
- `backend/app/railway/api.py`
- `backend/app/railway/application.py`
- `backend/app/railway/check.py`
- `backend/app/railway/config.py`
- `backend/app/railway/database.py`
- `backend/app/railway/operations.py`
- `backend/app/railway/serve.py`
- `backend/app/render/__init__.py`
- `backend/app/render/api.py`
- `backend/app/render/application.py`
- `backend/app/render/check.py`
- `backend/app/render/config.py`
- `backend/app/render/database.py`
- `backend/app/render/initialization.py`
- `backend/app/render/serve.py`
- `backend/app/render/setup.py`
- `backend/railway_alembic/env.py`
- `backend/render_alembic/env.py`
- `backend/tests/test_railway.py`
- `backend/tests/test_render.py`
- `deploy/Dockerfile.railway`
- `deploy/Dockerfile.render`
- `deploy/railway/caddy.template.json`
- `deploy/railway/settings.json`
- `deploy/render/caddy.template.json`
- `docs/RAILWAY.md`
- `docs/RENDER.md`
- `docs/RENDER_REVIEW.md`
- `render.yaml`

<a id="render-preparation-review-reuse-and-adaptation"></a>
## Reuse and adaptation

The original 14 Railway additions are retained byte-for-byte: eight modules in
`backend/app/railway/`, its Alembic entry point, tests, Dockerfile, two deployment
JSON contracts and runbook. They remain an alternate hosting adapter; no Railway
remote operation is proposed for the Render deployment.

Render directly reuses Railway's connection Guard/readiness, private IP networks,
server identity check, validated secret/port helpers and process readiness/shutdown
helpers. The Render factory/API worker/Dockerfile/Caddy template adapt their
reviewed Railway counterparts. Render-specific code supplies strict onrender/dpg
configuration, smaller pool, CF client identity, PORT/health routing, explicit
setup-only operation and transaction-owned Alembic environment. No app service or
public API behavior changes. Docs now select Render and retain VPS/Railway links.

The deployment-only claim schema is outside `public`, unavailable to runtime, and
records only one attempt UUID/SHA/state. It does not change version 0006 or domain
membership transactions. The ADR precedes the new adapter implementation.

<a id="render-preparation-review-proposed-commit-and-publication-sequence-owner-actions-only"></a>
## Proposed commit and publication sequence (owner actions only)

1. Review the **entire** pending inventory above, its ADR and [runbook](../RENDER.md),
   including the retained Railway files. Check private evidence is still ignored.
2. After approval, explicitly stage the reviewed paths (avoid broad `git add .`),
   inspect `git diff --cached --stat` / `git diff --cached --check`, and create one
   local commit with proposed message `chore(deploy): prepare Render Free adapter`.
   No commit or staging was performed in this task.
3. Record `git rev-parse HEAD`; review its exact staged scope and final status.
   After separate publication approval, the push command is `git push origin main`.
   Require a new passing GitHub Actions execution for this actual commit; the old
   baseline pass does not certify the adapters. No Actions rerun was requested here.
4. After separate deployment approval, follow [RENDER.md](../RENDER.md): create private
   PG17 and the Free web service, manually deploy explicit setup at that reviewed
   SHA, inspect its JSON result, then remove privileged inputs and select ordinary
   serve at the same SHA. Dashboard settings must match the reviewed contract.
5. Verify native build/startup, 512 MB use, provider grants, HTTPS/header spoofing,
   cookies/CSRF and real SSE/browser reconnect. Publish a live URL only afterward.
   Do not seed/load-test the free production instance or upgrade billing.

Offline validation results and actual commands: [TESTING.md](../TESTING.md).

<a id="render-preparation-review-owner-explanation-and-small-exercise"></a>
## Owner explanation and small exercise

The default command can only verify and serve an existing exact-0006 database.
The separate setup command requires a fresh database, reviewed source SHA and
explicit attempt, and commits a claim before its transactional DDL. A crash cannot
silently turn restart into a retry. Its HTTP endpoint is status-only, not an admin
API. Caddy alone is public; the app trusts forwarding only from loopback and keeps
its normal Origin/session/CSRF policy.

Exercise: change the synthetic `PORT` in the packaging regression to another
unprivileged port and verify both generated Caddy listeners/host routes remain
correct. Then set it to 8000 and confirm rejection. Run the offline test only;
do not launch the app or connect to a database.

<a id="render-preparation-review-remaining-gates"></a>
## Remaining gates

No Docker/Caddy binary is installed locally. JSON/source checks cannot prove
native image compatibility, managed owner/grant behavior, Blueprint acceptance,
Linux peak memory or 0.1-CPU startup, Render header overwrite/stream flushing,
public HTTPS or integrated browser acceptance. Full load acceptance remains
unexecuted; Free production is excluded from that work. PostgreSQL expires after
30 days; no durable portfolio availability or backup promise is made.


---

<a id="testing-before-release-cleanup"></a>

## Verification guide before release cleanup

Historical snapshot; current commands/results are in [TESTING.md](../TESTING.md).

# Testing and verification

## Latest Render preparation - 15 November 2026

Windows PowerShell, Python 3.11 virtual environment and existing locked Node/npm
installation; no dependency download, database, server/browser startup, benchmark,
Docker build or cloud action. Results are actual local execution against both
pending deployment adapters, not a public CI or production certification.

| Directory | Exact command | Result |
| --- | --- | --- |
| backend | `.\.venv\Scripts\python.exe -B -m pytest -q tests/test_render.py tests/test_railway.py tests/test_production.py tests/test_ci_configuration.py tests/test_release_support.py --tb=short` | **347 passed**, 17.69 s; includes 93 Render cases |
| backend | `.\.venv\Scripts\python.exe -B -m pytest -q -m 'not database' --tb=short` | **2163 passed**, **32 deselected**, 151.22 s |
| frontend | `npm.cmd test -- --reporter=dot --maxWorkers=1` | **434 passed**, 18 files, 248.36 s |
| frontend | `npm.cmd run build` | TypeScript passed; Vite 50 modules, build 1.84 s |
| backend | `.\.venv\Scripts\python.exe -B -m app.render.check` | Passed offline Docker/Caddy/Blueprint contracts |
| backend | `.\.venv\Scripts\python.exe -B -m app.railway.check` | Passed retained Railway contract |
| backend | `.\.venv\Scripts\python.exe -B -m app.production.check` | Passed retained VPS contract |
| backend | `.\.venv\Scripts\python.exe -B -m pip check` | No broken requirements |
| root | `node --check load/board.js` | Passed syntax only, no load execution |
| root | `git diff --check` | Passed; Git emitted LF-to-CRLF notices only |

The initial focused run found test-fixture/import/argv mistakes; these were
corrected before the final 347-case and full-suite passes. No test was deleted or
weakened. One FastAPI/Starlette httpx deprecation warning remains; no dependency
change. Vitest printed environment performance advice; no isolation setting changed.

New local-only audit command from repository root:

```powershell
$renderEvidence = Get-Content backend/test-results/render-prep-current.txt
.\backend\.venv\Scripts\python.exe -B (Join-Path $renderEvidence 'check_repository.py')
```

It passed **340 source paths**, **206 Python files** parsed/compiled without
bytecode, **731 local import targets**, **266 Markdown file links**, JSON/Blueprint
parsing, both Docker COPY inventories, secret-pattern/artifact/new-file whitespace
checks, and all six migration paths. **324 starting source paths** remain;
**1018 historical local evidence hashes** match and remain ignored. All 14 prior
Railway additions are byte-identical. The audit helper/results are newly generated
ignored local files, not public diagnostic artifacts. The inventory is in
[RENDER_REVIEW.md](ENGINEERING_HISTORY.md#render-preparation-review).

Native Docker/Caddy executables are absent (`Get-Command docker,caddy` found
neither). No actual image build, Caddy native validation, Linux/container startup,
512 MB peak RSS/CPU observation, managed DB grants/setup, provider Blueprint
validation, HTTPS/header/SSE/browser acceptance or new public CI was run. No
performance result is claimed, and Free production must not be load-tested.
Detailed constraints, exact owner settings and setup/rollback: [RENDER.md](../RENDER.md).

## Previous Railway preparation - 15 November 2026

The new isolated Railway adapter passed the full offline suite: **2070 backend
cases passed**, 32 database cases deselected (57.87 s), plus **434 frontend cases**
with one worker and a passing TypeScript/Vite production build. Focused Railway/
VPS/CI checks passed 187 cases. The new adapter adds 95 synthetic offline cases;
no live database or platform behavior is certified. Exact commands, results,
source inventory, cost sources and pending native/platform gates are in
[RAILWAY.md](../RAILWAY.md). The repository-polish results below retain their earlier
scope; the owner reports baseline bb60ab3's five CI jobs passed, while this adapter
is uncommitted and has not run in hosted CI.

Offline tests check application behavior with service/connection doubles, API
contracts, evidence guards and repository configuration. They do not prove
PostgreSQL serialization, browser transport, TLS or load capacity.

## Reproducible offline commands

With locked dependencies already installed, run from the indicated directories:

| Directory | Command |
| --- | --- |
| backend | `.\.venv\Scripts\python.exe -B -m pytest -q -m 'not database' --tb=short` |
| backend | `.\.venv\Scripts\python.exe -B -m pytest -q tests/test_ci_configuration.py tests/test_release_support.py tests/test_production.py --tb=short` |
| backend | `.\.venv\Scripts\python.exe -B -m app.production.check` |
| frontend | `npm.cmd test -- --reporter=dot --maxWorkers=1` |
| frontend | `npm.cmd run build` |
| root | `node --check load/board.js` |
| root | `git diff --check` |

PowerShell users should check `$LASTEXITCODE` after each command. Linux uses
`.venv/bin/python` and `npm`. The frontend command uses one worker because earlier
parallel runs showed timing intermittency. Vitest/jsdom and Node harness tests
are not full browser acceptance. No lint script is currently configured.

## Evidence scope

The published baseline records 1,972 database-free backend passes, 32 database
cases deselected, 434 frontend passes across 18 files and a passing TypeScript/Vite
build. These are recorded historical local results in [PROGRESS.md](../PROGRESS.md).
The repository polish results are recorded below after actual execution.

Retained local PostgreSQL acceptance reports record:

| Suite | Historical result | Qualification |
| --- | --- | --- |
| Profiles | 30/30 at `0006_profiles` | Source/native-bound receipt |
| Realtime | 4/4 at `0005_invitations` | Historical source/native-bound receipt |
| Lifecycle | 10/10 at `0005_invitations` | Aggregate report, owner-confirmed exit; no independent source/native receipt |
| Invitations / G1 | 13 cases x 3; three 50-caller last-seat races | Aggregate/provenance limits in [G1_ACCEPTANCE.md](../G1_ACCEPTANCE.md) |

These results do not certify modified sources, current public CI or production.
Historical reports, manifests and hashes remain local and unchanged. Never
rewrite an old receipt to claim a new source binding.

## GitHub Actions contract

[ci.yml](../../.github/workflows/ci.yml) uses the JSON subset of YAML 1.2, allowing
standard-library offline parsing without a new dependency. The PostgreSQL service
now uses version 17 and the argument value equivalent to:

```yaml
options: >-
  --health-cmd=pg_isready
  --health-interval=5s
  --health-timeout=5s
  --health-retries=10
```

The previous quoted multiword command allowed `-U` to escape into Docker's flags.
The replacement has no embedded shell quoting or multiword health argument.
`pg_isready` checks server availability, not credentials or schema readiness;
bootstrap and guarded suites perform their own authenticated identity checks.

Four independent jobs retain exact revisions `0003_auth`, `0004_admission`,
`0005_invitations` and `0006_profiles`. The auth/team API suites alone account
for 53 expected cases; admission, invitations, lifecycle, realtime and profiles
remain required. Invitation acceptance includes the distinct authenticated
50-caller last-seat race.

The hosted Ubuntu runner binds the service port to loopback. The command obtains
the service container PID, resolves the host Python executable, then runs Python
through `sudo nsenter --net`. Only the network namespace changes; the runner's
filesystem, checkout, working directory and interpreter remain in use. Therefore
guarded `127.0.0.1:5432` connections reach PostgreSQL inside the container without
weakening the fixed identity checks. The same run/attempt value supplies the
service password and `CI_ADMIN_PASSWORD`; the application role gets a separately
generated random password. These are disposable CI inputs, not production secrets.

The wrapper requires GitHub-hosted CI markers, a fresh database/role namespace,
exact suite counts, native exit zero and completed invariant verification. It
rejects missing/ambiguous reports. Receipt upload runs even after failure and
fails if files are absent. No `continue-on-error` bypass is introduced.

**Public CI remains unverified.** The owner reported initialization failure on the
published workflow. This task corrects configuration and tests it offline; no
remote run was triggered or rerun. Docker availability, sudo/nsenter permissions,
Python visibility, container readiness, locked Linux installs, receipt handling
and real PostgreSQL suites must all pass on a new hosted execution.

## Live acceptance and performance

Consult [release validation](../RELEASE_VALIDATION.md) and [test database guards](../TEST_DATABASE.md)
before any database access. Each live suite has a fixed target/revision and fresh
fixture scope; default offline tests must not be used as race evidence.

Full integrated browser acceptance is incomplete. The original consumed campaign
must not be restarted or adopted; [integrated host](../INTEGRATED_HOST.md) and
[recovery history](ENGINEERING_HISTORY.md#batch-d-recovery) explain its limits. Mobile/keyboard/real
cookie and proxy checks remain pending.

[Seed/load tooling](../RELEASE_VALIDATION.md) targets a separate disposable
`merge_bench`, with 10,000 users, 2,000 teams and 100 clients. It has not been
executed for a measured report. The p95 < 200 ms figure is an acceptance target,
not a result. No seed, k6, PostgreSQL or browser execution was part of this polish.

## Repository polish validation - 15 November 2026

Actual environment: Windows PowerShell, Python 3.11.9, Node 22.15.0, npm 10.9.2;
existing locked dependencies, no installation or live operation.

| Exact command (directory as above) | Actual result |
| --- | --- |
| Backend full offline command above | **1,975 passed**, 32 deselected, 97.06 s, exit 0 |
| Backend focused CI/release/production command above | **159 passed**, 10.46 s, exit 0 |
| Frontend one-worker command above | **434 passed**, 18 files, 147.91 s, exit 0 |
| `npm.cmd run build` | TypeScript and Vite passed; 50 modules, Vite 3.48 s, exit 0 |
| `python -B -m app.production.check` using the backend venv | Offline JSON/topology/security contracts passed, exit 0 |
| `python -m pip check` using the backend venv | No broken requirements, exit 0 |
| `node --check <file>` for `load/board.js` and all six JS/MJS files in `frontend/test_support/` | Seven syntax checks passed; no browser/k6 execution |
| `git diff --check` | Passed |

The backend reports the existing Starlette/httpx deprecation warning. Git emits
existing LF/CRLF conversion notices. Neither warning was suppressed or used to
weaken checks. The additional three backend tests cover CI configuration only.

Static review compiles Python in memory, checks local backend import targets,
Markdown file links, required migration/suite/script paths, JSON configuration,
Docker COPY inputs, generated/private artifact exclusions and high-signal secret
patterns. Three matches in unchanged existing tests were inspected as synthetic
Origin/DSN/redaction fixtures; no real credential match was identified. This is a
targeted scan, not proof against every possible secret format.

Final static review passed for 310 tracked/new paths: 185 Python files compiled
in memory, 680 local backend import targets and 238 Markdown file links checked.
The tracked PowerShell script and nine new-guide PowerShell blocks parsed without
execution. All 35 required migration/suite/script/deployment paths checked exist.

All 958 preexisting local evidence files remain byte-identical and ignored.
The complete retained-path classification is in the [audit inventory](REPOSITORY_AUDIT.md).
New local baselines, result summaries and an executable offline review helper are
retained under ignored `backend/test-results/repo-polish-e61161879e0a416784e2bc8ff3e44e00/`.
From the root, the review helper is reproducible with:

```powershell
.\backend\.venv\Scripts\python.exe -B backend/test-results/repo-polish-e61161879e0a416784e2bc8ff3e44e00/check_repository.py
```

That local helper requires the retained baseline; it is intentionally not a public
CI prerequisite. No PostgreSQL/race/migration/seed/load/native Docker/Caddy/browser/
HTTPS execution or remote action ran. A passing hosted Actions run remains required.

The first local helper ignore comparison failed because Windows text-mode stdin
added carriage returns to Git path arguments. NUL-delimited byte input corrected
the helper; evidence bytes and ignore rules were not changed.

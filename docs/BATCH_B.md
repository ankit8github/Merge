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

## Migration, CI, scale and evidence contracts

The complete executable proposal is [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md).
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

# Consolidated Batch A — owner review, 2026-11-14

Recommendation: **CONDITIONAL**. Profiles/ranking and essential UX are implemented
and reviewed offline. No PostgreSQL, live SSE, browser, deployment or performance
acceptance is claimed. No commit, push, migration, fixture cleanup/reset or service
startup is authorized by this report. The official PS1 request for complementary
skill/time-zone ranking and explanations was rechecked against the
[organizer statement](https://hack4hack.com/hackathons/hack4hack-crew-hiring-challenge-2026-tp3m).

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

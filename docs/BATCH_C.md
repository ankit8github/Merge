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

## Owner explanation / exercise

Production isolation keeps test certificates meaningful: no old guard gains a
remote/production exception. A runtime cannot create schema; the separate migration
owner checks preserved rows before commit. Caddy is the sole trusted hop, so its
header replacement and disabled Uvicorn proxy handling are both necessary. An
offline exercise: change the synthetic compose API to publish8000 or change the
trusted proxy address; run test_production.py and explain why the contract fails.
Restore the edit. Explain why a healthy process is not a healthy schema, and why
ordinary merge_dev startup is never a production recovery command.

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

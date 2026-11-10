# Merge — Verified Progress, Risks & Next Actions

**Last updated:** 2026-11-10
**Competition:** Hack4Hack Crew Hiring Challenge 2026, PS1.
**Official deadline:** 2026-11-15 23:59 IST.
**Status policy:** Mark DONE only with recorded evidence. 'Planned', 'in progress', 'implemented', 'tested' and 'verified' are not interchangeable.

## Current verified context
- [x] User confirmed registration in Hack4Hack (screenshot in prior conversation; not stored in this repository).
- [x] User selected **PS1** for this project.
- [x] User chose public-facing project name **Merge**.
- [x] User chose VS Code with Codex coding support and component-by-component AI-assisted engineering.
- [x] Architecture direction chosen: React/TypeScript, FastAPI, PostgreSQL modular monolith.
- [x] Local Git repository at `I:/Merge` on `main`; initial verified commit `66d28b51728f466b3d0124de03f457dd190c22f1` created 2026-11-07 (M-004).
- [ ] Remote connected — none configured; no push performed.
- [x] Application code executed — FastAPI and Vite verified over local HTTP (M-002).
- [x] Automated tests passed — M-007B.3B final checkpoint: owner verified 33 throttles in 31.42s, 54 updated API cases in 30.94s and 78 session cases in 48.33s; 165 passed in 110.69s, three repetitions requested and fresh committed-state invariants verified. Codex reran 546 database-free checks in 8.52s, dependency/static and controlled-launcher HTTP/Vite checks; all passed. Existing Starlette/HTTPX warning and earlier proxy timing flakiness remain. No CI, deployed HTTPS/browser or 50-way team-race claim.
- [x] M-008B final checkpoint: owner verified guarded merge_test / 0003_auth (head), 57 passed in 40.99s, three repetitions requested and fresh committed-state invariants verified; reduced diagnostic 19 passed in 13.19s. Codex reran 554 database-free cases in 23.07s; dependency/static checks passed. Earlier interrupted run remains inconclusive history. G1 remains open.
- [ ] Any public deployment exists — **not verified**.
- [ ] PS1 submission completed — **not verified**.

## Milestones / exit criteria

| Gate | Scope | Required objective evidence | Status |
|---|---|---|---|
| G0 | Repository and local integration | Commit hash, README, backend health, React build, PostgreSQL connectivity, migration, smoke test | DONE — local checks recorded in M-003; initial commit `66d28b51728f466b3d0124de03f457dd190c22f1`; closed 2026-11-07 |
| G1 | Transactional team core | Real PostgreSQL 50-way last-seat race, cross-team race, idempotency; repeatable tests | PARTIAL — schema, M-007A internal services and M-008B extraction verified within their scope; idempotency and 50-way authenticated API acceptance pending |
| G2 | Business flows and security | Team lifecycle, invites, requests, leader succession, audit, authorization negative tests | PARTIAL — durable auth throttle and updated API/session suites owner-verified (165 passes); browser/deployed HTTPS and domain flows remain open |
| G3 | Frontend and realtime | Complete React flows, SSE between two clients, mobile/keyboard browser tests, scoring | NOT STARTED |
| G4 | Acceptance performance and CI | >=20 API tests in passing GitHub Actions, 10k/2k seed, k6 100 VUs, measured board p95 <200ms | NOT STARTED |
| G5 | Deployment and competition submission | Public URL, repo, one-page doc, load report, <=5-minute video, submitted links | NOT STARTED |

## Immediate Codex tasks (in order)
1. **M-001 — Repository audit:** Owner accepted audit. Existing source-of-truth files preserved; no application code or Git repository existed at inspection.
2. **M-002 — Minimal end-to-end skeleton:** IMPLEMENTED / LOCAL VERIFICATION PASSED, including database integration completed in M-003. FastAPI health, Vite React app, local PostgreSQL configuration, empty Alembic baseline, environment example, startup docs and tests. Owner approved existing PostgreSQL 17 instead of Compose; Docker unverified.
3. **M-003 — PostgreSQL integration (owner's task scope):** VERIFIED locally on 2026-11-06: authenticated SELECT 1, online baseline upgrade, repeated upgrade, current revision, full backend suite and frontend/HTTP regressions passed. Owner completed provisioning/schema recovery. Do not rerun provisioning. Earlier schema/lock design scope remains deferred: propose DDL/lock order and record ADR-016/017/020 before coding transactions.
4. **M-004 — Initial verified Git commit (owner's current task scope):** Initial local bootstrap commit created after source/index secret and artifact checks; G0 closed. Earlier concurrency-core scope is deferred, not implemented: after schema/lock ADR review, implement create/join with idempotency and real PostgreSQL race tests under a future task ID.
5. **M-005/M-005B — Schema and transaction design (owner's revised task IDs):** Owner approved active memberships, derived count/readiness, deferred leader FK and final-state guards, fixed lock order, frozen sizes and additive migration. Detailed implemented subset and unresolved service work: `SCHEMA.md`.
6. **M-006A — PostgreSQL domain schema (current bounded component):** IMPLEMENTED / TESTED locally: 0002 tables, functions/triggers, metadata consistency and 31 schema cases. No APIs, auth, replay service, audit generation, dispatch or React changes. Future lifecycle/concurrency services and frontend/SSE work require separately scoped tasks.
7. **M-007 — Challenge verification:** CI, seeds, k6 baseline/tuning, deployment, deliverables, owner-led live-change exercise.

## Test/benchmark evidence log
| Date | Component | Command / environment | Result | Evidence link or path |
|---|---|---|---|---|
| 2026-11-06 | Backend | From `backend`: `.\.venv\Scripts\python.exe -m pytest -q -m "not database"` | 7 passed, 1 deselected, 1 HTTPX deprecation warning; exit 0 | M-002 log below |
| 2026-11-06 | Migration config | From `backend`: `.\.venv\Scripts\python.exe -m alembic upgrade head --sql` | Generated baseline SQL; exit 0; no DB accessed | M-002 log below |
| 2026-11-06 | Python dependencies | From `backend`: `.\.venv\Scripts\python.exe -m pip check` | No broken requirements; exit 0 | `backend/requirements.lock` |
| 2026-11-06 | Frontend | From `frontend`: `npm.cmd run typecheck`, `npm.cmd test`, `npm.cmd run build`, `npm.cmd audit` | All exit 0; 6 tests passed; production assets built; audit 0 vulnerabilities | `frontend/package-lock.json` |
| 2026-11-06 | Local HTTP | From root: `.\backend\.venv\Scripts\python.exe scripts/check_local_http.py` | API health, frontend HTML, Vite proxy, outage and recovery passed; exit 0 | `scripts/check_local_http.py` |
| 2026-11-06 | PostgreSQL readiness | `pg_isready -h 127.0.0.1 -p 5432` | Accepting connections; not authenticated SQL proof | M-002 log below |
| 2026-11-06 | Database / online migrations, earlier checkpoint | SELECT 1 test; `alembic upgrade head` twice; `alembic current` | Initially NOT RUN; superseded by verified M-003 results below | Historical checkpoint |
| 2026-11-06 | Authenticated DB smoke | From `backend`: `.\.venv\Scripts\python.exe -m pytest -q -m database` | 1 passed, 14 deselected, 1 existing warning; exit 0 | M-003 final verification below |
| 2026-11-06 | Online migration | From `backend`: `.\.venv\Scripts\python.exe -m alembic upgrade head`, then the same command again, then `.\.venv\Scripts\python.exe -m alembic current` | Each exit 0; current `0001_baseline (head)` | M-003 final verification below |
| 2026-11-06 | Full backend suite | From `backend`: `.\.venv\Scripts\python.exe -m pytest -q` | 15 passed, 1 existing warning; exit 0 | M-003 final verification below |
| 2026-11-06 | Frontend regression | From `frontend`: `npm.cmd run typecheck`, `npm.cmd test`, `npm.cmd run build` | All exit 0; 6 tests passed; production build completed | M-003 final verification below |
| 2026-11-06 | HTTP regression | From root: `.\backend\.venv\Scripts\python.exe scripts/check_local_http.py` | Initial outage timeout; harness deadline adjusted; final run passed all three stages, exit 0 | M-003 final verification below |

## Risk register
| Risk | Impact | Mitigation | Status |
|---|---|---|---|
| Deadline / feature overload | Incomplete submission | Must-haves first; task-size limits; daily gate review | OPEN |
| Transaction lock-order errors | Over-capacity, deadlocks | Single mutation service, real-DB adversarial tests | OPEN |
| Cross-team uniqueness not DB-enforced | Duplicate membership | Unique index and concurrent test | OPEN |
| Unverified hosting / cold starts | Broken live demo or benchmark | Deploy a skeleton early; report environment accurately | OPEN |
| Cookie auth / CSRF / CORS | Security or broken login | Security design and browser tests | OPEN |
| SSE disconnected / multiple instances | Stale UI | Re-fetch authoritative state, declare deployment topology | OPEN |
| AI-generated code not understood | Interview failure | Owner explanation and live change after each component | OPEN |
| Missing reproducibility | Judging penalty | Preserve scripts, commands, CI logs and reports | OPEN |

## M-002 evidence — 2026-11-06

Goal: local process health, React health display, environment-based SQLAlchemy setup, empty Alembic baseline, reproducible dependencies and safe Windows instructions. No domain features.

Implementation / files:
- Added `.gitignore`, `.env.example`, `README.md`, `backend/`, `frontend/`, and `scripts/check_local_http.py`.
- Updated architecture implementation status and recorded owner-approved local setup clarification in `DECISIONS.md`. Preserved `AGENTS.md`, `REQUIREMENTS.md` and `.vscode/extensions.json`.
- Initialized Git using `git init --initial-branch=main`. Final `git -c safe.directory=I:/Merge rev-parse --show-toplevel` returned `I:/Merge`; `symbolic-ref --short HEAD` returned `main`; `remote -v` returned nothing. Source files are untracked because there is no initial commit or staging.

Environment / installation actually executed:
- Windows PowerShell; Python 3.11.9, Node 22.15.0, npm.cmd 10.9.2, uv 0.9.29; local PostgreSQL 17 server.
- `python -m venv backend/.venv` completed.
- `uv pip compile backend/pyproject.toml --extra dev --python backend/.venv/Scripts/python.exe --output-file backend/requirements.lock` executed; final refresh added `--upgrade --quiet` to update transitive pins.
- From root: `.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock` and `.\backend\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e backend` completed after fixing build dependencies.
- From `frontend`: `npm.cmd install --package-lock-only` and `npm.cmd ci` completed. Direct dependencies are exact pins; transitive versions are recorded in both lockfiles.
- Sandbox shell initialization failed after Git setup (`setup refresh had errors`); verification used approved elevated shell execution. Git then required per-command `-c safe.directory=I:/Merge` because sandbox-created `.git` has different ownership. No global Git settings or execution policy were changed.

Failures encountered and corrected:
- Initial editable install failed with missing `bdist_wheel`; pinned setuptools/wheel were added and installation then passed.
- Initial npm command with `--prefix frontend` looked for a root package.json and failed; subsequent commands ran from `frontend` and passed.
- Initial npm pins reported vulnerabilities; Vite/Vitest were updated, lockfile regenerated and final `npm.cmd audit` reported zero vulnerabilities. No force-fix command was run.
- Preliminary backend runs had 5 tests; final result after configuration tests is 7 passed, 1 database test deselected. Installed Starlette emits one warning that its HTTPX TestClient integration is deprecated. Warning was not suppressed.

Review / scope:
- Inspected source additions and file inventory. `git -c safe.directory=I:/Merge diff --check` exited 0, but has no tracked diff before an initial commit; a separate Python whitespace scan covered untracked source and found no trailing whitespace.
- `git -c safe.directory=I:/Merge check-ignore .env .env.local backend/.venv/pyvenv.cfg frontend/node_modules/vite/package.json frontend/dist/index.html` confirmed all five paths ignored. `.env.example` remains visible to Git.
- No actual `.env` was created, secrets printed, database objects changed, commits made, or remotes configured/pushed. Docker/Compose not installed or tested; no Compose file added.

Incomplete verification / limitations:
- No environment credential configuration or explicit password-file entry for `merge_dev` / `merge_app` was available. Did not guess credentials or try an administrator account. Existence/ownership of database and role remains unverified.
- Database smoke and online baseline/repeated upgrade require owner provisioning using safe preflight and exact instructions in `README.md`. Offline SQL is not migration/connectivity proof.
- Frontend state tests use jsdom/mocked fetch. Separate real HTTP verification covers proxy outage and recovery; no full browser/mobile/keyboard E2E or visual QA is claimed.
- Vite proxy does not establish production routing. No load/race tests, CI, domain schema, authentication, deployment or production readiness claimed.
- G0 remains PARTIAL, including its required commit evidence, which waits for owner approval.

Owner explanation / exercise: distinguish process liveness from database readiness; stop/restart the API and retry from the page. Change its timeout from five to two seconds and update the corresponding test.

Commit hash: none. Proposed message: `chore: bootstrap Merge frontend and backend (M-002)`.

Next: owner provisions dedicated Merge database/role and configures credentials privately, then run database smoke test, baseline upgrade twice and current-revision check.

## M-003 evidence — 2026-11-06, blocked before provisioning

Objective: inspect dedicated PostgreSQL objects, configure `backend/.env` after safe provisioning, then verify real SELECT 1, online baseline, repeated upgrade, current revision and full backend suite. No application features or new dependencies.

Changes: `backend/app/core/config.py` now loads ignored `backend/.env` by absolute path; added its working-directory regression test in `backend/tests/test_config.py`. Updated `.env.example`, README local commands and the dated decision clarification. Added `scripts/inspect_merge_postgres.sql`, an owner-run read-only metadata query for connection identity, Merge database ownership, role flags and memberships. The script is prepared but NOT executed against PostgreSQL.

Access evidence: `pg_isready -h 127.0.0.1 -p 5432` returned accepting connections (exit 0). Root `.env` and `backend/.env` are absent. Only environment variable names were inspected: no `MERGE_*`, `PG*` or `DATABASE*` variables were present. Password-file metadata check found zero explicit local credential candidates for maintenance/Merge access; no passwords or unrelated entries were printed. No login was attempted by guessing an account or password. Therefore existence/ownership of `merge_dev`, `merge_owner` and `merge_app` remains UNKNOWN, not absent.

Actual verification on Windows, Python 3.11.9:
- From `backend`: `.\.venv\Scripts\python.exe -m pytest -q -m "not database"`: 8 passed, 1 database test deselected, 1 existing Starlette/HTTPX deprecation warning; exit 0.
- From `backend`: `.\.venv\Scripts\python.exe -m pip check`: no broken requirements; exit 0.
- From root: `.\backend\.venv\Scripts\python.exe scripts/check_local_http.py`: real API health, frontend HTML/proxy, API outage and recovery passed; exit 0. Temporary child servers stopped by the script.
- `git -c safe.directory=I:/Merge check-ignore backend/.env`: returned `backend/.env`; exit 0. Local secret file not created because provisioning is not yet verified.
- Git root `I:/Merge`; branch `main`, no commits, no remotes. Source files remain untracked. No staging, commits or pushes.

NOT RUN: authenticated object inspection; database provisioning; real SELECT 1 test; either online `alembic upgrade head`; `alembic current`; full backend suite. Credential-dependent operations remain blocked. No database/role/global-setting changes, destructive operations, Docker installs, or credential replacements occurred. Sandbox shell initialization failed; approved elevated read/test commands used the same per-command Git ownership exception as M-002, with no global changes.

Next owner step: run the exact read-only PowerShell/psql command in README using a known administrator account. Enter the password only into psql's local prompt. If any Merge objects exist, stop and review metadata before provisioning; if none exist, follow the README's guarded manual creation steps. Configure the new application password privately in `backend/.env` after provisioning, then resume integration verification. G0/Phase 0 is NOT complete.

Owner explanation/exercise: distinguish a responding PostgreSQL server from authenticated database access; inspect `rolsuper`, `rolcreatedb`, `rolcreaterole` and granted memberships to explain why the application account is not an administrator.

## M-003 provisioning handoff — 2026-11-06

Owner-reported evidence (not independently rerun by Codex): read-only inspection succeeded as `postgres` against database `postgres`, server `127.0.0.1:5432`; no matching Merge database or roles found; transaction completed without modifications. This supersedes the earlier unknown-existence report for that inspection time, but creation must recheck because server state can change.

Prepared `scripts/provision_merge_postgres.sql`: validates connection identity and absence of all three names, creates only new `merge_owner`/`merge_app`, uses hidden psql password entry with transaction-local SCRAM setting, creates dedicated `merge_dev`, and grants only CONNECT plus public-schema USAGE/CREATE. Non-login database owner is retained from the documented setup. No role membership grants, global changes or other-database changes. Role creation is transactional; database creation must be outside that transaction, so partial errors require owner inspection, never an automatic retry/drop.

Prepared `scripts/configure_backend_env.py`: interactive masked entry of the application password twice, Git exclusion check, exclusive creation of `backend/.env`, no credential output. Rejects empty/mismatched passwords, control characters and dotenv interpolation syntax. Updated README with exact commands and explanations. Added `backend/tests/test_local_env_helper.py` to verify secret roundtrip without output leakage, existing-file preservation, Git-ignore enforcement and unsafe-input rejection using synthetic test values only. No dependency changes.

Executed from `backend`: `.\.venv\Scripts\python.exe -m pytest -q -m "not database"` — 14 passed, 1 database test deselected, 1 existing HTTPX deprecation warning; exit 0. SQL script was source-reviewed only; provisioning, real configuration helper, SELECT 1, online migration twice, current revision and full suite remain NOT RUN, pending local owner password entry. No actual credentials supplied to Codex, no DB objects modified, no commits or pushes. Phase 0 remains incomplete.

Owner next step: run guarded provisioning and masked configuration commands in README, then report completion or a non-secret error so Codex can execute the database checks. Explain why `merge_app` can migrate tables without owning the database or being a superuser.

## M-003 partial-provisioning recovery audit — 2026-11-06

Owner-reported read-only results: `merge_dev` exists and is owned by `merge_owner`; `merge_owner` is NOLOGIN; `merge_app` is LOGIN; neither role has SUPERUSER, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS or role memberships. Original provisioning stopped at line 36 during administrator reconnection. These results are owner-verified, not a new Codex database query.

Read the entire 53-line `scripts/provision_merge_postgres.sql`, including lines after the failure. Given the reported stop location and ON_ERROR_STOP, the execution path is:
- Lines 5–30: transaction, identity/existence preflight, creation of both roles, transaction-local password-encryption selection, hidden application-password entry and non-null password check, then COMMIT completed.
- Line 33: CREATE DATABASE completed. Line 34: database PUBLIC privileges revoked. Line 35: CONNECT granted to merge_app. These run outside the roles' transaction and were committed before the reconnect. Their execution is inferred from the reported stop point, while their current effective privileges still require inspection.
- Line 36: psql `\connect merge_dev` attempted and failed; it is a client meta-command, not SQL.
- Lines 37–53: skipped entirely — BEGIN, database/owner validation, REVOKE ALL ON SCHEMA public FROM PUBLIC, GRANT USAGE/CREATE to merge_app, COMMIT and both final verification queries. No schema-grant success can be claimed.

Prepared `scripts/inspect_merge_recovery.sql` and documented its direct-to-merge_dev psql command in README. It uses a REPEATABLE READ READ ONLY transaction, checks local server/database identity, and selects only connection/privilege/ownership/role metadata, user schemas, relations, routines, types and extensions. No application row contents, password/hash values or routine definitions selected. Source reviewed; SQL NOT RUN because authentication is unavailable.

Actual local availability inspection: `backend/.env` absent, configured app password absent, no PG credential/service environment variables, and no matching local password-file credential for merge_app/postgres against merge_dev. Only flags/names printed; no password output. Therefore current CONNECT, schema USAGE/CREATE, public-schema owner/ACL and existing user objects remain UNKNOWN until owner-run inspection. No login guessing or recovery/provisioning/migration command attempted.

Proposed recovery is conditional on inspection and owner approval: preserve valid roles/database/ownership; omit CONNECT grant if already effective; grant only missing schema permissions; separately review the skipped PUBLIC schema hardening, preserving explicit app access if its existing USAGE is inherited from PUBLIC. Stop for unexpected owners, elevated privileges, memberships or unexplained user objects. No recovery SQL executed or automatically scheduled. PostgreSQL default `public` owner `pg_database_owner` alone is not a conflict.

Changed only recovery-inspection SQL, README and this evidence log. No dependencies, runtime behavior or tests changed. Database SQL tests, migrations and full-suite execution remain NOT RUN for this recovery audit; no repeat backend build/test needed for these documentation/SQL-query additions. Phase 0 remains incomplete. No commits or pushes. Owner exercise: explain why committed database grants survive a later failed client reconnect and why effective schema USAGE might come from PUBLIC.

## M-003 final local verification — 2026-11-06

Owner-reported prerequisite: provisioning and schema recovery committed successfully; `merge_dev` owned by `merge_owner`; `merge_app` has CONNECT plus explicit public-schema USAGE/CREATE; PUBLIC schema privileges revoked; Merge roles lack elevated administrative privileges; no unexpected objects. Codex did not repeat provisioning or change any role, password, ownership or privilege.

Confirmed `Test-Path -LiteralPath backend/.env` returned True. `git -c safe.directory=I:/Merge check-ignore -v backend/.env` reported `.gitignore:1:.env`; `git -c safe.directory=I:/Merge ls-files -- backend/.env` returned nothing. No secret file content, password or connection string was printed.

Actual commands, sequential for database operations, from `I:\Merge\backend` using Python 3.11.9:
1. `.\.venv\Scripts\python.exe -m pytest -q -m database` — real PostgreSQL SELECT 1 passed: 1 passed, 14 deselected, 1 warning; exit 0.
2. `.\.venv\Scripts\python.exe -m alembic upgrade head` — online run exited 0, no console output.
3. `.\.venv\Scripts\python.exe -m alembic upgrade head` — repeat online run exited 0, no console output.
4. `.\.venv\Scripts\python.exe -m alembic current` — `0001_baseline (head)`; exit 0.
5. `.\.venv\Scripts\python.exe -m pytest -q` — complete backend suite: 15 passed, 1 warning; exit 0.
6. `.\.venv\Scripts\python.exe -m pip check` — no broken requirements; exit 0.

Frontend regression from `I:\Merge\frontend`, Node 22.15.0/npm.cmd 10.9.2: `npm.cmd run typecheck`, `npm.cmd test` and `npm.cmd run build` all exited 0. Vitest: 1 file, 6 tests passed. Vite built 29 modules and production assets. Commands stopped on nonzero exit; none failed.

HTTP regression from root: `.\backend\.venv\Scripts\python.exe scripts/check_local_http.py` initially exited 1: API/HTML/proxy success passed, but the outage request exceeded the harness's two-second client deadline. Updated only `scripts/check_local_http.py`: `get` accepts a timeout argument and the outage request has a bounded ten-second deadline. It still requires an actual HTTP error status; a client timeout is not accepted as success. Repeated the command: API health/HTML/proxy, outage error and restart recovery all passed; exit 0. Temporary owned servers were stopped by cleanup. No frontend/API feature behavior changed.

Additional read-only SQL through the configured engine, in a READ ONLY transaction: authenticated identity `merge_dev` / `merge_app`; `SELECT version_num FROM public.alembic_version` returned `0001_baseline`; public table inventory contained only `alembic_version`. No domain tables added. The online baseline/version tracking is the only database write in this verification task.

Git/secret review: root `I:/Merge`, `main`, no commits or remotes. `git -c safe.directory=I:/Merge status --short --branch` showed only untracked source groups (`.env.example`, `.gitignore`, `.vscode/`, `AGENTS.md`, `README.md`, `backend/`, `docs/`, `frontend/`, `scripts/`). No staging/commits/pushes. Enumerated 40 source candidates using `git ls-files --cached --others --exclude-standard`; none contained the configured password and none were local `.env` or generated artifacts. This checks the configured secret, not every possible unknown secret. Root-level `check-ignore -v` confirmed actual backend/.env, backend/.venv, frontend/node_modules and frontend/dist paths excluded. `git diff --check` exited 0 (there is no tracked baseline yet).

Warnings/incomplete gates: existing Starlette TestClient HTTPX deprecation warning remains unsuppressed; no test failure. Docker, deployment, CI, race/load tests and full browser/mobile/keyboard E2E are not verified by this task. All G0 local execution checks are verified, but G0's recorded commit-hash criterion remains pending explicit owner commit approval. No Phase 1 features implemented; schema/lock protocol ADRs still required before domain implementation.

Changes this task: HTTP verification harness deadline and this progress record only. No dependencies or application migrations changed. Owner explanation/exercise: explain why repeating `upgrade head` leaves revision at `0001_baseline`, then use `alembic current` to verify it without modifying schema. Proposed eventual commit message remains `chore: bootstrap Merge frontend and backend (M-002/M-003)`; no commit created.

## M-004 initial verified commit and G0 closure — 2026-11-07

Owner authorized the first local commit and a separate documentation commit recording its hash. No remotes, pushes or database-object changes authorized or performed. Scope is Git review/commit only; no new application features, dependencies or migrations.

Initial commit: `66d28b51728f466b3d0124de03f457dd190c22f1` on `main`, message exactly `chore: bootstrap Merge frontend and backend (M-002)`. Created successfully with 40 intended source/configuration-example/test/documentation files and 4468 insertions. Working tree was clean immediately afterward. This follow-up progress update is committed separately, preserving the initial commit hash.

Review/evidence actually executed:
- Read AGENTS.md and this progress log; inspected `.gitignore`, `git status --short --branch`, root, unstaged/staged diffs, full candidate file list and remotes, using the existing per-command `git -c safe.directory=I:/Merge` ownership exception.
- Reviewed all source additions and setup documents; parsed npm's 187 lock entries, confirmed exact manifest pin agreement and that all resolved URLs use HTTPS registry.npmjs.org with SHA-512 integrity.
- Inline Python pre-stage scan covered all 40 candidates for the actual configured application password, credential-bearing URLs, private keys, provider-token patterns, secret/artifact filenames and generated directories; no findings. `.env.example` password is blank; synthetic test values are deliberate fixtures, not live credentials. Git author/committer identity was already configured; no identity/global settings changed.
- Staged only the explicit 40 reviewed file paths with `git add -- ...`; did not use broad directory staging or force-add ignored files. Scanned the actual staged blobs again before committing, with no findings. `git diff --quiet` confirmed the reviewed working files matched the index; `git diff --cached --check` passed. Confirmed `backend/.env` ignored and absent from tracked/index paths. No virtual environment, cache, node_modules, build output, database dump, local environment file or known real credential was staged.
- `git -c safe.directory=I:/Merge commit -m "chore: bootstrap Merge frontend and backend (M-002)"` exited 0; `git -c safe.directory=I:/Merge rev-parse HEAD` returned the full initial hash above; `git -c safe.directory=I:/Merge status --short --branch` returned only `## main`.
- Git emitted LF-to-CRLF working-copy conversion warnings during staging; staged whitespace validation passed. No line-ending/global Git settings changed.

G0 closure: all local runtime gates have actual M-003 evidence (15 backend tests, 6 frontend tests, TypeScript/build, real HTTP success/outage/recovery, authenticated PostgreSQL SELECT 1, online baseline upgrade twice, `0001_baseline (head)`, dependency check). The initial commit supplies the final missing evidence. Tests/builds/migrations were NOT rerun for this Git-only task; existing verified results are retained, not presented as new runs. No database connection or database mutation was made during this task.

Outstanding limitations: one known Starlette/HTTPX TestClient deprecation warning; Docker/Compose, CI, browser/mobile/keyboard E2E, deployment, concurrency correctness, load benchmarks and Phase 1/domain features remain unverified or unimplemented. G1–G5 remain open. No remote configured or push performed.

Owner explanation/exercise: `git show --stat 66d28b5` shows the bootstrap snapshot; the next documentation commit records that immutable hash without rewriting it. Explain why `backend/.env` remains local and why a clean working tree alone is not a secret scan.

## M-006A schema implementation and verification — 2026-11-07

Scope: approved active-only relational schema and PostgreSQL guards, no domain APIs or application services. Files: new `backend/app/models/{__init__,domain}.py`, `backend/alembic/versions/0002_domain.py`, `backend/tests/test_domain_schema.py`, `docs/SCHEMA.md`; updated `backend/app/db/{base,session}.py`, `backend/alembic/env.py`, architecture/decisions/progress. No new dependencies, role/permission/credential changes, commits or pushes.

Preflight actually executed through configured SQLAlchemy engine, READ ONLY: authenticated `merge_dev`/`merge_app`; revision `0001_baseline`; only public relations `alembic_version` and its existing primary-key index; zero public routines. No conflicting domain objects found. No database reset, unrelated object replacement or data removal performed.

Implementation: seven tables (minimal users, hackathons, teams, active memberships, idempotency records, audit events, outbox). Counts/readiness derived. Immediate `(hackathon_id,user_id)` membership PK; composite hackathon and frozen-size FKs; initially deferred exact-team leader FK; immutable identities/current membership rows; irreversible team tombstones; append-only/immutable transactional support; five fixed-search-path VOLATILE SECURITY INVOKER functions; 18 user triggers including seven statement-level TRUNCATE guards. Deferred validators re-read current final rows, not queued row images. Parent membership guards lock teams NO KEY UPDATE. READ COMMITTED is explicit on the runtime engine. SQLSTATE/constraint names and lock caveats: `SCHEMA.md`.

Migration evidence, commands from `I:\Merge\backend` using the existing Python 3.11.9 venv:
- `.\.venv\Scripts\python.exe -m alembic upgrade head --sql > .pytest_cache/0002-review.sql`: offline render passed, exit 0; ignored artifact reviewed. No database changes from this command.
- `.\.venv\Scripts\python.exe -m alembic upgrade head`: applied the additive 0002 transaction, exit 0; no console output.
- `.\.venv\Scripts\python.exe -m alembic current`: `0002_domain (head)`, exit 0.
- Schema test `test_migration_upgrade_repeat` executes `alembic upgrade head` twice and `alembic current` as subprocesses, all exit 0. It does not reset or recreate the schema.
- `.\.venv\Scripts\python.exe -m alembic check`: final result `No new upgrade operations detected.`, exit 0; FK/type/default differences are not excluded.
- `git -c safe.directory=I:/Merge diff --exit-code -- alembic/versions/0001_baseline.py` from backend: exit 0. Existing 0001 file unchanged; 0002 explicitly references it. Destructive downgrade intentionally refuses and needs a separately approved procedure.

Actual test outcomes and correction:
- First `.\.venv\Scripts\python.exe -m pytest -q tests/test_domain_schema.py --tb=short`: 26 passed, 1 metadata-consistency failure. Alembic reported 22 FK remove/add differences because reflected default public schema was unnamed while ORM targets explicitly named public. Diagnostic comparison confirmed matching FK targets/options. No design invariant or PostgreSQL constraint failed.
- Corrected only metadata representation: default-schema ORM metadata now matches PostgreSQL reflection; engine schema translation explicitly targets public even with caller search_path excluding it. Frozen migration/actual FK constraints were NOT relaxed or recreated.
- Repeated focused command: 27 passed, exit 0. First full suite: 42 passed, 1 existing HTTPX warning; exit 0.
- Added four more cases for explicit ORM public resolution, membership in distinct hackathons, invalid live-empty departure and audit/outbox schema constraints. Final `.\.venv\Scripts\python.exe -m pytest -q --tb=short`: **46 passed, 1 existing Starlette/HTTPX deprecation warning**, exit 0. This includes 31 schema cases and all 15 prior tests. No test was weakened/deleted to pass.
- `.\.venv\Scripts\python.exe -m pip check`: no broken requirements, exit 0.

Real PostgreSQL coverage: founding membership; actual failing COMMIT for founderless team and direct overflow; cross-team PK conflict; invalid leader FK; forbidden membership move; valid/invalid soft deletion and blocked resurrection; TRUNCATE rejection on all seven protected tables; temporary overflow followed by departures/succession in the same transaction; composite hackathon consistency; frozen sizes; team identity/hard-delete protection; pending/completed idempotency state; immutable audit; allowed outbox attempt update; fixed function search path; full metadata and leader-FK deferral; repeated upgrade.

Cleanup/safety: tests use UUID fixture rows in outer transactions, forcing genuine deferred validation via SET CONSTRAINTS ALL IMMEDIATE before rollback. The two failing-COMMIT tests exercise PostgreSQL rollback of those transactions. Successful fixtures are not durably committed. TRUNCATE tests verify guard presence before asserting statement rejection; cleanup never uses TRUNCATE or disables triggers. After the final suite, actual READ ONLY count queries returned **0 rows in each of all seven domain tables**, 18 noninternal domain triggers and revision `0002_domain`. No unrelated data existed in the new tables before migration; the preexisting Alembic tracking table remains.

Phase 0 regression commands from frontend: `npm.cmd run typecheck`, `npm.cmd test`, `npm.cmd run build` — all exit 0; 6 frontend tests passed and 29-module production build completed. From root: `.\backend\.venv\Scripts\python.exe scripts/check_local_http.py` — API health/frontend HTML/proxy, outage error and recovery all passed, exit 0. No frontend source changed.

Limits/risks: these are real schema tests, not authenticated API/race proofs. Independent multi-connection final-seat/leader races, actual successful durable domain-operation commits, complete service lock ordering/retries, audit generation, replay and event publication remain future work. Deferred capacity's snapshot argument assumes the approved READ COMMITTED isolation; tests/runtime use it, and other isolation modes are not certified. Raw DELETE can lock membership before its trigger locks the team and may deadlock; later services must prelock team/participant rows in canonical order and retry entire transactions. Privileged DDL/trigger disabling is outside the runtime integrity boundary. One existing HTTPX deprecation warning and Windows LF/CRLF warnings remain. G1 is not closed.

Owner explanation/exercise: inspect `merge_validate_team` and explain why its count runs after the parent lock in a separate query, and why a queued founderless/overflow row can become valid before final validation. Add a case inserting a temporary third member then deleting that member before validation; verify no committed overflow and no stored counter to repair.

Proposed commit message: `feat: add PostgreSQL domain schema and integrity guards (M-006A)`. Not committed. G0 baseline commits preserved; no push.

## M-006B isolation preflight — 2026-11-07

Stopped before implementing or running adversarial tests, following the task's
explicit disposable-database fallback when reliable cleanup is unavailable.
Initial `git -c safe.directory=I:/Merge status --short --branch` returned only
`## main`. `git -c safe.directory=I:/Merge log -1 --format="%H %s"` confirmed
committed M-006A at `41b6bdc6849340ff6018d84c1f5b74e28bfcdfea`, message
`feat: add PostgreSQL domain schema and integrity guards (M-006A)`.

Read AGENTS and requirements/architecture/decisions/schema/progress, existing
schema fixtures, engine/configuration and migration guards. Authenticated
inspection executed from backend via a PowerShell here-string piped to
`.\.venv\Scripts\python.exe -`, using `build_engine(Settings())` and
`SET TRANSACTION READ ONLY; SET LOCAL statement_timeout = '10s'`.
`SELECT current_database()` returned `merge_dev`; engine isolation was
READ COMMITTED; `SELECT version_num FROM public.alembic_version` returned
`0002_domain`. Individual `SELECT count(*) FROM public.<table>` queries returned
zero for all seven domain tables. A pg_trigger query confirmed one enabled
noninternal DELETE trigger on public.teams. Transaction rolled back; exit 0.
No credentials or connection strings printed; no database objects/data changed.

Isolation blocker: existing successful fixtures use an outer rollback-only
transaction. Independent sessions need committed shared seed rows for the
requested commit-order races. Migration guards prohibit physical team deletion
(`guard_team_soft_delete`) and changes to tombstones (`guard_team_tombstone`);
retained teams reference their hackathon and creator. Therefore committing
fixtures in merge_dev cannot be followed by complete ordinary-DML cleanup.
Unique UUIDs alone do not solve retained test data. Disabling guards, changing
schema or leaving permanent fixtures is not authorized and was not attempted.

Proposed next scope requires owner approval: provision an explicitly disposable,
uniquely named local test database; approve a narrow test-only target guard
(current Settings permits only merge_dev); apply the existing unchanged
0001/0002 migrations there; run bounded independent-connection races against
UUID-scoped committed fixtures; verify final invariants and collect SQLSTATEs
and lock observations; repeat against fresh disposable databases. Whole-database
cleanup must be separately authorized and restricted to those test databases.
Do not reset merge_dev or weaken any domain guard for cleanup.

No new tests, race repetitions, SQLSTATE outcomes or deadlock observations are
claimed. Backend/frontend/HTTP regressions were not rerun after this stop;
M-006A results above remain historical evidence only. M-006B success gate and
G1 remain open. Only this progress entry changed; no application/schema,
role/permission/credential changes, commits or pushes.

Owner explanation/exercise: explain why a rollback-only fixture is invisible
to another connection and why soft deletion cannot provide full fixture cleanup
under immutable tombstones.

## M-006B.1 dedicated test database preparation — 2026-11-08

Owner approved merge_test exclusively for automated integration/concurrency tests,
with privileged execution held for review. Preserved the existing uncommitted
M-006B blocker entry. HEAD remains M-006A
41b6bdc6849340ff6018d84c1f5b74e28bfcdfea; no commit/push.

Added scripts/inspect_merge_test.sql and scripts/provision_merge_test.sql,
backend/test_support/{__init__,database}.py, backend/test_alembic/env.py,
backend/tests/test_test_database_safety.py and docs/TEST_DATABASE.md. Updated
README, architecture, decisions and progress. No dependencies added. Ordinary
Settings, engine, Alembic environment, 0001/0002 and all domain guards unchanged.

Actual read-only preflight: from backend, a PowerShell Python here-string used
Settings credentials privately to build a maintenance postgres connection (not
merge_dev), SET TRANSACTION READ ONLY, a 10-second statement timeout, and
SELECT datname FROM pg_database WHERE datname='merge_test'. Result: connected
database postgres; merge_test exists False; rollback; exit 0. No password/URL
printed. Owner scripts repeat existence checks immediately before provisioning.
psql resolved to C:\Program Files\PostgreSQL\17\bin\psql.exe.

Prepared provisioning reuses non-elevated existing roles, creates only merge_test
owned by merge_owner, and scopes CONNECT/public USAGE/CREATE to merge_app there.
No role/password changes. All scripts stop on errors; partial CREATE DATABASE
cannot be rolled back with later ACLs, so failed provisioning requires inspection,
never automatic rerun. Exact owner-review commands and guarded disposal design
are in TEST_DATABASE.md. No executable DROP procedure provided or executed.

Test tools require --confirm-merge-test, fixed local address/port/database/role,
private interactive password or separate MERGE_TEST_DB_PASSWORD, no dotenv or
ordinary application settings. Every utility connection checks actual server
identity and READ COMMITTED; separate online Alembic environment rechecks before
writing. Fresh-target conflict checks reject public relations/routines; only base
or exact 0002 head is accepted. Verification transaction is read-only. Future
independent fixtures must use this connection helper; adversarial tests not added.

Actual commands from backend:
- `.\.venv\Scripts\python.exe -m pytest -q tests/test_test_database_safety.py tests/test_config.py tests/test_health.py --tb=short`: 17 passed, 1 existing HTTPX warning.
- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`: first 24 passed, 32 deselected, 2 warnings. Added explicit Alembic path_separator=os to remove its configuration warning; repeat: 24 passed, 32 deselected, 1 existing HTTPX warning, exit 0. These are pure safety/configuration/health tests, not PostgreSQL concurrency evidence.
- `git -c safe.directory=I:/Merge diff --exit-code HEAD -- backend/app backend/alembic backend/requirements.lock`: exit 0, baseline application/migrations/dependencies unchanged.
- `git -c safe.directory=I:/Merge diff --check`: exit 0; Git LF/CRLF working-copy warnings remain. `git ... check-ignore backend/.env` confirmed ignored.

Not executed: privileged SQL scripts, test provisioning, online test verification,
test migrations/repeat, real database tests, adversarial tests, frontend/HTTP
regressions or database disposal. merge_dev was not connected to or modified by
this task. No database/schema/role/permission/credential changes. M-006B remains
open pending owner review, provisioning and actual online verification.

Owner exercise: omit --confirm-merge-test; explain why the CLI refuses before
reading credentials, and why an initial identity check is repeated per connection.

## M-006B.1R read-only recovery correction — 2026-11-08

Added scripts/inspect_merge_test_recovery.sql and
backend/tests/test_recovery_inspection_safety.py; updated TEST_DATABASE.md and
this progress entry. Existing M-006B/M-006B.1 pending work preserved. Original
inspect_merge_test.sql preflight refusal and provisioning SQL unchanged in this
correction. No application/migration/dependency changes.

Recovery script uses ON_ERROR_STOP and explicit REPEATABLE READ READ ONLY,
transaction-local statement/lock deadlines and catalog-only search_path. It
requires local 127.0.0.1:5432, merge_test, current_user and session_user postgres
before metadata reports. Reports connection identity, raw database/schema ACLs
and owners, effective app CONNECT/USAGE/CREATE, role flags and memberships in
both directions, public relations/routine signatures/types, and optional Alembic
revision through guarded psql conditionals. No hashes, routine bodies or
application rows selected; no repair or privileged mutation commands. Existing
malformed version tables fail safely; absent version tables are reported.
Exact owner-run command and partial-outcome handling are in TEST_DATABASE.md.

Executed from backend:
`.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`.
First run: 1 failed, 27 passed, 32 deselected, one existing HTTPX warning.
The new static relation-read checker incorrectly treated IS DISTINCT FROM as a
FROM relation clause. Corrected only that checker to distinguish the operator
and strip string literals; no SQL safeguard relaxed. Repeat: 28 passed,
32 deselected, one existing HTTPX warning; exit 0.

`git -c safe.directory=I:/Merge diff --check` passed, with existing LF/CRLF
working-copy warnings. `git ... diff --exit-code HEAD -- backend/app backend/alembic`
passed: application, original Alembic environment and migrations unchanged.
Four new database-free checks cover identity/read-only guards, forbidden SQL and
psql operations, catalog-only reads/optional revision, and preflight refusal.
These checks are conservative text checks, not server-side SQL parsing/execution.

Static review now satisfies all 12 provisioning-audit checks, including the
separate administrator recovery path for partial provisioning. This is not an
online PostgreSQL verification claim. No database connection, credential access,
provisioning, migration, database creation/disposal or permissions change occurred
in this correction. merge_dev untouched. No commits/pushes. Owner review and
actual provisioning/online verification remain pending; M-006B still open.

Owner exercise: explain why recovery connects as postgres directly to merge_test
instead of depending on merge_app CONNECT after a partial grant failure, and why
an absent database must use the original maintenance preflight instead.

## M-006B.2A guarded migration credential preflight — 2026-11-08

Owner reported successful merge_test provisioning/recovery inspection, expected
owner/ACLs, no application objects and no Alembic revision. These are owner
evidence, not new automated connection verification. Read required instructions,
TEST_DATABASE, SCHEMA, progress and exact test-support/Alembic entry points.

Actual commands from backend:
- `.\.venv\Scripts\python.exe -m test_support.database --help`: exit 0;
  exact interface `{verify,migrate}` plus required `--confirm-merge-test`.
- `.\.venv\Scripts\python.exe -m test_support.database migrate`: correctly
  rejected with required-flag argparse error before credential/connection code.
  Tool reported process exit 1 for this expected rejection; no migration ran.
- Private Python environment-presence check printed only
  `Explicit test-only credential available: False`. No secret value or URL output.
- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
  28 passed, 32 deselected, 1 existing HTTPX deprecation warning; exit 0.

Stopped database execution as instructed: test-only MERGE_TEST_DB_PASSWORD is
unavailable and automated noninteractive stdin cannot securely satisfy the
runner's private terminal password prompt. Did not import development credentials
into test settings or bypass the guard. Owner should run the exact documented
verify / migrate / verify / migrate / verify sequence with --confirm-merge-test
in their interactive backend terminal, checking exit status after every command.
Each prompt requests the existing merge_app password privately; never send it
to chat or put it in a command. Migration preflight checks actual identity and
rejects unexpected fresh-target public relations/routines before writing.

Not executed: authenticated test verification, migrations/repeat, fresh-object
inspection, or independent merge_dev revision/data inspection after this stop.
No database connected to or modified in this task; no revision/head result claimed.
No concurrency tests, roles/ACL/password changes, database creation/disposal,
commits or pushes. Only this progress entry changed for M-006B.2A; earlier pending
preparation files preserved. Migration gate remains incomplete, awaiting secure
owner execution. Owner exercise: explain why backend/.env is not a fallback for
the explicitly separate test credential mechanism.

## M-006B.2A diagnostic-only follow-up — 2026-11-08

Owner reported two guarded verify failures with the original generic error and
successful direct psql authentication; no migrations executed. Inspected exact
verification/exception paths. Root cause cannot be established from the old
message without new owner-run diagnostic output. No database credentials accessed
or database connections attempted in this follow-up; merge_dev untouched.

Updated backend/test_support/database.py with allowlisted failure categories,
SQLSTATE-based authentication/connection/permission classification where available,
identity/permission/migration-state operation stages and sanitized CLI output.
No raw exception text/arguments, SQL parameters, secret values or URLs emitted.
Exceptions lacking SQLSTATE during setup remain connection-category rather than
being asserted to prove authentication failure. Opt-in, identity/address/port,
isolation, fixed target and no-development-fallback checks preserved. No migration
or domain code changes. Added backend/tests/test_test_database_diagnostics.py;
updated TEST_DATABASE.md with one safe owner-run verify diagnostic step.

Executed from backend:
`.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
39 passed, 32 deselected, one existing HTTPX warning; exit 0. New tests verify
sanitized categories, CLI secret suppression, pre-first-migration verification
without a version table, permission/state differentiation, and unencoded special
characters retained in URL.create. These are database-free tests, not live
authentication/driver/server validation. No live root cause or migration success
claimed. No roles, passwords, ACLs, databases or constraints changed; no commits
or pushes. Owner should rerun only guarded verify interactively and report the
fixed bracketed category, not credentials, before any remediation/migration.

Owner exercise: explain why successful psql login does not establish which secret
the Python process used when MERGE_TEST_DB_PASSWORD overrides its hidden prompt.

## M-006B.2B credential-safety preflight — 2026-11-08

Owner verified merge_test provisioning, authenticated merge_app identity,
READ COMMITTED, 0002_domain and repeated guarded migration. These are owner
evidence, not new results from this agent process. Read the requested source
documents and current test support. Existing uncommitted preparation preserved.

Actual command from backend: a Python here-string piped to
`.\.venv\Scripts\python.exe -` checked only availability of the approved
test-only secret environment and interactive stdin. Output:
`Test-only credential configured: False`; `Interactive stdin available: False`;
exit 0. No password or URL printed. No credential fallback attempted.

Stopped before adversarial test implementation/execution under the task's explicit
instruction to stop when credential handling is unsafe. A private test credential
must be made available to the actual tool process using the existing explicit
MERGE_TEST_DB_PASSWORD mechanism; setting it in an unrelated IDE terminal does
not configure an already running agent process. Never paste it into chat, source
or command arguments. Ordinary development dotenv is deliberately not a fallback.

No database connection, fixture writes, concurrency tests/repetitions, SQLSTATE
observations, lock/deadlock outcomes, migrations or database resets performed.
Full backend/database-free/frontend regressions were not rerun after this safety
stop; previous evidence remains historical. No code, schema, constraints, roles,
permissions or credentials changed; merge_dev untouched. Only this log entry
changed for M-006B.2B. No commits/pushes. M-006B success gate remains open.

Owner explanation: authenticated owner commands establish database readiness,
but do not give a separate process access to its password. Confirm secret injection
in the process launching the agent without printing its value, then resume.

## M-006B.2B credential-free test implementation — 2026-11-08

Owner approved implementing tests without credentials and running PostgreSQL cases
later in an interactive owner terminal. Added backend/test_support/concurrency.py
and races.py, backend/concurrency_tests/{conftest,test_adversarial}.py and
backend/tests/test_concurrency_harness.py; updated TEST_DATABASE.md and progress.
Earlier pending files preserved. No application services/APIs/dependencies,
migrations, schema, credentials, roles or ACL changes. No database connection
attempted; merge_dev never accessed. No commits/pushes.

Implemented 13 test functions / 15 scenarios (both orders for two departure races),
with default three repetitions = 45 collected cases:
test_competing_final_seat_joins;
test_same_user_different_teams_one_hackathon;
test_same_user_different_hackathons;
test_lock_wait_snapshot_freshness;
test_rolled_back_admission_consumes_no_capacity;
test_direct_sql_over_capacity_rejection;
test_leader_departure_versus_successor_departure (both orders);
test_last_member_departure_versus_join (both orders);
test_invalid_leader_reference_rejected_at_commit;
test_deferred_validator_uses_final_rows;
test_transaction_rollback_restores_all_mutations;
test_bounded_lock_timeout_rolls_back_admission;
test_deadlock_victim_has_no_partial_membership.

Dedicated owner CLI requires --confirm-merge-test and a private existing app
password via hidden interactive input or explicit test-only environment; rejects
empty/missing credentials and Python optimized assertion mode. It does not read
development Settings/dotenv. Guarded connections verify actual database/role/
address/port/isolation; preflight reads exact 0002 revision and never migrates.
Fixed suite path excludes legacy development-database tests. External pytest
autoload/options are disabled; failure dumps suppressed; fail-fast enabled.
Only sanitized outcome/status/SQLSTATE/constraint metadata is reported.

All fixtures use committed UUID-scoped data only in merge_test, retained without
cleanup DML or destructive operations. Workers each own independent connections.
Barriers/events have bounded waits; controlled schedules require actual server
pg_blocking_pids evidence before releasing the blocker. Observer polling's short
wait is not itself concurrency evidence. Worker joins share a 30-second deadline;
connections retain bounded connect/statement/lock deadlines. Fresh post-test
connections inspect scoped derived counts, leadership, deletion, uniqueness,
membership/hackathon consistency and frozen sizes, including on test failure.
Expected 23514/23505/23503 integrity failures, deliberate 55P03 timeout and 40P01
deadlock are asserted separately; unexpected errors do not count as success.

Actual credential-free commands from backend:
- `.\.venv\Scripts\python.exe -m pytest concurrency_tests --collect-only -q`:
  45 cases collected, exit 0; fixtures did not run.
- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
  46 passed, 32 deselected, one existing HTTPX warning, exit 0. Seven new harness
  checks cover safe worker results/errors, SQLSTATE sanitization, mandatory opt-in,
  missing/empty credentials, guarded connection reuse and fixed safe pytest options.
- `.\.venv\Scripts\python.exe -m test_support.concurrency --help`: exit 0;
  confirms --confirm-merge-test and --repetitions 1..10.
- Same module without flags: expected required-opt-in rejection, tool exit 1;
  no credential prompt/connection reached.
- `git -c safe.directory=I:/Merge diff --check`: passed (existing LF/CRLF warnings).
  `git ... diff --exit-code HEAD -- backend/app backend/alembic backend/requirements.lock backend/pyproject.toml`:
  exit 0, committed application/migrations/dependency configuration unchanged.

Owner command (NOT executed here): from backend,
`.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --repetitions 3`.
Stop on nonzero exit and review sanitized outcomes; do not change constraints or
retry blindly. No live SQLSTATE, lock/deadlock observation or concurrency pass is
claimed yet. Busy-host deadlines and server deadlock detection/pg_blocking_pids
availability remain unverified. Fixtures accumulate intentionally. These are
8-contestant database races, not 50-way API acceptance/CI/load proof. Existing real
database/backend/frontend/HTTP regressions not executed in this credential-free
scope. M-006B/G1 remain open until owner execution evidence and findings review.

Owner exercise: explain why pg_blocking_pids must confirm the waiter before the
first transaction commits, then run with --repetitions 1 for a first bounded review.

## M-006B final review and checkpoint — 2026-11-08

Owner-verified execution supplied for this checkpoint: guarded target merge_test,
merge_app, READ COMMITTED, revision 0002_domain, repeated guarded migration
succeeded; adversarial suite **45 passed in 39.72 seconds**, three repetitions,
fresh committed-state invariants verified. This is owner-reported real PostgreSQL
evidence, not a database run by Codex. No raw per-case transcript was supplied.
The passing suite strictly asserts capacity/deletion 23514, uniqueness 23505,
leader FK 23503, deliberate lock timeout 55P03 and deliberate deadlock 40P01.
No unexpected errors were reported. No 50-way HTTP/API race has been tested.

Reviewed all 20 pending source/test/SQL/documentation candidates, including guarded
setup, read-only recovery, isolated online migration environment, sanitized
diagnostics and concurrency suite. Every worker opens its own guarded SQLAlchemy
engine/connection and transaction. Barriers synchronize race starts; controlled
orders require pg_blocking_pids evidence before releasing held locks; deliberate
deadlock synchronizes opposing held locks. Strict outcome assertions reject
unexpected deadlocks/timeouts/constraints/infrastructure errors. Fresh independent
read-only checks inspect scoped committed capacity, leader, deletion, assignment,
FK consistency and frozen-size invariants after each case. UUID fixtures remain
only in merge_test with no destructive cleanup. No unaddressed correctness blocker
identified in this bounded review. Test helper departures are not production
services and do not certify the complete future canonical service lock protocol.

Actual checkpoint commands from backend, without credentials/database connections:
- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
  46 passed, 32 deselected, one existing Starlette/HTTPX warning; exit 0.
- `.\.venv\Scripts\python.exe -m pytest concurrency_tests --collect-only -q`:
  45 cases collected, exit 0; no fixture execution.

Git/safety evidence: `git -c safe.directory=I:/Merge diff --exit-code 41b6bdc6849340ff6018d84c1f5b74e28bfcdfea -- backend/app backend/alembic backend/requirements.lock backend/pyproject.toml`
returned exit 0: domain application, original Alembic environment, 0001/0002 and
dependencies unchanged. `git ... check-ignore -v` confirmed backend/.env, venv,
pytest cache, node_modules and dist ignored; tracked backend/.env query empty.
Changed-file scan of 20 candidates found no private-key/provider-token signatures,
credential URLs, sensitive/generated filenames or non-synthetic literal password
arguments. No local secret file was read; this signature-based scan is not proof
against every unknown secret. Fixed loopback targets/role names are intentional
nonsecret setup configuration. `git ... diff --check` passed; LF/CRLF working-copy
warnings remain. Owner authorized one local checkpoint commit with message
`test: add isolated PostgreSQL concurrency verification (M-006B)`; resulting hash
will be reported from Git, not invented or embedded self-referentially here.

Updated TEST_DATABASE, SCHEMA and architecture to point to the owner-verified
outcome while retaining historical preparation/failure entries. No new application
behavior or dependencies. No database connections, migrations, resets, disposal,
roles/privileges/password changes, merge_dev access, remotes or pushes in this
checkpoint. Real database tests were not rerun by Codex. Full backend database,
frontend/build/HTTP regressions were not rerun; their earlier evidence remains
historical. Only the owner-reported PostgreSQL suite and current database-free
checks are newly recorded evidence.

M-006B database-schema verification checkpoint is verified within its stated
scope. G1 remains partial: M-007 services/authorization/idempotency/audit writers,
complete lifecycle lock/retry behavior and 50-way authenticated HTTP race are
unimplemented/unverified. CI/API acceptance, frontend domain workflows, load and
deployment gates remain open. Local schedule coverage is not proof of all possible
interleavings or different isolation modes. Retained fixtures require separately
approved disposal; no cleanup permission inferred from this commit.

Owner explanation/exercise: explain why a deadlock victim must roll back its
earlier membership insert, and identify the strict 40P01 assertion that would
reject a lock-timeout substitute.

## M-007A internal transactional creation/join — 2026-11-09

Started from clean main at defb6b9ed0f3dc8e2236c6a3a57e7857afcbbaa7.
Read required source documents, SQLAlchemy domain models, frozen 0002 DDL,
transaction configuration and guarded concurrency harness. Critical dependency
check passed by static inspection: no team/membership FK or trigger requires an
idempotency/audit/outbox row. Audit's forward operation FK, outbox's forward audit
FK and deferred pending-idempotency validation constrain records when present;
they do not mandate reverse records. No fake support records or schema relaxation.
The complete public mutation/audit/idempotency contract remains future M-008 work.

Added app/services/{__init__,errors,teams}.py, service_tests/{conftest,test_teams}.py,
tests/test_team_services.py and docs/TEAM_SERVICES.md. Extended existing guarded
runner with --suite schema (unchanged default) / --suite services and extended its
database-free suite-selection tests. Updated architecture/decisions/TEST_DATABASE
and this log. No new dependencies, migrations, model/constraint or frontend changes.

TeamService accepts an Engine, never caller Connection/Session, and owns each
connection/transaction through commit before returning frozen TeamResult. Requires
PostgreSQL READ COMMITTED and no active supplied transaction; applies local 5s
lock/15s statement deadlines. Lock order is hackathon SHARE -> actor NO KEY UPDATE
-> exact team NO KEY UPDATE for joins; creation inserts its new team under subject
locks. Eligibility/membership/count queries happen after locks. Counts come from
actual rows, not identity-map/persistent counters. UUID/name validation precedes
connection acquisition. Deferred COMMIT failures unwind before mapping to safe
DomainError codes. Only named expected integrity conflicts map to business errors;
unknown class-23 faults remain integrity_fault. Deadlock/serialization and lock
deadline errors are marked retryable, with no implicit retry loop. No network
calls other than database I/O inside transactions. No authentication/authorization,
public routes, invitations/departures, idempotency/audit/outbox generation added.

Real PostgreSQL service suite has 14 scenarios / 42 cases at three repetitions:
founder atomicity; statement failure after team INSERT; deferred COMMIT rollback;
successful join/count; full/deleted rejection; same-hackathon assignment/repeat
conflicts; cross-hackathon permission; competing final-seat, same-user join and
same-user create races; wrong-hackathon team and missing-subject cases. Fault
injection uses test-only Engine events; no production hooks or database changes.
Per-connection Engine events verify actual test target/isolation before service
queries. Fresh invariant checks reuse the existing UUID-scoped committed fixture
harness; fixtures remain only in merge_test. No destructive cleanup.

Actual executed commands from backend (no database connections):
- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
  first 68 passed, 32 deselected, one existing HTTPX warning. Added explicit
  service-suite selection and active-transaction rejection checks; final run
  **70 passed, 32 deselected, one existing Starlette/HTTPX warning**, exit 0.
- `.\.venv\Scripts\python.exe -m pytest service_tests --collect-only -q`:
  42 cases collected, exit 0; no fixture execution.
- `.\.venv\Scripts\python.exe -m pytest concurrency_tests --collect-only -q`:
  original 45 schema cases collected, exit 0; no fixture execution.
- `.\.venv\Scripts\python.exe -m test_support.concurrency --help`: exit 0,
  confirms --suite {schema,services}, --confirm-merge-test and --repetitions 1..10.
- Python presence-only check: Private test credential available False;
  Interactive stdin False; exit 0. No development credential/dotenv read or copied.
- `git -c safe.directory=I:/Merge diff --check`: passed (LF/CRLF warnings remain).
  `git ... diff --exit-code HEAD -- backend/alembic backend/app/models backend/app/db backend/app/core backend/requirements.lock backend/pyproject.toml`:
  exit 0, schema/migrations/model/config/dependency baseline unchanged.

Owner-run real integration command, NOT executed here:
`.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite services --repetitions 3`
from backend, existing merge_app password via hidden interactive prompt. Stop and
review any failure; never weaken guards. No real service tests, SQLSTATE/lock
results, full database suite, frontend/build or HTTP regression executed. No
merge_dev access, database writes/migrations/roles/ACL/password changes, commits
or pushes by Codex. Existing M-006B owner 45-pass evidence is historical, not
reused as proof of the new services. G1 remains open pending real service tests
and later API acceptance.

Risks: unverified PostgreSQL service behavior; raw writers may still deadlock with
services (whole-transaction conflict classification, not automatic retries);
counts are mutation-time snapshots; COMMIT connection loss has an ambiguous
durable outcome, so database_failure must not be blindly retried without future
idempotency. This committing facade cannot be wrapped in an outer transaction to
append outcome/audit/outbox later; M-008 must integrate those into the same owned
transaction before public use. Current trusted actor inputs provide no API auth.
No 50-way HTTP or deployment/CI/load compliance claimed.

Owner explanation/exercise: trace hackathon/user/team locking in join_team; explain
why moving COUNT before the team lock is unsafe, and inspect the deferred-COMMIT
fault test to show why no partial team should survive.

## M-007A final review — checkpoint stopped, 2026-11-09

Owner-verified result: guarded merge_test service suite **42 passed in 33.12s**,
three repetitions requested, fresh committed-state invariants verified and expected
domain rejection cases reported. This is owner evidence, not a Codex PostgreSQL
run. No HTTP/authentication claim. Existing tests strictly assert business outcomes,
single committed winners and post-failure state; unexpected service error codes
or worker failures are not accepted as successful races.

Blocking transaction-configuration issue found before staging/commit:
TeamService._execute checks get_isolation_level() == READ COMMITTED and
in_transaction(), but does not check/disable DBAPI autocommit. Read the installed
SQLAlchemy Connection.get_isolation_level docstring and PGDialect_psycopg isolation
reader/setter through inspect.getdoc/getsource in a credential-free Python command.
The documented API explicitly never reports AUTOCOMMIT; it is independent of actual
isolation. The psycopg setter sets autocommit=True for AUTOCOMMIT. Therefore an
AUTOCOMMIT Engine can pass the current check, while c.begin() alone does not restore
DBAPI transaction semantics. Statement-level commits can release locks separately
and invalidate atomic team+membership creation. Normal configured test Engine
results do not establish safety for this Engine configuration.

Additional credential-free reproduction reused the existing FakeConnection and
service_for helper, supplied a synthetic driver_connection.autocommit=True, and
called create_team. Output reported current service accepted configuration True.
This is a mocked guard-coverage reproduction only, not an actual database write or
proof of a persisted partial team. No credentials or DB URLs printed/read.

Proposed correction for owner review, NOT implemented: explicitly establish owned
connection transactional READ COMMITTED before any SQL and/or fail closed on
DBAPI autocommit, then add database-free AUTOCOMMIT rejection/configuration tests
and guarded real-PostgreSQL fault/rollback tests with an AUTOCOMMIT-configured
Engine. Preserve the same lock order, constraints and complete transaction boundary.
No schema change is needed. Service code left unchanged for this review stop.

Executed `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`
from backend: 70 passed, 32 deselected, one existing HTTPX warning; exit 0.
These passing tests lack AUTOCOMMIT coverage; they do not close the blocker.
Baseline diff check against HEAD for backend/alembic, models, main/API paths and
dependency files returned exit 0: 0001/0002 and HTTP routes unchanged.
Ignore checks confirmed local backend/.env, venv/caches/node_modules/dist excluded;
tracked backend/.env query empty. No public mutation endpoints introduced.

Stopped before commit as instructed. HEAD remains
defb6b9ed0f3dc8e2236c6a3a57e7857afcbbaa7; pending service/test/documentation changes
remain unstaged. No databases accessed, no merge_dev changes, no migrations,
roles/permissions/password changes, resets/disposal, remotes, commits or pushes.
G1 remains open. Owner exercise: explain why READ COMMITTED and DBAPI autocommit
are independent, and why a Python transaction context is insufficient in that mode.

## M-007A-R1 explicit DBAPI AUTOCOMMIT rejection — 2026-11-09

Owner authorized fail-closed boundary correction, not silent isolation changes.
Read AGENTS/TEAM_SERVICES/SCHEMA/progress and exact service/tests. Inspected
installed SQLAlchemy 2.1.8 and psycopg 3.3.8 via Python inspect, without database
access: Connection.connection documented pool proxy, ManagesConnection's annotated
dbapi_connection/driver_connection interfaces, psycopg Connection.autocommit bool
getter and dialect isolation setter. get_isolation_level explicitly excludes DBAPI
AUTOCOMMIT. One initial documentation inspection command exited 1 because the
annotated driver_connection attribute has no class-level descriptor; inspected
documented dbapi_connection/annotations and actual source successfully afterward.
No credentials or server queried during inspection.

Changed app/services/teams.py: _require_transactional_connection accepts only
synchronous PostgreSQL psycopg and actual DBAPI autocommit is False through
SQLAlchemy's documented connection.connection.dbapi_connection accessor. Missing/
unreadable/non-bool/True state fails with transaction_configuration. Preserves
no-active-transaction and actual READ COMMITTED checks, same service interfaces,
locking, transaction ownership and error mapping. Guard runs before begin(),
isolation metadata query, SET LOCAL and all domain SQL. No mode setter or Engine
execution_options added to production service. Connection initialization/test
identity hooks may issue metadata reads only, not service/domain writes.

Changed tests/test_team_services.py with mocked AUTOCOMMIT create/join rejection
before any SQL/transaction/isolation read; missing/ambiguous/unreadable state and
unsupported/missing dialect/isolation rejection; normal False state accepted and
unchanged. Existing statement/COMMIT rollback tests remain. Added guarded live
create/join AUTOCOMMIT OptionEngine scenarios to service_tests/test_teams.py.
They inherit actual test identity guards, observe actual autocommit True on the
service connection, reject without domain/SET LOCAL statements, compare fresh
counts/roster, preserve original Engine options and verify original autocommit
False after pool return. Existing real injected-failure rollback test now explicitly
checks False/READ COMMITTED. No new production fault hooks or schema changes.
Updated TEAM_SERVICES/architecture/progress. Earlier pending M-007A files preserved.

Actual database-free commands from backend:
- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
  first 91 passed, 32 deselected, one existing HTTPX warning; added missing dialect
  configuration checks; final **94 passed, 32 deselected, one existing HTTPX warning**,
  exit 0. No failing test weakened/deleted.
- `.\.venv\Scripts\python.exe -m pytest service_tests --collect-only -q`:
  expanded **48 cases collected**, exit 0; no fixtures executed.
- Presence-only Python check: Private test credential available False;
  Interactive stdin available False. No development dotenv/credentials read.

Owner live command from backend (NOT executed here):
`.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite services --repetitions 3`.
Uses existing hidden password prompt; do not put secrets in arguments, logs or chat.
This reruns all existing service races/rollback cases plus new AUTOCOMMIT rejection.
Original owner result 42 passed in 33.12s remains historical pre-R1 evidence only.
No live R1 SQLSTATE/autocommit/rollback/race success claimed. A completed expanded
owner run is still required before final checkpoint review.

No database connections or fixture writes by Codex; merge_dev untouched. No schema,
migration, constraints/triggers, credentials, roles, privileges, endpoints or service
interfaces changed; no commit/push. No M-007B/M-008 work. Guard is driver-specific
by design; other drivers fail closed until explicitly supported. Engine listeners
and exclusive ownership of each driver connection remain trusted boundaries.
Owner exercise: explain why READ COMMITTED with DBAPI autocommit True is unsafe,
and find the test assertions that prove no service SQL precedes rejection.

Final R1 static checks: `git -c safe.directory=I:/Merge diff --check` exited 0,
with existing LF/CRLF warnings. Baseline diff against HEAD for backend/alembic,
models, db/core configuration, main.py and dependency files exited 0. Parsed all
changed Python sources with ast and scanned the 13 pending source/doc candidates
for secret signatures/generated paths: zero findings. No secret file read.

## M-007A final checkpoint review after R1 — 2026-11-09

Owner-verified expanded live evidence: **48 passed in 37.23 seconds**, three
repetitions requested, guarded merge_test. This records the owner's execution of
the R1-expanded service suite, not a PostgreSQL rerun by Codex. The expanded suite
includes actual AUTOCOMMIT create/join rejection with no domain SQL/unchanged
scoped counts, injected statement/COMMIT rollback, existing service races,
expected domain rejections and fresh committed-state invariant checks. Prior
42-pass and blocked-review entries remain historical evidence, superseded for
checkpoint readiness by R1 and this expanded run. No raw per-case transcript was
supplied; no additional per-case measurements are invented.

Reviewed all 13 pending source/test/doc candidates. TeamService acquires its own
Engine connection and transaction; rejects non-PostgreSQL/non-synchronous-psycopg
or unreadable/ambiguous actual DBAPI autocommit state, requiring is False before
the isolation metadata query, begin(), SET LOCAL or domain SQL. Requires READ
COMMITTED and no caller transaction; never changes Engine isolation. Creation
and joining retain hackathon SHARE -> user NO KEY UPDATE -> team NO KEY UPDATE
where applicable, fresh membership/count checks and parameterized public SQL.
Deferred commit errors unwind before safe mapping. Only expected named constraints
map to business conflicts; unknown integrity faults, timeouts or transaction
conflicts are not accepted as normal successful race results. No remaining
blocking transaction-safety issue identified within the documented supported-driver
and trusted Engine-listener/exclusive-connection contract. No services changed
during this checkpoint review.

New checkpoint commands actually executed, from backend:
- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
  **94 passed, 32 deselected, one existing Starlette/HTTPX warning**, exit 0.
- `.\.venv\Scripts\python.exe -m pytest service_tests --collect-only -q`:
  **48 cases collected**, exit 0; no fixture execution.

Git/safety checks: baseline diff against
defb6b9ed0f3dc8e2236c6a3a57e7857afcbbaa7 for backend/alembic, models, db/core,
main/API paths and dependency files exited 0. Existing 0001/0002, domain schema,
configuration and HTTP routes unchanged. Ignore checks confirmed backend/.env,
venv, pytest cache, node_modules and dist excluded; tracked backend/.env query
empty. No local secret files were read. Review includes secret/generated-path
scanning of intended source candidates and actual staged blobs before commit.
`git ... diff --check` passed; LF/CRLF conversion warnings remain. Owner authorized
one local commit exactly `feat: implement atomic team creation and joining services (M-007A)`;
the actual resulting hash will be reported directly from Git.

Updated TEAM_SERVICES, architecture, decisions and TEST_DATABASE to reflect
owner-verified expanded results; appended this evidence without rewriting earlier
failures. Includes all bounded M-007A/R1 service/test/runner/doc work; no new
dependencies/migrations. No database access, merge_dev access, merge_test reset,
roles/privileges/password changes, remote creation or push in this review. Real
database tests were not rerun; full legacy database/frontend/HTTP regressions were
not rerun and retain historical evidence only. No M-007B/M-008 implementation.

M-007A is verified within its internal service scope. G1/API acceptance remains
open: no authentication/authorization, public mutations, 50-way authenticated HTTP
race, idempotency/audit/outbox generation or later lifecycle services. No automatic
retries; ambiguous COMMIT connection loss still requires reconciliation/future
idempotency rather than blind retry. Returned counts are mutation-time snapshots.
The committing facade must be integrated with future transactional support writers
inside the SAME owned transaction before public use. Driver support intentionally
fails closed beyond sync psycopg. Tests cover specific local schedules, not every
possible interleaving, isolation mode, production/CI or load outcome.

Owner exercise: trace the actual DBAPI autocommit read before get_isolation_level,
and explain why the FK/constraint-trigger failure at COMMIT rolls back the team
insert instead of returning a partially successful result.

## M-007B.1 authentication storage preparation — 2026-11-09

Baseline: main HEAD 77e04fc1b9fbe307eeb6103d1d2b9fe002afb284. Implemented
storage and guarded migration support; NOT applied or live-verified. G1 stays open.
No database connection was opened in this task. A presence-only check found no
private test credential and no interactive stdin; development credentials were
not read or copied. Owner execution remains required.

New models and frozen additive 0003_auth (down_revision 0002_domain):
account_credentials, auth_sessions and auth_throttle_buckets. Named checks cover
canonical 3–32 ASCII usernames, hash-format marker, 32-byte session digest/CSRF,
finite timestamps, exact eight-hour lifetime, revocation and throttle storage.
Sessions require an existing credential row as well as a user. No principal
backfill/adoption or domain DML. Identity/lifetime UPDATE guards, terminal
revocation and TRUNCATE guards are included. No password hashing, issuance,
session verification, CSRF validation, throttle algorithm, endpoints or new
dependencies. Storage cannot establish token randomness/hash provenance or that
a real Argon2id hash/login exists. See AUTH_SCHEMA.md for decisions and commands.

Guarded migration support is explicit and separately tested: default remains
0002_domain; --revision 0003_auth requires current 0002 or 0003. No silent head
upgrade, unknown-state adoption or downgrade. --suite auth also requires that
explicit revision. Identity checks, fixed loopback/role/database and private
password handling remain. Runner owns the DDL transaction; dedicated Alembic env
no longer rolls back the caller's transaction. Bounded SHARE locks and aggregate
before/after domain row counts/fingerprints detect changes before committing DDL.
Fingerprints and row contents are not printed. Stop other merge_test writers;
online behavior, including this preservation check, still needs live execution.

Commands actually executed from backend using Python 3.11 virtual environment:

- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
  final **116 passed, 32 deselected, one existing Starlette/HTTPX deprecation
  warning**, exit 0, 2.34s. Includes offline PostgreSQL DDL rendering, mapper and
  revision checks, explicit-target rejection, migration commit/rollback ownership
  fakes and prior database-free regressions. These are not live PostgreSQL tests.
- `.\.venv\Scripts\python.exe -m pytest auth_schema_tests --collect-only -q`:
  **78 cases collected**, exit 0, 0.41s; no fixture execution. Covers uniqueness,
  username policy, digest/CSRF lengths, user/credential FKs, expiration/revocation,
  immutable identities, relationships, throttle storage, unchanged users and
  metadata comparison. Fixtures are UUID-scoped, rollback-only with savepoints.
- `python -m test_support.database --help` and
  `python -m test_support.concurrency --help`: confirmed implemented CLI flags.

Initial offline run: one failure compiling auth-only test metadata without its
referenced users table; 110 passed. Corrected the test metadata to include all
referenced tables, without weakening constraints. Next run: 111 passed. Added
five explicit verify-revision cases; final 116-pass result above supersedes it.
No SQLSTATE, online migration, repeat-upgrade, database metadata drift, preservation
or auth-schema live pass is claimed. Existing live service/concurrency results
remain historical evidence, not reruns after 0003. Frontend/HTTP checks not rerun
because this component has no route/frontend changes. Legacy ordinary database
tests still target merge_dev and were deliberately not executed.

Protected baseline review: git diff --exit-code HEAD for existing 0001/0002,
domain.py, services, db/core, main.py and dependency files exited 0. Ignore checks
confirmed backend/.env, venv, pytest cache, node_modules and dist excluded;
tracked backend/.env query empty. Local .env files were not read. No schema,
roles, privileges, ownership, passwords or live database contents modified.
No commit, push or remote creation. Full final diff/static safety evidence follows
the final check below; owner-run migration/repeat/verification and auth plus
service/domain live regression commands are documented in AUTH_SCHEMA.md.

Owner explanation/exercise: explain why an uncredentialed seeded user cannot
receive a session, then locate the exact check for eight-hour lifetime. Explain
why the future auth service must still validate expiry/revocation on every request.

Final static review: `git -c safe.directory=I:/Merge diff --check` exited 0 with
LF/CRLF conversion warnings. Parsed all 12 changed/new Python files with ast;
reviewed 18 source/doc candidates for private/generated paths, credential URL,
private key and access-token signatures and trailing whitespace: zero findings.
These scans supplement manual review, not a proof that all possible secrets can
be detected. Final Git state is 11 modified tracked files and seven new files,
all unstaged; HEAD remains 77e04fc1b9fbe307eeb6103d1d2b9fe002afb284.

## M-007B.1 final review and checkpoint — 2026-11-09

Owner-verified live evidence: guarded merge_test migration to 0003_auth completed,
repeat completed, verification returned **0003_auth (head)**, and existing domain
row counts/fingerprints were preserved. Authentication schema suite: **78 passed
in 11.75 seconds**, three repetitions requested. Owner explicitly reported the
expected **23514 / ck_throttle_expiration** rejection. This is owner-executed
PostgreSQL evidence, not a Codex database rerun. No additional per-case SQLSTATE
transcript, service/domain regression after 0003 or HTTP result was supplied.
Earlier pending-live entries above remain historical preparation evidence.

Reviewed all 18 pending source/test/documentation candidates, including the frozen
0003 DDL, auth ORM registry, explicit revision support, caller-owned Alembic
transaction and rollback-only live fixtures. Username/hash/digest/CSRF/time/FK
checks, credential/session relationships, lifetime immutability and terminal
revocation are consistent with the bounded storage contract. No existing users
are backfilled/adopted. SECURITY INVOKER function has fixed catalog/temp search
path; new TRUNCATE guards reuse the unchanged domain function. No blocking
correctness/security issue identified for this storage scope. No implementation,
migration, schema or permission changes were made during checkpoint review.

Expected-rejection tests require IntegrityError AND exact SQLSTATE AND allowlisted
constraint names inside savepoints. Unknown-user sessions allow either of the
two valid user/credential FK names; arbitrary FK failures are not accepted. Other
exceptions, missed rejections, metadata differences or assertion failures fail the
suite. Guarded runner rejects optimized assertion mode and uses fail-fast/no
exception dumps. Private credentials are hidden; direct fixture use without
runner settings/opt-in fails before writes. Each physical connection verifies
merge_test / merge_app, loopback address/port and READ COMMITTED. Default target
remains 0002; explicit 0003 selection is required. No development fallback.

Actual checkpoint commands from backend, with no credentials/database connection:
- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
  **116 passed, 32 deselected, one existing Starlette/HTTPX deprecation warning**,
  exit 0, 2.10s. Includes mapper/metadata and offline PostgreSQL migration render,
  revision graph/selection, identity guards and transaction ownership fake checks.
- `.\.venv\Scripts\python.exe -m pytest auth_schema_tests --collect-only -q`:
  **78 cases collected**, exit 0, 0.22s; fixtures were not executed.
- `git -c safe.directory=I:/Merge diff --check`: exit 0; LF/CRLF warnings remain.
- Protected baseline diff against 77e04fc1b9fbe307eeb6103d1d2b9fe002afb284 for
  0001/0002, ordinary Alembic env, domain models/services, db/core, main.py,
  dependency files, frontend, scripts and .gitignore: exit 0. Existing staging
  area was empty before this checkpoint. No HTTP route changes; only GET /health
  exists in the application. No new dependencies or M-007B.2 implementation.

Git safety review includes explicit candidate allowlisting, secret/generated-path
scan and actual staged-blob review before commit. Ignore checks confirmed
backend/.env, backend/.env.local, venv/cache, node_modules and dist excluded;
tracked backend/.env query empty. No local secret file was opened. Fixed local
host/database/role labels and deliberately synthetic test values are nonsecret
configuration/fixtures. No password or complete database URL belongs in this
checkpoint. Signature scans supplement manual review, not proof against every
unknown secret. Candidate scan parsed all 12 Python files and reviewed the exact
18-file allowlist with no actionable findings. A broader URL check initially
flagged two intentionally synthetic redaction-test strings in the preexisting
harness; verified both full lines match the committed baseline and contain no
credentials. They are not live database URLs; no new URL fixture was introduced.
The final scan retained only that exact baseline fixture exception. Owner
authorized exactly one local commit:
`feat: add authentication schema and session storage (M-007B.1)`.
The resulting hash is reported directly from Git rather than embedded in its own
commit. No remote creation/push, database connection/migration/reset, merge_dev
access, merge_test disposal, roles/privileges/password changes in this review.

Updated AUTH_SCHEMA, SCHEMA, TEST_DATABASE, architecture/decisions and this log
with owner evidence and current revision instructions. Storage schema checkpoint
is verified within its stated scope; G1 remains open. Runtime password hashing,
token issuance/verification, request-time expiry/revocation/CSRF checks, rate-limit
algorithm, auth endpoints and authorization remain unimplemented. Storage checks
cannot prove hash validity or entropy. Auth TRUNCATE guards have static DDL
coverage; this 78-case suite does not execute TRUNCATE. Service/domain live suites
after 0003, full legacy database tests, frontend/HTTP regressions, authenticated
50-way HTTP race, CI/load/deployment acceptance were not run in this checkpoint.

Owner exercise: find the exact 23514/constraint assertion for throttle expiration
and explain why accepting any IntegrityError would make that test misleading.

## M-007B.2A internal credential/registration services — 2026-11-09

Started from clean main at 66d0e8fc53e9797e87f581b798767878a7e16cd8. Read source
requirements/architecture/decisions/auth storage/test procedures and progress;
inspected actual users/credentials/sessions, TeamService's transaction guard,
schema constraints and guarded fixture infrastructure. No schema incompatibility
found by inspection. Existing 0001/0002/0003, models and TeamService are preserved.
This is an implemented/database-free-tested component, NOT live-service verified.

New app/security/{__init__,passwords}.py and
app/services/{credential_errors,credentials}.py implement canonical username and
15–128-character password validation; fixed Argon2id hashing/verification; atomic
new-principal registration; closed-read-transaction credential lookup followed by
real/dummy verification. No caller UUID/actor input, user adoption, rehash or session.
Engine-owned transactions reject actual DBAPI AUTOCOMMIT, ambiguous/unsupported
drivers/isolation or caller transactions, and require READ COMMITTED. Parameters
must be hidden and SQL echo/debug rows disabled. Hash before acquiring registration
connections; no database transaction/lock during verification KDF. Return after
commit; exact username unique constraint only maps to username_unavailable.
Wrong/unknown credentials share invalid_credentials; errors have fixed codes,
no native/DBAPI implicit exception context, and no password/hash result fields.
Traceback-local capture/external instrumentation remain prohibited trusted config.

Dependency/API sources reviewed: OWASP Password Storage Cheat Sheet and official
argon2-cffi API/PyPI metadata (linked in CREDENTIAL_SERVICES.md). Pinned
argon2-cffi 25.1.0; explicit Argon2id v19 / m=19456 KiB / t=2 / p=1 / random
16-byte salt / 32-byte output. Meets OWASP's 19 MiB/two-iteration/one-lane minimum.
Two nonblocking work slots shared across codec instances per process, including
real/dummy verification. Saturation is hashing_busy, not a DB-backed rate limit.
Stored verification profile is bounded exactly; malformed/unsupported encodings
use dummy work and fail closed. No timing-equality, production resource sizing or
password-strength/breach-list claim. No password normalization/truncation.

Commands actually executed from root:
- `uv pip compile backend/pyproject.toml --extra dev --python backend/.venv/Scripts/python.exe --output-file backend/requirements.lock --quiet`: exit 0.
- `.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock --quiet --disable-pip-version-check`: exit 0.
- `.\backend\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e backend --quiet --disable-pip-version-check`: exit 0.
Lock diff adds only argon2-cffi 25.1.0, bindings 26.1.0, cffi 2.1.1 and pycparser
3.12; no existing version upgrades. Installed versions confirmed with package
metadata, without any database connection.

Actual database-free checks from backend:
- Focused `python -m pytest -q tests/test_passwords.py tests/test_credentials.py --tb=short`
  using .venv interpreter: first **6 failed, 49 passed**. Instrumentation attempted
  to replace read-only PasswordHasher instance methods. Corrected test-only
  wrappers by replacing the codec's private hasher reference with a spy/fake;
  real Argon2 roundtrips and guard assertions were retained, no production weakening.
- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
  next **173 passed, 32 deselected, one existing Starlette/HTTPX warning**, 4.68s.
  After adding invalid-verification checks and removing raw exception context,
  final **175 passed, 32 deselected, one existing warning**, exit 0, 3.81s.
  Includes real Argon2 salt/profile/Unicode/passphrase/mismatch tests, bounded
  shared work-gate synchronization, generic/dummy behavior, sanitization, fail-closed
  AUTOCOMMIT/configuration and mocked full transaction rollback. No live DB proof.
- `.\.venv\Scripts\python.exe -m pytest credential_tests --collect-only -q`:
  **51 cases collected**, exit 0, 0.03s (17 scenarios at three repetitions).
- Existing suites collected separately: `python -m pytest auth_schema_tests --collect-only -q`
  **78 cases**; service_tests **48**; concurrency_tests **45**, each exit 0.
- `.\.venv\Scripts\python.exe -m pip check`: no broken requirements, exit 0.
- `.\.venv\Scripts\python.exe -m test_support.concurrency --help`: confirmed
  --suite credentials, explicit revision choices and mandatory confirmation.

Other command failures, corrected without infrastructure changes: invoking the
test_support module from repo root failed ModuleNotFoundError; reran from backend
successfully. A combined auth_schema_tests/service_tests/concurrency_tests
collection failed because their preexisting shared pytest_addoption hooks register
the same option repeatedly. Collected each suite in a separate process instead;
the guarded runner already selects one suite per invocation. No test failure was
counted as validation and no existing hooks/tests were weakened to hide it.

New credential_tests/{conftest,test_credentials}.py uses only explicit guarded
merge_test/0003 settings. All service Engine connections have actual identity and
revision events; observers open fresh guarded connections. UUID user/name fixtures
and runtime-generated test passwords; no destructive cleanup. Independent duplicate
registrations synchronize after both uncommitted user inserts, then require exactly
one successful account and actual 23505/uq_credentials_username for the loser.
Other cases cover invalid/duplicate inputs, failures after each INSERT/before COMMIT,
unclaimable existing users, hash preservation, wrong/unknown errors, malformed stored
hashes and actual AUTOCOMMIT rejection with no domain statements. Fresh scoped user/
credential counts and no-session/no-membership checks run after cases. SQLSTATE,
live rollback/concurrency and actual AUTOCOMMIT outcomes remain UNVERIFIED.

Private test credential availability False and interactive stdin False (presence
only; no secret values printed). No development .env or credential was read/copied;
no PostgreSQL connection or migration ran. Owner command from backend:
`.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite credentials --revision 0003_auth --repetitions 3`.
Full private-prompt/read-only-preflight and existing regression procedures:
CREDENTIAL_SERVICES.md. Do not expose passwords in chat/arguments/transcripts.
No live pass for new services or post-change auth/domain/team regressions claimed.
Earlier owner 78-pass storage evidence remains historical, not a rerun here.

Updated auth/architecture/decision/test documentation and the guarded fixed-suite
selector/tests. No HTTP routes, sessions/cookies, CSRF/rate-limit policy, TeamService,
invitation/joining/authZ, schema/migration, roles/permissions or frontend changes.
No merge_dev access, database reset/disposal, commits, remotes or pushes. G1 stays
open. Live credential verification and existing guarded regressions require owner
execution; no API/50-way HTTP/CI/load/deployment acceptance claimed. Registration
availability disclosure, per-process resource limits and concurrent password-change/
future session-issuance semantics are documented limitations, not solved features.

Owner exercise: trace why the losing duplicate transaction cannot leave an orphan
user, then inspect the dummy verification assertion and why a blanket IntegrityError
mapping would conceal a real database fault. Static safety evidence follows below.

Final static review: `git -c safe.directory=I:/Merge diff --check` passed, with
LF/CRLF conversion warnings. Parsed all 11 changed/new Python files with ast;
reviewed the exact 19-file candidate allowlist for private/generated paths,
credential URLs, literal real Argon2 encodings, private-key/provider-token
signatures and whitespace: zero findings. Two preexisting synthetic URL fixtures
were verified unchanged against HEAD and kept as the only exact scan exception.
Lockfile comparison confirmed all existing pins unchanged and precisely the four
documented additions. These checks supplement manual review, not a proof against
all possible secrets. No local secret file was opened for inspection.

`git ... diff --exit-code HEAD -- backend/alembic backend/app/models backend/app/services/teams.py backend/app/services/errors.py backend/app/db backend/app/core backend/app/main.py backend/test_support/database.py backend/test_alembic frontend scripts .gitignore`
passed: all existing migrations/constraints/models, TeamService, ordinary runtime
configuration, test identity/migration guards and HTTP/frontend behavior unchanged.
Ignore checks confirmed actual backend/.env, local dotenv variants, virtualenv,
cache, node_modules and build output excluded; backend/.env is not tracked.
Staging area is empty. Final HEAD remains
66d0e8fc53e9797e87f581b798767878a7e16cd8 on main; 10 modified tracked and nine
new source/doc files remain unstaged for owner review. No commit or push.

## M-007B.2A final review and checkpoint — 2026-11-09

Owner-verified execution: guarded merge_test / 0003_auth credential suite,
**51 passed in 28.76 seconds**, three repetitions requested. Fresh credential
committed-state checks verified. UUID-scoped fixtures intentionally retained;
no cleanup performed. This records the owner's PostgreSQL execution, not a Codex
database rerun. No separate raw per-case transcript or post-change auth/schema/
TeamService live regression results were supplied; no additional results invented.
The earlier pending-live entries remain historical preparation evidence.

Reviewed the full 19-file pending source/test/dependency/documentation scope.
CredentialService.register validates canonical usernames and 15–128-character
passwords, hashes before connection acquisition, generates its own fresh UUID and
owns one transaction through user + credential INSERT and COMMIT. No principal
adoption, caller user_id, check-then-insert or partial commit. verify_credentials
closes its read-only lookup before real/dummy verification, returns fixed
invalid_credentials for wrong/unknown credentials and never updates hashes or
issues sessions. Error mapping uses exact SQLSTATE/named uniqueness, after unwind;
unexpected integrity errors stay faults. Native/DBAPI exception context is detached.

Confirmed explicit Argon2id v19, 19456 KiB, two iterations, one lane, random
16-byte salt and 32-byte output. Shared process-wide two-slot nonblocking budget
covers hash and real/dummy verification; no DB locks during KDF, no unbounded work
queue or cost allocation from untrusted stored parameters. Saturation is a fixed
hashing_busy error. Other stored profiles require reviewed compatibility/rehash
policy. No claimed constant timing or zeroization in Python. Caller logging/APM/
Engine listeners remain a documented trusted boundary; secret capture is forbidden.

Transaction guard requires sync PostgreSQL psycopg, actual DBAPI autocommit is
False before isolation/service SQL, no caller transaction, READ COMMITTED and safe
SQL parameter/echo configuration. It never silently changes Engine mode. Live
tests cover actual AUTOCOMMIT zero-write rejection and pool reset, failures after
each INSERT and before COMMIT, successful verification/hash preservation, no user
adoption and generic wrong/unknown outcomes. Duplicate race uses independent
connections and a bounded barrier after both private user inserts, then strictly
requires one winner, actual 23505/uq_credentials_username and fresh (1 user,
1 credential) counts. Unknown errors/timeouts, missing injected failure or invalid
counts fail; the suite does not silently accept them. No blocker found in this
bounded review; no implementation changes were needed for the checkpoint.

Actual checkpoint commands executed from backend, with no database connection:
- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
  **175 passed, 32 deselected, one existing Starlette/HTTPX deprecation warning**,
  exit 0, 4.08s. Includes real Argon2 profile/salt/roundtrip/passphrase tests,
  synchronized work-budget checks and database-free transaction/error regressions.
- `.\.venv\Scripts\python.exe -m pip check`: **No broken requirements found**,
  exit 0. No dependency installation or update in this checkpoint review.
- `.\.venv\Scripts\python.exe -m pytest credential_tests --collect-only -q`:
  **51 cases collected**, exit 0, 0.03s; no fixture execution.

Protected-baseline diff against 66d0e8fc53e9797e87f581b798767878a7e16cd8 for
backend/alembic (0001/0002/0003 + ordinary env), models, TeamService/errors,
db/core/main.py, test database identity/migration guards, frontend, scripts and
.gitignore exited 0. Initial staging area empty. Existing .gitignore confirmed
backend/.env, backend/.env.local, virtualenv/cache, node_modules/dist excluded;
tracked backend/.env query empty. No secret file opened. Only reviewed explicit
source/test/documentation and pinned dependency files are commit candidates.
Candidate/source and actual staged-blob checks must pass before committing.

Updated CREDENTIAL_SERVICES, AUTH_SCHEMA, TEST_DATABASE, architecture/decisions
and this evidence log with owner verification. Owner authorized one local commit:
`feat: add secure credential and registration services (M-007B.2A)`.
Its resulting hash is reported directly from Git, not embedded in the same commit.
No database object/role/permission/password changes, merge_dev access, merge_test
reset/disposal, fixture cleanup, HTTP endpoints, session issuance, remote creation
or push in this checkpoint. Earlier failures/corrections remain documented above.

Verified internal credential component only. G1 stays open. Sessions/cookies,
CSRF, durable rate limits, registration/login endpoints, authorization, password
change/reset/rehash, concurrent password-change/session-issuance semantics and
timing-analysis remain future work. Two hash slots are per process, not global
abuse control. Registration availability is intentionally a separate conflict.
Commit connection loss can be ambiguous; no blind retry/idempotency claim.
Auth/domain/team live regressions after this component, full legacy DB tests,
frontend/HTTP/50-way authenticated race, CI/load/deployment were not rerun here.

Owner exercise: find the exact named-constraint assertion in the duplicate race,
then explain why hashing inside the database transaction would hold locks longer
without improving the username uniqueness guarantee.

Checkpoint static evidence: parsed all 11 Python candidates with ast; reviewed the
exact 19-file source/doc/dependency allowlist and tracked path names for private
environment files, generated artifacts, credential URLs, literal real Argon2
encodings and private-key/provider-token signatures: zero actionable findings.
Two unchanged committed synthetic redaction-test URL strings are the only exact
scan exception. All prior dependency pins remain unchanged, with only the four
documented Argon2-related additions. `git ... diff --check` passed; LF/CRLF
conversion warnings remain. These checks supplement manual review rather than
proving absence of every possible unknown secret. Actual staged blobs are reviewed
against the same scope and working contents before the authorized commit.

## M-007B.2B internal session lifecycle — 2026-11-10

Baseline main HEAD efaaec134bd8ddc08c3522f33aec7b0dac5019ad, initially clean.
Read AGENTS/source-of-truth and actual auth models/DDL, credential transaction/KDF
path and guarded fixture harness. Existing 0003_auth supports this bounded service;
no migration/model/constraint or TeamService change was needed. Earlier owner
51-pass credential and 78-pass storage results are historical, not session evidence.

Implemented SessionService.login/validate/verify_csrf/revoke and fixed session
error codes. No arbitrary UUID, registration result or constructible public
identity can issue a session. login internally calls the approved real/dummy
credential verification, captures a private verified hash fingerprint/timestamp
snapshot and compares it against current credentials under user KEY SHARE then
credential SHARE locks. Any relevant intervening change rejects before INSERT;
the SHARE lock blocks hash/username/timestamp UPDATE or DELETE through commit.
No KDF/network work occurs under those write-transaction locks. Public credential
interfaces, Argon2 parameters and work budget remain unchanged; private factoring
reuses the original verification rather than implementing another password check.

Independent CSPRNG calls generate 32-byte session and CSRF values before locking.
Only SHA-256(raw session) is a session SQL parameter; CSRF uses existing server-side
storage. Sensitive result fields use SecretBytes, excluded from ordinary repr and
returned only after commit. Database clock_timestamp supplies aware UTC creation
and immutable eight-hour expiry. Fresh READ ONLY validation joins stored user and
credential, checks active times/revocation/supported credential profile and derives
the principal. No renewal. CSRF checks the active session and compare_digest.
Revocation updates only NULL revoked_at, preserving terminal timestamps on repeat
and concurrent calls. Malformed session bytes reject before DB access.

The session facade deliberately reuses CredentialService's private transaction
owner, actual synchronous psycopg AUTOCOMMIT-is-False guard, READ COMMITTED check,
safe logging requirements, timeouts and sanitized error mapper. No caller-owned
transaction/connection is accepted and Engine mode is never silently changed.
The Python/Engine code boundary is trusted, not an unforgeable capability system;
no external authentication snapshot/ticket or memory session store is exposed.
No HTTP cookie/header/authentication policy, rate limiter, password-change service,
idempotency/audit/outbox writer or authenticated team API was implemented.

Actual commands from backend, Python 3.11.9 / SQLAlchemy 2.1.8 / psycopg 3.3.8:
- `.\.venv\Scripts\python.exe -m pytest -q tests/test_sessions.py tests/test_credentials.py tests/test_passwords.py --tb=short`:
  **102 passed in 4.37s**, exit 0.
- `.\.venv\Scripts\python.exe -m pytest -q -m "not database" --tb=short`:
  **222 passed, 32 deselected, one existing Starlette/HTTPX deprecation warning**,
  5.94s, exit 0. Includes real approved Argon2 and existing team/credential guards.
- `.\.venv\Scripts\python.exe -m pip check`: **No broken requirements found**,
  exit 0. No package installation or dependency changes.
- `.\.venv\Scripts\python.exe -m pytest session_tests --collect-only -q`:
  **63 collected**, 0.05s, exit 0. No fixture execution.
- Separate `pytest credential_tests --collect-only -q`, `pytest auth_schema_tests
  --collect-only -q`, `pytest service_tests --collect-only -q` and `pytest
  concurrency_tests --collect-only -q`, each using the same venv Python:
  **51 / 78 / 48 / 45 collected**, respectively, each exit 0. Shared suite hooks
  require separate invocations. No post-change live regression pass claimed.
- `.\.venv\Scripts\python.exe -m test_support.concurrency --help`: exit 0;
  actual CLI includes sessions with explicit revision support.

Added 63 guarded session cases (21 parameter-expanded scenarios, three default
repetitions): verified issuance/fresh service use; arbitrary identity/uncredentialed
seed rejection; digest-only storage/redaction; independent secrets and CSRF;
malformed/unknown/expired/revoked/future sessions; actual database expiry crossing
without renewal; unsupported credential rejection; repeated/concurrent revoke;
post-INSERT/pre-COMMIT failure rollback; actual AUTOCOMMIT no-service-SQL rejection;
credential changes between verification and lock acquisition; and credential
UPDATE blocked from final check through issuance commit. The last schedule requires
pg_blocking_pids proof, not sleep-based overlap. Independent actual connections,
bounded events/barriers/workers, strict outcomes and fresh scoped invariants are
implemented. **Live outcomes, SQLSTATEs and PostgreSQL lock behavior remain
UNVERIFIED for this new suite.** No test failure was observed in executed checks.

Extended only the guarded fixed-suite selector/tests; sessions requires explicit
--confirm-merge-test and --revision 0003_auth. Existing actual loopback/database/
role/port checks and no-development-fallback remain intact before fixture writes.
Fixture users/credentials/sessions are UUID-scoped and retained only in merge_test;
no destructive cleanup. Private credential presence False and interactive stdin
False were checked without printing values. No backend/.env or development
credential was read/copied. **No PostgreSQL connection, test or migration was
executed by Codex during this task; merge_dev was not accessed.**

Pending owner command from backend:
`.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite sessions --revision 0003_auth --repetitions 3`.
Full read-only preflight/private-prompt commands, existing guarded regression
commands and retained-fixture caveats are in SESSION_SERVICES.md. Never supply
passwords in chat, arguments, reports or transcripts. Current schema/migrations
remain at committed 0003_auth; no migration is needed for this service.

Known limitations: Python transient secrets/traceback locals cannot be zeroized;
trusted logging/Engine hooks must not capture them. Validation is a point-in-time
read and does not cancel in-flight authenticated work on logout. Existing sessions
do not automatically revoke after a future valid password change; that workflow
must revoke explicitly. Database clock must be trusted. A COMMIT transport loss
can leave an unreachable committed row, without returning raw material; no blind
retry/idempotency guarantee. The two-second initial expiry-test window can fail on
a busy host; missing lock visibility/timeouts are failures, never successful
validation. New live session and post-change auth/domain/team/credential regressions
remain pending. No HTTP/authenticated 50-way race, CI/load/deployment or G1 closure.

Updated AUTH_SCHEMA, CREDENTIAL_SERVICES, architecture/decisions, TEST_DATABASE and
new SESSION_SERVICES contract with current evidence and trust boundaries. No
frontend, role/permission/password, schema/model/migration, TeamService or HTTP
change; no commit, remote creation or push. Final static evidence is recorded below.
Owner exercise: trace stale verification rejection and explain why credential
KEY SHARE would fail to block a non-key password UPDATE while SHARE does block it.

Final static evidence: `git -c safe.directory=I:/Merge diff --check` passed (exit
0; existing LF/CRLF conversion warnings). Read-only protected-baseline comparison
`git ... diff --exit-code HEAD -- backend/alembic backend/app/models backend/app/services/teams.py backend/app/services/errors.py backend/app/services/credential_errors.py backend/app/db backend/app/core backend/app/main.py backend/test_support/database.py backend/test_alembic backend/pyproject.toml backend/requirements.lock frontend scripts .gitignore`
passed with exit 0. All migrations 0001/0002/0003, models/domain code, TeamService,
dependency pins, HTTP/frontend and test identity/migration safeguards are unchanged.
Parsed the exact ten changed/new Python files with ast. Reviewed the exact
17-file candidate allowlist: 11 modified tracked files, six new source/doc files,
all unstaged. Source/path scan found zero actionable credential URL, literal real
Argon2 encoding, private-key/provider-token or generated/private-file findings;
the only two URL-literal exceptions are unchanged committed synthetic redaction
fixtures. An initial scanner incorrectly matched an existing bare URL-prefix
assertion; corrected the matcher to require an address and reran successfully.
These checks supplement manual review, not a proof against all unknown secrets.
Seven ignore checks passed for dotenv variants, virtualenv/cache and frontend
node_modules/dist; backend/.env is not tracked and was never opened. Staging is
empty, main HEAD remains efaaec134bd8ddc08c3522f33aec7b0dac5019ad.

Executed missing-opt-in rejection check from backend:
`.\.venv\Scripts\python.exe -m test_support.concurrency --suite sessions --revision 0003_auth`.
It exited nonzero before credentials/DB access with required --confirm-merge-test
missing. Automatic approval review rejected the separately proposed CLI check
with confirmation but missing revision because it classified it as a possible
live test run; that command was not executed. The same batch's read-only protected
diff was initially blocked and then executed separately with the passing result
above. No approval bypass or live retry. The already-passing database-free
test_auth_suite_requires_explicit_revision_before_credentials[sessions] verifies
the missing-revision parser gate without connection/password access. No remaining
implementation blocker from these tooling checks; live validation stays owner-run.

## M-007B.2B final review and checkpoint — 2026-11-10

Owner-verified result: guarded merge_test / 0003_auth session suite,
**63 passed in 51.63 seconds**, three repetitions requested. Fresh session
committed-state invariants verified. Fixtures intentionally retained. This records
the owner's PostgreSQL execution, not a Codex database rerun. No separate raw
per-case transcript or additional post-change credential/auth/domain/team live
regression result was supplied. Earlier pending-live preparation entries above
remain historical; they are superseded for this session result only.

Bounded objective: review and checkpoint the 17 pending session source/test/doc
files against main efaaec134bd8ddc08c3522f33aec7b0dac5019ad. Read AGENTS,
requirements/architecture/decisions/progress and both identity service contracts.
No implementation change was needed. Reviewed login, validate, verify_csrf,
revoke, credential handoff, error mapping and all 63 collected live cases (21
parameter-expanded scenarios, three repetitions), including shared fixture,
guarded runner and bounded worker behavior. No security or transaction-safety
blocker found within this scope.

Issuance accepts username/password only, invokes the approved real/dummy Argon2
verification with its read connection closed before KDF, and cannot accept an
arbitrary UUID or constructible identity as proof. The private fingerprint and
timestamp snapshot is rechecked under user KEY SHARE then credential SHARE;
non-key credential changes cannot pass between final check and session commit.
Two independent secrets.token_bytes(32) calls precede write locks. Only the
SHA-256 session-token digest reaches SQL/storage; independent CSRF material uses
the existing server-side column. SecretBytes/repr redaction and return-after-
commit preserve the documented internal secret boundary.

Validation uses fresh READ ONLY storage, canonical credential/profile checks,
database clock and exact eight-hour absolute lifetime; it never renews expiry.
CSRF uses compare_digest after active-session validation. Revocation updates only
NULL revoked_at, so repeat/concurrent revocation cannot rewrite terminal state.
The shared transaction guard checks actual synchronous psycopg autocommit is
False before isolation/service SQL, no active caller transaction, READ COMMITTED
and safe Engine logging. Unsupported or ambiguous states fail closed; no silent
mode changes. Database errors are sanitized after unwind, unexpected class-23
faults remain integrity faults, and no blind retries are introduced.

Live-test assertions require the intended fixed error or exact successful worker
outcomes. Unexpected DBAPI/CredentialError failures, SQLSTATEs, integrity faults,
barrier/worker/SQL deadlines and missing pg_blocking_pids evidence fail the tests.
Injected rollback tests require the precise injected exception, proof of reaching
INSERT and zero fresh committed sessions. Fresh guarded invariant observers run
after failures too. No broad exception acceptance converts infrastructure faults
into successful concurrency evidence.

Actual checkpoint commands from backend (Windows PowerShell, Python 3.11.9,
SQLAlchemy 2.1.8, psycopg 3.3.8), no database connections:
- `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short`:
  **222 passed, 32 deselected, one existing Starlette/HTTPX warning in 7.49s**,
  exit 0.
- `.\.venv\Scripts\python.exe -m pip check`: **No broken requirements found**,
  exit 0. No package installation or dependency changes.
- `.\.venv\Scripts\python.exe -m pytest session_tests --collect-only -q`:
  **63 collected in 0.04s**, exit 0; no fixtures executed.

Read-only protected-baseline command from root:
`git -c safe.directory=I:/Merge diff --exit-code efaaec134bd8ddc08c3522f33aec7b0dac5019ad -- backend/alembic backend/app/models backend/app/services/teams.py backend/app/services/errors.py backend/app/services/credential_errors.py backend/app/db backend/app/core backend/app/main.py backend/test_support/database.py backend/test_alembic backend/pyproject.toml backend/requirements.lock frontend scripts .gitignore`
passed, exit 0. Migrations 0001/0002/0003, TeamService, schema/models, dependencies,
runtime/HTTP/frontend and test target safeguards are unchanged. `git -c
safe.directory=I:/Merge diff --check` passed, with existing LF/CRLF warnings.
No configured Python linter/type-checker found; no lint pass is invented.

Inline Python static audit via `.\backend\.venv\Scripts\python.exe -` parsed all
10 Python candidates with ast and checked the exact 17-file allowlist for private/
generated paths, credential URLs, literal real Argon2 encodings and private-key/
provider-token signatures: zero actionable findings. Initial scan flagged a
preexisting synthetic redaction URL fixture; manual review confirmed both exact
placeholder URL occurrences unchanged against HEAD, and the corrected
audit passed with precisely these two exceptions. Seven dotenv/virtualenv/cache/
node_modules/dist ignore checks passed; no private/generated paths are tracked.
Actual staged blobs were checked to match the reviewed working contents and pass
the same audit before committing. These checks supplement manual review; they do not prove
the absence of every possible secret. No local secret file was opened.

Updated SESSION_SERVICES, CREDENTIAL_SERVICES, AUTH_SCHEMA, TEST_DATABASE,
architecture/decisions and this evidence log with owner verification. Owner
authorized exactly one local commit:
`feat: implement secure session lifecycle services (M-007B.2B)`.
The resulting full hash is reported from Git after commit rather than embedded
in that same commit. No remote creation or push.

Known limits: internal service only; HTTP endpoints/cookies/browser CSRF policy,
durable rate limiting, password-change/reset invalidation and authenticated team
integration remain future work. Validation is point-in-time, Python secrets/
traceback locals cannot be reliably zeroized, trusted Engine/logging hooks must
not capture secrets, database time must be trustworthy, and COMMIT transport loss
can leave an unreachable committed row. No new live regressions, HTTP/50-way race,
CI/load/deployment or G1 closure claimed. No merge_dev access, merge_test reset,
fixture cleanup, database/role/permission changes, M-008 or migration execution.

Owner exercise: explain why FOR SHARE blocks a non-key credential UPDATE while
KEY SHARE does not, then change a snapshot timestamp in the database-free
stale-credential test and verify authentication_changed with no session persisted.

## M-007B.3A-R1 interface gate and HTTP authentication — 2026-11-10

Baseline main 09a064678361315df9870c5be3ed3a8569bedcf9, clean. Read AGENTS and
requirements/architecture/decisions/progress plus AUTH_SCHEMA, credential/session/
team service contracts and TEST_DATABASE. Previous task stopped without changes
because validate() could not return CSRF. Owner explicitly approved the narrow
read-only extension, then continuation of the four HTTP authentication routes.

Interface gate: inspected installed Pydantic SecretBytes implementation and
added frozen/slotted ValidatedSession(principal, csrf_token: SecretBytes), with
CSRF excluded from repr, and validate_with_csrf(token). One existing _read_active
snapshot supplies both fields, using unchanged active-account/expiry/revocation
validation, READ ONLY transaction and actual driver/isolation guard. No bearer,
credential hash or raw row escapes, no rotation/renewal/write. Existing methods
remain AST-identical against HEAD. Before HTTP implementation, from backend:
- `.\.venv\Scripts\python.exe -m pytest -q tests/test_sessions.py tests/test_credentials.py tests/test_passwords.py --tb=short`:
  **118 passed in 10.68s**, exit 0.
- `.\.venv\Scripts\python.exe -m pytest session_tests --collect-only -q`:
  **75 collected in 0.08s**, exit 0; no fixtures executed.
- Inline Python ast.parse of the three interface/service test files passed.
Gate passed available unit/static checks; no live interface verification claimed.
Final session collection increased to 78 after adding the new method to actual
AUTOCOMMIT regression coverage. The earlier owner 63-pass result is historical.

Implemented POST /auth/register (201, identity only, no session), POST /auth/login
(200, identity/expiry/CSRF and opaque HttpOnly cookie), GET /auth/session (200,
existing validated principal/CSRF without renewal), POST /auth/logout (JSON {},
active cookie plus session-bound CSRF, 204 and cookie deletion). HTTP adapters
call only public services; no route SQL/commit, lifecycle transaction change or
hash/storage duplication. The real authentication dependency derives identity
from validated storage, never submitted UUIDs or leader flags. All mutations
require strict JSON models and exact Origin; register/login also X-Merge-Request:
1, logout X-CSRF-Token. Fetch Metadata rejects cross-site/same-site/unknown values
when present. Canonical base64url token encoding, duplicate security-header/cookie
rejection, no permissive CORS and no-store auth responses/errors.

Production defaults require explicit HTTPS origin at startup and HTTPS ASGI
requests, __Host-merge_session with Secure/HttpOnly/SameSite=Lax/Path=/, no Domain.
Explicit loopback development mode uses merge_session_dev, Secure=False. Startup
does not initialize a database; the runtime dependency creates/disposes its Engine
lazily. Missing cookie rejects before that dependency. AuthSettings reads only
MERGE_AUTH_* environment, never backend/.env. Ordinary database Settings retain
their existing local merge_dev guard; no development connection was opened here.
Vite forwards /auth without origin rewriting, alongside /health; README and the
local HTTP runner explicitly select loopback development mode. No frontend UI
redesign. Fixed {error:{code,message,retryable}} responses include sanitized 401/
403/409/415/422/503 mapping and no validation input or driver text. Unknown and
ambiguous COMMIT failures do not advertise automatic retry.

Final executed checks (Windows PowerShell; backend venv Python 3.11.9,
SQLAlchemy 2.1.8 / psycopg 3.3.8; Node/npm from existing frontend installation):
- Backend `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short`:
  **349 passed, 32 deselected, one existing Starlette/HTTPX warning in 14.98s**,
  exit 0. Earlier adapter-only run: 107 passed in 5.32s; intermediate full run:
  346 passed in 11.16s. Final count includes additional no-runtime-DB/error/OpenAPI
  checks; no test was deleted/weakened.
- Backend `.\.venv\Scripts\python.exe -m pytest -q tests/test_auth_http.py --tb=short`:
  **109 passed, one existing warning in 5.61s**, exit 0, after adding exact
  retryable-flag assertions. The guarded AUTOCOMMIT API case was also strengthened
  to require actual driver state True plus the captured fixed
  transaction_configuration error, so arbitrary infrastructure 503s cannot pass
  as transaction-safety evidence; its live execution remains pending.
- Backend `.\.venv\Scripts\python.exe -m pip check`: no broken requirements,
  exit 0; no package installs or dependency changes.
- Backend `.\.venv\Scripts\python.exe -m pytest session_tests --collect-only -q`
  and `.\.venv\Scripts\python.exe -m pytest auth_api_tests --collect-only -q`:
  **78 / 54 collected**, respectively, exit 0. Collection opens no database.
- Frontend `npm.cmd run typecheck`, `npm.cmd test`, `npm.cmd run build`: exit 0;
  **6 tests passed**, production build completed (Vite 6.4.5).
- Root `.\backend\.venv\Scripts\python.exe scripts/check_local_http.py`:
  passed API health, frontend HTML, /health proxy, /auth missing-cookie 401 proxy,
  real API outage error and restart recovery. No database used. The new /auth
  proxy check first exceeded its existing two-second request timeout while run
  concurrently with backend regressions. Standalone rerun passed all assertions;
  timeout was a failed run, not a success, and the assertion/deadline was retained.

Private test credential presence False and interactive input False were checked
without printing values. No backend/.env read/copied or PostgreSQL connection,
test, migration, reset, DROP, fixture cleanup or merge_dev access by Codex. Added
dedicated fixed --suite auth-api with explicit --revision 0003_auth and tests for
the parser gate/selection. Its real-service fixtures reuse actual per-connection
merge_test/merge_app/loopback/port/revision guards and fresh scoped committed
invariants. Unique users/credentials/sessions are retained. Exact successes/error
codes are required; unexpected SQLSTATEs, integrity faults/timeouts fail. Safe
owner commands (read-only verify, extended sessions, auth-api) are in HTTP_AUTH.md.
No new live pass is claimed; prior owner 63-pass session evidence is not a rerun.

Static review: `git -c safe.directory=I:/Merge diff --check` passed (LF/CRLF
conversion warnings). Inline Python parsed 14 changed/new Python files, compared
all original SessionService methods against baseline AST, rejected private
service/SQL/commit access in the HTTP adapter and scanned candidate paths/content
for private/generated files, real Argon2 encodings, database credential URLs,
private keys and provider tokens. No actionable findings; only the two unchanged
synthetic redaction URL fixtures are excepted. Seven environment/cache/venv/
node_modules/dist ignore checks passed. These supplement manual review, not proof
against every possible secret. No Python linter is configured; no lint pass claimed.

Protected baseline diff command (root) passed, exit 0:
`git -c safe.directory=I:/Merge diff --exit-code 09a064678361315df9870c5be3ed3a8569bedcf9 -- backend/alembic backend/app/models backend/app/services/teams.py backend/app/services/credentials.py backend/app/services/credential_errors.py backend/app/services/errors.py backend/app/security/passwords.py backend/app/db backend/app/core/config.py backend/test_support/database.py backend/test_alembic backend/pyproject.toml backend/requirements.lock .gitignore`.
Migrations 0001/0002/0003, models/constraints, TeamService, credentials/KDF, DB
configuration and test identity/migration guards are unchanged. Source-of-truth
contracts/ADR-011/requirements/progress and README now describe implemented versus
verified scope. No staging, commits, remotes or pushes; owner review requested.

Limitations: shared throttling deferred to M-007B.3B; routes are not production-
ready. Live API/extended session/other post-change guarded regressions, browser
E2E, deployed HTTPS/trusted-proxy/logging/DB-role setup and cache policy remain
unverified. Existing per-process KDF budget is not abuse prevention. Registration
availability disclosure, stolen bearers, XSS, database clock trust, Python secret
retention, point-in-time validation and ambiguous COMMIT loss remain documented.
No password reset/change policy, team mutation/authZ, invitation/request API,
idempotency/audit/outbox, M-008, 50-way authenticated HTTP race, CI/load/deployment
acceptance or G1 closure.

Owner exercise: explain the single validated read snapshot, then omit the login
custom header and try another session's CSRF at logout; both must reject before
the requested mutation. Contracts and exact commands: HTTP_AUTH.md.

## M-007B.3A final review and commit checkpoint — 2026-11-10

Owner-verified live results: merge_test at **0003_auth (head)**; expanded session
suite **78 passed in 72.48 seconds**, HTTP API suite **54 passed in 40.90 seconds**,
**132 passing live executions** total. Fresh committed-state invariants verified;
one existing Starlette/HTTPX deprecation warning. This records owner execution,
not a Codex PostgreSQL rerun. No separate per-case transcript or additional
post-change credential/auth-schema/domain/team live suite result was supplied.
Earlier pending-live preparation entries remain historical; these results
supersede them for the expanded sessions and HTTP API suite only.

Review scope: all 26 pending source/test/config/doc files against main baseline
09a064678361315df9870c5be3ed3a8569bedcf9. Read AGENTS and relevant source-of-truth
requirements/architecture/decisions/progress, HTTP_AUTH, SESSION_SERVICES,
AUTH_SCHEMA, TEST_DATABASE and credential/team contracts. No implementation
change was required. Reviewed all four routes, single-snapshot CSRF extension,
logging/error boundaries, configuration, shared service transaction owner and
all 54 live API cases (18 expanded scenarios, three repetitions), their fixtures,
runner and relevant extended session cases. No security or transaction-safety
blocker found within this bounded scope.

validate_with_csrf calls the unchanged active READ ONLY lookup once, returning
only frozen/slotted principal and repr-excluded SecretBytes CSRF. It does not
return a bearer, hash or database row or extend expiry. All original session
methods remain AST-identical against baseline. Protected identity comes from
validated storage; strict request models forbid actor_id/user_id/identity/leader
fields. Registration cannot authenticate or create a session. Login invokes the
existing credential-verified session facade and returns no bearer in JSON.
Logout checks active state and session-bound CSRF through public services before
revocation; no route SQL/commit or transaction-boundary changes. Actual DBAPI
AUTOCOMMIT and READ COMMITTED guards remain unchanged.

Confirmed production-only __Host-merge_session, Secure, HttpOnly, SameSite=Lax,
Path=/, no Domain and matching deletion attributes. Explicit loopback development
mode uses a separate cookie without Secure; production defaults reject insecure
or missing origin configuration at startup. JSON-only mutations require exact
configured Origin, register/login custom header and logout CSRF; supplied Fetch
Metadata rejects non-same-origin values. No reflected/permissive credentialed CORS.
No-store headers cover auth responses/errors. Passwords use redacted request
fields; response models omit bearer/hash/connection data. Validation and DB/native
failures return fixed public errors and never format raw details. Trusted hosting,
SQL/server logging, APM and traceback-local capture remain deployment boundaries.

API assertions require exact successful statuses or intended rejection/error
codes and fresh state counts. Unknown database errors/integrity faults/timeouts
cannot stand in for credential, cookie or CSRF rejections. The deliberate
AUTOCOMMIT HTTP 503 requires actual driver state True, captured fixed
transaction_configuration failure, zero service SQL and zero committed sessions;
an unrelated infrastructure 503 cannot satisfy it. Fixtures use guarded real
services and fresh actual test connections; ordinary runtime Engine initialization
is forbidden in the API fixture. No tests were changed or weakened for this review.

Executed checkpoint checks (Windows PowerShell; Python 3.11.9 / SQLAlchemy 2.1.8 /
psycopg 3.3.8, existing Node/npm installation):
- Backend `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short`:
  **349 passed, 32 deselected, one existing warning in 17.49s**, exit 0.
- Backend `.\.venv\Scripts\python.exe -m pip check`: **No broken requirements
  found**, exit 0. No dependency installation/update.
- Backend `.\.venv\Scripts\python.exe -m pytest session_tests --collect-only -q`
  and `.\.venv\Scripts\python.exe -m pytest auth_api_tests --collect-only -q`:
  **78 in 0.08s / 54 in 0.05s collected**, exit 0, no fixtures executed.
- Frontend `npm.cmd run typecheck`, `npm.cmd test`, `npm.cmd run build`: exit 0;
  **six tests passed**, Vite 6.4.5 build completed in 3.96s.
- Root `.\backend\.venv\Scripts\python.exe scripts/check_local_http.py`: initial
  standalone run failed with a two-second timeout at the /auth/session proxy
  assertion, after health/frontend checks passed. Separate timed no-database
  diagnostic returned actual 401: direct 0.031s, first proxy 1.484s, next proxy
  0.157s (diagnostic request deadline 10s). The unchanged ordinary script then
  passed standalone: health/frontend, /auth missing-cookie 401, outage error and
  restart recovery. No timeout counted as success; no deadline/assertion was
  relaxed. Both earlier concurrent and current standalone flakiness remain open.

Static evidence: `git -c safe.directory=I:/Merge diff --check` passed (existing
LF/CRLF conversion warnings). Inline Python via
`.\backend\.venv\Scripts\python.exe -` checked the exact 26-file allowlist,
parsed all 14 Python files, verified original session-method AST equality and no
HTTP private-service/SQL/commit access, inspected source/path/whitespace safety
and required seven ignore checks. No actionable secret/generated/unrelated-file
findings. Reviewed exact synthetic exceptions: two unchanged database-URL
redaction fixtures and one rejected HTTP-origin user/password fixture. No secret
file opened; backend/.env remains untracked/ignored. These checks supplement
manual review and do not prove absence of every possible secret. No configured
Python linter; no lint pass claimed. Staged blobs are checked against the same
scope and reviewed working contents before committing.

Protected baseline command passed, exit 0:
`git -c safe.directory=I:/Merge diff --exit-code 09a064678361315df9870c5be3ed3a8569bedcf9 -- backend/alembic backend/app/models backend/app/services/teams.py backend/app/services/credentials.py backend/app/services/credential_errors.py backend/app/services/errors.py backend/app/services/session_errors.py backend/app/security/passwords.py backend/app/db backend/app/core/config.py backend/test_support/database.py backend/test_alembic backend/pyproject.toml backend/requirements.lock scripts/*.sql scripts/configure_backend_env.py .gitignore`.
Migrations 0001/0002/0003, models/domain constraints, TeamService, credential/KDF
code, DB runtime settings, guarded identity/migration support, provisioning/role/
permission scripts and dependency pins are unchanged. No database connection or
role/ACL mutation was performed by Codex; external role state was not queried.
No merge_dev access, merge_test reset/drop/cleanup, migrations or live test rerun.

Updated HTTP_AUTH, SESSION_SERVICES, AUTH_SCHEMA, TEST_DATABASE, credential,
architecture/decision/requirement/progress docs with owner verification. Approved
one local commit: `feat: add secure HTTP authentication endpoints (M-007B.3A)`.
Full resulting hash is read/reported from Git after commit, not embedded in its
own contents. No remote creation or push; no rate limiter or team API added.

Outstanding: shared throttling (M-007B.3B), intermittent proxy timing failure,
browser E2E/deployed HTTPS/trusted proxy/cache/logging verification and deployment
DB-role topology. No production-readiness or browser HTTPS-security claim.
Password-change invalidation, Python transient secret retention, XSS/stolen
bearers, database time trust, point-in-time logout and ambiguous COMMIT transport
loss remain documented. No team mutation/authZ, invitation/request API, M-008,
idempotency/audit/outbox, 50-way authenticated team race, CI/load/deployment
acceptance or G1/G2 closure. Other post-change live suites remain unreported.

Owner exercise: explain why the GET returns CSRF from the same validated snapshot,
then omit X-Merge-Request from login and confirm 403 without credential mutation.

## M-007B.3B durable PostgreSQL auth throttling — 2026-11-10

Baseline main 05db480b1d128e6a3c2b382227de86b080f6ab43, initially clean. Read AGENTS,
requirements/architecture/decisions/progress and HTTP_AUTH, AUTH_SCHEMA,
credential/session services and TEST_DATABASE; inspected actual 0003_auth DDL,
models and HTTP adapter. Proposed the bounded contract in DECISIONS before coding.
The existing throttle PK/counter/expiry supports it without schema changes.
Prior owner 54 HTTP / 78 session passes remain pre-throttling evidence only.

Implemented a separate ThrottleService using the existing credential transaction
owner and exact AUTOCOMMIT-is-False / READ COMMITTED guard. Aligned DB-clock
date_bin windows and atomic INSERT ON CONFLICT updates saturate attempts at N+1
without overflow. Defaults: 300 seconds, login canonical-account 5, login IP 30,
registration IP 5. HTTP config ranges: window 60–3600, account 1–100, login IP
1–500, registration IP 1–50. No disabled/unlimited option. Charge IP before account;
skip account creation on IP denial, preserve the IP charge on account denial.
Return the decision and commit before raising 429; KDF/session/registration work
starts only after throttle commit. Narrow lock/statement timeouts: 1s/2s. Storage,
integrity/configuration or unexpected failure gives sanitized 503 and no KDF.
No route SQL/commit, password hashing duplication or session lifecycle changes.

Domain-separated HMAC-SHA256 keys use a required explicit private 32-byte secret
(64 lowercase hex); raw username/IP/secret never reaches limiter SQL or public
responses/errors. Existing canonical ASCII account validation remains unchanged.
Secret/settings must match all workers/restarts, with no random runtime fallback.
Responses use existing structured errors plus 429 rate_limited and bounded
Retry-After from database time, ceil/clamp 1..window, auth no-store headers.
Successful and failed valid requests consume budget; no success-based reset.

Actual-peer client identity rejects untrusted/ambiguous forwarding and normalizes
IPv4-mapped IPv6. Explicit single-hop proxy mode requires an allowed literal peer,
one overwritten literal XFF and one exact http/https XFP. Alternative headers,
chains, duplicates, malformed peers and wildcard(/0) trust fail closed. Independent
review found a mapped-/0 startup-validation mismatch; it was corrected and tested.
The new app.serve launcher fixes proxy_headers=False/forwarded_allow_ips='' and
disables access logs, preventing stock Uvicorn loopback trust from rewriting the
peer before app policy. README, HTTP_AUTH and the local HTTP runner use it.
The reverse proxy/alternative ASGI host remains trusted deployment configuration;
actual public TLS/proxy/browser security is not claimed verified.

Added 80 database-free throttle-service cases using the real transaction owner
with queued fake SQL results, 84 actual-peer policy cases and HTTP throttle/error/
configuration/launcher tests. These do not prove PostgreSQL atomicity. Existing
HTTP/health tests now supply explicit synthetic secret/literal peers and a typed
limiter double; real API regression fixtures inject the real limiter with a
unique per-case private fixture key. They still execute the actual default limits
and services, with no runtime bypass. HTTP AUTOCOMMIT regression now captures the
earliest limiter guard; independent unchanged session cases retain lifecycle guard
coverage. No existing test deleted or weakened.

Dedicated guarded --suite throttles / explicit 0003_auth collects 33 cases at
three repetitions: first N/saturation/committed denial, separate account/IP
budgets, account and IP races over eight actual concurrent PostgreSQL connections
with eight backend PIDs required, DB-clock expiry/reset with retained old bucket,
shared two-app login/registration, wrong/unknown credentials consuming quotas,
real lock failure requiring exact 55P03 plus zero hashing/accounts/extra charge,
and actual driver AUTOCOMMIT True with fixed configuration failure/zero service
SQL. Other faults/timeouts become failures, never expected 429/503 successes.
Fresh observers recheck revision and scoped throttle/session/credential invariants
after cases, including failure paths. No cleanup, reset or trigger disabling.
Independent read-only review found no remaining security/transaction blocker.

Executed checks (Windows PowerShell, existing backend Python 3.11.9, SQLAlchemy
2.1.8 / psycopg 3.3.8):
- Backend `.\.venv\Scripts\python.exe -m pytest -q tests/test_auth_http.py tests/test_auth_throttle_http.py tests/test_health.py --tb=short`:
  **140 passed in 9.41s**, one existing Starlette/HTTPX warning, exit 0.
- Backend `.\.venv\Scripts\python.exe -m pytest -q tests/test_client_identity.py --tb=short`:
  **84 passed in 0.31s**, exit 0 (independent component verification).
- Backend `.\.venv\Scripts\python.exe -m pytest -q tests/test_throttling.py --tb=short`:
  **80 passed in 1.48s**, exit 0 (independent component verification).
- Backend `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short`:
  **546 passed, 32 deselected, one existing warning in 17.56s**, exit 0.
- Backend `.\.venv\Scripts\python.exe -m pip check`: **No broken requirements
  found**, exit 0. No package installs or dependency updates.
- Separate backend `.\.venv\Scripts\python.exe -m pytest throttle_tests --collect-only -q`,
  `... -m pytest auth_api_tests --collect-only -q`, and
  `... -m pytest session_tests --collect-only -q`: **33 / 54 / 78 collected**,
  exit 0, fixtures not executed. Throttle collection repeated after strengthening
  the actual connection schedule: 33 in 0.02s; no live run.
- Root `.\backend\.venv\Scripts\python.exe scripts/check_local_http.py`: exit 0;
  controlled-server health, frontend HTML, /health and /auth missing-cookie 401
  proxy, outage error and restart recovery all passed. No database access. Earlier
  proxy timing failures remain an open limitation; no timeout was accepted or
  deadline weakened. Frontend code unchanged; frontend build/tests were not rerun
  in this bounded backend task (previous six-test/build evidence is historical).
- AST parsing and `git -c safe.directory=I:/Merge diff --check` passed (existing
  LF/CRLF conversion warnings). Full candidate/path/secret/whitespace review and
  protected-baseline checks are part of the final source review; no Python linter
  is configured and no lint pass is invented.

Private test credential availability False and interactive hidden input False
were checked without printing values. No database connection/test/migration was
executed by Codex, no merge_dev access or backend/.env read/copied. Guarded live
throttle and updated HTTP/session outcomes remain UNVERIFIED. Exact owner-run
read-only verify and three fixed-suite hidden-password commands are documented
in AUTH_THROTTLING.md. Test fixture secrets are ephemeral and retained rows scoped;
only the deliberate multi-instance tests share keys. No production key generated,
persisted in source, printed or changed by Codex.

Known limits: fixed-window boundary bursts (up to 2N), pre-wait window assignment,
account-denial abuse, shared NAT budgets, exact IPv6 address rotation, distributed
IPs, required identical settings/secret, and retained expired-row/storage growth.
No automatic cleanup or background worker; retention needs later owner review.
One-second expiry and near-hour-boundary test schedules can fail on busy hosts;
they are failed tests, not proofs. HMAC is pseudonymization, not anonymity.
No deployed proxy/TLS/browser E2E, timing equality, production readiness, global
DDoS control or per-user immunity is claimed. Existing Python secret retention,
clock trust, point-in-time logout and ambiguous COMMIT caveats remain.

No changes to migrations 0001/0002/0003, models/domain constraints, TeamService,
credential/session/KDF implementations, DB settings/roles/permissions, core
dependencies or frontend. No team/invite/request endpoints, M-008,
idempotency/audit/outbox, CI/load/deployment acceptance or gate closure. No staging,
commit, remote creation or push. Stop after implementation for owner review.

Owner exercise: trace why throttle denial must be raised after commit. Change the
account limit from 5 to 3 consistently across app instances, then predict the
fourth valid login request's 429 and why rotating IP cannot bypass that account
budget. Contract and full changed-file inventory: AUTH_THROTTLING.md.

Final static evidence: inline Python via
`.\backend\.venv\Scripts\python.exe -` checked the exact 30-file candidate
allowlist (21 modified tracked, nine new), parsed all 19 Python files and scanned
all source/doc contents and paths for whitespace, private/generated artifacts,
database/basic-auth credential URLs, real Argon2 encodings, private keys and
provider tokens. Zero actionable findings; only the unchanged committed synthetic
redaction/rejected-origin URL fixtures were excepted. Seven ignore checks passed;
backend/.env is untracked/ignored and was not opened. HTTP adapter AST has no SQL
or commit access; HEAD unchanged and index empty. This supplements manual review,
not proof against every possible unknown secret. No staging/commit was performed.

Protected-baseline command from root passed, exit 0:
`git -c safe.directory=I:/Merge diff --exit-code 05db480b1d128e6a3c2b382227de86b080f6ab43 -- backend/alembic backend/app/models backend/app/services/teams.py backend/app/services/credentials.py backend/app/services/credential_errors.py backend/app/services/sessions.py backend/app/services/session_errors.py backend/app/security/passwords.py backend/app/db backend/app/core/config.py backend/test_support/database.py backend/test_alembic backend/pyproject.toml backend/requirements.lock frontend scripts/*.sql scripts/configure_backend_env.py .gitignore`.
The subsequent `git -c safe.directory=I:/Merge diff --check` also passed. SQL
provisioning/permission scripts and existing test-target guards remain unchanged;
no external database/role state was queried or mutated. Final source status is
intentionally dirty for owner review on main, HEAD
05db480b1d128e6a3c2b382227de86b080f6ab43, with no remote/push action.

## M-007B.3B final review and local commit checkpoint - 2026-11-10

Owner-verified live evidence supplied for this review, guarded merge_test /
0003_auth suites, three repetitions requested:

| Suite | Result | Duration |
|---|---|---|
| Throttles | 33 passed | 31.42s |
| Updated authentication API | 54 passed | 30.94s |
| Session regressions | 78 passed | 48.33s |
| Combined | 165 passed | 110.69s |

Fresh committed-state invariants verified; existing Starlette/HTTPX deprecation
warning remains. This records owner execution, not a Codex PostgreSQL rerun.
No separate per-case transcript was supplied. These results supersede earlier
pending-live M-007B.3B statements for these three suites only; other historical
results and outstanding acceptance gates retain their original scope.
Reproduction commands from backend (not executed by Codex):

    .\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite throttles --revision 0003_auth --repetitions 3
    .\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite auth-api --revision 0003_auth --repetitions 3
    .\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite sessions --revision 0003_auth --repetitions 3

Reviewed all 30 candidate files against baseline
05db480b1d128e6a3c2b382227de86b080f6ab43, including all dedicated throttle
scenarios, updated API cases, unchanged session regressions, fixtures and guarded
runner. Read AGENTS, relevant requirements/architecture/decisions/progress and
AUTH_THROTTLING, HTTP_AUTH, TEST_DATABASE contracts. No blocking correctness or
security issue found within this bounded scope. No implementation, dependency,
migration, role or permission change was needed during final review; only
checkpoint documentation was refreshed.

Confirmed database-clock aligned fixed windows and one parameterized atomic
UPSERT per scope. The existing unique key serializes competing connections;
LEAST(existing_attempts,limit)+1 saturates before addition. The independent owned
READ COMMITTED transaction commits its decision before ThrottleExceeded becomes
HTTP 429, including IP charge on account denial. IP denial skips account insertion.
KDF/service work begins only after admission commit. Persistent storage/commit/
configuration/integrity or unexpected failures return sanitized 503 and never
bypass enforcement; ambiguous commit loss cannot authorize work. No in-memory
admission authority or retry loop.

Confirmed required environment-only shared 32-byte HMAC key, redacted settings,
no hardcoded runtime key, logging or random runtime fallback. Scope plus NUL
domain separation distinguishes login IP/account and registration IP; only the
digest/fixed scope reaches counter SQL. Synthetic unit keys and unique private
per-case integration keys are fixtures. All workers/restarts must reuse matching
key/policy. Actual-peer normalization and explicit immediate-proxy checks reject
untrusted, duplicate, chained or alternative forwarding. The controlled launcher
disables upstream header rewriting and access logs. Proxy overwrite/ingress/TLS
configuration remains a deployment trust boundary.

Race assertions require eight distinct backend PIDs and exactly three admissions/
five denials, then inspect committed saturation. Denial, expiry/reset, multi-app
sharing and wrong/unknown-credential tests inspect fresh state. Deliberate lock
failure requires exact 55P03, no hashing/accounts/extra committed charge.
AUTOCOMMIT cases require actual driver True, fixed configuration failure and
zero service SQL. Other database errors remain CredentialError, distinct from
intended throttle/session denial; worker infrastructure errors/deadlines fail.
The HTTP guard moved to the earliest throttle boundary; unchanged direct session
AUTOCOMMIT cases retain lifecycle coverage. No tests were weakened for this review.

Executed final checks, Windows PowerShell, Python 3.11.9 / SQLAlchemy 2.1.8 /
psycopg 3.3.8, existing frontend Node/Vite installation:

- Backend database-free regressions: **546 passed, 32 deselected, one existing
  warning in 8.52s**, exit 0.
- Backend dependency check: **No broken requirements found**, exit 0.
- Separate guarded-suite collection: **33 throttles in 0.02s / 54 API in 0.03s /
  78 sessions in 0.03s**, all exit 0; fixtures not executed.
- Root controlled-launcher HTTP/Vite regression: **PASS**, exit 0; health,
  frontend HTML, Vite health proxy, missing-session 401, actual outage HTTP error
  and restart recovery. No database access. This pass does not resolve prior
  proxy timing flakiness.
- Diff whitespace check: exit 0; existing LF/CRLF conversion warnings only.
- Inline Python source audit: exact 30-file allowlist, 19 Python ASTs, HTTP
  adapter without SQL/private transaction access, path/secret-pattern/whitespace
  scan and seven ignores; no actionable findings. One candidate credential-URL
  match was the unchanged committed synthetic rejected-origin fixture. No
  private environment file opened. This supplements manual review, not a proof
  against every possible secret. Repeat audit and inspect staged contents before
  commit.
- No configured Python linter; no lint pass claimed. Frontend unchanged;
  standalone frontend typecheck/unit/build not rerun. No installs/updates.

Exact commands from backend:

    .\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short
    .\.venv\Scripts\python.exe -m pip check
    .\.venv\Scripts\python.exe -m pytest throttle_tests --collect-only -q
    .\.venv\Scripts\python.exe -m pytest auth_api_tests --collect-only -q
    .\.venv\Scripts\python.exe -m pytest session_tests --collect-only -q
    .\.venv\Scripts\python.exe -c "import platform, sqlalchemy, psycopg; print('Python', platform.python_version(), '/ SQLAlchemy', sqlalchemy.__version__, '/ psycopg', psycopg.__version__)"

Exact root commands (source audit supplied inline to Python):

    .\backend\.venv\Scripts\python.exe scripts/check_local_http.py
    .\backend\.venv\Scripts\python.exe -
    git -c safe.directory=I:/Merge diff --check
    git -c safe.directory=I:/Merge diff --exit-code 05db480b1d128e6a3c2b382227de86b080f6ab43 -- backend/alembic backend/app/models backend/app/services/teams.py backend/app/services/credentials.py backend/app/services/credential_errors.py backend/app/services/sessions.py backend/app/services/session_errors.py backend/app/security/passwords.py backend/app/db backend/app/core/config.py backend/test_support/database.py backend/test_alembic backend/pyproject.toml backend/requirements.lock frontend scripts/*.sql scripts/configure_backend_env.py .gitignore

Protected-baseline check passed, exit 0. Migrations 0001/0002/0003, models/domain
constraints, TeamService, credential/session/KDF implementations, DB settings/
identity guards, provisioning/privilege scripts, dependency pins and frontend are
unchanged. Codex opened no database connection, queried no external role/ACL state,
performed no migration, reset/drop/cleanup, role/permission or credential change.
No merge_dev access. Sandbox initialization failed; approved elevated local
execution was used for review/check commands. No global settings changed.

Updated current summaries in README, AUTH_THROTTLING, HTTP_AUTH, TEST_DATABASE,
AUTH_SCHEMA, CREDENTIAL_SERVICES, SESSION_SERVICES, ARCHITECTURE, DECISIONS,
REQUIREMENTS and this log; preparation entries remain historical.
Owner authorized one local commit after successful review:

    feat: add durable authentication throttling (M-007B.3B)

The full resulting hash and final Git status are read from Git and reported after
commit; the commit cannot embed its own hash. No remote creation or push.

Remaining: production HTTPS/trusted proxy/browser E2E/cache/logging verification,
prior proxy timing flakiness, coordinated key/policy provisioning and retained
bucket storage monitoring/owner-approved retention. Fixed-window edge bursts,
pre-wait window assignment, account denial, NAT sharing, IPv6/distributed IP
rotation and HMAC pseudonymization caveats remain. Existing session/clock/secret
retention/ambiguous-COMMIT limits persist. No production-readiness claim, M-008,
team mutation endpoints, invite/request authorization, audit/outbox, 50-way
authenticated team race, CI/load/deployment acceptance or gate closure.

Owner explanation/exercise: PostgreSQL serializes charges at the unique bucket
row; returning a decision lets the transaction commit before HTTP denial.
Explain why raising inside that transaction would undo the charge. Change the
login account limit consistently from 5 to 3 across instances and predict why
the fourth valid request gets 429 even after changing IP.

## M-008B transaction-local team mutation extraction — 2026-11-10

Historical implementation preparation; pending-live statements below are
superseded by the M-008B final review/checkpoint entry later in this log.

Baseline: clean main at 35b14080be905f8a7d3e0921724cf4d07fd779c4.
Read AGENTS and source-of-truth requirements/architecture/decisions/progress,
SCHEMA, TEAM_SERVICES and TEST_DATABASE; inspected actual TeamService, schema
constraints and existing real service tests before editing. Owner approved the
M-008A extraction boundary for this task; other composition policies are future
work. No invariant or transaction/locking protocol needed to be weakened.

Changed five files: backend/app/services/teams.py,
backend/tests/test_team_services.py, backend/service_tests/test_teams.py,
docs/TEAM_SERVICES.md and this log. No new dependencies, migrations or files.

Extracted _create_team_in_tx(connection, command) and
_join_team_in_tx(connection, command), using private frozen/slotted
_CreateTeamCommand/_JoinTeamCommand data. Public input validation, signatures,
creation UUID timing and immutable TeamResult remain unchanged. The private
operations use only the supplied connection and contain the same SQL operations
as the former closures. No unused _join_locked_in_tx split: a second authorized
admission path does not exist yet. No version update, idempotency, audit/outbox,
retry framework, public team HTTP route or frontend work.

Before: public validation -> _execute -> connect/guard/begin/timeouts -> nested
closure -> locks/checks/writes/count -> COMMIT -> result.
After: public validation/private command -> _execute -> connect/guard/begin/
timeouts -> extracted private operation -> identical locks/checks/writes/count ->
COMMIT -> result. The actual order is connect, actual DBAPI guard/isolation check,
begin, SET LOCAL, operation, commit, close, return; no guard SQL precedes the
actual AUTOCOMMIT rejection. Engine initialization/test identity listeners remain
the existing trusted metadata-only boundary.

_execute is still the only connection/transaction owner. Extracted methods never
open/begin/commit/roll back/close a connection and expose no new public API. Their
internal preconditions are validated commands and an active owner-guarded
transaction; Python-private methods are not an adversarial in-process sandbox.
Public APIs retain Engine-only construction and reject caller transactions.
Hackathon SHARE -> user NO KEY UPDATE -> existing team NO KEY UPDATE is unchanged;
create inserts its own team/founder. Counts remain fresh post-lock SQL queries.
Founder leadership, deleted-team rules, frozen sizes, deferred final-state guards,
timeouts (5s/15s), READ COMMITTED, actual DBAPI AUTOCOMMIT rejection and named
constraint/error mapping are preserved. A local result is not a committed public
result: _execute must still finish COMMIT before the public method returns it.

Actual offline evidence, Windows PowerShell, Python 3.11.9 / SQLAlchemy 2.1.8 /
psycopg 3.3.8, existing venv, commands from backend:
- `.\.venv\Scripts\python.exe -m pytest -q tests/test_team_services.py --tb=short`:
  **55 passed in 0.57s**, exit 0.
- `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short`:
  **554 passed, 32 deselected, one existing Starlette/HTTPX warning in 10.58s**,
  exit 0; includes unchanged authentication/throttling database-free regressions.
- `.\.venv\Scripts\python.exe -m pip check`:
  **No broken requirements found**, exit 0; no installs/updates.
- `.\.venv\Scripts\python.exe -m pytest service_tests --collect-only -q`:
  **57 cases collected in 0.07s**, exit 0; no fixtures executed.

Added eight database-free executions proving exact supplied connection/command
use, one owner begin/commit, absence of local lifecycle calls and create/join
insert/deferred-COMMIT unwind before error mapping. The test fake now records
active state and begin/commit counts, rejecting nested begin; it does not prove
PostgreSQL behavior. Every original test function and decorator is unchanged.

Prepared nine additional guarded executions (three scenarios, three repetitions):
real create/join connection/root-transaction/single-commit observation with fresh
roster/leader/unchanged-version/empty-support checks; failed join INSERT rollback
and later successful admission. All 48 original service executions, including
founder/deferred rollback, final-seat/same-user/create races and actual AUTOCOMMIT
rejection, remain intact. Guarded results for this refactor are **PENDING**.
The earlier owner-verified 48 in 37.23s and auth/throttle 165 in 110.69s are
historical results, not post-refactor live executions.

Static checks actually executed from root:
- Inline Python via `.\backend\.venv\Scripts\python.exe -` compared baseline and
  working ASTs: _execute, actual DBAPI guard and all existing SQL helpers are
  identical; public signatures/validation/UUID timing and moved operation bodies
  are identical; no local lifecycle calls/new public methods; every original
  unit/live test function and decorator preserved. PASS, exit 0.
- `git -c safe.directory=I:/Merge diff --check`: PASS, exit 0; existing LF/CRLF
  conversion warnings only. No configured Python linter; no lint pass claimed.
- Final inline source audit: exact five-file scope, three Python ASTs,
  path/secret-pattern/whitespace review and six ignore checks passed, exit 0.
  No actionable secret/generated/unrelated-file findings; no staged/untracked
  files and HEAD unchanged. This supplements manual review, not proof against
  every possible unknown secret. No private environment file opened.
- Protected-baseline diff exited 0 for migrations, models/constraints, error
  mapper, authentication/session/throttle/security, DB/core settings, guarded
  test infrastructure, dependency pins, frontend, scripts and .gitignore:
  `git -c safe.directory=I:/Merge diff --exit-code 35b14080be905f8a7d3e0921724cf4d07fd779c4 -- backend/alembic backend/app/models backend/app/services/errors.py backend/app/services/credentials.py backend/app/services/credential_errors.py backend/app/services/sessions.py backend/app/services/session_errors.py backend/app/services/throttling.py backend/app/auth.py backend/app/main.py backend/app/security backend/app/db backend/app/core backend/test_support backend/concurrency_tests backend/pyproject.toml backend/requirements.lock frontend scripts .gitignore`.

Private credential presence was checked without printing a value: no
MERGE_TEST_DB_PASSWORD supplied. stdin reported interactive; no hidden prompt was
invoked and no credential was requested/read. Codex opened no database connection,
accessed no merge_dev or private environment file and ran no live test/migration,
reset/drop/cleanup, role/permission or credential change. Only offline tests and
fixture-free collection were executed. No frontend/build/browser/HTTP deployment
checks rerun for this bounded backend extraction.

Current owner-run command, NOT executed by Codex. Run in an interactive
PowerShell terminal without transcripts; use the existing hidden password prompt:

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Read-only target verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite services --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'M-008B service verification failed. Stop; do not change constraints.' }
```

The runner selects services and the current verified 0003_auth explicitly;
existing per-connection target guards and fresh invariant observers remain in
force. No migration/reset is needed. Record the new pass/fail count, duration,
fresh-state checks and warnings as a separate follow-up entry after owner execution.
No post-refactor concurrency/invariant pass is claimed from collection or mocks.

Risks/missing work: live refactor verification pending; raw-writer deadlocks,
mutation-time snapshot counts and ambiguous COMMIT remain documented. No automatic
retry/idempotency safety was added. Later composition must keep one transaction
owner and must not call the committing facade from an outer transaction.
G1 remains open for idempotency and authenticated 50-way API/CI acceptance.
No public mutation/authZ, invitation/request, audit/outbox, load/deployment or
production-readiness claim. HEAD is unchanged; changes remain unstaged for owner
review. No commit, remote creation or push.

Owner exercise: identify where the supplied connection reaches _insert_membership,
then explain why an exception at COMMIT after _join_team_in_tx has returned still
rolls back membership and prevents a public TeamResult. Predict the behavior if a
second begin() were added to the extracted method; the ownership tests must fail.

## M-008B-R1 interrupted service verification investigation — 2026-11-10

Historical investigation. The interruption remains inconclusive; the subsequent
full 57-case pass is recorded separately in the final checkpoint below.

Owner-reported partial live evidence: merge_test authentication succeeded;
revision 0003_auth (head); **8 passed in 13.17s**, with fresh committed-state
invariant reports for completed cases. Execution ended with KeyboardInterrupt
inside psycopg.connection.py. The 57-case suite did NOT complete; M-008B and G1
are not marked passed. This result is separate from all historical M-007A and
authentication/throttling evidence. No full traceback, active node/phase or
server wait observation was supplied; no exact interrupted SQL is claimed.

Read AGENTS, TEAM_SERVICES, TEST_DATABASE and the relevant progress/source-of-truth
contracts. Inspected actual service tests/fixtures, shared concurrency fixtures,
runner, RaceDatabase, guarded connection setup, deferred constraints, TeamService
and installed psycopg interruption handling. R1 changes documentation only;
the uncommitted M-008B source/test changes are preserved, with no harness or
transaction/constraint correction made.

Credential-free collection confirmed source-order execution with three repetitions:
1-3: test_create_team_with_exact_founder_membership[0..2].
4-6: test_creation_failure_after_team_insert_rolls_back[0..2].
7-9: test_failed_creation_at_deferred_commit_rolls_back[0..2].
Therefore the next nominal node after eight successful calls is
test_failed_creation_at_deferred_commit_rolls_back[2]. Quiet output alone cannot
exclude interruption during case 8 teardown or case 9 fixture setup. The first
service race is case 28; no Barrier/Event/worker synchronization occurs in case 9.

That test seeds a fresh UUID hackathon and 16 users, then injects SELECT 1 in place
of founder membership INSERT on the service Engine. The service locks hackathon
SHARE then actor NO KEY UPDATE and inserts its own new team. Deferred leader-FK
or live-nonempty validation must reject COMMIT, mapping to integrity_fault.
The listener is removed in finally, and fresh observers require zero committed
team/membership rows. The preceding founder test deliberately injects an invalid
integer cast and requires database_failure, rollback counts and a subsequent
successful creation. Those printed categories are intended and asserted; they
are not an independent exact-SQLSTATE transcript. Ordinary lock/statement timeout
categories cannot substitute for the intended rejection without failing assertions.

Each db/repetition fixture uses a new RaceDatabase and fresh UUID-scoped rows.
Service Engine identity queries are rolled back before the mutation; its held
anchor connection has no deliberate domain locks. Service listeners are removed,
connections close/roll back and the test Engine is disposed on exit. Retained
committed rows do not retain transaction locks and have no shared hardcoded keys
that would normally collide with this case. Storage growth can affect latency;
another live connection or external DDL/maintenance could still block shared
relations. No database inspection was performed to rule those out.

Shared synchronization audit: service/schema barriers have an 8s default,
Event waits use 8s, PID queue reads use timeout=8, server-blocking observation has
a 3s polling deadline, and daemon workers share a 30s join deadline. Broken
barriers, infrastructure errors, missing results and overdue workers fail; they
are not accepted as business outcomes. Guarded SQL connections configure 5s
connect, 5s server lock and 15s server statement timeouts; TeamService retains
its transaction-local 5s/15s values. These are not one whole-case wall-clock limit.
Installed psycopg commit/rollback call wait() without its optional client timeout;
transport/server stalls, driver mutex waits and cleanup are not all bounded by
server SQL timeouts. Worker deadlines also do not hard-stop fixture setup/teardown
or an independent driver wait. No absolute whole-run bound is claimed.

Installed psycopg wait() catches KeyboardInterrupt/SystemExit, attempts cancellation
for an active query and re-raises. The output establishes an interrupt/cancellation,
not the reason it was issued or a server-confirmed lock/deadlock. The total 13.17s
is shorter than the configured 15s statement timeout, so no timeout violation or
indefinite hang follows from the supplied timing. Probable location is ordinary
database work around the third deferred-rollback case; exact setup/call/teardown,
commit/rollback/connection phase remains unknown.

Offline commands actually executed from backend:
- `.\.venv\Scripts\python.exe -m pytest service_tests --collect-only -q`:
  **57 collected in 0.02s**, exit 0; confirms the order above, no fixtures run.
- `.\.venv\Scripts\python.exe -m pytest -q tests/test_team_services.py tests/test_concurrency_harness.py tests/test_test_database_safety.py tests/test_test_database_diagnostics.py --tb=short`:
  **89 passed in 0.74s**, exit 0; no live database execution.
- Inline Python via `.\.venv\Scripts\python.exe -`: offline doubles verified
  unsignalled Event and overdue-worker failure branches, including the configured
  timeout and remaining shared deadline; PASS, exit 0. No actual wait/thread/DB.
- `.\.venv\Scripts\python.exe -m pytest service_tests --collect-only -q --race-repetitions=1`:
  **19 collected in 0.02s**, exit 0, no fixtures run.
- Root protected diff against HEAD for shared test_support, concurrency_tests,
  service fixture, migrations/models, error mapper, DB/core and dependencies:
  exit 0. No source/harness edits made by R1.

No TeamService/guard/constraint correction is justified by this evidence. A small
future harness improvement could expose an allowlisted service-case selector and
fixed node/phase/duration messages, retaining private settings, all target guards,
fail-fast behavior and suppression of raw SQL/parameters/exceptions/locals. The
current runner has no case selector and strips PYTEST_ADDOPTS, so do not use an
unsupported -k/-v argument or direct live pytest to bypass it. No diagnostic
selector/progress plugin or deadline extension was implemented in R1.

Smallest existing guarded owner diagnostic is one repetition (19 executions),
not the full 57-case verification. Proposed next command, NOT executed by Codex;
run privately in an owner PowerShell terminal without transcripts:

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite services --revision 0003_auth --repetitions 1
if ($LASTEXITCODE -ne 0) { throw 'Reduced diagnostic failed or was interrupted. Stop; do not rerun blindly.' }
```

The guarded runner uses the owner's private credential mechanism. No credentials
or credential presence were accessed by Codex for R1. No database access, live
rerun, migration/schema/role/permission change, reset/drop/cleanup, commit or push.
HEAD remains 35b14080be905f8a7d3e0921724cf4d07fd779c4; the original five M-008B
files remain modified and unstaged. Full M-008B verification remains pending even
if a reduced diagnostic later succeeds.

Owner debugging exercise: distinguish a test call PASS from fixture teardown
completion, then locate the deliberately omitted founder INSERT and explain why
its COMMIT should fail. If another interruption occurs, retain the sanitized last
node/phase and elapsed duration; do not share credentials, raw SQL or locals.

## M-008B final review and local checkpoint — 2026-11-10

Owner-verified live evidence supplied for this checkpoint:
- Guarded merge_test verification passed; Alembic **0003_auth (head)**.
- Full service suite: **57 passed in 40.99s**, three repetitions requested.
- Fresh committed-state invariants verified.
- Reduced diagnostic previously passed **19 in 13.19s**.

These are owner-run results, not a Codex PostgreSQL rerun. No separate per-case
transcript was supplied. The earlier KeyboardInterrupt after 8 passes in 13.17s
remains inconclusive, but the full suite subsequently completed successfully.
This completed run supersedes the historical pending-live status for M-008B;
it does not establish the earlier interrupt's cause or close G1.

Reviewed the exact five changed files against baseline
35b14080be905f8a7d3e0921724cf4d07fd779c4: backend/app/services/teams.py,
backend/tests/test_team_services.py, backend/service_tests/test_teams.py,
docs/TEAM_SERVICES.md and this log. Read AGENTS, the required service/test-database/
progress contracts and relevant requirements, architecture, decisions and schema
sections. No correctness/security blocker found within this bounded component.
Final review required documentation updates only; no implementation fix or test
change was made after the owner-verified full run.

Confirmed _execute remains the sole connection/begin/commit/unwind owner, unchanged
against baseline. Its actual DBAPI AUTOCOMMIT guard, READ COMMITTED check, no-caller-
transaction rule and 5s/15s local timeouts are unchanged. Public create_team and
join_team signatures, input validation/UUID timing and frozen TeamResult match
baseline. The moved operation bodies and all existing SQL helpers are AST-identical.
The private methods use the supplied connection without lifecycle calls. Hackathon
SHARE -> user NO KEY UPDATE -> existing team NO KEY UPDATE, fresh post-lock counts,
founder leadership, deleted-team rejection and complete deferred-COMMIT rollback
remain intact. Runtime DML targets only teams/memberships; no idempotency, audit,
outbox, team-version update or retry framework was introduced. All original unit/
live test functions and decorators remain unchanged; added cases strengthen owner
connection/transaction/commit observation and rollback coverage.

Final commands actually run by Codex, Windows PowerShell, existing Python 3.11.9 /
SQLAlchemy 2.1.8 / psycopg 3.3.8 venv, from backend:
- `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short`:
  **554 passed, 32 deselected, one existing Starlette/HTTPX warning in 23.07s**,
  exit 0. Includes the 55 focused TeamService cases and auth/throttle regressions.
  The separate earlier 55-pass focused command was not rerun at this checkpoint.
- `.\.venv\Scripts\python.exe -m pip check`:
  **No broken requirements found**, exit 0. No install/update.
- `.\.venv\Scripts\python.exe -m pytest service_tests --collect-only -q`:
  **57 collected in 0.06s**, exit 0; fixtures not executed.

Root inline Python via `.\backend\.venv\Scripts\python.exe -` passed baseline
AST comparisons for owner/guard/helpers, public signatures/validation/UUID timing,
TeamResult, moved SQL bodies and original test functions. It checked the exact
five-file allowlist, three Python ASTs, private lifecycle-call exclusion, runtime
write targets, secret-pattern/source-path/whitespace safety and six ignore paths;
no actionable secret/generated/unrelated-file findings. This supplements manual
review, not a proof against every possible secret. No private environment file
was opened. `git -c safe.directory=I:/Merge diff --check` passed, with existing
LF/CRLF conversion warnings. Staged content is compared to these reviewed working
contents, scanned and checked before the authorized commit. No configured Python
linter; no lint pass claimed. Frontend/build/browser checks not rerun.

Protected-baseline diff exited 0 using the exact command in the implementation
preparation entry above. Migrations 0001/0002/0003, domain/auth models and schema,
error mapping, authentication/session/throttle code, database settings, guarded
test infrastructure, dependencies/locks, frontend, provisioning/privilege scripts
and .gitignore remain unchanged. No database connection, external privilege query,
merge_dev access, test reset/drop/cleanup, migration, role/permission or credential
change was performed by Codex. Actual external ACL state was not queried.

Owner authorized exactly one local commit after successful review:
`refactor: extract transaction-local team mutations (M-008B)`.
The resulting full hash and clean Git status are read and reported after commit;
the commit cannot embed its own hash. No remote creation or push.

Remaining limitations: internal trusted-actor services only; no public team HTTP
mutations or leader authorization, idempotency/replay, audit/outbox or retries.
No M-008C work, authenticated 50-way API/CI race, load/deployment acceptance or G1
closure. Existing ambiguous COMMIT, raw-writer deadlocks, mutation-time counts,
server/transport timeout boundaries and production HTTPS/browser limitations
remain. Successful local schedules do not establish all possible interleavings.

Owner explanation/exercise: each private method returns inside the owner's
transaction, while the public result escapes only after COMMIT. Trace a deferred
COMMIT failure and explain why it still removes the already-inserted membership;
adding a second begin() to the extracted method must fail the ownership tests.

### 2026-11-10 — M-008C private idempotency primitives (owner review; live pending)

Historical implementation entry: its pending-live status is superseded by the
M-008C final checkpoint below; the commands/results remain as originally observed.

Baseline: main `35ddacecfd803c7fd1b1d1ed2a188873ba62f488`, initially clean.
The owner's M-008B 57 live passes / 554 offline passes are prior evidence only.
M-008C is implemented and offline tested, not yet PostgreSQL verified or committed.
G1 and requirement R-08 remain open.

New private command/fingerprint/reservation/stored-reply types and transaction-local
helpers implement the approved success-only policy. Keys exactly match the existing
1–128 printable-ASCII contract, including significant spaces/case. Versioned
canonical meaningful-command JSON is SHA-256 hashed; create outcome UUIDs are
excluded. Reservation uses the exact named ON CONFLICT constraint and a separate
fresh READ COMMITTED SELECT for replay. Scope, hash, hackathon, completed state and
bounded versioned successful response/header values are checked. Mismatch returns
only `idempotency_mismatch`; missing/pending/corrupt outcomes are integrity faults.
Completion is bound to the original connection and root transaction and updates
only its matching pending row. Every helper rejects actual DBAPI AUTOCOMMIT.
No helper owns a connection, transaction or commit.

Exact changed files (15):
- `backend/app/services/idempotency.py`, `backend/app/services/errors.py`.
- `backend/tests/test_idempotency.py`, `backend/tests/test_concurrency_harness.py`,
  `backend/tests/test_auth_schema_support.py`.
- `backend/test_support/concurrency.py`, `backend/idempotency_tests/conftest.py`,
  `backend/idempotency_tests/test_idempotency.py`.
- `docs/IDEMPOTENCY.md`, `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, `docs/SCHEMA.md`,
  `docs/TEAM_SERVICES.md`, `docs/TEST_DATABASE.md`, this `docs/PROGRESS.md`.

Why: retain the existing unique/immutable/deferred constraints and transaction
owner instead of adding a lease or second commit owner. A same-statement CTE
cannot guarantee a fresh snapshot after waiting for an invisible winning INSERT.
Private replies are bounded JSON with schema_version 1, data object and exact
optional `content-type: application/json` and `cache-control: no-store` headers. No
cookies or arbitrary headers are replayed. Floats are excluded to avoid JSONB
exponent expansion producing an out-of-bounds integer on replay. These private
response limits do not introduce a public HTTP contract; see IDEMPOTENCY.md.

Actual Codex commands, existing Windows PowerShell backend venv, Python 3.11.9 /
SQLAlchemy 2.1.8 / psycopg 3.3.8, from `backend` unless stated:
- `.\.venv\Scripts\python.exe -m pytest tests/test_idempotency.py tests/test_concurrency_harness.py tests/test_auth_schema_support.py -q --tb=short`:
  **109 passed in 1.72s**, exit 0, before the additional float-rejection case.
- `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short`:
  **626 passed, 32 deselected, one existing Starlette/HTTPX warning in 8.30s**,
  exit 0. Includes all 554 previous offline cases, 70 new primitive cases and two
  added guarded-runner parameter cases; team/auth/throttle regressions pass.
- `.\.venv\Scripts\python.exe -m pytest tests/test_idempotency.py -q --tb=short`:
  final focused **70 passed in 0.46s**, exit 0, after adding a constant-time
  two-field envelope-length check before constructing its key set. This is the
  only runtime refinement after the full 626-pass run; no valid reply changes.
- `.\.venv\Scripts\python.exe -m pip check`:
  **No broken requirements found**, exit 0. No install/update.
- `.\.venv\Scripts\python.exe -m pytest idempotency_tests --collect-only -q`:
  **60 collected in 0.17s**, exit 0 (20 scenarios, default three repetitions).
- `.\.venv\Scripts\python.exe -m pytest service_tests --collect-only -q`:
  **57 collected in 0.05s**, exit 0. Neither collection executes fixtures.

An initial focused invocation from the repository root failed collection with
two `test_support` import errors; rerunning from the documented backend directory
passed. No database was opened. The inline static review initially assumed AST
walk order was source order; sorting query nodes by source line corrected that
review-script assertion, with no application change needed for it.

Root `.\backend\.venv\Scripts\python.exe -` inline static review passed:
exact file allowlist, eight Python ASTs, byte-equivalent unchanged TeamService,
AST-equivalent database error mapper, unchanged protected paths, no private-helper
lifecycle ownership, exactly three parameterized SQL statements with only
idempotency INSERT/UPDATE targets and a separate conflict SELECT. Changed-file
secret/artifact pattern and path scans, new-file whitespace and
`git -c safe.directory=I:/Merge diff --check` passed (existing LF/CRLF conversion
warnings). No actionable secret/generated/unrelated-file findings; pattern scans
are not an exhaustive secret proof. No Python linter is configured or claimed.

The dedicated guarded runner requires explicit `--suite idempotency --revision
0003_auth`, fixed merge_test identity and revision checks before all live writes.
New UUID fixtures are retained. Fresh independent connections check completed
state, reply shape, existing team invariants and zero teams/memberships/audit/outbox
rows in each fixture hackathon. A test-only user display-name update proves one
effect and rollback without implementing team composition. Concurrency requires
different backend PIDs and observed server blocking; unexpected errors/timeouts
cannot pass. Event/queue/observation/join and server SQL waits remain bounded.
The pending case uses own-transaction visibility plus exact deferred constraint
`23514 / ct_idempotency_completed`; committed pending cannot be manufactured
without weakening the unchanged database guard. Offline injection also tests
the loaded pending branch. No constraints are bypassed.

Pending live evidence: **none of the 60 new cases was executed against PostgreSQL
by Codex**. No private test credential was supplied in the environment; no prompt,
private environment file, database connection or migration was used. Exact
two-step owner verification/suite commands with 0003_auth and three repetitions
are in IDEMPOTENCY.md. Report actual counts/timing and fresh invariant outcomes
after that run; do not reuse M-008B's live result for this milestone.

Protected baseline remains unchanged: TeamService public create/join/TeamResult,
_execute ownership, READ COMMITTED/DBAPI guard, lock order, fresh counts, timeouts
and rollback handling; all migrations, models/schema, database settings/guards,
dependencies/locks, authentication/session/throttle code, existing live team tests,
frontend and provisioning/privilege scripts. Only the stable mismatch enum extends
errors; existing database mappings are unchanged. No role/permission or external
ACL change/query, merge_dev access, reset/drop/cleanup, audit/outbox/membership
implementation, public idempotent mutation/HTTP route, retry framework, commit,
remote creation or push. Historical architecture sketches are not deployed proof.

Remaining work: owner PostgreSQL verification and review before any checkpoint;
future approved authenticated mutation composition with audit/outbox, invitation/
request authorization, public API/error policy and ambiguous-COMMIT reconciliation.
One reservation per future mutation must precede hackathon -> user -> team locks;
inverse/multiple-key ordering can deadlock. No expiry/lease/takeover/cleanup,
50-way authenticated API/CI race, load or production HTTPS/browser proof is added.

Owner explanation/exercise: the unique INSERT waits for its competing transaction,
then the SELECT sees the committed immutable result. Change only a generated
create UUID in the canonical-hash test and explain why the hash stays identical;
trace failure after completion to show both effect and reservation roll back.

### 2026-11-10 — M-008C-R1 first live failure: test-only SQL bind repair

Historical R1 entry: the successful full 60-case owner run in the final checkpoint
below supersedes its pending-live status and earlier failed run.

Owner-reported live evidence: guarded merge_test verification passed at
**0003_auth (head)**. The `idempotency` suite with three repetitions requested
stopped at `test_first_completion_and_matching_replay_has_one_effect[0]`:
**1 failed in 0.67s**. SQLAlchemy raised StatementError wrapping InvalidRequestError,
`A value is required for bind parameter 'effect'`. Fresh committed-state invariants
were reported verified. No successful full M-008C live verification exists.
This is owner execution evidence, not a Codex PostgreSQL run.

Exact root cause: `backend/idempotency_tests/test_idempotency.py:33`, test-only
`effect()`. The SQL literal `display_name || ':effect'` passes through
`test_support.races.sql()` to `connection.execute(text(statement), values)`.
SQLAlchemy's text parser recognizes `:effect` even inside SQL quotes, but values
contained only `u`. The UPDATE therefore failed bind construction before reaching
PostgreSQL. This defect is in test-only SQL, not fixture instrumentation or runtime
reservation/replay/completion. Earlier offline mocks did not compile this helper.

Minimal repair: use `display_name || :effect` and explicitly pass
`effect=':effect', u=cmd.actor_id`. This appends exactly the intended literal suffix
and leaves the original `(1, 'race-test:effect')` assertion, replay/rollback checks,
uniqueness/fingerprint checks and every live test scenario intact. The existing
offline `tests/test_idempotency.py` now imports and exercises the actual live
helper through a compile-only connection using the PostgreSQL dialect and real
SQLAlchemy `construct_params()`. It asserts the supplied suffix and actor bind,
without mocking text parsing, opening an Engine or executing database SQL.

R1 changed only four already-pending files: the live helper, its offline test,
this progress log and TEST_DATABASE.md's current verification-status sentence.
No runtime file changed in R1. A pre-repair hash snapshot verified every Python
file under app/, the fixture, runner, database helper and races helper unchanged;
reversing the exact helper-call replacement reproduced the original live-file
hash, proving all other live assertions/schedules remained byte-unchanged.
The temporary review snapshot was removed. No dependency, schema, migration,
permission, TeamService or transaction-guard change.

Commands actually run by Codex from backend, existing Python 3.11.9 venv:
- `.\.venv\Scripts\python.exe -m pytest tests/test_idempotency.py::test_live_effect_helper_supplies_binds_and_preserves_literal_suffix -q --tb=short`:
  before repair, **1 failed in 1.03s**, reproducing the exact missing `effect`
  InvalidRequestError without a database connection.
- `.\.venv\Scripts\python.exe -m pytest tests/test_idempotency.py -q --tb=short`:
  after repair, **71 passed in 1.41s**, exit 0.
- `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short`:
  **627 passed, 32 deselected, one existing Starlette/HTTPX warning in 13.98s**,
  exit 0. All 626 previous cases remain, plus the new regression.
- `.\.venv\Scripts\python.exe -m pytest idempotency_tests --collect-only -q`:
  **60 collected in 0.07s**, exit 0; no fixture execution.
- `.\.venv\Scripts\python.exe -m pip check`:
  **No broken requirements found**, exit 0; no dependency install/update.

Database-free inline Python via `.\.venv\Scripts\python.exe -` compiled 35 related
literal sql/_query call sites in the live suite, fixtures, runtime primitives and
races helper, checking required bind names against supplied parameters (including
the explicit _scope expansion). A wider application/test/support scan examined
277 SQL-like source literals for the same quoted-colon bind trap: no remaining
findings. This is source/compilation evidence, not SQL execution or a claim to
cover every dynamic statement. Git whitespace checks passed; existing LF/CRLF
conversion warnings remain. No database or credentials were accessed by Codex.

Owner next step, PowerShell without a transcript; credentials stay in hidden
prompts, and a verification failure stops before the suite:

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Database verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite idempotency --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'M-008C-R1 verification failed. Stop.' }
```

Live rerun remains pending; Codex only collected the 60 cases. Retained fixtures,
fresh committed-state checks and all guards remain in place. No merge_dev access,
database reset/cleanup, schema/role/permission changes, commit or push. HEAD stays
`35ddacecfd803c7fd1b1d1ed2a188873ba62f488`; all M-008C changes remain uncommitted
for owner review. G1 and R-08 remain open.

Owner explanation/exercise: SQLAlchemy parses binds before PostgreSQL sees SQL;
quotes in text() do not protect a colon-prefixed word. Run the new focused test,
then explain why binding the suffix as data preserves the exact effect while
removing the accidental missing parameter. It does not demonstrate live replay
or concurrency correctness; the guarded PostgreSQL rerun still must do that.

### 2026-11-10 — M-008C final review and authorized local checkpoint

Owner-verified live result: guarded **merge_test / 0003_auth**, idempotency suite
**60 passed in 40.82 seconds**, three repetitions requested. Fresh committed-state
invariants verified; UUID-scoped fixtures retained. This full successful run
supersedes the earlier first-test failure (**1 failed in 0.67s**), whose test-only
SQL bind defect and R1 repair remain documented above. No separate per-case raw
transcript was supplied. This records owner execution, not a Codex PostgreSQL
rerun. M-008B's 57 live service cases are distinct prior evidence. G1 and R-08
remain open because authenticated public mutation composition is not implemented.

Reviewed all 15 pending files against main baseline
`35ddacecfd803c7fd1b1d1ed2a188873ba62f488`; the exact inventory is in the original
M-008C entry above and the commit. No correctness/security/transaction blocker
was found. This checkpoint changes only evidence/status documentation; runtime
and tests remain the owner-verified R1 contents.

Confirmed policy: one operation, success-only retention, scope actor/operation/key,
exact 1–128 printable-ASCII keys with significant spaces/case, and canonical
versioned SHA-256 meaningful-input fingerprints excluding generated create IDs.
The INSERT uses ON CONFLICT ON CONSTRAINT uq_idempotency_scope DO NOTHING
RETURNING id. Conflict lookup is a separate READ COMMITTED SELECT; a same-statement
snapshot is not substituted. Stored scope/hash/hackathon/state are checked before
replay; mismatch is a fixed non-retryable idempotency_mismatch, pending/missing/
corrupt outcomes fail closed. Immutable retained completed rows need no replay
UPDATE. Completion checks the original connection and root transaction and updates
only the matching pending reservation. No helper connection or commit ownership.

Reply validation requires successful 2xx, exact schema_version 1/data envelope,
16,384-byte UTF-8 JSON, bounded depth/nodes/containers/strings, signed 64-bit
integers and no floats/NUL/invalid UTF-8. The only optional headers are exact
`content-type: application/json` and `cache-control: no-store` pairs; cookies,
authorization and arbitrary values are excluded. Values are frozen and sensitive
repr fields are suppressed. The R1 helper explicitly binds the literal ':effect';
its original one-effect assertion and real SQLAlchemy compilation regression are
intact. No unexpected database_failure/timeout outcome is accepted as a pass in
the new live schedules; they require the exact replay/winner/rollback outcomes,
server blocking and the named deferred pending constraint.

Actual checkpoint commands, Windows PowerShell, existing backend Python 3.11.9 /
SQLAlchemy 2.1.8 / psycopg 3.3.8 venv, from backend:
- `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short`:
  **627 passed, 32 deselected, one existing Starlette/HTTPX warning in 14.19s**,
  exit 0. Includes team, authentication/session/throttle and all primitive cases.
- `.\.venv\Scripts\python.exe -m pytest tests/test_idempotency.py -q --tb=short`:
  **71 passed in 1.08s**, exit 0, including the R1 bind regression.
- `.\.venv\Scripts\python.exe -m pip check`:
  **No broken requirements found**, exit 0; no install/update.
- `.\.venv\Scripts\python.exe -m pytest idempotency_tests --collect-only -q`:
  **60 collected in 0.05s**, exit 0; no fixtures executed.

Root `.\backend\.venv\Scripts\python.exe -` inline review passed exact 15-file
scope, eight Python ASTs, byte-equivalent TeamService and AST-equivalent existing
database error mapper, protected-baseline comparison, no private-helper lifecycle
calls, exactly three literal parameterized runtime SQL statements and only
idempotency INSERT/UPDATE targets with a separate conflict SELECT. Backend inline
Python compiled 35 related SQL call sites and checked required bind dictionaries,
including R1 and the explicit _scope expansion; no quoted accidental binds were
found. Runtime source inspection found no route or facade importing the primitives.
The helpers do not implement team/audit/outbox composition or bypass a future owner.

Changed-file secret/artifact path and content scans, new-file whitespace and
`git -c safe.directory=I:/Merge diff --check` passed, with existing LF/CRLF
conversion warnings. No actionable private credential, generated artifact or
unrelated-file findings; pattern scanning is not an exhaustive secret proof.
No private environment file was opened. No configured Python linter, frontend
build or browser/production HTTPS test was run or claimed.

Protected baseline is unchanged: TeamService/create/join/TeamResult/_execute and
their READ COMMITTED/actual DBAPI AUTOCOMMIT guard, lock order, fresh counts,
timeouts and rollback handling; migrations 0001/0002/0003, models/schema, database
settings/guard helpers, existing live team tests, authentication/session/throttle
runtime, dependencies/locks, frontend and provisioning/privilege scripts. Only
the fixed mismatch enum extends service errors; existing mappings are unchanged.
No database connection or external ACL query/change, merge_dev access, reset,
cleanup, migration, role/permission or credential change was performed by Codex.

Owner authorized exactly one local commit after successful review:
`feat: add transactional idempotency primitives (M-008C)`.
Checkpoint procedure stages exactly the reviewed 15-file allowlist and compares
the staged blobs to reviewed working contents before committing. The resulting
full hash and final Git status are read and reported afterward; this commit cannot
embed its own hash. No remote creation or push is authorized or performed.

Limitations: private primitives and test-only effect composition, no new public
idempotent facade or team HTTP mutation endpoints, no audit/outbox/invitation or
request authorization composition, retry framework, ambiguous-COMMIT reconciliation,
expiry/lease/takeover/cleanup, M-008D/E implementation or G1 closure. Future approved
composition must reserve before hackathon -> user -> team locks and expose replies
only after the existing owner's COMMIT succeeds. Raw writers/inverse/multiple-key
lock order can still deadlock; tested local schedules do not prove every possible
interleaving. Authenticated 50-way API/CI, load and deployed HTTPS/browser proof
remain outstanding.

Owner explanation/exercise: the losing INSERT waits, then a separate SELECT sees
the committed immutable reply. Explain why a generated create UUID must not enter
the command hash; trace an exception after completion through the owner's rollback
to show that neither the reservation nor the simulated effect survives.

### 2026-11-10 — M-008D atomic composed mutations (owner review; live pending)

Historical implementation entry: its pending-live/no-commit status is superseded
by the owner-verified final checkpoint below. Original commands/results are retained.

Baseline: main `d8cf343a50cfaec4e83c47d318bfac79d10072ea`, initially clean.
M-008B's 57 owner-verified service cases and M-008C's 60 primitive cases remain
historical evidence, not a live pass for this composition. G1, R-08 and R-12
remain open. Implemented/offline-tested only; no commit is authorized in this task.

New TeamService.create_team_idempotent()/join_team_idempotent() validate trusted
UUID/meaningful inputs/key and construct the unchanged canonical V1 fingerprint
before connecting. A frozen _CreateTeamRequest contains no outcome UUID, allowing
replay without allocating a new team ID. Local imports avoid the existing command/
fingerprint module cycle. The compatibility create_team()/join_team(), private
mutation commands/TeamResult and every original TeamService method are AST-identical
to baseline. Only the new composed methods may back a future authenticated and
authorized public mutation boundary; no HTTP team routes are implemented.

Graph: new entry point -> private facade/validated input/hash -> unchanged _execute
connection/guard/begin/timeouts -> reservation -> either stored reply or existing
transaction-local mutation -> version -> audit -> outbox -> reply completion ->
one COMMIT -> return. Reservation precedes hackathon SHARE -> user NO KEY UPDATE
-> existing team NO KEY UPDATE and fresh post-lock counts. No helper owns a
connection, transaction, savepoint, commit, retry or external publication.
Create requires version 1; join increments once under its retained parent lock
and stamps updated_at with database clock_timestamp(). Bigint version exhaustion
fails closed and rolls back admission. Legacy methods deliberately retain their
internal compatibility semantics without version/audit/outbox composition.

One audit row links the reservation, trusted actor, hackathon, team, team_version
and operation action. Its bounded before/after summary includes count/version,
leader, frozen sizes/readiness and affected subject membership. Create before is
SQL NULL; join before count/version are result minus one because this path adds
exactly one member and retains the parent lock, with unchanged leader/sizes.
One corresponding outbox row uses team.changed.v1/schema_version 1, only
hackathon/team IDs and team_version, published_at SQL NULL, attempt_count zero.
No key/hash, credential, cookie, CSRF/session, profile or audit snapshot goes into
the event. Create response status 201, join 200; existing bounded versioned reply
contains result IDs/count/version and exact safe content-type/cache-control.
Replay preserves the original response after later state changes and adds no
mutation, version, audit, outbox or outcome UUID. Payloads/limits are in
TEAM_MUTATIONS.md. No schema changes are needed for the actual named constraints.

Changed-file inventory (17):
- `backend/app/services/teams.py`, `backend/app/services/idempotency.py`,
  new `backend/app/services/team_mutations.py`.
- new `backend/tests/test_team_mutations.py`, existing
  `backend/tests/test_concurrency_harness.py`, `backend/tests/test_auth_schema_support.py`.
- `backend/test_support/concurrency.py`, new
  `backend/team_mutation_tests/conftest.py`, `backend/team_mutation_tests/test_composition.py`.
- new `docs/TEAM_MUTATIONS.md`, existing `docs/TEAM_SERVICES.md`, `docs/IDEMPOTENCY.md`,
  `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, `docs/SCHEMA.md`, `docs/TEST_DATABASE.md`,
  this `docs/PROGRESS.md`.

Actual Codex evidence, Windows PowerShell, existing backend Python 3.11.9 /
SQLAlchemy 2.1.8 / psycopg 3.3.8 venv, from backend unless stated:
- `.\.venv\Scripts\python.exe -m pytest tests/test_team_mutations.py tests/test_team_services.py tests/test_idempotency.py -q --tb=short`:
  **154 passed in 1.83s**, exit 0. Covers 28 new orchestration cases plus the
  unchanged 55 team/71 primitive offline cases.
- `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short`:
  **657 passed, 32 deselected, one existing Starlette/HTTPX warning in 17.89s**,
  exit 0. Includes all prior 627 cases and two extra runner parameter cases.
- `.\.venv\Scripts\python.exe -m pip check`:
  **No broken requirements found**, exit 0; no install/update.
- `.\.venv\Scripts\python.exe -m pytest team_mutation_tests --collect-only -q`:
  initial **81 collected in 0.15s**; final collection after strengthening fresh
  audit-state assertions **81 in 0.03s**, exit 0 (output summarized with
  `| Select-Object -Last 2`). These are 27 scenarios at default three repetitions.
- `.\.venv\Scripts\python.exe -m pytest service_tests --collect-only -q`:
  **57 collected in 0.07s**, exit 0.
- `.\.venv\Scripts\python.exe -m pytest idempotency_tests --collect-only -q`:
  **60 collected in 0.08s**, exit 0. No collection executed database fixtures.

Root inline Python via `.\backend\.venv\Scripts\python.exe -` passed source AST
comparisons for all original TeamService methods/commands/TeamResult, every
unchanged primitive helper, and normalized factory comparison proving only the
new create input shape is accepted (canonical bytes/rules unchanged). It checked
the exact component file allowlist, nine Python ASTs, no composition lifecycle/
retry calls, four literal composition SQL statements and their expected team
version/audit/outbox write targets. Protected baseline comparison passed for all
migrations/models/db configuration, error mapping, auth/session/throttle runtime,
existing 57/60 live suite sources, existing team/primitive offline tests,
dependencies/locks, frontend and provisioning/privilege scripts. Backend inline
Python compiled 28 literal service/live SQL call sites, checked required binds
against supplied parameters and rejected quoted accidental binds. Source inspection
confirmed no route or non-service facade imports the new methods.

Changed-file secret/artifact path/content and whitespace scans passed with no
actionable findings; these are supplementary pattern checks, not an exhaustive
secret proof. `git -c safe.directory=I:/Merge diff --check` passed, with existing
LF/CRLF conversion warnings. No configured Python linter or frontend/browser
build/test result is claimed. No private environment file was opened. No credential
was supplied in the test environment; Codex did not prompt, connect to PostgreSQL,
access merge_dev, migrate/reset/drop/clean up data, or alter roles/permissions.

New guarded runner `--suite mutations --revision 0003_auth` verifies revision before
requesting credentials; all independent fixture/service/worker/observer connections
check fixed merge_test identity/revision/READ COMMITTED before writes. Retained
UUID fixtures receive fresh independent original team-invariant and record-chain
checks: exactly one audit/outbox per completed success, scope/subject/snapshots,
safe unpublished payloads, contiguous versions and current counts. Fault injection
after actual reservation/founder/member/version/audit/outbox/completion SQL must
raise the exact injected signal and leave all five affected tables unchanged.
Deferred COMMIT failure requires exact 23503/fk_teams_leader_member and full chain
rollback with no returned result. Concurrent duplicates require observed server
blocking, original equal responses and one chain; held-before-commit snapshots
prove outbox/other effects invisible and no reply returned. Different-key capacity/
same-user races require exact team_full/already_assigned rejection, not a timeout
or generic database error. Real DBAPI AUTOCOMMIT, ownership and lock order cases
are included. Waits remain bounded (8s sync, 3s observation, 30s join, 5s connect/
lock, 15s SQL). No production retry framework is introduced by explicit test reruns.

Pending: **all 81 new live executions and the 57/60 post-M-008D regression executions
have only been collected, not executed by Codex**. Exact owner PowerShell verify,
mutations, services and idempotency commands with revision 0003_auth, three
repetitions, hidden credentials and stop-on-failure checks are in TEAM_MUTATIONS.md.
No live success/timing is inferred from previous milestones.

Limitations: trusted actor syntax/existence is not authentication/authorization;
eventual HTTP must derive the actor from a verified session and authorize replay
and mutation. Immediate reservation FKs use the existing integrity_fault mapping
for nonexistent actor/hackathon IDs before legacy existence lookup; public error
policy is not defined here. Legacy/raw writers are not automatically audited or
versioned and must remain excluded from public workflows. Audit is a bounded
state summary, not a roster/profile snapshot. No dispatcher, invitation/request
workflow, general retries, ambiguous-COMMIT reconciliation, expiry/lease/takeover/
cleanup, public 50-way API/CI, load, deployment or browser/HTTPS proof. M-008E and
G1 closure are not included. No staging, commit, remote creation or push.

Owner exercise: trace failure after outbox insertion through the only owner's
rollback; then explain why replay after a different user's join returns the old
count/version and why the stored response cannot escape before COMMIT.

### 2026-11-10 — M-008D final review and authorized local checkpoint

Owner verified the explicit target: merge_test / merge_app, READ COMMITTED,
Alembic **0003_auth (head)**. The owner-run PostgreSQL results are:

| Suite | Passing executions | Reported suite duration |
|---|---:|---:|
| Composed mutations | 81 | 101.23s |
| Service regressions | 57 | 59.59s |
| Idempotency regressions | 60 | 40.81s |
| Total / sum | **198** | **201.63s** |

Three repetitions requested for each suite. Fresh composed mutation chains and
committed-state invariants verified; fixtures retained. These are owner-run
results, not Codex database executions. The owner explicitly corrected the earlier
202.63s combined figure as an arithmetic error, not an independently measured
duration; the individual timings remain exactly as reported. 201.63s is their
sum. No code or test change was required for that correction. No separate per-case
raw transcript was supplied. G1 and public R-08/R-12 acceptance remain open.

Final review against main baseline
`d8cf343a50cfaec4e83c47d318bfac79d10072ea` found no correctness/security blocker.
All 17 changed files were inspected; their exact inventory is in the implementation
entry above and the commit. This checkpoint changes only evidence/status docs;
runtime and tests remain the implementation that the owner verified.

Confirmed _execute is the sole connection/transaction owner and retains its
original guard, isolation, timeouts, rollback/error mapping and commit-before-return
behavior. Reservation precedes unchanged hackathon SHARE -> user NO KEY UPDATE
-> team NO KEY UPDATE / fresh-count logic. The composed paths invoke the original
_create_team_in_tx/_join_team_in_tx once, never their committing compatibility
facades. Create allocates its team UUID after winning the reservation and requires
initial version 1; join increments version once under its retained parent lock.
Exactly one successful audit and linked unpublished outbox are inserted and checked
with RETURNING before completing the successful idempotency outcome.

Stored status/body/headers reflect the mutation-time count/version and existing
bounded V1 reply contract. Matching replay returns before outcome UUID allocation,
domain locks, mutation/version/audit/outbox stages; no subsequent state regeneration.
Mismatch/pending/malformed outcomes fail closed. Audit records link actor, subject,
scope, operation and bounded before/after state; outbox contains only hackathon ID,
team ID and version, with published_at NULL and attempt_count zero. No event or
external notification is emitted from the transaction. Failure at any write or
deferred COMMIT unwinds the full chain; tests require the specific injected signal,
named leader-FK violation or intended race rejection, never generic database failure
or a timeout accepted as success. All original legacy method signatures/behavior
remain internal compatibility only, excluded from future public HTTP mutations.
No new HTTP actor-ID/authentication boundary or unauthenticated join was added.

Actual checkpoint commands, Windows PowerShell, existing backend Python 3.11.9 /
SQLAlchemy 2.1.8 / psycopg 3.3.8 venv, from backend:
- `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short`:
  **657 passed, 32 deselected, one existing Starlette/HTTPX warning in 12.80s**,
  exit 0. Team, auth/session/throttle and composed orchestration regressions pass.
- `.\.venv\Scripts\python.exe -m pytest tests/test_team_mutations.py tests/test_team_services.py tests/test_idempotency.py -q --tb=short`:
  **154 passed in 1.52s**, exit 0.
- `.\.venv\Scripts\python.exe -m pip check`:
  **No broken requirements found**, exit 0; no install/update.
- `.\.venv\Scripts\python.exe -m pytest team_mutation_tests --collect-only -q`:
  **81 collected in 0.05s**, exit 0.
- `.\.venv\Scripts\python.exe -m pytest service_tests --collect-only -q`:
  **57 collected in 0.03s**, exit 0.
- `.\.venv\Scripts\python.exe -m pytest idempotency_tests --collect-only -q`:
  **60 collected in 0.05s**, exit 0. Collection outputs were summarized with
  `| Select-Object -Last 2`; no fixtures executed.

Root `.\backend\.venv\Scripts\python.exe -` inline static review passed: exact
17-file scope, nine Python ASTs, all original TeamService methods/commands/
TeamResult AST-identical, unchanged primitive helpers and normalized factory
comparison proving only new create-input acceptance, not changed canonical bytes.
It verified no composition lifecycle/retry calls and four literal composition SQL
queries with only expected version/audit/outbox write targets. Backend inline
Python compiled 28 literal service/live SQL call sites with required supplied
binds, rejected accidental quoted binds, and verified no route or non-service
facade imports the new methods. Protected-baseline comparison passed for all
migrations/models/db settings, error mapper, auth/session/throttle runtime,
existing service/idempotency live sources and team/primitive offline tests,
dependencies/locks, frontend, provisioning/privilege scripts, AGENTS and gitignore.

Changed-file secret/artifact path/content scans and
`git -c safe.directory=I:/Merge diff --check` passed; existing LF/CRLF conversion
warnings remain. No actionable credential, generated artifact or unrelated-file
finding; pattern checks supplement manual review, not an exhaustive secret proof.
No private environment file was opened, and no PostgreSQL connection, credential
access, merge_dev access, merge_test reset/drop/cleanup, schema/migration or
role/permission change/query was performed by Codex. External ACL state was not
independently queried. No configured Python linter, frontend build, browser/HTTPS
or deployment check was run or claimed.

Owner authorized exactly one local commit after successful review:
`feat: compose atomic team mutations with audit and outbox (M-008D)`.
Checkpoint procedure stages exactly the 17 reviewed files, compares every staged
blob to reviewed working contents, and checks staged syntax, secret patterns and
whitespace before committing once. Full resulting hash and final Git status are
read and reported after commit; this commit cannot embed its own hash. No remote
creation or push is authorized or performed.

Remaining limitations: trusted internal actor input, future HTTP session-derived
identity/current authorization/error policy, legacy/raw writers excluded from
public audited workflows, audit summaries rather than rosters, unpublished outbox
without dispatcher, no invitation/request workflow, no M-008E bounded retries or
ambiguous-COMMIT reconciliation, no lease/expiry/takeover/cleanup. Existing
reservation-FK missing-identity errors retain the documented integrity_fault
mapping. Tested local schedules do not prove all interleavings, authenticated
50-way API/CI, load, browser/HTTPS or production readiness. G1 remains open.

Owner explanation/exercise: trace an exception after outbox insertion through
the only owner's rollback, including a locally completed reply; then explain why
replay after another member joins returns the original count/version without
publishing or adding a second audit/outbox pair.

## Daily work log template
```
### YYYY-MM-DD — [component/task ID]
Goal:
Implementation / files:
Tests and actual commands:
Measured results:
Known limitations:
Owner explanation / live-change exercise:
Commit hash (only if committed):
Next:
```

## Milestone closure protocol
A gate closes only when links/commands to objective evidence exist in this file. No assumptions based on Codex summaries alone. Review Git diff and actual logs. Record only real benchmark results, not targets.

Official statement: https://hack4hack.com/hackathons/hack4hack-crew-hiring-challenge-2026-tp3m

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
- [x] Automated tests passed — M-007B.2B checkpoint: owner verified 63 guarded live session cases in 51.63s, three repetitions requested, fresh committed-state invariants verified and fixtures retained. Codex verified 222 database-free tests in 7.49s. Earlier M-007B.2A owner evidence: 51 live credential cases in 28.76s. Domain/frontend evidence remains recorded below. This is not a claim of 20 API tests or a verified 50-way HTTP race.
- [ ] Any public deployment exists — **not verified**.
- [ ] PS1 submission completed — **not verified**.

## Milestones / exit criteria

| Gate | Scope | Required objective evidence | Status |
|---|---|---|---|
| G0 | Repository and local integration | Commit hash, README, backend health, React build, PostgreSQL connectivity, migration, smoke test | DONE — local checks recorded in M-003; initial commit `66d28b51728f466b3d0124de03f457dd190c22f1`; closed 2026-11-07 |
| G1 | Transactional team core | Real PostgreSQL 50-way last-seat race, cross-team race, idempotency; repeatable tests | PARTIAL — schema/guards verified in M-006A; services and multi-connection/API races pending |
| G2 | Business flows and security | Team lifecycle, invites, requests, leader succession, audit, authorization negative tests | NOT STARTED |
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

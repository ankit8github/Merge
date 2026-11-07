# Merge — Verified Progress, Risks & Next Actions

**Last updated:** 2026-11-06
**Competition:** Hack4Hack Crew Hiring Challenge 2026, PS1.
**Official deadline:** 2026-11-15 23:59 IST.
**Status policy:** Mark DONE only with recorded evidence. 'Planned', 'in progress', 'implemented', 'tested' and 'verified' are not interchangeable.

## Current verified context
- [x] User confirmed registration in Hack4Hack (screenshot in prior conversation; not stored in this repository).
- [x] User selected **PS1** for this project.
- [x] User chose public-facing project name **Merge**.
- [x] User chose VS Code with Codex coding support and component-by-component AI-assisted engineering.
- [x] Architecture direction chosen: React/TypeScript, FastAPI, PostgreSQL modular monolith.
- [x] Local Git repository initialized at `I:/Merge` on `main`; no commits created (M-002, 2026-11-06).
- [ ] Remote connected — none configured; no push performed.
- [x] Application code executed — FastAPI and Vite verified over local HTTP (M-002).
- [x] Automated tests passed — latest M-003 verification: 15 backend tests including real PostgreSQL, plus 6 frontend tests; see evidence below.
- [ ] Any public deployment exists — **not verified**.
- [ ] PS1 submission completed — **not verified**.

## Milestones / exit criteria

| Gate | Scope | Required objective evidence | Status |
|---|---|---|---|
| G0 | Repository and local integration | Commit hash, README, backend health, React build, PostgreSQL connectivity, migration, smoke test | LOCAL CHECKS VERIFIED — required commit hash pending; no commit authorized |
| G1 | Transactional team core | Real PostgreSQL 50-way last-seat race, cross-team race, idempotency; repeatable tests | NOT STARTED |
| G2 | Business flows and security | Team lifecycle, invites, requests, leader succession, audit, authorization negative tests | NOT STARTED |
| G3 | Frontend and realtime | Complete React flows, SSE between two clients, mobile/keyboard browser tests, scoring | NOT STARTED |
| G4 | Acceptance performance and CI | >=20 API tests in passing GitHub Actions, 10k/2k seed, k6 100 VUs, measured board p95 <200ms | NOT STARTED |
| G5 | Deployment and competition submission | Public URL, repo, one-page doc, load report, <=5-minute video, submitted links | NOT STARTED |

## Immediate Codex tasks (in order)
1. **M-001 — Repository audit:** Owner accepted audit. Existing source-of-truth files preserved; no application code or Git repository existed at inspection.
2. **M-002 — Minimal end-to-end skeleton:** IMPLEMENTED / LOCAL VERIFICATION PASSED, including database integration completed in M-003. FastAPI health, Vite React app, local PostgreSQL configuration, empty Alembic baseline, environment example, startup docs and tests. Owner approved existing PostgreSQL 17 instead of Compose; Docker unverified.
3. **M-003 — PostgreSQL integration (owner's current task scope):** VERIFIED locally on 2026-11-06: authenticated SELECT 1, online baseline upgrade, repeated upgrade, current revision, full backend suite and frontend/HTTP regressions passed. Owner completed provisioning/schema recovery. Do not rerun provisioning. Earlier schema/lock design scope remains deferred and is required before M-004: propose DDL/lock order and record ADR-016/017/020 before coding transactions.
4. **M-004 — Real DB concurrency core:** Implement create/join with idempotency, add parallel tests for 50-way last seat and cross-team membership, verify postconditions in database.
5. **M-005 — Team lifecycle:** Invites, requests, approvals, leave, transfer, deletion, audit and authorization via same transaction service.
6. **M-006 — React user flows + SSE:** Board, profiles, teams, requests, suggestions, live events, browser accessibility tests.
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

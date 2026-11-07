# Merge

Hack4Hack PS1 project. Phase 0 provides a FastAPI liveness endpoint, a React development page, and PostgreSQL/Alembic scaffolding. Domain features are not implemented. See [requirements](docs/REQUIREMENTS.md), [architecture](docs/ARCHITECTURE.md), [decisions](docs/DECISIONS.md), and [verified progress](docs/PROGRESS.md).

## Windows prerequisites

- Python **3.11.9**, Node **22.15.0**, npm **10.9.2** (`npm.cmd`).
- Local PostgreSQL **17**, listening on `127.0.0.1:5432`.
- Docker is not required for Phase 0 and has not been verified.

Use commands below from `I:\Merge`, unless another directory is shown. No PowerShell execution-policy changes or virtual-environment activation are needed.

## One-time database provisioning — owner action required

No credentials are supplied by this repository. Do not guess passwords or use a superuser as the application account. Use an administrator account you already know; SQL Shell (psql) or pgAdmin is suitable. The following is a **manual procedure**, not an automatically executed script.

Connect to the local server's maintenance database using your known administrator credentials, then inspect:

From PowerShell, this exact read-only preflight prompts locally for your known administrator name and password:

```powershell
Set-Location I:\Merge
$mergeAdminUser = Read-Host 'Your existing PostgreSQL administrator role name'
if ([string]::IsNullOrWhiteSpace($mergeAdminUser)) { throw 'A known role name is required. Stop.' }
psql -X -h 127.0.0.1 -p 5432 -U $mergeAdminUser -d postgres -W -v ON_ERROR_STOP=1 -f scripts/inspect_merge_postgres.sql
if ($LASTEXITCODE -ne 0) { throw 'Inspection failed. Stop; do not provision.' }
```

Do not send passwords to chat. The script uses a read-only transaction, selects only Merge object metadata, and makes no database/role/global-setting changes. Stop if the returned connection is not the intended local server. If Merge objects exist, stop before creation and review their ownership, role attributes and memberships. A database/role name alone does not prove it is safe to reuse.

The underlying existence checks are:

```sql
SELECT datname FROM pg_database WHERE datname = 'merge_dev';
SELECT rolname FROM pg_roles WHERE rolname IN ('merge_owner', 'merge_app');
```

**If either query returns any rows, STOP.** Inspect ownership and intended use with the owner. Do not run the creation steps, change a password, reuse the objects blindly, reset, alter, or drop anything existing.

Only when both queries return no rows, create new objects:

Open an interactive session with the same known administrator role:

```powershell
psql -X -h 127.0.0.1 -p 5432 -U $mergeAdminUser -d postgres -W -v ON_ERROR_STOP=1
```

Repeat the two existence queries immediately before creation. Proceed only if both are empty. Run each following step in order and stop on any error; do not paste the entire procedure blindly. These instructions require a known administrator with sufficient privileges to create the new roles/database and grant schema privileges.

```sql
CREATE ROLE merge_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE merge_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
```

In **psql**, set a new password using its hidden interactive prompt (do not paste a password into SQL, shell history or this chat):

```text
\password merge_app
```

Then, outside any transaction:

```sql
CREATE DATABASE merge_dev OWNER merge_owner;
REVOKE ALL ON DATABASE merge_dev FROM PUBLIC;
GRANT CONNECT ON DATABASE merge_dev TO merge_app;
```

Connect to the **new** database as the administrator:

```text
\connect merge_dev
```

Confirm `SELECT current_database();` returns `merge_dev`, then:

```sql
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO merge_app;
```

These revocations apply only to newly created Merge objects. The application role has no cluster administration or database-creation privileges. For this development bootstrap it can create its own tables in `merge_dev.public`, including Alembic's version table. Separate runtime and migration roles are deferred until the schema/security design; this is not a production privilege model. Stop and inspect any error; do not automatically retry partial provisioning.

## Configuration and installation

### Recovery inspection after a failed provisioning reconnect

If `provision_merge_postgres.sql` stopped at line 36 (`\connect merge_dev`), do not rerun it. Earlier role/database changes were committed, while lines 37–53 (schema grants and final verification) were skipped. Inspect the new database by connecting directly, with one local administrator password prompt:

```powershell
Set-Location I:\Merge
psql -X -h 127.0.0.1 -p 5432 -U postgres -d merge_dev -W -v ON_ERROR_STOP=1 -f scripts/inspect_merge_recovery.sql
if ($LASTEXITCODE -ne 0) { throw 'Recovery inspection failed. Stop; do not change privileges.' }
```

This script is read-only. It reports CONNECT, schema USAGE/CREATE, schema/database ACLs, ownership, Merge role flags/memberships and user-schema object metadata; it does not select secrets or application rows. Report only this metadata, never a password. No recovery SQL is authorized until the owner reviews and approves the specific statements derived from the results.

Recovery rules: stop for unexpected ownership, elevated role privileges, memberships or unexplained user objects. Normal `public` ownership by `pg_database_owner` does not require an ownership change. If CONNECT is already true, no database GRANT is needed. Grant only missing schema USAGE/CREATE to `merge_app`. Removing remaining PUBLIC schema privileges is the skipped hardening step from the original setup and must be reviewed separately: if approved, revoke the reported PUBLIC privileges and explicitly grant `merge_app` USAGE/CREATE in one transaction so it does not lose inherited access. Do not alter role attributes/passwords or schema/database ownership, create domain objects, or apply migrations as part of recovery inspection.

### Guarded provisioning workflow (after successful owner inspection)

`scripts/provision_merge_postgres.sql` automates the SQL above with fresh existence and connection checks. It stops on the first error, creates only new Merge objects, and prompts for the application password using `\password`. The password-encryption setting is transaction-local, not global. The non-login `merge_owner` owns the database; `merge_app` receives only database CONNECT and public-schema USAGE/CREATE, sufficient to own and migrate its own development tables. No membership in the owner/admin role is granted. Existing databases' privileges are unchanged; PostgreSQL roles are cluster-wide, and this script only creates the two new names.

Run in your own PowerShell terminal, without transcript/session recording:

```powershell
Set-Location I:\Merge
psql -X -h 127.0.0.1 -p 5432 -U postgres -d postgres -W -v ON_ERROR_STOP=1 -f scripts/provision_merge_postgres.sql
if ($LASTEXITCODE -ne 0) { throw 'Provisioning failed. Stop; do not rerun or replace objects.' }
```

The first password prompt is for the existing administrator. The `merge_app` prompts ask twice for a new application password. Choose a strong, unique, single-line password without `${` syntax (dotenv interprets that syntax). Reconnecting to the new database may prompt again for the administrator password. Do not paste passwords into commands or chat. Database creation cannot share the roles' transaction, so an error can leave a partial setup: stop and report only the error/object metadata, without retrying.

After successful provisioning, the following owner-run helper prompts twice for the **same new merge_app password**, checks Git exclusion, and exclusively creates `backend/.env`. It refuses an existing file or noninteractive input, and prints no secret:

```powershell
.\backend\.venv\Scripts\python.exe scripts/configure_backend_env.py
if ($LASTEXITCODE -ne 0) { throw 'Configuration failed. Stop and inspect locally.' }
```

Once that succeeds, run the migration/verification commands below or let Codex run them. Never give Codex the administrator password. The manual configuration alternative below is for a fresh setup; do not overwrite a file created by the helper.

```powershell
Set-Location I:\Merge
if (-not (Test-Path backend/.env)) { Copy-Item .env.example backend/.env }
git check-ignore backend/.env
notepad backend/.env
```

After provisioning, set `MERGE_DB_PASSWORD` in `backend/.env` locally to the new application password. Quote dotenv values containing `#`, spaces or other special characters. Alternatively leave it empty and configure a dedicated PostgreSQL password-file entry for `127.0.0.1:5432:merge_dev:merge_app`. Do not publish the file or print configuration. Environment variables override `backend/.env`; this absolute file location works independently of the working directory. A root `.env` is no longer loaded. Existing local files must be reviewed/moved manually without overwriting either file. Passwords are assembled into a SQLAlchemy URL programmatically, so URL escaping is unnecessary. If Git reports dubious ownership in this workspace, use `git -c safe.directory=I:/Merge check-ignore backend/.env` for this check; do not change global settings.

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
.\backend\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e backend
Push-Location frontend
npm.cmd ci
Pop-Location
```

`backend/requirements.lock` pins the complete Windows/Python 3.11 dependency resolution; `frontend/package-lock.json` pins npm's resolution. Do not use unpinned upgrades as part of setup. To deliberately regenerate the Python lock with uv 0.9.29, use `uv pip compile backend/pyproject.toml --extra dev --python backend/.venv/Scripts/python.exe --output-file backend/requirements.lock` and review the diff.

## Migration and verification

After manual provisioning and configuration:

```powershell
Push-Location backend
.\.venv\Scripts\python.exe -m pytest -q -m database
if ($LASTEXITCODE -ne 0) { throw 'Database smoke failed. Stop before migrations.' }
.\.venv\Scripts\python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Migration failed. Stop and inspect.' }
.\.venv\Scripts\python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Repeated upgrade failed. Stop and inspect.' }
.\.venv\Scripts\python.exe -m alembic current
if ($LASTEXITCODE -ne 0) { throw 'Revision check failed. Stop and inspect.' }
.\.venv\Scripts\python.exe -m pytest -q
Pop-Location
Push-Location frontend
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
Pop-Location
```

The baseline contains no domain DDL. Online upgrade creates only Alembic's version table and records `0001_baseline`; the second upgrade should do nothing. Offline SQL generation (`python -m alembic upgrade head --sql`) does **not** prove database connectivity or successful application.

From the repository root, `.\backend\.venv\Scripts\python.exe scripts/check_local_http.py` verifies real API/Vite HTTP connectivity, a backend outage and recovery without database access. It requires free ports 8000/5173, starts its own servers, and stops only those processes. Frontend rendering/state tests use jsdom with mocked fetch; this HTTP check complements them and does not claim full browser E2E coverage.

Without database configuration, run `python -m pytest -q -m "not database"` from `backend` using its venv interpreter. The separate `python -m pytest -q -m database` test executes real `SELECT 1`; unavailable credentials cause a failure, never a silently passing mock. Phase 0 database code refuses targets other than `127.0.0.1:5432/merge_dev` with `merge_app`.

## Run locally

Terminal 1:

```powershell
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
Set-Location I:\Merge\frontend
npm.cmd run dev
```

Open <http://127.0.0.1:5173>. Vite proxies the page's `/health` request to <http://127.0.0.1:8000/health>, which returns `{"status":"ok"}`. The page shows loading, success, or a generic error, with a five-second timeout and retry button. Stop the API and press **Check again** to verify failure; restart it and retry to verify recovery. Stop both servers with Ctrl+C.

`/health` is public process liveness; it makes no database-readiness claim. The frontend uses a relative URL, so no CORS middleware or frontend secrets are needed. Vite's proxy is development-only: a future deployment must explicitly configure same-origin API routing. Production hosting is out of scope.

## Owner explanation / exercise

`main.py` handles HTTP liveness, `config.py` reads local settings, `session.py` creates a lazy database engine, and Alembic tracks schema revisions separately from API startup. Explain why a healthy HTTP server can coexist with a failed database smoke test. Change the frontend timeout from five to two seconds, rerun its tests, and adapt the timeout assertion.

No commits or pushes are performed automatically. Review `git status`, the source files and `docs/PROGRESS.md` before approving a commit.

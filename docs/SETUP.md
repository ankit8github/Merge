# Local development setup

Use Python 3.11, Node 22.15.0, npm 10.9.2 and PostgreSQL 17. See
[testing](TESTING.md) to work entirely offline. The commands here are instructions
for a fresh developer environment; repository polish did not execute database
commands or start services.

## Install dependencies

From the repository root in PowerShell:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
npm.cmd --prefix frontend ci
```

On Linux, use `backend/.venv/bin/python` instead. No package activation is needed.
Frontend dependency installation uses the committed lockfile.

## Provision a fresh development database

The ordinary application is deliberately fixed to TCP `127.0.0.1:5432`, database
`merge_dev`, role `merge_app`. It cannot address test, benchmark or production
through arbitrary connection overrides. Install/start PostgreSQL separately.
For a **new** local cluster namespace, review then run from the repository root:

```powershell
psql -X -h 127.0.0.1 -p 5432 -U postgres -d postgres -W -f scripts/provision_merge_postgres.sql
```

The script prompts privately for the application password, creates a non-login
owner and restricted application role, and refuses existing Merge objects.
Stop on partial failure; inspect before retrying. Do not reset an existing database.
The dedicated test/profile/benchmark targets use different reviewed scripts and
explicit guards; see [test database contracts](TEST_DATABASE.md) and
[release validation](RELEASE_VALIDATION.md).

Create the ignored backend environment through the masked interactive helper:

```powershell
.\backend\.venv\Scripts\python.exe scripts/configure_backend_env.py
```

It exclusively creates `backend/.env`; it never overwrites an existing file.
[.env.example](../.env.example) documents the permitted fields. Never put a real
password in source, a command argument or a `VITE_*` variable.

## Apply an explicit development revision

Review the migration files and database identity first. From `backend/`, a fresh
approved development target can be migrated explicitly:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade 0006_profiles
```

This is a state-changing development command, not an offline verification step.
Do not use it for retained acceptance or production databases. Their owned
migration transactions and exact-revision gates have separate runbooks.
No automatic migration occurs at application startup. Profiles require revision
`0006_profiles`; older test suites intentionally run at earlier exact revisions.

The app has no catalog administration UI or automatic development seed. A fresh
database initially has an empty catalog. Review a bounded local catalog fixture
before expecting team journeys; benchmark seed tooling cannot target `merge_dev`.
Production catalog preparation is documented in [the production runbook](PRODUCTION.md).

## Start the API

Use a private secret mechanism to provision/reuse a random 32-byte lowercase hex
`MERGE_AUTH_THROTTLE_SECRET`. Authentication reads process environment, not
`backend/.env`. For a fresh local shell, this generates a key without printing it;
retain the shell for restarts so throttle partitions remain stable:

```powershell
Set-Location backend
$env:MERGE_AUTH_MODE = 'development'
$env:MERGE_AUTH_ORIGIN = 'http://127.0.0.1:5173'
$env:MERGE_AUTH_THROTTLE_SECRET = & .\.venv\Scripts\python.exe -c 'import secrets; print(secrets.token_hex(32))'
.\.venv\Scripts\python.exe -m app.serve --host 127.0.0.1 --port 8000
```

Use the controlled launcher; it preserves the transport peer used by authentication.
Keep development mode on loopback. See [authentication](HTTP_AUTH.md) and
[throttling](AUTH_THROTTLING.md) for startup, cookie and trusted-proxy contracts.

## Start the frontend

In another terminal, from the repository root:

```powershell
Set-Location frontend
npm.cmd run dev
```

Open exactly `http://127.0.0.1:5173`. Vite proxies `/health`, `/auth` and `/api`
to the loopback API, preserving the configured Origin. `localhost` is a different
origin. Register, then explicitly sign in. Changing to production requires the
[separate production package](DEPLOYMENT.md), secure cookies and HTTPS.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| API refuses startup | Exact Origin, explicit local mode, 64-character lowercase hex throttle key |
| Database connection rejected | Fixed database/role/host, ignored environment and actual provisioned role |
| 403 on browser commands | Open the exact frontend origin; preserve Origin/custom headers and CSRF |
| Empty discovery | Fresh schema contains no hackathon catalog data |
| Profile operation unavailable | Exact profile migration and matching guarded target |
| Test collection requests credentials | Use the default offline command; select live suites only under their runbooks |

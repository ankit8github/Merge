# Railway deployment runbook - prepared, not deployed

**Retained alternative:** [Render](RENDER.md) is the current demonstration target.
Railway preparation is superseded as the immediate hosting choice; its helpers
remain Render source dependencies. Neither adapter is live verified.

This adapter is the primary evaluated hosting option for the owner's requested
single-service cloud deployment. **No Railway project/service, production
connection, migration, purchase, commit, push or deployment was performed.**
The owner reports that all five Actions jobs passed for `bb60ab3`; that report
was not independently fetched in this task and does not certify this new adapter.

## Architecture and trust boundary

```text
Browser -- Railway-managed HTTPS --> Railway public HTTP edge
                                      |
                      one application service, assigned PORT
                      Caddy: React assets, /auth, /api, SSE
                                      |
                               127.0.0.1:8000
                              FastAPI, one worker
                                      |
                         private Railway network + TLS
                                      |
                     postgres.railway.internal:5432
                     PostgreSQL 17, merge_prod, volume
```

The API has no public listener, domain or TCP proxy. PostgreSQL has no public
access/TCP proxy. Only Caddy listens on `PORT`; it accepts the exact assigned
hostname, requires the Railway HTTPS/client-IP headers, retains existing static
security/cache policy, and forwards `/auth` and `/api` without removing prefixes.
SSE retains immediate Caddy flushing, no compression, 75-second proxy ceiling
and the existing 60-second lease/reconnect behavior. No domain model changed.

Uvicorn's proxy middleware stays disabled. The existing authentication boundary
trusts only `127.0.0.1/32`; Caddy removes alternative forwarding headers and supplies
one X-Forwarded-For value from the platform's X-Real-IP and an HTTPS scheme. Origin,
CSRF, session authorization, durable throttles and Secure/HttpOnly/SameSite=Lax
`__Host-merge_session` remain enforced. No CORS wildcard or development fallback.

**Platform trust assumption:** Railway's project/environment network is trusted.
No stable edge-IP allowlist or request signature is implemented. A compromised
same-environment service can reach Caddy and forge edge headers, although it still
needs a valid authenticated session/CSRF for protected actions. Use a dedicated
production environment with only the app, database and temporary trusted operations.
Do not add untrusted services, TCP proxies, CDN or extra public domains. Test that
the actual edge overwrites spoofed headers before acceptance; this has not been
proven offline. Direct loopback worker access requires container compromise.

Railway documents public HTTPS forwarding headers and streaming request limits in
[network specs](https://docs.railway.com/networking/public-networking/specs-and-limits),
and environment isolation in [private networking](https://docs.railway.com/networking/private-networking/how-it-works).
The existing fixed-IP [VPS runbook](PRODUCTION.md) is a separate supported package;
its settings/credentials must not be mixed into this adapter.

## Deployment files and exact dashboard settings

Build [deploy/Dockerfile.railway](../deploy/Dockerfile.railway) with repository root
as the build context. It builds locked React assets, copies the existing Caddy
binary into the Python image, runs non-root, and adds no Python/npm dependency.
No build ARG accepts secrets; no frontend environment variable is needed.
The [Caddy template](../deploy/railway/caddy.template.json) is public configuration.

[settings.json](../deploy/railway/settings.json) is a checked **dashboard contract**,
not an auto-discovered Railway configuration file. Current Railway docs mark
`railway.json`/`railway.toml` deprecated and unavailable to new services; newer
[IaC](https://docs.railway.com/infrastructure-as-code) requires a separate CLI/SDK.
For this bounded deployment, enter these settings in the dashboard rather than
introducing a new dependency or applying project-wide IaC.

| Application service setting | Exact required value |
| --- | --- |
| GitHub source | ankit8github/Merge, reviewed commit on main |
| Root directory / build context | repository root `/` |
| Dockerfile variable | `RAILWAY_DOCKERFILE_PATH=deploy/Dockerfile.railway` |
| Start command | `python -m app.railway.serve` |
| Pre-deploy command | empty; no automatic migrations |
| Public domain | Generate Railway domain; target the assigned `PORT` |
| TCP proxy | disabled/absent |
| Replicas / region | one replica, one region, same region as PostgreSQL |
| Healthcheck path / timeout | `/ready` / 180 seconds |
| Restart policy | On Failure, maximum 3 retries |
| Serverless/sleep | disabled |
| Deployment draining | 40 seconds or more |
| Application volume | none |
| Autodeploy | disable during initialization; enable only after release approval |

A Python supervisor validates generated Caddy config natively before launching,
starts the API, waits up to 60 seconds for private readiness, then starts Caddy.
Either child exiting fails the container. SIGTERM/SIGINT stops ingress, terminates
both children, waits up to 30 seconds in total, then kills/reaps a stalled child.
No migration runs in any of those startup paths.

Caddy routes Railway's `Host: healthcheck.railway.app`, GET/HEAD `/ready` probes to
the API readiness check. The public hostname's `/ready` is 404. Ordinary `/health`
is liveness only. Railway [health checks](https://docs.railway.com/deployments/healthchecks)
gate activation; they are not continuous monitoring. Configure external monitoring
separately after deployment. Native Caddy/Docker and actual health-host behavior
have not been executed here.

## Exact environment variables - application

Set only service-scoped production values, not shared admin/migration credentials.

| Variable | Required value/source |
| --- | --- |
| `RAILWAY_DOCKERFILE_PATH` | `deploy/Dockerfile.railway` |
| `PORT` | Platform-assigned decimal port, 1024-65535 except private API port 8000; explicitly using `8080` is also supported when the public domain targets 8080 |
| `RAILWAY_PUBLIC_DOMAIN` | Railway-injected generated hostname, no scheme/path; must be a single label under `.up.railway.app` |
| `RAILWAY_ENVIRONMENT_NAME` | Railway-provided `production`; create/select this exact environment name |
| `RAILWAY_PROJECT_ID` | Railway-provided UUID |
| `RAILWAY_ENVIRONMENT_ID` | Railway-provided UUID |
| `MERGE_RAILWAY_DB_HOST` | `postgres.railway.internal`; verify it matches the database service's private domain |
| `MERGE_RAILWAY_RUNTIME_PASSWORD` | Fresh private password for `merge_runtime` |
| `MERGE_RAILWAY_THROTTLE_KEY` | Fresh random 32-byte key encoded as exactly 64 lowercase hex characters; keep stable across restarts/rollbacks |

The HTTPS Origin is derived exactly as `https://` + assigned public domain.
Do not override it with a second origin or hostname. Passwords must contain 32-128
characters from `A-Z a-z 0-9 _ -`; generate fresh cryptographic values privately.
No literal sample password is supplied. Never print secrets or place them in a
command argument, Git, build ARG, browser variable, screenshot or recording.

Do not attach `DATABASE_URL`, `DATABASE_PUBLIC_URL`, `PG*`, `VITE_*`, `MERGE_DB_*`,
`MERGE_AUTH_*`, VPS `MERGE_PROD_ORIGIN`, admin or migrator passwords to the app.
They reject startup. Railway's unrelated platform variables are permitted.
No `.env` is read by this adapter. Renaming a public domain changes the Origin;
review/redeploy explicitly and expect host-only sessions on the old host to end.

## Provision private PostgreSQL 17

Owner dashboard actions, after reviewing plan and billing:

1. Create a dedicated project/environment named `production`. Add a PostgreSQL
   service named **postgres** in the same region as the app. Use a fresh persistent
   volume and a fresh platform-generated administrator password. No retained/local
   database, existing volume or credentials may be adopted.
2. Inspect the source image **before first initialization**. Railway's maintained
   SSL-enabled source supports `ghcr.io/railwayapp-templates/postgres-ssl:17`;
   select major 17, record the resolved digest, and keep its SSL-enabled start
   command/volume initialization. Do not assume the default template selects 17.
   Never change the major image on an initialized volume to make this recipe fit.
   If it initialized at another major version, stop for a fresh-target decision.
3. Keep the template's administrator/database initialization variables and volume
   mount. The default template database may remain `railway`; the explicit
   bootstrap creates a new `merge_prod` and refuses an existing one. The private
   hostname must be exactly `postgres.railway.internal`, TCP 5432, admin `postgres`.
4. Ensure PostgreSQL Public Access/TCP Proxy and public domains are **absent**.
   No `DATABASE_PUBLIC_URL` is consumed. App credentials are restricted new roles,
   not the template superuser. Do not copy all PG variables into the app.
5. Review private networking, volume size, backup retention and restore policy.
   Standard single-node hosting is not HA/PITR certification. Railway notes that
   changing its shipped template can change the maintenance/support boundary;
   verify that scope for the selected 17 image in the dashboard.

Sources: [Railway PostgreSQL](https://docs.railway.com/databases/postgresql),
[maintained SSL image/version usage](https://github.com/railwayapp-templates/postgres-ssl/blob/main/README.md).
The adapter checks major 17, actual private address, TLS, database/role, role flags,
privileges, READ COMMITTED, non-autocommit, bounded timeouts and exact revision.
DNS must resolve exclusively to private addresses; each process pins one resolved
address. A platform address change requires restart/redeploy, not a public fallback.
`sslmode=require` encrypts transport; the template's self-signed TLS is not public-CA
hostname authentication. Trust is scoped to Railway's isolated private network/DNS.

## Explicit bootstrap and migrations

Create one **temporary private operations service** from the same reviewed GitHub
source/Dockerfile. It is not another public application or permanent worker.
Set root `/`, no public domain, no TCP proxy, no healthcheck, no pre-deploy command,
one replica, no autodeploy and restart policy **Never**. Its start command is:

```text
python -m app.railway.operations --confirm-merge-prod
```

Set platform-provided project/environment identity and the Dockerfile variable as
for the app, plus the fixed private `MERGE_RAILWAY_DB_HOST`. It must not have
`RAILWAY_PUBLIC_DOMAIN`, runtime throttle key, `DATABASE_URL` or PG overrides.
Configure each action explicitly and approve one deployment at a time. Do not
set a recurring job, parallel replica or automatic action/retry.

| Ordered action: `MERGE_RAILWAY_ACTION` | Secret variables allowed on operations service | Effect |
| --- | --- | --- |
| `bootstrap` | `MERGE_RAILWAY_ADMIN_PASSWORD`, `MERGE_RAILWAY_RUNTIME_PASSWORD`, `MERGE_RAILWAY_MIGRATOR_PASSWORD` | Create only fresh `merge_prod`, `merge_runtime`, `merge_migrator`; apply restricted database/schema grants |
| `prepare` | `MERGE_RAILWAY_MIGRATOR_PASSWORD` only | Empty public schema -> exact `0005_invitations`, owned DDL transaction |
| `migrate` | `MERGE_RAILWAY_MIGRATOR_PASSWORD` only | Exact 0005 -> 0006; SHARE-lock/hash all twelve old tables and reject any content change |
| `verify` | `MERGE_RAILWAY_MIGRATOR_PASSWORD` only | Read-only guarded connection at exact 0006; no writes |
| `catalog` | `MERGE_RAILWAY_MIGRATOR_PASSWORD` only | Insert one explicitly approved hackathon; no upsert or replacement |

The three bootstrap passwords must be distinct and fresh. The runtime password
must match the app's runtime value. The admin password must match the new
PostgreSQL service's private template password; use a private dashboard reference
or secret input, never copy it into logs/chat. Use no global/shared secret scope.

After bootstrap success, **remove admin/runtime secrets from the operations
service before `prepare`**. They are forbidden for other operations. Keep the
migrator secret only on operations. New objects make bootstrap intentionally
non-repeatable. Creating roles and CREATE DATABASE cannot be one PostgreSQL
transaction: a partial failure retains state and requires inspection, never reset
or blind retry. Before preparation/migration on existing data, stop app traffic
and approve a backup; the first run must target an otherwise empty new deployment.

For each action, require native process exit 0 **and** one final JSON result with
matching `action`, `database=merge_prod`, `native_exit_code=0`; preparation/migration
also report their exact final revision. Stop on missing/ambiguous/nonzero output.
Retain source commit, image digest, timestamp and sanitized result privately.
`verify` checks migrator identity/revision; API startup/readiness separately checks
runtime table inventory and exact least-privilege grants. No guard is weakened to
work around a failed stage.

For `catalog`, also set exactly:

- `MERGE_RAILWAY_CATALOG_ID`: a new owner-approved UUID.
- `MERGE_RAILWAY_CATALOG_NAME`: owner-approved nonempty name, maximum 120 characters.
- `MERGE_RAILWAY_CATALOG_MIN`: integer minimum team size.
- `MERGE_RAILWAY_CATALOG_MAX`: integer maximum, with `1 <= min <= max <= 100`.

No automatic seed/admin UI exists. Remove catalog inputs after the single approved
insertion. Never run benchmark seed tooling against production. When operations
are complete, stop/remove only the temporary operations service and its secret
access after reviewing retention; retain the database service/volume and private
release evidence. This runbook performs no service deletion automatically.

## Deploy GitHub source and verify HTTPS

After reviewing/committing/publishing this change in separately approved steps:

1. Add an empty app service connected to `ankit8github/Merge`, reviewed main commit.
   Configure the Dockerfile, root, start/health/drain/replica settings and only the
   runtime variables above. Generate its Railway domain and verify the injected
   hostname/target port before starting. A premature startup fails closed; it does
   not bootstrap/migrate a database.
2. After successful explicit operations, deploy the app. Native image installation,
   Caddy validation, private API readiness and Railway health activation must pass.
   Keep source/image identity and a sanitized result. Do not call a green build a
   successful release without an accessible HTTPS URL and feature smoke checks.
3. From an external browser, verify valid TLS, React/deep links/assets, public
   `/ready` and docs 404, exact-Origin registration/login, Secure host-only cookie,
   CSRF rejection, hostile Origin and forwarding spoof rejection. Verify a real
   client gets its own throttle partition and spoofed X-Real-IP/XFF cannot select
   another identity. If the edge does not overwrite hostile values, stop before
   public acceptance; do not add wildcard trust as a workaround.
4. Complete create/request/approve/invite/redeem/leave/remove/succession/deletion,
   profile edit and explained leader ranking, and unauthorized/full-team failures.
   Use fresh bounded demo accounts; no privileged/demo credentials in Git/video.
5. Two authenticated browsers must see SSE updates without refresh; verify event
   frames arrive incrementally through the actual Railway edge and reconnect after
   60-second leases and a deployment. Verify phone/keyboard/focus/zoom. Static
   config tests do not prove proxy buffering behavior.

Railway documents a 15-minute active HTTP request ceiling and 5-minute inactivity
limit; current SSE leases/heartbeats fit those limits in design, but actual streaming
is untested. There is no known application feature requiring an unsupported
Railway primitive. Fixed-IP VPS settings, custom domains, arbitrary connection URLs,
HA/poolers, sleeping services and multiple worker topologies are intentionally
unsupported by this adapter. No image-pull, account-plan or deadline success is
promised; domain issuance can take time.

## Rollback and operations

Keep the app/DB region, throttle key, runtime password and assigned domain stable.
A later rollback can select a previously **successful Railway adapter image/commit**
compatible with schema 0006, then repeat readiness and smoke. Baseline `bb60ab3`
contains only the VPS package and is not a Railway rollback target. First launch
has no known-good Railway image: stop ingress/app and fix forward if needed.
Never downgrade/reset/drop roles or remove the database volume to recover a failed
migration or deploy. Inspect ambiguous/partial state under separate owner approval.

Configure platform backups and perform a separately approved isolated restore
drill. Snapshot existence alone is not a verified restore. Healthchecks do not
provide ongoing uptime monitoring. Retained outbox/session/throttle history grows;
no new automatic retention/deletion policy is introduced.

## Cost and resource limits - checked 15 November 2026

Railway's [plan documentation](https://docs.railway.com/pricing/plans) currently lists
Hobby at **$5/month with $5 of included usage**, not a fixed $5 total for app plus
PostgreSQL. Published usage rates are RAM **$10/GB-month**, CPU **$20/vCPU-month**,
volume **$0.15/GB-month**, egress **$0.05/GB**. Billing is based on actual consumption;
app, database, temporary operations and deployment overlap all contribute. Taxes,
backup services and extra resources may add cost. Confirm the dashboard/plan before
accepting charges. No purchase or billing change was made.

Example only, not measured: average combined RAM 0.7 GB, CPU 0.1 vCPU and 1 GB volume
would be about $9.15/month before egress/tax/other charges at those published rates;
the $5 usage credit is applied, not added again. Actual cost here is unknown.
Free/trial is not a production guarantee: the docs list Free at 0.5 GB RAM/service,
0.5 GB volume and $1 monthly credit, with eligibility/resource restrictions.

Suggested initial **limits for review**, not demonstrated requirements: app 1 GB
RAM / 1 vCPU and PostgreSQL 0.5-1 GB RAM with a reviewed persistent volume. Measure
actual RSS/CPU/storage before reducing limits. Existing API pool is 5+5, Argon2 has
two bounded workers, and SSE caps remain 64/process and two/account. PostgreSQL
must have enough connections for runtime, temporary operations and rollout overlap.
Disable sleep; SSE/private database traffic may prevent expected idling anyway.
No 100-client, 10k/2k seed or p95 claim has been measured on Railway.

## Historical offline verification - before Render selection

Actual environment: Windows PowerShell, Python 3.11.9, Node 22.15.0, npm 10.9.2;
existing locked dependencies. Commands ran from the indicated directories:

| Directory / exact command | Actual result |
| --- | --- |
| backend: `.\.venv\Scripts\python.exe -B -m pytest -q -m 'not database' --tb=short` | Final **2070 passed**, 32 deselected, 57.87 s, exit 0 |
| backend: `.\.venv\Scripts\python.exe -B -m pytest -q tests/test_railway.py tests/test_production.py tests/test_ci_configuration.py --tb=short` | Final **187 passed**, 2.36 s, exit 0 |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1` | **434 passed**, 18 files, 122.22 s, exit 0 |
| frontend: `npm.cmd run build` | TypeScript/Vite passed, 50 modules, Vite 1.89 s, exit 0 |
| backend: `.\.venv\Scripts\python.exe -B -m app.railway.check` | Offline Railway packaging contracts passed |
| backend: `.\.venv\Scripts\python.exe -B -m app.production.check` | Existing VPS contracts passed |
| backend: `.\.venv\Scripts\python.exe -m pip check` | No broken requirements |
| root: `git diff --check` | Passed |

The existing Starlette/httpx deprecation and Git LF/CRLF notices remain. Earlier
new-test collection/execution found one test patched the config source instead of
an imported worker alias; the test injection was corrected. Its synthetic migrator
password was also separated from the runtime fixture so namespace rejection is
actually reached and asserted. An initial full 2069-pass checkpoint preceded the
last client-IP capture regression; the final 2070-pass run includes it. No existing
test was removed or weakened.

Static AST/import/link/JSON/Docker-input/secret-artifact checks passed. All 310
baseline paths are retained; all 980 preexisting local evidence files are unchanged
and ignored. Existing secret-pattern matches are three unchanged synthetic
security-test fixtures, not newly introduced credentials. New logs, baseline,
source inventory and review helper are retained only in ignored
`backend/test-results/railway-prep-b189e3aa09d44151b4bbb3bcd662c17d/`.
Exact source/evidence/review status: [PROGRESS.md](PROGRESS.md).
No native Docker/Caddy or Railway platform run is available locally. Secret scans,
Python tests and JSON checks cannot certify container startup, DNS/TLS/grants,
public edge identity/SSE, backup restore or production resource capacity.

Owner exercise: explain why changing PORT to 8000 rejects startup, then change it
to another allowed port in a synthetic fixture and verify that Caddy follows it
while the private worker remains on 127.0.0.1:8000.

## Source inventory and review handoff

- New `backend/app/railway/`: `__init__.py`, `config.py`, `database.py`,
  `application.py`, `api.py`, `serve.py`, `operations.py`, `check.py`.
- New `backend/railway_alembic/env.py`: owned Railway-only migration environment;
  all six existing schema revision files remain unchanged.
- New `backend/tests/test_railway.py`: 95 synthetic offline cases.
- New `deploy/Dockerfile.railway`, `deploy/railway/caddy.template.json`,
  `deploy/railway/settings.json` and this runbook.
- Updated `README.md`, `docs/README.md`, `docs/ARCHITECTURE.md`,
  `docs/DECISIONS.md`, `docs/DEPLOYMENT.md`, `docs/TESTING.md`, `docs/PROGRESS.md` for the adapter,
  trust decision, evidence and owner-reported baseline CI result.
- No dependency/lockfile, frontend application, domain/authentication service,
  existing VPS/test/release guard, workflow or migration revision was changed.
  No files removed/moved; no index/staging change or commit performed.

This inventory/results describe the earlier Railway preparation phase. Current
release scope, local commit and separately approved publication sequence are in
[the documentation audit](archive/DOCUMENTATION_AUDIT.md). Render remains the
selected demonstration target; no Railway cloud operation is proposed here.

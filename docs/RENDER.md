# Render Free deployment preparation

Status: prepared locally, not deployed. No production connection, initialization,
server startup, resource creation, deployment, push or billing action was performed.
The owner reports five Actions jobs passed at baseline `bb60ab3`; these adapters
need fresh hosted CI and live acceptance. This is a temporary demonstration target,
not a production availability commitment. Review this guide before any publication.

## Architecture and bounded scope

```text
Browser -- Render-managed HTTPS / assigned onrender.com hostname
   |
Render Free web container :$PORT (10000 by default)
   Caddy: built React assets, /auth + /api, immediate SSE flushing
   | 127.0.0.1:8000 only
   FastAPI: one Uvicorn worker, existing production auth and domain services
   | private same-region dpg-* hostname, TCP 5432, TLS required
Render Free PostgreSQL 17: merge_prod
   merge_runtime: restricted application login
   configured Render-created owner: setup deployment only (merge_prod_user here)
```

Caddy is the only public listener during ordinary application operation. Render
owns certificates; Caddy listens on HTTP behind that edge and does not issue
certificates or expose its admin API. Only the exact assigned hostname is accepted.
Custom domains, additional proxies and preview environments are deliberately
unsupported by this adapter. No separate frontend, API service, Redis or worker.

Unchanged: application APIs, secure host-only session cookies, CSRF and exact Origin
checks, password hashing, transaction/lock/retry strategy, audit/outbox, deterministic
ranking, SSE authorization, all six migrations, CI, local/test/release/VPS guards.
No dependency or business schema revision is added. A private deployment-only
`merge_deployment.setup_claim` table records explicit initialization attempts.

## Existing database reported by the owner

The owner reports this resource available; no connection or privilege inspection
was performed during this compatibility fix:

| Field | Reported value |
| --- | --- |
| Database / PostgreSQL | `merge_prod` / **17** |
| Region / port | **Oregon (US West)** / `5432` |
| Initial owner | `merge_prod_user` |
| Internal hostname | `dpg-dbsob2e1egvs73edo350-a` |
| Plan | Free |

Use this existing resource for the separately approved fresh setup. Do not
recreate it, rename its user, change credentials or apply the fresh-resource
Blueprint to it. Put the web service in **Oregon**, in the same account/region.
The hostname/account are nonsecret configuration; no password or full connection
URL belongs in this document.

## Dashboard settings: review first, execute only after owner approval

Manual creation is recommended for the first initialization because Free has no
shell, one-off job or paid pre-deploy command. The root [render.yaml](../render.yaml)
is a **fresh-resource legacy template** (Singapore, initial user merge_migrator),
with autodeploy disabled and no setup hook. It is not the procedure for attaching
the existing Oregon database. Do not sync it to adopt/recreate that resource. It is not an automatic initialization recipe. A direct initial
Blueprint sync starts the ordinary command against an empty schema and fails
closed until the separate setup deployment is explicitly selected.

| Resource / field | Exact selection |
| --- | --- |
| PostgreSQL resource | Select the existing owner-reported resource; no new database |
| Database / initial user | Existing `merge_prod` / `merge_prod_user`; do not rename or recreate |
| PostgreSQL version / plan | Explicitly **17**, **Free**; do not accept a newer default |
| Region | **Oregon (US West)** for the web service, matching the existing database |
| External database access | Disable all external access; Blueprint `ipAllowList: []` |
| Web name / source | `merge-demo`; `https://github.com/ankit8github/Merge`, branch `main` |
| Runtime / plan / instances | Docker / **Free** / **1** |
| Root / Docker context | Repository root (`.`); leave Root Directory empty |
| Dockerfile | `./deploy/Dockerfile.render` |
| Normal Docker command | `python -m app.render.serve` |
| First setup Docker command | `python -m app.render.setup --confirm-new-render-production` |
| Health check path | `/ready` in both modes; meanings differ below |
| Automatic deploys / previews | Off / disabled; deploy only the reviewed SHA manually |
| Pre-deploy command / initial hook | Empty; no automatic migrations |
| Shutdown delay | 40 seconds; Caddy is signaled first; both children have bounded shutdown |
| Disks, scaling, extra ports, custom domains | None |
| Public URL | Use only the assigned HTTPS hostname; no verified URL exists yet |

The Docker build performs locked `npm ci`, TypeScript/Vite build and Python locked
installation. Node/build dependencies do not run in the final image. Runtime is
non-root UID/GID 10001. No database is contacted during build. Builds themselves
need more resources than a running 512 MB web instance and consume pipeline quota.
The image copies Caddy from its official Alpine stage into the Debian Python stage;
native binary/config compatibility remains a required build/startup gate.

## Exact environment variables (values below contain no secrets)

Ordinary application environment:

| Name | Required value / source |
| --- | --- |
| `PORT` | `10000` or Render-assigned unprivileged port; never 8000/18012/18013/19099 |
| `MERGE_RENDER_ENVIRONMENT` | `production` |
| `MERGE_RENDER_DB_HOST` | `dpg-dbsob2e1egvs73edo350-a` for the reported database; never its external hostname |
| `MERGE_RENDER_RUNTIME_PASSWORD` | Fresh private runtime password, 32-128 URL-safe letters/digits/underscore/hyphen |
| `MERGE_RENDER_THROTTLE_KEY` | Fresh private 64-character lowercase hex key |

Render supplies `RENDER=true`, `RENDER_SERVICE_TYPE=web`, `RENDER_SERVICE_ID=srv-*`,
`RENDER_EXTERNAL_HOSTNAME`, `RENDER_EXTERNAL_URL`, `RENDER_GIT_COMMIT` and, when
applicable, `IS_PULL_REQUEST=false`. Do not invent these locally to connect to a
real database. Auth origin is exactly `https://` plus the assigned hostname.

For the **setup deployment only**, retain PORT/environment/host/runtime password,
**omit** the throttle key, and add all of:

| Name | Source / constraint |
| --- | --- |
| `MERGE_RENDER_SETUP_OWNER` | **`merge_prod_user`** for this existing database; legacy `merge_migrator` is the only other reviewed name; no default |
| `MERGE_RENDER_MIGRATOR_PASSWORD` | Private Render-provided password for the selected owner; historical variable name retained, safe alphabet/length required, distinct from runtime password |
| `MERGE_RENDER_SETUP_ATTEMPT` | Fresh UUID, stored with the reviewed deployment record |
| `MERGE_RENDER_SETUP_COMMIT` | Exact reviewed 40-character lowercase Git SHA, equal to `RENDER_GIT_COMMIT` |
| `MERGE_RENDER_CATALOG_ID` | Fresh explicit hackathon UUID |
| `MERGE_RENDER_CATALOG_NAME` | Approved nonempty name, at most 120 characters |
| `MERGE_RENDER_CATALOG_MIN` | Explicit integer, e.g. `2` |
| `MERGE_RENDER_CATALOG_MAX` | Explicit integer, e.g. `4`; min <= max <= 100 |

Generate runtime password/key privately with Python `secrets.token_hex(32)` for
each distinct value; generate UUIDs with `uuid.uuid4()`. Do not paste generated
values into Git, screenshots, build arguments, command lines, support tickets or
this guide. Save them in the owner's secret manager and service-specific private
variables. No shared environment group or frontend `VITE_*` secret.

No `DATABASE_URL`, `DATABASE_PUBLIC_URL`, `PG*`, `RAILWAY_*`, `VITE_*` or unrelated
`MERGE_*` overrides. The adapter rejects these. The database/user/port are fixed
`merge_prod` / **merge_runtime during normal serve** / 5432. The setup-only
owner is selected explicitly and cannot be passed to the runtime engine. Normal
serve rejects every setup-owner/migrator/setup/catalog input; remove them all
before switching commands. Public region-qualified database hosts,
localhost and DSNs are rejected before connecting. Remove accidental imported
variables rather than weakening validation. If provider-generated credentials or
internal hostname do not meet this contract, stop for adapter review; no fallback.

## Explicit first database setup without a Free shell

These steps are **future owner actions**, not actions taken in this preparation.

1. Review and commit/publish the complete pending scope after offline checks, then
   require fresh public CI at that SHA. Record the full reviewed SHA. Connect that
   GitHub repository in Render only after publication approval.
2. Use the **existing** fresh Free PostgreSQL resource reported above. Confirm it
   is the intended unused production target, never a development/acceptance/retained
   database. Do not recreate it or rename/change its owner. Confirm external access
   is disabled before attaching credentials to the web service; any needed change
   is a separate approved owner action. Keep the existing owner credential private.
   Do not expose a public database port or use the external PSQL command locally.
3. Create the Free Docker web service in the same account/region. In the creation
   form, select the explicit **setup Docker command**, `/ready`, autodeploy off and
   the complete setup-only environment before its first deploy. Pin/check the
   reviewed source commit in the deployment view. Do not select paid hooks/jobs.
4. The explicit setup process validates inputs, resolves only private addresses,
   requires TLS and PostgreSQL 17, checks exact database/user/server identity,
   **current_user equal to MERGE_RENDER_SETUP_OWNER**, actual database ownership,
   non-superuser authority with CREATE ROLE, primary read-write status, and
   acquires a session advisory lock. It requires an empty public schema and no
   existing `merge_runtime` role. It cannot adopt or reset an existing database.
5. It commits one private attempt/SHA claim **before** application DDL. In a separate
   single owned transaction it creates only the restricted runtime login, removes
   PUBLIC database/schema access, grants runtime CONNECT/USAGE, upgrades the existing
   migrations to exact **0006_profiles**, applies the existing table/column/function
   grants, inserts one explicitly supplied hackathon, and marks the claim complete.
   The private deployment schema is authorized to the already verified CURRENT_USER,
   not a fixed owner name or interpolated identifier. Raw runtime password is
   converted to a SCRAM verifier client-side before CREATE
   ROLE; SQL errors/parameters are suppressed by the command. Provider SQL logs may
   still contain credential verifiers and require private access/retention review.
6. It verifies the existing runtime identity, exact revision, public table inventory
   and least privileges with the new runtime credential. Success status is JSON
   containing `state: complete`, `initialized: true`, revision `0006_profiles`, the
   exact reviewed `source_commit`, and the chosen attempt UUID. Inspect the deploy
   log and `/ready` JSON. No password, session or database URI is returned.
7. **A green setup deployment is not a working application.** The setup-only status
   listener returns HTTP 200 at `/ready` even when initializing/failed to avoid a
   platform health restart loop. It serves no React/API and accepts no HTTP command.
   Require the complete JSON success fields, never only the dashboard health badge.
8. On failure/interruption, stop and retain the attempt/log/source record privately.
   A durable incomplete claim blocks every automatic retry, including a new UUID.
   Identical completed claims permit only read-only runtime verification. Unknown,
   mismatched or partial state is refused. There is no claim reset, password change,
   schema cleanup, downgrade or destructive recovery command. Investigation and
   any repair need a separate reviewed operation. Do not repeatedly click deploy.
9. After verified success, remove **all** migrator/setup/catalog variables, add the
   runtime throttle key and change Docker Command to **`python -m app.render.serve`**.
   Save the coherent runtime configuration and deploy the **same reviewed SHA**.
   Keep host/runtime credential/environment/PORT. Runtime rejects privileged inputs.
10. Ordinary startup validates Caddy, verifies the existing runtime DB/revision/grants
    and only then opens Caddy. `/ready` now returns `{"status":"ready"}` or HTTP 503;
    this is real application readiness. It never creates roles/catalog/schema or
    runs migrations. Privileged setup inputs are absent from the runtime process.

### Can merge_prod_user perform setup?

**Conditionally; its name and availability do not prove its permissions.** The
unchanged preflight requires exact `merge_prod` identity/private address/5432,
PostgreSQL17 and TLS, then `rolsuper=false`, `rolcreaterole=true`, database owner
OID equal to the selected account's OID, primary status and read-write transaction.
There is no fallback to another login, SET ROLE, superuser or relaxed role flags.
A syntactically approved name with the wrong connected identity still fails.
`merge_runtime`, postgres/pg_* and unknown names cannot be setup owners.

[PostgreSQL's role attributes](https://www.postgresql.org/docs/17/role-attributes.html)
require CREATE ROLE authority explicitly; Render's credential documentation does
not attest the live flags of this instance. The account **can satisfy** the adapter
if these checks pass, but that has **not** been verified with a database connection.
Missing authority fails before claim/DDL; stop for a separately reviewed provisioning
decision rather than weakening a guard. Runtime keeps its stricter no-elevated-flags,
no-membership, exact0006 and table/column grant checks. Its post-setup verification
uses a newly constructed fixed runtime target and only the runtime password.

If Render's initial user lacks the required ownership/CREATE ROLE/grant authority,
setup stops. This provider capability has **not** been tested; do not make runtime
superuser, use the owner login for the app, broaden database exposure or bypass a
guard. A provider-supported least-privilege provisioning decision is then required.
Direct SQL-created runtime users are not managed by Render's credential UI; retain
that secret securely rather than rotating the default user and assuming it updates
runtime credentials. No test fixtures, seed campaign or benchmark runs in setup.

## HTTPS, proxy identity and SSE verification

Render documents Cloudflare-overwritten `CF-Connecting-IP` for public web services;
leftmost caller-supplied X-Forwarded-For is unsafe. Caddy captures the CF value,
strips forwarding variants, sends exactly one client identity and HTTPS scheme,
and forwards to loopback. Uvicorn's proxy middleware is disabled. Existing app
policy still rejects malformed/multiple IPs, wrong scheme, invalid Origin, missing
CSRF and unauthorized sessions. The public host match requires edge HTTPS/identity;
the narrow GET/HEAD health route checks the assigned host without these headers
so Render's health probe can work. This route exposes only sanitized readiness.

SSE retains authorization, commit-only invalidations, short database reads,
heartbeat/reconnect behavior and bounded 60-second leases. Caddy flush interval is
-1, no compression handler, with a 75-second stream timeout. ASGI concurrency is
64, including long-lived streams; application SSE caps and two-stream/account
limits are unchanged. No 100-client capacity claim. Provider buffering, header
rewrite, cold wake and real browser reconnection remain untested.

After owner-approved runtime deployment, manually verify: HTTPS and exact host;
GET `/ready`; register/login cookie Secure/HttpOnly/SameSite/host scope; Origin and
CSRF failures; forged forwarding header rejection/normal client identity;
authenticated API; two-browser team invalidation and flush/reconnect; logout and
session expiry closing streams; idle sleep/wake. Do not publish a live URL until
these pass. Do not run a load test or large seed on the free production database.

## Resources, costs and availability limits

Owner-confirmed allocations: web **0.1 CPU / 512 MB**, database **0.1 CPU / 256 MB**,
base compute **$0/month** on both Free plans. Verify the creation review still says
Free. Provider quotas apply; build minutes/bandwidth can exhaust allowances or
incur supplementary charges when billing is enabled. No purchase, plan upgrade,
storage autoscaling, credit-card change or uptime-bot is part of this preparation.

Resource choices: one API worker, runtime pool **2 + 0 overflow**, ASGI concurrency
64, Caddy `GOMEMLIMIT=64MiB`/`GOMAXPROCS=1`, Python `MALLOC_ARENA_MAX=2`; no Node server.
GOMEMLIMIT is a soft Go heap target, **not** a process/container memory ceiling.
There are two Python processes (supervisor and API) plus Caddy. Existing Argon2id
uses 19,456 KiB per hash and at most two concurrent hash workers (~38 MiB hash
working memory before other overhead). Security settings are preserved. Startup,
Linux peak RSS, cgroup/OOM behavior and CPU throttling have not been measured;
512 MB fit and latency are **not certified**. Stop on OOM/failed readiness and
review measured usage rather than weakening hashing or adding workers.

Free web idle sleep begins after 15 minutes without inbound traffic; waking takes
about a minute. Restarts and deploys can drop SSE; clients reconnect/refetch. The
filesystem is ephemeral, so no app data, certificates or setup success marker is
stored there. Free provides 750 workspace web hours/month, no shell/SSH, one-off
jobs, persistent disk or multi-instance scale. It can **send** private requests to
same-region Postgres; it cannot **receive** private service traffic.

Free Postgres is limited to **1 GB**, expires after **30 days**, and has no managed
backups; expiry makes it inaccessible. After a further 14-day upgrade grace period
Render deletes its data. Record creation/expiry and plan a separately approved
private export/hosting transition well before expiry. Do not treat free hosting as
a permanent portfolio URL or backup strategy. No automatic paid upgrade or export
operation is implemented here. Database restarts/maintenance may occur at any time.

## Rollback and future migrations

Automatic deployments remain off. Roll back only to a previously verified
**Render-capable** image/SHA compatible with the same `0006_profiles` schema and
runtime settings, after checking the dashboard's retained deployment limit.
Baseline `bb60ab3` has no Render adapter and is not a valid Render rollback image.
An application rollback never invokes setup, changes passwords or downgrades the
database. A failed first deployment has no verified previous image: stop exposure,
retain diagnostics and investigate without resetting the database.

This adapter performs only fresh 0006 initialization, not future migrations or
repairs. Existing VPS/Railway operations are not approved substitutes against a
Render database. A future revision needs a separately reviewed explicit owned
migration runner, maintenance/backup plan and source-compatible rollback before
execution. Normal `serve` always requires exact 0006 and never migrates on restart.

## Offline verification and pending-file inventory

See [TESTING.md](TESTING.md) for actual offline commands/results and
[the documentation audit](archive/DOCUMENTATION_AUDIT.md) for the complete release
inventory. The owner authorized a local release commit after validation; push and
cloud actions require separate approval. No native Docker/Caddy binary is available
on the review host. Offline contracts do not certify native Caddy schema, binary
compatibility, Linux startup, 512 MB operation, managed grants, provider Blueprint
acceptance, public HTTPS/header/SSE behavior or new hosted CI.

Owner explanation: normal serve cannot initialize a database or select the owner
account. Set MERGE_RENDER_SETUP_OWNER=merge_prod_user only for explicit setup;
remove it and the owner password before normal serve. Explicit setup
binds a fresh attempt to the reviewed SHA, commits a claim before owned DDL and
blocks unattended recovery after interruption. Its HTTP endpoint is status-only.
For an offline exercise, change the synthetic PORT in the packaging test to a
valid unprivileged port, then to 8000, and explain acceptance versus rejection.
Run only the regression test; no database or server is needed.

## Provider sources checked 15 November 2026

- [Free plans](https://render.com/docs/free): idle/expiry/quotas/private connectivity and unsupported Free features.
- [Postgres creation and connections](https://render.com/docs/postgresql-creating-connecting): immutable name/user, same-region private host, TLS require and external-access control.
- [Blueprint reference](https://render.com/docs/blueprint-spec): Free plans, port/env/database fields, manual deploy and external allowlist.
- [Environment variables](https://render.com/docs/environment-variables): assigned hostname, service identity, source SHA and PORT.
- [Deploys](https://render.com/docs/deploys): Docker command override and paid-only pre-deploy commands.
- [Health checks](https://render.com/docs/health-checks): GET/host, five-second probe and deployment readiness.
- [Public client IP guidance](https://render.com/articles/host-pocketbase-on-render): CF-Connecting-IP overwrite, unsafe leftmost XFF.
- [SSE guidance](https://render.com/articles/sse-vs-websockets-llm-streaming): streaming/reconnection patterns; not acceptance evidence for this app.
- [Database credentials](https://render.com/docs/postgresql-credentials): direct SQL users are outside dashboard credential management.
- [PostgreSQL17 schema authorization](https://www.postgresql.org/docs/17/sql-createschema.html): CURRENT_USER ownership without identifier interpolation.
- [PostgreSQL17 role attributes](https://www.postgresql.org/docs/17/role-attributes.html): explicit CREATEROLE and privileged-role semantics.

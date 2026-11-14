# Production proposal and owner runbook — NOT DEPLOYED

This is preparation, not permission to execute. No live PostgreSQL, migration,
service/browser, load, remote, publication or deployment action ran in Batch C.
Use [SUBMISSION.md](SUBMISSION.md) for dependency order and approval boundaries;
Batch B [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md) remains unchanged.

## Topology and prerequisites

Recommend a Docker-capable **Ubuntu24.04 LTS Linux VPS**, provider-neutral, with
a public domain pointing directly to it. Initial planning size:2vCPU/4GB RAM and
adequate persistent SSD/backup storage; this is not a measured capacity guarantee
or verified provider/free-tier offer. Owner must confirm cost, region, resources,
patching and deadlines before purchase. No provider/API is contacted here.

```text
Browser --HTTPS:443--> Caddy: compiled React + same-origin /auth and /api
                        | private edge network, one trusted proxy
                        +--> FastAPI:8000, one worker
                                  | internal-only database network
                                  +--> PostgreSQL17:5432 / merge_prod
```

Only Caddy publishes80/443. DNS must have correct A/AAAA records; remove an
unusable AAAA record before ACME issuance. No CDN/second reverse proxy is assumed.
Cloudflare proxying, managed-ingress chains and alternate subnets need a separately
reviewed peer policy; never add wildcard proxy trust. Firewall exposes80/443 and
owner-restricted SSH only. Check Docker firewall behavior independently, not just
UFW. Do not expose API5432/8000 or Docker's control socket.

Fixed Docker subnets:edge172.30.240.0/29, database172.30.241.0/29. Caddy is
172.30.240.2 (sole trusted /32); PostgreSQL is172.30.241.3. Check host/VPN overlap
before launch. Internal PostgreSQL TCP is unencrypted on this single trusted
host; no public DB route. Moving DB to another host requires TLS verification and
a new reviewed configuration. Do not modify these addresses in only one file.

Docker Engine/Compose v2, psql for separate local acceptance, Python3.11 and Node
22.15.0/npm10.9.2 are prerequisites. Images currently use moving Python3.11,
Caddy2 and PostgreSQL17 tags; Node22.15.0 is pinned to the tested frontend toolchain.
Before release, review current advisories and resolve/pin immutable digests after
approved pulls. No image build/pull, supply-chain scan or native Docker/Caddy
validation occurred here (binaries unavailable). Python/OS/tzdata image contents
and cross-platform locked dependency installation remain rehearsal gates.

## Configuration and secret separation

| Input | Meaning |
| --- | --- |
|MERGE_PROD_ORIGIN|Exact lower-case public HTTPS origin, no path/port; e.g. your real owned domain. Placeholder/reserved/loopback origins reject.|
|MERGE_IMAGE_TAG|Reviewed immutable release tag for both local API/web images; operator variable only, not passed into API.|
|deploy/private/runtime_db_password|Random private DB runtime password, mounted only into API/bootstrap.|
|deploy/private/migrator_db_password|Distinct migration password, mounted only into operation containers.|
|deploy/private/admin_db_password|Distinct PostgreSQL bootstrap/admin password; never mounted into API.|
|deploy/private/throttle_key|Private32-byte hex key shared across API restarts; changing it resets throttle partitions.|
|deploy/private/caddy.json|Generated public hostname/proxy configuration, mounted read-only into Caddy.|

Production loads no dotenv/ordinary Settings and accepts no arbitrary DATABASE_URL,
PG* target or MERGE_AUTH/DB/test/release override. Runtime always uses
postgres:5432/merge_prod as merge_runtime; migrator always merge_migrator.
Every new SQLAlchemy connection checks actual server address/database/role,
unprivileged flags/no role memberships, READ COMMITTED, non-autocommit, exact
revision and5s lock/15s statement bounds. Runtime has schema USAGE but no CREATE.
Readiness also checks table inventory and intended table/column grants. This is
not a comprehensive schema-drift or compromise detector.

API logs use a fixed formatter that discards exception/message values; no access
logging or SQL parameter logging. CLI failures print fixed errors and metadata,
not tracebacks/configuration. Caddy request access/error loggers are excluded;
containers rotate local logs. This sacrifices diagnostics to protect credentials;
owner must review host/daemon/APM/crash-dump policy and avoid request-header capture.
Never run compose config with secrets expanded manually or dump process env.

## Approval 1: source, images and new local secret files

Only after owner-approved commit/publication, establish a reviewed clean checkout
on the VPS. Do not deploy a tag bearing old HEAD while it contains uncommitted
A/B/C changes. Capture clean Git revision plus image IDs/digests in a private
release record. Do not put credentials in CLI arguments, shell history/transcripts
or public Actions artifacts. Commands below are **Linux bash**, from repo root.
Replace REAL_OWNED_HOST and REVIEWED_TAG; no default live origin is supplied.

```bash
set -euo pipefail
export MERGE_PROD_ORIGIN='https://REAL_OWNED_HOST'
export MERGE_IMAGE_TAG='REVIEWED_TAG'
```

The checker must run with backend on the module path; use this exact root form:

```bash
(cd backend && .venv/bin/python -m app.production.check)
```

For actual new-file creation, run from backend so imports resolve:

```bash
(cd backend && sudo .venv/bin/python -m app.production.prepare \
  --confirm-new-secrets --origin "$MERGE_PROD_ORIGIN")
docker compose -f deploy/compose.json config --quiet
docker compose -f deploy/compose.json build api web
docker image inspect --format '{{.Id}}' "merge-api:$MERGE_IMAGE_TAG" "merge-web:$MERGE_IMAGE_TAG"
docker compose -f deploy/compose.json run --rm --no-deps --entrypoint caddy web \
  validate --config /etc/caddy/config.json
```

The helper is Linux-root-only, creates only a previously absent deploy/private,
generates secrets without printing them, and assigns secret files0400/UID10001
(the API image user); the private directory is0700. Compose file-backed secrets
preserve host ownership, so Docker uid/mode settings alone would not solve access.
Native validation and ownership must be checked in rehearsal. No existing file
is overwritten or removed. A partial preparation requires owner inspection, not
automatic cleanup/retry. .gitignore/.dockerignore exclude all private inputs and
test reports/build artifacts. Builds execute npm ci/build and the locked Python
install; no source credential enters an image layer.

## Approval 2: fresh DB bootstrap and explicit migrations

Use an isolated rehearsal VPS first; fixed subnets/names cannot coexist with a
second copy on the same host. PostgreSQL container initialization only creates
the named database/administrator on a **new** persistent volume. Ordinary API
startup cannot create tables or roles. Never mount an unknown existing volume;
POSTGRES_* values do not reconfigure credentials in an existing PGDATA.

After reviewing the exact new-volume/role/DDL scope:

```bash
docker compose -f deploy/compose.json up -d postgres
docker compose -f deploy/compose.json run --rm --no-deps bootstrap --confirm-new-merge-prod
docker compose -f deploy/compose.json run --rm --no-deps migrate prepare --confirm-merge-prod
docker compose -f deploy/compose.json run --rm --no-deps migrate migrate --confirm-merge-prod
docker compose -f deploy/compose.json run --rm --no-deps migrate verify --confirm-merge-prod
```

Wait for PostgreSQL health before bootstrap. Stop on any nonzero/incomplete
action; preserve volume and sanitized JSON/stdout/native exit. Bootstrap connects
only to internal merge_prod as postgres, refuses existing app roles/public objects,
and creates runtime/migrator roles and new DB/schema grants in one transaction.
No existing role/password is changed. Local Unix socket peer authentication is
restricted to the trusted container OS identity; TCP uses SCRAM.

Prepare accepts a wholly empty public schema and migrates explicitly through0005.
Migrate accepts exact0005 only and upgrades to0006, reusing Batch B's12-table
SHARE-lock/content fingerprints in the same owned transaction as DDL/grants. No
old data is updated/backfilled/deleted. Failure rolls back; no downgrade/cleanup.
0006 is the only current Alembic head and remains unapplied by this task.
The separate production_alembic environment requires this owned transaction and
production migrator identity. Existing test/release targets never accept production.

The runtime receives explicit SELECT/INSERT/UPDATE rights where services need
them, membership DELETE, SELECT/INSERT-only audit/outbox, no TRUNCATE/DDL, and
SELECT-only Alembic state. Column UPDATE(id/user_id) on hackathons/users/credentials
is needed by existing SELECT FOR SHARE/NO KEY UPDATE locks, not new edit routes.
Triggers remain security-invoker; the runtime can execute them. These restricted
grants are **not live verified**; exercise register/login/create/request/invite/
leave/remove/profile/SSE as this role before public launch.

Seed no benchmark/retained-test data into production. To populate an otherwise
empty catalog, separately approve one explicit new hackathon ID/name/size:

```bash
docker compose -f deploy/compose.json run --rm --no-deps migrate catalog --confirm-merge-prod \
  --id OWNER_APPROVED_UUID --name 'Owner-approved demo hackathon' --min-size 2 --max-size 4
```

No admin UI or automatic catalog insertion exists. Duplicate IDs fail; no upsert
or retry changes an existing event. Participant/team changes use authenticated
application transactions only. Retain metadata-only operation outputs and source/
image hashes; owner independently records native exit codes. Never publish DB dumps.

## Approval 3: public launch and actual HTTPS/browser smoke

```bash
docker compose -f deploy/compose.json up -d api
docker compose -f deploy/compose.json ps
docker compose -f deploy/compose.json up -d web
```

API lifespan checks identity/exact0006/table inventory/grants before readiness.
It disposes its engine on failure/shutdown. /health is process liveness only;
/ready performs bounded real DB/privilege checks for internal Docker health and
is404 at Caddy. PostgreSQL pg_isready is not application-schema readiness. App
startup fails closed on old/unexpected revision. Docker restart does not run
migrations and does not automatically restart an unhealthy-but-running process;
owner monitoring/alerting is required.

Caddy serves compiled hashed assets (immutable cache) and SPA fallback (revalidate),
routes /auth and /api without stripping prefixes, overwrites one XFF/XFP, removes
Forwarded/X-Real-IP, and uses no Uvicorn proxy middleware. No response compression
is configured. SSE flush_interval=-1,75s stream ceiling and no short body timeout
permit existing60s leases/reconnect; API send deadline10s and subscriber caps stay
unchanged. CSP allows same-origin scripts/connections; inline styles are needed
by existing capacity bars. HSTS is enabled after domain launch. API no-store/private
headers remain unchanged. Proxy/TLS buffering/timeout behavior is not proven offline.

Owner-approved smoke: public valid TLS and HTTP->HTTPS; React asset/deep-link
load; register/login/Secure __Host cookie/no Domain; CSRF and foreign Origin reject;
spoofed forwarding reject/overwrite; named request/invite flows; full/unauthorized
safe failures; lifecycle succession/deletion; profile CAS/ranking explanations;
two separate authenticated clients update without reload and reconnect after a
short outage; mobile320/375/768px, keyboard-only, focus/status, long names and zoom.
Use fresh approved accounts; registration throttles limit shared-IP demos. Do not
reuse legacy manifests or expose tokens in DevTools/video. Retain URL/revision/
image/time/environment plus sanitized evidence. No load against this deployment.

VPS has no configured idle sleep; reboot, PG recovery, image pull and first ACME
issuance create downtime/cold starts. No availability SLA or p95 claim. One worker
has64 SSE slots and pool5+5 connections;100-VU performance must be measured on the
approved isolated benchmark target. Retained outbox/history and throttles/sessions
grow; no automatic retention/fixture deletion policy is installed.

## Shutdown, backups and rollback

Before changes with existing data, approve an encrypted off-host backup and restore
drill; volumes alone are not backups. A reviewed Linux example (private output):

```bash
umask 077
docker compose -f deploy/compose.json exec -T --user postgres postgres \
  pg_dump -U postgres -d merge_prod -Fc > /OWNER_PRIVATE_BACKUP_PATH/merge-prod.dump
```

Check exit/status and independently test restoration in an isolated approved
environment. Include private role/secret recovery and Caddy certificate volume
backup in the owner plan; never commit/upload the dump or passwords. No restore,
pg_restore --clean, volume removal or data reset command is authorized/prepared.

On failure stop ingress first, then API; retain DB/volumes/logs:

```bash
docker compose -f deploy/compose.json stop web api
```

Caddy has25s grace, API20s graceful shutdown under30s container stop, PG60s if
explicitly stopped. In-flight SSE closes and clients reconnect/reset; uncertain
mutations still need their original key. Never use down -v, prune, rm volumes or
automatic downgrade. For a subsequent release, stop ingress/API, keep DB schema0006
and restore the last owner-reviewed compatible API+web image pair/tag, then verify
readiness/smoke before ingress. First deployment has no known-good production image;
stop and fix forward. The old local baseline is not a deployable production rollback.
Ambiguous COMMIT/partial initialization requires approved read-only inspection,
not blind retry. DNS/secrets/certificate changes and disaster recovery are separate
owner decisions. All live gates and missing evidence remain in SUBMISSION.md.

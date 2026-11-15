# Deployment

**Public HTTPS deployment is not verified. No working live URL is recorded.**
The production package has offline contract checks; native images, database-role
grants, initialization/migration, proxy behavior and TLS need a live rehearsal.

```text
Browser --HTTPS--> Caddy (React assets, /auth, /api and SSE)
                     | private edge network
                     v
                 FastAPI (one worker)
                     | private database network
                     v
                 PostgreSQL 17 / merge_prod
```

Only Caddy publishes ports 80/443. The package fixes one trusted proxy, private
subnets, persistent PostgreSQL/certificate volumes and separate runtime/migrator
identities. Startup checks readiness and never migrates. `/health` is liveness;
`/ready` checks database/configuration and is not publicly proxied.

## Package and prerequisites

| Asset | Purpose |
| --- | --- |
| [compose.json](../deploy/compose.json) | Services, networks, volumes, health checks and secret mounts |
| [Dockerfile.api](../deploy/Dockerfile.api) | Non-root Python API and explicit operations entry points |
| [Dockerfile.web](../deploy/Dockerfile.web) | Locked frontend build and Caddy static server |
| [caddy.template.json](../deploy/caddy.template.json) | Same-origin API/SSE proxy and security policy |
| [Production checker](../backend/app/production/check.py) | Offline topology/security contract validation |

A Linux Docker/Compose host, reviewed image tag, owned DNS name, reachable 80/443,
non-overlapping subnets, private mounted secrets and an explicit backup/restore
plan are prerequisites. No credential values belong in Git, frontend variables,
command arguments or public logs. `deploy/private/` is excluded from Git/builds.

## Execution order

The full [production runbook](PRODUCTION.md) is the sole detailed launch/rollback
procedure. Review its exact commands and state-changing scope before execution:

1. Prepare new secret files, build reviewed images, validate Compose/Caddy natively.
2. Initialize a fresh persistent database namespace and separate roles.
3. Run explicit owned migrations to exact `0006_profiles`; verify preservation/grants.
4. Prepare a separately approved catalog entry, then start API and ingress.
5. Verify public TLS, authentication/CSRF, membership flows, two-client SSE,
   reconnect, phone and keyboard behavior. Retain sanitized release evidence.
6. Rehearse encrypted backup/restore and compatible image rollback.

The [submission checklist](SUBMISSION.md) tracks missing public artifacts.
[Release validation](RELEASE_VALIDATION.md) covers isolated seed/load testing;
retained tests and production must never be used as benchmark targets. This task
ran no Docker build, migration, database access, startup or deployment.

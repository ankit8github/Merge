# Deployment

**Current demonstration target: Render Free. Deployment has not been executed.**
No verified public application URL exists. The GitHub repository is published;
source publication and public application deployment are separate gates.

Use the [Render runbook](RENDER.md) as the canonical dashboard/environment,
private PostgreSQL 17, explicit setup, launch, smoke-check and rollback procedure.
It covers one public Caddy/React service, one loopback FastAPI worker and a private
managed database. Ordinary startup verifies exact 0006 and never migrates.
The root [render.yaml](../render.yaml) records the runtime Blueprint contract;
first initialization must use the separate owner-selected setup deployment.

Render Free's cold starts, resource limits and 30-day database expiry make this a
temporary demonstration target. Never load-test or scale-seed the free production
service. No paid upgrade, cloud action or automatic recovery is implied.

## Retained alternatives

- [Railway runbook](RAILWAY.md): previously evaluated cloud adapter, superseded as
  the immediate target. Its source helpers remain Render dependencies.
- [VPS runbook](PRODUCTION.md): separate Docker Compose, Caddy-owned HTTPS and
  persistent-volume model. Retained source/configuration remains unchanged.

Choose one platform's runbook. Do not mix credentials, database guards, hostname
rules, proxy trust or initialization commands across platforms.

## Release order

Review and commit locally, then obtain separate approval to publish. Require new
CI for that exact release commit. Only after deployment approval follow Render's
explicit initialization, runtime switch and live HTTPS/auth/SSE checks. Green
setup liveness is not application readiness. Record actual source/image identifiers
and sanitized results; publish the live URL only after verification.

[Testing](TESTING.md) records offline results and pending native gates;
[submission](SUBMISSION.md) tracks required deliverables. Seed/load reproduction
belongs to [isolated release validation](RELEASE_VALIDATION.md), never production
or retained acceptance targets. Complete file decisions: [documentation audit](archive/DOCUMENTATION_AUDIT.md).

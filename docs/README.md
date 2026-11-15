# Documentation

Start with the [project homepage](../README.md). These are the primary guides:

| Guide | Purpose |
| --- | --- |
| [Architecture](ARCHITECTURE.md) | Current boundaries, invariants, security and realtime design |
| [Setup](SETUP.md) | Dependencies and explicit local database/API/frontend steps |
| [Testing](TESTING.md) | Reproducible offline checks, evidence scope and pending live gates |
| [Deployment](DEPLOYMENT.md) | Selected Render target and retained platform alternatives |
| [Render runbook](RENDER.md) | Exact dashboard settings, private DB setup and rollback |
| [One-page design](DESIGN_ONE_PAGE.md) | Submission design source; export pagination remains unverified |
| [Demo](DEMO.md) | Five-minute walkthrough plan and privacy rules |
| [Requirements](REQUIREMENTS.md) | Organizer criteria and required submission artifacts |
| [Submission](SUBMISSION.md) | Current artifact status and delivery order |
| [Progress](PROGRESS.md) | Verified current state and missing work |
| [Decisions](DECISIONS.md) | Architectural rationale and chronology |

## Technical contracts

These documents preserve details needed to defend, maintain and reproduce the code.

- Data/transactions: [schema](SCHEMA.md), [services](TEAM_SERVICES.md),
  [mutations](TEAM_MUTATIONS.md), [idempotency](IDEMPOTENCY.md), [retries](TRANSACTION_RETRY.md).
- Security: [auth storage](AUTH_SCHEMA.md), [credentials](CREDENTIAL_SERVICES.md),
  [sessions](SESSION_SERVICES.md), [HTTP policy](HTTP_AUTH.md), [throttling](AUTH_THROTTLING.md).
- Features: [discovery](READ_API.md), [team creation](TEAM_API.md), [requests](ADMISSION.md),
  [invitations](INVITATIONS.md), [lifecycle](LIFECYCLE.md), [matching](RANKING.md),
  [SSE](REALTIME.md), [frontend](FRONTEND.md).
- Reproduction: [database guards](TEST_DATABASE.md), [release/load tooling](RELEASE_VALIDATION.md),
  [race evidence](G1_ACCEPTANCE.md), [browser harness](BROWSER_ACCEPTANCE.md),
  [integrated preparation](INTEGRATED_ACCEPTANCE.md), [independent host](INTEGRATED_HOST.md).
- Alternate deployment: [Railway](RAILWAY.md), [VPS](PRODUCTION.md).

Older component checkpoints retain their dated scope. Follow current status and
the named target guard before considering historical commands. Consumed campaigns
and historical certificates cannot be reused or recertified by documentation edits.

## History and file decisions

[Archive index](archive/README.md) groups development reviews, the earlier proposal
and progress journal. [Documentation audit](archive/DOCUMENTATION_AUDIT.md) records
every retained, consolidated and removed Markdown path and its reference checks.
Private diagnostics and generated certification artifacts remain ignored locally.

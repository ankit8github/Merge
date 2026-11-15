# Documentation

Start with [the project homepage](../README.md), then choose the guide for the task.
Public guides summarize the current implementation; detailed component contracts
retain engineering rationale and exact safety/reproduction requirements.

| Guide | Purpose |
| --- | --- |
| [SETUP.md](SETUP.md) | Dependencies, fresh development database, explicit migration, API/frontend startup |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and links to concrete contracts |
| [TESTING.md](TESTING.md) | Offline commands, evidence scope, CI networking and outstanding live checks |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production overview and full runbook entry point |
| [DESIGN_ONE_PAGE.md](DESIGN_ONE_PAGE.md) | Submission design source; exported pagination remains unverified |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Captured organizer requirements and acceptance criteria |
| [DECISIONS.md](DECISIONS.md) | Approved refinements and earlier proposals, with chronology |

## Component contracts

- Data and mutations: [schema](SCHEMA.md), [team services](TEAM_SERVICES.md),
  [idempotency](IDEMPOTENCY.md), [atomic mutations](TEAM_MUTATIONS.md),
  [transaction retries](TRANSACTION_RETRY.md).
- Authentication: [storage](AUTH_SCHEMA.md), [credentials](CREDENTIAL_SERVICES.md),
  [sessions](SESSION_SERVICES.md), [HTTP boundary](HTTP_AUTH.md),
  [durable throttling](AUTH_THROTTLING.md).
- Product APIs/UI: [read API](READ_API.md), [team creation](TEAM_API.md),
  [admission](ADMISSION.md), [invitations](INVITATIONS.md),
  [lifecycle](LIFECYCLE.md), [ranking](RANKING.md), [SSE](REALTIME.md),
  [frontend](FRONTEND.md).

## Acceptance, operations and submission

- [Test database guards](TEST_DATABASE.md), [release validation](RELEASE_VALIDATION.md),
  [G1 race evidence](G1_ACCEPTANCE.md).
- [Browser acceptance](BROWSER_ACCEPTANCE.md), [integrated acceptance preparation](INTEGRATED_ACCEPTANCE.md),
  [independent integrated host](INTEGRATED_HOST.md).
- [Full production runbook](PRODUCTION.md), [submission checklist](SUBMISSION.md),
  [walkthrough script](DEMO.md).
- [Verified progress](PROGRESS.md) and [historical review catalog](archive/README.md).

Older component headings include milestone names and proposed/unexecuted steps.
Read their latest dated refinements and the current testing summary before using
historical commands. They are retained for owner understanding and evidence
provenance; they are not instructions to rerun a consumed acceptance scope.

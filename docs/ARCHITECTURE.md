# Architecture

Merge is a modular monolith: React/TypeScript, FastAPI/Pydantic and PostgreSQL 17.
The database owns membership, capacity, leadership, sessions, idempotency and
committed audit/outbox state. No process-local mutex or browser state grants a seat.
Current evidence and remaining gates are in [PROGRESS.md](PROGRESS.md).

## Deployment boundary

```text
Browser -- Render-managed HTTPS --> Caddy on $PORT
                                     | React production assets
                                     | same-origin /auth, /api and SSE
                                     v
                              FastAPI 127.0.0.1:8000
                              one worker; pool 2, no overflow
                                     | private same-region TLS
                                     v
                              PostgreSQL 17 / merge_prod
```

[Render Free](RENDER.md) is the selected demonstration target, prepared but not
live verified. Caddy is the only public application listener. Render owns HTTPS;
Caddy matches the assigned hostname, replaces forwarding headers and preserves
stream flushing. The existing authentication boundary trusts only loopback,
requires the exact HTTPS Origin, and retains secure host-only cookies and CSRF.

Runtime credentials cannot migrate. Default startup validates configuration,
private database identity, least privileges, exact `0006_profiles` revision and
schema readiness. A separate, explicitly selected fresh setup command owns DDL.
Its private attempt/SHA claim blocks unattended retry after interruption. It has
no HTTP command endpoint. Exact setup, status meanings and rollback: [RENDER.md](RENDER.md).

The Render adapter reuses Railway's connection guard and process helpers, plus
production constants, grants and readiness. Those sources are dependencies, not
cleanup candidates. [Railway](RAILWAY.md) and the [VPS package](PRODUCTION.md) are
retained alternatives, superseded only as the immediate hosting choice. Their
network/credential models must not be mixed. No deployment is certified.

## Data and transaction invariants

Membership is keyed by `(hackathon_id, user_id)`. Scoped foreign keys and deferred
final-state checks protect capacity, live-team membership and valid leadership.
Pending requests reserve no seats. A final departure retires the team while
preserving audit history. [Schema](SCHEMA.md) defines the database constraints.

Mutations reserve the caller/operation/idempotency key and command fingerprint,
then lock the hackathon, affected users in UUID order, team and auxiliary request
or invitation. They recheck authorization, eligibility and actual membership
under lock. Domain changes, team version, audit/outbox and canonical stored reply
commit or roll back together. Duplicate commands replay the stored outcome;
mismatched reuse is rejected. Bounded retries retain ownership and command data;
uncertain COMMIT needs reconciliation. See [mutations](TEAM_MUTATIONS.md),
[idempotency](IDEMPOTENCY.md), [retries](TRANSACTION_RETRY.md),
[admission](ADMISSION.md), [invitations](INVITATIONS.md) and [lifecycle](LIFECYCLE.md).

## Authentication and application boundary

Argon2id protects passwords. Opaque database sessions use token hashes, absolute
expiry and server-side authorization. Secure HttpOnly host-only cookies, exact
Origin/transport checks, CSRF and durable account/IP throttles protect browser
commands. Client selectors never create authority. Credential/session transactions
remain separate from domain mutations. [HTTP authentication](HTTP_AUTH.md),
[sessions](SESSION_SERVICES.md) and [throttling](AUTH_THROTTLING.md) specify the rules.

React provides discovery, profiles, team creation, requests, invitations,
membership lifecycle and explained recommendations. Account/scope changes fence
stale responses and close streams. Unknown mutation delivery requires recovery;
UI refresh never silently replays a command. [Frontend](FRONTEND.md) retains the
component contracts and failure cases.

## Realtime and deterministic matching

Authenticated SSE reads committed subscriber-visible outbox counts in short
read-only transactions; no transaction spans a network wait. Frames invalidate
views without private domain payload. Reconnect refetches canonical state.
Session/scope checks, subscriber caps, leases and send deadlines bound resources.
This provides neither ordered nor exactly-once delivery. [Realtime](REALTIME.md)
records the protocol and unmeasured retained-history cost.

Ranking uses exact deterministic fractions: 70 points for candidate skill novelty
and 30 for average time-zone working-hour overlap, with UUID tie breaks. Candidates
must be opted in and eligible in scope; only current leaders may read suggestions.
A suggestion never grants admission. [Ranking](RANKING.md) specifies pagination,
privacy, assumptions and limits.

## Verification and design history

Offline tests cover contracts and refusal paths. Real PostgreSQL race/grant tests,
public HTTPS, integrated browser behavior and measured load need their own evidence.
Render Free's cold starts, small resources and expiring database limit availability;
512 MB fit is unmeasured. [Testing](TESTING.md) separates current checks from prior
certificates. [Requirements](REQUIREMENTS.md), [decisions](DECISIONS.md) and the
[one-page design](DESIGN_ONE_PAGE.md) explain the submission scope.

The superseded proposal/API sketches are preserved in
[architecture history](archive/ARCHITECTURE_HISTORY.md). Historical commands do not
authorize database access or recertify an old campaign.

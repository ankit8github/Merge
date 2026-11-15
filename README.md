# Merge

### Hackathon Team Formation Platform

Merge helps hackathon participants find teammates and form teams without
oversubscribing seats or assigning a participant to two teams in the same event.
PostgreSQL transactions and constraints govern admission, while React provides
team discovery, invitations, membership management and explained recommendations.

Built for [Hack4Hack Crew Hiring Challenge 2026, PS1](https://hack4hack.com/hackathons/hack4hack-crew-hiring-challenge-2026-tp3m).
**Current status:** local release candidate. Integrated browser acceptance,
measured load and public HTTPS deployment are outstanding. The owner reports all
five Actions jobs passed for `bb60ab3`. The deployment adapters are published at
`424f29c`; the setup-owner compatibility patch is verified offline and awaits
review/publication and new CI.

## Overview

Participants register, sign in, choose a hackathon and browse teams. They can
create a team, request admission or redeem a recipient-bound invitation. Leaders
review requests, invite suggested teammates and manage membership. Members can
leave; leadership transfers deterministically, and the final departure retires
the team while preserving its audit history.

## Key features

- **Authentication and profiles:** password authentication, database sessions,
  validated skills/time zones and explicit discovery opt-in.
- **Hackathon discovery:** paginated events and teams, capacity information and
  exact UUID lookup.
- **Team formation:** idempotent creation, leader-approved join requests and
  expiring recipient-bound invitations.
- **Membership lifecycle:** leave, leader removal, automatic succession and
  last-member soft deletion.
- **Explainable recommendations:** deterministic skill complementarity and time
  zone overlap scores, visible to the current team leader.
- **Realtime updates:** authenticated SSE invalidates affected views so clients
  refetch canonical state after committed changes and reconnects.

## Technology stack

| Area | Implementation |
| --- | --- |
| Frontend | React 19, TypeScript 5.8, Vite 6 |
| API | Python 3.11, FastAPI, Pydantic 2, Uvicorn |
| Persistence | PostgreSQL 17, SQLAlchemy 2, psycopg 3, Alembic |
| Security | Argon2id, opaque cookie sessions, CSRF/Origin checks, durable throttles |
| Verification | pytest, Vitest, Testing Library, browser acceptance harnesses, k6 tooling |
| Delivery | GitHub Actions; Docker Compose and Caddy production package |

Exact versions are pinned in [backend dependencies](backend/requirements.lock)
and the [frontend lockfile](frontend/package-lock.json).

## Architecture

```text
React / TypeScript
       | same-origin HTTPS + SSE
       v
Caddy: static assets + reverse proxy       (planned production entry point)
       |
       v
FastAPI modular monolith
       | short, owned transactions
       v
PostgreSQL: membership + sessions + idempotency + audit/outbox
```

Production adapters use one API worker, private database networking and separate
runtime/migration credentials. The VPS package uses persistent volumes; Render
uses managed PostgreSQL and an ephemeral web filesystem. It has been checked offline;
images, restricted database grants and HTTPS behavior require live verification.
See [architecture](docs/ARCHITECTURE.md) and [deployment](docs/DEPLOYMENT.md).

## Engineering highlights

- **Transaction-safe admission.** Active membership is keyed by
  `(hackathon_id, user_id)`. Scoped foreign keys and deferred final-state checks
  backstop capacity, leadership and membership consistency.
- **Deterministic lock ordering.** Mutations reserve the idempotency key, lock the
  hackathon, affected users in UUID order, then the team and request/invitation.
  Authorization and capacity are rechecked under lock. Pending requests reserve
  no seats.
- **Idempotency and replay protection.** Caller/operation/key plus a command
  fingerprint identify a mutation. Successful replies commit with the effect;
  mismatched reuse is rejected. Bounded retries preserve the original command,
  and an uncertain commit requires reconciliation.
- **Consistent audit/outbox.** Membership, team version, audit record, outbox event
  and stored reply commit or roll back together.
- **Authorized SSE invalidation.** Short read-only polls inspect committed,
  subscriber-visible outbox counts. Session and scope checks protect private
  signals; frames carry no private domain payload. Reconnect refetches state.
- **Explainable ranking.** Exact deterministic scores combine skill novelty
  (70 points) and assumed working-hour overlap (30 points), with UUID tie breaks
  and bounded snapshot pages. Recommendations never grant membership.

Detailed contracts: [transactions](docs/TEAM_MUTATIONS.md),
[retries](docs/TRANSACTION_RETRY.md), [SSE](docs/REALTIME.md),
[matching](docs/RANKING.md).

## Getting started

Prerequisites: Git, Python **3.11**, Node **22.15.0**, npm **10.9.2**.
PostgreSQL **17** is needed for application use and database acceptance, but not
for the default offline suite. Commands below use PowerShell from the repository
root; replace the Python path with `backend/.venv/bin/python` on Linux.

```powershell
git clone https://github.com/ankit8github/Merge.git
Set-Location Merge
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
npm.cmd --prefix frontend ci
```

Then follow [local setup](docs/SETUP.md) for the separate steps:

1. Provision a fresh local database and migrate to an explicit revision.
2. Configure the ignored backend environment and authentication settings.
3. Start the controlled API launcher and the Vite frontend in separate terminals.

Database setup changes local state and is deliberately separate from dependency
installation. Retained acceptance databases must never be reused as development
or benchmark targets. Production uses the separate [deployment runbook](docs/DEPLOYMENT.md).

## Testing and verification

Run the database-free checks with existing dependencies:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -B -m pytest -q -m 'not database' --tb=short
.\.venv\Scripts\python.exe -B -m app.production.check
Set-Location ../frontend
npm.cmd test -- --reporter=dot --maxWorkers=1
npm.cmd run build
```

Latest local verification on Windows: **2,213 backend tests passed** (32 database
cases deselected), **434 frontend tests passed** across 18 files with one worker,
and the **TypeScript/production build passed**. These checks used existing locked
dependencies. Exact commands, timings and warnings are recorded in
[testing](docs/TESTING.md). Offline results do not establish PostgreSQL race,
public CI, browser or performance certification.

| Verification scope | Evidence / status |
| --- | --- |
| Local PostgreSQL profiles | 30/30 on historical exact `0006_profiles` sources |
| Local PostgreSQL SSE | 4/4 on historical exact `0005_invitations` sources |
| Local PostgreSQL lifecycle | 10/10; aggregate report and owner-confirmed exit |
| Local authenticated last-seat race | Prior invitation acceptance: 13 cases x 3; three 50-caller races, each 1 success / 49 safe rejections |
| Public GitHub Actions | Owner reports 5/5 at bb60ab3; the current setup-owner patch has not run in public CI |
| Full integrated browser acceptance | Incomplete; original consumed campaign is uncertified |
| Scale seed and load | Tooling exists for 10,000 users / 2,000 teams / 100 clients; not executed, no measured p95 |
| Public HTTPS deployment | Not verified; no live URL claimed |

Historical reports retain their original source/provenance limits. This polish
does not recertify them. See [progress](docs/PROGRESS.md),
[G1 evidence](docs/G1_ACCEPTANCE.md) and [testing scope](docs/TESTING.md).

## Deployment

[Render Free preparation](docs/RENDER.md) is the owner-selected hosting target:
one public Caddy/React service, loopback FastAPI and private PostgreSQL 17, using
a Render HTTPS domain. Free idle sleep and 30-day database expiry make this a
temporary demonstration target. The adapter is prepared locally; no live deployment
is claimed. [Railway preparation](docs/RAILWAY.md) is retained as an alternative.

The existing VPS package serves React and proxies the API/SSE through Caddy
on HTTPS, with FastAPI and PostgreSQL on private Docker networks. Startup does
not run migrations. Secrets are mounted from ignored private files.
[Deployment preparation](docs/DEPLOYMENT.md) links the full launch, backup and
rollback runbook.

## Project structure

```text
backend/
  app/                 API, domain services, security, production entry point
  alembic/             Versioned PostgreSQL migrations
  tests/               Default offline tests; database tests explicitly marked
  *_tests/             Guarded PostgreSQL acceptance suites
  test_support/        Exact-version test and browser guards
  release_support/     CI, seed, load and evidence tooling
frontend/
  src/                 React views, hooks, API client and component tests
  test_support/        Browser campaign and evidence tooling
acceptance/            Versioned browser campaign specification
deploy/                Dockerfiles, Compose and Caddy template
load/                  k6 board scenario and environment template
scripts/               Provisioning, inspection and local configuration tools
docs/                  Setup, design, testing, deployment and component contracts
```

## Design documentation

- [One-page technical design](docs/DESIGN_ONE_PAGE.md)
- [Architecture](docs/ARCHITECTURE.md) and [decision records](docs/DECISIONS.md)
- [Documentation index](docs/README.md)
- [Requirements](docs/REQUIREMENTS.md), [submission checklist](docs/SUBMISSION.md)
  and [walkthrough script](docs/DEMO.md)
- [Historical review catalog](docs/archive/README.md)

## Limitations and current status

Full-catalog name search and email delivery are absent; exact UUID entry remains
available. Profiles are self-reported, and time zone overlap assumes 09:00-17:00
local working hours. SSE scans retained history; its cost and ranking performance
need measurement. Ordered/exactly-once delivery and multi-instance capacity are
not claimed. Parallel frontend runs have shown timing intermittency; the repeatable
verification command uses one worker.

Adapter CI, browser/mobile/keyboard acceptance, native production rehearsal,
HTTPS, the required load report, design export and walkthrough video remain
release gates. The submission deadline is **15 November 2026, 23:59 IST**.

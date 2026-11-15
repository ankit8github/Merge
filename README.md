# Merge

Race-proof hackathon team formation for Hack4Hack PS1. React/TypeScript, FastAPI,
PostgreSQL, SSE and explained deterministic teammate ranking. Individual submission;
deadline **15 November 2026, 23:59 IST**.

**Status:** product and release tooling are implemented/offline tested as a local
release candidate. Retained local PostgreSQL evidence records profiles **30/30**,
SSE **4/4** and lifecycle **10/10**, with provenance limits documented below.
Public CI, HTTPS deployment, browser acceptance, scale seed and measured
performance are **pending**. No live URL/video is claimed.
See [verified progress](docs/PROGRESS.md) and [submission gate](docs/SUBMISSION.md).
Current UI audit, focused simplifications and offline verification:
[product review](docs/PRODUCT_AUDIT.md).
Current recovery, evidence limits and minimum public release checklist:
[Batch D triage](docs/BATCH_D_RECOVERY.md). The original browser campaign is
permanently consumed and uncertified; it must not be restarted.
Local freeze review and exact publication/deployment handoff:
[Batch E release](docs/BATCH_E_RELEASE.md). Public links and measured load remain
pending; a local commit does not establish a submitted or deployed release.

## Product

Register and explicitly sign in; discover paginated hackathons/teams; create a
team; request admission; approve/decline as leader; issue recipient-bound expiring
invitations and redeem a private inbox. Names/usernames/team labels accompany IDs.
UUID lookup/recipient entry remain advanced fallbacks. Full-catalog name search
and email delivery are **not implemented**.

Members leave, leaders remove members, deterministic succession uses joined_at
then UUID, and last departure soft-deletes while retaining history. Confirmations
and explicit uncertain-command recovery explain outcomes. SSE refetches canonical
state on visible committed changes/reconnect. Profiles opt in to leader discovery;
rankings explain new skills and working-hour overlap, then select invite recipients.

## Architecture and correctness

PostgreSQL owns membership/capacity/leadership. Membership primary key
`(hackathon_id,user_id)`, scoped foreign keys and deferred final-state triggers
backstop the shared transaction protocol. Reserve idempotency key/command hash,
lock hackathon then affected users in UUID order then team/request/invitation,
recheck authority/capacity, and commit membership/version/audit/outbox/stored reply
together. Bounded retries preserve the original command/key; uncertain COMMIT
requires reconciliation. Pending requests reserve no seats; rankings grant none.

Argon2 has a bounded work budget. Sessions store token hashes. Production cookies
are Secure, HttpOnly, SameSite=Lax and host-only, with exact HTTPS Origin, CSRF,
durable throttles and one explicitly trusted proxy. Secrets/commands remain in
memory; only public navigation hints persist. No frontend secret or CORS is needed.

SSE polls committed public/private counts in short read-only transactions every2s,
with subscriber/lease limits; no private event payload or exactly-once guarantee.
Retained-history scan cost is unmeasured. Ranking is deterministic, not AI/ML:
`70 * novel_skill_fraction + 30 * timezone_overlap`, assuming09:00-17:00 local.
Exact fractions/UUID ties, bounded pool/pages and snapshot cursors preserve stable
order. Self-reported profiles are not skill verification or actual availability.
Contracts: [transactions](docs/TEAM_SERVICES.md), [lifecycle](docs/LIFECYCLE.md),
[retries](docs/TRANSACTION_RETRY.md), [realtime](docs/REALTIME.md), [ranking](docs/RANKING.md).

## Reproducible offline setup

Prerequisites: Python 3.11 (local evidence: 3.11.9), Node 22.15.0, npm 10.9.2, Git.
Existing Windows venvs need no activation/execution-policy change. Installation
requires approved package access; PostgreSQL is unnecessary for these checks.

```powershell
Set-Location I:\Merge
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
Set-Location frontend
npm ci
Set-Location ../backend
.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short
if ($LASTEXITCODE -ne 0) { throw 'Backend failed' }
.\.venv\Scripts\python.exe -m app.production.check
if ($LASTEXITCODE -ne 0) { throw 'Production configuration failed' }
Set-Location ../frontend
npm test -- --reporter=dot --maxWorkers=1
if ($LASTEXITCODE -ne 0) { throw 'Frontend failed' }
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Typecheck/build failed' }
```

Linux uses `backend/.venv/bin/python`. Offline setup never migrates/starts a server.
Do not use unrestricted DB tests, ordinary `alembic upgrade head`, retained fixture
cleanup or benchmark startup. [Release validation](docs/RELEASE_VALIDATION.md)
separates exact-version targets and approvals. Local profile acceptance ran at
**0006_profiles**; production migration/readiness remains separately unverified.

## Hosting and evidence

Ordinary Settings/app.serve remain limited to local127.0.0.1:5432/merge_dev as
merge_app. Development DB setup/startup needs separate reviewed authorization;
retained merge_test is never a seed target. Vite is only a development proxy.

[Production packaging](docs/PRODUCTION.md) proposes a Linux VPS, Caddy HTTPS/static
React, one API worker and private PostgreSQL17/persistent volumes. Separate mounted
runtime/migration secrets and exact merge_prod identity prevent local/test fallback;
startup never initializes/migrates. Native images/configuration, TLS and restricted
DB-role behavior remain unrun. Review launch/backup/rollback gates before deployment.

Prior owner-run local invitation evidence records39 cases (13 x3), including three
50-distinct-authenticated-caller last-seat races:1 success/49 safe rejections.
[G1 evidence](docs/G1_ACCEPTANCE.md) documents aggregate/provenance limits. This is
not public CI or production proof. Retained SSE4/profile30 reports passed on
their historical sources; lifecycle10 has an aggregate report and owner-confirmed
native exit. They do not certify the changed source or browser/HTTPS transport.
Actions isolates PostgreSQL16 jobs at0003/0004/0005/0006 and includes the race;
no public run exists. New disposable merge_bench tooling seeds10000/2000 and k6
measures100 VUs, p95<200ms, optionally32 SSE clients. No measured result exists.
Never benchmark retained test or production databases.

- [Current freeze results](docs/PROGRESS.md) / [combined 97-file inventory](docs/BATCH_C.md)
- [One-page design](docs/DESIGN_ONE_PAGE.md)
- [Five-minute demo script](docs/DEMO.md), no video recorded
- [Submission links/checklist](docs/SUBMISSION.md)
- [Batch A](docs/BATCH_A.md) / [Batch B](docs/BATCH_B.md)
- [Requirements](docs/REQUIREMENTS.md), [architecture](docs/ARCHITECTURE.md), [decisions](docs/DECISIONS.md)

Source review covers labels/native controls, skip link, focus/status handling,
responsive stacking and long labels. Current real browser/mobile/keyboard proof
is pending; jsdom is not a browser certificate. Owner exercise: explain why
/health differs from readiness and why a lost response reuses the original key.
Local freeze approval does not authorize publication or live actions.

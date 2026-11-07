# Merge — Repository Instructions for Codex

> Project: Merge | Hack4Hack Crew Hiring Challenge 2026 | PS1: Race-proof team formation at scale
> Owner: Individual contestant. AI coding tools permitted, but the owner must understand and defend the code.
> Source of truth: `docs/REQUIREMENTS.md` (what), `docs/ARCHITECTURE.md` (how), `docs/DECISIONS.md` (why), `docs/PROGRESS.md` (verified status).

## Mission and priority
Produce a correct, secure, usable, deployed PS1 submission by **2026-11-15 23:59 IST**, then retain it as an independently maintainable portfolio project. Optimize for verified mandatory acceptance criteria before polish or bonus features.

## Non-negotiable workflow
1. **Read the docs first.** Before modifying code, read `AGENTS.md`, the relevant sections of `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` and `docs/PROGRESS.md`.
2. **One bounded component per task.** Restate objective, target files, behavior, acceptance tests and dependencies before implementation. Do not scaffold the entire product in one pass.
3. **No silent architecture changes.** Ask for a decision or propose an ADR before changing database invariants, authentication/session model, serialization/locking protocol, public API contracts, deployment topology or core dependencies.
4. **Tests are part of implementation.** Add relevant tests and run them. Do not claim a pass without the actual command and results. Never delete or weaken a failing test merely to pass CI.
5. **Use a real PostgreSQL instance for race tests.** SQLite, mocked repositories or an in-process mutex cannot demonstrate PS1 concurrency correctness.
6. **Preserve invariant enforcement.** All paths that add/remove memberships, accept requests, redeem invites, create teams or transfer leaders must follow one consistent transaction/lock strategy and enforce database constraints.
7. **Safe operations.** No secrets in source, logs, sample datasets or Git. No destructive command, force push, production migration, remote data removal or credential change without explicit owner approval.
8. **No fabricated evidence.** Do not invent benchmark results, screenshots, test counts, deployed URLs, coverage, interview outcomes or commit hashes. Clearly distinguish 'planned', 'implemented', 'tested' and 'verified'.
9. **Make code explainable.** Prefer explicit services, typed APIs, documented transactions and narrow functions to opaque abstractions. The owner should be able to explain and live-modify the component.
10. **Avoid scope creep.** No LLM, vector DB, microservices, Kafka, Redis or Kubernetes unless a measured, documented requirement warrants them.
11. **Security baseline.** Authenticate every protected route; enforce authorization server-side; validate inputs; protect sessions; rate-limit invite redemption and login; avoid logging raw secrets; use parameterized queries.
12. **Review before commit.** Inspect diff, update documentation/progress, report known limitations. Never commit on the user's behalf unless instructed.

## Task response contract
Each coding task must end with:
- **What changed**: behavior, files modified, new dependencies and migrations.
- **Why**: key engineering decisions and any alternatives considered.
- **Evidence**: exact tests/lints/build/benchmark commands run, outcomes and environment; state 'not run' when appropriate.
- **Risks / missing work**: honest known limitations and blocked prerequisites.
- **Owner explanation**: a concise description plus one small modification or debugging exercise the owner should be able to perform.
- **Progress update**: change `docs/PROGRESS.md` only for milestones with evidence.

## Architecture guardrails (proposed, not organizer mandates)
- Modular monolith: **React + TypeScript + Vite**, **FastAPI + Pydantic**, **PostgreSQL**, SQLAlchemy/Alembic, SSE, pytest, Playwright, k6, GitHub Actions.
- PostgreSQL is the authority for membership, capacity, leadership, invite, idempotency and audit state. Browser and process memory are never authoritative.
- **No check-then-insert race**: use a documented transaction and lock order, constraints and explicit idempotency handling.
- **One active membership per `(hackathon_id, user_id)`** must be database enforced (schema may use active-only partial index or active membership table).
- Events are emitted only for committed changes; clients can refetch canonical state after reconnect.
- Use transaction-scoped DB sessions; do not hold transactions across network calls.
- Any cached team member count must be updated in the same transaction as membership and verified against true rows in tests.
- The current architecture is a design proposal, not a claim of deployed production reliability.

## File/document hierarchy and conflicts
1. Official organizer problem statement and rules (external requirements; link in REQUIREMENTS).
2. `docs/REQUIREMENTS.md` (traceable requirements; any source changes must be reviewed).
3. Approved decisions in `docs/DECISIONS.md`.
4. `docs/ARCHITECTURE.md` (current design).
5. Component task specification.
If two documents conflict, **stop and surface the conflict**. Do not silently choose.

## Definition of done for a component
- Behavior implemented according to explicit acceptance criteria.
- Relevant tests added and passing; important failure modes tested.
- Authentication/authorization, validation and retries addressed where relevant.
- Docs and progress updated with reproducible evidence.
- Owner can explain the implementation, including at least one failure case and a potential live modification.

## Challenge-specific constraints
- **Individual** submission, **one** problem statement, original work; AI tools allowed with owner understanding.
- Due **2026-11-15 23:59 IST**; late submissions not reviewed.
- Minimum **20 API tests including 50-way race test in GitHub Actions**.
- Seed **10,000 users and 2,000 teams**; **100 concurrent clients**, board p95 **under 200 ms** with documented load-test setup.
- Public React app, mobile and keyboard usability, live updates, security, auditing and matching.
- Submission: GitHub repo, live URL, load report, **one-page design document**, walkthrough video **up to 5 minutes**.

Official specification: https://hack4hack.com/hackathons/hack4hack-crew-hiring-challenge-2026-tp3m

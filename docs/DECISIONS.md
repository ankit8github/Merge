# Merge — Architecture Decision Records (ADRs)

**Status:** Initial decisions for review. **Date:** 2026-11-06.

This file explains **why** we are building the system a particular way. `docs/REQUIREMENTS.md` explains **what** must be true. `docs/ARCHITECTURE.md` explains **how** we intend to achieve it.

## Decision register

| ID | Decision | Status | Alternatives / principal trade-off |
|---|---|---|---|
| ADR-001 | Choose PS1 rather than PS2 | ACCEPTED | PS2 has additional storage, queue and failure boundaries |
| ADR-002 | Modular monolith | ACCEPTED | Less operational overhead than microservices; easy end-to-end transactions |
| ADR-003 | React + TypeScript + Vite | ACCEPTED | Aligned with required React UI, accessible familiar stack |
| ADR-004 | Python FastAPI + Pydantic | ACCEPTED | Personal implementation fluency; employer generally uses Express |
| ADR-005 | PostgreSQL as authoritative transactional store | ACCEPTED | Rich relational invariants; employer generally uses MongoDB |
| ADR-006 | Row-level locks + DB uniqueness, not in-memory mutex | ACCEPTED IN PRINCIPLE | Precise lock order is pending G1 proof |
| ADR-007 | Persisted idempotency outcomes | PROPOSED | Must handle concurrent same-key operations and crash/retry |
| ADR-008 | SSE with post-commit outbox, client state refetch | PROPOSED | Simpler push than WebSocket; multi-replica fanout unresolved |
| ADR-009 | Deterministic skill/timezone matching | ACCEPTED | Explainable and easy to test; no LLM needed |
| ADR-010 | GitHub Actions, pytest, Playwright, k6 | ACCEPTED | Strong reproducible evidence; setup/testing time cost |
| ADR-011 | Cookie sessions with CSRF protection | PROPOSED | Consider auth integration constraints in deployment |
| ADR-012 | Soft deletion for teams | PROPOSED | Preserves audit; must still satisfy organizer's 'deletes the team' semantics |
| ADR-013 | No speculative infrastructure | ACCEPTED | Add Redis/queue/services only if requirements or measurements justify |
| ADR-014 | Realtime deployment topology | OPEN | Single instance initially; multi-instance needs shared fanout |
| ADR-015 | Hosting provider | OPEN | Must measure latency, persistence, SSE and cold starts |

## ADR-001 — PS1 selection
**Context:** Individual challenge, short deadline, full-stack hiring evaluation; two distinct systems: PS1 team concurrency and PS2 fault-tolerant 100MB submission infrastructure.
**Decision:** Implement PS1: Race-proof team formation at scale.
**Rationale:** More direct reuse of existing FastAPI, React and PostgreSQL experience. Hard invariant can be tested in a contained PostgreSQL environment, enabling stronger quality and interview defense with available effort.
**What this does not prove:** PS1 is not guaranteed less competitive or more likely to result in an offer. No participant distribution or selection probability was published.

## ADR-002 — Modular monolith
**Decision:** One backend app with explicit identity, teams, membership, invite, request, matching, audit and realtime modules.
**Rationale:** Membership operations need strong transaction boundaries; microservice decomposition would increase failure paths and test complexity without helping the prescribed scale.
**Revisit if:** Independent scaling bottleneck or organizational need emerges after benchmarking.

## ADR-003/004 — React / FastAPI
**Decision:** React + TypeScript frontend; FastAPI backend.
**Rationale:** React is explicitly required. FastAPI is familiar to the owner and supports typed interfaces, testable routes and Pydantic validation.
**Trade-off:** Organizer's usual stack is React/Express/MongoDB; using Python requires a credible, framework-independent explanation and evidence of full-stack capability.

## ADR-005/006 — PostgreSQL correctness
**Decision:** PostgreSQL is authoritative for capacity, membership uniqueness and team lifecycle. Locks and unique constraints work together.
**Rationale:** A `SELECT COUNT(*)`, followed by a separate insert with no serialization is unsafe. A team row lock serializes same-team capacity checks; a unique active membership key prevents cross-team double joining. Use consistent lock order and transactional updates for lifecycle changes.
**Trade-off:** More explicit transaction and database design than optimistic app-level logic. Correctness under deadlocks/conflicts must be verified; PostgreSQL doesn't magically fix bad transaction design.
**Revisit if:** Tests reveal deadlocks or constraints insufficiently capture invariants.

## ADR-007 — Idempotency
**Decision proposal:** Persist `(actor,operation,key,request_hash)` and completed outcome atomically with domain changes. Same fingerprint replays; mismatched payload rejects.
**Rationale:** Lost responses and double clicks must not duplicate teams or memberships.
**Outstanding:** Pending-in-progress request response, expiration window and storage schema.

## ADR-008 — SSE + outbox
**Decision proposal:** Use SSE to broadcast committed changes; outbox tracks durable event records, client refetches canonical state.
**Rationale:** Server-driven UI updates do not require full-duplex sockets. Durable records improve recovery; reconnect resynchronization guards against missed events.
**Trade-off:** SSE is one-way; shared fanout is needed for multi-replica deployment, and event delivery is not inherently exactly-once.

## ADR-009 — Deterministic recommendations
**Decision:** Start with a transparent weighted function for complementary skills and timezone overlap, document weights, bound input data and test rank stability.
**Rationale:** Organizer requests ranking and explanation, not generative AI; complexity should serve requirements.

## ADR-010 — Tests and benchmarks as contract
**Decision:** Target at least 20 API tests in CI, real-DB 50-way race, 10k/2k seed, documented 100-user load and measured board p95 <200ms.
**Rationale:** This is explicitly part of assessment. Never assert compliance from mocks or an unrepresentative benchmark.

## ADR-011/012 — Sessions and deletion
**Decision proposals:** Secure session cookies with CSRF defenses; soft deletion of teams while hiding deleted teams and keeping audit history.
**Trade-offs:** Cross-site deployment/cookie policies need testing. Soft deletion must preserve the functional semantics of 'team deletes when last leaves'.

## ADR-013 — Scope discipline
**Decision:** No extra AI assistant, recommendation LLM, microservices, Kafka or Kubernetes before official must-haves.
**Rationale:** Finish correctness, security, UX, CI, load and submission first.

## Pending ADRs to resolve at G0/G1
- **ADR-016** Final DDL, active membership uniqueness and foreign-key design.
- **ADR-017** Canonical lock order for create/join/approve/leave/remove/transfer.
- **ADR-018** Exact invitation redemption semantics and minimum team-size states.
- **ADR-019** Hosted deployment topology and realtime event fanout.
- **ADR-020** Idempotency concurrent reservation behavior.

## ADR change protocol
### ADR-016/017/018/020 — approved M-005B refinement, implemented schema subset in M-006A

Accepted by owner for bounded schema implementation, 2026-11-07: active-only memberships with `(hackathon_id,user_id)` primary key; derived counts/readiness (supersedes earlier cached-count suggestion); composite hackathon FKs; initially deferred leader membership FK; final-state constraint triggers and parent-team NO KEY UPDATE locks; immutable identities; soft deletion; frozen hackathon size configuration; transactional-support tables with deferred completed-outcome validation; additive 0002 after unchanged 0001. READ COMMITTED is explicit. See `SCHEMA.md` for exact mechanisms, error categories and tests. No auth, mutation/idempotency services, audit generation, dispatcher, or API/race correctness claim is included. Raw SQL can still deadlock; supported future services must use the full lock matrix and bounded whole-transaction retries. Tests must establish actual enforcement rather than treating this ADR as evidence.

### Phase 0 local setup clarification — accepted 2026-11-06

Owner approved using the existing PostgreSQL 17 server at `127.0.0.1:5432` instead of requiring Docker Compose for M-002. Use only a dedicated `merge_dev` database and non-administrative `merge_app` role, provisioned manually when credentials are unavailable. Do not modify existing databases or roles. Docker remains an optional later local setup, with no verification claim. This changes the local setup assumption only; PostgreSQL authority, domain invariants, lock protocol, authentication and production deployment decisions remain unchanged. Add public `GET /health` returning `{"status":"ok"}` as process liveness; database connectivity is a separate smoke test. Dependencies are pinned for the bootstrap. Consequence: G0 remains incomplete until real connectivity and baseline migration/repeated upgrade are verified.

When a decision changes, append an ADR entry with: context, change, alternatives, consequences, impact on acceptance tests, and date. Do not rewrite history silently. If the change alters organizer requirement coverage, update `REQUIREMENTS.md` and `PROGRESS.md` in the same review.

### Phase 0 PostgreSQL integration clarification — accepted 2026-11-06

Owner scoped M-003 to PostgreSQL integration, superseding the earlier task number assigned to schema/lock design. That design work remains pending before domain implementation. Local backend secrets now belong in ignored `backend/.env`, loaded by an absolute path regardless of working directory; the root `.env` is no longer loaded. This is an explicit local configuration change, not a change to authentication/session design or production deployment. Existing database/role conflicts must stop provisioning; unavailable credentials require an owner-run read-only metadata inspection and manual provisioning without secrets in chat. No database integration success is asserted until real smoke, online baseline, repeated upgrade and full backend tests pass.

Official source: https://hack4hack.com/hackathons/hack4hack-crew-hiring-challenge-2026-tp3m

### M-006B.1 dedicated test target — owner-approved preparation, 2026-11-08

Owner approved local merge_test exclusively for automated integration/concurrency
tests, with execution deferred for review. Reuse existing merge_owner/merge_app;
only new database/schema ACLs are in scope. Dedicated test settings and an online
Alembic entry point require explicit opt-in and server-side identity checks; they
do not load backend/.env, change ordinary Settings or edit frozen migrations.
This avoids durable test tombstones in merge_dev without weakening guards.
No DROP is authorized/executed here; disposal requires separate approval. See
TEST_DATABASE.md for commands, partial-provisioning risks and cleanup design.

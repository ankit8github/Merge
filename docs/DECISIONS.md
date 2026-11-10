# Merge — Architecture Decision Records (ADRs)

### M-007B.3B — owner-scoped durable auth throttling, 2026-11-10

Implementation contract proposed before coding: reuse unchanged
auth_throttle_buckets with actual DB-clock aligned fixed-window keys; atomic
UPSERTs serialize independent workers and saturate at limit + 1. Default 300s
window: login account 5, login IP 30, register IP 5. Charge IP first, skip account
creation after IP denial, and commit consumed counters even on a denial before
returning 429. KDF/session work starts only after this independent transaction
commits. Reuse the credential transaction owner/actual driver guard; storage or
configuration failure must give fixed 503 with no authentication work.

Use domain-separated HMAC-SHA256 keys with one explicitly configured 32-byte
secret shared by workers/restarts; no raw usernames/IPs in storage or logs. The
account identifier is the existing canonical ASCII username; do not change HTTP
username validation. Require shared window/limit/secret configuration, bounded
positive settings, no disabled mode or random runtime fallback.

Trust actual socket identity, no proxies by default. Support only an explicitly
configured immediate proxy with one overwritten X-Forwarded-For literal IP and
one X-Forwarded-Proto http/https; reject ambiguous/chained/alternative/untrusted
forwarding. A controlled Uvicorn entry point disables its header rewriting so
application checks see the actual peer. Keep Origin/CSRF checks unchanged.

Trade-offs: fixed-window edge bursts, account denial/NAT sharing, IPv6 address
rotation and retained expired rows need documentation. No automatic cleanup or
background process. No change to credentials/session boundaries, schema,
TeamService, roles/permissions, dependencies, team endpoints or M-008 scope.
Owner verified guarded throttles: 33 passed in 31.42s; updated API: 54 passed
in 30.94s; sessions: 78 passed in 48.33s. Combined 165 passed in 110.69s,
three repetitions requested, fresh committed-state invariants verified.
Existing Starlette/HTTPX warning remains; Codex did not rerun PostgreSQL.
This verifies the bounded local schedules, not deployed HTTPS/browser security.

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
| ADR-011 | Cookie sessions with CSRF protection | ACCEPTED FOR M-007B.3A-R1 | Exact-origin same-origin HTTP adapter; durable throttling owner-verified M-007B.3B; deployed proxy/TLS/browser pending |
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

### M-007A bounded internal create/join services — owner-scoped, 2026-11-09

Owner scoped creation/join to internal trusted-actor services, with no public
endpoints or authentication/idempotency/audit/outbox writers. Schema inspection
confirmed those support records are not required for team/membership commits;
their own forward FKs/triggers do not imply mandatory reverse records. This does
not waive the final atomic outcome/audit/outbox architecture. The Engine-owned
facade commits each complete operation and cannot be composed by adding records
in an outer transaction afterward; M-008 must integrate them before public use.
Use hackathon SHARE -> user NO KEY UPDATE -> team NO KEY UPDATE, fresh row counts,
strict named-constraint error mapping and complete rollback. No automatic retry
or schema change. See TEAM_SERVICES.md. Final owner verification: 48 expanded
PostgreSQL cases passed in 37.23s, including R1 actual DBAPI AUTOCOMMIT rejection;
Codex checkpoint regressions: 94 database-free checks passed. The supported
transaction contract is synchronous postgresql+psycopg, actual autocommit is False,
READ COMMITTED and no active caller transaction; other/ambiguous states fail closed
without silently changing Engine configuration. This does not close API/auth gates.

### M-007B.1 auth storage — owner-approved, 2026-11-09

Use canonical lowercase ASCII usernames and future Argon2id password hashes,
PostgreSQL-backed opaque sessions with 32-byte SHA-256 digest identifiers, eight-hour
absolute expiry and session CSRF secrets. Keep separate credential rows; no seeded
user adoption/backfill. Sessions require both principal and credential FKs. Add
minimal PostgreSQL throttle bucket storage without implementing its algorithm.
Add 0003_auth after unchanged 0002; constrain lengths, finite times, immutable
session identity/lifetime and terminal revocation. Do not claim cryptographic
provenance or login from storage constraints. Preserve default guarded target 0002;
auth support requires explicit --revision 0003_auth. No services/endpoints in
this component. Owner checkpoint evidence (2026-11-09): guarded migration/repeat,
0003_auth (head), preserved domain counts/fingerprints and 78 live schema cases
passed in 11.75s, three repetitions requested. Codex checkpoint: 116 database-free
tests passed; no PostgreSQL rerun. Details/owner commands: AUTH_SCHEMA.md.

### M-007B.2A bounded credential services — owner-scoped, 2026-11-09

Implement internal registration/verification using unchanged 0003_auth. Username
policy remains canonical ASCII; passwords are 15–128 characters without trimming
or composition rules. Pin argon2-cffi 25.1.0; Argon2id v19, 19 MiB, two iterations,
one lane, random 16-byte salts and 32-byte output. Shared two-slot nonblocking
per-process hashing budget; no DB locks during hashing. This is a resource bound,
not persistent rate limiting. Exact bounded stored profile only; no automatic
rehash/adoption. Unknown-user dummy verification uses that same profile.

Registration creates a new server UUID plus credential atomically; only the
canonical username constraint maps to username_unavailable. Verification uses a
closed read-only lookup before KDF and generic invalid_credentials for wrong or
unknown accounts. Reject DBAPI AUTOCOMMIT/ambiguous isolation and unsafe SQL
logging configuration, preserve READ COMMITTED and caller-independent ownership.
No TeamService/schema changes, endpoints, sessions or rate-limit service. Explicit
0003 guarded credentials suite, retained UUID fixtures. Owner checkpoint evidence:
51 live cases passed in 28.76s, three repetitions requested, fresh committed-state
checks verified and no fixture cleanup. Codex checkpoint: 175 database-free tests
passed; no database rerun. No additional post-change live suite result supplied.
Contract, reviewed trade-offs and sources: CREDENTIAL_SERVICES.md.

### M-007B.2B internal session lifecycle — owner-scoped, 2026-11-10

Use unchanged 0003_auth and the approved PostgreSQL-backed opaque session model.
The only issuance interface is SessionService.login(username,password), internally
reusing credential verification. Do not accept a UUID, public CredentialIdentity
or externally supplied proof object. A private verified snapshot is rechecked
against current credentials under user KEY SHARE → credential SHARE locks before
session INSERT/COMMIT. This rejects a credential change after verification and
blocks changes after the final check through commit, without holding locks during
Argon2. Public CredentialService interfaces/parameters remain unchanged. Python
private members and caller Engine hooks are trusted code, not an adversarial
in-process sandbox; no process-memory authentication/session store is introduced.

Generate independent 32-byte session/CSRF secrets before write locks; store only
the SHA-256 session digest and the existing server-side CSRF representation.
Return raw material in explicitly sensitive SecretBytes fields only after commit.
Use authoritative database clock_timestamp(), aware UTC and an eight-hour absolute
lifetime. Validate active session and credential rows on each call, never renew
implicitly, compare CSRF with compare_digest, and revoke only where revoked_at
is NULL. Reuse the credential transaction guard/error mapper; no TeamService or
schema changes. Existing sessions do not automatically invalidate after a future
valid password change; that workflow needs explicit revocation and separate review.

Alternative rejected: public constructible identity as login proof, or a memory
ticket registry. The login facade keeps the verification/issuance dependency local
without exposing an authentication-ticket protocol. Validation remains a point-in-
time read, not cancellation of already-authenticated in-flight work. No HTTP,
cookie/header policy, rate limiter or automatic transaction retry is implemented.
Owner checkpoint: 63 guarded session cases passed in 51.63s against merge_test /
0003_auth, three repetitions requested, fresh committed-state invariants verified
and fixtures retained. Codex checkpoint: 222 database-free passes; no database
connection or migration ran during Codex review. No additional post-change live
regression result supplied. Security boundary, errors, tests: SESSION_SERVICES.md.

### ADR-011 refinement — M-007B.3A-R1, owner-approved 2026-11-10

Owner approved the narrow session interface extension before the previously
authorized four HTTP authentication routes. validate_with_csrf returns a frozen,
sensitive principal/SecretBytes CSRF result from the existing validated read
snapshot. It never exposes a bearer/hash/raw row or changes expiry/transaction
boundaries. Unit/static verification is required before the HTTP adapter proceeds.

Use same-origin requests, exact configured Origin on mutations, JSON-only strict
bodies and X-Merge-Request: 1 for register/login. Logout checks the active cookie
and session-bound X-CSRF-Token through existing services before revoke. Fetch
Metadata rejects non-same-origin values when present. No permissive CORS. Strict
canonical base64url encoding for cookie/CSRF. Auth responses/errors are no-store
and sanitized, including validation inputs and unexpected service failures.

Production defaults require explicit HTTPS origin at startup and use only
__Host-merge_session, Secure, HttpOnly, SameSite=Lax, Path=/, no Domain. Explicit
loopback development mode uses merge_session_dev without Secure and Vite /auth
proxying. Configuration is environment-only; runtime database construction stays
lazy and uses existing local Settings. Guarded API tests inject real services on
the fixed merge_test Engine, with no development-settings fallback.

Alternatives rejected: route SQL or private-row access for CSRF retrieval,
client-submitted identities as proof, reflected origins/cross-origin credentialed
CORS, default insecure cookies, route-owned commits and session renewal on reads.
Consequences: startup now needs explicit browser-origin configuration; README
and local regression runner set it. No frontend redesign, domain API, schema or
dependency change. Shared throttling is deliberately deferred to M-007B.3B;
production readiness, browser E2E and deployed TLS/proxy correctness remain open.
Owner checkpoint: 78 expanded session cases passed in 72.48s and 54 HTTP API
cases passed in 40.90s on guarded merge_test / 0003_auth (head), 132 live
executions total, fresh committed-state invariants verified, one existing
Starlette/HTTPX warning. Codex did not rerun PostgreSQL. Shared throttling and
browser/deployed HTTPS correctness remain unverified; the proxy timing flake
remains open. Exact contracts, failure semantics and reproduction: HTTP_AUTH.md.

### M-008C — owner-approved idempotency primitives, 2026-11-10

Use the unchanged idempotency table and constraints at 0003_auth. Reserve one
operation in scope `(actor_id, operation, key)` before future domain locks;
operation names are `team.create.v1` and `team.join.v1`. Keys are exactly 1–128
printable ASCII characters, case-sensitive, without trimming. Hash versioned,
canonical JSON of validated meaningful inputs with SHA-256; a generated team ID
is an outcome, not a create-command input. A different fingerprint or hackathon
in the same scope is `idempotency_mismatch`.

Retention is success-only. The owner's transaction reserves, performs one future
mutation, records its successful reply and commits once. Failure rolls everything
back. Conflicting INSERT waits for its winner, then a separate READ COMMITTED
SELECT loads an immutable completed response. Pending visibility is an integrity
fault; the existing deferred constraint forbids committing pending rows. No lease,
expiry, takeover, cleanup, autonomous transaction or retry framework is added.

This milestone supplies private transaction-local helpers and test-only
composition, without changing TeamService or exposing idempotent public methods.
Reply format and bounded header policy are internal and versioned; no HTTP API
contract is introduced. Audit/outbox and ambiguous-COMMIT reconciliation remain
separate milestones. See IDEMPOTENCY.md for the precise contract and evidence.

Owner checkpoint: 60 guarded idempotency cases passed in 40.82s on merge_test /
0003_auth, three repetitions requested, fresh committed-state invariants verified
and fixtures retained. This supersedes the first-test bind failure repaired in
test-only R1. Codex did not rerun PostgreSQL; no public mutation facade, audit/
outbox composition, retry reconciliation or G1 closure is included.

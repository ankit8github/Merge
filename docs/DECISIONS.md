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

### M-008D — owner-approved atomic composition, 2026-11-10

Add explicit create_team_idempotent/join_team_idempotent methods on TeamService.
The existing _execute remains the only transaction owner. Reserve before domain
locks, replay without invoking domain logic, otherwise compose one existing
transaction-local mutation, version, audit, outbox and successful reply completion.
Legacy create/join remain internal compatibility facades, excluded from future
HTTP use. No schema, migration, dependency, dispatcher or retry framework change.

Create allocates its outcome UUID only after reservation succeeds and starts at
version 1. Join increments version once under its retained team lock. Audit stores
bounded before/after team summaries and affected subject membership, using schema
columns for actor/scope/action/version/operation linkage. The unchanged leader/
sizes and pre-join version/count can be derived under the retained lock from the
single join's resulting values. Outbox contains only hackathon/team IDs and team
version with event_type team.changed.v1, unpublished and attempt_count zero.
See TEAM_MUTATIONS.md for payloads, ownership, verification and limitations.

Owner checkpoint: guarded merge_test / merge_app, READ COMMITTED, 0003_auth (head);
81 composed cases passed in 101.23s, 57 service regressions in 59.59s and 60
idempotency regressions in 40.81s. Total 198 passed, corrected suite-time sum
201.63s, three repetitions requested per suite, fresh chains/invariants verified,
fixtures retained. The owner corrected 202.63s as an arithmetic error. No Codex
PostgreSQL run, M-008E implementation, public HTTP integration or G1 closure.

### M-008E — owner-authorized bounded retry/reconciliation, 2026-11-10

Only composed idempotent create/join enter retry orchestration. Pin the validated
command/scope/key/hash once; at most three total fresh owned transactions,
including reconciliation. Retry confirmed PostgreSQL 40P01/40001 only after
the owner unwinds; retryable DomainError alone is not proof. Legacy operations
retain single-attempt behavior. No statement retry, new key or background worker.

Use an immutable service retry policy: total budget 1–60 seconds (default 30),
jitter ceiling 0–250ms (default 50). A monotonic deadline checks attempts, waits,
statements and COMMIT preparation; server lock/statement timeouts are clamped to
remaining budget without exceeding existing 5s/15s limits. Synchronous connection,
transport and cleanup waits retain their driver bounds, not hard thread cancellation.

Track actual owner phase and sanitized DBAPI SQLSTATE without retaining driver
text. Lost/unknown COMMIT acknowledgement is reconciled only by the same-key
reservation protocol on a fresh guarded connection. A loaded immutable matching
reply is valid reconciliation; winning a new reservation proves the earlier
reservation did not commit. No immediate-absence inference. If proof cannot be
obtained within attempts/budget, return retryable outcome_uncertain; do not report
failure/success. No public HTTP status contract is added. See TRANSACTION_RETRY.md.

Owner checkpoint: merge_test / merge_app, READ COMMITTED, 0003_auth (head);
retries 54 passed in 48.66s, mutations 81 in 72.40s, TeamService 57 in 36.15s,
idempotency 60 in 42.84s. Total 252 passed, suite-time sum 200.05s, three
repetitions requested per suite, fresh committed-state invariants verified and
fixtures retained. These are owner-run PostgreSQL results, not Codex database
executions. No schema/permission/dependency change, HTTP team API or G1 closure.

### M-010A — authenticated read-only discovery, 2026-11-10

The owner authorizes GET-only hackathon/team discovery and own membership. The
schema has no enrollment, tenant or private-visibility rules; all authenticated
accounts may view this bounded public metadata, including unjoined teams. Scope
every team/cursor lookup to its hackathon; derive own identity only from validated
PostgreSQL session cookies. No new mutation authorization model is inferred.

Use /api/hackathons, scoped /teams and /teams/{id}, and /me/team. Share existing
browser/proxy/HTTPS policy and no-store protection with /auth. New read service
owns READ ONLY snapshots on the existing lazy owned Engine; TeamService and
mutation helpers are unchanged. One domain SELECT returns counts, leader and
membership state consistently, without row write locks. Allowlisted typed DTOs
omit account/session/audit fields and full rosters. Pagination is keyset-based,
1–100 rows, over existing PK/board/roster indexes; no schema change. Team cursors
resolve immutable timestamp/ID in the same hackathon, including tombstones;
missing/cross-scope cursors are invalid. No stable snapshot across pages promised.

Alternatives rejected: client identities, enrollment invented without schema,
unbounded lists/rosters, offset scans, separate count/state snapshots and ORM/auth
object serialization. READ_API.md records exact contracts and live evidence.
No HTTP team mutations, invitation/request workflow, dependency,
frontend, privilege or migration changes. G1 remains open.

Owner checkpoint at 0003_auth: read API 87 passed in 73.35s, auth API regressions
54 in 28.28s; combined 141 passed, suite-time sum 101.63s. Three repetitions
requested; one existing Starlette/HTTPX warning. These are owner-run PostgreSQL
results, not Codex database executions. No public mutation or production/G1 claim.

### M-011A ? React authentication and discovery, 2026-11-10

Within the owner's approved frontend scope, use the existing React/TypeScript/
Vite/plain-CSS stack and unchanged auth/read DTOs. Keep an explicit small session
state machine and cancellable view-owned reads; no additional state/router/UI
framework or persistence. Native cookie handling, memory-only CSRF, exact relative
URLs and existing browser Origin/custom-header rules remain authoritative.
No client identity is sent to the server. Generation changes discard private
workspace state and ignore late responses; failed logout does not claim success.
Registration confirms account creation before explicit login. No automatic retry
of authentication mutations, even after an ambiguous transport failure.

Catalog and team lists request bounded cursor pages and preserve server ordering;
details/My Team use canonical GETs. Membership null is a distinct successful
empty state. Readiness/counts confer no admission right. A future join control
is disabled and no mutation endpoint or fake live fixture is introduced. UI view
navigation stays local React state; deep-link routing/realtime are later work.

FRONTEND.md records implementation, tests and browser steps. Offline/component/
proxy checks are not PostgreSQL or real-browser proof. Ordinary backend Settings
still require merge_dev, so authenticated browser testing requires a separately
approved guarded HTTP host, not weakening that guard. No schema, dependency,
backend transaction, authentication model or deployment topology change. G1 open.

### M-012A - owner-scoped authenticated team creation HTTP, 2026-11-10

Expose only the owner's requested scoped create endpoint. Derive actor from the
existing validated PostgreSQL cookie, require the existing session-bound CSRF and
Origin/Fetch Metadata/peer/HTTPS policy, and accept only name plus one exact
Idempotency-Key. The route calls create_team_idempotent once, never legacy create
or direct SQL, and returns its stored 201 status/body/allowlisted headers with the
existing no-store policy overlay. Matching replay is still authenticated/CSRF
checked. Changed commands conflict; outcome_uncertain instructs unchanged same-key
retry and claims neither failure nor success. No new transaction owner, separate
audit/outbox write, schema, join authorization or dependency. See TEAM_API.md.

Retain the existing reservation-first service semantics, including sanitized 503
for a missing hackathon that fails the immediate reservation FK; do not add a
check-then-write existence transaction or infer business absence from generic
integrity errors. Unknown faults remain sanitized. The M-011A test browser host
excludes the new router by identity and still fails closed if it is reintroduced;
its manifest grants no team-write scope. Guarded HTTP tests have a separate fixed
suite and retained scoped fixtures. The owner subsequently verified 105 HTTP
cases in 140.81s at guarded 0003_auth. Codex did not rerun PostgreSQL. G1 remains
open; browser/deployed HTTPS and other lifecycle authorization remain pending.

### M-012B - owner-scoped React team creation, 2026-11-10

Use the exact M-012A contract. Generate a cryptographic printable key per meaningful
command and retain exact name/key after uncertain delivery; retry is explicit.
Keep metadata in App above the session-generation workspace, scoped to validated
account/hackathon IDs, never sending actor identity. Expose the existing frontend
session generation's invalidation signal rather than introducing another auth
model. Logout/restore/expiry abort and ignore callbacks, retaining unresolved
metadata for the same account to resolve. Cancellation is not transaction proof.

Unknown/network/503/mismatch responses lock the name. Only documented status/
code pairs permit editing after definite rejection; proxy HTML or a status alone
is not rollback proof. A later 401/403/422 cannot erase earlier uncertainty. Validated 201 acknowledges the stored founder result;
refetch My Team and reset/invalidate the list rather than inventing TeamView data.
Read-refresh failure cannot erase confirmed creation. Known membership blocks new
creation, with only frozen original-key replay permitted for an unresolved command.
Server auth/CSRF and membership/invariant enforcement remain authoritative.

Rejected alternative for this milestone: persisting private command metadata to
browser storage or adding a query/state library. Memory survives navigation and
reauthentication but is lost on reload/tab close/crash; beforeunload is best-effort
and the UI says keep the tab open. Durable recovery is not claimed. FRONTEND.md
records offline tests and future browser prerequisites. No frontend join, new
dependency, backend/schema change, browser-host scope expansion or G1 closure.

### M-013A - leader-approved admission design, 2026-11-10

Owner-requested backend scope: proposed additive 0004_admission request state,
retained terminal history, explicit cookie/CSRF protected request/decision API,
and single-owner atomic authorized admission. The design/lock order is recorded
before coding in [ADMISSION.md](ADMISSION.md). No live migration approval is
implied; real races and G1 remain unverified until a separate owner-run test.

Final checkpoint, 2026-11-11: owner verified already-applied 0004_admission on
merge_test and successful one- and two-repetition admission runs (35 + 70 cases,
exit 0 and completed fixture checks in each). This records evidence for the
existing approved protocol, not a new transaction/auth/locking decision. No
manual migration rerun is authorized. The 50-candidate test uses one leader's
decision session, so distinct-caller G1 remains open. No frontend admission UI,
legacy-suite compatibility port or browser-host scope expansion is approved.

### M-013B - owner-scoped React admission, 2026-11-11

Use the exact committed admission endpoints and the existing React/TypeScript/
plain-CSS/session-generation design. Keep a separate narrow in-memory admission
journal in App, keyed by authenticated account/hackathon/team/request; preserve
original key and decision under uncertain delivery. Explicit retries use the
current restored session's CSRF, never a stored session/CSRF. Navigation does not
move a command into another scope; auth generation changes abort and ignore old
callbacks. No generic state/query framework or persistent credential storage.

Canonical detail/own-request/My Team reads govern presentation; successful POSTs
invalidate reads rather than synthesize status, membership, leader or counts.
Pending applicants are fetched only from the current-leader view, and errors
hide them. Recovery commands contain request UUID/decision rather than applicant
DTOs and require a successful authorized pending-list read before display.
Known membership blocks new requests but never authorizes discarding an uncertain
original retry. Sticky uncertainty prevents an opposite decision/new-key escape.
Backend authorization and transaction invariants remain the actual boundary.

Memory-only recovery deliberately cannot survive reload/tab close/crash. A
beforeunload warning is best-effort; no durable recovery claim or silent new-key
fallback. No additional admission rules, backend/schema changes, new dependency,
browser-host permission expansion or G1 closure. Real-browser/HTTPS/mobile/
keyboard acceptance needs a separately reviewed guarded 0004 host/write scope.

### M-014B - owner-scoped invitation prerequisite, 2026-11-11

The owner authorizes recipient-bound leader-issued invitations and a distinct-
caller harness, addressing M-014A's missing legitimate self-admission capability.
Design before implementation: [INVITATIONS.md](INVITATIONS.md). UUID inbox
references are not bearer authority; cookie recipient/current issuer/expiry are
checked under existing locks, including replay. Fixed 24-hour expiry, separate
durable per-account attempt scopes and retained history keep the component small.
Reuse the existing transaction/retry owner and already-locked membership helper;
no current auth/lock protocol refactor or public unrestricted join. Additive 0005
and its fixed suite need separate owner migration/live review. Existing 0004
admission and 0003/browser gates remain exact. G1 cannot close offline.

M-014B-R2 evidence update, same date: the owner reports applied 0005 and a
successful guarded invitation run. The existing report records 39 total cases
at three repetitions, exit 0 and completed suite/fixture checks. The audit in
G1_ACCEPTANCE.md closes original Phase 1 G1 within local PostgreSQL scope; it does
not change the contract or authorize another migration/live run. Earlier readiness
statements above retain their dated scope. CI/production/browser/load remain open.

### M-015B - separate bounded exact-0005 browser host, 2026-11-11

The owner authorizes M-015A's test-only environment implementation, not live use.
Preserve ordinary Settings and restricted 0003 browser host. Add a separate 0005
CLI with fixed loopback target, every-checkout guard, exact route/dependency audit
and all five real service overrides; leave ordinary runtime engines unset. Real
auth/CSRF/Origin/throttle/authorization and service transaction/lock ownership
remain authoritative. No application endpoint, privilege, dependency or schema
change is approved. Shared lifecycle/private-prompt helpers are reused unchanged.

Choose the explicitly planned nine-success/one-full-conflict journey rather than
an unrestricted test-write facade. Fresh approved usernames bind only server
registration results. Separate two-hackathon preparation never runs at startup.
Freeze exact command/key/scopes, bound attempts, retain all effects and compare
all preexisting row fingerprints plus scoped membership/request/grant/reply/
audit/outbox/auth state. Require complete journey and positive drain/disposal for
terminal success. Current-state verify cannot certify a lost/incomplete run.

Browser-only fault installation is separately approved against resolved exact
URLs/methods. Keep it out of src/builds and /auth, send one real request before
delaying/losing/replacing delivery, bound memory/time and restore transport.
Synthetic 401 is labelled UI evidence, never proof of real authentication or
COMMIT failure. Keys and both journals are memory-only; restarting the host cannot
adopt a retained run. A more general resume environment needs separate review.
Supported commands and honest limitations: BROWSER_ACCEPTANCE.md; actual offline
evidence: PROGRESS.md. No live database, browser/server or commit here.

### M-014C-R1 - mutation display ownership after navigation, 2026-11-11

The invitation journal's account/session guard cannot identify selected-workspace
ownership: navigation leaves that session generation unchanged. Two preserved
issue/redeem regressions and three additional creation/request/decision cases
reproduced global expiry from an old hackathon's 401 before the repair.

Use a narrow committed-workspace token, independent of HTTP transport and session
authority. A layout effect creates it; navigation cleanup invalidates it. Capture
it when submitting and require it for global expiry/automatic refresh. Continue
settling the original account/scoped command journal, preserving exact scope,
payload and key. Returning creates a fresh display token for explicit retry with
current CSRF. Canonical read refreshes/pagination do not rotate display ownership.
Creation owns the hackathon lifetime; team admission and invitations own view/team.

This avoids cancelling work on navigation (which cannot establish rollback),
clearing recoverable commands, globally ignoring 401s or changing authentication.
No new render-time mutable workspace assignment. Current-workspace 401 handling
and session/account cancellation remain intact. The reproduced related hooks use
the same correction; no backend/API/dependency/persistence change. Tests include
StrictMode, stale success/conflict, away/back recovery and reauthentication.
Full offline evidence: PROGRESS.md; real browser/HTTPS acceptance remains open.

### M-014C - invitation frontend within the existing contract, 2026-11-11

The owner authorizes leader UUID issuance, recipient inbox/redemption and offline
tests, without changing backend contracts. No account-lookup endpoint exists:
label UUID-only entry and let recipients share their own session-derived account
UUID from the inbox. Team UUIDs open existing canonical detail reads; fabricate
neither names nor user search. Reuse same-origin session/CSRF/key protections and
the existing App-lifetime account-scoped journal pattern for an independent
invitation journal. Uncertain commands freeze exact scope/payload/key and remain
reachable when refreshed inbox rows disappear; only validated acknowledgement
resolves uncertainty. Session abort cancels/isolates transports, and same-account
reauthentication retries with current CSRF. Recovery stays memory-only with
documented reload/crash loss, no new storage/dependency/authorization rule or
browser write permission. Exact behavior and limits: FRONTEND.md.

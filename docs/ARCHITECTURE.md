# Merge — Architecture Blueprint (Proposed v1.0)

**Status:** PHASE 0 VERIFIED / M-006A DOMAIN SCHEMA IMPLEMENTED; M-007A internal create/join services and R1 AUTOCOMMIT rejection implemented. Owner verified 48 expanded PostgreSQL cases in 37.23s; Codex verified 94 database-free checks. No domain APIs; G1 remains open for later acceptance work. Concrete schema and database guards: `docs/SCHEMA.md`; bounded service contract: `docs/TEAM_SERVICES.md`. Source requirements: `docs/REQUIREMENTS.md`. Decisions: `docs/DECISIONS.md`. Verification: `docs/PROGRESS.md`.

## 1. Goals and constraints

Current team-core overlay: M-008D composed idempotent mutation/version/audit/outbox
is committed; owner verified 198 live cases (suite-time sum 201.63s) at 0003_auth.
M-008E bounded retries and same-key ambiguous-COMMIT reconciliation are implemented;
owner verified 54 retry / 81 mutation / 57 service / 60 idempotency cases, 252
passes with suite-time sum 200.05s at guarded 0003_auth, three repetitions
requested per suite and fresh committed invariants verified. Codex did not
execute PostgreSQL tests. Only composed operations
participate, maximum three total attempts, monotonic budget and bounded jitter;
`_execute` remains sole transaction owner and lock order/schema remain unchanged.
See [TRANSACTION_RETRY.md](TRANSACTION_RETRY.md) and PROGRESS.md. Older milestone
statements below describe their original scope. No HTTP team API or G1 closure.
- Solve PS1 with a **correct-by-design membership core**, not an application-server mutex.
- Support 10k seeded users, 2k teams, board p95 < 200ms under 100 concurrent clients in the measured environment.
- Deliver an end-to-end React UI, secure API, realtime team/board notifications, verified tests and deployment by challenge deadline.
- Keep solution understandable for a 45-minute technical interview with live modification.
- Non-goals before submission: microservices, LLM matching, multi-region deployments, enterprise SSO, speculative high-scale queues.

## 2. Topology
```
React + TypeScript (Vite)  -- HTTPS -->  FastAPI modular monolith
       |                                      |-- Auth / sessions
       |                                      |-- Hackathons + team lifecycle
       +<-- SSE (committed change signal) --  |-- Membership transaction service
                                              |-- Invites + join requests
                                              |-- Suggestions + board queries
                                              |-- Audit + outbox dispatcher
                                              |
                                              +-- PostgreSQL (source of truth)
                                                  users, hackathons, teams, memberships,
                                                  invitations, join_requests,
                                                  idempotency, audit, outbox

CI: GitHub Actions → pytest/API/real Postgres race tests → UI build
Performance: k6 → deployed/staging board with fixed seed and test environment
Browser verification: Playwright → accessible mobile/keyboard flows
```

**Deployment assumption:** Start with a single backend instance for SSE delivery simplicity. No correctness rule may depend on one instance; PostgreSQL remains authority. A multi-replica fanout design will require cross-instance event distribution (e.g. LISTEN/NOTIFY plus replay) before scaling horizontally.

## 3. Modules (one codebase, clear ownership)
- `identity`: accounts, safe sessions, password hashing, profiles/skills/timezone.
- `hackathons`: event configuration and min/max sizes.
- `teams`: create, rename (if supported), soft-delete, leadership.
- `memberships`: join/leave/remove, atomic capacity and uniqueness.
- `invitations`: generate hashed, expiring, revocable invite codes; redeem through memberships.
- `join_requests`: create/cancel, approve/decline, enforce leader authorization; approve via same membership service.
- `board`: team discovery, filters, pagination and indexed queries.
- `matching`: deterministic skill/timezone ranking and rationale.
- `audit`: durable actor/action/time record within mutation transaction.
- `events`: transactional outbox, SSE stream, reconnect reconciliation.
- `reliability`: idempotency records, structured errors and diagnostics.

**Critical rule:** Every route that changes member count or assignments enters one authoritative membership/domain service, never copies SQL business rules into handlers.

## 4. Data model proposal
- `users(id, display_name, created_at, ...)` remains the principal table. Approved
  M-007B.1 storage is separate: account_credentials, opaque auth_sessions and
  auth_throttle_buckets. Owner verified additive 0003_auth/repeat on merge_test,
  preserved domain rows and 78 live auth schema cases in 11.75s (three repetitions
  requested); checkpoint database-free regressions: 116 passed.
  See AUTH_SCHEMA.md. M-007B.2A adds internal credential services with bounded
  Argon2id work and owned transactions; owner verified 51 guarded live cases in
  28.76s, three repetitions requested and fresh credential committed-state checks.
  Codex checkpoint regressions: 175 database-free tests. See
  CREDENTIAL_SERVICES.md. M-007B.2B adds internal PostgreSQL session lifecycle:
  credential-verified login with a locked snapshot recheck, digest-only bearer
  storage, eight-hour absolute expiry, session-bound CSRF and terminal revocation.
  Owner verified 63 guarded session cases passed in 51.63s against merge_test /
  0003_auth, three repetitions requested; fresh session invariants verified and
  fixtures retained. Codex checkpoint: 222 database-free tests; no PostgreSQL
  rerun. See SESSION_SERVICES.md for the trusted handoff, transaction
  authority and remaining limitations. M-007B.3A-R1 adds owner-approved
  validate_with_csrf plus four HTTP auth endpoints, strict JSON bodies, exact
  Origin/custom-header/Fetch Metadata checks, session-bound logout CSRF and
  separate production/development cookies. No lifecycle transaction changes.
  Owner verified 78 expanded session cases in 72.48s and 54 guarded API cases in
  40.90s against merge_test / 0003_auth (head), with fresh committed-state
  invariants. M-007B.3B now implements durable PostgreSQL fixed-window HTTP auth
  admission for review, with independent short transactions before KDF, HMAC
  identifiers and explicit actual-peer/single-hop proxy trust. Owner verified
  33 throttle cases in 31.42s, 54 updated API cases in 30.94s and 78 session
  cases in 48.33s: 165 passes in 110.69s, three repetitions requested and fresh
  committed-state invariants verified. Codex did not rerun PostgreSQL.
  See AUTH_THROTTLING.md and HTTP_AUTH.md.
  Browser/deployed HTTPS remains unverified; no team API or production-readiness claim.
- `hackathons(id, name, min_team_size, max_team_size, ...)` with `min>=1`, `max>=min`.
- `teams(id, hackathon_id, leader_user_id, min_team_size, max_team_size, version, deleted_at, ...)`. Member count is derived from rows; readiness is derived from count/minimum/deletion, with neither stored.
- Active-only `memberships(hackathon_id, user_id, team_id, joined_at)` with **PRIMARY KEY `(hackathon_id,user_id)`**, composite team/hackathon FK and unique `(team_id,user_id)` for the deferred leader FK. History belongs in audit.
- `invitations(id, team_id, token_hash UNIQUE, expires_at, revoked_at, created_by, ...)`.
- `join_requests(id, team_id, user_id, state, created_at, decided_at, decided_by, ...)` with sensible pending uniqueness.
- `idempotency_records(id, actor_id, hackathon_id, operation, key, request_hash, state, http_status, response_body, response_headers, created_at, completed_at)` with unique `(actor_id,operation,key)`. M-008C adds private success-only reservation/replay helpers on this unchanged schema. Owner verified 60 guarded merge_test cases in 40.82s at 0003_auth, three repetitions requested, fresh invariants verified; public mutation composition remains pending. See IDEMPOTENCY.md.
- `audit_events(id, actor_id, hackathon_id, team_id, action, old_state?, new_state?, occurred_at, ...)`.
- `outbox_events(id, aggregate_type, aggregate_id, event_type, payload, occurred_at, published_at?)`.

**Integrity details requiring migration-level design:**
- Ensure membership `hackathon_id` is consistent with its `team.hackathon_id` (composite foreign key or equivalent validated transactional rule).
- Ensure leader is a current member, including initial team creation and succession. If circular FKs complicate creation, use a controlled deferred constraint/transactional design; document concrete implementation.
- Capacity is a cross-row invariant and cannot be guaranteed by a naive CHECK. Parent-team locks and deferred final-state validation enforce capacity using actual membership rows; no stored counter exists.
- M-005B chose active-only membership storage; audit preserves history. M-006A provides database-enforced capacity/final-state checks, with the exact table/function definitions documented in `SCHEMA.md`.
- Soft deletion retains audit references but user-facing APIs and board must hide deleted teams.

## 5. Canonical transaction protocol (to finalize in first implementation PR)
All membership-changing operations must acquire locks in **one consistent order**. Proposed:
1. Authenticate/authorize and perform syntax validation before transaction.
2. Begin database transaction; establish idempotency ownership for operation (unique key, fingerprint, safe replay semantics).
3. Lock hackathon FOR SHARE, then serialize affected membership subjects with user-row **FOR NO KEY UPDATE** locks in sorted user-ID order. No new user lock may be acquired after a team lock.
4. Lock target `teams` row with **FOR NO KEY UPDATE** (if multiple teams, sorted team IDs), then future auxiliary request/invite rows. Leadership changes use the team lock; selecting a successor does not change its membership or acquire its user lock afterward.
5. Under lock, re-read team state and current membership; verify action permission, capacity, membership uniqueness, invite expiry, request state and leader rules.
6. Write membership/team updates, corresponding audit event, idempotency outcome and outbox record in the **same transaction**.
7. Commit; event dispatcher may publish committed outbox signal. Any rolled-back transaction produces no durable domain mutation or event.

**Lock-order warning:** User-before-team ordering is a proposal and must be checked against team creation, join approval, leader departure, and multi-member operations for deadlocks. Avoid reverse-order locks in any endpoint. Record final invariant proof and lock protocol in an ADR before scaling feature work.

### Last-seat race proof
- Team has exactly one free seat.
- Fire 50 independently authenticated requests concurrently against the same real PostgreSQL database.
- Locking serializes capacity mutation for that team; only the first eligible mutation can fill the seat.
- Remaining requests observe full capacity and return an explicit conflict response.
- Assertions: one newly inserted active membership, zero over-capacity, no duplicates, member-count matches rows, valid leader, correct audit/outbox count, no 500s. Repeat multiple runs.

### Cross-team race proof
- Same user submits two concurrent joins targeting different teams.
- Per-user lock (if used) and active membership UNIQUE constraint ensure at most one succeeds.
- Verify state in DB, not only HTTP responses.

### Idempotency
- M-008D adds internal create_team_idempotent/join_team_idempotent composition
  under TeamService._execute, with one audit/outbox pair and version per success.
  Owner verified 81 composed + 57 service + 60 idempotency cases on guarded
  0003_auth: 198 passed, corrected suite-time sum 201.63s, three repetitions
  requested per suite, fresh invariants verified. Public HTTP integration remains
  pending; see TEAM_MUTATIONS.md. Codex did not rerun PostgreSQL.
  Legacy methods remain internal compatibility facades, excluded from future HTTP.
- M-008C implements private primitives only: exact printable-ASCII keys, versioned
  canonical SHA-256 command hashes, ON CONFLICT reservation, separate fresh
  READ COMMITTED replay lookup and transaction-local successful completion.
  Pending cannot commit; failed mutations retain no record. The existing
  TeamService transaction owner and public methods are unchanged. The bullets
  below describe the future public integration, not a verified endpoint.
- Client sends `Idempotency-Key` on creation/join mutations.
- Atomic record uniqueness scoped to actor+operation+key; immutable fingerprint of meaningful request payload.
- Same key+same payload returns one recorded result; same key+different payload returns conflict.
- Concurrent same-key requests cannot each perform the operation; use locked or unique reservation semantics.
- Commit record and domain effect together; define behavior for a request crashing before commit (rollback allows retry) and after commit/before HTTP response (replay returns stored result).

## 6. Business-state policies (proposed)
- Team states: `forming`, `ready`, `deleted`. A team may have one founding member even if `min_team_size > 1`; readiness requires min members.
- Pending join requests never reserve capacity; leader acceptance invokes standard safe join.
- Invitation redeems to a join attempt, no guarantee of seat availability.
- Leader departure: deterministically select valid successor (e.g. earliest joined remaining member) within same transaction; if no members remain, soft-delete team.
- Team-deleted means absent from discovery and API mutations; history retained in audit.
- Team changes have actor/action/timestamp and old/new state where relevant.

## 7. API sketch (to be refined, not yet implemented)
```
POST /auth/register          POST /auth/login          POST /auth/logout
GET  /me                     GET  /hackathons/{id}/teams
POST /hackathons/{id}/teams  GET  /teams/{team_id}
POST /teams/{id}/invitations POST /invitations/redeem
POST /teams/{id}/requests    POST /requests/{id}/accept
POST /requests/{id}/decline POST /teams/{id}/leave
DELETE /teams/{id}/members/{user_id}
GET  /hackathons/{id}/suggestions
GET  /teams/{id}/audit       GET  /events
```
- Validate every payload and enforce authorization for read/write operations.
- Use consistent error mapping: `400/422` bad request, `401` unauthenticated, `403` forbidden, `404` absent/private, `409` capacity/membership/conflict, `429` rate limit.
- Use pagination and server-side filters for board endpoints.

## 8. Authentication, invites and security
- Prefer HttpOnly, Secure, SameSite cookies and server-revocable sessions. If using cookies, include CSRF protection on state-changing requests (SameSite alone may not be sufficient).
- Password hashes with a maintained password KDF (e.g. Argon2id); never log passwords or raw invite tokens.
- Invitation tokens generated with cryptographic RNG, sufficient entropy (e.g. >=128 random bits), stored as hashes, expiration and revocation checked server-side, rate-limited per identity/IP.
- Team leader verification always server-side within transaction.
- Bound pagination, normalize and validate skills/timezone strings, escape user-provided content at render, and configure CORS narrowly.
- Test unauthorized access and IDOR cases.

## 9. Realtime strategy
- Server writes an outbox event in the same transaction as the relevant team mutation.
- Dispatcher publishes **after commit** to connected SSE clients; events can be duplicated or missed if disconnected.
- Clients invalidate cached team/board queries and refetch authoritative state (TanStack Query recommended).
- Reconnection must always re-fetch latest state; optionally use event IDs/replay to reduce refresh cost.
- For multiple API replicas, implement shared fanout before asserting robust cross-instance live delivery.

## 10. Teammate recommendations
- Filter to eligible, discoverable, currently unassigned users for given hackathon.
- Score skills complementary to team's existing coverage and timezone overlap. Initial documented formula suggestion: `0.7 * skill_complement + 0.3 * timezone_overlap` (both normalized to [0,1]).
- Score ties deterministically. Publish explanation in endpoint/README; add positive and negative cases in unit tests.
- This is deterministic matching, not a requirement to use ML/LLMs.

## 11. Performance and observability
- For the board query: indexed hackathon/team status and paging, avoid N+1, bounded result sets, inspect `EXPLAIN ANALYZE` before tuning.
- Seed script creates 10k users and 2k teams, ideally deterministically with an idempotent/resettable mode that requires confirmation before destructive changes.
- k6: 100 concurrent VUs, enough duration for warm and sustained periods; report p50/p95/p99, request rate, error %, actual dataset, server hardware/region and test script. Fail target if p95 >=200ms or errors are significant.
- Structured logs, request IDs, errors and slow SQL timings. Optional tracing only after must-haves.

## 12. Repo layout (incremental)
```
merge/
├── AGENTS.md
├── backend/
│   ├── app/{api,core,db,models,schemas,services,realtime}/
│   ├── tests/
│   ├── alembic/
│   └── pyproject.toml
├── frontend/src/{components,features,pages,hooks,lib}/
├── docs/{REQUIREMENTS,ARCHITECTURE,DECISIONS,PROGRESS}.md
├── scripts/
├── load-tests/
├── .github/workflows/
├── compose.yaml
├── .env.example
└── README.md
```
Folders beyond `docs/` are **proposed**; create only as tasks need them.

## 13. Build sequence / gates
- **G0:** Docs, repo, local Postgres backend/frontend minimal smoke tests.
- **G1:** Schema + join service; repeated 50-way race and cross-team join tests pass with real PostgreSQL.
- **G2:** All lifecycle paths, idempotency, authZ, invite security, audit pass.
- **G3:** Full React flow, SSE, matching, mobile/keyboard E2E pass.
- **G4:** CI >=20 API tests, seed verified, k6 board p95 <200ms in declared environment.
- **G5:** Working public deployment, one-page design, benchmark report, <=5-min demo, submitted links.

## 14. Known limitations / decision gates
- M-006B provides a separate opt-in local merge_test target and dedicated online
  migration runner using unchanged versions. Owner verified 45 database-level
  adversarial cases in 39.72s (three repetitions); see TEST_DATABASE.md/PROGRESS.md.
  Ordinary backend configuration remains merge_dev. Service/API races remain open.
- M-006A adds concrete schema, deferred leadership/final-state integrity and immutability guards. APIs, full service lock protocol, auth, idempotency replay, audit generation and dispatch remain future work. Schema tests do not prove 50-way service races.
- Phase 0 uses the owner's existing local PostgreSQL 17 server, dedicated `merge_dev` database and non-administrative `merge_app` role; manual provisioning is required when credentials are unavailable. Docker is optional and unverified. See the dated setup clarification in `DECISIONS.md`.
- Deployment provider and database hosting must be chosen after checking availability and cold-start constraints.
- SSE scaling across multiple instances is not solved merely by adding a transactional outbox.
- Counts/readiness are derived; future services must count in a fresh statement after taking the team lock, not use stale loaded ORM values.
- Browser-only or SQLite tests cannot prove cross-process PostgreSQL race correctness.

# Authenticated discovery reads — M-010A

M-012A now adds POST on the existing scoped teams collection, without changing
any GET response, pagination or My Team null contract. Earlier statements about
GET-only routes and no public mutations describe M-010A history. Creation is
defined separately in [TEAM_API.md](TEAM_API.md); no public join or other lifecycle
route is added.

Checkpoint against `0372c85caa59f0a114f6634957dd8f61f2e64b19`, revision
**0003_auth**: owner verified **87 authenticated read API cases in 73.35s** and
**54 authentication API regressions in 28.28s**, **141 passed**, suite-time sum
**101.63s**. Three repetitions requested; one existing Starlette/HTTPX warning.
These are owner-run PostgreSQL results, not Codex database executions. The guarded
harness retains fixtures and checks fresh committed invariants. Final checkpoint
offline/static evidence is in PROGRESS.md. No mutation HTTP route, migration,
dependency or frontend change. G1 remains open.

## Access and response contract

The current schema has no enrollment, tenant, private-hackathon or visibility
policy. Under the owner-authorized discovery scope, every valid authenticated
account may read hackathon metadata and live team summaries, including teams it
has not joined. Every team/cursor lookup is scoped server-side to its hackathon.
This does not grant admission, leadership, invitation/request or mutation rights.
Future visibility/enrollment rules require a separate approved design.

All four GET routes require the existing PostgreSQL-validated session cookie.
There is no actor field, bearer-header or X-User-ID authentication. Authenticated
requests supplying X-User-ID/X-Actor-ID or unsupported query fields receive 422;
without a cookie, they remain unauthenticated (401). The actor for `/me/team`
comes only from the validated principal. No usernames, credential/session data,
CSRF, roster, creator, audit/outbox or idempotency material is returned.

| GET endpoint | Success |
| --- | --- |
| `/api/hackathons?limit=20&cursor=<uuid>` | `{items: Hackathon[], next_cursor: uuid|null}` |
| `/api/hackathons/{hackathon_id}/teams?limit=20&cursor=<uuid>` | `{items: Team[], next_cursor: uuid|null}` |
| `/api/hackathons/{hackathon_id}/teams/{team_id}` | `Team` |
| `/api/hackathons/{hackathon_id}/me/team` | `{team: Team|null}` |

All successes are 200. A Hackathon is exactly `id`, `name`, `min_team_size`,
`max_team_size`. A Team is exactly:

```json
{
  "id": "00000000-0000-0000-0000-000000000002",
  "hackathon_id": "00000000-0000-0000-0000-000000000001",
  "name": "Example team",
  "min_team_size": 2,
  "max_team_size": 4,
  "member_count": 1,
  "readiness": "forming",
  "leader": {
    "user_id": "00000000-0000-0000-0000-000000000003",
    "display_name": "Public display name"
  },
  "created_at": "2026-11-10T00:00:00Z"
}
```

These illustrative UUIDs are not seeded data or live evidence. Readiness is
`ready` exactly when actual count >= minimum, otherwise `forming`. Counts are
actual membership rows, never a stored counter. Leader is a public display
reference, not an account username. Details intentionally reuse this small
summary contract; a full/paginated roster is not part of this milestone. No
version field or arbitrary ORM/auth object serialization is exposed. Pydantic
models forbid extra fields and reject inconsistent response sizes/count/readiness.

## Pagination, scope and errors

Both lists default to limit 20 and accept only integer limits 1–100 plus an
optional UUID cursor. Duplicate/unknown query parameters, invalid UUIDs and bounds
receive sanitized 422. Detail and current-membership routes accept no query fields.
No offset, unbounded list, total-count query or client-selected SQL ordering.

Hackathons order by primary-key `id ASC`; cursor means strictly greater than
that UUID, whether or not it currently names a row. Teams order by
`created_at DESC, id DESC`. Their cursor names a team in the same hackathon;
the server loads its immutable timestamp/ID as the exclusive keyset boundary.
A nonexistent/cross-hackathon team cursor is 422. A retained tombstone remains
a valid anchor but is never returned. The next cursor is the last returned ID
only when a limit+1 lookahead proves another row. Last/empty pages return null.
Ordering is deterministic, including timestamp ties; separate pages are separate
snapshots, so new rows before a cursor require a refresh to discover.

Existing empty hackathon -> 200 empty teams; missing hackathon ->
404 `hackathon_not_found`. Missing, deleted or cross-hackathon team ->
404 `team_not_found`. No membership in an existing hackathon -> 200 `{team:null}`.
Missing/malformed/forged/expired/revoked session -> 401 `invalid_session`.
Database/configuration/unexpected/response-validation faults -> sanitized
503 `service_unavailable`, without SQL, driver text or submitted values.
Errors use existing `{error:{code,message,retryable}}`; new read errors have
retryable=false. Clients should branch on code/status, not message wording.

For an authenticated user with no membership in an existing hackathon,
`GET /api/hackathons/{hackathon_id}/me/team` returns **HTTP 200**,
Content-Type `application/json`, Cache-Control `no-store, private`, and exactly:

```json
{"team":null}
```

It is not a 404 or an empty team object. A missing hackathon still returns 404
`hackathon_not_found`.

## Security, transactions and query design

The existing AuthBoundary also wraps `/api`, retaining actual-peer/trusted-proxy,
production HTTPS, exact supplied-Origin and Fetch Metadata checks. Same-origin
GETs may omit Origin; cross-site/sibling origins remain rejected. There is no
CORS middleware/reflection. All `/api` responses, including errors/404/405,
receive Cache-Control `no-store, private`, Pragma `no-cache`, Expires `0` and
nosniff. Reads do not set/renew cookies or return CSRF. GET requires neither a
CSRF header nor the register/login custom header. Existing `/auth` policy is
otherwise unchanged. Session validation precedes domain reads; revocation cannot
cancel work already authenticated in another request, as documented for auth.

`get_read_service` reuses the lazy runtime Engine already owned by authentication;
it creates no engine, reads no Settings/env file and disposes nothing independently.
Tests override both auth and read dependencies. `/health` and missing-cookie
requests do not initialize a database. The service accepts an Engine, guards
synchronous PostgreSQL/psycopg, actual DBAPI autocommit=False, no existing
transaction and READ COMMITTED, then owns a short transaction with server-enforced
`SET TRANSACTION READ ONLY`, lock timeout 5s and statement timeout 15s. No row
write locks, retries, domain writes or external calls. TeamService is unchanged.

Each operation materializes exactly one domain SELECT before returning. Team
rows, leader display, derived count, hackathon/cursor validation and own membership
are read in that single statement's snapshot. No second roster/count query can
mix old team state with newer membership. Concurrent commits may produce a newer
snapshot on the next HTTP request; no cross-request snapshot is promised.

Team paging uses existing `ix_teams_board(hackathon_id,created_at DESC,id DESC)`
for live rows, a primary-key cursor lookup, and an inner limited page before count/
leader projection. Counts can use the existing `(team_id,user_id)` index; own
membership uses `(hackathon_id,user_id)`; catalog uses the hackathon primary key.
All values are bound parameters, including UUID NULL casts and limit+1 <=101.
These are query/index design observations, not EXPLAIN or performance measurements.
No migration or permission change is needed or performed.

## Tests and guarded owner run

Offline tests cover HTTP authentication and browser-policy failures, forged
identities, bounds/UUIDs, fixed errors, private fields, lazy wiring, read-only SQL
ordering/parameters, one statement, exact projection and transaction guards.
A database-free fixture-construction test exercises the guarded app wiring too.
These doubles are not PostgreSQL concurrency evidence.

`--suite reads` selects only `read_api_tests`, requires explicit 0003_auth before
credentials, and retains UUID fixtures. Every fixture/service/observer connection
verifies merge_test / merge_app, READ COMMITTED and exact revision. Fresh independent
checks verify original team invariants plus scoped session validity and zero
idempotency/audit/outbox fixture effects. Test-only registration/session issuance,
team seeding, legal tombstone INSERT and legacy internal admission create the
fixtures; no mutation is exposed over HTTP and there is no destructive cleanup.

The 87 read executions (29 scenarios x3) include real expired/revoked sessions,
scope/deletion/cursor behavior, deterministic pages, counts, UUID/bounds, actual
AUTOCOMMIT rejection and transaction_read_only checks. A writer is held after
membership INSERT and before COMMIT; independent HTTP list/detail/current-team
reads must see the coherent old committed state without waiting for the writer.
After release they must see count/readiness/own membership from the new state.
Event waits are 8s and workers share a 30s join bound, with server deadlines.
Unexpected errors/timeouts fail; no broad outcomes are accepted as passes. If a
worker deadline fails, stop and inspect before any rerun. No natural-race/load,
50-way HTTP, CI, browser or production result is claimed.

For reproduction, run interactively without transcripts, using the hidden prompt:

```powershell
Set-Location I:\Merge\backend
Remove-Item Env:MERGE_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m test_support.database verify --confirm-merge-test --revision 0003_auth
if ($LASTEXITCODE -ne 0) { throw 'Database verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite reads --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'M-010A read API verification failed. Stop.' }
.\.venv\Scripts\python.exe -m test_support.concurrency --confirm-merge-test --suite auth-api --revision 0003_auth --repetitions 3
if ($LASTEXITCODE -ne 0) { throw 'Authentication API regressions failed. Stop.' }
```

These commands verify/test, never migrate/reset/drop. **Not run by Codex**.
The prior M-008E 252 owner-verified passes remain separate baseline evidence;
the current M-010A results are recorded above. Original mutation/service sources
remain unchanged; current
offline regressions include them. No credential or ordinary development DB access.

## Next frontend integration

M-011A implements this integration for owner review: authentication forms/session
bootstrap, hackathon and team pages, details and exact null/present membership
states. Vite now includes the same-origin `/api` proxy, preserving Origin and
the controlled launcher convention. Typed relative cookie-authenticated fetches
never send actor IDs or identity headers; navigation/session changes cancel and
ignore stale responses. Names are text, counts are fetched snapshots and join
is visibly disabled. No public team mutation is added. Component/build and safe
proxy evidence, browser prerequisites and remaining work are in FRONTEND.md.
Production must still route /api under the same trusted HTTPS origin; deployed
HTTPS and authenticated browser integration remain unverified.

Owner exercise: hold a join before COMMIT and explain why count and `/me/team`
remain old; change the offline page limit and predict the exact lookahead/next
cursor without changing the ordering or weakening the database constraints.

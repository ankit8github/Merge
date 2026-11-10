# PostgreSQL domain schema — M-006A

M-007B.1 adds authentication storage in additive 0003_auth. Owner verified guarded
merge_test migration/repeat, 0003_auth (head), preserved domain row counts and
fingerprints, and 78 live auth schema cases in 11.75s (three repetitions requested).
Codex checkpoint checks are database-free. Existing 0001/0002 and domain guards remain unchanged.
Exact storage decisions and explicit owner commands: [AUTH_SCHEMA.md](AUTH_SCHEMA.md).

This is the approved schema foundation, not an implementation of team APIs,
authentication, idempotency services, audit generation or event delivery.
Verification commands and measured results are in `PROGRESS.md`.

## Objects and invariants

`0002_domain` follows the unchanged `0001_baseline` and creates seven tables:
`users`, `hackathons`, `teams`, `memberships`, `idempotency_records`,
`audit_events`, and `outbox_events`. Users are minimal principal references;
there are no credentials or session tables. No roles/permissions are modified.

- Memberships contain current rows only. Their immediate primary key is
  `(hackathon_id, user_id)`; `(team_id, user_id)` is also unique.
- A composite FK binds membership `(team_id, hackathon_id)` to its team.
- Teams copy min/max sizes with a composite FK to the hackathon configuration.
  `ON UPDATE RESTRICT` freezes sizes once a team exists, including tombstones.
- `fk_teams_leader_member` references membership `(team_id, user_id)` from team
  `(id, leader_user_id)`, `MATCH SIMPLE`, `NO ACTION`, initially deferred.
- A row CHECK requires non-null leader on a live team and null leader on a
  deleted team. Deferred validation requires live count in `1..max_team_size`
  and deleted count zero. Minimum is a readiness threshold, not an admission or
  departure restriction. Counts always come from actual memberships.
- There is no stored count or readiness column. The ORM count is a correlated
  query expression; readiness is a property. Refresh an already-loaded ORM
  instance after membership writes; future mutation services must use fresh
  locked queries rather than an identity-map value for admission decisions.
- Team IDs, hackathon assignment, size copies, creator and creation timestamp
  are immutable. All membership UPDATEs are rejected. User/hackathon primary
  IDs are immutable. Teams cannot be physically deleted or resurrected;
  tombstones cannot be changed. Deleting the last membership must be paired
  with leader-null/soft-delete update in the same transaction.
- Statement-level BEFORE TRUNCATE guards cover all seven domain tables.
  No destructive reset is part of setup or tests.

## Functions, locks and final validation

All five `public.merge_*` functions are VOLATILE, SECURITY INVOKER, with fixed
`search_path = pg_catalog, pg_temp`. Every application table reference in their
bodies is explicitly `public` qualified. There is no dynamic SQL.

`merge_lock_membership_team` locks the parent with `FOR NO KEY UPDATE` before
membership INSERT/DELETE. INSERT into a tombstone is rejected immediately.
`merge_validate_team`, called by initially deferred constraint triggers on
teams and memberships, re-reads the final team under that same lock, then counts
memberships in a separate query with a fresh READ COMMITTED snapshot. It never
validates historical NEW/OLD contents as the final state. Temporary overflow or
founderless intermediate rows are permitted inside a transaction, but invalid
final states cannot commit with triggers/constraints enabled.

The deferred FK independently verifies leadership. All INSERT/DELETE paths
serialize on the parent. Supported services must additionally acquire locks in
this order: idempotency reservation; hackathon FOR SHARE; affected membership
subjects' user rows FOR NO KEY UPDATE in sorted order; team rows FOR NO KEY
UPDATE in sorted order; future auxiliary request/invite rows; membership DML;
audit/outbox/outcome. Never obtain a new user lock after a team lock. Membership
FK checks can take KEY SHARE locks, compatible with NO KEY UPDATE. Direct raw
DELETE can lock a membership tuple before its trigger locks the team and can
deadlock with a service; PostgreSQL victim rollback preserves integrity. Later
services need whole-transaction bounded retries for 40P01/40001 and explicit
handling of lock deadlines. This component does not implement retry services.

ORM metadata uses the unnamed default schema, matching PostgreSQL's FK
reflection. The engine's schema translation explicitly compiles that schema as
`public`, including when a caller's search_path excludes public. The migration
is a frozen public-qualified DDL snapshot, independent of future model edits.
Alembic loads the model registry and checks all schema objects; FK drift is not
filtered out to make comparisons pass.

## Supporting transactional records

M-008D adds composed team/idempotency/audit/outbox writers on this unchanged
schema. Owner verified 81 composed, 57 service and 60 idempotency cases: 198 passed
on guarded 0003_auth, three repetitions requested per suite and fresh invariants
verified. Exact timings, payloads and rollback guarantees are in TEAM_MUTATIONS.md.
No dispatcher or schema/migration change is introduced.

Idempotency has immediate uniqueness `(actor_id, operation, key)`, a 32-byte
fingerprint, bounded printable-ASCII key and checked pending/completed response
shape. A deferred trigger reads final state and rejects a committed pending
record. Scope/fingerprint and completed outcomes are immutable; deletion is
rejected. M-008C adds private reservation/replay/completion helpers using these
unchanged constraints. Owner verified 60 guarded cases in 40.82s at 0003_auth,
three repetitions requested, fresh invariants verified; public composition is pending.
See IDEMPOTENCY.md. No retention worker, lease, expiry or schema change is added.

Audit has unique operation and `(team_id, team_version)` references; records are
append-only. Outbox has one row per audit event and immutable identity/payload;
only publication timestamp/attempt count can change. These are constraints for
future writers, not automatic audit generation. Services must still atomically
write the effect, outcome, audit and outbox. Database-owner trigger disabling,
arbitrary DDL and privileged maintenance are outside the runtime threat model.

## Stable database diagnostics

Future services must inspect SQLSTATE **and the named constraint**, not parse
human messages or map every integrity error to HTTP 409.

| SQLSTATE | Constraint/example | Meaning |
|---|---|---|
| 23505 | `pk_memberships`, `uq_idempotency_scope` | Assignment/key uniqueness conflict |
| 23503 | `fk_memberships_team_hackathon` | Missing/mismatched team/hackathon |
| 23503 | `fk_teams_leader_member` | Leader is not a member at validation |
| 23503 | `fk_teams_hackathon_sizes` | Frozen size change or bad size copy |
| 23514 | `ct_team_capacity` | Final actual membership count exceeds max |
| 23514 | `ct_team_nonempty` | Live team would be empty |
| 23514 | `ct_team_deleted_empty`, `guard_team_deleted` | Invalid deleted-team state/admission |
| 23514 | `guard_membership_immutable`, `guard_team_identity` | Forbidden identity/membership update |
| 23514 | `guard_team_tombstone`, `guard_team_soft_delete` | Forbidden resurrection/hard deletion |
| 23514 | `guard_domain_truncate` | Forbidden domain TRUNCATE |
| 23514 | `ct_idempotency_completed`, `guard_idempotency_*` | Incomplete/changed retained outcome |
| 23514 | `guard_audit_append_only`, `guard_outbox_*` | Forbidden transactional-record modification |
| 40P01 / 40001 / 55P03 | PostgreSQL transaction errors | Deadlock / serialization / lock timeout; not capacity outcomes |

Unexpected constraint failures are implementation faults until classified.

## Migration and tests

From `backend`, use its venv interpreter with:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m pytest -q --tb=short
```

The migration checks for existing domain table/routine names and stops rather
than absorbing/replacing them. All DDL runs in Alembic's PostgreSQL transaction.
Downgrade refuses execution because dropping populated domain tables needs a
separate owner-approved procedure. No schema reset or 0001 edit is performed.

Schema tests use UUID-scoped fixtures in outer rollback-only transactions.
`SET CONSTRAINTS ALL IMMEDIATE` runs actual deferred PostgreSQL checks before
rollback, not mocks. Founderless/over-capacity tests also exercise real failing
COMMITs, whose fixture inserts are atomically rolled back. Successful fixtures
are not durably committed. TRUNCATE tests first verify the guard is installed,
then assert statement rejection; no fixture cleanup uses TRUNCATE or disables
triggers. Metadata comparison includes FK/type/default comparison. Repeat
upgrade tests run against the existing head and do not reset the database.

These tests are schema checks, not 20 API tests or the required 50-way race.
M-006B adds an isolated merge_test suite: owner verified 45 database-level
adversarial cases in 39.72 seconds with three repetitions and fresh-state checks
(2026-11-08). See TEST_DATABASE.md/PROGRESS.md. This covers the implemented
multi-connection schedules; service authorization/retries, the 50-way HTTP race,
deployment and board performance remain separate acceptance work.

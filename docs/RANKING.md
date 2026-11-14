# Profiles and deterministic teammate ranking — Batch A

Pre-implementation contract, 2026-11-14. Owner-authorized additive APIs/schema;
proposed ADR-009 refinement for review, with no change to membership, session,
locking, stored mutation replies, SSE publication or old acceptance scopes.

## Component / acceptance

New backend profile DTO/API/service/model and matching service; one additive
0006_profiles migration (offline rendering only). New React profile/ranking UI,
private GET labels, field validation and lifecycle wording. No new dependency.
Test strict skills/zones, empty skills, exact scores/ties, eligibility, permission,
scope/cursor bounds, optimistic conflicts, identity/navigation isolation and
existing SSE/lifecycle journeys. Preserve all prior SSE work and guarded cases.

## API / schema proposal

GET /api/me/profile returns authenticated user's account name/username and
skills (max 20), timezone (IANA or null), discoverable (default false), version
(default 0). POST same path fully replaces own skills/timezone/discoverability,
with expected version. Existing cookie, exact Origin, strict JSON and current
session CSRF required. No actor selector or arbitrary-user update. CAS version
rejects stale edits with 409 profile_changed; after unknown delivery refetch
before editing. No automatic mutation retry. Profile changes create no team
change, audit/outbox or membership and do not change auth identity.

public.participant_profiles: user_id primary/FK to users, skills varchar(32)[]
(default empty), timezone varchar(64) nullable, discoverable boolean default false,
version bigint positive. Missing rows behave as private/empty version 0. Database
checks bound skill syntax/count and timezone shape; application validates zones
against installed IANA data using Python zoneinfo. OS/IANA tzdata is a runtime
prerequisite (598 zones available in the inspected environment); no network lookup.
Skill labels trim/lowercase, deduplicate and sort; 1–32 ASCII letters/digits then
letters/digits/plus/hash/dot/hyphen, max 20 input entries. No skill taxonomy/ML.
Raw individual labels are capped at 64 characters before normalization.
Opt-in requires a timezone; empty skills are allowed and earn zero skill credit.
Saved profiles also contribute to the current team's coverage/overlap even when
not discoverable as a candidate; the editor discloses this. Leaders see aggregate
team skills, and candidate fields only for opted-in, eligible users.

GET /api/hackathons/{h}/teams/{t}/suggestions?limit=20&cursor=... requires the
current leader of a live team. No actor selector. Candidate eligibility: an
existing credentialed, discoverable account, not caller, no membership in this
hackathon. Accounts need no nonexistent event-enrollment state; opt-in is global.
A full team yields no suggestions. Pending requests/invites reserve no seats.
Returned IDs are public identifiers, never permission to invite/join; existing
mutation services recheck all invariants. Deleted/foreign team 404, nonleader 403.

## Deterministic formula

Keep architecture weights: score = 100 * (0.7 * skill_complement + 0.3 * timezone_overlap).
Team coverage is the union of current members' skills. skill_complement is
|candidate skills minus team coverage| / |candidate skills|; empty candidate skills
score 0. No desired-skill catalog exists, so explain novelty rather than invent
team requirements. This rewards complementary coverage, not self-declared depth.

Timezones approximate shared working hours, not availability commitments. Assume
09:00–17:00 local, compute circular UTC offset distance at server UTC day's noon,
and overlap = max(0, 480 - distance_minutes) / 480. Average across ALL current team
members; missing member timezone contributes 0. Return reference_at, candidate
zone, novel skills, team coverage, normalized components and weighted points.
DST changes with the returned reference day and installed tzdata. Exact Fraction
arithmetic orders scores before display rounding; ties use UUID ascending.

One read-only SQL snapshot supplies current leadership/capacity, profiles and
candidate eligibility. Bound materialization to 10,001 candidates/members and
reject over 10,000 rather than silently rank a partial pool. Limit 1–20. Cursor
binds actor/hackathon/team/reference day and canonical ranking snapshot digest
plus offset (bounded 10,000); any relevant change gives 409 ranking_changed.
No stored snapshots, signing secret, SQL interpolation or actor authority in cursor.
Clients restart on change. Ranking scans/sorts the bounded pool; cost unmeasured.
The SQL result is materialized and the connection closes before CPU scoring.
Member offsets are counted once and exact overlap is reused per candidate zone.

## UX / compatibility

Profile editing is explicit and account-scoped. Leader rankings load on demand,
show explanations and select a labelled recipient into the existing UUID form.
Canonical team invalidations refresh mounted ranking reads; profile edits and
other profiles require explicit ranking refresh (no fabricated outbox events).
Read refresh must preserve inputs and lifecycle confirmation. Private pending GET
rows gain applicant names/usernames; private inbox rows gain team/recipient labels.
Stored mutation replies stay byte-for-byte unchanged; older DTO fixtures may omit
additive label fields and UI retains identifier fallback. UUID lookup stays.
Full-catalog name search is deferred: not necessary for this bounded component.

0006 is NOT applied or added to old runner revision allowlists. Existing exact
0005 SSE/lifecycle cases remain unchanged and collect only. Old browser hosts
exclude the new profile/ranking router before their unchanged closed audits;
no manifest, budget, ledger or auth/dependency scope is broadened. Fresh live
profile/migration/ranking acceptance and browser scope need separate owner review.
Offline mocks/SQL rendering are not PostgreSQL acceptance or load evidence.

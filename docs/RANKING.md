# Profiles and deterministic teammate ranking — Batch A

Pre-implementation contract, 2026-11-14. Owner-authorized additive APIs/schema;
proposed ADR-009 refinement for review, with no change to membership, session,
locking, stored mutation replies, SSE publication or old acceptance scopes.

## Profile editor refinement — 17 November 2026

Owner-approved local implementation supersedes the original manual-entry UX below,
without changing the stored/API skill rules, schema, ranking or authorization.

The editor accepts internal ASCII space runs as hyphens after trimming/lowercasing;
it previews the exact deduplicated/sorted labels that will be sent. Count all
entered comma-separated labels before deduplication (maximum 20); reject empty
entries, unsupported characters and canonical labels longer than 32. Empty skills
remain allowed. Existing punctuation/hyphens are not rewritten; no taxonomy,
fuzzy matching or synonym merging beyond this explicit input alias is introduced.
Direct API callers still cannot store spaces. Backend raw-label limits stay intact.

### Authenticated zone catalogue

`GET /api/profile/timezones` returns only `{"items": ["…"]}`: a sorted unique list
of identifiers in the installed `ZONES` set accepted by the existing validator,
excluding `localtime`, `Factory` and identifiers exceeding the 64-character field
bound. Require 1–2048 entries; an empty/oversized catalogue yields sanitized 503,
never truncation. Existing authenticated same-origin read policy/private no-store
headers apply; no query/actor parameters or POST. No profile/membership service,
external lookup, domain mutation, audit/outbox event or schema access is added.
Authentication still performs its existing session validation.

The frontend checks response keys, types, count/identifier bounds, ordering,
duplicates, prohibited names and malformed path segments. It uses these identifiers
for selection/validation, never browser Intl canonicalization. Saved aliases stay
exact. Search text is separate from selection; unfinished search blocks submission.
Browser-detected zones are optional buttons only when present in the server list.
Catalogue failure disables selection/save and offers explicit read retry; drafts
remain. The picker renders at most 50 matches, announces the total and asks users
to narrow a broader search; the API catalogue itself is complete.

### Drafts, versions and recovery

The account/session-scoped panel owns memory-only draft values, search, baseline
version and recovery state. Closing hides the editor without destroying these or
cancelling an in-flight save. Account/credential replacement and logout fence and
abort requests. Existing session-revalidation behavior remains unchanged.

Blur/submit validate fields; an erroneous field updates on correction. Discovery
changes immediately revalidate the zone requirement. A definite `422 invalid_request`
retains an editable draft and its server error until a meaningful payload change or
explicit recovery. Other failures, including unknown 422/malformed acknowledgements,
freeze edits and require canonical GET. Reload shows current server state separately,
keeping the draft and old expected version. Explicit "Keep draft for a new save"
adopts the observed version without POST; "Discard draft and use saved profile"
replaces the draft. Only another explicit Save sends a write. A matching GET cannot
prove an uncertain earlier write failed, and CAS still guards later completions.
No persistence, automatic replay/rebase, migration or backend-rule relaxation.

Current integrated host audit adds only the authenticated catalogue GET (25 routes
including health, nine unchanged service overrides). Legacy profile-router exclusions
remain unchanged; receipts and old fixture scopes are not recertified. Verification
and browser/real-PostgreSQL limits: [TESTING.md](TESTING.md).

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

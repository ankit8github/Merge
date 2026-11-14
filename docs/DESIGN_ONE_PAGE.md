# Merge | PS1 technical design

**Purpose.** Form hackathon teams without overfilling seats, duplicate membership
or leaderless teams. Individual submission; the owner must defend AI-assisted
code. Deadline:15 November2026,23:59 IST.

**Topology.** React/TypeScript -> same-origin HTTPS Caddy -> one FastAPI worker ->
private PostgreSQL. PostgreSQL is authoritative; process memory never grants a
seat. Proposed VPS packaging separates runtime/migration roles and persistent
DB/certificate volumes. Public hosting is not verified.

**Data.** Users/credentials/sessions; hackathons with min/max size; versioned teams
with leader/tombstone; memberships keyed by `(hackathon_id,user_id)`; requests/
invitations; idempotency, audit/outbox and optional skills/zone profiles. Foreign
keys bind scope and leader membership. Deferred triggers validate final capacity,
nonempty live teams and completed idempotency. Last departure soft-deletes.

**Transaction.** Reserve caller/operation/key plus command hash, then lock the
hackathon, affected users in UUID order, team and grant/request. Check current
authorization, eligibility and actual count while serialized. Commit membership,
succession/deletion, version, audit/outbox and canonical response together.
Constraints are the final backstop. Bounded retries preserve command/key;
ambiguous COMMIT reconciles stored outcome. Succession uses joined_at then UUID.
No application mutex; pending requests reserve no seats.

**Security/UX.** Argon2, database sessions/token hashes, Secure HttpOnly host-only
cookie, exact HTTPS Origin, CSRF and durable throttles. One trusted proxy replaces
forwarding headers; API/DB ports stay private. Server authorization governs every
private read/action. React covers discovery, creation, requests/decisions, private
invites, leave/remove, confirmations and explicit retry recovery. Only public
navigation hints persist; secrets/commands stay in memory.

**Realtime/matching.** Short read-only SSE polls count committed subscriber-visible
outbox facts; reconnect resets canonical reads. Frames reveal no private domain
payload; no transaction spans network waits. This is invalidation, not ordered/
exactly-once delivery. Deterministic ranking gives70 points for candidate-skill
novelty against team coverage,30 for average assumed09:00-17:00 zone overlap.
Opt-in, same-hackathon membership/capacity/leader checks, explained components,
exact fractions, UUID ties and bounded snapshot pages. Self-reported fields are
proxies, not AI or actual availability.

**Evidence/trade-offs.** Prior local G1:13 invitation cases x3, including three
50-caller last-seat races (1 success/49 safe rejections); local lifecycle acceptance
also exists. Public CI, current SSE/profile PostgreSQL,10k/2k seed,100-VU p95<200ms
and deployed HTTPS/browser evidence remain pending. Offline tests cannot certify
races/TLS/load. History-growing SSE COUNT and10k candidate ranking need measurement;
one VPS is a failure domain. No broker or full-catalog name search.

**One more week.** Complete browser/accessibility and backup restore drills;
measure history-heavy SSE/ranking/board queries; fix worker-test flakiness; add
alerts and measured retention policy; review dependencies/images and automate
reproducible release evidence.

Details: README.md, PRODUCTION.md, G1_ACCEPTANCE.md, RELEASE_VALIDATION.md.
One-page text source; exported pagination needs checking before submission.

# Merge — PS1 Requirements & Acceptance Criteria

**Status:** Specification captured; implementation not yet verified. **Checked:** 2026-11-06.
**Organizer:** Hack4Hack Crew Hiring Challenge 2026. **Problem:** PS1 · Race-proof team formation at scale.
**Official source:** https://hack4hack.com/hackathons/hack4hack-crew-hiring-challenge-2026-tp3m
**Submission deadline:** 2026-11-15, 23:59 IST. **Participation:** individual; AI coding tools allowed, original work, explain every line.

## Classification
- **OFFICIAL:** Required or optional content explicitly advertised by organizer (paraphrased).
- **DESIGN POLICY:** Our proposed clarification or implementation behavior; not a rule imposed by organizer.
- **ACCEPTANCE:** Repeatable evidence needed to treat a feature as verified.
- All IDs below start **PENDING** until backed by test logs, CI run, screenshots, report or review.

## Organizer-required features

| ID | Type | Requirement | Verifiable acceptance evidence | Status |
|---|---|---|---|---|
| R-01 | OFFICIAL | Configure minimum/maximum team size | Create teams under a configured hackathon; verify capacity and min-size policy | PENDING |
| R-02 | OFFICIAL | One team per participant per hackathon | Two concurrent attempts to join distinct teams cannot result in two active memberships | PENDING |
| R-03 | OFFICIAL | Expiring invitation codes | Accept valid code; reject expired/revoked/invalid code; no raw code in logs | PENDING |
| R-04 | OFFICIAL | Leader can accept/decline join requests | Non-leader receives 403; leader outcome persists | PENDING |
| R-05 | OFFICIAL | Leader leaving transfers leadership | After leader leaves a nonempty team has valid leader who is a member | PENDING |
| R-06 | OFFICIAL | Last person leaving deletes team | Last departure makes team unavailable; no active orphan memberships | PENDING |
| R-07 | OFFICIAL | Race-proof last-seat join | 50 distinct authenticated callers, one available seat: exactly 1 success, 49 safe rejections, capacity never exceeded, rerunnable against real DB | PENDING |
| R-08 | OFFICIAL | Idempotent retries for join/team creation | Same idempotency key/payload produces one effect; retry returns stable outcome | PENDING |
| R-09 | OFFICIAL | Realtime board and team updates, no refresh, via SSE or WebSockets | Two browser sessions see updates on changes without manual refresh | PENDING |
| R-10 | OFFICIAL | Authentication and leader-only accept/decline/remove | AuthN/AuthZ negative cases plus user/leader end-to-end flows | PENDING |
| R-11 | OFFICIAL | Invite codes resistant to brute force; rate limits; validated inputs | Entropy rationale; repeated bad attempts throttled; malformed inputs rejected | PENDING |
| R-12 | OFFICIAL | Audit log for every team change: who/what/when | Audit entries exist for every committed mutation; none for rollbacks | PENDING |
| R-13 | OFFICIAL | Teammate ranking by complementary skills and time zone, explained | Deterministic endpoint, explanation and ranking tests | PENDING |
| R-14 | OFFICIAL | At least 20 API tests incl race, run in GitHub Actions | Successful CI logs show >=20 actual API tests + race | PENDING |
| R-15 | OFFICIAL | Seed 10,000 participants and 2,000 teams | Repeatable seed script, counts verified, sensible state distribution | PENDING |
| R-16 | OFFICIAL | Board load test with 100 concurrent users and p95 < 200ms | k6/autocannon report with p95, error rate, duration, seed and environment | PENDING |
| R-17 | OFFICIAL | React UI for entire flow; phone and keyboard support | Mobile viewport and keyboard-only E2E run; relevant workflows completed | PENDING |
| R-18 | OFFICIAL | Deployed at an accessible live URL (free tier allowed) | External smoke test of app + API + database | PENDING |
| R-19 | OFFICIAL | Submit public GitHub repository | Submission link opens repository and README | PENDING |
| R-20 | OFFICIAL | Submit load-test report | Reproducible script + report linked in submission | PENDING |
| R-21 | OFFICIAL | Submit one-page design document | Data model, race prevention, trade-offs, one-more-week plan | PENDING |
| R-22 | OFFICIAL | Submit walkthrough video (up to 5 min) | Accessible video showing critical user flows and concurrency proof | PENDING |

## Official optional bonuses (not mandatory)
- B-01: Optimistic UI with rollback on conflict.
- B-02: Docker Compose one-command local setup.
- B-03: Tracing or metrics.
- B-04: Chaos test: kill server mid-join and show invariants intact.

## Organizer's stated evaluation order
1. Correctness under concurrency.
2. Design choices and ability to defend them.
3. Code quality, testing and UX.
**No numeric grading weights are published.** We will not invent them.

## Our design policies needing verification/documentation

| ID | DESIGN POLICY (not organizer requirement) | Reason / open question |
|---|---|---|
| D-01 | A team can be 'forming' while below configured minimum; readiness is distinct from creation | Reconcile min size with 1-person initial creation |
| D-02 | Pending join requests do not reserve seats | Stable capacity semantics |
| D-03 | Invite redemption joins directly if eligible; request flow requires leader acceptance | Implement both stated flows clearly |
| D-04 | Expiration checked by server/database time; client clocks non-authoritative | Avoid manipulation / clock skew |
| D-05 | Leadership successor must be an existing member; automatic deterministic transfer if no nomination | Avoid leaderless nonempty teams |
| D-06 | Soft-delete teams for audit integrity, while treating them as deleted in public APIs | Interpret 'deletes' with traceability; reassess if organizer requires hard deletion |
| D-07 | Idempotency keys scoped to caller + operation + request fingerprint; mismatched replay rejected | Avoid accidental reuse across operations |
| D-08 | Teammate suggestion scoring deterministic, based on missing team skills + timezone overlap | Transparent and verifiable; no LLM needed |
| D-09 | A board event signals invalidation; client refetches authoritative state | Tolerate missed/duplicated events |

## Mandatory edge-case acceptance scenarios
1. **Last-seat race:** 50 distinct accounts join one team with one vacancy; 1 succeeds, 49 reject, team not overfilled.
2. **Cross-team race:** same account joins two different teams simultaneously; at most one active membership.
3. **Join/request race:** accepting requests and redeeming invitations share one invariant-preserving mutation path.
4. **Duplicate team creation:** same request/key replays and creates exactly one team; different keys are separate authorized operations subject to per-hackathon membership rule.
5. **Leader leaves during accept:** outcome preserves a valid designated leader and capacity rules.
6. **Last-member departure:** team disappears from board, events and audit persist, no active memberships remain.
7. **Invite expiry and guessing:** valid/expired/revoked/invalid codes handled; abuse throttled.
8. **Error mid-transaction:** no partial membership, count, audit or outbox state.
9. **Realtime:** connected clients update, reconnect refetches canonical truth.
10. **Load:** seeded board under 100 concurrent virtual users reports p95 < 200 ms **in the actual declared test environment**.

## Submission artifacts and final gate
- [ ] Accessible GitHub repo with README, reproducible setup and meaningful Git history.
- [ ] Public live deployment and stable demo accounts/instructions (do not publish privileged credentials).
- [ ] Load-test script and measured report (environment, p95, errors, duration, dataset, repetitions).
- [ ] One-page technical design: schema, transaction semantics, lock order, compromises and extra-week plan.
- [ ] Walkthrough video <= 5 minutes.
- [ ] Submit all artifact links through Hack4Hack workspace by deadline.

## Known uncertainties, not claims
- Organizer does not specify precise team size values, invite delivery mechanism, auth provider, schema, API paths, suggestion formula or exact load-test duration.
- The company's usual stack is React/Express/MongoDB; alternatives are allowed if defended.
- Employment pay, contract/bond terms and offer are not specified by the technical assignment.
- The implementation must not claim performance, production readiness or test completeness before verification.

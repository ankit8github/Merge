# Final product audit and simplification — 2026-11-14

Baseline: clean `main`, HEAD `db17f3ef2c2934d2d4cc7db06499a291949a3d16`,
confirmed locally. Scope: audit the existing PS1 product, fix demonstrated UI
defects in bounded components, and validate offline. No architecture, API,
authentication, transaction, database, dependency or deployment change.

## Recommendation and scope of proof

**CONDITIONAL for owner review; deployment approval is withheld.** Offline checks
do not complete the profile PostgreSQL or full browser acceptance gates. The
existing 0006_profiles migration remains unapplied. No newly discovered P0 code
defect was established in this source/component audit. The known migration
prerequisite prevents treating profile/ranking as a complete live workflow.

Owner-supplied baseline: SSE PostgreSQL acceptance 4/4, lifecycle 10/10, backend
offline 1719 and frontend offline 394. These historical live results were not
rerun or extended. Existing source-bound receipts keep their original scope;
changed frontend bytes need fresh browser evidence. Nothing here certifies a
public URL, CI run, scale seed, benchmark, TLS, production roles or submission.

## Audit findings

P0 blocks a required journey or creates a security risk; P1 materially harms
correctness/usability; P2 is cosmetic or optional. Deferred items below are
deliberate limits, not verified defects silently marked fixed.

| ID | Priority | Proven finding / location | Resolution and evidence |
| --- | --- | --- | --- |
| G1 | P0 prerequisite | Profile/matching SQL needs unapplied 0006_profiles. | Known baseline release blocker, not corrected under the explicit no-database/no-migration instruction. Separate guarded profile acceptance required. |
| F1 | P1 | Every generic 409 became “That username is unavailable”, including profile CAS and ranking snapshot conflicts (`api.ts`). | Code-specific profile/ranking/username messages and a neutral unknown-conflict fallback. Four regression cases. |
| F2 | P1 | Exact server validation rejection disabled the entire profile until reload, which discards the draft (`Profile.tsx`). Browser Intl and server IANA support can differ. | Only exact 422/invalid_request permits correcting the retained draft at the same CAS version. Unknown failures/conflicts still require reload. Tests check no automatic retry, draft/version retention and reloaded version use. |
| F3 | P1 | Profile field errors were plain paragraphs, without alert semantics. | Keep associated descriptions and first-invalid-field focus; announce populated field errors. Component regression verifies alert/focus and no save. |
| F4 | P1 | Named inbox invitations still had UUID headings/action names; approval aria-labels spoke account UUIDs despite available applicant names. | Named team/applicant headings and accessible actions. Technical IDs remain in expandable reference details; old responses and uncertain-command recovery retain identifier fallbacks. Tests verify unchanged UUID command targets. |
| F5 | P1 | Cancel removed the focused membership button and left focus without a useful destination. Opening confirmation did not establish focus. | Opening focuses Cancel, avoiding accidental destructive activation. Cancel returns to its leave/remove trigger, with Manage membership as fallback. Both actions have component regressions. |
| F6 | P1 | An open removal confirmation survived a canonical change to another leader, despite removal controls disappearing. Server authorization still prevented an unauthorized mutation. | Hide and clear the unsubmitted removal confirmation on lost leadership. It cannot revive if leadership returns. Leave confirmations and command journals remain independent. Regression checks no mutation. |
| F7 | P2 | Successful redemption had both card-level and unconditional inbox-level success announcements. | Keep the summary only for successful commands absent from the current page. Present/absent-row tests verify one confirmation and preserve off-page feedback. |
| F8 | P2 | Footer called process liveness “healthy” and instructed participants to start the API. | State that the service responds, without claiming account/team access; give participant-facing failure/retry text. Existing network/HTTP/payload/JSON/timeout/retry tests retained. |
| D1 | P2 | Disabled creation form remains above each workspace view, even with known membership. | Deferred optional density reduction. It also hosts exact-command recovery and Start another team; no blanket removal or new navigation flow introduced. |
| D2 | P2 | UUID lookup/manual recipient fields are prominent and use technical vocabulary. | Retained functional fallbacks: no account search API exists, opt-in rankings intentionally exclude some recipients, and exact lookup crosses catalog pages. Collapsing these is optional polish. |
| D3 | P2 | Some roster pager/restart buttons use native styling; ranking reference time is raw ISO; brand “home” label targets the main-content anchor. | Deferred minor presentation/wording work. No dead link was found: both actual hrefs target the existing #main element. |
| D4 | P2 / verification | Real overflow, touch targets, focus announcements, contrast, zoom and keyboard traversal cannot be certified from jsdom/source. | Static review completed below. Full browser/mobile/assistive-technology checks remain pending; no browser/server was started. |

## Bounded implementation contracts

1. Feedback/profile (`api.ts`, `Profile.tsx`, new component tests): distinguish
   conflict causes and recover a draft only on a known pre-write validation
   rejection. Keep CAS, session ownership and unknown-delivery reload rules.
2. Invitations/approvals (`Invitations.tsx`, `Admission.tsx`, new tests): names
   identify people/teams; UUIDs still identify every command internally. Remove
   duplicate presentation without changing eligibility, pagination or recovery.
3. Lifecycle (`Lifecycle.tsx`, new tests): explicit confirmation and useful
   keyboard focus; current leadership controls unsubmitted removal drafts. Keep
   the original lifecycle journal, locks, retries and confirmed outcomes.
4. Service wording (`HealthStatus.tsx`, `App.test.tsx`): describe the existing
   liveness-only endpoint accurately and retain all failure/retry tests.

Dependencies are the existing React/API DTOs and native controls. No package,
migration, backend source, service guard or public contract was changed.

## Route, page and journey coverage

The client is one App with local discover/mine/invitations/detail views and public
navigation hints; there is no client URL router. This audit inspected the
entrypoint, App, all eleven components, all nine hooks, API transport/parsers,
styles, index metadata and existing journey tests. Production import traversal
from main.tsx reached all 24 production TS/TSX/CSS files; no unused production
module was established. No file or existing test was deleted.

| Journey / UI | Existing API surface reviewed | Offline coverage / remaining boundary |
| --- | --- | --- |
| Register, explicit login, session restore and sign out | POST /auth/register, /auth/login, /auth/logout; GET /auth/session | Journeys, API, profile field validation and backend auth tests; no automatic auth retry, cookie/CSRF generation fencing retained. Real HTTPS/cookie interaction pending. |
| Profile edit/opt-in and explained ranking | GET/POST /api/me/profile; GET /api/hackathons/{h}/teams/{t}/suggestions | ProfilesRanking, ProductAudit, BatchCompatibility and backend profiles/matching tests; SQL/CAS/eligibility needs separate PostgreSQL acceptance at 0006. |
| Hackathon discovery and exact lookup | GET /api/hackathons | HackathonLookup, DiscoveryNavigation and read API tests cover bounded pages, missing/neighbor lookup and stale replies; name search remains outside scope. |
| Team board, details and own membership | GET /api/hackathons/{h}/teams, /teams/{t}, /me/team | Journeys, CreateTeam, navigation/read tests; canonical null/errors distinct from membership. |
| Creation and one-team guard | POST /api/hackathons/{h}/teams | CreateTeam/API/backend tests preserve exact name/key under uncertainty, double-submit prevention and account isolation. |
| Request and leader approval/rejection | POST /api/hackathons/{h}/teams/{t}/join-requests; GET same and /mine; POST /{request}/decision | Admission/API/backend tests plus named-action regression; permission loss hides applicant data, pending requests reserve no seat. |
| Issue/receive/redeem invitations | POST /api/hackathons/{h}/teams/{t}/invitations and /{invitation}/redeem; GET /api/hackathons/{h}/invitations/mine | Invitations/API/backend tests plus named identity and duplicate-feedback regressions; expiry, account binding, original-key recovery and no seat reservation retained. |
| Member leave/removal, succession and last departure | POST /api/hackathons/{h}/teams/{t}/leave and /members/{user}/remove; GET /members | Lifecycle tests cover confirmation/Cancel, refreshed membership/deletion, recovery, later rejoin/new key and named removal. New tests cover keyboard focus and lost-leadership draft removal. Prior owner PostgreSQL 10/10 remains historical. |
| Committed workspace updates/reconnect | GET /api/hackathons/{h}/events | Realtime/BatchCompatibility and backend SSE tests cover canonical invalidation, drafts, expiry, stale callbacks and permission loss. No SSE service/protocol change. Prior owner PostgreSQL 4/4 is not real browser/proxy proof. |
| Account isolation, Back/Forward, remount and recovery | Same authenticated scoped reads; no new route | DiscoveryNavigation/Journeys and all journal suites cover scoped storage hints, session recheck, late replies and original-key recovery. Reload/crash still loses mutation journals. |
| Footer connection check | GET /health | App.test checks liveness wording, bounded timeout, sanitized failures and explicit retry. It is not readiness. |

All protected domain routes retain validated-session dependencies; writes retain
CSRF/current authorization and original services. No direct-join bypass was
added. No broken primary link or speculative user-directory endpoint was found.
Generated FastAPI documentation routes are not product navigation controls.

## Redundant elements and code removal decisions

- Removed the duplicate team-name paragraph when the invitation heading already
  names the team. IDs moved to secondary details rather than being discarded.
- Suppressed redundant inbox success when the same confirmed command has a card.
  Off-page success and all uncertain-command controls remain reachable.
- Cleared obsolete unsubmitted removal confirmation after permission loss and on
  collapsing Manage membership; confirmed/uncertain commands remain untouched.
- Replaced developer-facing liveness wording. Kept the bounded service check and
  existing timeout/retry tests, rather than introducing a new diagnostic feature.
- No deleted modules, hooks, guards, audit/outbox code or tests. Independent
  refresh controls serve different canonical reads; no blind deduplication.

## Static keyboard/responsive review

Reviewed explicit form labels, aria-invalid/describedby, role=status/alert,
native buttons/summary controls, skip link and #main focus target. Membership
Cancel/focus is now covered offline; existing detail/navigation heading focus
and first-invalid-field focus remain. Technical references use native details.
Names stay React text, not HTML. Session/account transitions still hide private
content and cancel/fence old responses.

CSS already stacks workspace/auth layouts at 700px, reduces the board to one
column at 1000px, wraps navigation/action rows and long headings/UUIDs, uses
minmax(0,1fr)/min-width:0 in key containers, and provides visible focus outlines
and reduced-motion rules. Standard .button controls have a 44px minimum height.
No CSS redesign was made. Browser checks at 320/375/768/1280px, 200% zoom,
long user/team names, all roster buttons, native details and keyboard/screen-reader
announcements are still required. Source rules do not prove rendered geometry.

## Actual commands and results

Windows PowerShell, existing Python 3.11.9, Node 22.15.0, npm 10.9.2; installed
dependencies reused. Commands ran locally without a network server/database.
The sandbox failed before process startup; explicit runtime review permitted
the same bounded offline work outside it. Git used command-scoped
`-c safe.directory=I:/Merge`, with no global configuration change.

| Working directory / exact command | Observed result |
| --- | --- |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1 src/ProductAudit.test.tsx` before production fixes | 10 failed, 1 passed, 9.35s, exit 1. Demonstrated original defects; username-conflict control passed. Initial file-write attempt used a duplicated frontend path, wrote nothing, then Vitest correctly reported no tests; corrected before this reproduction. |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1 src/ProductAudit.test.tsx src/ProfilesRanking.test.tsx src/BatchCompatibility.test.tsx src/Lifecycle.test.tsx src/Invitations.test.tsx src/Admission.test.tsx src/api.test.ts` | 189 passed / 7 files, 89.03s, exit 0. Checkpoint before the final added cases/service wording. |
| backend: `.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short` | 1719 passed, 32 deselected, 81.30s, exit 0. Existing Starlette/httpx deprecation warning; no dependency replacement. |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1` initial full run | 407 passed, 1 failed / 16 files, 146.31s, exit 1. Existing restored-inbox test checked an effect-owned fetch after only waiting for a static heading. |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1 src/DiscoveryNavigation.test.tsx src/ProductAudit.test.tsx src/App.test.tsx` diagnostic checkpoint | 56 passed, 1 failed, 22.90s, exit 1. New no-mutation assertion initially required method=GET even for the liveness fetch's implicit GET; corrected to allow omitted method. No production issue concealed. |
| frontend: `npm.cmd test -- --reporter=dot --maxWorkers=1` FINAL | 408 passed / 16 files, 122.18s, exit 0. Includes all fourteen new regressions and strengthened navigation coverage. |
| frontend: `npm.cmd run build` FINAL | TypeScript passed; Vite transformed 50 modules, built in 3.18s, exit 0. Earlier successful build: 2.96s. |
| root: `git -c safe.directory=I:/Merge diff --check` | Passed, exit 0; only LF-to-CRLF notices, no whitespace errors. Command-scoped safe.directory is needed because the fallback executor and repository have different Windows owners. |

The restored-inbox test now defers the response, waits for the actual GET,
asserts loading and absence of a fabricated empty state, resolves the canonical
response, checks the returned empty state and forbids mutations. No test was
deleted/skipped, no timeout was increased, and product guards were unchanged. Fourteen new cases
live in ProductAudit.test.tsx; the original six liveness tests are retained with
the new wording. No tests or historic evidence were deleted.

Static review already found all 24 production files reachable, zero targeted
secret-pattern hits in changed/new text, no backend or staged paths, and ignored
dist/node_modules/pytest-cache output. Targeted patterns cover private keys,
provider tokens and credential-bearing PostgreSQL URLs; this is not a claim of
comprehensive secret detection. Final inventory is ten modified files plus two
new files, matching the twelve paths below, with no staged/backend/dependency/
migration/evidence paths. No unexpected untracked deliverable was found.
An auxiliary diff check with core.autocrlf=false treated existing Windows CRLF
as trailing whitespace and showed README as a whole-file change. The repository's
normal line-ending configuration is retained; the final check uses ordinary Git
configuration. No global Git setting was changed.

## Complete task file inventory

Modified:

1. `frontend/src/api.ts` — conflict messages only; transport/DTOs unchanged.
2. `frontend/src/components/Profile.tsx` — exact validation recovery and alerts.
3. `frontend/src/components/Admission.tsx` — named accessible actions/reference IDs.
4. `frontend/src/components/Invitations.tsx` — named cards/actions, references and nonduplicated success.
5. `frontend/src/components/Lifecycle.tsx` — confirmation focus/current-leader draft handling.
6. `frontend/src/components/HealthStatus.tsx` — liveness-only participant wording.
7. `frontend/src/App.test.tsx` — preserve liveness failure/retry cases with accurate wording.
8. `frontend/src/DiscoveryNavigation.test.tsx` — strengthen canonical inbox synchronization.
9. `README.md` — link this review checkpoint.
10. `docs/PROGRESS.md` — append actual verified offline milestone only.

New:

11. `frontend/src/ProductAudit.test.tsx` — fourteen focused regressions.
12. `docs/PRODUCT_AUDIT.md` — audit, implementation/evidence/inventory and remaining gates.

No new dependencies, migrations or deleted files. Build output under frontend/dist
and test caches are ignored local artifacts. Old reports, receipts, manifests,
fixtures, migrations and backend sources were not edited by this task. No staging,
commit/push, deployment, fixture cleanup, database action, live API call or
browser/server startup occurred.

## Remaining owner verification and explanation

Before release: separately review/apply 0006 to an authorized exact-version target
and run profile PostgreSQL acceptance; use a fresh correctly scoped browser host
to validate every journey, mobile/keyboard behavior, cookies/HTTPS and SSE/proxy
transport. Do not reuse old browser manifests as authorization for these routes.
CI/race evidence, benchmark seed 10,000/2,000, 100 clients and measured p95, public
deployment, design/video/submission gates keep their separate review requirements.

Owner explanation: names are display data; UUIDs still choose the exact command.
A rejected profile validation happens before the write and can retain its draft.
A lost response cannot establish rollback, so reload/CAS or the existing
original-key command recovery is still required. Client leadership hides controls;
the backend remains responsible for authorization and race safety.

Exercise: in ProductAudit.test.tsx, change the named team's label and verify the
accessible invitation name changes while the submitted team/invitation UUIDs do
not. Then change the synthetic profile error from 422/invalid_request to an
unrecognized 422 and explain why editing must wait for canonical reload.

STOP for owner review. This checkpoint authorizes no live operation or commit.

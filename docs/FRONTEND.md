# Merge authentication, discovery, creation, admission and invitation UI

## M-014C - React invitation issuance, inbox and redemption

**M-014C-R1 repaired/offline verified, 2026-11-11:** the two final-review
old-hackathon issue/redeem 401 regressions pass unchanged. The same defect was
reproduced and repaired in creation, join-request and leader-decision mutations.
Full frontend: 261 passed; backend database-free: 1312 passed / 32 deselected;
typecheck/build passed. The earlier 242-pass result predates these schedules.
The R1 checkpoint created no commit. The subsequent final review reran all
checks and authorizes one local checkpoint; exact evidence is in PROGRESS.md.

Implemented for offline owner review, 2026-11-11, using the unchanged
[INVITATIONS.md](INVITATIONS.md) contract. No backend/schema/migration, dependency,
session model, persistent storage or browser-host permission change. M-014B is
committed as `2639c1fadffed6fb791496a023d63ddcdedff768`; 0005 is already applied.
Do not rerun migration or live tests. Earlier no-invitation-UI, 0004-current and
G1-open descriptions below retain their historical checkpoint scope. G1 remains
closed only within the audited owner-run local PostgreSQL acceptance scope.

### User workflow

The current leader of a selected canonical team gets **Invite a participant**.
The labelled recipient field accepts only an existing account UUID. There is no
username lookup/search endpoint or invented user list. A recipient can open the
selected hackathon's **Invitations** view and share their own session-derived
account UUID with the leader. This public identifier is not account authority.
Uppercase UUID input is canonicalized once before creating the command; surrounding
spaces and incomplete/username values are rejected with focused field feedback.
Issuance sends exactly `{recipient_id}` with current CSRF and a secure key.
Only a validated 201 acknowledges issuance; it never promises availability.
After confirmation, **Start another invitation** explicitly starts a distinct
command with a new key, including if the leader deliberately repeats a recipient.
Double submits cannot create concurrent duplicate commands.

The inbox reads only `/invitations/mine?limit=20&cursor=...` for the selected
hackathon, with Previous/Next and invalid-cursor restart. Every row must match the
current authenticated recipient before any row is rendered. Canonical status,
server availability, expiry and redeemed time come from the actual DTO. Dates are
displayed in the browser's local time; browser time never authorizes redemption.
The DTO has team UUID, not team name: each card labels the UUID and **View invited
team** opens the existing canonical public detail endpoint. No names or live data
are fabricated, and no unbounded background team lookup is introduced.

**Redeem invitation** sends exactly `{}` with that recipient's current session
CSRF and a separate secure key per invitation command. New redemption waits for
canonical My Team = null and a pending/available grant. These presentation checks
grant no authority; the backend rechecks recipient, current issuer, expiry,
membership and capacity. Availability reserves no seat. Already-redeemed or
unavailable rows stay visible without offering a new command. Expired/stale/full/
assigned/used/missing/denied/rate-limited errors give fixed actionable feedback;
unsuccessful commands never optimistically consume grants or add memberships.

Confirmed issue/redemption invalidates scoped canonical reads: active detail or
inbox and My Team refetch; discovery and inactive views fetch fresh on their next
activation. The inbox/roster comes only from GETs, never a mutation DTO. A failed
refresh cannot erase a confirmed command or cause another POST. A stored redeemed
reply is a historical acknowledgement, not proof of current membership.

### Recovery, security and response isolation

`useInvitations` lives in App above the session-keyed workspace, parallel to the
existing creation/admission journals. Records contain account/hackathon/team/
operation/recipient-or-invitation IDs, exact key, status and sanitized error
metadata, not session/CSRF/bearer or inbox DTOs. Native crypto.getRandomValues
generates 32 bytes as 64 hex characters, with no weak fallback. Keys and commands
are memory-only. Current transports use the latest valid session CSRF; no actor
field, cookie override, persistent key storage, automatic mutation retry or secret
logging is added.

Network/timeout/abort/malformed/unknown responses and outcome_uncertain freeze the
original command. Uncertainty stays sticky through later 401/403/409/422 replies;
only a matching validated success resolves it. Issuance cannot change recipient
while pending/unresolved. Redemption recovery uses the original hackathon/team/
invitation/key, even if a refresh removes the row, changes availability or finds
membership. Recovery cards contain command IDs only and belong to this account;
they are independent of inbox pagination and read failures. A new same-key call
after expiry may be denied while an earlier redemption remains committed; check
canonical membership and retain the original command for owner recovery rather
than silently replacing its key. A changed recipient after a definite issuance
rejection is a distinct command/new key; unchanged explicit retries reuse the key.

Session logout/restore/expiry synchronously aborts transports and marks in-flight
commands unresolved. Late successes and 401s from an older account/session cannot
update or end a newer workspace. Same-account sign-in restores original retries
with the new CSRF; other accounts cannot see/use that journal. Hackathon/team
navigation keeps each mutation in its original scope; completion never selects
another team or puts its success in another scope. Reads abort/ignore delayed
responses on navigation and pagination. Backend authorization remains authoritative.
If a leader loses authority, issuance controls hide until canonical leadership
permits them again; unresolved issuance is retained in memory, not bypassed.

R1 separates session ownership from display ownership. `useWorkspaceSignal`
creates a token in a layout effect after navigation commits; cleanup invalidates
it. Creation owns the selected hackathon lifetime because its form remains
visible across inner views. Admission and invitations own the selected view/team
lifetime. Tokens live above revision-keyed read children: canonical refresh and
inbox pagination do not revoke an otherwise current command. There is no new
render-time ref assignment for workspace ownership or change to session transport.

A response may settle its original account/scoped journal after navigation,
but only its still-current display token can expire the session or automatically
refresh canonical reads. Old successes/conflicts cannot remount another team's
draft. Current-workspace 401s still invoke the existing authentication failure
handling. Navigation does not erase or cancel the original command; returning
permits exact-command retry with a fresh display token and current-session CSRF.
Leaving and returning never revives an old token. Session changes retain their
existing transport-abort, unresolved-command and old-result isolation rules.

Pending/uncertain work installs a best-effort beforeunload warning. Keep the tab
open: reload, crash or closure loses keys and exact recovery commands. Canonical
membership/inbox reads cannot reconstruct an exact lost idempotent result. No
durable recovery or automatic new-key fallback is claimed; unresolved work after
that loss needs separately approved owner recovery. Session tokens and CSRF are
never persisted.

### Component map and offline limits

```text
App: useSession + useTeamCreation + useAdmission + useInvitations
  Discovery / SelectedWorkspace: account/session/hackathon-scoped invalidation
    TeamDetail: canonical team + existing TeamAdmission + InvitationIssuer
    InvitationInbox: bounded private pages + own account UUID + recovery commands
      RedemptionCard / CommandFeedback: exact retries and fixed status/errors
api.ts: exact three invitation endpoints, DTO/scope/state/time/reply validation
```

Timestamp validation preserves PostgreSQL/Python microseconds, so a valid
redemption immediately before expiry is not rejected by millisecond rounding.
The client validates recipient/issuer associations, schema/status, UUIDs, finite
ordered lifetime/consumption times, duplicate rows and next-cursor shape. Unknown
response fields are dropped. Tests use synthetic HTTP fixtures only, separate
from production views; exact evidence and file inventory are in PROGRESS.md.

Native forms/buttons, linked labels/help/errors, focused validation, status/alert
regions, wrapping navigation/actions and UUID overflow rules support keyboard and
responsive layouts. Initial team-detail heading focus now runs before paint, so
a deferred loading effect cannot steal focus after UUID validation. jsdom verifies
DOM focus and form submission, not browser
keyboard activation, screen-reader output, pixels, touch, viewport or zoom.
Real 320px/375px/desktop, keyboard/mobile/assistive-technology and HTTPS/cookie/
Origin acceptance remain unverified. No browser/server was launched. The existing
guarded browser host is still 0003-only, excludes invitation/admission/create
mutations and cannot target existing 0005. A separately reviewed exact-0005 host
and write scope is needed before live UI acceptance. No deployment, remote or
push; the prior intermittent frontend fetch-count concern remains documented.
Final review offline evidence: 261 frontend tests passed, typecheck/build passed,
backend database-free 1312 passed / 32 deselected. The initial concurrent review
run had three initial-loading timeouts (258 passed); the unchanged standalone
run passed all 261. Resource contention is a plausible explanation, not proven.
No assertion or timeout was changed; this does not resolve the earlier fetch-count
concern. The original M-014C 242-pass result predates the R1 cases. Exact commands,
failures, final review and 20-path inventory: PROGRESS.md.

## M-013B - React join requests and leader decisions

Implemented for offline owner review, 2026-11-11. Uses the existing M-013A
[ADMISSION.md](ADMISSION.md) contract and unchanged session/read/create workflows.
No backend, migration, privilege, dependency, persistent storage or browser-host
scope change. The M-012B/M-011A descriptions below retain their checkpoint scope;
their disabled-join/no-request UI statements are superseded by this section.

### Member and leader journeys

Open a team from discovery to see its canonical public detail. Nonleaders get
their own scoped /join-requests/mine read. Request membership is enabled only
after My Team is successfully null and their own request is successfully null.
Present/unknown membership or an existing pending/approved/rejected request blocks
a new command. Pending requests reserve no seats; capacity is not treated as a
client admission rule. POST {} uses a secure key and current-session CSRF. A
successful acknowledgement triggers fresh reads; only the canonical mine endpoint
supplies the displayed request status. An approved request says check My Team;
it does not synthesize membership. Terminal rejection has no re-request button.

The canonical team leader gets Pending join requests instead. Other users never
fetch this list. The server still authorizes every list/decision, and 403/404
responses hide applicants and offer a fresh team/permission check. The exact
bounded list requests limit=20, opaque UUID cursors, Previous/Next requests and
an explicit restart after a rejected cursor. Applicant UUIDs are displayed because
the documented DTO supplies no applicant names/profiles; none are fabricated.
Approve/Reject are labelled native buttons with per-request in-flight guards.
My Team links to the same team detail and guarded request controls.

Only {decision:"approve"|"reject"} is sent for decisions. A confirmed stored 200
acknowledges that command, then refetches the pending page, detail and My Team.
The discovery list is invalidated/remounted at page one on its next activation.
Read-refresh failure cannot erase a confirmed mutation and never automatically
POSTs again. Manual Refresh request and membership / Refresh requests and team
refetch canonical data; counts/status/leadership never come from optimistic rows.
No live event subscription or automatic polling is claimed in this milestone.

Full team, already-assigned, resolved-request, changed-leader, missing-resource,
validation, rate-limit and unknown-outcome errors have fixed actionable text.
Definite team-full rejection can be retried or changed to reject with a new key;
idempotency mismatch/unknown/malformed responses keep the original command
unresolved. Current leader/request authorization is always enforced by the backend.
Presentation gating cannot grant rights, and no unrestricted join is exposed.

### Journal, isolation and recovery

useAdmission lives in App above the session-generation workspace. Its journal
keys include validated account, hackathon, team and either mine or request UUID.
Records contain command key/decision/request UUID, status, uncertainty and fixed
error metadata, never Session/CSRF/bearer or cached applicant DTOs. Native
crypto.getRandomValues supplies 32 bytes encoded as 64 hex characters, with no
weak fallback. Exact same-command retries reuse the key; a changed decision gets
a new key only after a definite rejected attempt. Synchronous ref guards prevent
duplicate and opposite decisions before React rerenders.

Network/timeout/malformed/unknown responses, outcome_uncertain and session abort
retain the original command. Uncertainty is sticky across later 401/403/409/422
responses; only a validated matching stored success resolves it. Buttons offer
only the original approval/rejection while uncertain. If its request disappears
from a pending page, an original-command recovery row remains reachable after a
successful authorized pending-list read. It contains the request UUID/decision,
not cached applicant data. If leadership is lost, restore current permission
before recovery; never display an old applicant list to work around a denial.

Logout/restore/expiry synchronously abort transports, mark pending commands
unresolved and ignore late success/401 callbacks using the existing signal,
account and generation. Same-account sign-in can retry the original command with
the newly restored CSRF. Other accounts cannot read/use its journal. Navigation
allows the original operation to finish under its original scope; it never changes
selection or populates another team's status. A confirmed result invalidates
canonical reads only for that account/hackathon. View-owned reads still abort and
ignore stale results on team/page/account changes. App also guards read-driven
session expiry against an already-aborted authenticated generation.

Commands survive only this App instance. A best-effort beforeunload warning and
visible keep-this-tab-open instructions cover pending/unresolved work. Reload,
crash or tab closure loses keys; canonical status alone cannot prove an exact
ambiguous decision's stored reply. Do not infer rollback or silently issue a new
key if the journal is lost; obtain separately approved owner recovery. Browser
storage, raw cookie/Authorization headers and credential logging are not used.

### Components and acceptance limits

```text
App: useSession + existing useTeamCreation + new useAdmission journal
  Discovery / SelectedWorkspace: scoped canonical invalidation and navigation
    TeamDetail: canonical team + TeamAdmission, focus after detail load
      MemberRequest: canonical own status, membership eligibility, original retry
      LeaderRequests: authorized bounded pending pages + recovery commands
        DecisionActions / CommandFeedback: native labelled actions and fixed text
    MyTeam: canonical membership and Open team and requests
api.ts: validated request DTOs, exact four admission endpoints and stored replies
```

Scoped paths, UUIDs, statuses, finite ordered timestamps, exact decision response
ID/status and schema version are checked. Pending pages reject terminal/duplicate
rows and invalid next cursors. Unknown response fields are dropped. Own response
requester must match the authenticated account before display. Mutations use
same-origin cookies, no-store, strict JSON, current CSRF and one printable key;
the browser supplies Origin. No client actor identity is submitted.

Existing responsive/focus/reduced-motion CSS is retained; admission actions wrap,
applicant UUIDs break within cards, controls have native keyboard semantics,
request sections/list items have accessible names and progress/errors use live
status/alert regions. No CSS-hidden privileged content or fake live fallback.
jsdom tests cover native focus, DOM access, errors and response isolation, not
real-browser keyboard activation, pixel layouts or screen-reader announcements.
Manual 320px/375px/desktop/zoom/focus/screen-reader/HTTPS validation remains pending.

The browser host still excludes creation/admission routes, grants no team/request
writes, and requires 0003_auth; it refuses the already-upgraded 0004 merge_test.
No ordinary app.serve, PostgreSQL access, migration, credential prompt or browser
startup was performed. A separately reviewed guarded 0004 host/write scope is
required before live UI acceptance. Existing backend 105 admission executions
remain owner backend evidence, not frontend browser evidence. G1 stays open.
Actual offline checks and exact inventory are in PROGRESS.md.

M-012B adds the selected-hackathon Create Team form using the committed M-012A
contract in [TEAM_API.md](TEAM_API.md). **Offline verified only; real-browser
acceptance remains pending.** No backend, schema, dependency or browser-host
permission changes. Joining and other lifecycle actions remain unavailable.
M-011A sections below retain their earlier checkpoint scope; current behavior and
exceptions to discarded view state are recorded in this M-012B section.

## M-012B - authenticated team creation

The selected hackathon has a labelled, keyboard-submittable Create Team form with
field help, focused validation errors, live progress/error/success messages and
the existing responsive CSS/focus/reduced-motion policy. It waits for canonical
My Team to return null before enabling new creation; present/unknown membership
blocks new commands. Client rules match 1-120 Unicode code points, rejection of
ASCII-space-only names, NUL and unpaired surrogates, without trimming or Unicode
normalization. UTF-16 maxLength does not reject valid 120-emoji names.

api.createTeam sends exactly `{name}` to the fixed relative scoped /teams POST,
with same-origin cookies, no-store, application/json, current in-memory CSRF and
one Idempotency-Key. No actor, identity, size or generated team UUID is submitted.
The browser supplies Origin; cookie/auth/Origin/CSRF rules remain server authority.
Accept exactly 201 and the V1 stored envelope, literal founder count/version 1,
valid UUIDs and matching hackathon; also check the returned user UUID against the
current session. Extra response fields are dropped. This is an acknowledgement,
never a TeamView or synthetic live roster. Confirmed 201 (including replay)
refreshes My Team; the visible list resets to page one/refetches, while an inactive
list is invalidated and fetched fresh on its next activation. Details preserve
scoped GETs. A failed canonical refresh does not erase creation success; retry
reads without POST. Already-assigned 409 refreshes without claiming creation.

### Command lifetime and recovery

useTeamCreation lives in App above the workspace keyed by session generation.
Its in-memory journal is scoped to validated account/hackathon UUIDs. Commands
store exact name, random key, status, uncertainty and sanitized error metadata;
no bearer, CSRF, Session or canonical Team is stored in commands. Active requests
use the current session scope. Operation records (including settled records)
remain until this App instance is destroyed. Other accounts cannot see/use them.
No local/session storage, credential persistence, console logging or new library.

Generate 32 bytes through native crypto.getRandomValues, encoded as 64 lowercase
hex characters within the existing key contract. No time/Math.random fallback.
An edited meaningful name after definite rejection gets a new key; explicit retry
of an unchanged command reuses its key. Synchronous ref guards prevent duplicate
POSTs before React renders. No mutation automatically retries.

| Result | UI behavior |
| --- | --- |
| 201 initial/replay | Confirm success, disable more creation, refresh canonical reads |
| First 400/422 invalid_request | Fixed validation message; permit correction/new command |
| 401 | End the current workspace through useSession; no automatic retry |
| 403 | Fixed denied message and explicit Restore session action |
| 409 already_assigned | Block new creation, refresh My Team/list; no success claim |
| 409 idempotency_mismatch | Keep original command locked/unconfirmed; check membership/contact owner |
| 429 | Bounded Retry-After cooldown survives navigation; explicit retry only |
| outcome_uncertain, any 503, network/timeout/abort, malformed/wrong-principal/unknown response | Unresolved; retain exact name/key and offer original-command retry only |

Only documented pre-mutation status/code pairs establish a definite rejection:
400/422 invalid_request, 401 invalid_session, 403 invalid_csrf/origin_rejected/
client_identity_rejected/https_required, or 429 rate_limited. A status alone,
HTML/malformed error or unrecognized code cannot unlock the name; even an
outcome_uncertain body with an unexpected 400 stays unresolved.
Uncertainty is sticky across later pre-mutation errors (including 401/403/422):
such a response cannot prove the earlier outcome. The name is read-only until
the original operation is resolved. Only an authoritative 201 replay or
already_assigned resolves it. Membership becoming present alone cannot substitute
for the stored reply: new creation stays blocked, but only frozen original-key
replay remains available. No silent discard/new-key escape.

useSession exposes the existing generation's AbortSignal. start() invalidates it
synchronously on logout, expiry, restore or replacement. Creation callbacks check
signal/epoch/account before affecting a workspace or expiring a session. Abort
latches the old command unresolved because browser cancellation does not prove
PostgreSQL work stopped. Logging back into the same account can retry the same
command/key with newly restored CSRF; another account gets its own journal scope.
Hackathon navigation lets a request finish only under its original hackathon,
without changing selection or refreshing another scope. Existing read active
flags, aborts, absolute session expiry and cursor/detail navigation are retained.
No join/invite/request/leave/leadership/delete action is implemented.

### Persistence and acceptance limits

The journal survives in-app navigation, foreground checks and logout/login only
while this App instance lives. beforeunload warns for pending/unresolved commands,
but browsers may suppress it and crashes cannot run it. **Reload, tab closure or
crash loses the journal/key.** The UI says keep this tab open until resolved.
If the record is lost, do not infer rollback or submit a fresh key based on an
ambiguous outcome; use separately approved authoritative inspection/owner review.
Durable recovery across reloads is not claimed. Same-origin XSS remains outside
this client boundary, as with the existing CSRF.

Mocked HTTP/jsdom checks are not real cookie, browser layout/keyboard/screen-reader,
production HTTPS or PostgreSQL UI acceptance. Manual 320px/375px/desktop/zoom/focus
and approved delayed-response browser exercises remain pending. The existing
guarded browser host excludes creation; its auth-only manifest grants no team
writes. New live creation acceptance requires a separately reviewed host/write
scope and retained fixtures/invariant checks. Never switch to ordinary app.serve
to bypass it (ordinary Settings still target merge_dev). No live startup/credential
prompt, browser execution or PostgreSQL access occurred here. M-012A's 105 owner-
run backend passes remain separate evidence. G1 stays open.

Final M-012B commands/results and exact inventory are in PROGRESS.md. The sections
below describe earlier M-011A behavior/counts, not new M-012B live evidence.

**M-011A-R4: shutdown defect corrected offline; stop for owner review.** The R3
regression now passes. Timeout/incomplete drains remain unsuccessful independently
of later snapshots; final success is printed only after Engine/listener cleanup.
[BROWSER_HOST_AUDIT.md](BROWSER_HOST_AUDIT.md) records the minimal source diff and
R3/R4 evidence. Live reads, scoped auth writes and all account/fixture prerequisites
still require separate owner approval; no live startup is authorized by this fix.

M-011A-R2 implements a separate retained-account-only test browser launcher in
`backend/test_support/browser.py`. Exact guarded inspect/serve/verify commands,
manifest budgets, per-connection/dependency checks and shutdown procedure are in
[BROWSER_ACCEPTANCE.md](BROWSER_ACCEPTANCE.md). Registration remains blocked;
ordinary app.serve is not safe for merge_test browser acceptance. Implementation
is offline verified only; live reads and scoped session/throttle writes require
separate owner approval. No browser, database access or G1 closure is claimed.

Initially implemented against `cc67e18ffd6a6845642170fa358ecc48d2fef38b`.
No new dependency, migration or production backend runtime change. G1 remains open.
This is the existing React 19 / TypeScript / Vite app with plain CSS; Tailwind,
a router, UI kit and query/cache library are not installed or added.

## Component map

```text
App
  useSession: bootstrap / authenticated / guest / error / signing out
  AuthForm: explicit registration and login
  Discovery
    Hackathons: independent bounded catalog pages and selection
    TeamList: scoped cursor pages and refresh
    TeamDetail: canonical summary, disabled future join action
    MyTeam: canonical membership or explicit null empty state
  HealthStatus: preserved liveness check / timeout / retry

api.ts: typed DTOs, runtime validation, fixed relative endpoint functions
useRead: cancellable view-owned reads, sanitized errors, active-session expiry
Feedback: loading, error, manual retry and bounded 429 cooldown
```

The responsive shell uses system fonts, a restrained green/cream palette and
CSS-only decorative geometry. Labels, field hints, skip link, landmarks, live
status/error regions, native buttons, navigation focus and reduced-motion support
are included. No external fonts/images, tracking or fabricated live statistics.
Names are escaped React text. Test accounts/teams exist only in test modules;
production imports none of them. There is no offline/sample-data fallback.

## Journeys and transport

- Initial mount calls GET `/auth/session`. A 401 shows sign-in; other errors keep
  the workspace hidden and offer an explicit session retry. Refresh reconstructs
  identity and CSRF from the server, never browser storage.
- Register POSTs `{username,password,display_name?}` to `/auth/register`.
  A 201 shows confirmation and the sign-in form; it never invents a session or
  automatically logs in. Login POSTs `{username,password}` to `/auth/login` and
  accepts the documented 200 session response. Passwords are uncontrolled form
  fields and are cleared after requests. Client hints follow the existing
  lowercase username and 15–128 Unicode-code-point password policy; server
  validation remains authoritative. Values are not trimmed or normalized.
- Both POSTs use application/json and `X-Merge-Request: 1`. The browser supplies
  Origin automatically. Logout POSTs `{}` with `X-CSRF-Token` from the current
  session and accepts exactly 204. No CSRF header is sent to reads/register/login.
- Cookie ownership is entirely the browser's. Every authenticated request uses
  `credentials: same-origin`, `cache: no-store` and fixed relative URLs. There is
  no Cookie/Authorization/identity header, raw bearer, document.cookie access,
  local/session storage, credential logging or arbitrary HTML rendering.
- Pick a hackathon, explore teams, open details or switch to My Team. All four
  M-010A GET contracts are used without changes. Exact DTO fields/errors are in
  READ_API.md. HTTP 200 `{"team":null}` means no membership, not a missing resource.
  Actual returned counts, size bounds, readiness and public leader are displayed.
- Catalog and team pages always request limit=20. Next uses the returned UUID
  cursor; Previous re-fetches its preceding cursor. Response order is preserved.
  Refresh, hackathon changes and returning from details restart the team list.
  There is no fabricated total count or client-side admission decision.
- Join is clearly disabled with an explanation. No create/join/leave/invite/
  request/approval endpoint is called and no mutation is simulated.

DTO parsing selects documented fields, validates IDs/scope, bounded pages,
count/size/readiness and timestamps. Unknown fields are not retained/rendered.
An absent `team` field is rejected rather than treated as null membership.
Responses with the wrong successful status are rejected. Raw server messages,
HTML and transport exceptions are not shown or logged. Error display uses fixed
client text for 401/403/404/409/422/429/503/network/unexpected responses.

## Session lifetime and failures

Successful login creates a new workspace generation. Logout immediately unmounts
and discards authenticated views before its request completes; only a 204 or 401
confirms the session is gone. Failed/lost logout acknowledgement leaves a private
recovery screen that explicitly says the server session may remain active. Retry
sign-out or check session manually. It never reports false logout success.

Each read owns an AbortController and an active flag. Navigation, refresh,
session checks and logout abort and ignore stale responses, including late 401s
from a previous login. GET 401 unmounts the workspace and requests sign-in. The
advertised absolute expiry clears the in-memory session; the server is still the
authority. Window focus/pageshow while authenticated revalidate the cookie and
discard old workspace state, covering session replacement/revocation in other
tabs when foregrounded. This is not immediate cross-tab revocation notification.

Requests have a 20-second cancellation timer; no operation is automatically
resubmitted, including when retryable=true. A transport failure may have followed
a successful register/login/logout, so the UI provides session recovery rather
than assuming rollback. Error metadata is retained only as status/fixed code/
retryability/cooldown. Integer Retry-After seconds are bounded to 1–3600; absent
or malformed 429 headers use a 30-second UI cooldown. Timers stop at expiry and
form switching does not bypass the cooldown. The server throttle remains authority.

## Proxy and safe local checks

Vite now proxies `/api` alongside existing `/auth` and `/health` to
`http://127.0.0.1:8000`. It keeps the established proxy convention, without URL
rewrites, Origin rewriting, CORS or public backend configuration. Frontend calls
must stay relative. Production hosting must route these same paths under the
configured trusted HTTPS origin; Vite's dev proxy is not production hosting.

Historical initial M-011A evidence on Windows, Node 22.15.0/npm 10.9.2, existing
dependencies (the final checkpoint reruns are recorded in PROGRESS.md):

```powershell
Set-Location I:\Merge\frontend
npm run typecheck
npm test
npm run build
npm ls --depth=0
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m pytest -q -m 'not database' --tb=short
.\.venv\Scripts\python.exe -m pip check
Set-Location I:\Merge
.\backend\.venv\Scripts\python.exe scripts/check_local_http.py
```

- Typecheck and production build passed. Final build transformed 36 modules;
  production JS 210.43 kB (65.98 kB gzip), CSS 9.94 kB (3.02 kB gzip). Bundle size
  is not a performance/load result.
- Vitest: **52 passed across three files in 11.83s**, jsdom/component/transport
  tests. Six original health tests remain, now targeting the extracted component.
  New tests exercise registration/login/logout, bootstrap/refresh/expiry,
  unauthorized/denied/rate-limited/unavailable/network states, pagination,
  detail, null/present membership, cancellation, session generations,
  foreground revalidation, labels/focus/text escaping and request contracts.
  Mocked HTTP test fixtures do not prove real PostgreSQL or browser behavior.
- Backend offline: **806 passed, 32 deselected in 20.51s**, one existing
  Starlette/HTTPX warning; pip check: no broken requirements.
- The controlled launcher smoke check passed health, frontend HTML, auth and all
  four read missing-session proxy 401s, followed by upstream outage and recovery.
  Its final run additionally checks preserved allowed/rejected Origin headers.
  Missing-cookie/browser-policy rejection occurs before database dependencies;
  no database or credentials were accessed. It starts/stops only its own children.
- Final static/scope review passed: 22 reviewed files, ten-file production import
  graph excluding tests, no test fixtures in built assets, smoke-script Python
  AST/compile, secret/artifact patterns and `git diff --check`. Entire backend,
  migrations/schema, permission/provisioning scripts, package manifests and
  lockfile remain unchanged. These pattern checks supplement manual review.

Initial TypeScript runs exposed response-narrowing and test-query typing errors;
both were corrected, with no weakened assertions. Review also aligned Unicode
string bounds with the server's code-point policy and added a regression test.
Passing commands above
supersede those intermediate failures. No browser screenshots, Playwright,
real-cookie E2E, load/CI or production HTTPS verification was performed.

## Browser verification still pending

M-011A-R2 implements the retained-account-only guarded test launcher described in
[BROWSER_ACCEPTANCE.md](BROWSER_ACCEPTANCE.md). It includes offline fail-closed
tests and conditional owner startup/shutdown commands. Live reads and scoped
session/throttle writes still require separate owner approval. Registration
acceptance and the deterministic late-response instrument remain pending.

Do not submit these forms to the ordinary development backend in this task.
Its unchanged Settings guard permits only merge_dev; overriding a database name
does not safely retarget it to merge_test. The test host injects both real service
dependencies on one per-connection-guarded Engine at exact revision 0003_auth.
No live startup, credential prompt or PostgreSQL/browser result is claimed.
The existing guarded owner API commands in READ_API.md remain valid backend
evidence, not M-011A browser evidence. No PostgreSQL run was performed by Codex.

Once that safe environment is provided, use its exact configured origin, proxy
and browser-managed cookies, then verify manually without recording credentials:

1. At desktop 1440px and phone 375px/320px widths, check wrapping, scrolling,
   contrast, 200% zoom and loading/empty/error layouts. Tab from the skip link
   through labels, forms, event selection, pages and details. Use Enter/Space;
   confirm visible focus, navigation heading focus and screen-reader feedback.
2. Register a private test account, confirm explicit sign-in, reload to restore
   it, then sign out. Inspect cookie attributes privately; never copy cookie,
   password or CSRF values into reports/screenshots. Verify no credentials/tokens
   in storage, URLs, console, DOM text or logs.
3. Use existing retained authorized fixtures to verify list pages/ties, details,
   membership and `{"team":null}`. No browser mutation is available to create a
   membership. Switch hackathons while throttling the network; stale responses
   must not overwrite the selection.
4. Expire/revoke a test session through the approved harness, then foreground/
   refetch; verify sign-in replaces private views. Drop a response during logout:
   the UI must show uncertainty and session recovery, not confirmed success.
5. Check 403/429 (including cooldown), 503, offline recovery, and backend health
   outage/restart. Disabled join must issue no request. Verify production
   HTTPS/proxy/Origin behavior separately in the approved deployment.

No realtime, roster, team mutation, deep-link routing, invitation/request UI,
matching, new visibility model, authenticated 50-way HTTP acceptance or G1
closure is claimed. XSS in trusted same-origin JavaScript would compromise CSRF
and displayed data; deployment CSP/telemetry/cookie enforcement need real browser
review. Browsers/extensions/password managers may retain form data independently
of application state. Frontend abort does not prove server rollback.

Owner exercise: delay a team response, sign out and sign in again, then release
the old response; explain why its data and 401 cannot change the new workspace.
Change the empty-membership copy without changing its exact null parser.

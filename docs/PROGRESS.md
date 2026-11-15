# Current verified status

## Routine session checks preserve UI - 16 November 2026

Started clean at `1416c72434d5323ac5c80fb5f5854d53cda7f2c7`. A pre-fix regression
proved focus immediately unmounted the authenticated workspace before a session
reply. The old restore/checking/epoch path explains a reset without requiring a
document reload; actual owner browser navigation/HMR attribution remains unknown.

Routine focus, visible visibilitychange, pageshow and popstate now validate in
the background. Matching user/CSRF/absolute expiry preserves epoch/signal and
mounted views, pagination and drafts. Events coalesce to one active GET and one
latest trailing observation. Superseded replies cannot replace identity; logout,
expiry, denials and replacement credentials/account still invalidate the scope.
Blocking bootstrap/explicit recovery, server authorization, SSE reconnect/refetch,
public-only navigation persistence and memory-only/no-auto-replay journals remain.
An expired suspended tab is cleared on return even before its timer is serviced.
Decision and scope: [DECISIONS.md](DECISIONS.md), [FRONTEND.md](FRONTEND.md).

Offline evidence: **111 focused tests passed**, 33.10 s; **464 full frontend tests
passed**, 19 files with one worker, 188.13 s; **38 unchanged admission tests passed**,
30.16 s. An earlier full run had one catalog-wait timeout (463 passed); direct
admission and complete confirmation passed without changing assertions/timeouts.
This intermittent timing observation remains documented. TypeScript/Vite build passed, 50
modules, 2.77 s. Includes **30 new regressions** and retained genuine-reload/race
checks; current-scope 401/403 denials cannot be masked by queued lifecycle events.
Commands/coverage/limits: [TESTING.md](TESTING.md). Diff/secret/source/link
checks passed and all **1169** baseline evidence hashes are preserved. Favicon
PNG/index.html remain byte-identical. No backend, policy, dependency, migration,
business-rule or deployment change; no fixture/DB/live/cloud operation.

Uncommitted owner-review patch. **CONDITIONAL for release** pending separately
approved deployment/public-browser acceptance. No commit, push or deployment.
Browser discard/crash/manual reload still loses memory-only drafts/journals;
network/service and 403 failures still hide private content for explicit recovery.
The owner reports the application deployed; this investigation did not verify a
public URL, deployed source SHA or live fix. Earlier release records retain scope.

## Header favicon polish - 15 November 2026

Added [frontend/public/favicon.png](../frontend/public/favicon.png), a 64x64 RGBA
capture of the existing App.tsx header mark and unmodified CSS: lowercase m,
green #315c48, yellow #f2f6b5 and the original rounded tile. No redesign or font
dependency added. index.html references the PNG; source and production title
remain `Merge — Find your people`. No default Vite favicon reference exists.

Offline Chromium inspection at 16/24/32 pixels on light/dark backgrounds passed.
On Windows, Node 22.15.0/npm 10.9.2: `npm.cmd test -- --reporter=dot --maxWorkers=1`
passed **434 tests in 18 files**, 111.75 s; `npm.cmd run build` passed TypeScript
and Vite (50 modules, 2.83 s). Production favicon bytes match the source asset.
`git diff --check` passed; all **1161** pre-review evidence hashes are preserved.
Only the asset, HTML favicon link and this note changed. No backend, application
behavior, authentication, deployment or dependency changes; no server/cloud/push
operation or commit. Isolated asset rendering does not certify a live deployment.
Proposed local commit: `chore(frontend): use Merge header logo as favicon`.

## Render setup input rejection diagnostics - 15 November 2026

Started clean at published `96e32e154df38c8447b6a4dd85c6029dbb331d52`.
The owner reports a Render setup process exiting at input validation, before
DNS/SQL/initialization/listener construction in that invocation. The existing
message cannot identify its exact failed condition. Owner confirms no throttle
key during setup, the complete setup SHA, explicit PORT 10000 and setup owner
merge_prod_user. Render's documented Docker platform defaults match the existing
checks. Remaining field presence/format and deployed SHA equality are unverified;
no secret or dashboard environment was read and no root cause is fabricated.

Implemented fixed allowlisted input categories with a generic unexpected fallback;
no values, raw exceptions, credentials or URLs are logged. Preserved every input,
owner/runtime, DB identity/private-host/TLS/privilege, create-once and revision guard.
No dependencies, migrations or application feature changes. Canonical trace and
private dashboard review checklist: [RENDER.md](RENDER.md#setup-input-rejection-offline-diagnosis).

Actual focused regressions: **467 passed**, 10.49 s, one existing Starlette/httpx
deprecation warning; includes 70 new diagnostic cases. Render/Railway/VPS offline
contracts passed. A synthetic comparison of published versus pending setup/runtime
validation found **zero acceptance changes across 758 cases**. Static source,
imports, documentation and secret/artifact review passed; all **1149** captured
pre-review evidence hashes remain intact. Exact commands/scope: [TESTING.md](TESTING.md).

Initial preparation stopped before staging or commit. The owner subsequently
authorized exactly one reviewed local commit of these six files:
`fix(deploy): add sanitized Render setup diagnostics`.
Final review reran the focused suite: **467 passed**, 13.17 s, with the same single
deprecation warning. Render/Railway/VPS checks and source/import/documentation/
secret/artifact review passed again. All **1154** pre-review evidence hashes remain
intact. Git history supplies the resulting identity after staged review.
No DB connection, setup retry, migration, service startup, cloud modification,
deployment or push. Full backend/frontend/build suites and native/live checks
were not rerun for this diagnostic-only change. The next owner action is private
configuration review, not a setup retry to obtain a category; publication/live
actions need separate approval. The exact failing live input remains unknown.

## Render database owner compatibility - 15 November 2026

Started from the owner-reported published release 424f29c459cb8049d70809b74dd9082eade469b5.
The owner reports existing available merge_prod / PG17 in Oregon, initial username
merge_prod_user. No database connection, live permission query, setup/migration,
startup, cloud modification, staging, commit or push occurred during initial
preparation. The owner subsequently authorized one reviewed local commit, including
all ten pending files; push and live operations remain outside scope.

Added explicit setup-only MERGE_RENDER_SETUP_OWNER and a separate setup target.
Only merge_prod_user and legacy merge_migrator are accepted; no owner default,
arbitrary identifier or privileged-role fallback. Normal serve stays merge_runtime
and rejects setup inputs/targets. Owner preflight still requires exact database,
configured current_user, private address, TLS, PG17, non-superuser/CREATE ROLE,
actual database ownership and primary read-write status. Deployment schema uses
verified CURRENT_USER. Durable create-once claim, exact0006, runtime grants,
application behavior and all shared/VPS/Railway/local/CI safeguards remain unchanged.

Actual offline results: **397 focused checks passed** (13.69 s), including 143
Render cases; **2213 full database-free backend tests passed**, 32 database cases
deselected (125.95 s). Render/Railway/VPS deployment checks passed. Static review
passed for 336 source paths, 206 Python files, 761 local import targets, 369 local
Markdown links and 56 fragments. All 1122 captured baseline evidence paths retain
their hashes and ignore status. The capture includes the new audit pointer.
Exact commands and limits: [TESTING.md](TESTING.md).

The actual account's role flags, ownership and grant capability remain unknown:
its name/availability are not permission evidence. Missing authority must stop
before claim/DDL, not trigger another account or relaxed guard. The existing
fresh-resource Blueprint remains unchanged and must not recreate/adopt this
existing database. Use the manual Oregon procedure in [RENDER.md](RENDER.md).
Authorized local commit: `fix(deploy): support Render-provided setup owner`.
Final commit review reran the focused suite: **397 passed** (10.57 s), with one
existing Starlette/httpx deprecation warning. Render/Railway/VPS offline checks
passed again. Static review preserved all **1142** pre-review evidence hashes;
source/import/documentation/secret/artifact checks passed. Git history supplies
the resulting commit identity after staged review and diff checks.
New CI and separately approved live verification remain pending. Frontend/build,
native Docker/Caddy, DB/setup/migrations and cloud operations were not run for
this backend-only fix. The previous release results below retain their scope.


Updated: 15 November 2026. Deadline: **23:59 IST**. Merge is implemented locally;
Render Free is the selected demonstration target, prepared but not deployed.
The public repository exists. The owner reports five Actions jobs passed at
baseline `bb60ab3`; the local release needs a fresh hosted run after publication.
No verified live application URL, measured load report or completed integrated
browser certificate is claimed.

## Published release review - 424f29c

The owner authorized one local commit after validation:
`chore(deploy): prepare Render release and streamline docs`.
This entry records the validated scope; Git history supplies its actual identity.
No push, cloud, database, migration, fixture cleanup, startup, load or paid action
is authorized by this review. No application feature or invariant changed.

- Complete pending Render adapter reviewed: one public Caddy/React container,
  dynamic PORT, one loopback worker, same-origin auth/API/SSE, private TLS PG17,
  restricted runtime role, exact0006 readiness and separate explicit fresh setup.
- Railway/VPS source retained, including helpers directly imported by Render.
  All 290 non-Markdown starting paths, dependencies, migrations, CI, security,
  seed/load and acceptance tooling remain byte-identical.
- Public Markdown reduced from **50 to 46**. Eight redundant review paths were
  consolidated into labeled history; architecture/progress proposals and earlier
  results were preserved. Current architecture, testing, deployment and submission
  have canonical guides. Exact classifications: [documentation audit](archive/DOCUMENTATION_AUDIT.md).
- All **1044 baseline ignored evidence paths** match their captured hashes; no
  generated certificate, receipt or fixture was deleted or rewritten. The count
  includes the new audit pointer captured before cleanup.

## Actual offline evidence

Windows PowerShell, Python 3.11.9, Node 22.15.0, npm 10.9.2; locked dependencies.

| Check | Actual result |
| --- | --- |
| Full backend database-free suite | **2163 passed**, **32 database cases deselected**, 153.27 s |
| Focused Render/Railway/VPS/CI/release-support | **347 passed**, 21.33 s |
| Frontend, one worker | **434 passed**, 18 files, 239.02 s |
| TypeScript/Vite build | Passed, 50 modules, Vite 3.88 s |
| Render/Railway/VPS offline contracts | Passed |
| Dependency consistency / retained load-script syntax | Passed; no benchmark executed |
| Documentation/import/secret/artifact/hash review and working diff check | Passed; 366 local links, 56 fragments |

Exact commands, warnings, link/secret/artifact validation and limits: [TESTING.md](TESTING.md).
Historical PostgreSQL records remain profile30/SSE4/lifecycle10 with their original
source/receipt qualifications. Dated details and prior results are preserved in
[the progress journal](archive/PROGRESS_HISTORY.md) and
[engineering history](archive/ENGINEERING_HISTORY.md).

## Remaining gates and next action

Review the local commit, separately approve push, then require fresh CI for that
exact SHA. Only after cloud approval follow [RENDER.md](RENDER.md): fresh private
PG17, explicit setup deployment, inspect initialized/revision/SHA JSON, remove
privileged inputs, switch to ordinary runtime and verify HTTPS/auth/SSE/browser.
Setup liveness is not application readiness. Never load-test Free production.

Native Docker/Caddy is unavailable; actual container startup, managed role/grants,
512 MB memory use, 0.1 CPU behavior, edge identity/stream flushing and public HTTPS
remain unverified. Free cold starts and 30-day PostgreSQL expiry limit availability.
Required isolated seed/load measurement, full browser/mobile/keyboard acceptance,
design export, video and final organizer submission remain outstanding. Use
[SUBMISSION.md](SUBMISSION.md) for current artifact status.

# Testing and verification

## Session revalidation without workspace resets - 16 November 2026

Baseline: clean `1416c72434d5323ac5c80fb5f5854d53cda7f2c7`; the committed favicon
and index.html remain byte-identical. Windows, Node 22.15.0/npm 10.9.2, locked
dependencies; synthetic same-origin HTTP/EventSource and jsdom, no live account,
backend, database, public browser, deployment or fixture operation.

The initial targeted `SessionRevalidation.test.tsx` test failed before correction:
the existing workspace's `isConnected` became false immediately on focus, before
the deferred session response. This proves the React unmount path, without claiming
a real document navigation. After correction the same test retains DOM identity,
unsaved fields and scope throughout an unexpired matching-session 200 response.

| Directory | Exact command | Final actual result |
| --- | --- | --- |
| frontend | `npm.cmd test -- --reporter=dot --maxWorkers=1 src/SessionRevalidation.test.tsx src/DiscoveryNavigation.test.tsx src/Journeys.test.tsx src/Realtime.test.tsx` | **111 passed**, 4 files, 33.10 s |
| frontend | `npm.cmd test -- --reporter=dot --maxWorkers=1` | **464 passed**, 19 files, 188.13 s |
| frontend | `npm.cmd test -- --reporter=dot --maxWorkers=1 src/Admission.test.tsx` | **38 passed**, 30.16 s; unchanged admission suite investigated after the timeout |
| frontend | `npm.cmd run build` | TypeScript passed; Vite passed, 50 modules, 2.77 s |
| root | `git diff --check` | Passed |

Thirty new cases cover focus/blur/screenshot-like events, hidden/visible
minimize/restore, pageshow, rapid coalescing, superseded identity observations,
valid 200 DOM/scope preservation, 401/403/service failure, pending logout,
late account responses, credential/expiry replacement, local/persisted public
pagination and private inbox pagination, open profile drafts, explicit restoration,
absolute expiry including suspended timers, guest bootstrap, SSE continuity and
reconnect/reset canonical reads, and pending/uncertain journal non-replay/storage.
Current-scope 401/403 denials also hide immediately despite queued events; only
a genuinely replaced scope can fence an old denial as stale.
One earlier final-code full run had **463 passed / 1 failed**, 205.62 s: the first
unchanged admission case timed out finding the catalog button while its loading
state remained visible. The unchanged admission file then passed all 38 tests,
and the complete unchanged final code passed 464/464 on confirmation. No assertion,
timeout, dependency or test configuration was relaxed; one intermittent timing
failure remains recorded rather than claiming the suite is flake-free.
Existing reload/StrictMode, navigation-generation, stale read and mutation suites
remain. Four old lifecycle race cases now assert sequential coalescing instead
of overlapping GETs/full-page loading; identity and navigation isolation assertions
remain, alongside new late-result tests for transports that ignore cancellation.

No backend, authentication policy, business logic, dependencies, migration or
deployment files changed. All **1169** captured prior ignored evidence hashes
are preserved. Source/secret/artifact/link review covers the bounded change.
Raw logs and the pre-fix source snapshot are in the new ignored
`frontend/test-results/session-refresh-*` directory; historical receipts were
not rewritten. Full backend tests were not run for this frontend-only component.

Recommendation is **CONDITIONAL for live release**: offline acceptance passed;
no commit/push/deploy or public manual check was performed. After separately
approved deployment, the owner can use an existing authorized account to select
a hackathon, paginate, open/edit an unsaved draft, switch tabs, minimize/restore
and take a screenshot. Inspect document requests/navigation timing to distinguish
an actual reload from a React remount, and confirm unchanged DOM/view/no POST.
Do not create live mutations or revoke resources just to exercise this checklist.
Browser discard/crash/manual reload cannot retain memory-only drafts/journals;
only validated public navigation hints are recoverable. 403/network/service failures
still hide the workspace with explicit recovery; revocation detection is not
instant cross-tab notification. No HMR code is included in the production HTML.

## Render setup input diagnostics - 15 November 2026

Windows PowerShell, Python 3.11.9, existing locked dependencies. Synthetic input
validation only; no real environment secrets, DNS, database, setup, migrations,
listener/service startup, cloud action, commit or push. No acceptance rule changed.

| Directory | Exact command | Actual result |
| --- | --- | --- |
| backend | `.\.venv\Scripts\python.exe -B -m pytest -q tests/test_render.py tests/test_railway.py tests/test_production.py tests/test_ci_configuration.py tests/test_release_support.py --tb=short` | **467 passed**, 10.49 s; one existing Starlette/httpx deprecation warning |
| backend | `.\.venv\Scripts\python.exe -B -m app.render.check` | Passed offline Render contracts |
| backend | `.\.venv\Scripts\python.exe -B -m app.railway.check` | Passed unchanged Railway contracts |
| backend | `.\.venv\Scripts\python.exe -B -m app.production.check` | Passed unchanged VPS contracts |

Seventy new regressions cover every input diagnostic category, failure ordering,
documented Docker defaults, secret-format boundaries and refusal, unknown/forged
exception categories and exact sanitized stderr. Rejected input never reaches
DNS, initialization or the HTTP listener. Exceptions are not stringified, and
normal serve remains runtime-only. Published acceptance decisions were also
compared offline with the pending implementation: **758 synthetic cases, zero
acceptance changes**. Local results are retained under the new ignored `backend/test-results/render-input-review-*`
directory. Historical evidence is retained, not rewritten.

The full backend/frontend/build suites were not rerun for this diagnostic-only
patch. Previous results below retain their original scope. Live cause is still
unknown: owner confirms throttle absent, full setup SHA, explicit PORT 10000 and
owner merge_prod_user, without exposing credentials or dashboard environment.
The complete validation trace and private review checklist are in
[RENDER.md](RENDER.md#setup-input-rejection-offline-diagnosis). Stop before setup
retry, publication or deployment; no permission/credential relaxation is justified.

## Render setup-owner compatibility - 15 November 2026

Python 3.11.9 on Windows PowerShell with existing locked dependencies. Only
synthetic env/DNS/connections/processes were used in the focused tests; no database,
setup, migration, server/browser, cloud, commit or push action was performed.

| Directory | Exact command | Actual result |
| --- | --- | --- |
| backend | `.\.venv\Scripts\python.exe -B -m pytest -q tests/test_render.py tests/test_railway.py tests/test_production.py tests/test_ci_configuration.py tests/test_release_support.py --tb=short` | **397 passed**, 13.69 s; includes **143 Render cases** |
| backend | `.\.venv\Scripts\python.exe -B -m pytest -q -m 'not database' --tb=short` | **2213 passed**, 32 database cases deselected, 125.95 s |
| backend | `.\.venv\Scripts\python.exe -B -m app.render.check` | Passed offline Render contracts |
| backend | `.\.venv\Scripts\python.exe -B -m app.railway.check` | Passed unchanged Railway contracts |
| backend | `.\.venv\Scripts\python.exe -B -m app.production.check` | Passed unchanged VPS contracts |
| root | `git diff --check` | Passed |

Fifty new regressions cover explicit reviewed owner selection, missing/unknown/
reserved names, runtime refusal, exact connected identity, database/TLS/version/
owner/CREATE ROLE rejection, schema CURRENT_USER ownership, bounded setup engine,
Blueprint validation and CLI rejection before status-listener construction. Existing
transactional rollback/replay, exact0006, runtime authentication/CSRF and platform
checks remain. One existing Starlette/httpx deprecation warning remains.

The new ignored local audit helper runs from repository root:

```powershell
$ownerEvidence = Get-Content backend/test-results/render-owner-current.txt
.\backend\.venv\Scripts\python.exe -B (Join-Path $ownerEvidence 'check_repository.py')
```

It checks the explicitly bounded source delta, secret/artifact patterns, Python
AST/imports, JSON, local Markdown paths/fragments and unchanged source/evidence.
All **1122 baseline evidence paths** retain their hashes/ignore status (including
the new pointer captured at baseline). Shared guard/grant files, migrations, CI,
frontend, Docker/Caddy and root fresh-resource Blueprint stay byte-identical.
No actual account privilege is established by these tests. Frontend/build and
native/live deployment checks were not rerun for this backend-only change. The
existing Oregon database must not be recreated or modified during review.
Configuration and remaining live requirements: [RENDER.md](RENDER.md).

## Previous local release review - 15 November 2026

Actual environment: Windows PowerShell, Python 3.11.9, Node 22.15.0 and npm 10.9.2;
existing locked dependencies. No database, migration, startup, browser, benchmark,
Docker build, hosted CI or cloud action was run. These are offline results for
the documentation cleanup plus the already pending Render/Railway adapters.

| Directory | Exact command | Actual result |
| --- | --- | --- |
| backend | `.\.venv\Scripts\python.exe -B -m pytest -q -m 'not database' --tb=short` | **2163 passed**, **32 database cases deselected**, 153.27 s |
| backend | `.\.venv\Scripts\python.exe -B -m pytest -q tests/test_render.py tests/test_railway.py tests/test_production.py tests/test_ci_configuration.py tests/test_release_support.py --tb=short` | **347 passed**, 21.33 s; includes 93 Render cases |
| frontend | `npm.cmd test -- --reporter=dot --maxWorkers=1` | **434 passed**, 18 files, 239.02 s |
| frontend | `npm.cmd run build` | TypeScript passed; Vite 50 modules, 3.88 s |
| backend | `.\.venv\Scripts\python.exe -B -m app.render.check` | Offline Docker/Caddy/Blueprint contract passed |
| backend | `.\.venv\Scripts\python.exe -B -m app.railway.check` | Retained Railway contract passed |
| backend | `.\.venv\Scripts\python.exe -B -m app.production.check` | Retained VPS contract passed |
| backend | `.\.venv\Scripts\python.exe -B -m pip check` | No broken requirements |
| root | `node --check load/board.js` | Syntax passed; benchmark not executed |

Check `$LASTEXITCODE` after each PowerShell command. Linux uses `.venv/bin/python`
and `npm`. Frontend verification uses one worker because earlier parallel runs
showed timing intermittency; assertions, timeouts and isolation were not weakened.
The existing Starlette/httpx deprecation warning and Vitest environment-performance
advice remain. No linter is configured and no dependency was changed/downloaded.

## Documentation, source and artifact validation

All local Markdown file links and fragments, backend import targets, Python
AST/compilation, JSON, Docker COPY sources, migration graph and retired-document
executable references are checked by the new local-only audit helper:

```powershell
$releaseEvidence = Get-Content backend/test-results/release-review-current.txt
.\backend\.venv\Scripts\python.exe -B (Join-Path $releaseEvidence 'check_repository.py')
git diff --check
# During the reviewed staging step, before the authorized local commit:
git diff --cached --check
```

The helper also checks high-signal secret/artifact patterns, new-document whitespace,
exact archived code blocks, unchanged non-Markdown sources and all 1044 baseline
ignored evidence hashes. The baseline includes the new audit pointer created at
capture. No historical receipt was modified. Three matches in unchanged old tests
are synthetic credential/Origin/redaction fixtures. This is a targeted scan, not
an exhaustive secret audit. The first archive check found doubled Windows line
endings in two copies; normalization restored exact original code blocks before
staging. No content was removed to satisfy validation.

Final static review passed: **336 source paths**, **46 Markdown files**,
**206 Python files** compiled in memory, **761 local import targets**, **366 local
Markdown links** and **56 fragments**. All 290 non-Markdown starting paths remain
byte-identical; no executable reference to a retired document remains. The six-
revision migration graph has the sole head `0006_profiles`. Working-tree
`git diff --check` passed. Staged checks are a required gate before the local commit.

The before/after classification, per-removal reasons, complete retained inventory
and exact release delta are in the [documentation audit](archive/DOCUMENTATION_AUDIT.md).
The helper/baseline/results remain ignored locally and are not a public CI dependency.
Earlier verification tables are retained once in
[engineering history](archive/ENGINEERING_HISTORY.md#testing-before-release-cleanup),
with detailed dated entries in [the progress journal](archive/PROGRESS_HISTORY.md).

## GitHub Actions contract

[ci.yml](../.github/workflows/ci.yml) is unchanged from the published baseline.
The owner reports all five expanded jobs passed at `bb60ab3`; this release still
needs a new hosted run after separately approved publication. No run URL was
fetched or invented during this review.

The workflow retains the offline job and four exact PostgreSQL 17 revisions:
`0003_auth`, `0004_admission`, `0005_invitations`, `0006_profiles`. Health options
use `--health-cmd=pg_isready --health-interval=5s --health-timeout=5s --health-retries=10`,
without the former broken multiword quoting. Readiness is not authentication;
guarded bootstrap/suites verify real identity and revision.

The Ubuntu runner resolves the service PID and runs its Python through
`sudo nsenter --net`, preserving checkout/interpreter filesystem while joining
only the PostgreSQL container network namespace. Fixed loopback guards stay intact.
Service/admin input matches the run/attempt; the app role gets a fresh password.
Authenticated API suites and the distinct 50-caller last-seat race remain required.
Strict native exits, exact completed suite counts, invariant verification and
sanitized receipt uploads reject missing/skipped/inconclusive results. No workflow,
runner guard or required test was removed or relaxed.

## Historical PostgreSQL evidence

| Suite | Retained result | Scope qualification |
| --- | --- | --- |
| Profiles | 30/30, exact `0006_profiles` | Historical source/native-bound receipt |
| Realtime | 4/4, exact `0005_invitations` | Historical source/native-bound receipt |
| Lifecycle | 10/10, exact `0005_invitations` | Aggregate report and owner-confirmed exit; no independent native/source receipt |
| Invitations/G1 | 13 cases x 3, including three 50-caller last-seat races | Prior source/provenance limits in [G1_ACCEPTANCE.md](G1_ACCEPTANCE.md) |

Offline tests cannot certify PostgreSQL serialization or rebind old certificates
to new source. Never reset fixtures, rewrite receipts or reuse a consumed campaign.

## Remaining live and performance gates

Full integrated browser acceptance remains incomplete. The original campaign is
consumed and uncertified; [integrated host](INTEGRATED_HOST.md),
[browser safeguards](BROWSER_ACCEPTANCE.md) and
[recovery history](archive/ENGINEERING_HISTORY.md#batch-d-recovery) explain its limits.
Real mobile/keyboard, cookie, proxy, two-client SSE and reconnect checks remain.

[Release validation](RELEASE_VALIDATION.md) uses explicit isolated targets for
10,000 users, 2,000 teams and 100 clients. No measured p95 exists; <200 ms is the
acceptance target. Never seed/load-test retained acceptance or Free production.

Docker/Caddy binaries are absent locally. No native Caddy validation, image build,
Linux/container startup, managed role/grant/setup, Render Blueprint validation,
512 MB peak memory/0.1 CPU measurement, public HTTPS or new hosted CI was run.
Offline contracts passed; live success is not claimed. Use [RENDER.md](RENDER.md)
for exact settings, initialization and remaining deployment checks.

# Testing and verification

## Current local release review - 15 November 2026

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

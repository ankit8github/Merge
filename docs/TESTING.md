# Testing and verification

Offline tests check application behavior with service/connection doubles, API
contracts, evidence guards and repository configuration. They do not prove
PostgreSQL serialization, browser transport, TLS or load capacity.

## Reproducible offline commands

With locked dependencies already installed, run from the indicated directories:

| Directory | Command |
| --- | --- |
| backend | `.\.venv\Scripts\python.exe -B -m pytest -q -m 'not database' --tb=short` |
| backend | `.\.venv\Scripts\python.exe -B -m pytest -q tests/test_ci_configuration.py tests/test_release_support.py tests/test_production.py --tb=short` |
| backend | `.\.venv\Scripts\python.exe -B -m app.production.check` |
| frontend | `npm.cmd test -- --reporter=dot --maxWorkers=1` |
| frontend | `npm.cmd run build` |
| root | `node --check load/board.js` |
| root | `git diff --check` |

PowerShell users should check `$LASTEXITCODE` after each command. Linux uses
`.venv/bin/python` and `npm`. The frontend command uses one worker because earlier
parallel runs showed timing intermittency. Vitest/jsdom and Node harness tests
are not full browser acceptance. No lint script is currently configured.

## Evidence scope

The published baseline records 1,972 database-free backend passes, 32 database
cases deselected, 434 frontend passes across 18 files and a passing TypeScript/Vite
build. These are recorded historical local results in [PROGRESS.md](PROGRESS.md).
The repository polish results are recorded below after actual execution.

Retained local PostgreSQL acceptance reports record:

| Suite | Historical result | Qualification |
| --- | --- | --- |
| Profiles | 30/30 at `0006_profiles` | Source/native-bound receipt |
| Realtime | 4/4 at `0005_invitations` | Historical source/native-bound receipt |
| Lifecycle | 10/10 at `0005_invitations` | Aggregate report, owner-confirmed exit; no independent source/native receipt |
| Invitations / G1 | 13 cases x 3; three 50-caller last-seat races | Aggregate/provenance limits in [G1_ACCEPTANCE.md](G1_ACCEPTANCE.md) |

These results do not certify modified sources, current public CI or production.
Historical reports, manifests and hashes remain local and unchanged. Never
rewrite an old receipt to claim a new source binding.

## GitHub Actions contract

[ci.yml](../.github/workflows/ci.yml) uses the JSON subset of YAML 1.2, allowing
standard-library offline parsing without a new dependency. The PostgreSQL service
now uses version 17 and the argument value equivalent to:

```yaml
options: >-
  --health-cmd=pg_isready
  --health-interval=5s
  --health-timeout=5s
  --health-retries=10
```

The previous quoted multiword command allowed `-U` to escape into Docker's flags.
The replacement has no embedded shell quoting or multiword health argument.
`pg_isready` checks server availability, not credentials or schema readiness;
bootstrap and guarded suites perform their own authenticated identity checks.

Four independent jobs retain exact revisions `0003_auth`, `0004_admission`,
`0005_invitations` and `0006_profiles`. The auth/team API suites alone account
for 53 expected cases; admission, invitations, lifecycle, realtime and profiles
remain required. Invitation acceptance includes the distinct authenticated
50-caller last-seat race.

The hosted Ubuntu runner binds the service port to loopback. The command obtains
the service container PID, resolves the host Python executable, then runs Python
through `sudo nsenter --net`. Only the network namespace changes; the runner's
filesystem, checkout, working directory and interpreter remain in use. Therefore
guarded `127.0.0.1:5432` connections reach PostgreSQL inside the container without
weakening the fixed identity checks. The same run/attempt value supplies the
service password and `CI_ADMIN_PASSWORD`; the application role gets a separately
generated random password. These are disposable CI inputs, not production secrets.

The wrapper requires GitHub-hosted CI markers, a fresh database/role namespace,
exact suite counts, native exit zero and completed invariant verification. It
rejects missing/ambiguous reports. Receipt upload runs even after failure and
fails if files are absent. No `continue-on-error` bypass is introduced.

**Public CI remains unverified.** The owner reported initialization failure on the
published workflow. This task corrects configuration and tests it offline; no
remote run was triggered or rerun. Docker availability, sudo/nsenter permissions,
Python visibility, container readiness, locked Linux installs, receipt handling
and real PostgreSQL suites must all pass on a new hosted execution.

## Live acceptance and performance

Consult [release validation](RELEASE_VALIDATION.md) and [test database guards](TEST_DATABASE.md)
before any database access. Each live suite has a fixed target/revision and fresh
fixture scope; default offline tests must not be used as race evidence.

Full integrated browser acceptance is incomplete. The original consumed campaign
must not be restarted or adopted; [integrated host](INTEGRATED_HOST.md) and
[recovery history](BATCH_D_RECOVERY.md) explain its limits. Mobile/keyboard/real
cookie and proxy checks remain pending.

[Seed/load tooling](RELEASE_VALIDATION.md) targets a separate disposable
`merge_bench`, with 10,000 users, 2,000 teams and 100 clients. It has not been
executed for a measured report. The p95 < 200 ms figure is an acceptance target,
not a result. No seed, k6, PostgreSQL or browser execution was part of this polish.

## Repository polish validation - 15 November 2026

Actual environment: Windows PowerShell, Python 3.11.9, Node 22.15.0, npm 10.9.2;
existing locked dependencies, no installation or live operation.

| Exact command (directory as above) | Actual result |
| --- | --- |
| Backend full offline command above | **1,975 passed**, 32 deselected, 97.06 s, exit 0 |
| Backend focused CI/release/production command above | **159 passed**, 10.46 s, exit 0 |
| Frontend one-worker command above | **434 passed**, 18 files, 147.91 s, exit 0 |
| `npm.cmd run build` | TypeScript and Vite passed; 50 modules, Vite 3.48 s, exit 0 |
| `python -B -m app.production.check` using the backend venv | Offline JSON/topology/security contracts passed, exit 0 |
| `python -m pip check` using the backend venv | No broken requirements, exit 0 |
| `node --check <file>` for `load/board.js` and all six JS/MJS files in `frontend/test_support/` | Seven syntax checks passed; no browser/k6 execution |
| `git diff --check` | Passed |

The backend reports the existing Starlette/httpx deprecation warning. Git emits
existing LF/CRLF conversion notices. Neither warning was suppressed or used to
weaken checks. The additional three backend tests cover CI configuration only.

Static review compiles Python in memory, checks local backend import targets,
Markdown file links, required migration/suite/script paths, JSON configuration,
Docker COPY inputs, generated/private artifact exclusions and high-signal secret
patterns. Three matches in unchanged existing tests were inspected as synthetic
Origin/DSN/redaction fixtures; no real credential match was identified. This is a
targeted scan, not proof against every possible secret format.

Final static review passed for 310 tracked/new paths: 185 Python files compiled
in memory, 680 local backend import targets and 238 Markdown file links checked.
The tracked PowerShell script and nine new-guide PowerShell blocks parsed without
execution. All 35 required migration/suite/script/deployment paths checked exist.

All 958 preexisting local evidence files remain byte-identical and ignored.
The complete retained-path classification is in the [audit inventory](archive/REPOSITORY_AUDIT.md).
New local baselines, result summaries and an executable offline review helper are
retained under ignored `backend/test-results/repo-polish-e61161879e0a416784e2bc8ff3e44e00/`.
From the root, the review helper is reproducible with:

```powershell
.\backend\.venv\Scripts\python.exe -B backend/test-results/repo-polish-e61161879e0a416784e2bc8ff3e44e00/check_repository.py
```

That local helper requires the retained baseline; it is intentionally not a public
CI prerequisite. No PostgreSQL/race/migration/seed/load/native Docker/Caddy/browser/
HTTPS execution or remote action ran. A passing hosted Actions run remains required.

The first local helper ignore comparison failed because Windows text-mode stdin
added carriage returns to Git path arguments. NUL-delimited byte input corrected
the helper; evidence bytes and ignore rules were not changed.

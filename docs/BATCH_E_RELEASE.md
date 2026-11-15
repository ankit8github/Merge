# Batch E local freeze and public delivery handoff

15 November 2026; deadline **23:59 IST**. Application code is frozen. Batch E
reviews the existing changes and runs offline checks, then creates exactly the
one owner-authorized local commit if staged gates pass. No remote/DB/service,
benchmark, provisioning, deployment or submission-form operation is performed.
Commit message: `chore(release): finalize application acceptance tooling`.
The actual hash belongs in the final response/ignored receipt after creation;
it cannot be embedded self-referentially in this commit's source.

## Complete starting-path review

Starting main: `db17f3ef2c2934d2d4cc7db06499a291949a3d16`; 39 pending paths,
none staged. Every candidate is text source, tests, public plan or docs. No
credential, raw diagnostic, dump, binary, build output or installed dependency
belongs in the commit. This handoff and finalization of the previously clean
DEMO.md add two paths: **41 reviewed commit paths**. README/PROGRESS/SUBMISSION
updates are within the starting inventory. No feature, runtime-source, dependency
or migration change is made in Batch E.

Paths below are repository-relative; abbreviated sibling names use the nearest
preceding directory. The staged manifest records every full path and blob identity.

| Reviewed files | Disposition / reason |
| --- | --- |
|README.md; docs/DESIGN_ONE_PAGE.md; PROGRESS.md; RELEASE_VALIDATION.md; SUBMISSION.md|Honest current status, historical evidence/provenance and owner gates; old commands grant no new live permission.|
|frontend/src/api.ts|Specific 409 messages; transport/session/command behavior preserved.|
|frontend/src/components/Admission.tsx; Invitations.tsx|Named accessible actions/less duplicate feedback; UUID targets and uncertain recovery retained.|
|frontend/src/components/HealthStatus.tsx|Liveness wording does not claim account/domain readiness.|
|frontend/src/components/Lifecycle.tsx|Cancel restores focus; leadership loss withdraws unsubmitted removal; backend remains authoritative.|
|frontend/src/components/Profile.tsx|Only definite 422/invalid_request permits draft correction; unknown/CAS failures require reload; accessible errors.|
|frontend/src/App.test.tsx; DiscoveryNavigation.test.tsx; ProductAudit.test.tsx|Relevant UI regressions, actual effect/fetch synchronization and no unintended mutation.|
|acceptance/integrated-campaign.json|Public planned scope/budgets; consumed namespace remains preserved, not reusable.|
|backend/release_support/integrated_plan.py; integrated_ledger.py|Closed plan/target, exact 38-POST/14-effect protocol, one active command and no unknown-outcome retry.|
|backend/release_support/integrated_host.py; integrated_diagnostics.py|Fixed isolated target, nine service overrides/closed dependency audit; secret-free aggregate diagnostics.|
|backend/release_support/integrated_run.py; integrated_observer.py; integrated_certify.py|CreateNew fence, native exits, mandatory drain/ledger/observer, prior-row checks and hash-bound observations.|
|backend/release_support/profile_inspection.py; profile_inspection_capture.py; scripts/inspect_merge_profile_0005.ps1|Owner-only SELECT snapshot, hidden credentials and exclusive native/source capture. Historical 0005 tool, not a reason to rerun it on now-0006 profile state.|
|backend/tests/test_integrated_diagnostics.py; test_integrated_host.py; test_integrated_evidence.py; test_integrated_plan.py|Synthetic lifecycle/ASGI/evidence/ledger tests, live-operation traps and tamper/failure cases.|
|backend/tests/test_profile_inspection_auth.py; test_profile_inspection_capture.py|Hidden-input, persistence, source/native and tamper regressions; no real inspection in tests.|
|frontend/test_support/integratedCampaign.js; integratedCampaign.test.js; integratedEvidence.mjs; integratedEvidence.test.js|Offline budget/scope and owner-observation integrity checks; outside production src; no browser or credentials.|
|docs/BATCH_D_RECOVERY.md; INTEGRATED_ACCEPTANCE.md; INTEGRATED_HOST.md; PRODUCT_AUDIT.md|Contracts, offline results and historical failure boundaries. Current overlays supersede stale checkpoint status, not evidence.|
|docs/DEMO.md; BATCH_E_RELEASE.md (freeze additions)|Final <=5-minute script, concrete future commands and delivery checklist.|

All historical receipts/markers and both old browser hosts stay byte-identical.
Ignored evidence/logs stay local. Authentication, transactions, locks, constraints,
audit/outbox, mutation budgets and final observer requirements are not weakened.

## Safeguards and proof limits

Server-validated sessions/current CSRF, exact Origin/Fetch Metadata and durable
login/invite throttles remain. PostgreSQL and the existing transaction owner
enforce membership/capacity/leadership/idempotency; process counters grant nothing.
Production fixes merge_prod, separate restricted runtime/migration roles, exact
0006_profiles and one trusted Caddy peer, without Settings/merge_dev fallback.

Production uses app.production.serve and its separate factory. Production app
and frontend src import no integrated host/diagnostics/ledger or inspection tool.
Dockerfile.api copies only the four existing migration-related release_support
helpers, not integrated tooling/test_support. A harness failure is not a proven
production startup defect. Native containers, grants and TLS remain unverified.

Historical local PostgreSQL results: profile 30/30, SSE 4/4, lifecycle 10/10;
provenance limits remain in BATCH_D_RECOVERY.md/LIFECYCLE.md. These are not new
source, production-role, public CI or HTTPS certificates. A commit changes HEAD;
never rewrite old receipts or loosen full-source eligibility to make them current.

Campaign `17ff1152-1ac0-4ace-a887-13436dd2963f` remains permanently consumed and
uncertified: browser checkpoints 0/13 (owner baseline), saved POST/domain counters
0, readiness/exact failed drain check unknown, no final observer. Zero POSTs does
not certify database-wide preservation. No campaign retry/adoption/reset is part
of the release or deployment proposal.

## GitHub publication prerequisites and exact proposal

Local findings: author identity configured; only sample Git hooks; no remote;
GitHub CLI absent. No credential store/account/token or authenticated remote was
queried. Owner authentication is **unverified**. GitHub CLI is optional: a later
approved HTTPS push may use Git for Windows credential-manager/browser sign-in.

Owner must choose account/repository, authorize publication of the reviewed
history/workflow and have rights to publish both. Create an EMPTY public repo
without initial README/license/gitignore. Enable Actions/hosted Linux runner
access. Never place a password/PAT into a remote URL, command or retained log.

**Future PowerShell, NOT EXECUTED.** Replace placeholders with the owner-approved
public account/repository. Remote setup and push each require approval. Divergent
remote history is a stop; never force-push or merge automatically.

```powershell
Set-Location -LiteralPath 'I:\Merge'
$releaseCommit = git -c safe.directory=I:/Merge rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Cannot identify release' }
if (git -c safe.directory=I:/Merge status --porcelain) { throw 'Dirty release tree' }
if (git -c safe.directory=I:/Merge remote) { throw 'Review existing remote first' }
$publicRepository = 'https://github.com/OWNER/REPOSITORY.git'
if ($publicRepository -match '/OWNER/|/REPOSITORY\.git$') { throw 'Set approved repository URL' }
# APPROVAL G1: configure this credential-free public remote.
git -c safe.directory=I:/Merge remote add origin $publicRepository
if ($LASTEXITCODE -ne 0) { throw 'Remote configuration failed; stop' }
# APPROVAL G2: publish reviewed main history and trigger its workflow.
git -c safe.directory=I:/Merge push -u origin main
if ($LASTEXITCODE -ne 0) { throw 'Publication failed; stop without force/retry' }
```

Review the actual public URL and Actions run at the same commit. The workflow has
read-only repository permissions and isolated PostgreSQL 16 services at four exact
revisions. Its wrapper requires GitHub-hosted CI and enters the service network
namespace; it refuses local/retained target adoption.

| Revision | Required suites |
| --- | --- |
|0003_auth|18 authenticated auth API + 35 team creation API cases.|
|0004_admission|35 admission cases.|
|0005_invitations|13 invitation API cases including test_distinct_authenticated_50_caller_last_seat; lifecycle 10; realtime 4.|
|0006_profiles|30 profile cases.|

The race uses 50 distinct actors/sessions/CSRF values, gates after actual HTTP
authentication, observes PostgreSQL overlap and checks winner/rejections,
invariants and exact replay. Source coverage is verified; **no public Actions pass
is claimed**. Require every job green, no skipped/failed acceptance cases and
complete native/source artifacts. Inspect sanitized artifacts before sharing;
automatic upload is not a privacy review. Do not publish a fabricated CI badge.

## Hosting prerequisites and shortest existing route

Use the existing Caddy/static React -> one FastAPI worker -> private PostgreSQL
17 Linux single-host proposal. No alternative architecture is required. Docker,
Caddy and k6 are absent locally; native validation/image builds have not run.

Owner supplies approved VPS/SSH access, Docker/Compose, an owned domain and direct
DNS A/AAAA. Confirm costs/resources, subnet overlap, firewall, image provenance/
digests and fresh volumes/backups. Only 80/443 plus owner-restricted SSH are public;
API 8000/DB 5432 stay private. Fixed subnets are 172.30.240.0/29 and
172.30.241.0/29; sole trusted proxy is 172.30.240.2/32. No CDN/extra proxy is assumed.
Exact lower-case HTTPS origin has no path/port. Generate separate runtime,
migrator/admin DB password files and shared 32-byte throttle key with the existing
create-only helper; deploy/private is ignored. Retain Caddy certificate/config and
PostgreSQL volumes. Production restricted grants/readiness need real verification.

**Future Linux bash, NOT EXECUTED.** On the approved host obtain the actual frozen
revision; replace all placeholders. Each nonzero result stops. API startup never
initializes/migrates. These commands do not authorize provisioning or execution now.

```bash
set -euo pipefail
git clone 'https://github.com/OWNER/REPOSITORY.git' Merge
cd Merge
git checkout --detach 'OWNER_REVIEWED_RELEASE_COMMIT'
test -z "$(git status --porcelain)"
python3.11 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.lock
export MERGE_PROD_ORIGIN='https://REAL_OWNED_HOST'
export MERGE_IMAGE_TAG="$(git rev-parse HEAD)"
(cd backend && .venv/bin/python -m app.production.check)
# APPROVAL H1: create-only secrets and reviewed images/configuration.
(cd backend && sudo .venv/bin/python -m app.production.prepare \
  --confirm-new-secrets --origin "$MERGE_PROD_ORIGIN")
docker compose -f deploy/compose.json config --quiet
docker compose -f deploy/compose.json build api web
docker image inspect --format '{{.Id}}' "merge-api:$MERGE_IMAGE_TAG" "merge-web:$MERGE_IMAGE_TAG"
docker compose -f deploy/compose.json run --rm --no-deps --entrypoint caddy web \
  validate --config /etc/caddy/config.json
# APPROVAL H2: fresh production-only volume/roles/explicit migrations.
docker compose -f deploy/compose.json up -d postgres
```

STOP and verify PostgreSQL container health before continuing. Existing/partial
state is a stop for review, not cleanup/adoption/overwrite or automatic rerun.

```bash
set -euo pipefail
docker compose -f deploy/compose.json run --rm --no-deps bootstrap --confirm-new-merge-prod
docker compose -f deploy/compose.json run --rm --no-deps migrate prepare --confirm-merge-prod
docker compose -f deploy/compose.json run --rm --no-deps migrate migrate --confirm-merge-prod
docker compose -f deploy/compose.json run --rm --no-deps migrate verify --confirm-merge-prod
# APPROVAL H3: exactly one new approved demo catalog event.
docker compose -f deploy/compose.json run --rm --no-deps migrate catalog --confirm-merge-prod \
  --id OWNER_APPROVED_UUID --name 'Owner-approved demo hackathon' --min-size 2 --max-size 4
# APPROVAL H4: API launch; require actual /ready health before ingress.
docker compose -f deploy/compose.json up -d api
docker compose -f deploy/compose.json ps
```

STOP until API health/readiness is confirmed, then separately approve ingress:

```bash
docker compose -f deploy/compose.json up -d web
docker compose -f deploy/compose.json ps
```

Verify externally: valid TLS/redirect, React assets/deep links, restricted-role
auth/domain/profile workflows, Secure host-only cookie/CSRF/Origin/proxy policy,
two-client SSE/reconnect, keyboard/mobile. /health is liveness; /ready is internal
and blocked by Caddy. Retain actual URL/commit/image IDs/native exits and sanitized
smoke evidence. On failure stop web then API and retain volumes. Never down -v,
prune, reset or downgrade automatically. PRODUCTION.md contains full migration,
grant/backup/rollback semantics. No production pass exists here.

## Performance and artifact preparation

Reviewed seed/benchmark_host/load/board.js and their offline regressions. Seed:
exactly 10,000 users, 2,000 teams, 5,000 memberships and 10,000 profiles; deterministic,
atomic and empty-target-only, with true-row/identity/roster checks. Load: 100 real
authenticated clients, 20s warmup/60s measurement, board p95 <200ms, zero errors,
>=100 samples, real session setup before measurement and aggregate-only evidence.
Optional 32-SSE comparison is secondary to the mandatory baseline/public delivery.

Still missing: reviewed k6 installation, approved isolated exact-0006 merge_bench/
merge_bench_app, truthful hardware/cache/history disclosure, actual seed/load/native
outputs and report. Never load-test production/retained fixtures. After separate
provision/migration approvals in RELEASE_VALIDATION.md, the minimum **future
PowerShell proposals** in I:\Merge\backend are:

```powershell
.\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m release_support.seed --confirm-merge-bench --seed 2026
if ($LASTEXITCODE -ne 0) { throw 'Seed failed; retain state and stop' }
.\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m release_support.seed --confirm-merge-bench --seed 2026 --verify-only
if ($LASTEXITCODE -ne 0) { throw 'Seed verification failed; stop' }
# Approved foreground terminal 1; no transcript/piping of hidden input.
.\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m release_support.benchmark_host --confirm-merge-bench --seed 2026
# Approved terminal 2; complete private environment disclosure first.
.\.venv\Scripts\python.exe -W error::getpass.GetPassWarning -m release_support.load --confirm-merge-bench --seed 2026 --sse-clients 0 --environment test-results/bench-environment.json
if ($LASTEXITCODE -ne 0) { throw 'Load failed/incomplete; retain evidence and stop' }
```

Use load/environment.example.json's exact schema, not fabricated hardware values.
The report must include actual commit/revision/date, PG/k6 versions, topology/
resources/cache/outbox history, seed counts, workload/window, p50/p95/p99, errors,
requests/throughput, native exits and limits. Missing/failed outputs stay missing/
failed, including threshold exit 99. Never publish cohort passwords/cookies/CSRF
or headers. No benchmark was executed here and no percentile is invented.

Design export: open DESIGN_ONE_PAGE.md in a trusted local Markdown/document
renderer; export A4 portrait with roughly 14mm margins and readable 10–11pt body.
Verify the actual PDF is exactly ONE page, readable, unclipped and has current
evidence labels/links. Tighten wording/spacing if needed without omitting data
model, race prevention, trade-offs, extra-week plan or pending evidence. Source
length is not pagination proof. No renderer/browser/PDF export ran here.

DEMO.md targets 4:50/hard 5:00 on the same release with fresh separately approved
demo scope. Pause before credential entry, show actual results/score components,
review the whole exported recording/duration and public access, and never imply
that recording certifies the consumed campaign. No recording/publication ran.

## Official submission checklist and missing evidence

This follows REQUIREMENTS.md's captured organizer specification and its official
challenge link. The live form was not opened or interacted with; current field
labels/options were not independently inspected.

- [ ] Individual/original PS1 work; owner can explain and live-modify it.
- [ ] Public GitHub URL for this revision, reproducible setup, honest README and
  successful Actions evidence with >=20 API tests and authenticated 50-caller race.
- [ ] Externally verified public HTTPS React/API URL, mobile/keyboard usability
  and real live-update/security/auditing/matching workflows.
- [ ] Actual 10,000-user/2,000-team evidence and 100-client board p95 <200ms load
  report with declared environment, native exits and reproducible script.
- [ ] Reviewed one-page design: data model, race prevention, trade-offs, extra week.
- [ ] Actual walkthrough <=5 minutes, no credentials/private data, public reviewer
  access without owner credentials.
- [ ] Enter actual repo/live/load/design/video links into the organizer workspace
  before 15 November 2026, 23:59 IST; verify access and retain the real submission
  confirmation/time. No form action or submission occurred in this task.

All public links and current CI/load/HTTPS/browser evidence remain missing.
Historical local PG certificates keep their original scope. A local commit and
offline build cannot establish deployment, performance or successful submission.

## Freeze evidence and next owner gate

PROGRESS.md records exact new offline results. Ignored freeze directory:
backend/test-results/batch-e-freeze-8cd3dd0d101942f29f3ee99a9ecaf1d9/.
It holds starting source/evidence inventory, publication scan, new test/build logs,
staged path/blob manifest and the post-commit local receipt. The initial pre-stage
scan covered 302 source files and 603 reachable historical Git blobs, with no
high-signal secret tokens/private keys, suspicious artifact paths or oversized
unscanned blobs. This targeted review cannot guarantee unknown secret formats.

PASS applies only to verified local freeze gates. Public delivery remains
CONDITIONAL/BLOCKED on the concrete missing prerequisites above. Next protected
action: owner authentication and approval to create/select the public GitHub repo,
configure its credential-free remote and push main. No live action is implied.

Owner exercise: explain why a new commit cannot make an old full-source receipt
current, then trace the 50-caller case through the exact-0005 CI plan.

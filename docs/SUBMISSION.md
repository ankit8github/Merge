# PS1 submission and release gate

Deadline: **2026-11-15 23:59 IST**. Prepared only; nothing published/submitted.
Replace PENDING only after approval/verification. No secrets, fixture dumps or
invented measurements. Check organizer workspace requirements before delivery.

| Required item | Link-ready location | State |
| --- | --- | --- |
|Public repository|PENDING: verified repository URL|Local A/B/C release candidate; no remote publication.|
|HTTPS app/API|PENDING: verified public origin|Package only, no deployed evidence.|
|Successful Actions|PENDING: run URL/artifacts|Workflow unrun; require APIs and50-caller race.|
|Scale seed|PENDING: receipt/report link|Generator only;10000/2000 not live counted.|
|Load report|PENDING: report/script/revision/environment|100-VU tooling only; no measured p95; required<200ms.|
|One-page design|[Design](DESIGN_ONE_PAGE.md)|Concise source; exported pagination needs checking.|
|Video<=5min|PENDING: URL and duration|[Script](DEMO.md) only, no recording.|
|Setup/evidence|[README](../README.md)|Actual features, limits and commands.|

Earlier preparation order (historical; the current freeze order below supersedes it):

1. Review combined diff/inventory. Approve guarded DB writes/new targets. Finish
   exact0005 SSE4 and exact0006 profile30 with complete receipts; preserve all old
   fixtures/certificates. Follow RELEASE_VALIDATION.md.
2. Approve commit(s), remote creation/publication and CI. Review secrets; retain
   source/image hashes. Require all matrix jobs green with exact counts/no skips
   and actual race proof. YAML syntax alone is not R-14 acceptance.
3. Approve disposable benchmark DB/seed/host/load. Retain10k/2k counts, environment,
   native exits, percentiles/errors and baseline/SSE comparisons. Never benchmark
   retained or production databases.
4. Review/pin images. Approve isolated production-topology rehearsal: Docker/Caddy
   checks, secret ownership, role grants/migrations, startup/shutdown and fresh HTTP
   flows. Owner-role DB tests do not certify restricted production-runtime grants.
5. Approve VPS/domain/DNS/firewall, secrets, volumes/backups, production bootstrap/
   migrations/catalog and launch. Verify TLS, cookie/CSRF/forwarding rejection,
   two-client SSE, ranking/lifecycle and actual mobile/keyboard. Record sanitized
   smoke evidence. Old browser manifests grant none of this.
6. Finish design export/load report; rehearse/record fresh demo accounts. Owner
   checks redaction/duration, approves publication and fills links for the same
   release revision.
7. Open public links unauthenticated, submit in organizer workspace before deadline
   and retain receipt/time. Prepared links are not delivery.

Remaining gates: unrun containers/native validation; current image/dependency
security review; actual role/migration rehearsal; backup restore; history-growing
polling cost; no current HTTPS/browser/mobile/keyboard certificate; no public CI/
load/deployment/video links. Parallel frontend flakes remain documented; CI uses
one worker. No full-catalog name search, email delivery, AI/ML ranking or production
reliability claim.


## Final freeze: next live actions, not executed

The final-freeze request authorizes only one local reviewed commit. Every DB,
service, remote, deployment, recording/publication and submission action below
still requires explicit owner approval for its stated scope. No live exit code
or successful artifact exists yet. Use the committed release candidate, a quiet
validation window, and no concurrent source edits. Do not execute historical
REALTIME.md's old-HEAD block after this freeze; use the source-bound wrapper below.
The complete97-file inventory is in BATCH_C.md; current checks are in PROGRESS.md.

PowerShell commands below run in I:\Merge\backend unless noted. After **each**
native command immediately capture `$rc=$LASTEXITCODE`; record `$rc` privately
beside its source-bound sanitized receipt. Require0 and stop before dependencies
on nonzero, interruption, skipped/missing/ambiguous/stale results. Never pipe or
transcribe credential prompts. Verify each new receipt offline with:

```powershell
.\.venv\Scripts\python.exe -m release_support.verify test-results/release/KIND-PRINTED_RECEIPT_ID.json
$rc=$LASTEXITCODE
if ($rc -ne 0) { throw 'Uncertified receipt; retain evidence and stop' }
```

Replace only the printed receipt filename. No cleanup, reset, destructive downgrade
or automatic retry is part of this runbook. Ambiguous COMMIT requires separately
approved read-only verification. No existing manifest is reused or modified.

### A. Exact0005 SSE acceptance

```powershell
.\.venv\Scripts\python.exe -m release_support.realtime_acceptance --confirm-merge-test
```

Target: actual127.0.0.1:5432, merge_test /merge_app /0005_invitations. Effects:
fresh retained fixture/domain/auth/history writes; one rollback schedule; no DDL,
deletion/reset or old-row modification. Approval required for this DB-write scope.
Success: native0, realtime4 collected/completed, skip0/fail0, complete invariant
checks, unchanged source. Artifact: release/realtime-*.json plus guarded/run-*.json.
Nonzero/incomplete: preserve all fixtures/reports, stop without rerunning. Exact
write counts/privacy/transport limits: RELEASE_VALIDATION.md section2 /REALTIME.md.

### B. Isolated0006 migration and profile acceptance

From repo root, then switch to backend:

```powershell
psql -X -h 127.0.0.1 -p 5432 -U postgres -d postgres -W -f scripts/provision_merge_profile_test.sql
Set-Location I:\Merge\backend
.\.venv\Scripts\python.exe -m release_support.migrations prepare --target profiles --confirm-target merge_profile_test
.\.venv\Scripts\python.exe -m release_support.migrations migrate --target profiles --confirm-target merge_profile_test
.\.venv\Scripts\python.exe -m release_support.migrations verify --target profiles --confirm-target merge_profile_test
.\.venv\Scripts\python.exe -m release_support.acceptance --confirm-profile-test
```

Apply the immediate native-exit check after each line. Target: NEW local
merge_profile_test /existing merge_app, exact0006; postgres only provisions the
new database. Effects: create-only DB/schema grants, empty-schema prepare through
0005, additive0006, fresh retained profile/domain/auth cases. No merge_test/dev
upgrade or deletion. Approval required separately for provisioning, DDL and cases.
Success: each native0,12 old-table preservation counts match, exact0006, profiles30
unique successful/completed cases with no skips. Artifacts: migration-*.json,
profiles-*.json, guarded report; private provisioning exit record. DDL failures
roll back; partial CREATE DATABASE cannot roll back as one unit: stop for owner
inspection without adopting/dropping the target. Full commands/contracts: section3.

### C. Dedicated seed, benchmark host and measured load

Approve new merge_bench /merge_bench_app at actual127.0.0.1:5432 only. Execute
RELEASE_VALIDATION.md section5 create-only provisioning and explicit
prepare/migrate/verify commands, checking each native exit. Then:

```powershell
.\.venv\Scripts\python.exe -m release_support.seed --confirm-merge-bench --seed 2026
.\.venv\Scripts\python.exe -m release_support.seed --confirm-merge-bench --seed 2026 --verify-only
# Separate terminal1, only after host approval:
.\.venv\Scripts\python.exe -m release_support.benchmark_host --confirm-merge-bench --seed 2026
# Terminal2: actual reviewed k6 installed; ignored environment disclosure completed:
.\.venv\Scripts\python.exe -m release_support.load --confirm-merge-bench --seed 2026 --sse-clients 0 --environment test-results/bench-environment.json
.\.venv\Scripts\python.exe -m release_support.load --confirm-merge-bench --seed 2026 --sse-clients 32 --environment test-results/bench-environment.json
```

Effects: new-only atomic10000-user/2000-team seed,5000 memberships; load creates
100 real sessions/run and reads board/SSE. No DELETE/TRUNCATE, retained/prod target
or public binding. Approval required for provision/seed, host and each load run.
Success: seed/verify native0/exact counts/digest;100 VUs/20s warmup/60s measurement,
p50/p95/p99/errors/throughput and actual hardware/version/history disclosure;
p95<200ms/error0/native0 for each load. Artifacts: migration/seed/load-*.json and
aggregate *.k6.json. Host is a foreground service, no test-pass exit signal; record
its launch/termination separately. Stop host with Ctrl+C; threshold99 or any
incomplete report is failure, never acceptance. No invented result/tuning claim.

### D. GitHub publication and CI

Approval required to create/select the actual public repository, publish this
commit and run Actions. Do not infer or invent an origin. From repo root, after
owner verifies the remote URL and all staged/committed content:

```powershell
git -c safe.directory=I:/Merge remote get-url origin
# If absent, separately approve: git remote add origin OWNER_APPROVED_HTTPS_REPOSITORY_URL
git -c safe.directory=I:/Merge push --set-upstream origin main
# Push triggers ci.yml. Select the actual run for the frozen commit, then:
gh run watch OWNER_VERIFIED_RUN_ID --exit-status
gh run download OWNER_VERIFIED_RUN_ID --dir backend/test-results/public-ci-OWNER_VERIFIED_RUN_ID
```

Targets: owner-approved public repo and GitHub-hosted ephemeral PostgreSQL16
containers only. Effects: public source/history and CI artifacts; fresh disposable
CI DBs, no retained DB. Native0 for push/watch/download plus all offline/four
revision jobs green; require exact suites/counts and authenticated50-caller race,
no skips/missing receipts. Preserve run URL/commit/job exits/sanitized artifacts.
These ID/URL placeholders must be supplied by owner; no remote is contacted here.
Any failed/missing/inconclusive job stops release. Do not relax guards or hide it.

### E. Production HTTPS rehearsal, then deployment

Approval required for provider/DNS/firewall, image pulls/builds/advisories, new
secret files, persistent volumes/bootstrap/DDL/catalog and launch. Use an isolated
rehearsal host first, then separately approved production. Exact Linux commands,
required variables and private file handling: PRODUCTION.md approval1 through3.
The fixed target is private postgres:5432/merge_prod, merge_migrator for DDL and
merge_runtime for API; only Caddy80/443 are published. Core ordered commands are:

```bash
(cd backend && .venv/bin/python -m app.production.check)
(cd backend && sudo .venv/bin/python -m app.production.prepare --confirm-new-secrets --origin "$MERGE_PROD_ORIGIN")
docker compose -f deploy/compose.json config --quiet
docker compose -f deploy/compose.json build api web
docker compose -f deploy/compose.json run --rm --no-deps --entrypoint caddy web validate --config /etc/caddy/config.json
docker compose -f deploy/compose.json up -d postgres
# Wait for PostgreSQL health before the explicit operations:
docker compose -f deploy/compose.json run --rm --no-deps bootstrap --confirm-new-merge-prod
docker compose -f deploy/compose.json run --rm --no-deps migrate prepare --confirm-merge-prod
docker compose -f deploy/compose.json run --rm --no-deps migrate migrate --confirm-merge-prod
docker compose -f deploy/compose.json run --rm --no-deps migrate verify --confirm-merge-prod
# Add only the separately approved catalog command from PRODUCTION.md.
docker compose -f deploy/compose.json up -d api
docker compose -f deploy/compose.json up -d web
```

Run under `set -euo pipefail`; independently record each native exit and sanitized
operation JSON/source/image digests in a private release record. Effects: new
secrets/roles/schema/catalog, persistent volumes/TLS certificates and public
service; no destructive cleanup. Success needs native0, actual healthy runtime
grants/exact0006 plus valid HTTPS/Secure cookie/CSRF/Origin/forwarding/two-client
SSE/ranking/lifecycle/mobile/keyboard smoke, backup/restore evidence. Native0 for
`up` alone is insufficient. On failure `docker compose -f deploy/compose.json stop web api`;
retain DB/volumes. First release has no known-good image; no downgrade/down -v.

### F. Demo and submission

After all required evidence exists, rehearse/record DEMO.md's4:50 script against
fresh approved demo accounts/hackathon at the verified HTTPS URL. Capture only
sanitized proof points, export/check one-page design pagination, attach the actual
load report and fill the link table above. Recording has no repository CLI/native
exit criterion: require playable<=5:00, correct revision/environment and no secrets.
Owner approval required for recording, public upload and organizer submission.
Verify all public links unauthenticated, submit before2026-11-15 23:59 IST and
retain actual organizer receipt/time. Portal submission likewise has no native
CLI exit code; success is the real receipt. Missing evidence/links or deadline
failure stops any claim that PS1 has been submitted or accepted.

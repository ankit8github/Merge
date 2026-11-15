# Documentation audit and local release review

Audit date: 15 November 2026. Starting HEAD: `bb60ab3dd764e63de6a2261e4f3924e3d78bda33`.
The owner authorized exactly one local commit after offline validation, named
`chore(deploy): prepare Render release and streamline docs`. Push/cloud/database
operations remain outside scope. The commit identity belongs in Git history, not
a self-referential document. [Current status](../PROGRESS.md) and [testing](../TESTING.md)
record actual results; [Render](../RENDER.md) is the current deployment runbook.

## Before and after

| Inventory | Before | After |
| --- | --- | --- |
| Public tracked/untracked Markdown | 50 | 46 |
| Standalone retired review documents | 8 | 0 (full content consolidated into one archive) |
| New archive pages | 0 | 4: engineering history, architecture history, progress history, this audit |
| Current architecture | 448 lines | Current design, with original full proposal preserved |
| Current progress | 8813 lines | Current evidence/gates, with full journal preserved |

Starting source candidates: 340. Final candidates: 336 (eight retired Markdown
paths, four new archive pages). All 290 non-Markdown source/configuration/test
paths are byte-identical to the starting tree. Every runtime, dependency,
migration, workflow, benchmark, seed, security and acceptance file remains.
No required source was archived or deleted. No PostgreSQL, startup, migration,
fixture cleanup, benchmark, cloud, billing or remote operation ran.

The Git inventory distinguishes 47 tracked and 3 pending public Markdown files
at the start. In addition, 180 ignored Markdown files were inventoried locally:
175 installed-dependency documents, one pytest cache README, and four historical
acceptance/review files. All are KEEP LOCAL; no private file was added to Git.
Ignored inventories, original document bytes and the starting evidence-hash map
are stored only in a new ignored local review directory. The 1044 baseline
ignored evidence files (including the audit pointer created at capture) are checked byte-for-byte; no receipt/hash was rewritten.

## Reference review and removal safety

All tracked/untracked source candidates were searched for complete document
paths and basenames, plus `.md` and `docs/` usage. This included Python/TypeScript,
frontend harnesses, CI workflows, test validators/runners, deployment/Docker COPY
inputs, migration tooling, seed/load tooling, README/indexes and submission/design
materials. No executable source reads or requires any retired Markdown path.
`/docs` in Caddy/FastAPI is the disabled API documentation route, not a file dependency.

Public documentation links and prose references were redirected to namespaced
archive sections. Local fragments and archive relative paths are validated.
Historical code/inline inventories intentionally retain their original dated
filenames; they are not active links or executable paths. No executable reference
required changing. A file with uncertain runtime/reproduction value was kept.

No document's content was discarded without a retained canonical purpose or
historical copy. The eight physical removals below (seven tracked reports and one previously
untracked Render handoff) are consolidation, not evidence destruction. Runtime/testing cannot depend on a removed Markdown file because the
source/reference audit found no executable consumer, all scripts/migrations stay
unchanged, and required offline suites/configuration checks are rerun.

### docs/BATCH_A.md

Dated profile/ranking/UX review; current contracts are RANKING, SCHEMA and FRONTEND. Full review is preserved in history.

Preserved at [engineering history](ENGINEERING_HISTORY.md#batch-a). References checked: `docs/ADMISSION.md`, `docs/BATCH_B.md`, `docs/BATCH_C.md`, `docs/FRONTEND.md`, `docs/INVITATIONS.md`, `docs/PROGRESS.md`, `docs/TEST_DATABASE.md`, `docs/archive/README.md`, `docs/archive/REPOSITORY_AUDIT.md`. No executable references.

### docs/BATCH_B.md

Dated CI/seed/load implementation review; RELEASE_VALIDATION and TESTING are canonical. Full failure/evidence details are preserved.

Preserved at [engineering history](ENGINEERING_HISTORY.md#batch-b). References checked: `docs/ARCHITECTURE.md`, `docs/BATCH_C.md`, `docs/DECISIONS.md`, `docs/PROGRESS.md`, `docs/archive/README.md`, `docs/archive/REPOSITORY_AUDIT.md`. No executable references.

### docs/BATCH_C.md

Superseded packaging inventory/release proposal; current Render and retained VPS runbooks own commands. Full source inventory remains historical.

Preserved at [engineering history](ENGINEERING_HISTORY.md#batch-c). References checked: `docs/DECISIONS.md`, `docs/PROGRESS.md`, `docs/SUBMISSION.md`, `docs/archive/README.md`, `docs/archive/REPOSITORY_AUDIT.md`. No executable references.

### docs/BATCH_D_RECOVERY.md

Dated recovery triage, not an active runbook. Consumed-campaign limits and diagnostic qualifications are retained in full.

Preserved at [engineering history](ENGINEERING_HISTORY.md#batch-d-recovery). References checked: `docs/BATCH_E_RELEASE.md`, `docs/INTEGRATED_HOST.md`, `docs/PROGRESS.md`, `docs/SUBMISSION.md`, `docs/TESTING.md`, `docs/archive/README.md`, `docs/archive/REPOSITORY_AUDIT.md`. No executable references.

### docs/BATCH_E_RELEASE.md

Old local-freeze/publication/VPS handoff duplicates current platform and submission guides. Dated commands and original scope remain archived.

Preserved at [engineering history](ENGINEERING_HISTORY.md#batch-e-release). References checked: `docs/DEMO.md`, `docs/PROGRESS.md`, `docs/SUBMISSION.md`, `docs/archive/README.md`, `docs/archive/REPOSITORY_AUDIT.md`. No executable references.

### docs/PRODUCT_AUDIT.md

Completed UI audit/review; current feature contracts and status are canonical. Original findings and results remain archived.

Preserved at [engineering history](ENGINEERING_HISTORY.md#product-audit). References checked: `docs/BATCH_E_RELEASE.md`, `docs/INTEGRATED_ACCEPTANCE.md`, `docs/INTEGRATED_HOST.md`, `docs/PROGRESS.md`, `docs/archive/README.md`, `docs/archive/REPOSITORY_AUDIT.md`. No executable references.

### docs/BROWSER_HOST_AUDIT.md

Historical guard/drain repair analysis; current harness contracts stay in BROWSER_ACCEPTANCE. Detailed failure analysis is preserved.

Preserved at [engineering history](ENGINEERING_HISTORY.md#browser-host-audit). References checked: `docs/BROWSER_ACCEPTANCE.md`, `docs/FRONTEND.md`, `docs/PROGRESS.md`, `docs/TEST_DATABASE.md`, `docs/archive/README.md`, `docs/archive/REPOSITORY_AUDIT.md`. No executable references.

### docs/RENDER_REVIEW.md

Temporary uncommitted handoff has a stale 37-path inventory and old proposed commit. Current audit/runbook replace it; original review is archived.

Preserved at [engineering history](ENGINEERING_HISTORY.md#render-preparation-review). References checked: `docs/PROGRESS.md`, `docs/README.md`, `docs/RENDER.md`, `docs/TESTING.md`. No executable references.

## Every starting Markdown document

Classifications describe this cleanup; KEEP permits safe cross-link/navigation edits.
The before hashes identify exact starting bytes, not new certification receipts.

| Before path | Classification / retained purpose | Original SHA-256 |
| --- | --- | --- |
| `AGENTS.md` | KEEP - Repository workflow and ownership rules. | `ed3a33606e6afe68ab94535d2a7f45e97869a92ac9f3dca08bb7d4fd0f788200` |
| `README.md` | KEEP - Public project homepage and current entry points. | `ba0b433e624e455595441d5f5d77fab423bf2a2d2e08132bbb30dc74519a48d3` |
| `docs/ADMISSION.md` | KEEP - Authorization, transaction/locking and race/fault reproduction for requests. | `2c124bd617f13114a0b89019ac7d35c8f59967c8ffbe02cb22cddb8fe4ce86dc` |
| `docs/ARCHITECTURE.md` | CONSOLIDATE - Current architecture rewritten; superseded full proposal preserved in archive/ARCHITECTURE_HISTORY.md. | `08461e1b9e19365c2ba59233ff2c2d7cd7814fec95c6c2a38f50d4babd30a623` |
| `docs/AUTH_SCHEMA.md` | KEEP - Credential/session database schema and guarded migration contract. | `4a2c250238ef7644b45878e5bb89e539a526a04a339969f21c159fc2359d7f85` |
| `docs/AUTH_THROTTLING.md` | KEEP - Durable throttle limits, privacy and trusted-client identity contract. | `3778eea2d6112c4f54fa30872d9b70e1227a4427047e514dcee52e44e40c35bd` |
| `docs/BATCH_A.md` | CONSOLIDATE / ARCHIVE - Dated profile/ranking/UX review; current contracts are RANKING, SCHEMA and FRONTEND. Full review is preserved in history. | `6b4f54ef12b79f5e6071198ce6519a6eb36b726fe63b4a50c836ae3b4c0ef633` |
| `docs/BATCH_B.md` | CONSOLIDATE / ARCHIVE - Dated CI/seed/load implementation review; RELEASE_VALIDATION and TESTING are canonical. Full failure/evidence details are preserved. | `95d36dabe234e5f7c4e30eb90a9424a868d16e82f430f588487e7174527414c0` |
| `docs/BATCH_C.md` | CONSOLIDATE / ARCHIVE - Superseded packaging inventory/release proposal; current Render and retained VPS runbooks own commands. Full source inventory remains historical. | `5c1b5c2d6cab6eb156627a81d4355cbb5a11bf5fb3a347f2037047af75fa6e30` |
| `docs/BATCH_D_RECOVERY.md` | CONSOLIDATE / ARCHIVE - Dated recovery triage, not an active runbook. Consumed-campaign limits and diagnostic qualifications are retained in full. | `3e594f7aed05651a09b7dc9bf5ff8a756b78b7f43055d1d1f118a14599076fae` |
| `docs/BATCH_E_RELEASE.md` | CONSOLIDATE / ARCHIVE - Old local-freeze/publication/VPS handoff duplicates current platform and submission guides. Dated commands and original scope remain archived. | `bb4c0560a0226ce9289560b9b0c0c05d71a9dcdfde4cac08ba0eb797bb3d3bd4` |
| `docs/BROWSER_ACCEPTANCE.md` | KEEP - Guarded browser harness scopes, budgets and historical restrictions. | `a4302b42a773b79d85ac9621a766f686b31c3f69cf10908a0a16ebe798bc8884` |
| `docs/BROWSER_HOST_AUDIT.md` | CONSOLIDATE / ARCHIVE - Historical guard/drain repair analysis; current harness contracts stay in BROWSER_ACCEPTANCE. Detailed failure analysis is preserved. | `98989c390d62e07b382ae6ee71ff0f28294f4485d9f844e01e3c4092a1b05192` |
| `docs/CREDENTIAL_SERVICES.md` | KEEP - Argon2 work bounds, registration/login transaction contract. | `2e8a0472a41f101aba6113636027bc2fd007041ca589edcf28ed49ef8545db60` |
| `docs/DECISIONS.md` | KEEP - Decision register and rationale; dated release-commit authorization clarified. | `d0c42f66b3a9c68f9f0c76fc4a43d4c0d968fdbf2369ca06cacaff1683aaf96a` |
| `docs/DEMO.md` | KEEP - Required <=5-minute demo instructions and privacy controls. | `47eb35a68232b068fc9421ba0014c25058621f5948996ba043d4c1e36f678592` |
| `docs/DEPLOYMENT.md` | CONSOLIDATE - Current Render index replaces copied VPS overview/execution blocks; full alternate runbooks retained. | `4c587498eaa88d3dd4f81e2759b362731a90707e6af49569fbc4f56d08b1d64e` |
| `docs/DESIGN_ONE_PAGE.md` | KEEP - Mandatory concise submission design; updated selected hosting/CI scope. | `66847b7e82e7973dd7f843b5286e18cc6b71c3058cfd48aeb0b8005d6b2399ae` |
| `docs/FRONTEND.md` | KEEP - Account/scope isolation, UI recovery and component contracts. | `0b5eec27a579722b9c404912d2411759df4c67f7209832f0a5ac6cc39f02a54e` |
| `docs/G1_ACCEPTANCE.md` | KEEP - Distinct authenticated 50-caller proof and provenance limits. | `a3dd43ca9887c205e2be829381455700ad7f57de72212e50021461be5d976e5e` |
| `docs/HTTP_AUTH.md` | KEEP - Cookie/Origin/CSRF and endpoint trust boundary. | `80e019d43953dccedf16876d2ff5391ddd7a3f054963c54a2f3a1d4b31ecfe90` |
| `docs/IDEMPOTENCY.md` | KEEP - Key ownership, request fingerprints and replay semantics. | `c874621caa7a442a9077446e5eeb27d7c193cd5478b352567b4905a743ebaaf5` |
| `docs/INTEGRATED_ACCEPTANCE.md` | KEEP - Distinct profile/browser preparation, source/receipt restrictions. | `edeb6333bdae8806317c564a7240a9145c8434fd320ac9d8ab7784b63a2b3b48` |
| `docs/INTEGRATED_HOST.md` | KEEP - Independent browser host/observer/certification and campaign safety. | `79023faa9810eabf31523c7ca99a57465259dd86de6c6012f02a8181b326bdfb` |
| `docs/INVITATIONS.md` | KEEP - Recipient binding, expiry, replay and admission concurrency contract. | `6031f4fb8de5d4fabb2694250a55f1c5b4903a3d72b096d46c5db518be24a440` |
| `docs/LIFECYCLE.md` | KEEP - Departure/removal/succession/deletion invariants and acceptance scope. | `d27eca2d9eb8f52b5ad9be4981fbbcc76816707f9ca182f597bde950c2fe130d` |
| `docs/PRODUCTION.md` | KEEP - Retained separate VPS runbook; production helpers are Render dependencies. | `f234917a86e1aea247a64722ddcf890e53f59a0d09d1ee12d9229f9a1da0dddb` |
| `docs/PRODUCT_AUDIT.md` | CONSOLIDATE / ARCHIVE - Completed UI audit/review; current feature contracts and status are canonical. Original findings and results remain archived. | `4a425d0de3f00d0d56949d9bc06162c7f6ea20f17d253815aceab46c54bb50e6` |
| `docs/PROGRESS.md` | CONSOLIDATE - Current status kept concise; all earlier journal entries preserved in archive/PROGRESS_HISTORY.md. | `1907117c938dab1d4df07c05e11557e511c5517245a1a3cf3273b25dfbc023be` |
| `docs/RAILWAY.md` | KEEP - Retained alternate runbook; source helpers are Render dependencies; clearly superseded as target. | `fe7c89577eb1fb65ab4d93f27a3c8643eb9518b8294f50cac1a1ed9a642b45c8` |
| `docs/RANKING.md` | KEEP - Deterministic formula, privacy, snapshot cursor and candidate contract. | `9209efd433979546fdc3a2a2fddbd235929843e941ad54867dfaeb3ac79e6ec0` |
| `docs/README.md` | KEEP - Canonical public documentation navigation. | `6602177174c1db3ad2c1fb7fce8f0b120031284e8fbe2a7b083f8be55ac45b64` |
| `docs/READ_API.md` | KEEP - Discovery access, scope, pagination and errors. | `4920e5c9ddb0edf16d62a39a5ccfcf186f3f07e344b42a42ae95a5b39f6b3e22` |
| `docs/REALTIME.md` | KEEP - SSE authorization, invalidation, leases and reconnect bounds. | `2d6c1ea068788442a6a317a8ced1f756910b047ae756b3095a7a93b05d99b0bc` |
| `docs/RELEASE_VALIDATION.md` | KEEP - Explicit isolated migrations, acceptance, seed/load and receipt procedure. | `dfce149e4522ee7db96ee35b06b5fc9272ff1619efad6784d8ca56360c3bde8b` |
| `docs/RENDER.md` | KEEP - Canonical selected Render setup/runtime/rollback runbook; duplicate review inventory removed. | `47d30e7af893f021b12b8a9196f5b369914d399dc08d5eb37719bb8608319d7d` |
| `docs/RENDER_REVIEW.md` | CONSOLIDATE / ARCHIVE - Temporary uncommitted handoff has a stale 37-path inventory and old proposed commit. Current audit/runbook replace it; original review is archived. | `58bc051cba9200e741a0fad92d2cbb84772d42eb99566ab1689e6ffb346f3b9a` |
| `docs/REQUIREMENTS.md` | KEEP - Organizer requirements and acceptance targets; no requirement relaxed. | `c86d93eef6b88612b6a3a6ac346633405bb2cac79f13c5cb0482136500b96b3d` |
| `docs/SCHEMA.md` | KEEP - Database constraints, functions and version-specific schema contract. | `757ed3fb1f1cd9fe9ca40eb4b1317b9f2579f79b8c136e5088396f770afe8963` |
| `docs/SESSION_SERVICES.md` | KEEP - Session/CSRF/expiry/revocation interfaces and failure behavior. | `e35680c5795f3e123983a81092da7d0548d6d2810aa32cfaba7be4cc06e32987` |
| `docs/SETUP.md` | KEEP - Reproducible local provisioning/migration/startup steps. | `79f7227caf7ecaa5dd7572590eafc7ff1e0ac084f41bce0b8f96898ef44c3717` |
| `docs/SUBMISSION.md` | CONSOLIDATE - Current artifact checklist replaces stale freeze/VPS command duplicates; detailed procedures stay in runbooks. | `e75ba2487dce2df3f973357896a3c4caf024b7ede9b10e8e3133fab4a6ae649b` |
| `docs/TEAM_API.md` | KEEP - Authenticated team creation wire/error/retry contract. | `1b14177ae7781e5e6f53915427fd46977fc98832d371aa71369d5c2faca005b0` |
| `docs/TEAM_MUTATIONS.md` | KEEP - Atomic membership/idempotency/audit/outbox contract. | `4ed84e63a9af25ed8ad32c09859c1f4f97e2a7e349a325d6ef3c665e11f5b197` |
| `docs/TEAM_SERVICES.md` | KEEP - Transaction ownership, service interfaces and live failure cases. | `60ac1208590d3cbcae4249038d22ab62eb68358d77558da5f44496f90a6a809b` |
| `docs/TESTING.md` | CONSOLIDATE - Current commands/results canonical; prior full guide/tables retained once in engineering history. | `bf67ccb4219ef01a0900a883ed5f8bd50b6eba358b97207b42d10d8318da67af` |
| `docs/TEST_DATABASE.md` | KEEP - Exact target/revision guards and retained-fixture safeguards. | `428b43eba5b4a011f1ff3833152c9a3518514bf64bb150092d269eaee34f5175` |
| `docs/TRANSACTION_RETRY.md` | KEEP - Retry budgets and uncertain COMMIT reconciliation. | `bc70509c22ccb5cb2fe9d61a511099581abe8fab185c45d3df334cdfdd6d61b0` |
| `docs/archive/README.md` | KEEP - Labeled history navigation. | `3e3db7c8abb130cb31daf4fd6067a86ee819430eaf7ef3a523a8874ec56cbd39` |
| `docs/archive/REPOSITORY_AUDIT.md` | KEEP - Prior dated file audit retained byte-for-byte; not current inventory. | `1c4900f84095e2784a910f98a7e2242b6208c9b4b36350b05e7415273283e944` |

## Exact retained public Markdown inventory after cleanup

- `AGENTS.md`
- `README.md`
- `docs/ADMISSION.md`
- `docs/ARCHITECTURE.md`
- `docs/AUTH_SCHEMA.md`
- `docs/AUTH_THROTTLING.md`
- `docs/BROWSER_ACCEPTANCE.md`
- `docs/CREDENTIAL_SERVICES.md`
- `docs/DECISIONS.md`
- `docs/DEMO.md`
- `docs/DEPLOYMENT.md`
- `docs/DESIGN_ONE_PAGE.md`
- `docs/FRONTEND.md`
- `docs/G1_ACCEPTANCE.md`
- `docs/HTTP_AUTH.md`
- `docs/IDEMPOTENCY.md`
- `docs/INTEGRATED_ACCEPTANCE.md`
- `docs/INTEGRATED_HOST.md`
- `docs/INVITATIONS.md`
- `docs/LIFECYCLE.md`
- `docs/PRODUCTION.md`
- `docs/PROGRESS.md`
- `docs/RAILWAY.md`
- `docs/RANKING.md`
- `docs/README.md`
- `docs/READ_API.md`
- `docs/REALTIME.md`
- `docs/RELEASE_VALIDATION.md`
- `docs/RENDER.md`
- `docs/REQUIREMENTS.md`
- `docs/SCHEMA.md`
- `docs/SESSION_SERVICES.md`
- `docs/SETUP.md`
- `docs/SUBMISSION.md`
- `docs/TEAM_API.md`
- `docs/TEAM_MUTATIONS.md`
- `docs/TEAM_SERVICES.md`
- `docs/TESTING.md`
- `docs/TEST_DATABASE.md`
- `docs/TRANSACTION_RETRY.md`
- `docs/archive/ARCHITECTURE_HISTORY.md`
- `docs/archive/DOCUMENTATION_AUDIT.md`
- `docs/archive/ENGINEERING_HISTORY.md`
- `docs/archive/PROGRESS_HISTORY.md`
- `docs/archive/README.md`
- `docs/archive/REPOSITORY_AUDIT.md`

## Render adapter review

Complete pending adapter reviewed: nine Render modules, its Alembic environment,
93-case offline test module, Dockerfile, Caddy JSON and root runtime Blueprint.
The existing Railway and production helpers it imports are retained. No adapter
source/configuration changed in this documentation cleanup.

- Non-root multi-stage Docker packages locked React assets and Python dependencies;
  no build-time SQL, Node runtime server, build secrets or extra public port.
- Caddy binds assigned PORT (10000 default), exact hostname and HTTPS/CF identity;
  static assets and unstripped /auth, /api routing share one origin. Private upstream
  is 127.0.0.1:8000. SSE flush -1/no compression/75-second proxy lease remains.
- One loopback worker, proxy middleware disabled, pool 2/no overflow; no relaxed
  session/Origin/CSRF/hash/security configuration. Caddy receives no DB secrets.
- Private DNS-pinned TLS PG17 / merge_prod / restricted merge_runtime; exact0006,
  role/grant/table/readiness checks preserved. External DB allowlist stays empty.
- Explicit fresh setup is separate from normal startup, uses reviewed SHA/attempt,
  durable claim, advisory lock and owned DDL transaction. No adoption/reset/drop or
  HTTP mutation endpoint. Failed claims block retries; success must be read from
  setup JSON, not a green liveness badge. Normal startup never migrates.
- Supervisor signals Caddy first and then the API, with bounded shared shutdown;
  this is not a guarantee that Caddy finishes draining before API shutdown starts.
  The runbook wording was corrected without changing the implementation.
- CI PG17, four exact revisions, authenticated APIs, 50-caller race and strict
  receipt/native-result checks remain byte-identical. No hosted run was triggered.

Native Docker/Caddy is unavailable. Offline validation cannot establish native
image/Caddy compatibility, Linux peak RSS/512 MB fit/0.1-CPU startup, managed owner
privileges, Render Blueprint acceptance, actual header overwrite, HTTPS/SSE/browser
behavior, backup or required load performance. Render deployment is not claimed.

## Complete release scope relative to published HEAD

The commit includes the already pending Railway/Render adapters plus this
reference-checked documentation cleanup. No unrelated application changes.
The exact candidate delta is recorded below after final review.

- `README.md`
- `backend/app/railway/__init__.py`
- `backend/app/railway/api.py`
- `backend/app/railway/application.py`
- `backend/app/railway/check.py`
- `backend/app/railway/config.py`
- `backend/app/railway/database.py`
- `backend/app/railway/operations.py`
- `backend/app/railway/serve.py`
- `backend/app/render/__init__.py`
- `backend/app/render/api.py`
- `backend/app/render/application.py`
- `backend/app/render/check.py`
- `backend/app/render/config.py`
- `backend/app/render/database.py`
- `backend/app/render/initialization.py`
- `backend/app/render/serve.py`
- `backend/app/render/setup.py`
- `backend/railway_alembic/env.py`
- `backend/render_alembic/env.py`
- `backend/tests/test_railway.py`
- `backend/tests/test_render.py`
- `deploy/Dockerfile.railway`
- `deploy/Dockerfile.render`
- `deploy/railway/caddy.template.json`
- `deploy/railway/settings.json`
- `deploy/render/caddy.template.json`
- `docs/ADMISSION.md`
- `docs/ARCHITECTURE.md`
- `docs/BATCH_A.md`
- `docs/BATCH_B.md`
- `docs/BATCH_C.md`
- `docs/BATCH_D_RECOVERY.md`
- `docs/BATCH_E_RELEASE.md`
- `docs/BROWSER_ACCEPTANCE.md`
- `docs/BROWSER_HOST_AUDIT.md`
- `docs/DECISIONS.md`
- `docs/DEMO.md`
- `docs/DEPLOYMENT.md`
- `docs/DESIGN_ONE_PAGE.md`
- `docs/FRONTEND.md`
- `docs/INTEGRATED_HOST.md`
- `docs/INVITATIONS.md`
- `docs/PRODUCTION.md`
- `docs/PRODUCT_AUDIT.md`
- `docs/PROGRESS.md`
- `docs/RAILWAY.md`
- `docs/README.md`
- `docs/RENDER.md`
- `docs/SUBMISSION.md`
- `docs/TESTING.md`
- `docs/TEST_DATABASE.md`
- `docs/archive/ARCHITECTURE_HISTORY.md`
- `docs/archive/DOCUMENTATION_AUDIT.md`
- `docs/archive/ENGINEERING_HISTORY.md`
- `docs/archive/PROGRESS_HISTORY.md`
- `docs/archive/README.md`
- `render.yaml`

## Publication and owner explanation

After the local commit, stop. Next: owner reviews its exact SHA/scope and separately
approves `git push origin main`; require a new successful Actions run at that SHA.
Only after separate cloud approval follow the Render runbook's private PG17,
explicit setup deployment, JSON success review and normal-runtime switch. No cloud
resource, migration or deployment happens as a side effect of this commit.

The public guides describe current behavior; the archive preserves why earlier
choices and evidence had narrower scopes. Removing an old review path is safe only
because all active references resolve to its retained history/current contract.
Owner exercise: follow the archived Batch D link from testing, then locate the
current integrated-host guard. Explain why an old consumed campaign cannot be
restarted or recertified. No service or database access is needed.

## Exact retained non-Markdown source inventory

All 290 paths below remain byte-identical to the start of this review.
Some are already-pending adapter additions relative to published HEAD; they are
covered by the release commit and the offline suites, not by old hosted CI.

<details>
<summary>All retained runtime, test, tooling and configuration paths</summary>

- `.dockerignore`
- `.env.example`
- `.github/workflows/ci.yml`
- `.gitignore`
- `.vscode/extensions.json`
- `acceptance/integrated-campaign.json`
- `backend/admission_tests/conftest.py`
- `backend/admission_tests/test_admission.py`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/0001_baseline.py`
- `backend/alembic/versions/0002_domain.py`
- `backend/alembic/versions/0003_auth.py`
- `backend/alembic/versions/0004_admission.py`
- `backend/alembic/versions/0005_invitations.py`
- `backend/alembic/versions/0006_profiles.py`
- `backend/app/__init__.py`
- `backend/app/admission_api.py`
- `backend/app/auth.py`
- `backend/app/core/__init__.py`
- `backend/app/core/config.py`
- `backend/app/db/__init__.py`
- `backend/app/db/base.py`
- `backend/app/db/session.py`
- `backend/app/invitation_api.py`
- `backend/app/lifecycle_api.py`
- `backend/app/main.py`
- `backend/app/models/__init__.py`
- `backend/app/models/admission.py`
- `backend/app/models/auth.py`
- `backend/app/models/domain.py`
- `backend/app/models/invitations.py`
- `backend/app/models/profiles.py`
- `backend/app/production/__init__.py`
- `backend/app/production/application.py`
- `backend/app/production/bootstrap.py`
- `backend/app/production/check.py`
- `backend/app/production/config.py`
- `backend/app/production/database.py`
- `backend/app/production/grants.py`
- `backend/app/production/migrate.py`
- `backend/app/production/prepare.py`
- `backend/app/production/serve.py`
- `backend/app/profile_api.py`
- `backend/app/profile_models.py`
- `backend/app/railway/__init__.py`
- `backend/app/railway/api.py`
- `backend/app/railway/application.py`
- `backend/app/railway/check.py`
- `backend/app/railway/config.py`
- `backend/app/railway/database.py`
- `backend/app/railway/operations.py`
- `backend/app/railway/serve.py`
- `backend/app/read_api.py`
- `backend/app/read_models.py`
- `backend/app/realtime_api.py`
- `backend/app/render/__init__.py`
- `backend/app/render/api.py`
- `backend/app/render/application.py`
- `backend/app/render/check.py`
- `backend/app/render/config.py`
- `backend/app/render/database.py`
- `backend/app/render/initialization.py`
- `backend/app/render/serve.py`
- `backend/app/render/setup.py`
- `backend/app/security/__init__.py`
- `backend/app/security/auth_policy.py`
- `backend/app/security/client_identity.py`
- `backend/app/security/passwords.py`
- `backend/app/serve.py`
- `backend/app/services/__init__.py`
- `backend/app/services/admission.py`
- `backend/app/services/credential_errors.py`
- `backend/app/services/credentials.py`
- `backend/app/services/errors.py`
- `backend/app/services/idempotency.py`
- `backend/app/services/invitations.py`
- `backend/app/services/lifecycle.py`
- `backend/app/services/matching.py`
- `backend/app/services/profiles.py`
- `backend/app/services/realtime.py`
- `backend/app/services/session_errors.py`
- `backend/app/services/sessions.py`
- `backend/app/services/team_mutations.py`
- `backend/app/services/team_reads.py`
- `backend/app/services/teams.py`
- `backend/app/services/throttling.py`
- `backend/app/services/transaction_retry.py`
- `backend/app/team_api.py`
- `backend/auth_api_tests/conftest.py`
- `backend/auth_api_tests/test_auth_api.py`
- `backend/auth_schema_tests/conftest.py`
- `backend/auth_schema_tests/test_auth_schema.py`
- `backend/concurrency_tests/conftest.py`
- `backend/concurrency_tests/test_adversarial.py`
- `backend/credential_tests/conftest.py`
- `backend/credential_tests/test_credentials.py`
- `backend/idempotency_tests/conftest.py`
- `backend/idempotency_tests/test_idempotency.py`
- `backend/invitation_tests/conftest.py`
- `backend/invitation_tests/test_invitations.py`
- `backend/lifecycle_tests/conftest.py`
- `backend/lifecycle_tests/test_lifecycle.py`
- `backend/production_alembic/env.py`
- `backend/profile_tests/conftest.py`
- `backend/profile_tests/test_profiles.py`
- `backend/pyproject.toml`
- `backend/railway_alembic/env.py`
- `backend/read_api_tests/conftest.py`
- `backend/read_api_tests/test_reads.py`
- `backend/realtime_tests/conftest.py`
- `backend/realtime_tests/test_realtime.py`
- `backend/release_alembic/env.py`
- `backend/release_support/__init__.py`
- `backend/release_support/acceptance.py`
- `backend/release_support/benchmark_host.py`
- `backend/release_support/ci.py`
- `backend/release_support/evidence.py`
- `backend/release_support/integrated_certify.py`
- `backend/release_support/integrated_diagnostics.py`
- `backend/release_support/integrated_host.py`
- `backend/release_support/integrated_ledger.py`
- `backend/release_support/integrated_observer.py`
- `backend/release_support/integrated_plan.py`
- `backend/release_support/integrated_run.py`
- `backend/release_support/load.py`
- `backend/release_support/migrations.py`
- `backend/release_support/profile_inspection.py`
- `backend/release_support/profile_inspection_capture.py`
- `backend/release_support/realtime_acceptance.py`
- `backend/release_support/seed.py`
- `backend/release_support/targets.py`
- `backend/release_support/verify.py`
- `backend/render_alembic/env.py`
- `backend/requirements.lock`
- `backend/retry_tests/conftest.py`
- `backend/retry_tests/test_retry.py`
- `backend/service_tests/conftest.py`
- `backend/service_tests/test_teams.py`
- `backend/session_tests/conftest.py`
- `backend/session_tests/test_sessions.py`
- `backend/team_api_tests/conftest.py`
- `backend/team_api_tests/test_team_creation.py`
- `backend/team_mutation_tests/conftest.py`
- `backend/team_mutation_tests/test_composition.py`
- `backend/test_alembic/env.py`
- `backend/test_support/__init__.py`
- `backend/test_support/browser.py`
- `backend/test_support/browser_full.py`
- `backend/test_support/browser_full_scope.py`
- `backend/test_support/browser_full_state.py`
- `backend/test_support/browser_state.py`
- `backend/test_support/concurrency.py`
- `backend/test_support/database.py`
- `backend/test_support/diagnostics.py`
- `backend/test_support/invitation_race.py`
- `backend/test_support/races.py`
- `backend/test_support/revisions.py`
- `backend/tests/test_admission.py`
- `backend/tests/test_admission_api.py`
- `backend/tests/test_admission_commit_fault.py`
- `backend/tests/test_admission_readiness.py`
- `backend/tests/test_auth_http.py`
- `backend/tests/test_auth_schema_support.py`
- `backend/tests/test_auth_throttle_http.py`
- `backend/tests/test_browser_full_harness.py`
- `backend/tests/test_browser_harness.py`
- `backend/tests/test_ci_configuration.py`
- `backend/tests/test_client_identity.py`
- `backend/tests/test_concurrency_harness.py`
- `backend/tests/test_config.py`
- `backend/tests/test_credentials.py`
- `backend/tests/test_db_smoke.py`
- `backend/tests/test_domain_schema.py`
- `backend/tests/test_health.py`
- `backend/tests/test_idempotency.py`
- `backend/tests/test_integrated_diagnostics.py`
- `backend/tests/test_integrated_evidence.py`
- `backend/tests/test_integrated_host.py`
- `backend/tests/test_integrated_plan.py`
- `backend/tests/test_invitation_api.py`
- `backend/tests/test_invitation_readiness.py`
- `backend/tests/test_invitations.py`
- `backend/tests/test_lifecycle.py`
- `backend/tests/test_lifecycle_acceptance_review.py`
- `backend/tests/test_lifecycle_api.py`
- `backend/tests/test_lifecycle_readiness.py`
- `backend/tests/test_local_env_helper.py`
- `backend/tests/test_passwords.py`
- `backend/tests/test_product_labels.py`
- `backend/tests/test_production.py`
- `backend/tests/test_profile_inspection_auth.py`
- `backend/tests/test_profile_inspection_capture.py`
- `backend/tests/test_profiles_matching.py`
- `backend/tests/test_railway.py`
- `backend/tests/test_read_api.py`
- `backend/tests/test_realtime.py`
- `backend/tests/test_realtime_harness.py`
- `backend/tests/test_recovery_inspection_safety.py`
- `backend/tests/test_release_support.py`
- `backend/tests/test_render.py`
- `backend/tests/test_runner_diagnostics.py`
- `backend/tests/test_sessions.py`
- `backend/tests/test_team_api.py`
- `backend/tests/test_team_mutations.py`
- `backend/tests/test_team_reads.py`
- `backend/tests/test_team_services.py`
- `backend/tests/test_test_database_diagnostics.py`
- `backend/tests/test_test_database_safety.py`
- `backend/tests/test_throttling.py`
- `backend/tests/test_transaction_retry.py`
- `backend/throttle_tests/conftest.py`
- `backend/throttle_tests/test_throttling.py`
- `deploy/Dockerfile.api`
- `deploy/Dockerfile.railway`
- `deploy/Dockerfile.render`
- `deploy/Dockerfile.web`
- `deploy/caddy.template.json`
- `deploy/compose.json`
- `deploy/railway/caddy.template.json`
- `deploy/railway/settings.json`
- `deploy/render/caddy.template.json`
- `frontend/index.html`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/src/Admission.test.tsx`
- `frontend/src/AdmissionApi.test.ts`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/BatchCompatibility.test.tsx`
- `frontend/src/CreateTeam.test.tsx`
- `frontend/src/DiscoveryNavigation.test.tsx`
- `frontend/src/HackathonLookup.test.tsx`
- `frontend/src/InvitationApi.test.ts`
- `frontend/src/Invitations.test.tsx`
- `frontend/src/Journeys.test.tsx`
- `frontend/src/Lifecycle.test.tsx`
- `frontend/src/ProductAudit.test.tsx`
- `frontend/src/ProfilesRanking.test.tsx`
- `frontend/src/Realtime.test.tsx`
- `frontend/src/api.test.ts`
- `frontend/src/api.ts`
- `frontend/src/components/Admission.tsx`
- `frontend/src/components/AuthForm.tsx`
- `frontend/src/components/CreateTeam.tsx`
- `frontend/src/components/Discovery.tsx`
- `frontend/src/components/Feedback.tsx`
- `frontend/src/components/HackathonLookup.tsx`
- `frontend/src/components/HealthStatus.tsx`
- `frontend/src/components/Invitations.tsx`
- `frontend/src/components/Lifecycle.tsx`
- `frontend/src/components/Profile.tsx`
- `frontend/src/components/Rankings.tsx`
- `frontend/src/hooks/useAdmission.ts`
- `frontend/src/hooks/useDiscoveryNavigation.ts`
- `frontend/src/hooks/useInvitations.ts`
- `frontend/src/hooks/useLifecycle.ts`
- `frontend/src/hooks/useRead.ts`
- `frontend/src/hooks/useRealtime.ts`
- `frontend/src/hooks/useSession.ts`
- `frontend/src/hooks/useTeamCreation.ts`
- `frontend/src/hooks/useWorkspaceSignal.ts`
- `frontend/src/main.tsx`
- `frontend/src/style.css`
- `frontend/src/test/fixtures.ts`
- `frontend/src/test/navigationAssertions.ts`
- `frontend/src/test/setup.ts`
- `frontend/test_support/browserFaults.js`
- `frontend/test_support/browserFaults.test.js`
- `frontend/test_support/integratedCampaign.js`
- `frontend/test_support/integratedCampaign.test.js`
- `frontend/test_support/integratedEvidence.mjs`
- `frontend/test_support/integratedEvidence.test.js`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `load/board.js`
- `load/environment.example.json`
- `render.yaml`
- `scripts/check_local_http.py`
- `scripts/configure_backend_env.py`
- `scripts/inspect_merge_postgres.sql`
- `scripts/inspect_merge_profile_0005.ps1`
- `scripts/inspect_merge_recovery.sql`
- `scripts/inspect_merge_test.sql`
- `scripts/inspect_merge_test_recovery.sql`
- `scripts/provision_merge_bench.sql`
- `scripts/provision_merge_postgres.sql`
- `scripts/provision_merge_profile_test.sql`
- `scripts/provision_merge_test.sql`

</details>

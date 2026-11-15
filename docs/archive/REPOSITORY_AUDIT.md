# Repository audit - 15 November 2026

Scope: all **303 tracked baseline paths**, read as text and classified below, plus
this task's new guides/tests. Baseline commit:
`0d4c536cca83b42f2f572c429eb783e02d9885ac`. No application behavior, dependencies,
migrations, security guards, acceptance harnesses or deployment assets changed.

## Cleanup decision

**Retained: 303 original paths. Physically archived: 0. Removed: 0.** Seven historical
review reports are grouped through the [archive catalog](README.md), with their
original bytes/paths retained. The progress journal and component histories also
remain available. This avoids changing historical evidence or breaking source-bound
reproduction references. No tracked temporary/generated file was proven obsolete;
uncertain or useful files were kept. There are no proposed removals to justify.

Public documentation is consolidated through the homepage and focused setup,
testing/deployment guides. Detailed contracts remain useful for owner understanding,
security review, exact migration targets and fixture safety. The architecture now
separates the current overview from its original blueprint; no design changed.

## Reference review

The audit read every tracked file and checked application import paths, pytest's
default `tests` discovery and explicit guarded suite selection, frontend imports
and build configuration, workflow jobs, provisioning/migration tools, Docker COPY
inputs, browser campaign/harness paths, README and Markdown links. Executable
references to the workflow remain valid because it retains its JSON/YAML subset.
All six migration files and separate local/test/release/production Alembic
environments are retained. Required design/demo/submission artifacts remain.

No Markdown file links were broken at baseline. New guides link to existing
contracts rather than duplicating their operation commands. Plain historical
path mentions are provenance references, not executable link targets. New offline
checks pin service health arguments, PostgreSQL 17, all four revisions, authenticated
suites, the actual 50-caller test, namespace execution and strict receipt validation.
Full suites/build and final reference/preservation results are in [TESTING.md](../TESTING.md).

## Preserved local evidence

Before edits, a new ignored baseline captured hashes of **958 existing evidence
files** under backend/frontend test-results and untracked acceptance artifacts.
No original report, fixture, manifest, receipt or database was edited or deleted.
New logs/hashes are written only to a new ignored repo-polish directory. Existing
Git and Docker ignores already exclude credentials, test outputs, builds and
private deployment inputs; no ignore change was needed. Final byte comparison
is recorded in the testing guide. No private diagnostic data is copied here.

## CI review and remaining risks

The health value is exactly the requested four equals-form arguments. JSON string
encoding preserves the existing dependency-free validators and supplies the same
value as YAML's folded scalar. The service image changes from PostgreSQL 16 to 17.
Only these two workflow values change. Existing `release_support.ci` behavior and
strict result verification remain intact. See [network/credential review](../TESTING.md).

No remote call or rerun occurred. A new owner-approved push must still demonstrate
container initialization, hosted namespace execution and real PostgreSQL suites.
Offline checks cannot certify those steps. Native Docker/Caddy validation, browser,
HTTPS and measured load are also outstanding.

## Suggested GitHub presentation (not applied)

Description: "Merge is a concurrency-safe hackathon team formation platform with
explainable teammate matching and realtime collaboration updates."

Topics: `hackathon`, `team-formation`, `fastapi`, `react`, `postgresql`, `typescript`,
`server-sent-events`.

No repository settings, topics or metadata were modified remotely. No license file
exists in the tracked inventory; the homepage introduces no licensing terms.

## Full retained inventory

Every baseline path below is KEEP. "History catalog" indicates archival navigation,
not a move or deletion. Runtime/tests/tooling are preserved regardless of names.

| Path | Classification and reason |
| --- | --- |
| `.dockerignore` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `.env.example` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `.github/workflows/ci.yml` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `.gitignore` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `.vscode/extensions.json` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `AGENTS.md` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `README.md` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `acceptance/integrated-campaign.json` | KEEP - referenced browser campaign contract |
| `backend/admission_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/admission_tests/test_admission.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/alembic.ini` | KEEP - migration graph or guarded migration environment |
| `backend/alembic/env.py` | KEEP - migration graph or guarded migration environment |
| `backend/alembic/script.py.mako` | KEEP - migration graph or guarded migration environment |
| `backend/alembic/versions/0001_baseline.py` | KEEP - migration graph or guarded migration environment |
| `backend/alembic/versions/0002_domain.py` | KEEP - migration graph or guarded migration environment |
| `backend/alembic/versions/0003_auth.py` | KEEP - migration graph or guarded migration environment |
| `backend/alembic/versions/0004_admission.py` | KEEP - migration graph or guarded migration environment |
| `backend/alembic/versions/0005_invitations.py` | KEEP - migration graph or guarded migration environment |
| `backend/alembic/versions/0006_profiles.py` | KEEP - migration graph or guarded migration environment |
| `backend/app/__init__.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/admission_api.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/auth.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/core/__init__.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/core/config.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/db/__init__.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/db/base.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/db/session.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/invitation_api.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/lifecycle_api.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/main.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/models/__init__.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/models/admission.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/models/auth.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/models/domain.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/models/invitations.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/models/profiles.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/production/__init__.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/production/application.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/production/bootstrap.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/production/check.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/production/config.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/production/database.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/production/grants.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/production/migrate.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/production/prepare.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/production/serve.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/profile_api.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/profile_models.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/read_api.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/read_models.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/realtime_api.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/security/__init__.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/security/auth_policy.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/security/client_identity.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/security/passwords.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/serve.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/__init__.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/admission.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/credential_errors.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/credentials.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/errors.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/idempotency.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/invitations.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/lifecycle.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/matching.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/profiles.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/realtime.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/session_errors.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/sessions.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/team_mutations.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/team_reads.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/teams.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/throttling.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/services/transaction_retry.py` | KEEP - runtime/API/security/domain/production source |
| `backend/app/team_api.py` | KEEP - runtime/API/security/domain/production source |
| `backend/auth_api_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/auth_api_tests/test_auth_api.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/auth_schema_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/auth_schema_tests/test_auth_schema.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/concurrency_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/concurrency_tests/test_adversarial.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/credential_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/credential_tests/test_credentials.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/idempotency_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/idempotency_tests/test_idempotency.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/invitation_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/invitation_tests/test_invitations.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/lifecycle_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/lifecycle_tests/test_lifecycle.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/production_alembic/env.py` | KEEP - migration graph or guarded migration environment |
| `backend/profile_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/profile_tests/test_profiles.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/pyproject.toml` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `backend/read_api_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/read_api_tests/test_reads.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/realtime_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/realtime_tests/test_realtime.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/release_alembic/env.py` | KEEP - migration graph or guarded migration environment |
| `backend/release_support/__init__.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/acceptance.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/benchmark_host.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/ci.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/evidence.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/integrated_certify.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/integrated_diagnostics.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/integrated_host.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/integrated_ledger.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/integrated_observer.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/integrated_plan.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/integrated_run.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/load.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/migrations.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/profile_inspection.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/profile_inspection_capture.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/realtime_acceptance.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/seed.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/targets.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/release_support/verify.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/requirements.lock` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `backend/retry_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/retry_tests/test_retry.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/service_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/service_tests/test_teams.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/session_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/session_tests/test_sessions.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/team_api_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/team_api_tests/test_team_creation.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/team_mutation_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/team_mutation_tests/test_composition.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/test_alembic/env.py` | KEEP - migration graph or guarded migration environment |
| `backend/test_support/__init__.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/test_support/browser.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/test_support/browser_full.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/test_support/browser_full_scope.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/test_support/browser_full_state.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/test_support/browser_state.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/test_support/concurrency.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/test_support/database.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/test_support/diagnostics.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/test_support/invitation_race.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/test_support/races.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/test_support/revisions.py` | KEEP - test guards, CI, browser, seed/load or evidence tooling |
| `backend/tests/test_admission.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_admission_api.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_admission_commit_fault.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_admission_readiness.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_auth_http.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_auth_schema_support.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_auth_throttle_http.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_browser_full_harness.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_browser_harness.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_client_identity.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_concurrency_harness.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_config.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_credentials.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_db_smoke.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_domain_schema.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_health.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_idempotency.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_integrated_diagnostics.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_integrated_evidence.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_integrated_host.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_integrated_plan.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_invitation_api.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_invitation_readiness.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_invitations.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_lifecycle.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_lifecycle_acceptance_review.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_lifecycle_api.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_lifecycle_readiness.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_local_env_helper.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_passwords.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_product_labels.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_production.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_profile_inspection_auth.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_profile_inspection_capture.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_profiles_matching.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_read_api.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_realtime.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_realtime_harness.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_recovery_inspection_safety.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_release_support.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_runner_diagnostics.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_sessions.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_team_api.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_team_mutations.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_team_reads.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_team_services.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_test_database_diagnostics.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_test_database_safety.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_throttling.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/tests/test_transaction_retry.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/throttle_tests/conftest.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `backend/throttle_tests/test_throttling.py` | KEEP - offline or guarded PostgreSQL acceptance coverage |
| `deploy/Dockerfile.api` | KEEP - production image/proxy/topology configuration |
| `deploy/Dockerfile.web` | KEEP - production image/proxy/topology configuration |
| `deploy/caddy.template.json` | KEEP - production image/proxy/topology configuration |
| `deploy/compose.json` | KEEP - production image/proxy/topology configuration |
| `docs/ADMISSION.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/ARCHITECTURE.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/AUTH_SCHEMA.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/AUTH_THROTTLING.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/BATCH_A.md` | KEEP - history catalog; review rationale and evidence scope |
| `docs/BATCH_B.md` | KEEP - history catalog; review rationale and evidence scope |
| `docs/BATCH_C.md` | KEEP - history catalog; review rationale and evidence scope |
| `docs/BATCH_D_RECOVERY.md` | KEEP - history catalog; review rationale and evidence scope |
| `docs/BATCH_E_RELEASE.md` | KEEP - history catalog; review rationale and evidence scope |
| `docs/BROWSER_ACCEPTANCE.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/BROWSER_HOST_AUDIT.md` | KEEP - history catalog; review rationale and evidence scope |
| `docs/CREDENTIAL_SERVICES.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/DECISIONS.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/DEMO.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/DESIGN_ONE_PAGE.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/FRONTEND.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/G1_ACCEPTANCE.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/HTTP_AUTH.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/IDEMPOTENCY.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/INTEGRATED_ACCEPTANCE.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/INTEGRATED_HOST.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/INVITATIONS.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/LIFECYCLE.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/PRODUCTION.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/PRODUCT_AUDIT.md` | KEEP - history catalog; review rationale and evidence scope |
| `docs/PROGRESS.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/RANKING.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/READ_API.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/REALTIME.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/RELEASE_VALIDATION.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/REQUIREMENTS.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/SCHEMA.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/SESSION_SERVICES.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/SUBMISSION.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/TEAM_API.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/TEAM_MUTATIONS.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/TEAM_SERVICES.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/TEST_DATABASE.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `docs/TRANSACTION_RETRY.md` | KEEP - component contract, requirements, decisions, runbook or submission evidence |
| `frontend/index.html` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `frontend/package-lock.json` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `frontend/package.json` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `frontend/src/Admission.test.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/AdmissionApi.test.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/App.test.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/App.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/BatchCompatibility.test.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/CreateTeam.test.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/DiscoveryNavigation.test.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/HackathonLookup.test.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/InvitationApi.test.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/Invitations.test.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/Journeys.test.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/Lifecycle.test.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/ProductAudit.test.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/ProfilesRanking.test.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/Realtime.test.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/api.test.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/api.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/components/Admission.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/components/AuthForm.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/components/CreateTeam.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/components/Discovery.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/components/Feedback.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/components/HackathonLookup.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/components/HealthStatus.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/components/Invitations.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/components/Lifecycle.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/components/Profile.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/components/Rankings.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/hooks/useAdmission.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/hooks/useDiscoveryNavigation.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/hooks/useInvitations.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/hooks/useLifecycle.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/hooks/useRead.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/hooks/useRealtime.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/hooks/useSession.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/hooks/useTeamCreation.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/hooks/useWorkspaceSignal.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/main.tsx` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/style.css` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/test/fixtures.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/test/navigationAssertions.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/src/test/setup.ts` | KEEP - React source, API contracts or discovered component tests |
| `frontend/test_support/browserFaults.js` | KEEP - browser fault/campaign/evidence tooling and tests |
| `frontend/test_support/browserFaults.test.js` | KEEP - browser fault/campaign/evidence tooling and tests |
| `frontend/test_support/integratedCampaign.js` | KEEP - browser fault/campaign/evidence tooling and tests |
| `frontend/test_support/integratedCampaign.test.js` | KEEP - browser fault/campaign/evidence tooling and tests |
| `frontend/test_support/integratedEvidence.mjs` | KEEP - browser fault/campaign/evidence tooling and tests |
| `frontend/test_support/integratedEvidence.test.js` | KEEP - browser fault/campaign/evidence tooling and tests |
| `frontend/tsconfig.json` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `frontend/vite.config.ts` | KEEP - project guidance, dependencies, build/editor configuration or safety exclusions |
| `load/board.js` | KEEP - mandatory benchmark scenario/environment template |
| `load/environment.example.json` | KEEP - mandatory benchmark scenario/environment template |
| `scripts/check_local_http.py` | KEEP - reproducible provisioning, inspection or configuration tooling |
| `scripts/configure_backend_env.py` | KEEP - reproducible provisioning, inspection or configuration tooling |
| `scripts/inspect_merge_postgres.sql` | KEEP - reproducible provisioning, inspection or configuration tooling |
| `scripts/inspect_merge_profile_0005.ps1` | KEEP - reproducible provisioning, inspection or configuration tooling |
| `scripts/inspect_merge_recovery.sql` | KEEP - reproducible provisioning, inspection or configuration tooling |
| `scripts/inspect_merge_test.sql` | KEEP - reproducible provisioning, inspection or configuration tooling |
| `scripts/inspect_merge_test_recovery.sql` | KEEP - reproducible provisioning, inspection or configuration tooling |
| `scripts/provision_merge_bench.sql` | KEEP - reproducible provisioning, inspection or configuration tooling |
| `scripts/provision_merge_postgres.sql` | KEEP - reproducible provisioning, inspection or configuration tooling |
| `scripts/provision_merge_profile_test.sql` | KEEP - reproducible provisioning, inspection or configuration tooling |
| `scripts/provision_merge_test.sql` | KEEP - reproducible provisioning, inspection or configuration tooling |

## Changed-file categories

- CI: `.github/workflows/ci.yml`, new `backend/tests/test_ci_configuration.py`.
- Public guides: rewritten `README.md`; current overview in `docs/ARCHITECTURE.md`;
  new `docs/README.md`, `docs/SETUP.md`, `docs/TESTING.md`, `docs/DEPLOYMENT.md`.
- History navigation/inventory: new `docs/archive/README.md` and this audit.
- Evidence log: an additive `docs/PROGRESS.md` entry after actual validation.
- Broken references corrected: none at baseline; all new links checked offline.
- Dependencies/migrations/application changes: none.

Owner exercise: restore the old quoted health command in a temporary copy and
predict why the whitespace-token regression rejects it. Then trace the 0005
matrix entry through the invitation suite and explain why an offline pass cannot
prove the 50-caller PostgreSQL result.

# Submission checklist

Deadline: **15 November 2026, 23:59 IST**. The public repository exists; public
HTTPS deployment and final submission have not been verified. Use the organizer's
workspace to confirm the final submission form. No deployment, recording, upload
or portal action was performed during this local release review.

| Required item | Current location | Evidence / remaining action |
| --- | --- | --- |
| Public source | [GitHub repository](https://github.com/ankit8github/Merge) | Published baseline; this local release still needs approved push |
| GitHub Actions | Repository Actions tab | Owner reports 5/5 at `bb60ab3`; require a new passing run for this release |
| Live React/API | [Render runbook](RENDER.md) | Adapter prepared; no verified HTTPS URL |
| 20+ API tests and 50-caller race | [CI contract](TESTING.md#github-actions-contract), [race scope](G1_ACCEPTANCE.md) | Required suites retained; offline tests are not fresh PostgreSQL certification |
| 10,000 users / 2,000 teams | [Isolated seed tooling](RELEASE_VALIDATION.md) | Generator exists; no measured seed report claimed |
| 100-client p95 < 200 ms | [Isolated load tooling](RELEASE_VALIDATION.md) | Acceptance target, not a result; do not test against Free production |
| One-page design | [Design source](DESIGN_ONE_PAGE.md) | Export and check actual single-page pagination |
| Video <= 5 minutes | [Demo script](DEMO.md) | Record, redact and verify duration; no video URL yet |
| Setup and evidence | [README](../README.md), [testing](TESTING.md), [progress](PROGRESS.md) | Link only actual scope/source-bound evidence |

## Remaining delivery order

1. Review the complete local release scope and its offline results. The owner
   authorized one local commit for this cleanup; no remote or database action.
2. Separately approve source publication, push the reviewed commit and require a
   new successful Actions run at that exact SHA. Preserve its real run URL and
   artifact qualifications; a previous commit's green jobs do not certify this one.
3. Separately approve Render provisioning/initialization and deployment. Follow
   only [RENDER.md](RENDER.md), then verify actual HTTPS, cookie/CSRF/Origin behavior,
   forwarding spoof resistance, membership flows and two-client SSE/reconnection.
   Test phone/keyboard behavior and record sanitized source/image-bound evidence.
4. Complete required load evidence on a separately approved disposable benchmark
   target through [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md). Never reuse retained
   test data or load-test the small Free production service. Missing performance
   evidence remains a submission gap, regardless of deadline pressure.
5. Export the design, rehearse/record [DEMO.md](DEMO.md), inspect every frame for
   sensitive data and check <=300-second duration. Use fresh approved demo
   identities; no direct fixture reset or race/benchmark during recording.
6. Fill actual HTTPS, CI, load, design and video links for the same release scope.
   Open public artifacts unauthenticated, then submit through the organizer's
   workspace after owner approval. Retain the actual receipt/time. Prepared links
   or a local commit are not submission acceptance.

## Evidence boundaries

Historical profile 30/30, SSE 4/4 and lifecycle 10/10 records retain their original
source/receipt qualifications. The original integrated browser campaign is
consumed and uncertified; do not restart it or rewrite its receipt. New deployment
smoke checks cannot retroactively certify that campaign. [Testing](TESTING.md)
explains the distinction and links the guarded acceptance runbooks.

Render's temporary Free database/availability limits remain a delivery risk.
No fake deployment badge, coverage claim, load figure or success screenshot is
permitted. Old freeze/approval command sequences are retained only in
[review history](archive/ENGINEERING_HISTORY.md#batch-e-release); current platform
commands live in their canonical runbooks.

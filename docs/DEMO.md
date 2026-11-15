# Five-minute walkthrough — script only

Target **4:50**, hard stop **5:00**, including titles/transitions. No video or
screenshots were made. Use the exact published release revision. Live actions require
fresh approved demo accounts/hackathon and deployment/browser scope. Never use
retained fixtures, benchmark accounts or old manifests. Use separate browser
profiles (tabs share cookies); hide passwords, CSRF/cookie/network headers and
environments. Do not record password typing.
Prepare the four fresh approved A/B/C/D identities privately; pause recording
before credential entry and resume only after the real result. Do not display
DevTools, terminals with environment values, database rows, private messages,
password managers, cookies, CSRF values, HAR or copied request headers. Use only
approved public demo labels; inspect the entire exported recording before sharing.
Pauses/cuts must not imply an action or result that did not occur.

| Time | Expected action/narration | Proof/fallback after approval |
| --- | --- | --- |
|0:00-0:25|Purpose, topology, database invariants.|One-page design; no deployed claim before HTTPS smoke.|
|0:25-0:55|Show the real registration result for A and explicit signed-in state; explain the separate sign-in.|Pause before credential input. Respect 5 registrations/IP/5min; do not repeat registration for a better take.|
|0:55-1:20|Select hackathon, create team, leader/forming1-of4.|Named board/team capture with environment label.|
|1:20-1:55|B requests in second client; A sees name/@username and approves; B sees ready2-of4.|Two clients, current-leader authority.|
|1:55-2:25|A invites C; C's inbox names team/recipient; C redeems.|Recipient binding/expiry; no email/public token.|
|2:25-2:55|Primary take: A confirms leave; show B becoming leader of the nonempty team.|Use canonical roster/leadership. Last-member deletion/removal may be explained from source/evidence; do not claim they were demonstrated in this take.|
|2:55-3:20|Second client watches a membership change update without refresh.|Actual SSE capture; otherwise say live transport pending.|
|3:20-3:50|As current leader B, refresh rankings for the nonfull team; show opted-in D and actual new-skill/zone components, then select recipient.|Prepare D with a skill absent from the current B/C roster (for example react), not a fixed assumed score. Read actual 70/30 components; no AI or invented ranking result.|
|3:50-4:20|Show sanitized50-caller proof:50 authenticated,1 seat,1 success/49 rejections, invariants.|Prior local aggregate certificate with provenance label; no race during video.|
|4:20-4:45|Actual CI, seed counts, load percentiles/errors/environment, HTTPS/revision.|If missing, mark pending and show tooling only; no fake badges/metrics.|
|4:45-4:50|Trade-offs, extra-week plan, verified links.|Leave10s margin.|

Continue with the same nonfull team after succession, with B as current leader.
D must be opted in and unassigned in that scope. If actual state differs, stop
and review the take rather than creating replacement fixtures for the recording.
Close surplus streams (2/account,64/process). Any live rehearsal needs its own
approved scope; never reset retained fixtures or reuse the consumed campaign.

Fallback captures (all pending): validation/login; named board; applicant decision;
labeled invite; succession/deletion; two-client SSE; scores; sanitized G1/CI;
measured load/environment; HTTPS. Record timestamp, source/image digest and
accepted environment. Historical captures cannot prove the uncommitted tree.
Unavailable proof stays pending; never fabricate screenshots.

Owner reviews audio, legibility,<=5:00 duration, redaction and unauthenticated
access, approves publication and then fills actual video URL/duration in SUBMISSION.md.

Final check: media duration <=300 seconds, including titles. Label the old
integrated browser campaign incomplete; a recording cannot retroactively certify
it. If CI/load/HTTPS proof is absent, say pending and show tooling/source only.
No live race or benchmark is required during recording. [historical batch e release review](archive/ENGINEERING_HISTORY.md#batch-e-release) lists
the official artifacts and separate approvals needed before recording/publication.

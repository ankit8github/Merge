// Offline verifier for OWNER-OBSERVED browser evidence; never launches a browser.
// Its native exit is the browser evidence harness exit, NOT a browser engine exit.
import { readFileSync, realpathSync, lstatSync } from 'node:fs';
import { resolve, dirname, basename } from 'node:path';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';

export const observations = ['two_isolated_clients','sse_without_manual_refresh','lease_reconnect_refetch',
  'no_private_content_leak','old_account_callbacks_fenced','old_workspace_callbacks_fenced',
  'keyboard_only_actions','mobile_390_no_overflow','cancel_no_posts_focus_restored','navigation_no_automatic_posts'];

export function validateBrowserEvidence(data, plan, readArtifact) {
  const require = value => { if (!value) throw new Error('Browser observations incomplete'); };
  require(data.schema_version === 1 && data.kind === 'integrated-browser-observations' && data.run_id === plan.run_id &&
    data.status === 'passed' && data.skipped?.length === 0 && data.failures?.length === 0 && data.active_checkpoint === null &&
    data.owner_observed === true && data.browser_engine_exit === 'not_captured');
  require(typeof data.browser === 'string' && data.browser.trim().length > 2 && typeof data.browser_version === 'string' &&
    data.browser_version.trim().length > 0 && typeof data.os === 'string' && data.os.trim().length > 0);
  require(JSON.stringify(data.viewports) === JSON.stringify(plan.viewports));
  require(data.observations && Object.keys(data.observations).length === observations.length && observations.every(k => data.observations[k] === true));
  require(Number.isFinite(Date.parse(data.started_at)) && Number.isFinite(Date.parse(data.finished_at)) && Date.parse(data.finished_at) >= Date.parse(data.started_at));
  require(Array.isArray(data.checkpoints) && data.checkpoints.length === plan.coverage.length &&
    new Set(data.checkpoints.map(c => c.id)).size === plan.coverage.length);
  for (const c of data.checkpoints) {
    require(plan.coverage.includes(c.id) && c.status === 'passed' && /^[0-9a-f]{64}$/.test(c.evidence_sha256) &&
      typeof c.artifact === 'string' && c.artifact.startsWith(`browser-${plan.run_id}-`) &&
      /^browser-[0-9a-f-]+-[a-z_]+\.(?:png|json)$/.test(c.artifact));
    const bytes = readArtifact(c.artifact);
    require(bytes.length > 0 && bytes.length <= 8_000_000 && createHash('sha256').update(bytes).digest('hex') === c.evidence_sha256);
  }
  return { status: 'observed_evidence_integrity_passed', browser_engine_exit: 'not_captured' };
}

export function main(args) {
  try {
    if (args.length !== 1) throw new Error();
    const directory = resolve('backend/test-results/integrated'), path = resolve(args[0]);
    if (dirname(path) !== directory || realpathSync(directory) !== directory || lstatSync(path).isSymbolicLink() ||
        !/^browser-observations-[0-9a-f-]+\.json$/.test(basename(path)) || lstatSync(path).size > 1_000_000) throw new Error();
    const plan = JSON.parse(readFileSync('acceptance/integrated-campaign.json', 'utf8'));
    const data = JSON.parse(readFileSync(path, 'utf8'));
    const result = validateBrowserEvidence(data, plan, name => {
      const artifact = resolve(directory, name);
      if (dirname(artifact) !== directory || lstatSync(artifact).isSymbolicLink() || realpathSync(artifact) !== artifact) throw new Error();
      return readFileSync(artifact);
    });
    process.stdout.write(JSON.stringify(result) + '\n'); return 0;
  } catch { process.stdout.write('{"status":"not_certified"}\n'); return 1; }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) process.exitCode = main(process.argv.slice(2));

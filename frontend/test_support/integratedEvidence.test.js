import { test } from 'vitest';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { validateBrowserEvidence, observations } from './integratedEvidence.mjs';

const plan=JSON.parse(readFileSync('../acceptance/integrated-campaign.json','utf8'));
const bytes=Buffer.from('synthetic offline observation, not live evidence');
const hash=createHash('sha256').update(bytes).digest('hex');
function fixture() {
  return {schema_version:1,kind:'integrated-browser-observations',run_id:plan.run_id,status:'passed',skipped:[],failures:[],active_checkpoint:null,
    owner_observed:true,browser_engine_exit:'not_captured',browser:'Synthetic browser',browser_version:'offline',os:'synthetic',
    viewports:plan.viewports,observations:Object.fromEntries(observations.map(k=>[k,true])),
    started_at:'2026-11-14T01:00:00Z',finished_at:'2026-11-14T02:00:00Z',
    checkpoints:plan.coverage.map(id=>({id,status:'passed',artifact:`browser-${plan.run_id}-${id}.json`,evidence_sha256:hash}))};
}
test('accepts complete synthetic observation integrity without claiming browser-engine exit',()=>{
  assert.deepEqual(validateBrowserEvidence(fixture(),plan,()=>bytes),{status:'observed_evidence_integrity_passed',browser_engine_exit:'not_captured'});
});
for (const fault of ['skip','failure','unfinished','duplicate','missing','hash','artifact','traversal','observation','viewport','browser','exit','timing','unobserved','run']) {
  test(`refuses ${fault} browser evidence`,()=>{
    const data=fixture();let read=()=>bytes;
    if (fault==='skip') data.skipped=['auth'];
    else if (fault==='failure') data.failures=['auth'];
    else if (fault==='unfinished') data.active_checkpoint='auth';
    else if (fault==='duplicate') data.checkpoints[1]=data.checkpoints[0];
    else if (fault==='missing') data.checkpoints.pop();
    else if (fault==='hash') data.checkpoints[0].evidence_sha256='a'.repeat(64);
    else if (fault==='artifact') read=()=>Buffer.from('altered');
    else if (fault==='traversal') data.checkpoints[0].artifact='../old.json';
    else if (fault==='observation') data.observations.keyboard_only_actions=false;
    else if (fault==='viewport') data.viewports=[];
    else if (fault==='browser') data.browser='';
    else if (fault==='exit') data.browser_engine_exit=0;
    else if (fault==='timing') data.finished_at='invalid';
    else if (fault==='unobserved') data.owner_observed=false;
    else data.run_id='other';
    assert.throws(()=>validateBrowserEvidence(data,plan,read));
  });
}

import { test } from 'vitest';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { commandSpec, rehearsalBudget, assertInitialRanking, assertFinalScope } from './integratedCampaign.js';

const plan = JSON.parse(readFileSync('../acceptance/integrated-campaign.json', 'utf8'));
const bindings = Object.fromEntries(['l','q','r','x','a','b','request_q','request_r','issue_q','issue_r'].map(k => [k, randomUUID()]));
const request = tag => ({ ...commandSpec(plan, tag, bindings), key: `offline-${tag}` });

test('all 17 commands resolve exact scoped paths and permit only the 18 approved attempts', () => {
  const budget = rehearsalBudget(plan);
  for (const c of plan.commands) {
    for (let i = 0; i < c.attempts; i++) budget.claim(c.tag, request(c.tag), bindings);
    assert.throws(() => budget.claim(c.tag, request(c.tag), bindings), /exhausted/);
  }
  assert.equal(Object.values(budget.counts()).reduce((a,b) => a+b, 0), 18);
  assert.match(commandSpec(plan, 'create_b', bindings).path, new RegExp(plan.hackathons[1].id));
});

for (const field of ['key','body','actor','path','method']) test(`recovery refuses changed ${field} and spends no new attempt`, () => {
  const budget = rehearsalBudget(plan), original = request('create_a');
  budget.claim('create_a', original, bindings);
  const changed = { ...original, [field]: field === 'body' ? { name: 'other' } : 'other' };
  assert.throws(() => budget.claim('create_a', changed, bindings));
  assert.equal(budget.counts().create_a, 1);
  budget.claim('create_a', original, bindings);
});

test('rejects unknown commands, unbound identities and development target', () => {
  assert.throws(() => commandSpec(plan, 'join_any_team', bindings));
  assert.throws(() => commandSpec(plan, 'remove_r', { ...bindings, r: undefined }));
  assert.throws(() => commandSpec({ ...plan, target: { ...plan.target, database: 'merge_dev' } }, 'create_a', bindings));
  assert.throws(() => commandSpec({ ...plan, target: { ...plan.target, role: 'postgres' } }, 'create_a', bindings));
  assert.throws(() => commandSpec({ ...plan, target: { ...plan.target, host: 'localhost' } }, 'create_a', bindings));
  assert.throws(() => commandSpec({ ...plan, target: { ...plan.target, port: 5433 } }, 'create_a', bindings));
});

test('final departure cannot reuse the earlier voluntary-leave receipt key', () => {
  const budget = rehearsalBudget(plan);
  budget.claim('leave_q', request('leave_q'), bindings);
  assert.throws(() => budget.claim('final_q', { ...request('final_q'), key: request('leave_q').key }, bindings), /reused/);
  budget.claim('final_q', request('final_q'), bindings);
});

test('ranking catches eligibility leaks, wrong scores, explanations and reversed order', () => {
  const q = { user_id: bindings.q, score: 100, skill_points: 70, timezone_points: 30, new_skills: ['sql'] };
  const r = { user_id: bindings.r, score: 44.375, skill_points: 35, timezone_points: 9.375, new_skills: ['sql'] };
  assertInitialRanking([q,r], bindings);
  for (const rows of [[r,q], [q,{ ...r, score: 100 }], [q,r,{ ...q, user_id: bindings.x }], [q],
    [{ ...q, new_skills: [] },r]]) assert.throws(() => assertInitialRanking(rows, bindings));
});

test('terminal scope requires tombstone, exact audit chain sizes and untouched second workspace', () => {
  const state = { teams: [{ id: bindings.a, deleted_at: 'observed', leader_user_id: null, version: 13 },
    { id: bindings.b, deleted_at: null, leader_user_id: bindings.q, version: 1 }],
    memberships: [{ user_id: bindings.q, team_id: bindings.b, hackathon_id: plan.hackathons[1].id }],
    audit: 14, outbox: 14, idempotency: 14 };
  assertFinalScope(state, bindings, plan);
  for (const field of ['audit','outbox','idempotency']) assert.throws(() => assertFinalScope({ ...state, [field]: 15 }, bindings, plan));
  assert.throws(() => assertFinalScope({ ...state, memberships: [] }, bindings, plan));
  assert.throws(() => assertFinalScope({ ...state, teams: [state.teams[1]] }, bindings, plan));
});

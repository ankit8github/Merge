// Offline assertions for the proposed integrated browser campaign.
// No network, browser startup, storage, fault installation or production imports.
const fail = message => { throw new Error(message); };
const uuid = value => typeof value === 'string' && /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/.test(value);

export function commandSpec(plan, tag, bindings) {
  if (plan.target.database !== 'merge_profile_test' || plan.target.revision !== '0006_profiles' ||
      plan.target.role !== 'merge_app' || plan.target.host !== '127.0.0.1' || plan.target.port !== 5432 ||
      plan.origin !== 'http://127.0.0.1:5173' || plan.api_origin !== 'http://127.0.0.1:8000') fail('Unapproved campaign target');
  const command = plan.commands.find(c => c.tag === tag);
  if (!command) fail('Unknown command');
  const h = plan.hackathons[tag === 'create_b' ? 1 : 0].id;
  const actor = bindings[command.actor];
  if (!uuid(h) || !uuid(actor)) fail('Real reply bindings required');
  const base = `/api/hackathons/${h}/teams`;
  let path = base, body = {};
  if (tag.startsWith('create_')) body = { name: plan.teams[tag === 'create_a' ? 'a' : 'b'] };
  else {
    if (!uuid(bindings.a)) fail('Real team reply required');
    path += `/${bindings.a}`;
    if (tag.startsWith('request_')) path += '/join-requests';
    else if (['deny_decision', 'reject_r', 'approve_q'].includes(tag)) {
      const request = bindings[tag === 'approve_q' ? 'request_q' : 'request_r'];
      if (!uuid(request)) fail('Real request reply required');
      path += `/join-requests/${request}/decision`;
      body = { decision: tag === 'reject_r' ? 'reject' : 'approve' };
    } else if (tag.startsWith('issue_')) {
      const recipient = bindings[tag === 'issue_q' ? 'q' : 'r'];
      if (!uuid(recipient)) fail('Real recipient reply required');
      path += '/invitations'; body = { recipient_id: recipient };
    } else if (['deny_redeem', 'redeem_r', 'redeem_q'].includes(tag)) {
      const grant = bindings[tag === 'redeem_q' ? 'issue_q' : 'issue_r'];
      if (!uuid(grant)) fail('Real invitation reply required');
      path += `/invitations/${grant}/redeem`;
    } else if (['deny_remove', 'remove_r'].includes(tag)) {
      if (!uuid(bindings.r)) fail('Real member reply required');
      path += `/members/${bindings.r}/remove`;
    } else if (['leave_l', 'leave_q', 'final_q'].includes(tag)) path += '/leave';
    else fail('Unknown route');
  }
  return Object.freeze({ method: 'POST', path, body, actor, attempts: command.attempts });
}

// Local rehearsal only. A future host must enforce the same budget BEFORE any
// real service or durable invitation throttle; this object grants no DB authority.
export function rehearsalBudget(plan) {
  const seen = new Map(), keys = new Map();
  return Object.freeze({
    claim(tag, request, bindings) {
      const expected = commandSpec(plan, tag, bindings);
      if (request.method !== expected.method || request.path !== expected.path || request.actor !== expected.actor ||
          JSON.stringify(request.body) !== JSON.stringify(expected.body) || typeof request.key !== 'string' ||
          !request.key.length || request.key.length > 128) fail('Request outside approved command');
      const fingerprint = JSON.stringify([request.method, request.path, request.actor, request.body, request.key]);
      const keyScope = JSON.stringify([request.actor, request.key]);
      if (keys.has(keyScope) && keys.get(keyScope) !== tag) fail('Key reused across distinct campaign commands');
      const old = seen.get(tag);
      if (old && old.fingerprint !== fingerprint) fail('Retry changed original command');
      if ((old?.attempts ?? 0) >= expected.attempts) fail('Command budget exhausted');
      keys.set(keyScope, tag);
      seen.set(tag, { fingerprint, attempts: (old?.attempts ?? 0) + 1 });
    },
    counts() { return Object.fromEntries([...seen].map(([tag, value]) => [tag, value.attempts])); },
  });
}

export function assertInitialRanking(items, bindings) {
  const q = items.find(i => i.user_id === bindings.q);
  const r = items.find(i => i.user_id === bindings.r);
  if (!q || !r || items.some(i => [bindings.l, bindings.x].includes(i.user_id)) ||
      q.score !== 100 || q.skill_points !== 70 || q.timezone_points !== 30 ||
      r.score !== 44.375 || r.skill_points !== 35 || r.timezone_points !== 9.375 ||
      q.new_skills.join(',') !== 'sql' || r.new_skills.join(',') !== 'sql' ||
      items.indexOf(q) >= items.indexOf(r)) fail('Ranking/eligibility/explanation differs');
  // Other retained globally discoverable accounts may be present. Never hide or
  // delete them; page canonical results until both fresh candidate IDs are found.
}

export function assertFinalScope(state, bindings, plan) {
  const a = state.teams.find(t => t.id === bindings.a);
  const b = state.teams.find(t => t.id === bindings.b);
  if (state.teams.length !== 2 || !a || !b || !a.deleted_at || b.deleted_at !== null ||
      a.leader_user_id !== null || b.leader_user_id !== bindings.q || a.version !== 13 || b.version !== 1 ||
      state.memberships.length !== 1 || state.memberships[0].user_id !== bindings.q ||
      state.memberships[0].team_id !== bindings.b || state.memberships[0].hackathon_id !== plan.hackathons[1].id ||
      state.audit !== 14 || state.outbox !== 14 || state.idempotency !== 14) fail('Final fresh-scope state differs');
}

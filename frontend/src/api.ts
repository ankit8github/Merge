// Same-origin transport only. Cookies are owned by the browser, CSRF by memory.
export type Identity = { user_id: string; username: string };
export type Session = { identity: Identity; expires_at: string; csrf_token: string };
export type Hackathon = { id: string; name: string; min_team_size: number; max_team_size: number };
export type Team = Hackathon & {
  hackathon_id: string; member_count: number; readiness: 'forming' | 'ready';
  leader: { user_id: string; display_name: string }; created_at: string;
};
export type Page<T> = { items: T[]; next_cursor: string | null };
export type Credentials = { username: string; password: string };
export type CreateTeamBody = { name: string };
export type Decision = 'approve' | 'reject';
export type JoinRequest = {
  id: string; hackathon_id: string; team_id: string; requester_id: string;
  status: 'pending' | 'approved' | 'rejected'; created_at: string; resolved_at: string | null;
  requester_display_name?: string; requester_username?: string;
};
export type Invitation = {
  id: string; hackathon_id: string; team_id: string; recipient_id: string; issued_by: string;
  status: 'pending' | 'redeemed'; created_at: string; expires_at: string; redeemed_at: string | null;
};
export type InboxInvitation = Invitation & { available: boolean; team_name?: string; recipient_display_name?: string; recipient_username?: string };
export type Profile = Identity & { display_name: string; skills: string[]; timezone: string | null; discoverable: boolean; version: number };
export type ProfileEdit = Pick<Profile, 'skills' | 'timezone' | 'discoverable' | 'version'>;
export type Suggestion = Identity & { display_name: string; skills: string[]; timezone: string; new_skills: string[];
  skill_complement: number; timezone_overlap: number; skill_points: number; timezone_points: number; score: number };
export type Rankings = { hackathon_id: string; team_id: string; user_id: string; reference_at: string;
  team_skills: string[]; skill_weight: 0.7; timezone_weight: 0.3; items: Suggestion[]; next_cursor: string | null };
export type Member = { user_id: string; display_name: string; joined_at: string };
export type LifecycleReceipt = { hackathon_id: string; team_id: string; user_id: string;
  member_count: number; team_version: number; leader_user_id: string | null; deleted: boolean };
export type CreatedTeam = { schema_version: 1; data: {
  team_id: string; hackathon_id: string; user_id: string; member_count: 1; team_version: 1;
} };

export class ApiError extends Error {
  constructor(public status = 0, public code = 'network_error', public retryable = false,
              public retryAt = 0) { super('Request could not be completed'); }
}

const object = (value: unknown): Record<string, unknown> => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new ApiError(0, 'invalid_response');
  return value as Record<string, unknown>;
};
const string = (value: unknown, max: number): string => {
  if (typeof value !== 'string' || !value.length || Array.from(value).length > max) throw new ApiError(0, 'invalid_response');
  return value;
};
const uuid = (value: unknown): string => {
  const result = string(value, 36);
  if (!/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(result)) throw new ApiError(0, 'invalid_response');
  return result;
};
export function canonicalUuid(value: string): string {
  if (!/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(value)) throw new ApiError(422, 'invalid_request');
  return value.toLowerCase();
}

async function lookupHackathon(value: string, signal?: AbortSignal): Promise<Hackathon | null> {
  const id = canonicalUuid(value);
  const number = BigInt('0x' + id.replaceAll('-', ''));
  // The catalog uses an exclusive UUID boundary, even for a nonexistent row.
  const hex = number === 0n ? null : (number - 1n).toString(16).padStart(32, '0');
  const cursor = hex === null ? null : `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  return request('/api/hackathons?limit=1' + (cursor === null ? '' : `&cursor=${cursor}`), value => {
    const result = page(value, hackathon);
    if (result.items.length > 1) throw new ApiError(0, 'invalid_response');
    const found = result.items[0];
    return found && canonicalUuid(found.id) === id ? { ...found, id } : null;
  }, signal);
}
const integer = (value: unknown): number => {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 1) throw new ApiError(0, 'invalid_response');
  return value;
};
function identity(value: unknown): Identity {
  const v = object(value);
  return { user_id: uuid(v.user_id), username: string(v.username, 32) };
}
function session(value: unknown): Session {
  const v = object(value), csrf = string(v.csrf_token, 43), expiry = string(v.expires_at, 64);
  if (!/^[A-Za-z0-9_-]{43}$/.test(csrf) || !Number.isFinite(Date.parse(expiry))) throw new ApiError(0, 'invalid_response');
  return { identity: identity(v.identity), expires_at: expiry, csrf_token: csrf };
}
function hackathon(value: unknown): Hackathon {
  const v = object(value), min = integer(v.min_team_size), max = integer(v.max_team_size);
  if (min > max) throw new ApiError(0, 'invalid_response');
  return { id: uuid(v.id), name: string(v.name, 120), min_team_size: min, max_team_size: max };
}
function team(value: unknown, scope: string): Team {
  const v = object(value), base = hackathon(v), leader = object(v.leader), count = integer(v.member_count);
  const created = string(v.created_at, 64), hackathonId = uuid(v.hackathon_id);
  const readiness = count >= base.min_team_size ? 'ready' : 'forming';
  if (hackathonId !== scope || count > base.max_team_size || !Number.isFinite(Date.parse(created)) ||
      v.readiness !== readiness) throw new ApiError(0, 'invalid_response');
  return { ...base, hackathon_id: hackathonId, member_count: count, readiness,
    leader: { user_id: uuid(leader.user_id), display_name: string(leader.display_name, 80) }, created_at: created };
}
function page<T>(value: unknown, parse: (item: unknown) => T): Page<T> {
  const v = object(value);
  if (!Array.isArray(v.items) || v.items.length > 20) throw new ApiError(0, 'invalid_response');
  return { items: v.items.map(parse), next_cursor: v.next_cursor === null ? null : uuid(v.next_cursor) };
}

function joinRequest(value: unknown, hackathonId: string, teamId: string): JoinRequest {
  const v = object(value), created = string(v.created_at, 64);
  const resolved = v.resolved_at === null ? null : string(v.resolved_at, 64);
  if (v.hackathon_id !== hackathonId || v.team_id !== teamId ||
      !['pending', 'approved', 'rejected'].includes(String(v.status)) ||
      !Number.isFinite(Date.parse(created)) || (v.status === 'pending') !== (resolved === null) ||
      (resolved !== null && (!Number.isFinite(Date.parse(resolved)) || Date.parse(resolved) < Date.parse(created)))) {
    throw new ApiError(0, 'invalid_response');
  }
  return { id: uuid(v.id), hackathon_id: uuid(v.hackathon_id), team_id: uuid(v.team_id),
    requester_id: uuid(v.requester_id), status: v.status as JoinRequest['status'], created_at: created, resolved_at: resolved };
}
function mutationHeaders(key: string, csrf: string) {
  if (!/^[ -~]{1,128}$/.test(key) || !/^[A-Za-z0-9_-]{43}$/.test(csrf)) throw new ApiError(422, 'invalid_request');
}
const requestsPath = (h: string, t: string) => scope(h) + '/teams/' + uuid(t) + '/join-requests';
const invitationsPath = (h: string, t: string) => scope(h) + '/teams/' + uuid(t) + '/invitations';

function invitationTime(value: string): bigint {
  // Python/PostgreSQL retain microseconds; Date.parse alone can collapse a
  // valid redemption just before expiry into the same millisecond as expiry.
  const match = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.(\d{1,6}))?(?:Z|[+-]\d{2}:\d{2})$/.exec(value);
  const ms = Date.parse(value);
  if (!match || !Number.isFinite(ms)) throw new ApiError(0, 'invalid_response');
  return BigInt(ms) * 1000n + BigInt((match[1] ?? '').padEnd(6, '0').slice(3));
}

function invitation(value: unknown, h: string, t?: string): Invitation {
  const v = object(value), created = string(v.created_at, 64), expiry = string(v.expires_at, 64);
  const redeemed = v.redeemed_at === null ? null : string(v.redeemed_at, 64);
  const at = invitationTime(created), until = invitationTime(expiry), used = redeemed === null ? null : invitationTime(redeemed);
  if (v.hackathon_id !== h || (t !== undefined && v.team_id !== t) ||
      !['pending', 'redeemed'].includes(String(v.status)) || until <= at || until - at > 86400000000n ||
      (v.status === 'pending') !== (redeemed === null) || (used !== null && (used < at || used >= until))) throw new ApiError(0, 'invalid_response');
  return { id: uuid(v.id), hackathon_id: uuid(v.hackathon_id), team_id: uuid(v.team_id),
    recipient_id: uuid(v.recipient_id), issued_by: uuid(v.issued_by), status: v.status as Invitation['status'],
    created_at: created, expires_at: expiry, redeemed_at: redeemed };
}

async function request<T>(path: string, parse: (value: unknown) => T,
                          signal?: AbortSignal, body?: unknown, csrf?: string, expectedStatus: number | readonly number[] = 200,
                          idempotencyKey?: string): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  if (signal?.aborted) controller.abort();
  const timeout = window.setTimeout(abort, 20000);
  try {
    const response = await fetch(path, {
      method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin', cache: 'no-store',
      redirect: 'error', signal: controller.signal,
      headers: body === undefined ? { Accept: 'application/json' } : {
        Accept: 'application/json', 'Content-Type': 'application/json',
        ...(csrf ? { 'X-CSRF-Token': csrf } : { 'X-Merge-Request': '1' }),
        ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
      }, ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    if (!response.ok) {
      let code = 'request_failed', retryable = false;
      try {
        const error = object(object(await response.json()).error);
        if (typeof error.code === 'string' && /^[a-z_]{1,64}$/.test(error.code)) code = error.code;
        retryable = error.retryable === true;
      } catch { /* Never render or log arbitrary upstream text. */ }
      const seconds = response.headers.get('Retry-After');
      const wait = seconds && /^\d{1,6}$/.test(seconds) ? Math.min(3600, Math.max(1, Number(seconds))) : 30;
      throw new ApiError(response.status, code, retryable, response.status === 429 ? Date.now() + wait * 1000 : 0);
    }
    if (!(Array.isArray(expectedStatus) ? expectedStatus.includes(response.status) : response.status === expectedStatus)) throw new ApiError(0, 'invalid_response');
    return parse(response.status === 204 ? null : await response.json());
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError();
  } finally {
    window.clearTimeout(timeout);
    signal?.removeEventListener('abort', abort);
  }
}

const query = (cursor: string | null) => `?limit=20${cursor ? `&cursor=${encodeURIComponent(uuid(cursor))}` : ''}`;
const scope = (id: string) => `/api/hackathons/${uuid(id)}`;

const optionalLabel = (v: unknown, max: number) => v === undefined || v === null ? undefined : string(v, max);
function skillList(value: unknown, max = 20): string[] {
  if (!Array.isArray(value) || value.length > max || value.some(s => typeof s !== 'string' || !/^[a-z0-9][a-z0-9+#.\-]{0,31}$/.test(s)) ||
      new Set(value).size !== value.length) throw new ApiError(0, 'invalid_response');
  return value as string[];
}
function profile(value: unknown, actor: string): Profile {
  const v = object(value), account = identity(v);
  if (account.user_id !== actor || typeof v.discoverable !== 'boolean' || typeof v.version !== 'number' ||
      !Number.isSafeInteger(v.version) || v.version < 0 || (v.discoverable && v.timezone === null)) throw new ApiError(0, 'invalid_response');
  return { ...account, display_name: string(v.display_name, 80), skills: skillList(v.skills),
    timezone: v.timezone === null ? null : string(v.timezone, 64), discoverable: v.discoverable, version: v.version };
}
function rankings(value: unknown, h: string, t: string, actor: string): Rankings {
  const v = object(value);
  if (v.hackathon_id !== h || v.team_id !== t || v.user_id !== actor || v.skill_weight !== .7 || v.timezone_weight !== .3 ||
      typeof v.reference_at !== 'string' || !Number.isFinite(Date.parse(v.reference_at)) || !Array.isArray(v.items) || v.items.length > 20 ||
      (v.next_cursor !== null && (typeof v.next_cursor !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(v.next_cursor)))) throw new ApiError(0, 'invalid_response');
  const items = v.items.map(item => {
    const r = object(item), account = identity(r);
    for (const [field, max] of [['skill_complement', 1], ['timezone_overlap', 1], ['skill_points', 70], ['timezone_points', 30], ['score', 100]] as const) {
      if (typeof r[field] !== 'number' || !Number.isFinite(r[field]) || r[field] < 0 || r[field] > max) throw new ApiError(0, 'invalid_response');
    }
    const skill = r.skill_complement as number, overlap = r.timezone_overlap as number, score = r.score as number;
    const skillPoints = r.skill_points as number, zonePoints = r.timezone_points as number;
    if (account.user_id === actor || Math.abs(skillPoints - 70 * skill) > .000071 || Math.abs(zonePoints - 30 * overlap) > .000031 ||
        Math.abs(score - skillPoints - zonePoints) > .000002) throw new ApiError(0, 'invalid_response');
    return { ...account, display_name: string(r.display_name, 80), skills: skillList(r.skills), timezone: string(r.timezone, 64),
      new_skills: skillList(r.new_skills), skill_complement: skill, timezone_overlap: overlap, skill_points: skillPoints, timezone_points: zonePoints, score };
  });
  if (new Set(items.map(r => r.user_id)).size !== items.length) throw new ApiError(0, 'invalid_response');
  return { hackathon_id: h, team_id: t, user_id: actor, reference_at: v.reference_at, team_skills: skillList(v.team_skills, 200000),
    skill_weight: .7, timezone_weight: .3, items, next_cursor: v.next_cursor as string | null };
}
export const api = {
  profile: (actor: string, signal?: AbortSignal) => request('/api/me/profile', value => profile(value, actor), signal),
  saveProfile: (actor: string, body: ProfileEdit, csrf: string, signal?: AbortSignal) => {
    if (!/^[A-Za-z0-9_-]{43}$/.test(csrf)) throw new ApiError(422, 'invalid_request');
    return request('/api/me/profile', value => {
      const saved = profile(value, actor);
      const normalized = [...new Set(body.skills.map(s => s.trim().toLowerCase()))].sort();
      if (saved.version !== body.version + 1 || saved.timezone !== body.timezone || saved.discoverable !== body.discoverable ||
          JSON.stringify(saved.skills) !== JSON.stringify(normalized)) throw new ApiError(0, 'invalid_response');
      return saved;
    }, signal, body, csrf);
  },
  suggestions: (h: string, t: string, actor: string, cursor: string | null, signal?: AbortSignal) => {
    if (cursor !== null && !/^[A-Za-z0-9_-]{1,128}$/.test(cursor)) throw new ApiError(422, 'invalid_request');
    return request(scope(h) + '/teams/' + uuid(t) + '/suggestions?limit=20' + (cursor ? '&cursor=' + encodeURIComponent(cursor) : ''),
      value => rankings(value, h, t, actor), signal);
  },
  members: (h: string, t: string, cursor: string | null, signal?: AbortSignal) => request(scope(h) + '/teams/' + uuid(t) + '/members' + query(cursor), value => {
    const result = page<Member>(value, item => {
      const v = object(item);
      if (typeof v.joined_at !== 'string' || !Number.isFinite(Date.parse(v.joined_at))) throw new ApiError(0, 'invalid_response');
      return { user_id: uuid(v.user_id), display_name: string(v.display_name, 80), joined_at: v.joined_at };
    });
    if (new Set(result.items.map(row => row.user_id)).size !== result.items.length ||
        (result.next_cursor !== null && result.next_cursor !== result.items.at(-1)?.user_id)) throw new ApiError(0, 'invalid_response');
    return result;
  }, signal),
  lifecycle: (kind: 'leave' | 'remove', h: string, t: string, subject: string, key: string, csrf: string, signal?: AbortSignal) => {
    mutationHeaders(key, csrf); uuid(subject);
    return request(scope(h) + '/teams/' + uuid(t) + (kind === 'leave' ? '/leave' : '/members/' + uuid(subject) + '/remove'), value => {
      const v = object(value), d = object(v.data);
      const count = d.member_count, version = d.team_version, leader = d.leader_user_id === null ? null : uuid(d.leader_user_id);
      if (v.schema_version !== 1 || uuid(d.hackathon_id) !== h || uuid(d.team_id) !== t || uuid(d.user_id) !== subject ||
          typeof count !== 'number' || !Number.isSafeInteger(count) || count < 0 ||
          typeof version !== 'number' || !Number.isSafeInteger(version) || version < 2 ||
          typeof d.deleted !== 'boolean' || d.deleted !== (count === 0) || d.deleted !== (leader === null) ||
          (kind === 'remove' && (d.deleted || leader === subject))) throw new ApiError(0, 'invalid_response');
      return { hackathon_id: h, team_id: t, user_id: subject, member_count: count, team_version: version,
        leader_user_id: leader, deleted: d.deleted } satisfies LifecycleReceipt;
    }, signal, {}, csrf, 200, key);
  },
  lookupHackathon,
  invitations: (h: string, cursor: string | null, signal?: AbortSignal) => request(scope(h) + '/invitations/mine' + query(cursor), value => {
    const result = page<InboxInvitation>(value, item => {
      const v = object(item), row = invitation(v, h);
      if (typeof v.available !== 'boolean' || (row.status === 'redeemed' && v.available)) throw new ApiError(0, 'invalid_response');
      return { ...row, available: v.available, team_name: optionalLabel(v.team_name, 120),
        recipient_display_name: optionalLabel(v.recipient_display_name, 80), recipient_username: optionalLabel(v.recipient_username, 32) };
    });
    if (new Set(result.items.map(row => row.id)).size !== result.items.length ||
        (result.next_cursor !== null && result.next_cursor !== result.items.at(-1)?.id)) throw new ApiError(0, 'invalid_response');
    return result;
  }, signal),
  issueInvitation: async (h: string, t: string, recipient: string, key: string, csrf: string, signal?: AbortSignal) => {
    mutationHeaders(key, csrf); uuid(recipient);
    return request(invitationsPath(h, t), value => {
      const v = object(value), row = invitation(v.data, h, t);
      if (v.schema_version !== 1 || row.status !== 'pending' || row.recipient_id !== recipient) throw new ApiError(0, 'invalid_response');
      return row;
    }, signal, { recipient_id: recipient }, csrf, 201, key);
  },
  redeemInvitation: async (h: string, t: string, id: string, key: string, csrf: string, signal?: AbortSignal) => {
    mutationHeaders(key, csrf);
    return request(invitationsPath(h, t) + '/' + uuid(id) + '/redeem', value => {
      const v = object(value), row = invitation(v.data, h, t);
      if (v.schema_version !== 1 || row.id !== id || row.status !== 'redeemed') throw new ApiError(0, 'invalid_response');
      return row;
    }, signal, {}, csrf, 200, key);
  },
  ownRequest: (h: string, t: string, signal?: AbortSignal) => request(requestsPath(h, t) + '/mine', value => {
    const v = object(value);
    return v.request === null ? null : joinRequest(v.request, h, t);
  }, signal),
  pendingRequests: (h: string, t: string, cursor: string | null, signal?: AbortSignal) => request(requestsPath(h, t) + query(cursor), value => {
    const result = page(value, item => {
      const v = object(item);
      return { ...joinRequest(item, h, t), requester_display_name: optionalLabel(v.requester_display_name, 80),
        requester_username: optionalLabel(v.requester_username, 32) };
    });
    if (result.items.some(item => item.status !== 'pending') || new Set(result.items.map(item => item.id)).size !== result.items.length ||
        (result.next_cursor !== null && result.next_cursor !== result.items.at(-1)?.id)) throw new ApiError(0, 'invalid_response');
    return result;
  }, signal),
  createRequest: async (h: string, t: string, key: string, csrf: string, signal?: AbortSignal) => {
    mutationHeaders(key, csrf);
    return request(requestsPath(h, t), value => {
      const v = object(value);
      if (v.schema_version !== 1) throw new ApiError(0, 'invalid_response');
      return joinRequest(v.data, h, t);
    }, signal, {}, csrf, [200, 201], key);
  },
  decideRequest: async (h: string, t: string, id: string, decision: Decision, key: string, csrf: string, signal?: AbortSignal) => {
    mutationHeaders(key, csrf);
    if (decision !== 'approve' && decision !== 'reject') throw new ApiError(422, 'invalid_request');
    return request(requestsPath(h, t) + '/' + uuid(id) + '/decision', value => {
      const v = object(value), row = joinRequest(v.data, h, t);
      if (v.schema_version !== 1 || row.id !== id || row.status !== (decision === 'approve' ? 'approved' : 'rejected')) throw new ApiError(0, 'invalid_response');
      return row;
    }, signal, { decision }, csrf, 200, key);
  },
  session: (signal?: AbortSignal) => request('/auth/session', session, signal),
  login: (body: Credentials, signal?: AbortSignal) => request('/auth/login', session, signal, body),
  register: (body: Credentials & { display_name?: string }, signal?: AbortSignal) => request('/auth/register', identity, signal, body, undefined, 201),
  logout: (csrf: string, signal?: AbortSignal) => request('/auth/logout', () => undefined, signal, {}, csrf, 204),
  createTeam: (id: string, body: CreateTeamBody, key: string, csrf: string, signal?: AbortSignal) => {
    if (!/^[ -~]{1,128}$/.test(key) || !/^[A-Za-z0-9_-]{43}$/.test(csrf)) {
      return Promise.reject(new ApiError(422, 'invalid_request'));
    }
    return request(scope(id) + '/teams', (value): CreatedTeam => {
      const v = object(value), data = object(v.data), hackathonId = uuid(data.hackathon_id);
      if (v.schema_version !== 1 || data.member_count !== 1 || data.team_version !== 1 || hackathonId !== id) {
        throw new ApiError(0, 'invalid_response');
      }
      return { schema_version: 1, data: { team_id: uuid(data.team_id), hackathon_id: hackathonId,
        user_id: uuid(data.user_id), member_count: 1, team_version: 1 } };
    }, signal, { name: body.name }, csrf, 201, key);
  },
  hackathons: (cursor: string | null, signal?: AbortSignal) => request('/api/hackathons' + query(cursor), value => page(value, hackathon), signal),
  teams: (id: string, cursor: string | null, signal?: AbortSignal) => request(scope(id) + '/teams' + query(cursor), value => page(value, item => team(item, id)), signal),
  team: (id: string, teamId: string, signal?: AbortSignal) => request(scope(id) + '/teams/' + uuid(teamId), value => {
    const result = team(value, id);
    if (result.id !== teamId) throw new ApiError(0, 'invalid_response');
    return result;
  }, signal),
  myTeam: (id: string, signal?: AbortSignal) => request(scope(id) + '/me/team', value => {
    const v = object(value);
    return v.team === null ? null : team(v.team, id);
  }, signal),
};

export function errorMessage(error: ApiError): string {
  if (error.status === 401) return error.code === 'invalid_credentials' ? 'Username or password is incorrect.' : 'Your session has ended. Sign in again.';
  if (error.status === 403) return 'This request was denied. Check the application origin or restore your session before trying again.';
  if (error.status === 404) return 'This hackathon or team is no longer available. Refresh the list.';
  if (error.status === 409) {
    if (error.code === 'username_unavailable') return 'That username is unavailable. Choose another.';
    if (error.code === 'profile_changed') return 'Your profile changed. Reload it before editing again.';
    if (error.code === 'ranking_changed') return 'Teammate rankings changed. Restart from the first page.';
    return 'This action conflicts with the current state. Refresh and check before trying again.';
  }
  if (error.status === 422) return 'The request is invalid. Check the form or restart pagination.';
  if (error.status === 429) return 'Too many attempts. Please wait before trying again.';
  if (error.status === 503) return error.retryable ? 'The service is busy. You can try again shortly.' : 'The service is unavailable. Try again later.';
  if (error.code === 'invalid_response') return 'An unexpected response was received. Please try again later.';
  return 'We could not reach Merge. Check your connection and try again.';
}

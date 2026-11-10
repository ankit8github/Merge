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

async function request<T>(path: string, parse: (value: unknown) => T,
                          signal?: AbortSignal, body?: unknown, csrf?: string, expectedStatus = 200,
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
    if (response.status !== expectedStatus) throw new ApiError(0, 'invalid_response');
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
export const api = {
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
  if (error.status === 409) return 'That username is unavailable. Choose another.';
  if (error.status === 422) return 'The request is invalid. Check the form or restart pagination.';
  if (error.status === 429) return 'Too many attempts. Please wait before trying again.';
  if (error.status === 503) return error.retryable ? 'The service is busy. You can try again shortly.' : 'The service is unavailable. Try again later.';
  if (error.code === 'invalid_response') return 'An unexpected response was received. Please try again later.';
  return 'We could not reach Merge. Check your connection and try again.';
}

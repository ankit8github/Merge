import { useEffect, useReducer, useRef } from 'react';
import { api, ApiError, type Session } from '../api';

type Scope = { session: Session; epoch: number; signal: AbortSignal };
export type Creation = {
  name: string; key: string; status: 'pending' | 'unresolved' | 'rejected' | 'success' | 'assigned';
  uncertain: boolean; error: ApiError | null;
};
export type TeamCreation = ReturnType<typeof useTeamCreation>;

export function validTeamName(name: string): boolean {
  const characters = Array.from(name);
  return characters.length >= 1 && characters.length <= 120 && !!name.replace(/ /g, '') &&
    !characters.some(char => char === '\0' || /^[\uD800-\uDFFF]$/.test(char));
}

function newKey(): string {
  // No weak/time-based fallback. Keys are not credentials, but must not collide.
  const bytes = new Uint8Array(32);
  globalThis.crypto.getRandomValues(bytes);
  return Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
}

/** App-lifetime account-scoped commands; only active requests reference session CSRF. */
export function useTeamCreation(scope: Scope | null, onExpired: () => void) {
  const commands = useRef(new Map<string, Creation>());
  const requests = useRef(new Map<string, { cancel: () => void; scope: Scope }>());
  const current = useRef(scope);
  current.current = scope;
  const alive = useRef(true);
  const [, render] = useReducer(value => value + 1, 0);
  const publish = (id: string, command: Creation) => {
    commands.current.set(id, command);
    if (alive.current) render();
  };
  const sameScope = (a: Scope, b: Scope | null) => b !== null && a.epoch === b.epoch &&
    a.session.identity.user_id === b.session.identity.user_id && a.signal === b.signal && !a.signal.aborted;

  useEffect(() => {
    for (const request of requests.current.values()) {
      if (!sameScope(request.scope, current.current)) request.cancel();
    }
  }, [scope?.epoch, scope?.signal]);
  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; for (const request of requests.current.values()) request.cancel(); };
  }, []);
  const outstanding = Array.from(commands.current.values()).some(c => c.status === 'pending' || c.uncertain);
  useEffect(() => {
    if (!outstanding) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [outstanding]);

  function operation(hackathon: string): Creation | null {
    return scope ? commands.current.get(`${scope.session.identity.user_id}:${hackathon}`) ?? null : null;
  }
  function submit(hackathon: string, name: string, workspace: AbortSignal | undefined) {
    const owner = current.current;
    if (!owner || owner.signal.aborted || !workspace || workspace.aborted || !validTeamName(name)) return;
    const id = `${owner.session.identity.user_id}:${hackathon}`, previous = commands.current.get(id);
    if (previous && ['pending', 'success', 'assigned'].includes(previous.status)) return;
    if (previous?.error && previous.error.retryAt > Date.now()) return;
    if (previous?.uncertain && previous.name !== name) return;
    let key: string;
    try { key = previous?.name === name && previous.key ? previous.key : newKey(); }
    catch {
      publish(id, { name, key: '', status: 'rejected', uncertain: false, error: new ApiError(0, 'secure_random_unavailable') });
      return;
    }
    const command: Creation = { name, key, status: 'pending', uncertain: previous?.uncertain ?? false, error: null };
    const controller = new AbortController();
    let finished = false;
    const detach = () => { owner.signal.removeEventListener('abort', cancel); requests.current.delete(id); };
    const cancel = () => {
      if (finished) return;
      finished = true; controller.abort(); detach();
      // Abort cannot prove a synchronous service/transaction stopped.
      publish(id, { ...command, status: 'unresolved', uncertain: true, error: new ApiError() });
    };
    requests.current.set(id, { cancel, scope: owner });
    owner.signal.addEventListener('abort', cancel, { once: true });
    publish(id, command); // Ref guard precedes React rendering: double-click cannot POST twice.
    void api.createTeam(hackathon, { name }, key, owner.session.csrf_token, controller.signal).then(reply => {
      if (finished || !sameScope(owner, current.current) || !alive.current) return;
      if (reply.data.user_id !== owner.session.identity.user_id) throw new ApiError(0, 'invalid_response');
      finished = true; detach();
      publish(id, { ...command, status: 'success', uncertain: false });
    }).catch((error: unknown) => {
      if (finished || !sameScope(owner, current.current) || !alive.current) return;
      finished = true; detach();
      const failure = error instanceof ApiError ? error : new ApiError();
      const assigned = failure.status === 409 && failure.code === 'already_assigned';
      // A status alone (e.g. proxy HTML at 400) is not rollback evidence. Only
      // documented pre-mutation status/code pairs permit a new edited command.
      const definite = ([400, 422].includes(failure.status) && failure.code === 'invalid_request') ||
        (failure.status === 401 && failure.code === 'invalid_session') ||
        (failure.status === 403 && ['invalid_csrf', 'origin_rejected', 'client_identity_rejected', 'https_required'].includes(failure.code)) ||
        (failure.status === 429 && failure.code === 'rate_limited');
      const uncertain = !assigned && (command.uncertain || !definite);
      publish(id, { ...command, status: assigned ? 'assigned' : uncertain ? 'unresolved' : 'rejected', uncertain, error: failure });
      if (failure.status === 401 && !workspace.aborted) onExpired();
    });
  }
  return { operation, submit };
}

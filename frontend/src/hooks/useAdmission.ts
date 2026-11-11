import { useEffect, useReducer, useRef } from 'react';
import { api, ApiError, type Decision, type Session } from '../api';

type Scope = { session: Session; epoch: number; signal: AbortSignal };
export type AdmissionCommand = {
  requestId?: string; decision?: Decision; key: string;
  status: 'pending' | 'unresolved' | 'rejected' | 'success'; uncertain: boolean; error: ApiError | null;
};
export type Admission = ReturnType<typeof useAdmission>;

// Commands contain no session/CSRF or applicant data. Only active transports
// reference a session. App lifetime preserves original commands after navigation.
export function useAdmission(scope: Scope | null, onExpired: () => void) {
  const journal = useRef(new Map<string, AdmissionCommand>());
  const versions = useRef(new Map<string, number>());
  const active = useRef(new Map<string, () => void>());
  const current = useRef(scope); current.current = scope;
  const alive = useRef(true);
  const [, render] = useReducer(value => value + 1, 0);
  const publish = (id: string, command: AdmissionCommand) => {
    journal.current.set(id, command); if (alive.current) render();
  };
  const prefix = (owner: Scope, h: string, t = '') => `${owner.session.identity.user_id}:${h}:${t}`;
  const isCurrent = (owner: Scope) => !!current.current && !owner.signal.aborted &&
    owner.signal === current.current.signal && owner.epoch === current.current.epoch &&
    owner.session.identity.user_id === current.current.session.identity.user_id;
  const invalidate = (owner: Scope, h: string) => {
    const id = prefix(owner, h); versions.current.set(id, (versions.current.get(id) ?? 0) + 1);
    if (alive.current) render();
  };
  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; for (const cancel of [...active.current.values()]) cancel(); };
  }, []);
  const outstanding = [...journal.current.values()].some(c => c.status === 'pending' || c.uncertain);
  useEffect(() => {
    if (!outstanding) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [outstanding]);

  function operation(h: string, t: string, requestId?: string) {
    return scope ? journal.current.get(prefix(scope, h, t) + ':' + (requestId ?? 'mine')) ?? null : null;
  }
  function submit(h: string, t: string, requestId?: string, decision?: Decision) {
    const owner = current.current;
    if (!owner || owner.signal.aborted || (!!requestId !== !!decision)) return;
    const id = prefix(owner, h, t) + ':' + (requestId ?? 'mine'), previous = journal.current.get(id);
    if (previous?.status === 'pending' || previous?.status === 'success' || (previous?.error?.retryAt ?? 0) > Date.now()) return;
    if (previous?.uncertain && previous.decision !== decision) return;
    let key = previous && previous.decision === decision ? previous.key : '';
    try {
      if (!key) {
        const bytes = new Uint8Array(32); globalThis.crypto.getRandomValues(bytes);
        key = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
      }
    } catch {
      publish(id, { requestId, decision, key: '', status: 'rejected', uncertain: false, error: new ApiError(0, 'secure_random_unavailable') });
      return;
    }
    const command: AdmissionCommand = { requestId, decision, key, status: 'pending', uncertain: previous?.uncertain ?? false, error: null };
    const controller = new AbortController(); let finished = false;
    const detach = () => { owner.signal.removeEventListener('abort', cancel); active.current.delete(id); };
    const cancel = () => {
      if (finished) return;
      finished = true; controller.abort(); detach();
      publish(id, { ...command, status: 'unresolved', uncertain: true, error: new ApiError() });
    };
    active.current.set(id, cancel); owner.signal.addEventListener('abort', cancel, { once: true });
    publish(id, command); // Synchronous guard, before the next React render.
    const promise = requestId && decision
      ? api.decideRequest(h, t, requestId, decision, key, owner.session.csrf_token, controller.signal)
      : api.createRequest(h, t, key, owner.session.csrf_token, controller.signal);
    void promise.then(row => {
      if (finished || !alive.current || !isCurrent(owner)) return;
      if (!requestId && row.requester_id !== owner.session.identity.user_id) throw new ApiError(0, 'invalid_response');
      finished = true; detach();
      publish(id, { ...command, status: 'success', uncertain: false });
      invalidate(owner, h); // Canonical reads, never synthesize membership/status.
    }).catch((error: unknown) => {
      if (finished || !alive.current || !isCurrent(owner)) return;
      finished = true; detach();
      const failure = error instanceof ApiError ? error : new ApiError();
      const definite = ([400, 422].includes(failure.status) && failure.code === 'invalid_request') ||
        (failure.status === 401 && failure.code === 'invalid_session') ||
        (failure.status === 403 && ['forbidden', 'invalid_csrf', 'origin_rejected', 'client_identity_rejected', 'https_required'].includes(failure.code)) ||
        (failure.status === 404 && ['request_not_found', 'team_not_found'].includes(failure.code)) ||
        (failure.status === 409 && ['team_full', 'already_assigned', 'request_resolved'].includes(failure.code)) ||
        (failure.status === 429 && failure.code === 'rate_limited');
      const uncertain = command.uncertain || !definite;
      publish(id, { ...command, status: uncertain ? 'unresolved' : 'rejected', uncertain, error: failure });
      if (failure.status === 401) onExpired();
      else if ([403, 404, 409].includes(failure.status)) invalidate(owner, h);
    });
  }
  return {
    actor: scope?.session.identity.user_id ?? '', operation, submit,
    revision: (h: string) => scope ? versions.current.get(prefix(scope, h)) ?? 0 : 0,
    refresh: (h: string) => { if (current.current && !current.current.signal.aborted) invalidate(current.current, h); },
    decisions: (h: string, t: string) => scope ? [...journal.current.entries()]
      .filter(([id, command]) => id.startsWith(prefix(scope, h, t) + ':') && !!command.requestId).map(([, command]) => command) : [],
  };
}

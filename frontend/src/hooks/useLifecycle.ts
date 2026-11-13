import { useEffect, useReducer, useRef } from 'react';
import { api, ApiError, type Session } from '../api';

type Scope = { session: Session; epoch: number; signal: AbortSignal };
export type LifecycleCommand = { kind: 'leave' | 'remove'; hackathon: string; team: string; subject: string; key: string;
  status: 'pending' | 'unresolved' | 'rejected' | 'success'; uncertain: boolean; error: ApiError | null };
export type Lifecycle = ReturnType<typeof useLifecycle>;

// Same App-lifetime, account-bound memory journal as other domain commands.
export function useLifecycle(scope: Scope | null, onExpired: () => void) {
  const journal = useRef(new Map<string, LifecycleCommand>());
  const versions = useRef(new Map<string, number>()), active = useRef(new Map<string, () => void>());
  const current = useRef(scope); current.current = scope;
  const alive = useRef(true); const [, render] = useReducer(n => n + 1, 0);
  const prefix = (owner: Scope, h: string) => `${owner.session.identity.user_id}:${h}:`;
  const idFor = (owner: Scope, kind: string, h: string, t: string, subject: string) => prefix(owner, h) + `${t}:${kind}:${subject}`;
  const publish = (id: string, value: LifecycleCommand) => { journal.current.set(id, value); if (alive.current) render(); };
  const valid = (owner: Scope) => current.current?.signal === owner.signal && current.current?.epoch === owner.epoch &&
    current.current?.session.identity.user_id === owner.session.identity.user_id && !owner.signal.aborted;
  const refresh = (owner: Scope, h: string) => {
    const id = prefix(owner, h); versions.current.set(id, (versions.current.get(id) ?? 0) + 1);
    if (alive.current) render();
  };
  useEffect(() => { alive.current = true; return () => { alive.current = false; for (const cancel of [...active.current.values()]) cancel(); }; }, []);
  const outstanding = [...journal.current.values()].some(c => c.status === 'pending' || c.uncertain);
  useEffect(() => {
    if (!outstanding) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn); return () => window.removeEventListener('beforeunload', warn);
  }, [outstanding]);
  function operation(kind: 'leave' | 'remove', h: string, t: string, subject: string) {
    return scope ? journal.current.get(idFor(scope, kind, h, t, subject)) ?? null : null;
  }
  function submit(kind: 'leave' | 'remove', h: string, t: string, subject: string, workspace: AbortSignal | undefined, retry = false) {
    const owner = current.current;
    if (!owner || owner.signal.aborted || !workspace || workspace.aborted ||
        (kind === 'leave' ? subject !== owner.session.identity.user_id : subject === owner.session.identity.user_id)) return;
    const id = idFor(owner, kind, h, t, subject), previous = journal.current.get(id);
    if (previous?.status === 'pending' || (previous?.error?.retryAt ?? 0) > Date.now()) return;
    if (retry ? !previous || previous.status === 'success' : previous?.uncertain) return;
    let key = retry || previous?.status === 'rejected' ? previous?.key ?? '' : '';
    try {
      if (!key) { const bytes = new Uint8Array(32); crypto.getRandomValues(bytes); key = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join(''); }
    } catch {
      publish(id, { kind, hackathon: h, team: t, subject, key: '', status: 'rejected', uncertain: false, error: new ApiError(0, 'secure_random_unavailable') }); return;
    }
    const command: LifecycleCommand = { kind, hackathon: h, team: t, subject, key, status: 'pending', uncertain: previous?.uncertain ?? false, error: null };
    const controller = new AbortController(); let finished = false;
    const detach = () => { owner.signal.removeEventListener('abort', cancel); active.current.delete(id); };
    const cancel = () => {
      if (finished) return;
      finished = true; controller.abort(); detach(); publish(id, { ...command, status: 'unresolved', uncertain: true, error: new ApiError() });
    };
    active.current.set(id, cancel); owner.signal.addEventListener('abort', cancel, { once: true }); publish(id, command);
    void api.lifecycle(kind, h, t, subject, key, owner.session.csrf_token, controller.signal).then(() => {
      if (finished || !alive.current || !valid(owner)) return;
      finished = true; detach(); publish(id, { ...command, status: 'success', uncertain: false });
      if (!workspace.aborted) refresh(owner, h);
    }).catch((error: unknown) => {
      if (finished || !alive.current || !valid(owner)) return;
      finished = true; detach(); const failure = error instanceof ApiError ? error : new ApiError();
      const definite = (failure.status === 401 && failure.code === 'invalid_session') ||
        (failure.status === 403 && ['forbidden', 'invalid_csrf', 'origin_rejected', 'client_identity_rejected', 'https_required'].includes(failure.code)) ||
        (failure.status === 404 && failure.code === 'team_not_found') ||
        (failure.status === 409 && failure.code === 'member_not_found') ||
        (failure.status === 422 && ['invalid_request', 'use_leave'].includes(failure.code));
      const uncertain = command.uncertain || !definite;
      publish(id, { ...command, status: uncertain ? 'unresolved' : 'rejected', uncertain, error: failure });
      if (!workspace.aborted) { if (failure.status === 401) onExpired(); else if (definite) refresh(owner, h); }
    });
  }
  return { actor: scope?.session.identity.user_id ?? '', operation, submit,
    commands: (h: string) => scope ? [...journal.current.entries()].filter(([id]) => id.startsWith(prefix(scope, h))).map(([, c]) => c) : [],
    revision: (h: string) => scope ? versions.current.get(prefix(scope, h)) ?? 0 : 0 };
}

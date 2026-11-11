import { useEffect, useReducer, useRef } from 'react';
import { api, ApiError, type Session } from '../api';

type Scope = { session: Session; epoch: number; signal: AbortSignal };
export type InvitationCommand = Readonly<{
  kind: 'issue' | 'redeem'; hackathon: string; team: string; target: string; key: string;
  status: 'pending' | 'unresolved' | 'rejected' | 'success'; uncertain: boolean; error: ApiError | null;
}>;
export type Invitations = ReturnType<typeof useInvitations>;
export const validRecipient = (value: string) => /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(value);

// App lifetime, account-scoped commands only. No session, CSRF or inbox DTOs are
// retained in this journal. Transport cancellation never establishes rollback.
export function useInvitations(scope: Scope | null, onExpired: () => void) {
  const journal = useRef(new Map<string, InvitationCommand>());
  const versions = useRef(new Map<string, number>());
  const active = useRef(new Map<string, () => void>());
  const current = useRef(scope); current.current = scope;
  const alive = useRef(true);
  const [, render] = useReducer(n => n + 1, 0);
  const prefix = (owner: Scope, h: string) => `${owner.session.identity.user_id}:${h}:`;
  const idFor = (owner: Scope, kind: 'issue' | 'redeem', h: string, t: string, target: string) =>
    prefix(owner, h) + t + ':' + kind + ':' + (kind === 'issue' ? '' : target);
  const publish = (id: string, command: InvitationCommand) => {
    journal.current.set(id, command); if (alive.current) render();
  };
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

  function operation(kind: 'issue' | 'redeem', h: string, t: string, target = '') {
    return scope ? journal.current.get(idFor(scope, kind, h, t, target)) ?? null : null;
  }
  function submit(kind: 'issue' | 'redeem', h: string, t: string, target: string, workspace: AbortSignal | undefined) {
    const owner = current.current;
    if (!owner || owner.signal.aborted || !workspace || workspace.aborted || !validRecipient(target)) return;
    const id = idFor(owner, kind, h, t, target), previous = journal.current.get(id);
    if (previous?.status === 'pending' || previous?.status === 'success' || (previous?.error?.retryAt ?? 0) > Date.now()) return;
    if (previous?.uncertain && previous.target !== target) return;
    let key = previous?.target === target ? previous.key : '';
    try {
      if (!key) {
        const bytes = new Uint8Array(32); globalThis.crypto.getRandomValues(bytes);
        key = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
      }
    } catch {
      publish(id, { kind, hackathon: h, team: t, target, key: '', status: 'rejected', uncertain: false, error: new ApiError(0, 'secure_random_unavailable') });
      return;
    }
    const command: InvitationCommand = { kind, hackathon: h, team: t, target, key, status: 'pending', uncertain: previous?.uncertain ?? false, error: null };
    const controller = new AbortController(); let finished = false;
    const detach = () => { owner.signal.removeEventListener('abort', cancel); active.current.delete(id); };
    const cancel = () => {
      if (finished) return;
      finished = true; controller.abort(); detach();
      publish(id, { ...command, status: 'unresolved', uncertain: true, error: new ApiError() });
    };
    active.current.set(id, cancel); owner.signal.addEventListener('abort', cancel, { once: true });
    publish(id, command); // Guard synchronously, before another click can submit.
    const promise = kind === 'issue'
      ? api.issueInvitation(h, t, target, key, owner.session.csrf_token, controller.signal)
      : api.redeemInvitation(h, t, target, key, owner.session.csrf_token, controller.signal);
    void promise.then(row => {
      if (finished || !alive.current || !isCurrent(owner)) return;
      if ((kind === 'issue' ? row.issued_by : row.recipient_id) !== owner.session.identity.user_id) throw new ApiError(0, 'invalid_response');
      finished = true; detach();
      publish(id, { ...command, status: 'success', uncertain: false });
      if (!workspace.aborted) invalidate(owner, h); // Only refresh the originating workspace.
    }).catch((error: unknown) => {
      if (finished || !alive.current || !isCurrent(owner)) return;
      finished = true; detach();
      const failure = error instanceof ApiError ? error : new ApiError();
      const definite = ([400, 422].includes(failure.status) && failure.code === 'invalid_request') ||
        (failure.status === 401 && failure.code === 'invalid_session') ||
        (failure.status === 403 && ['forbidden', 'invalid_csrf', 'origin_rejected', 'client_identity_rejected', 'https_required'].includes(failure.code)) ||
        (failure.status === 404 && ['recipient_not_found', 'invitation_not_found', 'team_not_found'].includes(failure.code)) ||
        (failure.status === 409 && ['team_full', 'already_assigned', 'invitation_expired', 'invitation_stale', 'invitation_redeemed'].includes(failure.code)) ||
        (failure.status === 429 && failure.code === 'rate_limited');
      const uncertain = command.uncertain || !definite;
      publish(id, { ...command, status: uncertain ? 'unresolved' : 'rejected', uncertain, error: failure });
      if (!workspace.aborted) {
        if (failure.status === 401) onExpired();
        else if ([403, 404, 409].includes(failure.status)) invalidate(owner, h);
      }
    });
  }
  return {
    actor: scope?.session.identity.user_id ?? '', operation, submit,
    newIssue: (h: string, t: string) => {
      const owner = current.current;
      if (!owner || owner.signal.aborted) return;
      const id = idFor(owner, 'issue', h, t, ''), saved = journal.current.get(id);
      if (saved?.status === 'success') { journal.current.delete(id); render(); }
    },
    redemptions: (h: string) => scope ? [...journal.current.entries()]
      .filter(([id, c]) => id.startsWith(prefix(scope, h)) && c.kind === 'redeem').map(([, c]) => c) : [],
    revision: (h: string) => scope ? versions.current.get(prefix(scope, h)) ?? 0 : 0,
    refresh: (h: string) => { const owner = current.current; if (owner && !owner.signal.aborted) invalidate(owner, h); },
  };
}

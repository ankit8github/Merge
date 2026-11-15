import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError, type Session } from '../api';

type State = { status: 'checking' } | { status: 'guest'; message?: string } |
  { status: 'error'; error: ApiError } | { status: 'authenticated'; session: Session; epoch: number; signal: AbortSignal } |
  { status: 'ending'; session: Session; error: ApiError | null };

export function useSession() {
  const [state, setState] = useState<State>({ status: 'checking' });
  const visible = useRef<State>(state);
  const current = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const pending = useRef<{ controller: AbortController; version: number; queued: boolean } | null>(null);
  const publish = useCallback((next: State) => { visible.current = next; setState(next); }, []);
  const start = useCallback(() => {
    pending.current?.controller.abort();
    pending.current = null;
    current.current?.abort();
    const controller = new AbortController();
    current.current = controller;
    return { controller, version: ++generation.current };
  }, []);
  const expired = useCallback(() => {
    start(); publish({ status: 'guest', message: 'Your session has ended. Sign in again.' });
  }, [start, publish]);
  const accept = useCallback((session: Session) => {
    const { version, controller } = start();
    if (Date.parse(session.expires_at) <= Date.now()) return expired();
    publish({ status: 'authenticated', session, epoch: version, signal: controller.signal });
  }, [start, expired, publish]);
  const check = useCallback(function check() {
    const ticket = { controller: new AbortController(), version: generation.current, queued: false };
    pending.current = ticket;
    const owned = () => pending.current === ticket && generation.current === ticket.version && !ticket.controller.signal.aborted;
    void api.session(ticket.controller.signal).then(session => {
      if (!owned() || ticket.queued) return;
      const previous = visible.current;
      // A validated unchanged session is not a new authentication lifetime.
      // Different credentials (even for the same account) cancel old transports.
      if (previous.status === 'authenticated' && Date.parse(session.expires_at) > Date.now() &&
          previous.session.identity.user_id === session.identity.user_id &&
          previous.session.csrf_token === session.csrf_token &&
          Date.parse(previous.session.expires_at) === Date.parse(session.expires_at)) {
        publish({ ...previous, session });
      } else accept(session);
    }).catch((error: unknown) => {
      if (!owned()) return;
      const failure = error instanceof ApiError ? error : new ApiError();
      // A queued event cannot conceal a real denial of the current scope. Only
      // a replaced scope/ticket may fence an old 401/403 as genuinely stale.
      if (ticket.queued && failure.status !== 401 && failure.status !== 403) return;
      const authenticated = visible.current.status === 'authenticated';
      // All failed checks still fail closed, including Origin/CSRF/transport errors.
      start();
      if (failure.status === 401) publish({ status: 'guest', ...(authenticated ? { message: 'Your session has ended. Sign in again.' } : {}) });
      else publish({ status: 'error', error: failure });
    }).finally(() => {
      if (!owned()) return;
      pending.current = null;
      // New lifecycle events supersede this observation, but share one trailing
      // check rather than repeatedly aborting/restarting overlapping requests.
      if (ticket.queued) check();
    });
  }, [accept, publish, start]);
  const restore = useCallback(() => {
    start(); publish({ status: 'checking' }); // Explicit recovery discards private views.
    check();
  }, [start, publish, check]);
  const revalidate = useCallback(() => {
    if (visible.current.status !== 'authenticated' && visible.current.status !== 'checking') return;
    // A suspended tab can resume before its throttled expiry timer is serviced.
    if (visible.current.status === 'authenticated' && Date.parse(visible.current.session.expires_at) <= Date.now()) {
      expired(); return;
    }
    if (pending.current) pending.current.queued = true;
    else check();
  }, [check, expired]);
  const logout = useCallback((session: Session) => {
    const { controller, version } = start();
    publish({ status: 'ending', session, error: null });
    void api.logout(session.csrf_token, controller.signal).then(() => {
      if (generation.current === version && !controller.signal.aborted) publish({ status: 'guest', message: 'You have signed out.' });
    }).catch((error: ApiError) => {
      if (generation.current !== version || controller.signal.aborted) return;
      if (error.status === 401) publish({ status: 'guest', message: 'Your session has ended.' });
      else publish({ status: 'ending', session, error });
    });
  }, [start, publish]);
  useEffect(() => { restore(); return () => { generation.current++; current.current?.abort(); pending.current?.controller.abort(); pending.current = null; }; }, [restore]);
  useEffect(() => {
    const events = ['focus', 'pageshow', 'popstate'] as const;
    for (const event of events) window.addEventListener(event, revalidate);
    const visibility = () => { if (document.visibilityState === 'visible') revalidate(); };
    document.addEventListener('visibilitychange', visibility);
    return () => {
      for (const event of events) window.removeEventListener(event, revalidate);
      document.removeEventListener('visibilitychange', visibility);
    };
  }, [revalidate]);
  useEffect(() => {
    if (state.status !== 'authenticated') return;
    const timer = window.setTimeout(expired, Math.max(0, Math.min(2147483647, Date.parse(state.session.expires_at) - Date.now())));
    return () => window.clearTimeout(timer);
  }, [state, expired]);
  return { state, accept, expired, restore, logout };
}

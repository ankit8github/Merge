import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError, type Session } from '../api';

type State = { status: 'checking' } | { status: 'guest'; message?: string } |
  { status: 'error'; error: ApiError } | { status: 'authenticated'; session: Session; epoch: number; signal: AbortSignal } |
  { status: 'ending'; session: Session; error: ApiError | null };

export function useSession() {
  const [state, setState] = useState<State>({ status: 'checking' });
  const current = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const start = useCallback(() => {
    current.current?.abort();
    const controller = new AbortController();
    current.current = controller;
    return { controller, version: ++generation.current };
  }, []);
  const expired = useCallback(() => {
    start(); setState({ status: 'guest', message: 'Your session has ended. Sign in again.' });
  }, [start]);
  const accept = useCallback((session: Session) => {
    const { version, controller } = start();
    if (Date.parse(session.expires_at) <= Date.now()) return expired();
    setState({ status: 'authenticated', session, epoch: version, signal: controller.signal });
  }, [start, expired]);
  const restore = useCallback(() => {
    const { controller, version } = start();
    setState({ status: 'checking' }); // Unmount and discard authenticated data.
    void api.session(controller.signal).then(session => {
      if (generation.current === version && !controller.signal.aborted) accept(session);
    }).catch((error: ApiError) => {
      if (generation.current !== version || controller.signal.aborted) return;
      if (error.status === 401) setState({ status: 'guest' });
      else setState({ status: 'error', error });
    });
  }, [start, accept]);
  const logout = useCallback((session: Session) => {
    const { controller, version } = start();
    setState({ status: 'ending', session, error: null });
    void api.logout(session.csrf_token, controller.signal).then(() => {
      if (generation.current === version && !controller.signal.aborted) setState({ status: 'guest', message: 'You have signed out.' });
    }).catch((error: ApiError) => {
      if (generation.current !== version || controller.signal.aborted) return;
      if (error.status === 401) setState({ status: 'guest', message: 'Your session has ended.' });
      else setState({ status: 'ending', session, error });
    });
  }, [start]);
  useEffect(() => { restore(); return () => { generation.current++; current.current?.abort(); }; }, [restore]);
  useEffect(() => {
    if (state.status !== 'authenticated') return;
    const timer = window.setTimeout(expired, Math.max(0, Math.min(2147483647, Date.parse(state.session.expires_at) - Date.now())));
    const focus = () => restore(); // A different tab may revoke or replace the cookie.
    window.addEventListener('focus', focus); window.addEventListener('pageshow', focus);
    return () => { window.clearTimeout(timer); window.removeEventListener('focus', focus); window.removeEventListener('pageshow', focus); };
  }, [state, expired, restore]);
  return { state, accept, expired, restore, logout };
}

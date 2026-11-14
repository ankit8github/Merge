import { createContext, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api';

// Read invalidation only. Command journals and workspace ownership are separate.
export const ReadInvalidation = createContext(0);

export function useRealtime(hackathon: string, actor: string, sessionSignal: AbortSignal, onExpired: () => void) {
  const stopCurrent = useRef<(() => void) | null>(null);
  // Fence queued old callbacks in the same commit, before passive cleanup.
  useLayoutEffect(() => () => { stopCurrent.current?.(); }, [hackathon, actor, sessionSignal, onExpired]);
  const [revision, setRevision] = useState(0);
  const [status, setStatus] = useState<'connecting' | 'connected' | 'reconnecting' | 'unavailable'>('connecting');
  useEffect(() => {
    if (typeof EventSource !== 'function') { setStatus('unavailable'); return; }
    let active = true, source: EventSource | null = null, timer: ReturnType<typeof setTimeout> | undefined;
    let delay = 2000, previous = '';
    const probe = new AbortController();
    const owned = () => active && !sessionSignal.aborted;
    const close = () => { source?.close(); source = null; };
    const expire = () => { if (owned()) { close(); onExpired(); } };
    const retry = () => {
      close();
      if (!owned() || timer !== undefined) return;
      setStatus('reconnecting');
      timer = setTimeout(() => {
        timer = undefined;
        void api.session(probe.signal).then(session => {
          if (!owned()) return;
          if (session.identity.user_id !== actor) { expire(); return; }
          connect();
        }).catch((error: unknown) => {
          if (!owned()) return;
          if (error instanceof ApiError && error.status === 401) expire(); else retry();
        });
      }, delay);
      delay = Math.min(30000, delay * 2);
    };
    const connect = () => {
      if (!owned()) return;
      let current: EventSource;
      try { current = new EventSource(`/api/hackathons/${hackathon}/events`); }
      catch { retry(); return; }
      source = current; previous = '';
      const receive = (kind: 'reset' | 'invalidate' | 'expired' | 'unavailable') => (event: Event) => {
        if (!owned() || source !== current) return;
        const message = event as MessageEvent<string>;
        try {
          if (message.data.length > 512) throw new Error();
          const value = JSON.parse(message.data) as Record<string, unknown>;
          if (!value || Object.keys(value).sort().join(',') !== 'hackathon_id,schema_version,user_id' ||
              value.schema_version !== 1 || value.hackathon_id !== hackathon) throw new Error();
          if (value.user_id !== actor) { expire(); return; }
          if (kind === 'expired') { expire(); return; }
          if (kind === 'unavailable') { retry(); return; }
          if (!/^[0-9a-f]{64}$/.test(message.lastEventId)) throw new Error();
          setStatus('connected'); delay = 2000;
          if (kind === 'reset' || previous !== message.lastEventId) setRevision(n => n + 1);
          previous = message.lastEventId;
        } catch { retry(); }
      };
      for (const kind of ['reset', 'invalidate', 'expired', 'unavailable'] as const) current.addEventListener(kind, receive(kind));
      current.onerror = () => { if (owned() && source === current) retry(); };
    };
    const stop = () => { active = false; close(); probe.abort(); if (timer !== undefined) clearTimeout(timer); };
    stopCurrent.current = stop;
    sessionSignal.addEventListener('abort', stop, { once: true });
    setStatus('connecting'); connect();
    return () => { stop(); if (stopCurrent.current === stop) stopCurrent.current = null; sessionSignal.removeEventListener('abort', stop); };
  }, [hackathon, actor, sessionSignal, onExpired]);
  return { revision, status };
}

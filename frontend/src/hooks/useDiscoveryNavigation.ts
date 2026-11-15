import { useCallback, useLayoutEffect, useRef, useState } from 'react';
import { canonicalUuid } from '../api';

export type Navigation = {
  hackathon: string | null; catalog: (string | null)[]; teams: (string | null)[];
  view: 'discover' | 'mine' | 'invitations'; detail: string | null;
};
export type UpdateNavigation = (value: Navigation | ((current: Navigation) => Navigation), push?: boolean) => void;
type Record = { version: 1; owner: string | null; generation: number; value: Navigation };
export const NAVIGATION_KEY = 'merge.discovery.v1';
const HISTORY_KEY = 'mergeDiscovery';
export const emptyNavigation = (): Navigation => ({ hackathon: null, catalog: [null], teams: [null], view: 'discover', detail: null });

// Only public navigation hints are serializable. No response DTOs, commands,
// session, CSRF, idempotency keys or mutation display tokens enter either store.
function parse(value: unknown): Record | null {
  try {
    const r = value as Record, n = r.value;
    const id = (v: unknown) => typeof v === 'string' && canonicalUuid(v) === v;
    const cursors = (v: unknown): v is (string | null)[] => Array.isArray(v) && v.length > 0 && v.length <= 2048 && v[0] === null && v.slice(1).every(id);
    if (r.version !== 1 || !(r.owner === null || id(r.owner)) || !Number.isSafeInteger(r.generation) || r.generation < 0 ||
        !(n.hackathon === null || id(n.hackathon)) || !(n.detail === null || id(n.detail)) ||
        !['discover', 'mine', 'invitations'].includes(n.view) || !cursors(n.catalog) || !cursors(n.teams) ||
        (n.hackathon === null && (n.detail !== null || n.view !== 'discover' || n.teams.length !== 1)) ||
        (n.detail !== null && n.view !== 'discover')) return null;
    return { version: 1, owner: r.owner, generation: r.generation, value: {
      hackathon: n.hackathon, catalog: [...n.catalog], teams: [...n.teams], view: n.view, detail: n.detail,
    } };
  } catch { return null; }
}
function read(): Record | null {
  try {
    const text = window.sessionStorage.getItem(NAVIGATION_KEY);
    return text && text.length <= 256000 ? parse(JSON.parse(text)) : null;
  } catch { return null; }
}
function save(record: Record, push = false) {
  try { window.sessionStorage.setItem(NAVIGATION_KEY, JSON.stringify(record)); } catch { /* Navigation still works without storage. */ }
  try {
    // This app has no other history-state owner. Do not copy unknown fields.
    const state = { [HISTORY_KEY]: record };
    if (push) window.history.pushState(state, '');
    else window.history.replaceState(state, '');
  } catch { /* History can be unavailable or rate-limited. */ }
}

// undefined = blocking identity check; null = signed out/signing out. Routine
// background checks retain the currently validated owner until their result.
export function useDiscoveryNavigation(owner: string | null | undefined) {
  const [record, setRecord] = useState<Record | null>(read);
  const current = useRef(record); current.current = record;
  useLayoutEffect(() => {
    if (owner === undefined) return;
    const old = current.current;
    if (!old || old.owner !== owner) {
      const next: Record = { version: 1, owner, generation: (old?.generation ?? 0) + 1, value: emptyNavigation() };
      current.current = next; save(next); setRecord(next);
    } else save(old);
  }, [owner]);
  const update = useCallback<UpdateNavigation>((value, push = true) => {
    if (typeof owner !== 'string') return;
    const old = current.current;
    if (!old || old.owner !== owner) return;
    const next = parse({ ...old, value: typeof value === 'function' ? value(old.value) : value });
    if (!next) return;
    current.current = next; save(next, push); setRecord(next);
  }, [owner]);
  useLayoutEffect(() => {
    const pop = (event: PopStateEvent) => {
      if (owner === null) return;
      const old = current.current;
      if (!old || old.owner === null || (owner !== undefined && old.owner !== owner)) return;
      const hint = parse(event.state?.[HISTORY_KEY]);
      // Generation fences keep pre-logout/account-switch history entries dead.
      // While auth is checking, retain only the latest public destination. App
      // remains hidden; a different server-returned owner will discard the hint.
      const next = hint?.owner === old.owner && hint.generation === old.generation ? hint : { ...old, value: emptyNavigation() };
      current.current = next; save(next); setRecord(next);
    };
    window.addEventListener('popstate', pop);
    return () => window.removeEventListener('popstate', pop);
  }, [owner]);
  return { navigation: record && record.owner === owner ? record.value : emptyNavigation(), update };
}

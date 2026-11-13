import { expect } from 'vitest';
import { NAVIGATION_KEY } from '../hooks/useDiscoveryNavigation';

// Navigation persistence is now authorized. Keep the original credential /
// command non-persistence assertions, with an exact public-field allowlist.
export function expectPublicNavigationOnly(storage: { mock: { calls: unknown[][]; contexts: unknown[] } }, ...secrets: string[]) {
  storage.mock.calls.forEach(([key, text], index) => {
    expect(storage.mock.contexts[index]).toBe(window.sessionStorage);
    expect(key).toBe(NAVIGATION_KEY);
    const record = JSON.parse(text as string);
    expect(Object.keys(record).sort()).toEqual(['generation', 'owner', 'value', 'version']);
    expect(record.version).toBe(1);
    expect(Number.isSafeInteger(record.generation)).toBe(true);
    const id = (value: unknown) => expect(value).toMatch(/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/);
    if (record.owner !== null) id(record.owner);
    expect(Object.keys(record.value).sort()).toEqual(['catalog', 'detail', 'hackathon', 'teams', 'view']);
    if (record.value.hackathon !== null) id(record.value.hackathon);
    if (record.value.detail !== null) id(record.value.detail);
    expect(['discover', 'mine', 'invitations']).toContain(record.value.view);
    for (const cursors of [record.value.catalog, record.value.teams]) {
      expect(Array.isArray(cursors)).toBe(true); expect(cursors[0]).toBe(null);
      cursors.slice(1).forEach(id);
    }
    for (const secret of secrets) expect(text).not.toContain(secret);
  });
}

import { useCallback, useLayoutEffect, useRef } from 'react';

export type WorkspaceSignal = () => AbortSignal | undefined;

// A display-ownership token, separate from the session and HTTP transport.
// Rotate only after a committed navigation; speculative renders cannot change it.
export function useWorkspaceSignal(key: string): WorkspaceSignal {
  const current = useRef<{ key: string; controller: AbortController } | null>(null);
  useLayoutEffect(() => {
    const controller = new AbortController();
    const owner = { key, controller }; current.current = owner;
    return () => { controller.abort(); if (current.current === owner) current.current = null; };
  }, [key]);
  return useCallback(() => current.current?.key === key ? current.current.controller.signal : undefined, [key]);
}

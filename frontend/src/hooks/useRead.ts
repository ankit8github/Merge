import { useEffect, useState } from 'react';
import { ApiError } from '../api';

type ReadState<T> = { status: 'loading' } | { status: 'success'; data: T } | { status: 'error'; error: ApiError };
// Each mounted view owns its request. Unmount/navigation cancels and ignores even
// transports that finish after abort, including a stale unauthorized response.
export function useRead<T>(load: (signal: AbortSignal) => Promise<T>, onExpired: () => void) {
  const [state, setState] = useState<ReadState<T>>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setState({ status: 'loading' });
    void load(controller.signal).then(data => {
      if (active) setState({ status: 'success', data });
    }).catch((error: unknown) => {
      if (!active) return;
      const failure = error instanceof ApiError ? error : new ApiError();
      if (failure.status === 401) onExpired();
      else setState({ status: 'error', error: failure });
    });
    return () => { active = false; controller.abort(); };
  }, [load, onExpired, attempt]);
  return { state, retry: () => setAttempt(value => value + 1) };
}

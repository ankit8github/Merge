import { useContext, useEffect, useRef, useState } from 'react';
import { ApiError } from '../api';
import { ReadInvalidation } from './useRealtime';

type ReadState<T> = { status: 'loading' } | { status: 'success'; data: T } | { status: 'error'; error: ApiError };
// Each mounted view owns its request. Unmount/navigation cancels and ignores even
// transports that finish after abort, including a stale unauthorized response.
export function useRead<T>(load: (signal: AbortSignal) => Promise<T>, onExpired: () => void, invalidation?: number) {
  const inherited = useContext(ReadInvalidation);
  const revision = invalidation ?? inherited;
  const [state, setState] = useState<ReadState<T>>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);
  const previous = useRef({ load, onExpired, attempt, revision });
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    // Realtime refresh of this exact read keeps successful content/forms mounted.
    // Changed loaders (scope/navigation/mutations) still hide the old snapshot.
    const old = previous.current;
    if (!(old.load === load && old.onExpired === onExpired && old.attempt === attempt && old.revision !== revision)) {
      setState({ status: 'loading' });
    }
    previous.current = { load, onExpired, attempt, revision };
    void load(controller.signal).then(data => {
      if (active) setState({ status: 'success', data });
    }).catch((error: unknown) => {
      if (!active) return;
      const failure = error instanceof ApiError ? error : new ApiError();
      if (failure.status === 401) onExpired();
      else setState({ status: 'error', error: failure });
    });
    return () => { active = false; controller.abort(); };
  }, [load, onExpired, attempt, revision]);
  return { state, retry: () => setAttempt(value => value + 1) };
}

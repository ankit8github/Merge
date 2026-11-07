import { useEffect, useState } from 'react';

type HealthState = 'loading' | 'success' | 'error';

export default function App() {
  const [state, setState] = useState<HealthState>('loading');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setState('loading');
    const timeout = window.setTimeout(() => controller.abort(), 5000);

    async function checkHealth() {
      try {
        const response = await fetch('/health', { signal: controller.signal });
        if (!response.ok) throw new Error('Health request failed');
        const body: unknown = await response.json();
        if (typeof body !== 'object' || body === null || !('status' in body) || body.status !== 'ok') {
          throw new Error('Unexpected health response');
        }
        if (active) setState('success');
      } catch {
        if (active) setState('error');
      } finally {
        window.clearTimeout(timeout);
      }
    }
    void checkHealth();
    return () => {
      active = false;
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [attempt]);

  return (
    <main>
      <p>Merge · Phase 0</p>
      <h1>Development health</h1>
      <div role="status" aria-live="polite">
        {state === 'loading' && <p>Checking backend…</p>}
        {state === 'success' && <p>Backend is healthy.</p>}
        {state === 'error' && <p>Backend unavailable. Start the API and try again.</p>}
      </div>
      <button disabled={state === 'loading'} onClick={() => setAttempt(value => value + 1)}>
        Check again
      </button>
    </main>
  );
}

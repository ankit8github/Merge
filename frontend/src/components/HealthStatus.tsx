import { useEffect, useState } from 'react';

export default function HealthStatus() {
  const [state, setState] = useState<'loading' | 'success' | 'error'>('loading');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setState('loading');
    const timeout = window.setTimeout(() => controller.abort(), 5000);
    void (async () => {
      try {
        const response = await fetch('/health', { signal: controller.signal });
        if (!response.ok) throw new Error();
        const body: unknown = await response.json();
        if (typeof body !== 'object' || body === null || !('status' in body) || body.status !== 'ok') throw new Error();
        if (active) setState('success');
      } catch { if (active) setState('error'); }
      finally { window.clearTimeout(timeout); }
    })();
    return () => { active = false; window.clearTimeout(timeout); controller.abort(); };
  }, [attempt]);
  return <section className="health" aria-label="Service connection">
    <div role="status" aria-live="polite">
      {state === 'loading' && <p>Checking service…</p>}
      {state === 'success' && <p><span className="status-dot" aria-hidden="true" />Service is responding. This check does not verify team or account access.</p>}
      {state === 'error' && <p>We could not check the service. Try again shortly.</p>}
    </div>
    <button className="text-button" disabled={state === 'loading'} onClick={() => setAttempt(value => value + 1)}>Check again</button>
  </section>;
}

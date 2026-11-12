// Test-only, explicitly installed by the owner after review. Never import in src.
// No backend endpoint, automatic installation, storage, console or auth interception.
export function installBrowserFaults(surface, approval) {
  const origin = 'http://127.0.0.1:5173';
  const uuid = '[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}';
  const path = new RegExp(`^/api/hackathons/${uuid}/(?:me/team|invitations/mine|teams(?:/${uuid}(?:/join-requests(?:/mine|/${uuid}/decision)?|/invitations(?:/${uuid}/redeem)?)?)?)$`);
  if (surface.location.origin !== origin || approval?.approved !== true || approval.origin !== origin ||
      !Array.isArray(approval.cases) || !approval.cases.length || approval.cases.length > 8) throw new Error('Fault approval rejected');
  const cases = approval.cases.map(c => {
    if (!path.test(c.path) || !['GET', 'POST'].includes(c.method) ||
        !['hold', 'lose', 'unauthorized'].includes(c.mode) || c.method === 'GET' && c.mode === 'lose' ||
        Object.keys(c).sort().join() !== 'method,mode,path') throw new Error('Fault approval rejected');
    return Object.freeze({ ...c });
  });
  const original = surface.fetch;
  let armed = null, held = null, timer, rejectHeld, phase = 'idle', installed = true;
  function clear() {
    surface.clearTimeout(timer); held = null; rejectHeld = null; timer = undefined;
  }
  function restore() {
    installed = false; armed = null;
    if (surface.fetch === wrapper) surface.fetch = original;
    const reject = rejectHeld; clear(); phase = 'restored';
    reject?.(new Error('Fault gate restored'));
  }
  async function wrapper(input, options = {}) {
    const url = new URL(typeof input === 'string' ? input : input.url, surface.location.href);
    const command = armed;
    if (!command || url.origin !== origin || url.pathname !== command.path || url.search || url.hash ||
        (options.method ?? 'GET').toUpperCase() !== command.method) return original.call(surface, input, options);
    armed = null; phase = 'fetching';
    let response;
    try {
      // One real request only; use original signal/session/CSRF unchanged.
      response = await original.call(surface, input, options);
      const reader = response.body?.getReader(); const chunks = []; let size = 0;
      if (reader) {
        try {
          while (true) {
            const { done, value } = await reader.read(); if (done) break;
            size += value.length; if (size > 65536) { await reader.cancel(); throw new Error('Fault body limit'); }
            chunks.push(value);
          }
        } finally { reader.releaseLock(); }
      }
      if (!installed) throw new Error('Fault gate restored');
      const bytes = new Uint8Array(size); let at = 0;
      for (const chunk of chunks) { bytes.set(chunk, at); at += chunk.length; }
      // Public domain responses only. No auth body/header capture or output.
      const delivered = new Response(size ? bytes : null, { status: response.status, headers: {
        'Content-Type': response.headers.get('Content-Type') ?? 'application/json', 'Cache-Control': 'no-store',
        ...(response.headers.has('Retry-After') ? { 'Retry-After': response.headers.get('Retry-After') } : {}),
      } });
      if (command.mode === 'lose') { phase = 'lost'; throw new Error('Approved lost acknowledgement'); }
      phase = 'held';
      return await new Promise((resolve, reject) => {
        rejectHeld = reject;
        held = () => { clear(); phase = 'released'; resolve(command.mode === 'unauthorized'
          ? new Response(JSON.stringify({ error: { code: 'invalid_session', message: 'Injected acceptance response', retryable: false } }),
            { status: 401, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } }) : delivered); };
        timer = surface.setTimeout(() => { const fail = rejectHeld; clear(); restore(); fail?.(new Error('Fault gate deadline')); }, 15000);
      });
    } catch (error) { if (phase === 'fetching') phase = 'failed'; throw error; }
  }
  surface.fetch = wrapper;
  return Object.freeze({
    arm(index) {
      if (!installed || armed || held || phase === 'fetching' || !Number.isInteger(index) || !cases[index]) throw new Error('Fault gate unavailable');
      armed = cases[index]; phase = 'armed';
    },
    release() { if (!held) throw new Error('No held response'); held(); },
    status() { return phase; }, restore,
  });
}

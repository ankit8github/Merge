import { afterEach, expect, it, vi } from 'vitest';
import { installBrowserFaults } from './browserFaults';

const path='/api/hackathons/00000000-0000-0000-0000-000000000001/teams';
function setup(mode='hold') {
  const fetch=vi.fn().mockResolvedValue(new Response('{"schema_version":1}',{status:201,headers:{'Content-Type':'application/json'}}));
  const surface={location:{origin:'http://127.0.0.1:5173',href:'http://127.0.0.1:5173/'},fetch,setTimeout,clearTimeout};
  const approval={approved:true,origin:surface.location.origin,cases:[{path,method:'POST',mode}]};
  return {surface,fetch,approval};
}
afterEach(()=>vi.useRealTimers());
it.each(['/auth/session','/auth/login','https://other.example/api/hackathons/x','/api/hackathons/bad/teams',path+'?secret=x'])('refuses unsafe fault target %s',bad=>{
  const {surface,approval}=setup(); approval.cases[0].path=bad;
  expect(()=>installBrowserFaults(surface,approval)).toThrow();
});
it('requires explicit approval and exact local origin',()=>{
  const {surface,approval}=setup(); approval.approved=false;
  expect(()=>installBrowserFaults(surface,approval)).toThrow();
  approval.approved=true; surface.location.origin='http://localhost:5173';
  expect(()=>installBrowserFaults(surface,approval)).toThrow();
});
it('holds one actual response after an old workspace abort and restores fetch',async()=>{
  const {surface,fetch,approval}=setup(); const gate=installBrowserFaults(surface,approval); gate.arm(0);
  const controller=new AbortController(); const options={method:'POST',body:'{}',signal:controller.signal};
  const pending=surface.fetch(path,options); await vi.waitFor(()=>expect(gate.status()).toBe('held'));
  controller.abort(); gate.release(); expect((await pending).status).toBe(201);
  expect(fetch).toHaveBeenCalledExactlyOnceWith(path,options); gate.restore(); expect(surface.fetch).toBe(fetch);
});
it('loses one acknowledgement without retrying the request',async()=>{
  const {surface,fetch,approval}=setup('lose'); const gate=installBrowserFaults(surface,approval); gate.arm(0);
  await expect(surface.fetch(path,{method:'POST'})).rejects.toThrow('lost acknowledgement');
  expect(fetch).toHaveBeenCalledTimes(1); gate.restore();
});
it('labels synthetic unauthorized delivery without bypassing the real request',async()=>{
  const {surface,fetch,approval}=setup('unauthorized'); const gate=installBrowserFaults(surface,approval); gate.arm(0);
  const pending=surface.fetch(path,{method:'POST'}); await vi.waitFor(()=>expect(gate.status()).toBe('held'));
  gate.release(); expect((await pending).status).toBe(401); expect(fetch).toHaveBeenCalledTimes(1); gate.restore();
});
it('fails closed on timeout and restores the original transport',async()=>{
  vi.useFakeTimers(); const {surface,fetch,approval}=setup(); const gate=installBrowserFaults(surface,approval); gate.arm(0);
  const pending=surface.fetch(path,{method:'POST'}); const failure=expect(pending).rejects.toThrow('deadline');
  await vi.advanceTimersByTimeAsync(15000); await failure;
  expect(surface.fetch).toBe(fetch); expect(gate.status()).toBe('restored');
});
it('does not intercept another method or auth and cannot arm concurrently',async()=>{
  const {surface,fetch,approval}=setup(); const gate=installBrowserFaults(surface,approval); gate.arm(0);
  expect(()=>gate.arm(0)).toThrow(); await surface.fetch('/auth/session');
  expect(fetch).toHaveBeenCalledExactlyOnceWith('/auth/session',{}); expect(gate.status()).toBe('armed'); gate.restore();
});

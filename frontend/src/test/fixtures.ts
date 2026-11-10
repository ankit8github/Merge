// Test-only HTTP fixtures. Production views never import this module.
export const H1 = '00000000-0000-0000-0000-000000000001';
export const H2 = '00000000-0000-0000-0000-000000000002';
export const T1 = '00000000-0000-0000-0000-000000000011';
export const T2 = '00000000-0000-0000-0000-000000000012';
export const U1 = '00000000-0000-0000-0000-000000000021';
export const csrf = 'A'.repeat(43);
export const session = () => ({ identity: { user_id: U1, username: 'test_builder' }, expires_at: new Date(Date.now() + 3600000).toISOString(), csrf_token: csrf });
export const hackathon = (id = H1) => ({ id, name: id === H1 ? 'Test Challenge' : 'Second Challenge', min_team_size: 2, max_team_size: 4 });
export const team = (id = T1, scope = H1) => ({ ...hackathon(scope), id, hackathon_id: scope, name: id === T1 ? 'Test Team Alpha' : 'Test Team Beta', member_count: 2, readiness: 'ready', leader: { user_id: U1, display_name: 'Test Leader' }, created_at: '2026-11-10T00:00:00Z' });
export const json = (body: unknown, status = 200, headers?: HeadersInit) => new Response(JSON.stringify(body), { status, headers });
export const failure = (status: number, code = 'request_failed', retryable = false, headers?: HeadersInit) => json({ error: { code, message: 'Untrusted upstream message', retryable } }, status, headers);

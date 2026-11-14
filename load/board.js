import http from 'k6/http';
import exec from 'k6/execution';
import { Trend, Rate, Counter } from 'k6/metrics';

const latency = new Trend('board_latency', true);
const errors = new Rate('board_errors');
const requests = new Counter('board_requests');
const cookies = JSON.parse(__ENV.MERGE_BENCH_SESSIONS || '[]');
if (cookies.length !== 100 || !/^http:\/\/127\.0\.0\.1:8766\/api\/hackathons\/[0-9a-f-]{36}\/teams\?limit=20$/.test(__ENV.MERGE_BENCH_URL || '')) {
  throw new Error('Fixed benchmark configuration required');
}
export const options = {
  scenarios: {
    warmup: { executor: 'constant-vus', vus: 100, duration: '20s', gracefulStop: '0s', exec: 'warmup' },
    board: { executor: 'constant-vus', vus: 100, startTime: '20s', duration: '60s', gracefulStop: '5s', exec: 'board' },
  },
  thresholds: { board_latency: ['p(95)<200'], board_errors: ['rate==0'], board_requests: ['count>=100'] },
  summaryTrendStats: ['med', 'p(95)', 'p(99)'], discardResponseBodies: false,
};
function request(measured) {
  const response = http.get(__ENV.MERGE_BENCH_URL, {
    headers: { Cookie: cookies[(exec.vu.idInTest - 1) % 100], Accept: 'application/json', Origin: 'http://127.0.0.1:8766' },
    redirects: 0, timeout: '5s', tags: { kind: measured ? 'board' : 'warmup' },
  });
  let ok = response.status === 200;
  try {
    const data = response.json();
    ok = ok && data.items.length === 20 && data.items.every(t => t.hackathon_id === __ENV.MERGE_BENCH_HACKATHON && t.member_count >= 1 && t.member_count <= t.max_team_size);
  } catch { ok = false; }
  if (measured) { latency.add(response.timings.duration); errors.add(!ok); requests.add(1); }
}
export function warmup() { request(false); }
export function board() { request(true); }
export function handleSummary(data) {
  // Only aggregate metrics; never serialize response bodies, cookies or env.
  const result = { schema_version: 1, vus: 100, duration_seconds: 60, warmup_seconds: 20,
    measured_elapsed_seconds: (data.state.testRunDurationMs - 20000) / 1000, metrics: {} };
  for (const name of ['board_latency', 'board_errors', 'board_requests']) result.metrics[name] = data.metrics[name];
  return { [__ENV.MERGE_BENCH_SUMMARY]: JSON.stringify(result) };
}

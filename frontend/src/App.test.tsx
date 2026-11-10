import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from './components/HealthStatus';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.useRealTimers(); });

it('shows loading and then a healthy backend', async () => {
  let resolve!: (value: Response) => void;
  const fetchMock = vi.fn(() => new Promise<Response>(done => { resolve = done; }));
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);
  expect(screen.getByRole('status').textContent).toContain('Checking backend');
  resolve(new Response(JSON.stringify({ status: 'ok' })));
  await screen.findByText('Backend is healthy.');
  expect(fetchMock).toHaveBeenCalledWith('/health', expect.objectContaining({ signal: expect.any(AbortSignal) }));
});

it.each(['network', 'http', 'payload', 'json'])('handles %s failure and recovers on retry', async kind => {
  const fetchMock = vi.fn();
  if (kind === 'network') fetchMock.mockRejectedValueOnce(new Error('Offline'));
  if (kind === 'http') fetchMock.mockResolvedValueOnce(new Response('', { status: 503 }));
  if (kind === 'payload') fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ status: 'wrong' })));
  if (kind === 'json') fetchMock.mockResolvedValueOnce(new Response('invalid json'));
  fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ status: 'ok' })));
  vi.stubGlobal('fetch', fetchMock);
  render(<App />);
  await screen.findByText('Backend unavailable. Start the API and try again.');
  fireEvent.click(screen.getByRole('button', { name: 'Check again' }));
  await screen.findByText('Backend is healthy.');
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it('aborts a slow request and reports an error', async () => {
  vi.useFakeTimers();
  vi.stubGlobal('fetch', vi.fn((_url, options: RequestInit) => new Promise((_resolve, reject) => {
    options.signal?.addEventListener('abort', () => reject(new Error('Aborted')));
  })));
  render(<App />);
  await vi.advanceTimersByTimeAsync(5000);
  vi.useRealTimers();
  await waitFor(() => expect(screen.getByRole('status').textContent).toContain('Backend unavailable'));
});

import { useEffect, useState } from 'react';
import { ApiError, errorMessage } from '../api';

export function useCooldown(error: ApiError | null) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    setNow(Date.now());
    if (!error?.retryAt) return;
    const timer = window.setInterval(() => {
      const current = Date.now(); setNow(current);
      if (current >= error.retryAt) window.clearInterval(timer);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [error]);
  return Math.max(0, Math.ceil(((error?.retryAt ?? 0) - now) / 1000));
}
export function ErrorNotice({ error, retry }: { error: ApiError; retry?: () => void }) {
  const seconds = useCooldown(error);
  return <div className="notice error" role="alert">
    <p>{errorMessage(error)}</p>
    {seconds > 0 && <p>Try again in {seconds} seconds.</p>}
    {retry && <button className="button secondary" disabled={seconds > 0} onClick={retry}>Try again</button>}
  </div>;
}
export function Loading({ children }: { children: string }) {
  return <div className="loading" role="status"><span className="spinner" aria-hidden="true" />{children}</div>;
}

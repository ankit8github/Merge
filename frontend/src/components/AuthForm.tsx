import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, type Session } from '../api';
import { ErrorNotice, useCooldown } from './Feedback';

export default function AuthForm({ onSession, restore, message }: {
  onSession: (session: Session) => void; restore: () => void; message?: string;
}) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [notice, setNotice] = useState(message);
  const [username, setUsername] = useState('');
  const active = useRef<AbortController | null>(null);
  const cooldown = useCooldown(error);
  useEffect(() => () => active.current?.abort(), []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || cooldown) return;
    const form = event.currentTarget, data = new FormData(form);
    const credentials = { username: String(data.get('username')), password: String(data.get('password')) };
    const display = String(data.get('display_name') ?? '');
    if (Array.from(credentials.password).length < 15 || Array.from(credentials.password).length > 128 ||
        (mode === 'register' && (Array.from(display).length > 80 || /^ +$/.test(display) || display.includes('\0')))) {
      setError(new ApiError(422, 'invalid_request')); return;
    }
    const controller = new AbortController(); active.current = controller;
    setBusy(true); setError(null); setNotice(undefined);
    try {
      if (mode === 'register') {
        await api.register({ ...credentials, ...(display ? { display_name: display } : {}) }, controller.signal);
        if (controller.signal.aborted) return;
        setUsername(credentials.username); setMode('login');
        setNotice('Account created. Sign in with your new credentials.');
      } else {
        const session = await api.login(credentials, controller.signal);
        if (!controller.signal.aborted) onSession(session);
      }
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof ApiError ? failure : new ApiError());
    } finally {
      const password = form.elements.namedItem('password');
      if (password instanceof HTMLInputElement) password.value = '';
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return <div className="auth-layout">
    <section className="welcome" aria-labelledby="welcome-title">
      <span className="eyebrow">GOOD IDEAS START WITH PEOPLE</span>
      <h1 id="welcome-title">Find your people.<br /><span>Build what’s next.</span></h1>
      <p>Explore hackathons, meet the teams taking shape, and find where you belong.</p>
      <div className="welcome-art" aria-hidden="true"><span>M</span><i /><i /><i /></div>
      <p className="quiet">One community. More possibilities.</p>
    </section>
    <section className="panel auth-panel" aria-labelledby="auth-title">
      <p className="eyebrow">WELCOME TO MERGE</p>
      <h2 id="auth-title">{mode === 'login' ? 'Let’s get you in.' : 'Make a new connection.'}</h2>
      <p className="muted">{mode === 'login' ? 'Sign in to discover your next team.' : 'Create your account to explore the community.'}</p>
      <div className="segmented" aria-label="Account access">
        <button type="button" aria-pressed={mode === 'login'} disabled={busy} onClick={() => { setMode('login'); if (!cooldown) setError(null); }}>Sign in</button>
        <button type="button" aria-pressed={mode === 'register'} disabled={busy} onClick={() => { setMode('register'); if (!cooldown) setError(null); }}>Register</button>
      </div>
      {notice && <p className="notice success" role="status">{notice}</p>}
      {error && <ErrorNotice error={error} />}
      {error && error.status === 0 && <p className="muted">The request may have reached the server. Check your session before submitting again; if registering, try signing in.</p>}
      <form onSubmit={event => { void submit(event); }} aria-busy={busy}>
        <fieldset disabled={busy}>
          <label htmlFor="username">Username</label>
          <input key={username} id="username" name="username" autoComplete="username" autoCapitalize="none" spellCheck={false}
            defaultValue={username} required minLength={3} maxLength={32} pattern="[a-z0-9_]{3,32}" aria-describedby="username-help" />
          <small id="username-help">3–32 lowercase letters, numbers or underscores.</small>
          {mode === 'register' && <><label htmlFor="display_name">Display name <span className="muted">(optional)</span></label>
            <input id="display_name" name="display_name" autoComplete="nickname" />
            <small>Up to 80 characters. Visible to other participants.</small></>}
          <label htmlFor="password">Password</label>
          <input id="password" name="password" type="password" required autoComplete={mode === 'login' ? 'current-password' : 'new-password'} aria-describedby="password-help" />
          <small id="password-help">15–128 characters. Spaces are allowed.</small>
          <button className="button primary full" type="submit" disabled={busy || cooldown > 0}>
            {busy ? 'Please wait…' : cooldown > 0 ? `Wait ${cooldown}s` : mode === 'login' ? 'Sign in to Merge' : 'Create account'}<span aria-hidden="true">↗</span>
          </button>
        </fieldset>
      </form>
      <button className="text-button" disabled={busy} onClick={restore}>Already signed in? Check session</button>
      <p className="fine-print">Your session is kept in a browser cookie. Registration does not sign you in automatically.</p>
    </section>
  </div>;
}

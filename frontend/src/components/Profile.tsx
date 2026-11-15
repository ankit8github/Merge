import { useCallback, useLayoutEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, type Profile, type ProfileEdit, type Session } from '../api';
import { useRead } from '../hooks/useRead';
import { ErrorNotice, Loading } from './Feedback';

export function validateProfile(skills: string, zone: string, discoverable: boolean): { fields: Partial<Record<'skills' | 'timezone', string>>; values: Omit<ProfileEdit, 'version'> } {
  const labels = skills.trim() === '' ? [] : skills.split(',').map(s => s.trim().toLowerCase());
  const fields: Partial<Record<'skills' | 'timezone', string>> = {};
  if (labels.length > 20 || labels.some(s => !/^[a-z0-9][a-z0-9+#.\-]{0,31}$/.test(s))) fields.skills = 'Enter up to 20 comma-separated skills, each 1–32 letters, numbers, +, #, dot or hyphen; start with a letter or number.';
  let timezone: string | null = zone || null;
  try {
    if (timezone) new Intl.DateTimeFormat('en', { timeZone: timezone });
    if ((discoverable && !timezone) || timezone !== zone && zone !== '') throw new Error();
  } catch { fields.timezone = 'Enter a supported IANA time zone, such as Asia/Kolkata or UTC.'; timezone = null; }
  return { fields, values: { skills: [...new Set(labels)].sort(), timezone, discoverable } };
}

function Editor({ initial, session, signal, onExpired, reload }: { initial: Profile; session: Session; signal: AbortSignal; onExpired: () => void; reload: () => void }) {
  const [skills, setSkills] = useState(initial.skills.join(', '));
  const [zone, setZone] = useState(initial.timezone ?? '');
  const [discoverable, setDiscoverable] = useState(initial.discoverable);
  const [fields, setFields] = useState<Partial<Record<'skills' | 'timezone', string>>>({});
  const [version, setVersion] = useState(initial.version);
  const [state, setState] = useState<'editing' | 'saving' | 'saved' | 'reload'>('editing');
  const [error, setError] = useState<ApiError | null>(null);
  const owned = useRef(true), pending = useRef<AbortController | null>(null);
  useLayoutEffect(() => { owned.current = true; return () => { owned.current = false; pending.current?.abort(); }; }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current || state === 'reload' || signal.aborted) return;
    const result = validateProfile(skills, zone, discoverable);
    setFields(result.fields);
    const first = Object.keys(result.fields)[0];
    if (first) { (event.currentTarget.elements.namedItem(first) as HTMLInputElement)?.focus(); return; }
    const controller = new AbortController(); pending.current = controller;
    const abort = () => controller.abort(); signal.addEventListener('abort', abort, { once: true });
    setState('saving'); setError(null);
    try {
      const saved = await api.saveProfile(session.identity.user_id, { ...result.values, version }, session.csrf_token, controller.signal);
      if (!owned.current || signal.aborted) return;
      setVersion(saved.version); setSkills(saved.skills.join(', ')); setZone(saved.timezone ?? ''); setState('saved');
    } catch (failure) {
      if (!owned.current || signal.aborted) return;
      const e = failure instanceof ApiError ? failure : new ApiError();
      if (e.status === 401) onExpired();
      else {
        setError(e);
        // An exact validation rejection precedes the write. Other failures can
        // conceal a committed save, so still require canonical reload/CAS.
        setState(e.status === 422 && e.code === 'invalid_request' ? 'editing' : 'reload');
      }
    } finally { signal.removeEventListener('abort', abort); pending.current = null; }
  }
  return <form onSubmit={event => void submit(event)} noValidate aria-label="Edit matching profile" aria-busy={state === 'saving'}>
    <p>{initial.display_name} (@{initial.username})</p>
    <p>Opting in shares your name, username, skills and time zone with team leaders looking for teammates. Turn it off to leave rankings.</p>
    <p>Your saved skills and time zone also contribute to matching for your current teams. Leaders see combined team skill coverage.</p>
    <fieldset disabled={state === 'saving' || state === 'reload'}>
      <label htmlFor="profile-skills">Skills</label>
      <input id="profile-skills" name="skills" value={skills} onChange={e => { setSkills(e.target.value); setState('editing'); }} aria-invalid={!!fields.skills} aria-describedby="profile-skills-help profile-skills-error" />
      <small id="profile-skills-help">Up to 20 comma-separated labels, e.g. python, react, design. Empty is allowed.</small>
      <p id="profile-skills-error" className="field-error" role={fields.skills ? 'alert' : undefined}>{fields.skills}</p>
      <label htmlFor="profile-zone">Time zone</label>
      <input id="profile-zone" name="timezone" value={zone} onChange={e => { setZone(e.target.value); setState('editing'); }} placeholder="Asia/Kolkata" aria-invalid={!!fields.timezone} aria-describedby="profile-zone-help profile-zone-error" />
      <small id="profile-zone-help">IANA name, e.g. Asia/Kolkata, Europe/London, America/New_York or UTC. Required when discoverable.</small>
      <p id="profile-zone-error" className="field-error" role={fields.timezone ? 'alert' : undefined}>{fields.timezone}</p>
      <label className="checkbox-label"><input type="checkbox" checked={discoverable} onChange={e => { setDiscoverable(e.target.checked); setState('editing'); }} />Show me in teammate rankings</label>
      <button className="button primary" type="submit">{state === 'saving' ? 'Saving profile…' : 'Save profile'}</button>
    </fieldset>
    {state === 'saved' && <p role="status">Profile saved. Refresh teammate rankings to use the current profile.</p>}
    {error && <><ErrorNotice error={error} />{state === 'reload'
      ? <p role="status">{error.code === 'profile_changed' ? 'A newer edit exists.' : 'The save outcome needs checking.'} Reload your profile before editing again.</p>
      : <p role="status">Check your skills and time zone, including exact IANA spelling. The server rejected this edit; your draft is kept.</p>}</>}
    <button className="button secondary" type="button" disabled={state === 'saving'} onClick={reload}>Reload profile</button>
  </form>;
}

function ProfileLoader(props: { session: Session; signal: AbortSignal; onExpired: () => void }) {
  const load = useCallback((s: AbortSignal) => api.profile(props.session.identity.user_id, s), [props.session.identity.user_id]);
  const { state, retry } = useRead(load, props.onExpired);
  return <>{state.status === 'loading' ? <Loading>Loading your profile…</Loading> : state.status === 'error' ? <ErrorNotice error={state.error} retry={retry} /> :
    <Editor initial={state.data} {...props} reload={retry} />}</>;
}

export default function ProfilePanel(props: { session: Session; signal: AbortSignal; onExpired: () => void }) {
  const [open, setOpen] = useState(false);
  return <section className="profile-panel panel" aria-label="Matching profile">
    <button className="button secondary" aria-expanded={open} onClick={() => setOpen(v => !v)}>{open ? 'Close profile' : 'Edit skills and time zone'}</button>
    {open && <ProfileLoader {...props} />}
  </section>;
}

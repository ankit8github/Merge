import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, type Profile, type ProfileEdit, type Session } from '../api';
import { ErrorNotice, Loading } from './Feedback';
import TimezonePicker from './TimezonePicker';

type Fields = Partial<Record<'skills' | 'timezone', string>>;
type Draft = { skills: string; timezone: string | null; discoverable: boolean };
const draftFrom = (profile: Profile): Draft => ({ skills: profile.skills.join(', '), timezone: profile.timezone, discoverable: profile.discoverable });

export function validateProfile(skills: string, zone: string, discoverable: boolean, zones: readonly string[] = []): { fields: Fields; values: Omit<ProfileEdit, 'version'> } {
  const entered = skills.trim() === '' ? [] : skills.split(',');
  const labels = entered.map(s => s.trim().toLowerCase().replace(/ +/g, '-'));
  const fields: Fields = {};
  if (entered.length > 20) fields.skills = 'Enter at most 20 comma-separated skills, including duplicates.';
  else if (labels.some(s => !/^[a-z0-9][a-z0-9+#.\-]{0,31}$/.test(s))) fields.skills = 'Enter comma-separated skills of 1–32 characters after spaces become hyphens. Start with an ASCII letter or number; use letters, numbers, spaces, +, #, dot or hyphen. Empty entries are not allowed.';
  if (discoverable && !zone) fields.timezone = 'Select a time zone to appear in teammate rankings.';
  else if (zone && !zones.includes(zone)) fields.timezone = 'Select a time zone accepted by the server.';
  return { fields, values: { skills: [...new Set(labels)].sort(), timezone: zone || null, discoverable } };
}

type Props = { session: Session; signal: AbortSignal; onExpired: () => void };

function ScopedProfilePanel({ session, signal, onExpired }: Props) {
  const [open, setOpen] = useState(false);
  const [baseline, setBaseline] = useState<Profile | null>(null);
  const [canonical, setCanonical] = useState<Profile | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [search, setSearch] = useState('');
  const [zones, setZones] = useState<string[] | null>(null);
  const [fields, setFields] = useState<Fields>({});
  const [touched, setTouched] = useState({ skills: false, timezone: false });
  const [phase, setPhase] = useState<'editing' | 'saving' | 'saved' | 'recovery'>('editing');
  const [error, setError] = useState<ApiError | null>(null);
  const [readError, setReadError] = useState<ApiError | null>(null);
  const [zoneError, setZoneError] = useState<ApiError | null>(null);
  const [reading, setReading] = useState(false), [loadingZones, setLoadingZones] = useState(false);
  const owned = useRef(false);
  const reads = useRef<AbortController | null>(null), zoneRead = useRef<AbortController | null>(null), save = useRef<AbortController | null>(null);
  useLayoutEffect(() => {
    owned.current = true;
    const abort = () => { reads.current?.abort(); zoneRead.current?.abort(); save.current?.abort(); };
    signal.addEventListener('abort', abort, { once: true });
    return () => { owned.current = false; abort(); signal.removeEventListener('abort', abort); };
  }, [signal]);
  const active = (controller: AbortController) => owned.current && !signal.aborted && !controller.signal.aborted;

  async function loadProfile() {
    if (reads.current || save.current || signal.aborted) return;
    const controller = new AbortController(); reads.current = controller;
    setReading(true); setReadError(null);
    // Reload is an observation, never an implicit discard or version rebase.
    if (baseline) { setPhase('recovery'); setCanonical(null); }
    try {
      const current = await api.profile(session.identity.user_id, controller.signal);
      if (!active(controller)) return;
      if (!baseline) { setBaseline(current); setDraft(draftFrom(current)); }
      else setCanonical(current);
    } catch (failure) {
      if (!active(controller)) return;
      const e = failure instanceof ApiError ? failure : new ApiError();
      if (e.status === 401) onExpired(); else setReadError(e);
    } finally { if (active(controller)) setReading(false); if (reads.current === controller) reads.current = null; }
  }

  async function loadZones() {
    if (zoneRead.current || signal.aborted) return;
    const controller = new AbortController(); zoneRead.current = controller;
    setLoadingZones(true); setZoneError(null);
    try {
      const current = await api.profileTimezones(controller.signal);
      if (active(controller)) setZones(current);
    } catch (failure) {
      if (!active(controller)) return;
      const e = failure instanceof ApiError ? failure : new ApiError();
      if (e.status === 401) onExpired(); else setZoneError(e);
    } finally { if (active(controller)) setLoadingZones(false); if (zoneRead.current === controller) zoneRead.current = null; }
  }

  function validation(value: Draft, query = search) {
    const result = validateProfile(value.skills, value.timezone ?? '', value.discoverable, zones ?? []);
    if (query !== '') result.fields.timezone = 'Select a result or cancel the time zone search before saving.';
    return result;
  }
  useEffect(() => {
    if (!zones || !draft || !touched.timezone) return;
    const message = search !== '' ? 'Select a result or cancel the time zone search before saving.' :
      validateProfile(draft.skills, draft.timezone ?? '', draft.discoverable, zones).fields.timezone;
    setFields(previous => previous.timezone === message ? previous : { ...previous, timezone: message });
  }, [zones, draft, search, touched.timezone]);
  function change(next: Draft, query = search) {
    if (phase === 'saving' || phase === 'recovery' || signal.aborted || !draft) return;
    const meaningful = next.skills !== draft.skills || next.timezone !== draft.timezone || next.discoverable !== draft.discoverable;
    setDraft(next); setSearch(query);
    if (meaningful || query !== search) setPhase('editing');
    const payloadChanged = JSON.stringify(validation(next, query).values) !== JSON.stringify(validation(draft).values);
    if (payloadChanged && error?.status === 422 && error.code === 'invalid_request') setError(null);
    if (next.discoverable !== draft.discoverable) setTouched(previous => ({ ...previous, timezone: true }));
    const nextFields = validation(next, query).fields;
    setFields({ ...(touched.skills ? { skills: nextFields.skills } : {}), ...(touched.timezone || next.discoverable !== draft.discoverable ? { timezone: nextFields.timezone } : {}) });
  }
  function blur(field: 'skills' | 'timezone') {
    if (!draft) return;
    setTouched(previous => ({ ...previous, [field]: true }));
    setFields(previous => ({ ...previous, [field]: validation(draft).fields[field] }));
  }
  function recover(useSaved: boolean) {
    if (!canonical || reading || signal.aborted) return;
    // Explicit user choice only. CAS still protects a write completing after GET.
    setBaseline(canonical);
    if (useSaved) { setDraft(draftFrom(canonical)); setSearch(''); }
    setCanonical(null); setError(null); setReadError(null); setFields({});
    setTouched({ skills: false, timezone: false }); setPhase('editing');
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft || !baseline || !zones || save.current || reads.current || phase === 'recovery' || signal.aborted) return;
    const result = validation(draft);
    setTouched({ skills: true, timezone: true }); setFields(result.fields);
    const first = Object.keys(result.fields)[0];
    if (first) { (event.currentTarget.elements.namedItem(first) as HTMLInputElement)?.focus(); return; }
    const controller = new AbortController(); save.current = controller;
    setPhase('saving'); setError(null);
    try {
      const saved = await api.saveProfile(session.identity.user_id, { ...result.values, version: baseline.version }, session.csrf_token, controller.signal);
      if (!active(controller)) return;
      setBaseline(saved); setDraft(draftFrom(saved)); setPhase('saved');
    } catch (failure) {
      if (!active(controller)) return;
      const e = failure instanceof ApiError ? failure : new ApiError();
      if (e.status === 401) onExpired();
      else {
        setError(e); setCanonical(null);
        // Only this exact validation rejection proves that no write began.
        setPhase(e.status === 422 && e.code === 'invalid_request' ? 'editing' : 'recovery');
      }
    } finally { if (save.current === controller) save.current = null; }
  }
  const locked = phase === 'saving' || phase === 'recovery' || reading;
  const preview = draft ? validation(draft) : null;
  return <section className="profile-panel panel" aria-label="Matching profile">
    <button className="button secondary" aria-expanded={open} aria-controls="matching-profile-editor" onClick={() => {
      setOpen(!open);
      if (!open) { if (!baseline) void loadProfile(); if (!zones) void loadZones(); }
    }}>{open ? 'Close profile' : 'Edit skills and time zone'}</button>
    <div id="matching-profile-editor" hidden={!open}>
      {reading && <Loading>{baseline ? 'Checking the saved profile…' : 'Loading your profile…'}</Loading>}
      {readError && <ErrorNotice error={readError} retry={() => void loadProfile()} />}
      {draft && baseline && <form onSubmit={event => void submit(event)} noValidate aria-label="Edit matching profile" aria-busy={phase === 'saving' || reading}>
        <p>{baseline.display_name} (@{baseline.username})</p>
        <p>Opting in shares your name, username, skills and time zone with team leaders looking for teammates. Turn it off to leave rankings.</p>
        <p>Your saved skills and time zone also contribute to matching for your current teams. Leaders see combined team skill coverage.</p>
        <fieldset disabled={locked}>
          <label htmlFor="profile-skills">Skills</label>
          <input id="profile-skills" name="skills" value={draft.skills} onChange={e => change({ ...draft, skills: e.target.value })} onBlur={() => blur('skills')}
            aria-invalid={!!fields.skills} aria-describedby="profile-skills-help profile-skills-preview profile-skills-error" />
          <small id="profile-skills-help">Up to 20 comma-separated labels. Spaces become hyphens: Data Science → data-science. Empty is allowed.</small>
          <p id="profile-skills-preview">{preview?.fields.skills ? 'Fix skills to see the canonical preview.' : `Will save as: ${preview?.values.skills.join(', ') || '(no skills)'}`}</p>
          <p id="profile-skills-error" className="field-error" role={fields.skills ? 'alert' : undefined}>{fields.skills}</p>
          {loadingZones && <Loading>Loading supported time zones…</Loading>}
          {zoneError && <ErrorNotice error={zoneError} retry={() => void loadZones()} />}
          <TimezonePicker zones={zones ?? []} selected={draft.timezone} saved={baseline.timezone} search={search} discoverable={draft.discoverable}
            disabled={locked || !zones} error={fields.timezone} onSearch={query => change(draft, query)}
            onSelect={zone => change({ ...draft, timezone: zone }, '')} onBlur={() => blur('timezone')} />
          <label className="checkbox-label"><input type="checkbox" checked={draft.discoverable} onChange={e => change({ ...draft, discoverable: e.target.checked })} />Show me in teammate rankings</label>
          <button className="button primary" type="submit" disabled={!zones}>{phase === 'saving' ? 'Saving profile…' : 'Save profile'}</button>
        </fieldset>
        {phase === 'saved' && <p role="status">Profile saved. Refresh teammate rankings to use the current profile.</p>}
        {error && <><ErrorNotice error={error} />{phase === 'recovery'
          ? <p role="status">{error.code === 'profile_changed' ? 'A newer edit exists.' : 'The save outcome needs checking.'} Reload your profile before editing again. Your draft is kept.</p>
          : <p role="status">Check your skills and time zone. The server rejected this edit; your draft is kept.</p>}</>}
        <button className="button secondary" type="button" disabled={phase === 'saving' || reading} onClick={() => void loadProfile()}>Reload profile</button>
        {canonical && <section aria-label="Current saved profile" className="profile-recovery">
          <h3>Current saved profile</h3>
          <p>Saved skills: {canonical.skills.join(', ') || '(none)'}. Saved time zone: {canonical.timezone ?? '(none)'}. Discovery: {canonical.discoverable ? 'on' : 'off'}. Version: {canonical.version}.</p>
          <p>Your draft is retained above. This read does not prove an earlier uncertain save failed. Choose how to proceed; nothing is saved automatically.</p>
          <button type="button" className="button secondary" onClick={() => recover(false)}>Keep draft for a new save</button>
          <button type="button" className="button secondary" onClick={() => recover(true)}>Discard draft and use saved profile</button>
        </section>}
      </form>}
    </div>
  </section>;
}

export default function ProfilePanel(props: Props) {
  // App also keys by authenticated epoch; direct consumers cannot reuse drafts
  // across account/credential replacement even if they forget that outer key.
  return <ScopedProfilePanel key={`${props.session.identity.user_id}:${props.session.csrf_token}:${props.session.expires_at}`} {...props} />;
}

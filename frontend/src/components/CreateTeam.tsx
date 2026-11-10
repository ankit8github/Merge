import { useId, useRef, useState, type FormEvent } from 'react';
import { type Hackathon, type Team } from '../api';
import { type TeamCreation, validTeamName } from '../hooks/useTeamCreation';
import type { useRead } from '../hooks/useRead';
import { useCooldown } from './Feedback';

export default function CreateTeam({ hackathon, creation, membership, restore }: {
  hackathon: Hackathon; creation: TeamCreation; membership: ReturnType<typeof useRead<Team | null>>; restore: () => void;
}) {
  const operation = creation.operation(hackathon.id);
  const [name, setName] = useState(operation?.name ?? '');
  const [invalid, setInvalid] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const id = useId();
  const seconds = useCooldown(operation?.error ?? null);
  const pending = operation?.status === 'pending', unresolved = operation?.uncertain === true;
  const settled = operation?.status === 'success' || operation?.status === 'assigned';
  const locked = pending || unresolved || settled;
  const member = membership.state.status === 'success' && membership.state.data !== null;
  const eligible = membership.state.status === 'success' && !member;
  const value = locked ? operation!.name : name;
  function submit(event: FormEvent) {
    event.preventDefault();
    if (pending || settled || seconds || (!unresolved && !eligible)) return;
    if (!validTeamName(value)) { setInvalid(true); input.current?.focus(); return; }
    setInvalid(false); creation.submit(hackathon.id, value);
  }
  const failure = operation?.error;
  let message = '';
  if (failure?.code === 'idempotency_mismatch') message = 'The request key belongs to a different command. Creation is not confirmed. Keep the original request unchanged and check your membership before contacting the owner.';
  else if (failure?.status === 403) message = unresolved
    ? 'This reply did not confirm creation. Restore your session and check the application origin before retrying the original request.'
    : 'Creation was denied. Restore your session and check the application origin before retrying.';
  else if (failure?.status === 400 || failure?.status === 422) message = unresolved
    ? 'Creation is not confirmed. The earlier operation is still unresolved; keep its original name.'
    : 'The team request was rejected. Check the name and try again.';
  else if (failure?.status === 429) message = 'Too many attempts. Wait before retrying.';
  else if (failure?.code === 'secure_random_unavailable') message = 'A secure request key could not be generated. Restore browser cryptography support before trying again.';
  else if (failure && !settled) message = failure.status === 503 ? 'The service is unavailable. Creation is not confirmed.' : 'We could not confirm delivery of your request.';
  return <section className="panel create-team" aria-labelledby={`${id}-title`}>
    <div className="section-top"><div><span className="eyebrow">START SOMETHING TOGETHER</span><h2 id={`${id}-title`}>Create a team</h2></div><span className="badge forming">Founder</span></div>
    <p className="muted">Give your team a name in {hackathon.name}. You will be its first member and leader.</p>
    {operation?.status === 'success' && <p className="notice success" role="status">Team creation confirmed. View My team for the latest membership.</p>}
    {(member || operation?.status === 'assigned') && operation?.status !== 'success' && <p className="notice" role="status">You already belong to a team in this hackathon. New team creation is unavailable.</p>}
    {message && <div className="notice error" role="alert"><p>{message}</p>{seconds > 0 && <p>Try again in {seconds} seconds.</p>}
      {failure?.status === 403 && <button className="text-button" onClick={restore}>Restore session</button>}</div>}
    {unresolved && <p className="notice unresolved" role="status" id={`${id}-unresolved`}>The original operation must be resolved before changing its name or starting another. Keep this tab open. Retry sends the same name and request key; it does not start a new operation.</p>}
    {membership.state.status !== 'success' && !unresolved && !settled && <p className="muted">Check My team before creating. Creation stays unavailable until membership is confirmed.</p>}
    <form onSubmit={submit} noValidate aria-busy={pending} aria-label="Create team">
      <label htmlFor={`${id}-name`}>Team name</label>
      <input ref={input} id={`${id}-name`} value={value} readOnly={locked} required autoComplete="off"
        onChange={event => { if (!locked) { setName(event.target.value); setInvalid(false); } }}
        aria-invalid={invalid} aria-describedby={`${id}-help${invalid ? ` ${id}-error` : ''}${unresolved ? ` ${id}-unresolved` : ''}`} />
      <small id={`${id}-help`}>1–120 characters. Your spelling and spaces are kept exactly.</small>
      {invalid && <p className="field-error" id={`${id}-error`} role="alert">Use 1–120 characters, not only spaces. Unsupported characters cannot be used.</p>}
      <button type="submit" className="button primary" disabled={pending || settled || seconds > 0 || (!unresolved && !eligible)}>
        {pending ? 'Creating team…' : seconds > 0 ? `Wait ${seconds}s` : unresolved ? 'Retry original request' : 'Create team'}
      </button>
      {pending && <span className="muted" role="status">Please wait. Do not resubmit or close this tab.</span>}
    </form>
  </section>;
}

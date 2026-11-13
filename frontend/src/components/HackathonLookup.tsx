import { useEffect, useRef, useState } from 'react';
import { api, ApiError, canonicalUuid, type Hackathon } from '../api';
import { ErrorNotice, Loading } from './Feedback';

type State = { status: 'idle' | 'loading' | 'invalid' | 'missing' } |
  { status: 'found'; item: Hackathon } | { status: 'error'; error: ApiError };

export default function HackathonLookup({ choose, onExpired }: { choose: (item: Hackathon) => void; onExpired: () => void }) {
  const [input, setInput] = useState('');
  const [state, setState] = useState<State>({ status: 'idle' });
  const current = useRef<AbortController | null>(null);
  const cancel = () => { current.current?.abort(); current.current = null; };
  useEffect(() => () => { current.current?.abort(); }, []);
  const lookup = () => {
    cancel();
    let id: string;
    try { id = canonicalUuid(input); }
    catch { setState({ status: 'invalid' }); return; }
    const controller = new AbortController(); current.current = controller;
    setState({ status: 'loading' });
    void api.lookupHackathon(id, controller.signal).then(item => {
      if (!controller.signal.aborted) setState(item ? { status: 'found', item } : { status: 'missing' });
    }).catch((error: ApiError) => {
      if (controller.signal.aborted) return;
      if (error.status === 401) onExpired();
      else setState({ status: 'error', error });
    });
  };
  return <section aria-label="Exact hackathon lookup">
    <form onSubmit={event => { event.preventDefault(); lookup(); }}>
      <label htmlFor="hackathon-uuid">Hackathon UUID</label>
      <p id="hackathon-uuid-help" className="fine-print">Enter the full hyphenated UUID. This looks up an ID, not a name.</p>
      <input id="hackathon-uuid" value={input} maxLength={36} autoComplete="off" spellCheck={false}
        aria-describedby="hackathon-uuid-help" aria-invalid={state.status === 'invalid'}
        onChange={event => { cancel(); setInput(event.target.value); setState({ status: 'idle' }); }} />
      <button className="button secondary" disabled={state.status === 'loading'}>Look up UUID</button>
    </form>
    {state.status === 'invalid' && <p role="alert">Enter a complete UUID in hyphenated form.</p>}
    {state.status === 'loading' && <Loading>Looking up hackathon…</Loading>}
    {state.status === 'missing' && <p role="status">No hackathon matches that UUID.</p>}
    {state.status === 'error' && <ErrorNotice error={state.error} retry={lookup} />}
    {state.status === 'found' && <div className="lookup-result" role="status">
      <strong>{state.item.name}</strong><p className="public-id">{state.item.id}</p>
      <p>{state.item.min_team_size}–{state.item.max_team_size} per team</p>
      <button className="button secondary" onClick={() => choose(state.item)}>Select hackathon</button>
    </div>}
  </section>;
}

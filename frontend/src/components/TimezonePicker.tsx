import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';

export function zoneLabel(zone: string): string {
  return `${zone.split('/').at(-1)!.replaceAll('_', ' ')} — ${zone}`;
}

export default function TimezonePicker({ zones, selected, search, saved, discoverable, error, disabled, onSearch, onSelect, onBlur }: {
  zones: readonly string[]; selected: string | null; search: string; saved: string | null; discoverable: boolean;
  error?: string; disabled: boolean; onSearch: (value: string) => void; onSelect: (zone: string | null) => void; onBlur: () => void;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [active, setActive] = useState(-1);
  const matches = zones.filter(zone => zoneLabel(zone).toLowerCase().includes(search.trim().toLowerCase()));
  const results = matches.slice(0, 50);
  const activeId = !disabled && expanded && active >= 0 && active < results.length ? `${id}-${active}` : undefined;
  useEffect(() => { if (activeId) document.getElementById(activeId)?.scrollIntoView?.({ block: 'nearest' }); }, [activeId]);
  useEffect(() => { if (disabled) { setExpanded(false); setActive(-1); } }, [disabled]);
  let browserZone: string | undefined;
  try { browserZone = Intl.DateTimeFormat().resolvedOptions().timeZone; } catch { /* Suggestion is optional. */ }
  const choose = (zone: string | null) => {
    onSelect(zone); input.current?.focus(); setExpanded(false); setActive(-1);
  };
  function keyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault(); setExpanded(true);
      setActive(index => results.length ? (event.key === 'ArrowDown' ? (index + 1) % results.length : (index <= 0 ? results.length : index) - 1) : -1);
    } else if (event.key === 'Enter' && expanded && active >= 0 && results[active]) {
      event.preventDefault(); choose(results[active]);
    } else if (event.key === 'Escape' && expanded) {
      event.preventDefault(); setExpanded(false); setActive(-1);
    } else if (event.key === 'Tab') { setExpanded(false); setActive(-1); }
  }
  return <div className="timezone-picker">
    <label htmlFor="profile-zone">Time zone</label>
    <p id="profile-zone-saved" className="muted">{saved ? `Saved time zone: ${saved}` : 'No time zone saved.'}</p>
    <p id="profile-zone-selected">{selected ? `Selected time zone: ${zoneLabel(selected)}` : 'No time zone selected.'}</p>
    <input ref={input} id="profile-zone" name="timezone" role="combobox" autoComplete="off" value={search}
      placeholder="Search time zones…" disabled={disabled} aria-autocomplete="list" aria-expanded={expanded && !disabled}
      aria-controls={`${id}-list`} aria-activedescendant={activeId} aria-invalid={!!error}
      aria-describedby="profile-zone-help profile-zone-saved profile-zone-selected profile-zone-error"
      onFocus={() => { if (!disabled) setExpanded(true); }} onKeyDown={keyDown}
      onChange={event => { onSearch(event.target.value); setActive(-1); setExpanded(true); }}
      onBlur={() => { setExpanded(false); setActive(-1); onBlur(); }} />
    <ul id={`${id}-list`} role="listbox" aria-label="Time zone results" hidden={!expanded || disabled}>
      {results.map((zone, index) => <li key={zone} id={`${id}-${index}`} role="option" aria-selected={zone === selected}
        className={index === active ? 'active' : undefined} onMouseDown={event => event.preventDefault()} onClick={() => choose(zone)}>
        {zoneLabel(zone)}
      </li>)}
    </ul>
    {expanded && !disabled && <p role="status">{matches.length === 0 ? 'No matching time zones.' :
      matches.length > 50 ? `Showing 50 of ${matches.length} time zones. Type more to narrow the results.` : `${matches.length} time zones found.`}</p>}
    <small id="profile-zone-help">Search a city or IANA identifier, then select a result. Required when discoverable.</small>
    <p id="profile-zone-error" className="field-error" role={error ? 'alert' : undefined}>{error}</p>
    <div className="timezone-actions">
      {search !== '' && <button type="button" className="text-button" disabled={disabled} onClick={() => { onSearch(''); input.current?.focus(); }}>Cancel time zone search</button>}
      {selected && <button type="button" className="text-button" disabled={disabled || discoverable} onClick={() => choose(null)}>Clear time zone</button>}
      {browserZone && zones.includes(browserZone) && browserZone !== selected && <button type="button" className="text-button" disabled={disabled}
        onClick={() => choose(browserZone!)}>Use browser time zone ({browserZone})</button>}
    </div>
  </div>;
}

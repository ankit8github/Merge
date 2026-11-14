import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from './App';
import { api } from './api';
import { failure, H1, hackathon, invitation, json, session, T1, team, U1 } from './test/fixtures';

const U2='00000000-0000-0000-0000-000000000022';
class Source {
  static all: Source[]=[];
  listeners=new Map<string,EventListener>(); onerror=null;
  constructor(public url: string) { Source.all.push(this); }
  close=vi.fn(); addEventListener(kind: string, listener: EventListener) { this.listeners.set(kind,listener); }
  emit() { this.listeners.get('invalidate')?.(new MessageEvent('invalidate',{lastEventId:'a'.repeat(64),data:JSON.stringify({schema_version:1,hackathon_id:H1,user_id:U1})})); }
}
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();});

it('preserves lifecycle confirmation, ranking and recipient draft across committed SSE refresh, then hides leader-only content after succession', async()=>{
  Source.all=[];vi.stubGlobal('EventSource',Source);
  let leader=U1;
  const current=()=>({...team(),leader:{user_id:leader,display_name:leader===U1?'Original leader':'New leader'}});
  const fetch=vi.fn((url:string,options:RequestInit)=>{
    if(url==='/auth/session')return Promise.resolve(json(session()));
    if(url==='/health')return Promise.resolve(json({status:'ok'}));
    if(url==='/api/hackathons?limit=20')return Promise.resolve(json({items:[hackathon()],next_cursor:null}));
    if(url.endsWith('/me/team'))return Promise.resolve(json({team:current()}));
    if(url.endsWith('/teams?limit=20'))return Promise.resolve(json({items:[current()],next_cursor:null}));
    if(url.endsWith('/teams/'+T1))return Promise.resolve(json(current()));
    if(url.includes('/join-requests?'))return Promise.resolve(leader===U1?json({items:[{id:T1,hackathon_id:H1,team_id:T1,requester_id:U2,
      status:'pending',created_at:'2026-11-14T00:00:00Z',resolved_at:null,requester_display_name:'Applicant Sam',requester_username:'sam_dev'}],next_cursor:null}):failure(403,'forbidden'));
    if(url.endsWith('/join-requests/mine'))return Promise.resolve(json({request:null}));
    if(url.endsWith('/members?limit=20'))return Promise.resolve(json({items:[{user_id:U1,display_name:'Original leader',joined_at:'2026-11-13T00:00:00Z'}],next_cursor:null}));
    if(url.endsWith('/suggestions?limit=20'))return Promise.resolve(leader===U1?json({hackathon_id:H1,team_id:T1,user_id:U1,reference_at:'2026-11-14T12:00:00Z',team_skills:[],
      skill_weight:.7,timezone_weight:.3,items:[],next_cursor:null}):failure(403,'forbidden'));
    return Promise.resolve(failure(404));
  });vi.stubGlobal('fetch',fetch);
  render(<App/>);fireEvent.click(await screen.findByRole('button',{name:/Test Challenge/}));
  fireEvent.click(await screen.findByRole('button',{name:/View Test Team Alpha/}));
  await screen.findByText('Applicant Sam (@sam_dev)');
  const input=screen.getByLabelText('Recipient account UUID');fireEvent.change(input,{target:{value:'retained UUID draft'}});
  fireEvent.click(screen.getByRole('button',{name:'Find teammates'}));await screen.findByText(/No eligible discoverable/);
  fireEvent.click(screen.getByRole('button',{name:'Manage membership'}));await screen.findByRole('button',{name:'Leave team'});
  fireEvent.click(screen.getByRole('button',{name:'Leave team'}));const confirmation=screen.getByRole('button',{name:'Confirm leave'});
  const count=fetch.mock.calls.filter(([url])=>url.endsWith('/suggestions?limit=20')).length;
  act(()=>Source.all[0].emit());await waitFor(()=>expect(fetch.mock.calls.filter(([url])=>url.endsWith('/suggestions?limit=20')).length).toBe(count+1));
  expect(screen.getByRole('button',{name:'Confirm leave'})).toBe(confirmation);
  expect(screen.getByLabelText('Recipient account UUID')).toBe(input);expect((input as HTMLInputElement).value).toBe('retained UUID draft');
  leader=U2;
  // A distinct invalidation fingerprint is necessary; duplicate delivery dedupes.
  act(()=>Source.all[0].listeners.get('invalidate')?.(new MessageEvent('invalidate',{lastEventId:'b'.repeat(64),data:JSON.stringify({schema_version:1,hackathon_id:H1,user_id:U1})})));
  await screen.findByText('New leader');await waitFor(()=>expect(screen.queryByText('Applicant Sam (@sam_dev)')).toBeNull());
  expect(screen.queryByRole('button',{name:'Find teammates'})).toBeNull();expect(screen.queryByLabelText('Recipient account UUID')).toBeNull();
  expect(screen.getByRole('button',{name:'Confirm leave'})).toBe(confirmation);
  fireEvent.click(screen.getByRole('button',{name:'Cancel'}));expect(screen.queryByRole('button',{name:'Confirm leave'})).toBeNull();
  expect(fetch.mock.calls.every(([,options])=>options.method!=='POST')).toBe(true);
});

it('projects named inbox labels and applicant names without changing mutation DTO parsing',async()=>{
  vi.stubGlobal('fetch',vi.fn((url:string)=>Promise.resolve(json(url.includes('/invitations/')?
    {items:[invitation({team_name:'Named team',recipient_display_name:'Builder',recipient_username:'builder'})],next_cursor:null}:
    {items:[{id:T1,hackathon_id:H1,team_id:T1,requester_id:U2,status:'pending',created_at:'2026-11-14T00:00:00Z',resolved_at:null,
      requester_display_name:'Sam',requester_username:'sam_dev'}],next_cursor:null}))));
  expect((await api.invitations(H1,null)).items[0]).toMatchObject({team_name:'Named team',recipient_display_name:'Builder',recipient_username:'builder'});
  expect((await api.pendingRequests(H1,T1,null)).items[0]).toMatchObject({requester_display_name:'Sam',requester_username:'sam_dev'});
});

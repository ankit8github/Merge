"""Deterministic initial-state benchmark dataset. No retained target/cleanup mode."""
import argparse
from datetime import datetime,timezone
from getpass import getpass
from hashlib import sha256
import json
import os
from uuid import UUID,uuid5
from sqlalchemy import text
from app.profile_models import ProfileBody
from app.security.passwords import PasswordCodec,valid_password
from release_support.targets import Target,guarded_engine
from release_support.evidence import sources,receipt
from release_support.migrations import TABLES

NAMESPACE=UUID('6a8694d3-0f42-4ca1-a5ad-f5f541a9d537')
AT=datetime(2026,11,14,0,tzinfo=timezone.utc)
SKILLS=(('python','sql'),('react','typescript'),('design','research'),('go','postgresql'),
        ('testing','accessibility'),('java','spring'),('python','data'),('devops','linux'))
ZONES=('UTC','Asia/Kolkata','Europe/London','America/New_York','Asia/Tokyo','Australia/Sydney','America/Los_Angeles','Europe/Berlin')


def dataset(seed=2026,users=10000,teams=2000):
    if type(seed) is not int or not 0<=seed<=2**32-1 or type(users) is not int or type(teams) is not int or not 1<=teams<=2000 or not 4*teams<=users<=10000:
        raise ValueError('Dataset bounds rejected')
    def uid(kind,index):return uuid5(NAMESPACE,f'v1:{seed}:{kind}:{index}')
    h=uid('hackathon',0);people=[];groups=[];members=[]
    for i in range(users):
        opt=i%5!=0
        skills=[] if i%17==0 else sorted(SKILLS[(i+seed)%len(SKILLS)])
        zone=ZONES[(i+seed)%len(ZONES)] if opt or i%2 else None
        ProfileBody(skills=skills,timezone=zone,discoverable=opt,version=1)
        people.append(dict(id=uid('user',i),display_name=f'Benchmark participant {i:05d}',username=f'bench_{i:05d}',skills=skills,timezone=zone,discoverable=opt))
    cursor=0
    for i in range(teams):
        count=1+i%4;t=uid('team',i);leader=people[cursor]['id']
        groups.append(dict(id=t,hackathon_id=h,name=f'Benchmark team {i:04d}',leader=leader))
        for j in range(count):members.append(dict(hackathon_id=h,team_id=t,user_id=people[cursor+j]['id']))
        cursor+=count
    result=dict(seed=seed,hackathon_id=h,users=people,teams=groups,memberships=members)
    validate_dataset(result);return result


def validate_dataset(data):
    ids=[u['id'] for u in data['users']];teams={t['id']:t for t in data['teams']}
    if len(set(ids))!=len(ids) or len(teams)!=len(data['teams']) or len({u['username'] for u in data['users']})!=len(ids):raise ValueError('Duplicate dataset identity')
    assigned=set();known=set(ids);rosters={t:set() for t in teams}
    for m in data['memberships']:
        if m['hackathon_id']!=data['hackathon_id'] or m['user_id'] not in known or m['team_id'] not in teams or m['user_id'] in assigned:raise ValueError('Invalid membership')
        assigned.add(m['user_id']);rosters[m['team_id']].add(m['user_id'])
    for t,row in teams.items():
        if row['hackathon_id']!=data['hackathon_id'] or not 1<=len(rosters[t])<=4 or row['leader'] not in rosters[t]:raise ValueError('Invalid team')
    for u in data['users']:ProfileBody(skills=u['skills'],timezone=u['timezone'],discoverable=u['discoverable'],version=1)


def digest(data):return sha256(json.dumps(data,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()


VALIDATE_SQL='''SELECT
    (SELECT count(*) FROM public.users) AS users,
    (SELECT count(*) FROM public.account_credentials) AS credentials,
    (SELECT count(*) FROM public.participant_profiles) AS profiles,
    (SELECT count(*) FROM public.hackathons) AS hackathons,
    (SELECT count(*) FROM public.teams) AS teams,
    (SELECT count(*) FROM public.memberships) AS memberships,
    (SELECT count(*) FROM (SELECT hackathon_id,user_id FROM public.memberships GROUP BY hackathon_id,user_id HAVING count(*)<>1) d) AS duplicates,
    (SELECT count(*) FROM public.teams t WHERE t.deleted_at IS NOT NULL OR
        (SELECT count(*) FROM public.memberships m WHERE m.team_id=t.id) NOT BETWEEN 1 AND t.max_team_size OR
        NOT EXISTS(SELECT 1 FROM public.memberships m WHERE m.team_id=t.id AND m.user_id=t.leader_user_id)) AS invalid_teams,
    (SELECT count(*) FROM public.memberships m LEFT JOIN public.teams t ON t.id=m.team_id AND t.hackathon_id=m.hackathon_id WHERE t.id IS NULL) AS orphans'''


def validate_database(c,data):
    counts=dict(c.execute(text(VALIDATE_SQL)).mappings().one())
    expected=dict(users=len(data['users']),credentials=len(data['users']),profiles=len(data['users']),hackathons=1,
        teams=len(data['teams']),memberships=len(data['memberships']),duplicates=0,invalid_teams=0,orphans=0)
    if counts!=expected:raise ValueError('Benchmark dataset invariants failed')
    actual=c.execute(text('SELECT user_id,skills,timezone,discoverable,version FROM public.participant_profiles ORDER BY user_id')).mappings().all()
    wanted=sorted(data['users'],key=lambda u:u['id'])
    if len(actual)!=len(wanted):raise ValueError('Profile counts differ')
    for row,u in zip(actual,wanted):
        if (row['user_id'],row['skills'],row['timezone'],row['discoverable'],row['version'])!=(u['id'],u['skills'],u['timezone'],u['discoverable'],1):raise ValueError('Profile integrity failed')
    # Exact IDs/roster/leadership, not just equal row counts.
    if {tuple(r) for r in c.execute(text('SELECT id,display_name FROM public.users'))}!={(u['id'],u['display_name']) for u in data['users']}:raise ValueError('User identities differ')
    if {tuple(r) for r in c.execute(text('SELECT user_id,username FROM public.account_credentials'))}!={(u['id'],u['username']) for u in data['users']}:raise ValueError('Credential identities differ')
    if {tuple(r) for r in c.execute(text('SELECT id,hackathon_id,name,leader_user_id,min_team_size,max_team_size FROM public.teams'))}!={(t['id'],t['hackathon_id'],t['name'],t['leader'],2,4) for t in data['teams']}:raise ValueError('Team identities differ')
    if {tuple(r) for r in c.execute(text('SELECT id,name,min_team_size,max_team_size FROM public.hackathons'))}!={(data['hackathon_id'],'Merge benchmark v1',2,4)}:raise ValueError('Hackathon differs')
    if {tuple(r) for r in c.execute(text('SELECT hackathon_id,team_id,user_id FROM public.memberships'))}!={(m['hackathon_id'],m['team_id'],m['user_id']) for m in data['memberships']}:raise ValueError('Roster differs')
    return counts


def insert(c,data,password_hash):
    # Entire seed is atomic, and refuses even unrelated existing application rows.
    for table in (*TABLES,'participant_profiles'):
        c.execute(text(f'LOCK TABLE public.{table} IN ACCESS EXCLUSIVE MODE'))
        if c.execute(text(f'SELECT count(*) FROM public.{table}')).scalar_one():raise ValueError('Seed requires empty application tables')
    c.execute(text('INSERT INTO public.hackathons(id,name,min_team_size,max_team_size,created_at) VALUES (:h,:name,2,4,:at)'),dict(h=data['hackathon_id'],name='Merge benchmark v1',at=AT))
    people=data['users']
    for start in range(0,len(people),500):
        batch=people[start:start+500]
        c.execute(text('INSERT INTO public.users(id,display_name,created_at) VALUES (:id,:display_name,:at)'),[dict(u,at=AT) for u in batch])
        c.execute(text('INSERT INTO public.account_credentials(user_id,username,password_hash) VALUES (:id,:username,:password_hash)'),[dict(u,password_hash=password_hash) for u in batch])
        c.execute(text('INSERT INTO public.participant_profiles(user_id,skills,timezone,discoverable) VALUES (:id,CAST(:skills AS varchar[]),:timezone,:discoverable)'),batch)
    c.execute(text('INSERT INTO public.teams(id,hackathon_id,name,min_team_size,max_team_size,leader_user_id,created_by,created_at,updated_at) VALUES (:id,:hackathon_id,:name,2,4,:leader,:leader,:at,:at)'),[dict(t,at=AT) for t in data['teams']])
    for start in range(0,len(data['memberships']),500):
        c.execute(text('INSERT INTO public.memberships(hackathon_id,team_id,user_id,joined_at) VALUES (:hackathon_id,:team_id,:user_id,:at)'),[dict(m,at=AT) for m in data['memberships'][start:start+500]])
    c.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))
    return validate_database(c,data)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--confirm-merge-bench',action='store_true',required=True)
    p.add_argument('--seed',type=int,default=2026);p.add_argument('--verify-only',action='store_true');args=p.parse_args()
    data=dataset(args.seed);before=sources();code=1;counts=None
    db_password=os.environ.get('MERGE_RELEASE_DB_PASSWORD') or getpass('Existing merge_bench_app password (hidden): ')
    try:
        encoded=None
        if not args.verify_only:
            password=os.environ.get('MERGE_BENCH_PASSWORD') or getpass('Private benchmark cohort password (hidden, 15-128 characters): ')
            if not valid_password(password):raise ValueError('Invalid benchmark password')
            encoded=PasswordCodec().hash(password)
        with guarded_engine(Target('benchmark',True,db_password)) as (engine,guard):
            with engine.connect() as c:
                with c.begin():
                    if args.verify_only:c.execute(text('SET TRANSACTION READ ONLY'))
                    counts=validate_database(c,data) if args.verify_only else insert(c,data,encoded)
        code=0
    except Exception:print('Benchmark seed/verification failed; preserve database and stop. Details suppressed.')
    report=receipt('seed',before,code,seed=args.seed,dataset_sha256=digest(data),counts=counts,verify_only=args.verify_only)
    print(f'Seed receipt: {report.name}; exit={code}');raise SystemExit(code)


if __name__=='__main__':main()

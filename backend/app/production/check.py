"""Offline syntax/topology checks; opens no engine, socket, Docker or server."""
from copy import deepcopy
import json
from pathlib import Path
from urllib.parse import urlsplit
from app.production.config import public_origin,DB_ADDRESS,PROXY_ADDRESS,REVISION,SafeParser

ROOT=Path(__file__).resolve().parents[3]


def caddy(origin,template):
    host=urlsplit(public_origin(origin)).hostname
    result=deepcopy(template)
    result['apps']['http']['servers']['https']['routes'][0]['match'][0]['host']=[host]
    return result


def validate(compose,template):
    s=compose['services'];net=compose['networks']
    if set(s)!={'postgres','api','web','migrate','bootstrap'} or compose['name']!='merge-production':raise ValueError('Unexpected production services')
    if s['web']['ports']!=['80:80','443:443'] or any('ports' in s[n] for n in ('api','postgres','migrate','bootstrap')):raise ValueError('Private service exposed')
    if net['database'].get('internal') is not True or s['postgres']['networks']['database']['ipv4_address']!=DB_ADDRESS or s['web']['networks']['edge']['ipv4_address']+'/32'!=PROXY_ADDRESS:
        raise ValueError('Fixed network policy mismatch')
    if net['edge']['ipam']['config']!=[{'subnet':'172.30.240.0/29'}] or net['database']['ipam']['config']!=[{'subnet':'172.30.241.0/29'}]:raise ValueError('Unexpected subnet')
    if s['api']['secrets']!=['runtime_db_password','throttle_key'] or s['migrate']['secrets']!=['migrator_db_password']:raise ValueError('Secret isolation mismatch')
    for name in ('api','migrate','bootstrap'):
        if set(s[name]['environment'])!={'MERGE_PROD_ORIGIN'} or s[name].get('read_only') is not True or s[name].get('cap_drop')!=['ALL']:
            raise ValueError('Unsafe app environment or filesystem')
    for name in ('migrate','bootstrap'):
        if s[name]['profiles']!=['operations'] or s[name]['restart']!='no':raise ValueError('Unconditional database operation')
    db=s['postgres']
    if db['environment']['POSTGRES_DB']!='merge_prod' or db['environment']['POSTGRES_USER']!='postgres' or db['environment']['POSTGRES_HOST_AUTH_METHOD']!='scram-sha-256':raise ValueError('Unsafe database initialization')
    if db['volumes']!=['postgres-data:/var/lib/postgresql/data'] or 'log_min_error_statement=panic' not in db['command']:raise ValueError('Storage/log policy mismatch')
    if any('password' in k.lower() and not k.endswith('_FILE') for v in s.values() for k in v.get('environment',{})):raise ValueError('Literal environment credential')
    server=template['apps']['http']['servers']['https'];routes=server['routes'][0]['handle'][0]['routes']
    if template['admin']!={'disabled':True} or server['listen']!=[':443'] or server['tls_connection_policies']!=[{}]:raise ValueError('TLS/admin configuration mismatch')
    proxy=routes[2]['handle'][0]
    if routes[2]['match']!=[{'path':['/auth','/auth/*','/api','/api/*','/health']}] or proxy['upstreams']!=[{'dial':'api:8000'}]:raise ValueError('API same-origin routing mismatch')
    if proxy['flush_interval']!=-1 or proxy['stream_timeout']!='75s':raise ValueError('SSE streaming policy mismatch')
    if proxy['headers']['request']!={'delete':['Forwarded','X-Real-IP','X-Forwarded-Host'],
        'set':{'X-Forwarded-For':['{http.request.remote.host}'],'X-Forwarded-Proto':['https']}}:raise ValueError('Single-hop forwarding policy mismatch')
    if '/ready' not in routes[1]['match'][0]['path'] or routes[1]['handle'][0]['status_code']!=404:raise ValueError('Internal readiness exposed')
    return REVISION


def main():
    p=SafeParser(description=__doc__);p.parse_args()
    try:
        compose=json.loads((ROOT/'deploy/compose.json').read_text())
        template=json.loads((ROOT/'deploy/caddy.template.json').read_text())
        validate(compose,template)
    except Exception:p.exit(1,'Deployment configuration checks failed; details suppressed.\n')
    print('Offline JSON/topology/security contracts passed; Docker/Caddy runtime validation still required.')


if __name__=='__main__':main()

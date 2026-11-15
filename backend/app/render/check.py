"""Offline Render adapter checks; no DNS, database, process or server startup."""
from copy import deepcopy
import json
from pathlib import Path
from urllib.parse import urlsplit
from app.render.config import REVISION, SafeParser, RESERVED_PORTS, SETUP_OWNERS

ROOT = Path(__file__).resolve().parents[3]


def validate_template(template):
    if template['admin'] != {'disabled': True} or set(template['apps']['http']['servers']) != {'render'}:
        raise ValueError('Render Caddy admin/listener mismatch')
    server = template['apps']['http']['servers']['render']
    if server['listen'] != [':10000'] or server['automatic_https'] != {'disable': True} or 'tls_connection_policies' in server:
        raise ValueError('Render edge must own HTTPS')
    health, public, reject = server['routes']
    if health['match'] != [{'host': ['deployment.invalid'], 'method': ['GET', 'HEAD'], 'path': ['/ready']}]:
        raise ValueError('Render healthcheck route mismatch')
    if health['handle'][0]['handler'] != 'reverse_proxy' or health['handle'][0]['upstreams'] != [{'dial': '127.0.0.1:8000'}]:
        raise ValueError('Health must verify private API readiness')
    if public['match'] != [{'host': ['deployment.invalid'], 'header': {'X-Forwarded-Proto': ['https'], 'CF-Connecting-IP': ['*']}}]:
        raise ValueError('Render hostname/edge identity mismatch')
    routes = public['handle'][0]['routes']
    if routes[0]['handle'][0] != {'handler': 'vars', 'render_client_ip': '{http.request.header.CF-Connecting-IP}'}:
        raise ValueError('Capture Render identity before stripping headers')
    headers = routes[0]['handle'][1]['response']['set']
    if headers['Strict-Transport-Security'] != ['max-age=31536000'] or headers['X-Frame-Options'] != ['DENY'] or "connect-src 'self'" not in headers['Content-Security-Policy'][0]:
        raise ValueError('Browser policy mismatch')
    proxy = routes[2]['handle'][0]
    if routes[2]['match'] != [{'path': ['/auth', '/auth/*', '/api', '/api/*', '/health']}]:
        raise ValueError('Same-origin API routing mismatch')
    if proxy['upstreams'] != [{'dial': '127.0.0.1:8000'}] or proxy['flush_interval'] != -1 or proxy['stream_timeout'] != '75s':
        raise ValueError('Private worker/SSE mismatch')
    if proxy['headers']['request'] != {
        'delete': ['Forwarded', 'X-Real-IP', 'X-Forwarded-Host', 'X-Forwarded-Port', 'CF-Connecting-IP', 'True-Client-IP'],
        'set': {'X-Forwarded-For': ['{http.vars.render_client_ip}'], 'X-Forwarded-Proto': ['https']}}:
        raise ValueError('Render forwarding rewrite mismatch')
    if routes[1]['handle'][0]['status_code'] != 404 or not {'/ready', '/docs', '/docs/*', '/redoc', '/openapi.json'} <= set(routes[1]['match'][0]['path']):
        raise ValueError('API documentation exposed')
    if 'encode' in json.dumps(template) or reject['handle'] != [{'handler': 'static_response', 'status_code': 404}]:
        raise ValueError('Unexpected compression/unmatched-host route')
    if routes[3]['handle'][1]['root'] != '/srv/merge/web' or routes[4]['handle'][-1]['root'] != '/srv/merge/web':
        raise ValueError('Static asset root mismatch')
    return REVISION


def caddy(selected, port, template):
    selected.auth()
    validate_template(template)
    if type(port) is not int or not 1024 <= port <= 65535 or port in RESERVED_PORTS:
        raise ValueError('Invalid public Render PORT')
    result = deepcopy(template)
    server = result['apps']['http']['servers']['render']
    server['listen'] = [':' + str(port)]
    for route in server['routes'][:2]: route['match'][0]['host'] = [urlsplit(selected.origin).hostname]
    return result


def validate_blueprint(bp):
    service, db = bp['services'][0], bp['databases'][0]
    if len(bp['services']) != 1 or len(bp['databases']) != 1:
        raise ValueError('One public app and one private database required')
    if (service['type'] != 'web' or service['runtime'] != 'docker' or service['plan'] != 'free'
        or service['dockerfilePath'] != './deploy/Dockerfile.render' or service['dockerContext'] != '.'
        or service['dockerCommand'] != 'python -m app.render.serve' or service['healthCheckPath'] != '/ready'
        or service['autoDeployTrigger'] != 'off' or service['numInstances'] != 1
        or service['maxShutdownDelaySeconds'] != 40):
        raise ValueError('Render web deployment contract rejected')
    if any(key in service for key in ('preDeployCommand', 'initialDeployHook', 'disk', 'scaling')):
        raise ValueError('No paid hook/disk/scaling or automatic setup')
    if (db['plan'] != 'free' or db['postgresMajorVersion'] != '17' or db['databaseName'] != 'merge_prod'
        or db['user'] not in SETUP_OWNERS or db['ipAllowList'] != [] or db['region'] != service['region']):
        raise ValueError('Private fresh Render PostgreSQL 17 required')
    env = {item['key']: item for item in service['envVars']}
    if set(env) != {'PORT', 'MERGE_RENDER_ENVIRONMENT', 'MERGE_RENDER_DB_HOST', 'MERGE_RENDER_RUNTIME_PASSWORD', 'MERGE_RENDER_THROTTLE_KEY'}:
        raise ValueError('Runtime environment has privileged/unexpected inputs')
    if env['PORT'].get('value') != '10000' or env['MERGE_RENDER_ENVIRONMENT'].get('value') != 'production':
        raise ValueError('Explicit production PORT/environment required')
    if env['MERGE_RENDER_DB_HOST']['fromDatabase'] != {'name': db['name'], 'property': 'host'}:
        raise ValueError('Use the private database hostname')
    for key in ('MERGE_RENDER_RUNTIME_PASSWORD', 'MERGE_RENDER_THROTTLE_KEY'):
        if env[key] != {'key': key, 'sync': False}: raise ValueError('Runtime secrets must be private operator inputs')
    return REVISION


def main():
    p = SafeParser(description=__doc__)
    p.parse_args()
    try:
        validate_template(json.loads((ROOT / 'deploy/render/caddy.template.json').read_text()))
        validate_blueprint(json.loads((ROOT / 'render.yaml').read_text()))
        docker = (ROOT / 'deploy/Dockerfile.render').read_text()
        if ('USER 10001:10001' not in docker or 'npm ci' not in docker or 'npm run build' not in docker
            or 'COPY --from=frontend /build/dist /srv/merge/web' not in docker
            or 'CMD ["python", "-m", "app.render.serve"]' not in docker
            or any(line.startswith(('ARG ', 'EXPOSE ')) for line in docker.splitlines())):
            raise ValueError('Render Docker contract mismatch')
    except Exception: p.exit(1, 'Offline Render configuration rejected; details suppressed.\n')
    print('Offline Render contracts passed; native/free-platform/database acceptance remains unverified.')


if __name__ == '__main__': main()

"""Offline Railway packaging checks. No DNS, database, Docker or listener."""
from copy import deepcopy
import json
from pathlib import Path
from urllib.parse import urlsplit
from app.railway.config import REVISION, SafeParser

ROOT = Path(__file__).resolve().parents[3]


def validate_template(template):
    server = template['apps']['http']['servers']['railway']
    if template['admin'] != {'disabled': True} or set(template['apps']['http']['servers']) != {'railway'}:
        raise ValueError('Unexpected Caddy service/admin')
    if server['listen'] != [':8080'] or server['automatic_https'] != {'disable': True} or 'tls_connection_policies' in server:
        raise ValueError('Railway edge must own TLS')
    health, public, reject = server['routes']
    if health['match'] != [{'host': ['healthcheck.railway.app'], 'method': ['GET', 'HEAD'], 'path': ['/ready']}]:
        raise ValueError('Healthcheck route must remain narrow')
    if health['handle'][0]['upstreams'] != [{'dial': '127.0.0.1:8000'}] or health['handle'][0]['handler'] != 'reverse_proxy':
        raise ValueError('Healthcheck must reflect API readiness')
    if public['match'] != [{'host': ['deployment.invalid'], 'header': {'X-Forwarded-Proto': ['https'], 'X-Real-IP': ['*']}}]:
        raise ValueError('Exact hostname and Railway edge headers required')
    routes = public['handle'][0]['routes']
    if routes[0]['handle'][0] != {'handler': 'vars', 'railway_client_ip': '{http.request.header.X-Real-IP}'}:
        raise ValueError('Capture Railway identity before removing forwarding headers')
    headers = routes[0]['handle'][1]['response']['set']
    if (headers['X-Frame-Options'] != ['DENY'] or headers['X-Content-Type-Options'] != ['nosniff']
        or headers['Strict-Transport-Security'] != ['max-age=31536000']
        or "connect-src 'self'" not in headers['Content-Security-Policy'][0]):
        raise ValueError('Browser security policy mismatch')
    if routes[1]['match'][0]['path'] != ['/ready', '/docs', '/docs/*', '/redoc', '/openapi.json'] or routes[1]['handle'][0]['status_code'] != 404:
        raise ValueError('Internal routes must not be public')
    proxy = routes[2]['handle'][0]
    if routes[2]['match'] != [{'path': ['/auth', '/auth/*', '/api', '/api/*', '/health']}]:
        raise ValueError('Same-origin routes changed')
    if proxy['upstreams'] != [{'dial': '127.0.0.1:8000'}] or proxy['flush_interval'] != -1 or proxy['stream_timeout'] != '75s':
        raise ValueError('Private worker/SSE policy mismatch')
    if proxy['headers']['request'] != {
        'delete': ['Forwarded', 'X-Real-IP', 'X-Forwarded-Host', 'X-Forwarded-Port'],
        'set': {'X-Forwarded-For': ['{http.vars.railway_client_ip}'], 'X-Forwarded-Proto': ['https']}}:
        raise ValueError('Single-hop identity rewrite mismatch')
    if 'encode' in json.dumps(template) or reject['handle'] != [{'handler': 'static_response', 'status_code': 404}]:
        raise ValueError('Unexpected buffering/compression or unmatched-host route')
    if routes[3]['handle'][1]['root'] != '/srv/merge/web' or routes[4]['handle'][-1]['root'] != '/srv/merge/web':
        raise ValueError('React asset root mismatch')
    if any(r.get('terminal') is not True for r in (health, public, reject)):
        raise ValueError('Terminal ingress routes required')
    return REVISION


def caddy(selected, port, template):
    selected.auth()
    if type(port) is not int or not 1024 <= port <= 65535 or port == 8000:
        raise ValueError('Invalid public listener')
    validate_template(template)
    result = deepcopy(template)
    server = result['apps']['http']['servers']['railway']
    server['listen'] = [':' + str(port)]
    server['routes'][1]['match'][0]['host'] = [urlsplit(selected.origin).hostname]
    return result


def validate_settings(settings):
    app, ops, db = (settings[k] for k in ('application', 'operations', 'database'))
    for service in (app, ops):
        if service['rootDirectory'] != '/' or service['dockerfilePath'] != 'deploy/Dockerfile.railway' or service['preDeployCommand'] is not None or service['numReplicas'] != 1:
            raise ValueError('Unexpected Railway deployment scope')
    if (app['startCommand'] != 'python -m app.railway.serve' or app['healthcheckPath'] != '/ready'
        or app['healthcheckTimeout'] != 180 or app['sleepApplication'] is not False
        or app['publicTargetPort'] != '$PORT' or app['drainingSeconds'] < 35
        or app['restartPolicyType'] != 'ON_FAILURE' or app['restartPolicyMaxRetries'] != 3):
        raise ValueError('Application health/start/drain policy mismatch')
    if ops != {'rootDirectory': '/', 'dockerfilePath': 'deploy/Dockerfile.railway',
               'startCommand': 'python -m app.railway.operations --confirm-merge-prod',
               'preDeployCommand': None, 'healthcheckPath': None, 'numReplicas': 1,
               'restartPolicyType': 'NEVER', 'publicDomain': None, 'tcpProxy': False}:
        raise ValueError('Private explicit operations required')
    if db != {'serviceName': 'postgres', 'majorVersion': 17, 'publicDomain': None,
              'tcpProxy': False, 'persistentVolumeRequired': True}:
        raise ValueError('Private persistent PostgreSQL 17 required')
    return REVISION


def main():
    parser = SafeParser(description=__doc__)
    parser.parse_args()
    try:
        validate_template(json.loads((ROOT / 'deploy/railway/caddy.template.json').read_text()))
        validate_settings(json.loads((ROOT / 'deploy/railway/settings.json').read_text()))
        docker = (ROOT / 'deploy/Dockerfile.railway').read_text()
        if ('USER 10001:10001' not in docker or 'npm ci' not in docker or 'npm run build' not in docker
            or 'COPY --from=frontend /build/dist /srv/merge/web' not in docker
            or 'CMD ["python", "-m", "app.railway.serve"]' not in docker
            or any(line.startswith(('ARG ', 'EXPOSE ')) for line in docker.splitlines())):
            raise ValueError('Railway Dockerfile contract rejected')
    except Exception:
        parser.exit(1, 'Offline Railway configuration rejected; details suppressed.\n')
    print('Offline Railway packaging contracts passed; native/platform/database verification remains required.')


if __name__ == '__main__': main()

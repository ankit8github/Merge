"""Render-only inputs; no development, external DB, or privileged fallback."""
from dataclasses import dataclass, field
import os
import re
from uuid import UUID
from pydantic import SecretStr
from sqlalchemy import URL
from app.production.config import DATABASE, REVISION, ROLES, SafeParser, public_origin
from app.railway.config import secret, port as shared_port
from app.security.auth_policy import AuthSettings

COMMON = {'MERGE_RENDER_ENVIRONMENT', 'MERGE_RENDER_DB_HOST', 'MERGE_RENDER_RUNTIME_PASSWORD'}
RUNTIME = COMMON | {'MERGE_RENDER_THROTTLE_KEY'}
SETUP = COMMON | {'MERGE_RENDER_MIGRATOR_PASSWORD', 'MERGE_RENDER_SETUP_ATTEMPT',
                  'MERGE_RENDER_SETUP_COMMIT', 'MERGE_RENDER_CATALOG_ID', 'MERGE_RENDER_CATALOG_NAME',
                  'MERGE_RENDER_CATALOG_MIN', 'MERGE_RENDER_CATALOG_MAX'}
RESERVED_PORTS = {8000, 18012, 18013, 19099}


def port(env):
    value = shared_port(env)
    if value in RESERVED_PORTS: raise ValueError('Reserved Render/private API port rejected')
    return value


def host(value):
    # Render's internal database hostname is the short dpg-* name, never the
    # external region-qualified render.com hostname or a DSN/IP/local target.
    if not isinstance(value, str) or not re.fullmatch(r'dpg-[a-z0-9]{8,64}-[a-z]', value):
        raise ValueError('Exact short Render private database hostname required')
    return value


def platform(env, allowed):
    if (env.get('RENDER') != 'true' or env.get('RENDER_SERVICE_TYPE') != 'web'
        or env.get('MERGE_RENDER_ENVIRONMENT') != 'production'
        or env.get('IS_PULL_REQUEST', 'false') != 'false'
        or not re.fullmatch(r'srv-[a-z0-9]{8,64}', env.get('RENDER_SERVICE_ID', ''))):
        raise ValueError('Explicit Render production web service required')
    if any((k.startswith('MERGE_') and k not in allowed) or k.startswith(('PG', 'VITE_', 'RAILWAY_'))
           or k in ('DATABASE_URL', 'DATABASE_PUBLIC_URL') for k in env):
        raise ValueError('Conflicting Render environment rejected')
    host(env.get('MERGE_RENDER_DB_HOST'))
    domain = env.get('RENDER_EXTERNAL_HOSTNAME', '')
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.onrender\.com', domain):
        raise ValueError('Assigned Render HTTPS hostname required')
    if env.get('RENDER_EXTERNAL_URL', 'https://' + domain) != 'https://' + domain:
        raise ValueError('Render origin mismatch')
    port(env)
    return public_origin('https://' + domain)


@dataclass(frozen=True, repr=False)
class RenderConfig:
    db_host: str
    role: str
    password: SecretStr = field(repr=False)
    origin: str
    throttle_key: SecretStr | None = field(default=None, repr=False)

    def url(self):
        host(self.db_host)
        if self.role not in ROLES or not isinstance(self.password, SecretStr):
            raise ValueError('Fixed Render role required')
        secret(self.password.get_secret_value())
        public_origin(self.origin)
        return URL.create('postgresql+psycopg', host=self.db_host, port=5432,
                          database=DATABASE, username=ROLES[self.role], password=self.password.get_secret_value())

    def auth(self):
        self.url()
        if self.role != 'runtime' or not isinstance(self.throttle_key, SecretStr):
            raise ValueError('Render runtime authentication required')
        secret(self.throttle_key.get_secret_value(), hex_key=True)
        return AuthSettings(mode='production', origin=self.origin, throttle_secret=self.throttle_key,
            trusted_proxies=('127.0.0.1/32',), throttle_window_seconds=300,
            login_account_limit=5, login_ip_limit=30, register_ip_limit=5)


def load(*, environ=None):
    env = os.environ if environ is None else environ
    origin = platform(env, RUNTIME)
    selected = RenderConfig(host(env['MERGE_RENDER_DB_HOST']), 'runtime',
        secret(env.get('MERGE_RENDER_RUNTIME_PASSWORD')), origin,
        secret(env.get('MERGE_RENDER_THROTTLE_KEY'), hex_key=True))
    selected.auth()
    return selected


@dataclass(frozen=True, repr=False)
class SetupConfig:
    target: RenderConfig
    runtime_password: SecretStr = field(repr=False)
    attempt: UUID
    commit: str
    catalog_id: UUID
    catalog_name: str
    minimum: int
    maximum: int


def load_setup(*, environ=None):
    env = os.environ if environ is None else environ
    origin = platform(env, SETUP)
    commit = env.get('MERGE_RENDER_SETUP_COMMIT', '')
    if not re.fullmatch(r'[0-9a-f]{40}', commit) or commit != env.get('RENDER_GIT_COMMIT'):
        raise ValueError('Explicit reviewed Render Git SHA required')
    try:
        attempt = UUID(env['MERGE_RENDER_SETUP_ATTEMPT'])
        catalog_id = UUID(env['MERGE_RENDER_CATALOG_ID'])
        minimum, maximum = int(env['MERGE_RENDER_CATALOG_MIN']), int(env['MERGE_RENDER_CATALOG_MAX'])
        name = env['MERGE_RENDER_CATALOG_NAME']
        if (not 1 <= minimum <= maximum <= 100 or not isinstance(name, str)
            or not 1 <= len(name) <= 120 or not name.strip() or '\x00' in name): raise ValueError()
    except (KeyError, ValueError, TypeError):
        raise ValueError('Explicit bounded Render setup/catalog inputs required') from None
    target = RenderConfig(host(env['MERGE_RENDER_DB_HOST']), 'migrator',
                          secret(env.get('MERGE_RENDER_MIGRATOR_PASSWORD')), origin)
    runtime = secret(env.get('MERGE_RENDER_RUNTIME_PASSWORD'))
    if target.password.get_secret_value() == runtime.get_secret_value():
        raise ValueError('Distinct Render runtime/migrator secrets required')
    target.url()
    return SetupConfig(target, runtime, attempt, commit, catalog_id, name, minimum, maximum)

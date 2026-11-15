"""Explicit Railway inputs. No dotenv, arbitrary URL or privileged runtime role."""
from dataclasses import dataclass, field
import os
import re
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import URL
from app.production.config import DATABASE, REVISION, PREVIOUS, ROLES, SafeParser, public_origin
from app.security.auth_policy import AuthSettings

DB_HOST = 'postgres.railway.internal'
DB_PORT = 5432
PROXY = '127.0.0.1/32'
PREFIX = 'MERGE_RAILWAY_'
COMMON = {'MERGE_RAILWAY_DB_HOST'}
RUNTIME = COMMON | {'MERGE_RAILWAY_RUNTIME_PASSWORD', 'MERGE_RAILWAY_THROTTLE_KEY'}
ACTIONS = ('bootstrap', 'prepare', 'migrate', 'verify', 'catalog')


def secret(value, *, hex_key=False):
    pattern = r'[0-9a-f]{64}' if hex_key else r'[A-Za-z0-9_-]{32,128}'
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError('Missing or invalid Railway secret')
    return SecretStr(value)


def platform(env, allowed):
    if env.get('RAILWAY_ENVIRONMENT_NAME') != 'production':
        raise ValueError('Dedicated Railway production environment required')
    for name in ('RAILWAY_PROJECT_ID', 'RAILWAY_ENVIRONMENT_ID'):
        try:
            if str(UUID(env[name])) != env[name]: raise ValueError()
        except (KeyError, ValueError, TypeError):
            raise ValueError('Railway project/environment identity required') from None
    if env.get('MERGE_RAILWAY_DB_HOST') != DB_HOST:
        raise ValueError('Fixed private Railway PostgreSQL host required')
    if any((k.startswith('MERGE_') and k not in allowed) or k.startswith(('PG', 'VITE_'))
           or k in ('DATABASE_URL', 'DATABASE_PUBLIC_URL') for k in env):
        raise ValueError('Conflicting Railway environment rejected')


@dataclass(frozen=True, repr=False)
class RailwayConfig:
    role: str
    password: SecretStr = field(repr=False)
    origin: str | None = None
    throttle_key: SecretStr | None = field(default=None, repr=False)

    def url(self):
        if self.role not in ROLES or not isinstance(self.password, SecretStr):
            raise ValueError('Restricted Railway role required')
        secret(self.password.get_secret_value())
        return URL.create('postgresql+psycopg', username=ROLES[self.role],
                          password=self.password.get_secret_value(), host=DB_HOST,
                          port=DB_PORT, database=DATABASE)

    def auth(self):
        self.url()
        if self.role != 'runtime' or not isinstance(self.throttle_key, SecretStr):
            raise ValueError('Railway runtime authentication required')
        public_origin(self.origin)
        secret(self.throttle_key.get_secret_value(), hex_key=True)
        return AuthSettings(mode='production', origin=self.origin, throttle_secret=self.throttle_key,
                            trusted_proxies=(PROXY,), throttle_window_seconds=300,
                            login_account_limit=5, login_ip_limit=30, register_ip_limit=5)


def port(env):
    value = env.get('PORT', '')
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4,5}', value):
        raise ValueError('Explicit Railway PORT required')
    result = int(value)
    if not 1024 <= result <= 65535 or result == 8000:
        raise ValueError('Railway PORT conflicts with private backend or valid range')
    return result


def load(*, environ=None):
    env = os.environ if environ is None else environ
    platform(env, RUNTIME)
    if env.get('RAILWAY_TCP_PROXY_DOMAIN'):
        raise ValueError('Railway runtime TCP proxy is forbidden')
    domain = env.get('RAILWAY_PUBLIC_DOMAIN', '')
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.up\.railway\.app', domain):
        raise ValueError('Assigned Railway HTTPS hostname required')
    port(env)
    result = RailwayConfig('runtime', secret(env.get('MERGE_RAILWAY_RUNTIME_PASSWORD')),
                           public_origin('https://' + domain),
                           secret(env.get('MERGE_RAILWAY_THROTTLE_KEY'), hex_key=True))
    result.auth()
    return result


def operation_environment(env):
    action = env.get('MERGE_RAILWAY_ACTION')
    if action not in ACTIONS: raise ValueError('Explicit Railway operation required')
    allowed = COMMON | {'MERGE_RAILWAY_ACTION', 'MERGE_RAILWAY_MIGRATOR_PASSWORD'}
    if action == 'bootstrap':
        allowed |= {'MERGE_RAILWAY_ADMIN_PASSWORD', 'MERGE_RAILWAY_RUNTIME_PASSWORD'}
    if action == 'catalog':
        allowed |= {'MERGE_RAILWAY_CATALOG_ID', 'MERGE_RAILWAY_CATALOG_NAME',
                    'MERGE_RAILWAY_CATALOG_MIN', 'MERGE_RAILWAY_CATALOG_MAX'}
    platform(env, allowed)
    # No domain/TCP proxy on the temporary operations service.
    if env.get('RAILWAY_PUBLIC_DOMAIN') or env.get('RAILWAY_TCP_PROXY_DOMAIN'):
        raise ValueError('Railway operations must remain private')
    target = RailwayConfig('migrator', secret(env.get('MERGE_RAILWAY_MIGRATOR_PASSWORD')))
    target.url()
    return action, target

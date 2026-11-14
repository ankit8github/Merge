"""Fixed single-host topology. No dotenv, arbitrary DSN, or development fallback."""
from dataclasses import dataclass, field
import argparse
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from pydantic import SecretStr
from sqlalchemy import URL
from app.security.auth_policy import AuthSettings

DATABASE = 'merge_prod'
DB_HOST = 'postgres'
DB_ADDRESS = '172.30.241.3'
PROXY_ADDRESS = '172.30.240.2/32'
REVISION = '0006_profiles'
PREVIOUS = '0005_invitations'
ROLES = {'runtime': 'merge_runtime', 'migrator': 'merge_migrator'}
SECRETS = Path('/run/secrets')


class SafeParser(argparse.ArgumentParser):
    def error(self,message):
        self.exit(2,'Invalid production arguments; private details suppressed.\n')


def public_origin(value):
    if not isinstance(value, str) or len(value)>261:
        raise ValueError('Invalid public HTTPS origin')
    parsed = urlsplit(value)
    host = parsed.hostname or ''
    labels = host.split('.')
    if (value != 'https://'+host or len(labels)<2 or len(host)>253
        or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in labels)
        or not re.fullmatch(r'[a-z]{2,63}', labels[-1])
        or labels[-1] in ('localhost','local','internal','test','invalid','example')
        or host in ('example.com','example.net','example.org') or host.endswith(('.example.com','.example.net','.example.org'))):
        raise ValueError('Invalid public HTTPS origin')
    return value


def secret_file(name, *, directory=SECRETS):
    # Fixed reviewed names; no secret values in configuration errors/repr/output.
    if name not in ('runtime_db_password','migrator_db_password','admin_db_password','throttle_key'):
        raise ValueError('Unknown production secret')
    path=directory/name
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size>256:
            raise ValueError()
        value=path.read_bytes().decode('ascii').removesuffix('\n')
        if not re.fullmatch(r'[A-Za-z0-9_-]{32,128}' if name!='throttle_key' else r'[0-9a-f]{64}',value):
            raise ValueError()
    except Exception:
        raise ValueError('Missing or invalid production secret file') from None
    return SecretStr(value)


@dataclass(frozen=True, repr=False)
class ProductionConfig:
    origin: str
    role: str
    password: SecretStr = field(repr=False)
    throttle_key: SecretStr | None = field(default=None,repr=False)

    def url(self):
        public_origin(self.origin)
        if self.role not in ROLES or not isinstance(self.password,SecretStr) or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}',self.password.get_secret_value()):
            raise ValueError('Invalid fixed production target')
        return URL.create('postgresql+psycopg',username=ROLES[self.role],password=self.password.get_secret_value(),host=DB_HOST,port=5432,database=DATABASE)

    def auth(self):
        self.url()
        if self.role!='runtime' or not isinstance(self.throttle_key,SecretStr):
            raise ValueError('Production runtime authentication required')
        # Supply every field explicitly: MERGE_AUTH_* cannot relax policy.
        return AuthSettings(mode='production',origin=self.origin,throttle_secret=self.throttle_key,
            trusted_proxies=(PROXY_ADDRESS,),throttle_window_seconds=300,
            login_account_limit=5,login_ip_limit=30,register_ip_limit=5)


def load(role='runtime', *, environ=None, directory=SECRETS):
    env=os.environ if environ is None else environ
    if role not in ROLES or any((key.startswith('MERGE_') and key!='MERGE_PROD_ORIGIN')
        or key=='DATABASE_URL' or key.startswith('PG') for key in env):
        raise ValueError('Conflicting or unsupported production environment')
    origin=public_origin(env.get('MERGE_PROD_ORIGIN'))
    password=secret_file(role+'_db_password',directory=directory)
    key=secret_file('throttle_key',directory=directory) if role=='runtime' else None
    config=ProductionConfig(origin,role,password,key);config.url()
    if role=='runtime':config.auth()
    return config

"""Explicit browser origin and cookie configuration; no dotenv or database access."""
from typing import Literal
from urllib.parse import urlsplit
from ipaddress import ip_network
import re

from pydantic import Field, SecretStr, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='MERGE_AUTH_', env_file=None,
                                     extra='forbid', frozen=True, hide_input_in_errors=True)
    mode: Literal['production', 'development'] = 'production'
    origin: str
    throttle_secret: SecretStr = Field(repr=False)
    throttle_window_seconds: int = Field(default=300, ge=60, le=3600)
    login_account_limit: int = Field(default=5, ge=1, le=100)
    login_ip_limit: int = Field(default=30, ge=1, le=500)
    register_ip_limit: int = Field(default=5, ge=1, le=50)
    trusted_proxies: tuple[str, ...] = ()

    @field_validator('throttle_secret')
    @classmethod
    def valid_key(cls, value):
        if not re.fullmatch(r'[0-9a-f]{64}', value.get_secret_value()):
            raise ValueError('A shared 32-byte hex throttle secret is required')
        return value

    @field_validator('trusted_proxies')
    @classmethod
    def explicit_proxies(cls, values):
        if len(values) > 16:
            raise ValueError('Too many trusted proxy networks')
        for value in values:
            network = ip_network(value, strict=True)
            mapped = getattr(network.network_address, 'ipv4_mapped', None)
            if (network.prefixlen == 0 or '%' in value
                    or (mapped is not None and network.prefixlen == 96)):
                raise ValueError('Wildcard proxy trust is forbidden')
        return values

    @model_validator(mode='after')
    def safe_origin(self):
        # Require a serialized origin, never a URL path, wildcard or reflection.
        if not re.fullmatch(r'https?://(?:[a-z0-9][a-z0-9.-]*|\[::1\])(?::[0-9]{1,5})?', self.origin):
            raise ValueError('An exact serialized origin is required')
        parsed = urlsplit(self.origin)
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError('Invalid origin port')
        if self.mode == 'production' and parsed.scheme != 'https':
            raise ValueError('Production requires HTTPS')
        if self.mode == 'development' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('Development requires a loopback origin')
        return self

    @property
    def secure(self) -> bool:
        return self.mode == 'production'

    @property
    def cookie_name(self) -> str:
        return '__Host-merge_session' if self.secure else 'merge_session_dev'

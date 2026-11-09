"""Explicit browser origin and cookie configuration; no dotenv or database access."""
from typing import Literal
from urllib.parse import urlsplit
import re

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='MERGE_AUTH_', env_file=None,
                                     extra='forbid', frozen=True, hide_input_in_errors=True)
    mode: Literal['production', 'development'] = 'production'
    origin: str

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

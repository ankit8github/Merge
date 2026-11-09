"""Fixed lifecycle failures; no token, CSRF secret, password or driver details."""
from enum import StrEnum


class SessionCode(StrEnum):
    INVALID_SESSION = 'invalid_session'
    INVALID_CSRF = 'invalid_csrf'
    AUTHENTICATION_CHANGED = 'authentication_changed'
    CLOCK_CONFIGURATION = 'clock_configuration'
    ENTROPY_FAILURE = 'entropy_failure'


class SessionError(Exception):
    def __init__(self, code: SessionCode):
        self.code = code
        super().__init__(code.value)

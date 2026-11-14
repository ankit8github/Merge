"""Bounded public profile fields; no authentication material."""
import re
from typing import Annotated
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import BaseModel, Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator
from app.auth import StrictBody


ZONES = frozenset(available_timezones())
SKILL = re.compile(r'[a-z0-9][a-z0-9+#.\-]{0,31}', re.ASCII)


class ProfileBody(StrictBody):
    skills: list[Annotated[StrictStr, Field(max_length=64)]] = Field(max_length=20)
    timezone: StrictStr | None = Field(max_length=64)
    discoverable: StrictBool
    version: StrictInt = Field(ge=0, le=9223372036854775806)

    @field_validator('skills')
    @classmethod
    def valid_skills(cls, values):
        normalized = sorted({value.strip().lower() for value in values})
        if any(SKILL.fullmatch(value) is None for value in normalized):
            raise ValueError('Use 1-32 character skill labels')
        return normalized

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        if value is not None and (value not in ZONES or value in ('localtime', 'Factory')):
            raise ValueError('Use a supported IANA timezone')
        return value

    @model_validator(mode='after')
    def opt_in(self):
        if self.discoverable and self.timezone is None:
            raise ValueError('A timezone is required for discovery')
        return self


class ProfileView(BaseModel):
    user_id: UUID
    display_name: str
    username: str
    skills: list[str]
    timezone: str | None
    discoverable: bool
    version: int

"""Small allowlisted discovery responses; never serialize ORM/auth objects."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReadModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class HackathonView(ReadModel):
    id: UUID
    name: str = Field(min_length=1, max_length=120)
    min_team_size: int = Field(ge=1)
    max_team_size: int = Field(ge=1)

    @model_validator(mode='after')
    def consistent_sizes(self):
        if self.min_team_size > self.max_team_size:
            raise ValueError('Invalid team sizes')
        return self


class LeaderView(ReadModel):
    user_id: UUID
    display_name: str = Field(min_length=1, max_length=80)


class TeamView(HackathonView):
    hackathon_id: UUID
    member_count: int = Field(ge=1)
    readiness: Literal['forming', 'ready']
    leader: LeaderView
    created_at: datetime

    @model_validator(mode='after')
    def consistent_state(self):
        if (not self.min_team_size <= self.max_team_size
                or self.member_count > self.max_team_size
                or self.readiness != ('ready' if self.member_count >= self.min_team_size else 'forming')):
            raise ValueError('Invalid team state')
        return self


class HackathonPage(ReadModel):
    items: list[HackathonView]
    next_cursor: UUID | None


class TeamPage(ReadModel):
    items: list[TeamView]
    next_cursor: UUID | None


class MyTeam(ReadModel):
    team: TeamView | None

"""Own-account compare-and-set edits; no membership or command transaction changes."""
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from app.profile_models import ProfileBody, ProfileView
from app.services.team_reads import TeamReadService, _uuid


class ProfileError(Exception):
    def __init__(self, code='service_unavailable'):
        self.code = code if code in ('profile_changed', 'ranking_changed', 'forbidden', 'team_not_found', 'invalid_request') else 'service_unavailable'
        super().__init__(self.code)


PROFILE = '''SELECT u.id AS user_id,u.display_name,a.username,
    COALESCE(p.skills,'{}'::varchar[]) AS skills,p.timezone,
    COALESCE(p.discoverable,false) AS discoverable,COALESCE(p.version,0) AS version
    FROM public.users u JOIN public.account_credentials a ON a.user_id=u.id
    LEFT JOIN public.participant_profiles p ON p.user_id=u.id WHERE u.id=:actor'''


class ProfileService(TeamReadService):
    @staticmethod
    def _view(c, actor):
        row = c.execute(text(PROFILE), {'actor': actor}).mappings().one_or_none()
        if row is None:
            raise ProfileError()
        return ProfileView(**row)

    def get(self, actor):
        _uuid(actor)
        return self._read(lambda c: self._view(c, actor))

    def update(self, actor, body: ProfileBody):
        _uuid(actor)
        # Revalidate even internal callers. CAS prevents delayed/retried writes
        # from replacing newer edits; no automatic retry on ambiguous commit.
        body = ProfileBody.model_validate(body.model_dump())
        values = body.model_dump() | {'actor': actor}
        try:
            with self._engine.connect() as c:
                self._guard(c)
                with c.begin():
                    c.execute(text("SET LOCAL lock_timeout='5s'"))
                    c.execute(text("SET LOCAL statement_timeout='15s'"))
                    if body.version == 0:
                        statement = '''INSERT INTO public.participant_profiles(user_id,skills,timezone,discoverable)
                            VALUES (:actor,CAST(:skills AS varchar[]),:timezone,:discoverable)
                            ON CONFLICT (user_id) DO NOTHING RETURNING user_id'''
                    else:
                        statement = '''UPDATE public.participant_profiles
                            SET skills=CAST(:skills AS varchar[]),timezone=:timezone,
                                discoverable=:discoverable,version=version+1
                            WHERE user_id=:actor AND version=:version RETURNING user_id'''
                    if c.execute(text(statement), values).scalar_one_or_none() != actor:
                        raise ProfileError('profile_changed')
                    result = self._view(c, actor)
            return result
        except DBAPIError:
            raise ProfileError() from None

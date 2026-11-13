"""Offline checks for explicit lifecycle opt-in and old browser exclusion."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from sqlalchemy.engine import Engine
from app.lifecycle_api import get_lifecycle_service
from app.services.lifecycle import LifecycleError
from test_support import concurrency
from test_browser_full_harness import api, document, scope, forbid_live


def test_lifecycle_dependency_has_no_settings_or_engine_fallback(monkeypatch):
    def forbidden(*a,**k): pytest.fail('Fallback or database operation reached')
    import app.core.config,app.db.session
    monkeypatch.setattr(app.core.config,'Settings',forbidden)
    monkeypatch.setattr(app.db.session,'build_engine',forbidden)
    engine=MagicMock(spec=Engine); engine.connect.side_effect=forbidden
    state=SimpleNamespace(auth_engine=engine)
    request=SimpleNamespace(app=SimpleNamespace(state=state))
    assert get_lifecycle_service(request,MagicMock())._engine is engine
    state.auth_engine=None
    with pytest.raises(LifecycleError): get_lifecycle_service(request,MagicMock())
    engine.connect.assert_not_called()


def test_wrong_revision_lifecycle_runner_refused_before_credentials(monkeypatch):
    monkeypatch.setattr('sys.argv',['concurrency','--confirm-merge-test','--suite','lifecycle','--revision','0003_auth'])
    monkeypatch.setattr(concurrency,'getpass',lambda *a:pytest.fail('Credential prompt reached'))
    monkeypatch.setattr(concurrency,'test_connection',lambda *a:pytest.fail('Connection reached'))
    with pytest.raises(SystemExit) as error: concurrency.main()
    assert error.value.code==2


def test_full_browser_old_manifest_grants_no_lifecycle_routes(api):
    h=api.scope.hackathons[0].id
    from uuid import uuid4
    path=f'/api/hackathons/{h}/teams/{uuid4()}'
    assert api.client.get(path+'/members',headers=api.headers).status_code==404
    assert api.client.post(path+'/leave',headers=api.headers,json={}).status_code==404
    assert api.client.post(path+f'/members/{uuid4()}/remove',headers=api.headers,json={}).status_code==404


def test_live_fixture_refuses_unapproved_execution_before_database(monkeypatch):
    from lifecycle_tests.conftest import environment,LifecycleDatabase
    monkeypatch.setattr(LifecycleDatabase,'__init__',lambda *a:pytest.fail('Database constructed'))
    request=SimpleNamespace(config=SimpleNamespace(getoption=lambda name:False))
    with pytest.raises(pytest.fail.Exception): next(environment.__wrapped__(request,0))

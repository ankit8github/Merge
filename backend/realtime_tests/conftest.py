"""New retained scopes under the unchanged exact-0005 lifecycle connection guards."""
from uuid import UUID, uuid4
import pytest
from lifecycle_tests.conftest import environment, client, headers
from concurrency_tests.conftest import pytest_addoption, pytest_generate_tests
from test_support.races import sql


@pytest.fixture
def subject(environment, client):
    db=environment; h=uuid4(); db.hackathons.append(h)
    with db.connection() as c:
        sql(c,'INSERT INTO public.hackathons(id,name,min_team_size,max_team_size) VALUES (:h,:name,2,3)',
            h=h,name='m020a_'+h.hex)
        c.commit()
    accounts=[db.account() for _ in range(3)]
    created=client.post(f'/api/hackathons/{h}/teams',headers=headers(accounts[0][1],'create'),json={'name':'Realtime'})
    assert created.status_code==201
    return h,UUID(created.json()['data']['team_id']),accounts

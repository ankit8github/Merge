"""Private GET labels are additive; stored mutation acknowledgements stay fixed."""
from test_auth_http import api
from test_admission_api import admission
from test_invitation_api import invitation


def test_pending_applicant_names_are_private_get_projection(admission):
    d=admission
    row=d.dto|dict(requester_display_name='Applicant Name',requester_username='applicant_name')
    d.service.pending_requests.return_value=dict(items=[row],next_cursor=None)
    response=d.api.client.get(d.path)
    assert response.status_code==200
    assert response.json()['items'][0]['requester_display_name']=='Applicant Name'
    assert response.json()['items'][0]['requester_username']=='applicant_name'
    created=d.api.client.post(d.path,headers=d.headers,json={})
    assert created.status_code==201 and created.json()['data']==d.dto
    assert 'requester_display_name' not in created.json()['data']
    d.api.client.cookies.clear()
    assert d.api.client.get(d.path).status_code==401


def test_inbox_team_and_recipient_names_do_not_change_stored_issue(invitation):
    d=invitation
    row=d.service.mine.return_value['items'][0]|dict(team_name='The Builders',recipient_display_name='Recipient Name',recipient_username='recipient_name')
    d.service.mine.return_value=dict(items=[row],next_cursor=None)
    response=d.api.client.get(f'/api/hackathons/{d.h}/invitations/mine')
    assert response.status_code==200
    assert response.json()['items'][0]['team_name']=='The Builders'
    assert response.json()['items'][0]['recipient_display_name']=='Recipient Name'
    assert response.json()['items'][0]['recipient_username']=='recipient_name'
    issued=d.api.client.post(d.base,headers=d.headers,json={'recipient_id':str(d.recipient)})
    assert issued.status_code==201 and 'team_name' not in issued.json()['data']
    d.api.client.cookies.clear()
    assert d.api.client.get(f'/api/hackathons/{d.h}/invitations/mine').status_code==401

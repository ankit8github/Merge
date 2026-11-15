"""Offline integrated acceptance contract. Never connects, migrates or starts a host.

Exit 2 from readiness means the campaign is planned but cannot safely execute.
This module deliberately supplies no live execution or receipt-writing command.
"""
import argparse
from hashlib import sha256
import json
import re
from pathlib import Path
from uuid import UUID

from release_support.evidence import ROOT

PLAN = ROOT / 'acceptance/integrated-campaign.json'
TARGET = dict(database='merge_profile_test', role='merge_app', host='127.0.0.1',
              port=5432, revision='0006_profiles')
ROLES = ('l', 'q', 'r', 'x')
COVERAGE = ('auth', 'profiles', 'discovery_creation', 'ranking_eligibility',
            'requests_decisions', 'invitations', 'leave_remove', 'succession',
            'soft_delete', 'two_client_sse', 'account_workspace_isolation',
            'retry_navigation', 'keyboard_mobile')
# operation, actor, maximum transport attempts, successful effects, expected status
COMMANDS = (
    ('create_a', 'l', 2, 1, 201), ('create_b', 'q', 1, 1, 201),
    ('request_q', 'q', 1, 1, 201), ('request_r', 'r', 1, 1, 201),
    ('deny_decision', 'q', 1, 0, 403), ('reject_r', 'l', 1, 1, 200),
    ('approve_q', 'l', 1, 1, 200), ('issue_r', 'l', 1, 1, 201),
    ('deny_redeem', 'x', 1, 0, 404), ('redeem_r', 'r', 1, 1, 200),
    ('deny_remove', 'q', 1, 0, 403), ('remove_r', 'l', 1, 1, 200),
    ('leave_q', 'q', 1, 1, 200), ('issue_q', 'l', 1, 1, 201),
    ('redeem_q', 'q', 1, 1, 200), ('leave_l', 'l', 1, 1, 200),
    ('final_q', 'q', 1, 1, 200),
)
PROFILE_POSTS = (
    ('profile_l', 'l', 200), ('profile_q', 'q', 200),
    ('profile_r', 'r', 200), ('profile_x', 'x', 200),
    ('profile_invalid', 'l', 422), ('profile_edit', 'l', 200),
    ('profile_stale', 'l', 409),
)
SECURITY_POSTS = ('missing_session', 'missing_csrf', 'foreign_origin')
COUNTS = dict(accounts=4, hackathons=2, teams=2, requests=2, invitations=2,
              profiles=4, profile_successes=5, auth_posts=10, profile_posts=7,
              domain_posts=18, security_posts=3, total_posts=38,
              domain_effects=14, final_memberships=1, tombstones=1)


def definition(run_id, hackathons):
    """Build a new PUBLIC plan only; user/team/request IDs bind from real replies."""
    run = UUID(str(run_id))
    hs = [UUID(str(h)) for h in hackathons]
    if run.version != 4 or len(hs) != 2 or any(h.version != 4 for h in hs) or len({run, *hs}) != 3:
        raise ValueError('Three distinct random UUID4 plan identifiers required')
    prefix = 'ia_' + run.hex[:24] + '_'
    return dict(schema_version=1, kind='integrated-browser-plan', status='planned',
        run_id=str(run), target=TARGET.copy(), origin='http://127.0.0.1:5173',
        api_origin='http://127.0.0.1:8000', min_team_size=2, max_team_size=3,
        accounts=[dict(role=r, username=prefix+r, register_attempts=1,
                       login_attempts=2 if r == 'l' else 1,
                       logout_attempts=1 if r == 'x' else 0) for r in ROLES],
        hackathons=[dict(id=str(h), name=prefix+'event_'+str(i+1)) for i,h in enumerate(hs)],
        teams=dict(a=prefix+'team_a', b=prefix+'team_b'),
        commands=[dict(tag=t, actor=r, attempts=n, effects=e, status=s) for t,r,n,e,s in COMMANDS],
        profiles=[dict(tag=t, actor=r, attempts=1, status=s) for t,r,s in PROFILE_POSTS],
        profile_values=dict(
            l=dict(skills=['python'], timezone='UTC', discoverable=False, version=0),
            q=dict(skills=['sql'], timezone='UTC', discoverable=True, version=0),
            r=dict(skills=['python', 'sql'], timezone='Asia/Kolkata', discoverable=True, version=0),
            x=dict(skills=[], timezone='UTC', discoverable=False, version=0)),
        security=[dict(tag=t, attempts=1, status=401 if t == 'missing_session' else 403) for t in SECURITY_POSTS],
        counts=COUNTS.copy(), coverage=list(COVERAGE),
        viewports=[dict(width=1280, height=800), dict(width=390, height=844)],
        forbidden=['merge_dev', 'merge_test', 'merge_bench', 'merge_prod',
                   'cleanup', 'adopt', 'resume', 'automatic_retry', 'old_manifest'])


def validate_plan(plan):
    expected = definition(plan['run_id'], [h['id'] for h in plan['hackathons']])
    # Comparing canonical JSON also distinguishes booleans from numeric budgets.
    if json.dumps(plan, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True):
        raise ValueError('Plan differs from the closed reviewed campaign contract')
    return plan


def load_plan(path=PLAN):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError('Duplicate plan key')
            out[key] = value
        return out
    raw = Path(path).read_bytes()
    if len(raw) > 32768:
        raise ValueError('Plan too large')
    return validate_plan(json.loads(raw, object_pairs_hook=unique))


def digest(plan):
    return sha256(json.dumps(validate_plan(plan), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def route_gap():
    """Inspect endpoint objects only. No lifespan, engine or network activity."""
    from test_support.browser_full import ENDPOINTS, REVISION
    from app import lifecycle_api, realtime_api, profile_api
    required = {
        ('/api/me/profile', 'GET'): profile_api.profile,
        ('/api/me/profile', 'POST'): profile_api.update_profile,
        ('/api/hackathons/{hackathon_id}/teams/{team_id}/suggestions', 'GET'): profile_api.suggestions,
        ('/api/hackathons/{hackathon_id}/teams/{team_id}/members', 'GET'): lifecycle_api.members,
        ('/api/hackathons/{hackathon_id}/teams/{team_id}/leave', 'POST'): lifecycle_api.leave,
        ('/api/hackathons/{hackathon_id}/teams/{team_id}/members/{user_id}/remove', 'POST'): lifecycle_api.remove,
        ('/api/hackathons/{hackathon_id}/events', 'GET'): realtime_api.events,
    }
    if REVISION != '0005_invitations' or any(key in ENDPOINTS for key in required):
        raise ValueError('Legacy host boundary changed; review before planning')
    return sorted(f'{method} {path}' for path,method in required)


def readiness(plan):
    validate_plan(plan)
    from release_support.integrated_run import static_readiness
    result=static_readiness()
    return dict(result,plan_sha256=digest(plan),missing_legacy_routes=route_gap())


def validate_receipt(data, plan, current_source):
    """Future evidence review contract, not a live runner or a certificate issuer.

    This verifies metadata consistency only. A human must inspect the referenced
    source-bound host/database observer and private browser observations as well.
    """
    validate_plan(plan)
    if (data.get('schema_version') != 1 or data.get('kind') != 'integrated-browser'
            or data.get('run_id') != plan['run_id'] or data.get('plan_sha256') != digest(plan)
            or data.get('target') != TARGET or data.get('source') != current_source
            or not current_source.get('head') or not current_source.get('files')
            or data.get('source_unchanged') is not True or data.get('status') != 'passed'
            or data.get('failures') != [] or data.get('skipped') != []
            or data.get('active_checkpoint') is not None or 'active_checkpoint' not in data):
        raise ValueError('Incomplete, failed or stale campaign evidence')
    exits = data.get('native_exits', {})
    if set(exits) != {'host', 'browser', 'observer'} or any(type(v) is not int or v != 0 for v in exits.values()):
        raise ValueError('All three native process exits must be recorded as zero')
    valid_hash = lambda value: isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None
    if (not re.fullmatch('[0-9a-f]{40}', current_source['head'])
            or not all(valid_hash(v) for v in current_source['files'].values())):
        raise ValueError('Complete source hashes required')
    checkpoints = data.get('checkpoints', [])
    if (len(checkpoints) != len(COVERAGE) or {c.get('id') for c in checkpoints} != set(COVERAGE)
            or any(c.get('status') != 'passed' or not valid_hash(c.get('evidence_sha256')) for c in checkpoints)):
        raise ValueError('Every unique checkpoint requires reviewed evidence')
    wanted = {t:(n,e,s) for t,r,n,e,s in COMMANDS}
    observations = data.get('commands', {})
    if set(observations) != set(wanted):
        raise ValueError('Missing or unexpected command evidence')
    for tag,(attempts,effects,status) in wanted.items():
        value = observations[tag]
        if (type(value.get('attempts')) is not int or value['attempts'] != attempts
                or type(value.get('effects')) is not int or value['effects'] != effects
                or value.get('statuses') != [status] * attempts
                or (attempts > 1 and value.get('same_key_payload_actor_scope') is not True)):
            raise ValueError('Command budget, replay or outcome evidence differs')
    exact = dict(auth_posts=10, profile_posts=7, security_posts=3, total_posts=38,
                 users=4, credentials=4, sessions=5, revoked_sessions=1, profiles=4,
                 hackathons=2, teams=2, memberships=1, requests=2, invitations=2,
                 tombstones=1, idempotency=14, audit=14, outbox=14,
                 team_a_version=13, team_b_version=1)
    totals = data.get('totals', {})
    if set(totals) != set(exact) or any(type(totals[k]) is not int or totals[k] != v for k,v in exact.items()):
        raise ValueError('Exact retained-effect totals missing')
    if (data.get('invariants') != 'fresh_scope_and_prior_rows_verified'
            or data.get('host_drained') is not True or data.get('budget_enforced_by_host') is not True
            or data.get('actual_bindings_verified') is not True):
        raise ValueError('Source-bound host/observer certification required')
    profiles = {t:s for t,r,s in PROFILE_POSTS}
    security = dict(missing_session=401, missing_csrf=403, foreign_origin=403)
    for key, statuses in (('profile_statuses', profiles), ('security_statuses', security)):
        if data.get(key) != statuses or any(type(s) is not int for s in data[key].values()):
            raise ValueError('Profile and security probes require exact observed outcomes')
    required_observations = ('two_isolated_clients', 'sse_without_manual_refresh', 'lease_reconnect_refetch',
        'no_private_content_leak', 'old_account_callbacks_fenced', 'old_workspace_callbacks_fenced',
        'keyboard_only_actions', 'mobile_390_no_overflow', 'cancel_no_posts_focus_restored',
        'navigation_no_automatic_posts')
    if data.get('observations') != {key:True for key in required_observations}:
        raise ValueError('Required browser observations missing')
    return 'metadata_consistent_requires_evidence_review'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('validate', 'readiness'))
    args = parser.parse_args(argv)
    plan = load_plan()
    if args.action == 'validate':
        print(json.dumps(dict(status='plan_valid_only', plan_sha256=digest(plan), counts=COUNTS)))
        return 0
    print(json.dumps(readiness(plan), indent=2))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())

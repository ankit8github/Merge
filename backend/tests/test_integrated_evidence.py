"""Offline preservation, native-exit and evidence-composition adversaries."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import json
from types import SimpleNamespace
import pytest
from release_support import integrated_run as run,integrated_observer as o,integrated_certify as c
from release_support.integrated_plan import load_plan,digest
from release_support.integrated_ledger import DENIALS
from test_integrated_host import scene,forbid_live,empty
from test_integrated_plan import accepted


@pytest.mark.parametrize('tamper',[None,'prior','extra'])
def test_two_insert_preparation_owns_transaction_and_rolls_back_on_drift(monkeypatch,tamper):
    plan=load_plan();before=empty();before['hashes']['users']['old']='oldhash';events=[];inserted=[]
    monkeypatch.setattr(o,'snapshot',lambda *a:before)
    class Connection:
        @contextmanager
        def begin(self):
            events.append('begin')
            try:yield;events.append('commit')
            except BaseException:events.append('rollback');raise
        def execute(self,q,p=None):
            sql=str(q)
            if sql.startswith('INSERT'):
                assert 'public.hackathons' in sql;inserted.append(p['id']);return None
            table=sql.split(' FROM public.')[1].split()[0]
            values=deepcopy(before['hashes'][table])
            if table=='hackathons':values={i:'new' for i in inserted}
            if tamper=='prior' and table=='users':values['old']='changed'
            if tamper=='extra' and table=='teams':values['unexpected']='new'
            return SimpleNamespace(all=lambda:list(values.items()))
    class Engine:
        @contextmanager
        def connect(self):yield Connection()
    if tamper:
        with pytest.raises(ValueError):o.prepare(Engine(),plan)
        assert events==['begin','rollback']
    else:
        assert o.prepare(Engine(),plan) is before
        assert inserted==[h['id'] for h in plan['hackathons']] and events==['begin','commit']


@pytest.mark.parametrize('existing',['account_credentials','users','participant_profiles','teams','hackathons'])
def test_prepare_never_adopts_existing_scope(existing):
    plan=load_plan();state=empty();state['rows'][existing]['prior']={}
    with pytest.raises(ValueError):o.preflight(state,plan,False)


def test_snapshot_is_one_readonly_snapshot_and_selects_no_raw_auth_secrets():
    plan=load_plan();queries=[];events=[]
    class Connection:
        def in_transaction(self):return False
        @contextmanager
        def begin(self):
            events.append('begin');yield;events.append('end')
        def execute(self,q,p=None):
            queries.append(str(q));return SimpleNamespace(all=lambda:[],mappings=lambda:SimpleNamespace(all=lambda:[]))
    result=o.snapshot(Connection(),plan)
    assert events==['begin','end'] and set(result['hashes'])==set(o.PK)
    assert queries[0]=='SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'
    assert all(not sql.startswith(('INSERT','UPDATE','DELETE','DROP')) for sql in queries)
    sessions=next(sql for sql in queries if 'FROM public.auth_sessions t WHERE' in sql)
    assert "-'token_hash'-'csrf_token'" in sessions
    credentials=next(sql for sql in queries if 'FROM public.account_credentials WHERE' in sql)
    assert 'password' not in credentials


@pytest.fixture
def evidence(monkeypatch,tmp_path):
    folder=tmp_path/'reports';folder.mkdir();monkeypatch.setattr(run,'DIRECTORY',folder);monkeypatch.setattr(c,'DIRECTORY',folder)
    plan=load_plan();base,source=accepted(plan);monkeypatch.setattr(c,'sources',lambda:source)
    def write(path,data):path.write_text(json.dumps(data),encoding='utf8')
    marker=folder/f"campaign-{plan['run_id']}.json"
    write(marker,dict(kind='integrated-start-marker',status='started_not_certified',run_id=plan['run_id'],source=source,
        plan_sha256=digest(plan),target=plan['target']))
    observer=folder/'observer-synthetic.json';observed=dict(status='passed',native_exit_code=0,totals=base['totals'],invariants=base['invariants']);write(observer,observed)
    host=folder/'host-synthetic.json'
    hosted={k:base[k] for k in ('totals','commands','profile_statuses','security_statuses','invariants','host_drained','budget_enforced_by_host','actual_bindings_verified')}
    hosted.update(kind='integrated-host-step',action='serve',status='passed',source=source,source_unchanged=True,run_id=plan['run_id'],
        denial_codes=DENIALS.copy(),
        start_marker=marker.name,start_marker_sha256=sha256(marker.read_bytes()).hexdigest(),
        plan_sha256=digest(plan),target=plan['target'],observer_report=observer.name,observer_sha256=sha256(observer.read_bytes()).hexdigest(),observer_native_exit=0,
        started_at='2026-11-14T00:00:00+00:00',finished_at='2026-11-14T03:00:00+00:00');write(host,hosted)
    process=folder/'process-synthetic.json';processed=dict(schema_version=1,kind='integrated-process',action='serve',status='passed',run_id=plan['run_id'],
        source=source,source_unchanged=True,native_exit_code=0,worker_report=host.name,worker_sha256=sha256(host.read_bytes()).hexdigest());write(process,processed)
    browser=folder/'browser-observations-synthetic.json';browsed=dict(source=source,source_unchanged=True,plan_sha256=digest(plan),
        checkpoints=base['checkpoints'],observations=base['observations'],started_at='2026-11-14T01:00:00+00:00',finished_at='2026-11-14T02:00:00+00:00');write(browser,browsed)
    result=SimpleNamespace(returncode=0,stdout=b'{"status":"observed_evidence_integrity_passed"}')
    def verify(argv,**kw):
        assert argv[0]=='node' and argv[1].endswith('integratedEvidence.mjs') and argv[2]==str(browser)
        assert 'shell' not in kw
        return result
    monkeypatch.setattr(c.subprocess,'run',verify)
    def flush():
        write(observer,observed);hosted['observer_sha256']=sha256(observer.read_bytes()).hexdigest();write(host,hosted)
        processed['worker_sha256']=sha256(host.read_bytes()).hexdigest();write(process,processed);write(browser,browsed)
    return SimpleNamespace(process=process,host=host,observer=observer,browser=browser,processed=processed,hosted=hosted,
        observed=observed,browsed=browsed,result=result,flush=flush,folder=folder)


def test_final_evidence_join_keeps_native_roles_explicit(evidence):
    data=c.certify(evidence.process,evidence.browser)
    assert data['status']=='passed' and data['native_exits']==dict(host=0,browser=0,observer=0)
    assert data['native_exit_roles']['browser']=='native_browser_evidence_verifier'
    assert data['browser_engine_exit']=='not_captured'


@pytest.mark.parametrize('fault',['host-exit','observer-exit','observer-counter','browser-exit','browser-output','bool-native',
    'stale','host-source','browser-source','revision','missing-budget','active-command','times','plan','incomplete','role','observer-marker','hash','denial'])
def test_final_evidence_join_refuses_ambiguous_or_partial_results(evidence,fault):
    e=evidence
    if fault=='host-exit':e.processed['native_exit_code']=1
    elif fault=='observer-exit':e.observed['native_exit_code']=1
    elif fault=='observer-counter':e.observed['totals']=dict(e.observed['totals'],audit=13)
    elif fault=='browser-exit':e.result.returncode=1
    elif fault=='browser-output':e.result.stdout=b'{}'
    elif fault=='bool-native':e.result.returncode=False
    elif fault=='stale':e.processed['source_unchanged']=False
    elif fault=='host-source':e.hosted['source']={}
    elif fault=='browser-source':e.browsed['source']={}
    elif fault=='revision':e.hosted['target']=dict(e.hosted['target'],revision='0005_invitations')
    elif fault=='missing-budget':e.hosted['budget_enforced_by_host']=False
    elif fault=='active-command':e.hosted['commands']['create_a']['attempts']=1
    elif fault=='times':e.browsed['finished_at']='2026-11-14T04:00:00+00:00'
    elif fault=='plan':e.browsed['plan_sha256']='f'*64
    elif fault=='incomplete':e.processed['status']='incomplete'
    elif fault=='role':e.hosted['target']=dict(e.hosted['target'],role='postgres')
    elif fault=='observer-marker':e.observed['invariants']='not_certified'
    elif fault=='denial':e.hosted['denial_codes']={}
    e.flush()
    if fault=='hash':e.processed['worker_sha256']='0'*64;e.process.write_text(json.dumps(e.processed))
    with pytest.raises((ValueError,KeyError)):c.certify(e.process,e.browser)


def test_failed_certification_writes_new_sanitized_failure(evidence,monkeypatch):
    def fail(*a):raise RuntimeError('synthetic sensitive detail MUST NOT serialize')
    monkeypatch.setattr(c,'certify',fail)
    assert c.main(['--host-process',str(evidence.process),'--browser-observations',str(evidence.browser)])==1
    path=next(evidence.folder.glob('certification-*.json'));text=path.read_text()
    assert 'sensitive' not in text and json.loads(text)['status']=='failed'


def test_browser_notes_changed_during_native_verification_cannot_certify(evidence,monkeypatch):
    def altered(*a,**kw):
        evidence.browser.write_text('{}')
        return evidence.result
    monkeypatch.setattr(c.subprocess,'run',altered)
    with pytest.raises(ValueError):c.certify(evidence.process,evidence.browser)


def test_worker_rejects_existing_or_redirected_report_before_live_action(tmp_path):
    with pytest.raises(ValueError):run.worker('serve',tmp_path/'old.json')


def test_started_campaign_marker_cannot_reset_even_without_database_rows(monkeypatch,tmp_path):
    folder=tmp_path/'reports';folder.mkdir();monkeypatch.setattr(run,'DIRECTORY',folder)
    plan=load_plan();path=run.claim_campaign(plan,{'head':'synthetic','files':{}});before=path.read_bytes()
    with pytest.raises(FileExistsError):run.claim_campaign(plan,{'head':'different','files':{}})
    assert path.read_bytes()==before


def test_repeated_worker_stops_at_marker_before_connecting(monkeypatch,tmp_path):
    folder=tmp_path/'reports';folder.mkdir();monkeypatch.setattr(run,'DIRECTORY',folder)
    plan=load_plan();source={'head':'a'*40,'files':{'synthetic':'b'*64}}
    run.claim_campaign(plan,source);monkeypatch.setattr(run,'sources',lambda:source)
    monkeypatch.setenv('MERGE_INTEGRATED_CHILD_PASSWORD','synthetic-only')
    reached=[];monkeypatch.setattr(run,'serve_worker',lambda *a:reached.append(True))
    path=run.new_path('host')
    assert run.worker('serve',path)==1 and reached==[]
    report=json.loads(path.read_text())
    assert report['diagnostics']==dict(stage='start_marker',reason='scope_already_started')

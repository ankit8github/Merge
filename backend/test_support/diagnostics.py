"""Metadata-only evidence for the fixed guarded runner; never serialize exceptions."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import json
import os
from pathlib import Path
import re
import time
from uuid import uuid4

import pytest


# Parameter IDs are arbitrary strings in pytest. Only reviewed, non-private
# labels and repetition/boolean IDs may cross this output boundary.
SAFE_LABELS = frozenset({
    'True', 'False', 'request', 'membership', 'audit', 'outbox', 'completion',
    'deferred', 'commit', 'ambiguous',
    '', '08006', '40001', '40P01', '55P03', '57014', 'ZZ001', '403', '422',
    'Uppercase', 'a', 'ab', 'actor', 'actor_id=forged', 'after_credential',
    'after_insert', 'after_user', 'approve', 'approved', 'body', 'capacity',
    'content_type', 'create', 'csrf', 'cursor=not', 'custom_header', 'dash',
    'database_failure', 'display_name', 'expired', 'extra', 'extra_field',
    'fetch_site', 'fingerprint', 'fk', 'forged', 'future', 'hackathon', 'has',
    'has space', 'header', 'identity', 'invalid', 'join', 'json', 'key', 'key1',
    'lifetime', 'limit=0', 'limit=101', 'limit=bad', 'lock_timeout', 'login',
    'long_password', 'malformed', 'metadata', 'missing', 'name', 'origin',
    'other', 'reject', 'reservation', 'revocation', 'revoke', 'revoked', 'same',
    'scope', 'session', 'short_password', 'statement_timeout', 'surrogate',
    'team', 'terminal', 'unicode', 'unique', 'unknown', 'user', 'username',
    'uuid', 'validate', 'validate_with_csrf', 'version', 'without', 'wrong',
    'wrong_session', r'\n', r'\x00', r'\x7f', r'\xe9', r'nonascii_\xe9', r'trail\n',
})
MAX_EVENTS = 16


class Diagnostics:
    def __init__(self, root: Path, suite: str, revision: str, repetitions: int):
        directory = root / 'test-results' / 'guarded'
        # Fixed destination only; refuse redirects outside the repository.
        for parent in (root / 'test-results', directory):
            if parent.is_symlink() or parent.resolve() != parent.parent.resolve() / parent.name:
                raise ValueError('Unsafe diagnostic destination')
            parent.mkdir(exist_ok=True)
        self.path = directory / f'run-{uuid4().hex}.json'
        self.data = {
            'schema_version': 1, 'suite': suite, 'revision': revision,
            'repetitions': repetitions, 'status': 'incomplete', 'exit_code': None,
            'stage': 'credentials', 'invariant_verification': 'not_certified',
            'collected': 0, 'teardowns_completed': 0, 'skipped': 0,
            'failures': [], 'active_node': None,
        }
        # Never overwrite another run's evidence (including an interrupted run).
        with self.path.open('x', encoding='utf-8') as stream:
            json.dump(self.data, stream)

    def save(self):
        # Only bounded counters, fixed categories and validated node IDs enter data.
        payload = json.dumps(self.data, indent=2)
        if len(payload) > 16384:
            raise ValueError('Diagnostic budget exceeded')
        temporary = self.path.with_suffix('.tmp')
        with temporary.open('x', encoding='utf-8') as stream:
            stream.write(payload)
        # Windows scanners can briefly hold the destination without delete-share.
        # Retry only this metadata rename, never a test or a database operation.
        for attempt in range(4):
            try:
                temporary.replace(self.path)
                break
            except PermissionError:
                if attempt == 3:
                    raise
                time.sleep(0.025)

    @staticmethod
    def node_id(raw):
        base, separator, parameters = raw.partition('[')
        # Reject arbitrary paths/control characters; fixed suites use these names.
        if not re.fullmatch(r'[a-z_]+_tests/test_[A-Za-z0-9_]+\.py(?:::[A-Za-z0-9_]+)*', base):
            return 'node_withheld'
        if len(base) > 320:
            return 'node_withheld'
        if not separator:
            return base
        labels = parameters.removesuffix(']').split('-')
        if (raw.endswith(']') and len(parameters) <= 100 and
                all(label in SAFE_LABELS or re.fullmatch(r'[0-9]{1,2}', label) for label in labels)):
            return raw
        return base + '[parameter_id_withheld]'

    def failure(self, node, phase, category):
        if len(self.data['failures']) < MAX_EVENTS:
            self.data['failures'].append({
                'node_id': self.node_id(node), 'phase': phase, 'category': category,
            })
        self.save()

    def pytest_collection_finish(self, session):
        self.data['collected'] = len(session.items)
        self.save()

    def pytest_runtest_logstart(self, nodeid, location):
        self.data['active_node'] = self.node_id(nodeid)
        self.save()

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_makereport(self, item, call):
        report = yield
        if report.failed:
            category = 'assertion' if call.excinfo and isinstance(call.excinfo.value, AssertionError) else 'exception'
            self.failure(report.nodeid, report.when, category)
        if report.skipped:
            self.data['skipped'] += 1
        if report.when == 'teardown':
            self.data['teardowns_completed'] += 1
            self.data['active_node'] = None
        self.save()
        return report

    def pytest_collectreport(self, report):
        if report.failed:
            self.failure(report.nodeid, 'collection', 'collection_error')

    def pytest_keyboard_interrupt(self, excinfo):
        self.data['status'] = 'interrupted'
        self.save()

    def pytest_internalerror(self, excrepr, excinfo):
        self.data['status'] = 'internal_error'
        self.save()
        return True

    def finish(self, code):
        self.data['exit_code'] = int(code)
        if self.data['status'] == 'incomplete':
            self.data['status'] = 'passed' if code == 0 else 'failed'
        if (code == 0 and self.data['status'] == 'passed' and self.data['stage'] == 'pytest' and
                self.data['collected'] > 0 and
                self.data['teardowns_completed'] == self.data['collected'] and
                not self.data['failures'] and not self.data['skipped']):
            self.data['invariant_verification'] = 'suite_and_fixture_checks_completed'
        # Any failed/interrupted run remains uncertified even if teardown passed.
        self.save()

    def run_pytest(self, arguments, plugins):
        self.data['stage'] = 'pytest'
        self.save()
        # Suppress pytest's own assertion/collection/warning/internal-error text.
        # Discard OS writes too, without buffering private output in temp files.
        # ExitStack restores/closes descriptors on success, error or interruption.
        with ExitStack() as stack:
            sink = stack.enter_context(open(os.devnull, 'w', encoding='utf-8', errors='backslashreplace'))
            for descriptor in (1, 2):
                saved = os.dup(descriptor)
                stack.callback(os.close, saved)
                stack.callback(os.dup2, saved, descriptor)
                os.dup2(sink.fileno(), descriptor)
            stack.enter_context(redirect_stdout(sink))
            stack.enter_context(redirect_stderr(sink))
            return pytest.main(arguments, plugins=plugins)

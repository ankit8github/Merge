"""Collection is credential-free. Execution requires the guarded owner entry point."""
import pytest
from test_support.races import RaceDatabase


def pytest_addoption(parser):
    parser.addoption('--confirm-merge-test', action='store_true')
    parser.addoption('--race-repetitions', type=int, default=3, choices=range(1, 11))


def pytest_generate_tests(metafunc):
    if 'repetition' in metafunc.fixturenames:
        metafunc.parametrize('repetition', range(metafunc.config.getoption('--race-repetitions')))


@pytest.fixture
def db(request, repetition):
    settings = getattr(request.config, '_merge_concurrency_settings', None)
    if not request.config.getoption('--confirm-merge-test') or settings is None:
        pytest.fail('Use python -m test_support.concurrency --confirm-merge-test; no database opened', pytrace=False)
    database = RaceDatabase(settings)
    try:
        yield database
    finally:
        # Fresh committed-state check even when a test assertion failed. No cleanup DML.
        database.check_invariants()

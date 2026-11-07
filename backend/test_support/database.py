"""Dedicated merge_test tools. No ordinary Settings or dotenv inheritance."""
import argparse
from contextlib import contextmanager
from dataclasses import dataclass, field
from getpass import getpass
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, create_engine, text


class DiagnosticFailure(ValueError):
    """Fixed category only; never retain driver messages or connection values."""
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def failure_category(error, stage):
    """Classify without formatting an exception, its arguments, SQL or URL."""
    category = error.category if isinstance(error, DiagnosticFailure) else None
    state = getattr(getattr(error, 'orig', error), 'sqlstate', None)
    if category is None:
        if isinstance(state, str) and state.startswith('28'):
            category = 'authentication'
        elif isinstance(state, str) and state.startswith('08'):
            category = 'connection'
        elif state == '42501':
            category = 'permission'
        elif isinstance(error, (ImportError, ModuleNotFoundError)):
            category = 'driver-configuration'
        else:
            category = stage
    # Even labels are allowlisted: never echo arbitrary exception attributes.
    allowed = {'authentication', 'connection', 'identity', 'permission',
               'migration-state', 'driver-configuration', 'verification', 'migration'}
    if category not in allowed:
        category = 'verification'
    return category


def safe_failure_message(error, stage):
    return (f'Test database command failed [{failure_category(error, stage)}]. Stop; '
            'connection details and exception text suppressed.')


@contextmanager
def diagnostic_stage(category):
    try:
        yield
    except DiagnosticFailure:
        raise
    except Exception as error:
        # SQLSTATE classification has priority over the operation stage.
        raise DiagnosticFailure(failure_category(error, category)) from None


@dataclass(frozen=True)
class TestDatabaseSettings:
    __test__ = False
    confirmed: bool = False
    host: str = '127.0.0.1'
    port: int = 5432
    database: str = 'merge_test'
    user: str = 'merge_app'
    password: str = field(default='', repr=False)

    def url(self):
        if (not self.confirmed or self.host != '127.0.0.1' or self.port != 5432
                or self.database != 'merge_test' or self.user != 'merge_app'):
            raise ValueError('Explicit local merge_test opt-in is required')
        return URL.create('postgresql+psycopg', username=self.user,
                          password=self.password or None, host=self.host,
                          port=self.port, database=self.database)


def assert_test_identity(connection):
    """Must run on every independent connection before any fixture writes."""
    identity = connection.execute(text('''SELECT current_database(), current_user,
        inet_server_addr()::text, inet_server_port()''')).one()
    if tuple(identity) != ('merge_test', 'merge_app', '127.0.0.1/32', 5432):
        # inet::text can omit the netmask depending on the server representation.
        if tuple(identity) != ('merge_test', 'merge_app', '127.0.0.1', 5432):
            raise DiagnosticFailure('identity')
    if connection.get_isolation_level() != 'READ COMMITTED':
        raise DiagnosticFailure('identity')


@contextmanager
def test_connection(settings):
    """Fresh physical connection; caller owns commit, default exit rolls back."""
    engine = create_engine(settings.url(), hide_parameters=True,
                           isolation_level='READ COMMITTED',
                           execution_options={'schema_translate_map': {None: 'public'}},
                           connect_args={'connect_timeout': 5,
                                         'options': '-c statement_timeout=15000 -c lock_timeout=5000'})
    try:
        with engine.connect() as connection:
            with diagnostic_stage('identity'):
                assert_test_identity(connection)
            connection.rollback()
            yield connection
    finally:
        engine.dispose()


def verify(connection):
    with diagnostic_stage('verification'):
        connection.execute(text('SET TRANSACTION READ ONLY'))
    with diagnostic_stage('identity'):
        assert_test_identity(connection)
    with diagnostic_stage('permission'):
        permissions = connection.execute(text('''SELECT
            has_database_privilege(current_user,current_database(),'CONNECT'),
            has_schema_privilege(current_user,'public','USAGE'),
            has_schema_privilege(current_user,'public','CREATE')''')).one()
        if not all(permissions):
            raise DiagnosticFailure('permission')
    with diagnostic_stage('migration-state'):
        exists = connection.execute(text("SELECT to_regclass('public.alembic_version') IS NOT NULL")).scalar_one()
        revisions = connection.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all() if exists else []
        if revisions not in ([], ['0002_domain']):
            raise DiagnosticFailure('migration-state')
    print('Verified merge_test / merge_app, READ COMMITTED, CONNECT and schema USAGE/CREATE')
    print('Alembic revision:', revisions[0] if revisions else 'base (no recorded revision)')
    connection.rollback()


def migrate(connection):
    assert_test_identity(connection)
    # A fresh target must contain no application objects. Existing head is repeatable.
    exists = connection.execute(text("SELECT to_regclass('public.alembic_version') IS NOT NULL")).scalar_one()
    if exists:
        revisions = connection.execute(text('SELECT version_num FROM public.alembic_version')).scalars().all()
        if revisions != ['0002_domain']:
            raise ValueError('Unexpected migration state; stop for review')
    else:
        count = connection.execute(text("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'")).scalar_one()
        routines = connection.execute(text("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'")).scalar_one()
        if count or routines:
            raise ValueError('Unexpected objects in fresh test database')
    connection.rollback()
    root = Path(__file__).resolve().parents[1]
    config = Config()
    config.set_main_option('path_separator', 'os')
    config.set_main_option('script_location', str(root / 'test_alembic'))
    config.set_main_option('version_locations', str(root / 'alembic' / 'versions'))
    config.attributes['merge_test_connection'] = connection
    command.upgrade(config, '0002_domain')
    print('Test migration command completed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify', 'migrate'))
    parser.add_argument('--confirm-merge-test', action='store_true', required=True)
    args = parser.parse_args()
    password = os.environ.get('MERGE_TEST_DB_PASSWORD')
    if password is None:
        import sys
        if not sys.stdin.isatty():
            parser.error('Use an interactive password prompt or explicit test-only secret environment')
        password = getpass('Existing merge_app password (hidden): ')
    stage = 'connection'
    try:
        with test_connection(TestDatabaseSettings(confirmed=args.confirm_merge_test, password=password)) as connection:
            stage = 'verification' if args.action == 'verify' else 'migration'
            (verify if args.action == 'verify' else migrate)(connection)
    except Exception as error:
        print(safe_failure_message(error, stage))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()

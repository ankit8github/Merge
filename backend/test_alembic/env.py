"""Online-only dedicated test runner; ordinary alembic/env.py is unchanged."""
from alembic import context
import app.models
from app.db.base import Base
from test_support.database import assert_test_identity

if context.is_offline_mode():
    raise RuntimeError('Test migrations require an online identity check')
connection = context.config.attributes.get('merge_test_connection')
if connection is None:
    raise RuntimeError('Use python -m test_support.database migrate --confirm-merge-test')
if not connection.in_transaction():
    raise RuntimeError('Dedicated runner must own the complete migration transaction')
assert_test_identity(connection)
context.configure(connection=connection, target_metadata=Base.metadata, include_schemas=True)
with context.begin_transaction():
    context.run_migrations()

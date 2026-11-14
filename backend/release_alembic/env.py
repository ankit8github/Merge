"""Only a caller-owned transaction from the fixed new-target migration tool."""
from alembic import context
import app.models
from app.db.base import Base
from release_support.targets import identity

if context.is_offline_mode(): raise RuntimeError('Use migration SQL rendering tests for offline validation')
c=context.config.attributes.get('release_connection')
target=context.config.attributes.get('release_target')
if c is None or target is None or not c.in_transaction(): raise RuntimeError('Guarded migration owner required')
identity(c,target)
context.configure(connection=c,target_metadata=Base.metadata,include_schemas=True)
with context.begin_transaction(): context.run_migrations()

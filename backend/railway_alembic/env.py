"""Only the explicit Railway operations CLI supplies this owned transaction."""
from alembic import context
from app.db.base import Base
import app.models
from app.railway.database import identity

if context.is_offline_mode(): raise RuntimeError('Use offline migration rendering tests')
c = context.config.attributes.get('railway_connection')
target = context.config.attributes.get('railway_target')
addresses = context.config.attributes.get('railway_addresses')
if c is None or target is None or target.role != 'migrator' or not c.in_transaction() or not addresses:
    raise RuntimeError('Railway migration transaction owner required')
identity(c, target, addresses)
context.configure(connection=c, target_metadata=Base.metadata, include_schemas=True)
with context.begin_transaction(): context.run_migrations()

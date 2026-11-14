"""Only the explicit production migration CLI may supply the owned transaction."""
from alembic import context
from app.db.base import Base
import app.models
from app.production.database import identity

if context.is_offline_mode():raise RuntimeError('Use offline migration rendering tests')
c=context.config.attributes.get('production_connection')
target=context.config.attributes.get('production_config')
if c is None or target is None or target.role!='migrator' or not c.in_transaction():
    raise RuntimeError('Production migration transaction owner required')
identity(c,target)
context.configure(connection=c,target_metadata=Base.metadata,include_schemas=True)
with context.begin_transaction():context.run_migrations()

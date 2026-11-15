"""Only the explicit fresh Render setup supplies an owned DDL transaction."""
from alembic import context
from app.db.base import Base
import app.models
from app.render.initialization import owner

if context.is_offline_mode(): raise RuntimeError('Use offline migration rendering tests')
c = context.config.attributes.get('render_connection')
target = context.config.attributes.get('render_target')
addresses = context.config.attributes.get('render_addresses')
if c is None or target is None or not c.in_transaction() or not addresses:
    raise RuntimeError('Explicit Render setup transaction required')
owner(c, target, addresses)
context.configure(connection=c, target_metadata=Base.metadata, include_schemas=True)
with context.begin_transaction(): context.run_migrations()

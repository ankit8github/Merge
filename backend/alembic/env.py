from alembic import context
from sqlalchemy import pool

from app.core.config import Settings
from app.db.base import Base
from app.db.session import build_engine


def run_migrations() -> None:
    if context.is_offline_mode():
        context.configure(
            url=Settings().database_url(),
            target_metadata=Base.metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    engine = build_engine(Settings())
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=Base.metadata)
            with context.begin_transaction():
                context.run_migrations()
    except Exception:
        raise RuntimeError("Migration failed; check local database configuration and provisioning") from None
    finally:
        engine.dispose()


run_migrations()

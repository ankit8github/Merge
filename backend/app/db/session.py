from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url(),
        pool_pre_ping=True,
        hide_parameters=True,
        isolation_level="READ COMMITTED",
        execution_options={"schema_translate_map": {None: "public"}},
        connect_args={"connect_timeout": 5},
    )

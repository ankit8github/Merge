from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Default-schema metadata, matching PostgreSQL/Alembic reflection.

    The engine compiles this default schema explicitly as public. Migration and
    trigger SQL is independently frozen and public-qualified.
    """

    metadata = MetaData(naming_convention={"pk": "pk_%(table_name)s"})

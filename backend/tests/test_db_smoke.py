import pytest
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import build_engine


@pytest.mark.database
def test_database_select_one():
    engine = build_engine(Settings())
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
    except Exception:
        # Never include driver exception text, credentials or connection URLs.
        pytest.fail("Database smoke failed; check local provisioning and configuration", pytrace=False)
    finally:
        engine.dispose()

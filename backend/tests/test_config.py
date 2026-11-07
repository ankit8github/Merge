import pytest
from pathlib import Path

from app.core.config import Settings


def test_default_env_file_is_backend_local_and_independent_of_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    expected = Path(__file__).resolve().parents[1] / ".env"
    assert Settings.model_config["env_file"] == expected
    assert expected.is_absolute()


def test_database_password_is_not_in_settings_repr():
    settings = Settings(_env_file=None, db_password="example-test-only")
    assert "example-test-only" not in repr(settings)


def test_environment_overrides_dotenv(monkeypatch, tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("MERGE_DB_PASSWORD=file-test-only\n", encoding="utf-8")
    monkeypatch.setenv("MERGE_DB_PASSWORD", "environment-test-only")
    settings = Settings(_env_file=dotenv)
    assert settings.db_password.get_secret_value() == "environment-test-only"


def test_dotenv_loading(monkeypatch, tmp_path):
    monkeypatch.delenv("MERGE_DB_PASSWORD", raising=False)
    dotenv = tmp_path / ".env"
    dotenv.write_text("MERGE_DB_PASSWORD=file-test-only\n", encoding="utf-8")
    assert Settings(_env_file=dotenv).db_password.get_secret_value() == "file-test-only"


@pytest.mark.parametrize("change", [{"db_name": "postgres"}, {"db_user": "postgres"}, {"db_host": "remote"}])
def test_database_target_guard(change):
    with pytest.raises(ValueError, match="Phase 0"):
        Settings(_env_file=None, **change).database_url()

from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest
from dotenv import dotenv_values


@pytest.fixture
def helper(monkeypatch, tmp_path):
    path = Path(__file__).resolve().parents[2] / "scripts" / "configure_backend_env.py"
    main = runpy.run_path(str(path))["main"]
    monkeypatch.setitem(main.__globals__, "ROOT", tmp_path)
    (tmp_path / "backend").mkdir()
    monkeypatch.setattr("sys.stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    return main, tmp_path / "backend" / ".env"


def test_password_roundtrip_and_no_output_leak(helper, monkeypatch, capsys):
    main, target = helper
    password = "test-only # ' \" \\ $ Unicode-é"
    monkeypatch.setattr("getpass.getpass", lambda prompt: password)
    main()
    assert dotenv_values(target)["MERGE_DB_PASSWORD"] == password
    assert password not in capsys.readouterr().out


def test_existing_env_is_preserved(helper):
    main, target = helper
    target.write_text("existing", encoding="utf-8")
    with pytest.raises(SystemExit, match="already exists"):
        main()
    assert target.read_text() == "existing"


def test_unignored_file_is_refused(helper, monkeypatch):
    main, target = helper
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=1))
    with pytest.raises(SystemExit, match="gitignored"):
        main()
    assert not target.exists()


@pytest.mark.parametrize("password", ["", "test-${VALUE}", "line\nbreak"])
def test_unsafe_or_empty_password_is_not_written(helper, monkeypatch, password):
    main, target = helper
    monkeypatch.setattr("getpass.getpass", lambda prompt: password)
    with pytest.raises(SystemExit):
        main()
    assert not target.exists()
